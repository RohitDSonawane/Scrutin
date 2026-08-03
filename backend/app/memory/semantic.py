from __future__ import annotations
import math
import os
from typing import Any

PINECONE_INDEX_NAME = "scrutin-claims"
EMBEDDING_DIM = 768
CLAIMS_NAMESPACE = "claims"


def _get_pinecone(api_key: str):
    from pinecone import Pinecone, ServerlessSpec
    pc = Pinecone(api_key=api_key)
    if PINECONE_INDEX_NAME not in [i.name for i in pc.list_indexes()]:
        pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=EMBEDDING_DIM,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
    return pc


def embed_claim(text: str, api_key: str) -> list[float]:
    """
    Generate a 768-dim embedding for a claim text using the standard google.genai SDK.
    Embedding model resolved from EMBEDDING_MODEL env var.
    IMPORTANT: Do NOT use 'text-embedding-3-small' — that is an OpenAI model name.
    """
    from google import genai

    client = genai.Client(api_key=api_key)
    embedding_model = os.getenv("EMBEDDING_MODEL")
    if not embedding_model:
        raise RuntimeError("No embedding model configured: set EMBEDDING_MODEL in .env")
    if embedding_model.startswith("models/"):
        embedding_model = embedding_model.replace("models/", "")

    response = client.models.embed_content(
        model=embedding_model,
        contents=text,
    )
    emb = response.embeddings[0].values
    return emb[:EMBEDDING_DIM]


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    dot_product = sum(a * b for a, b in zip(v1, v2))
    mag1 = math.sqrt(sum(a * a for a in v1))
    mag2 = math.sqrt(sum(b * b for b in v2))
    if not mag1 or not mag2:
        return 0.0
    return dot_product / (mag1 * mag2)


async def upsert_claim(
    claim_id: str,
    claim_text: str,
    run_id: str,
    verdict: str,
    config: dict,
    db_path: str = "scrutin.db",
) -> None:
    """
    Local-First Vector Store:
    1. Embeds claim text via Google GenAI SDK (if GOOGLE_API_KEY present).
    2. Writes metadata + vector_json to local SQLite claim_similarity_cache.
    3. Syncs to Pinecone cloud index if PINECONE_API_KEY is present.
    """
    google_key = config.get("GOOGLE_API_KEY")
    if not google_key:
        return

    import json
    import asyncio
    from loguru import logger

    pinecone_vector_id = f"{run_id}_{claim_id}"
    vector: list[float] = []

    try:
        vector = await asyncio.to_thread(embed_claim, claim_text, google_key)
    except Exception as e:
        logger.warning(f"Claim embedding failed (non-fatal): {e}")

    # Optional Pinecone Cloud Sync
    if config.get("PINECONE_API_KEY") and vector:
        try:
            pc = await asyncio.to_thread(_get_pinecone, config["PINECONE_API_KEY"])
            index = pc.Index(PINECONE_INDEX_NAME)
            await asyncio.to_thread(
                index.upsert,
                vectors=[{
                    "id": pinecone_vector_id,
                    "values": vector,
                    "metadata": {"run_id": run_id, "verdict": verdict, "text": claim_text[:200]}
                }],
                namespace=CLAIMS_NAMESPACE,
            )
        except Exception as e:
            logger.warning(f"Pinecone sync failed (non-fatal): {e}")

    # Always write to local SQLite claim_similarity_cache
    import aiosqlite
    async with aiosqlite.connect(db_path, timeout=30.0, isolation_level=None) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("BEGIN IMMEDIATE")
        try:
            vector_json = json.dumps(vector) if vector else None
            await db.execute(
                """INSERT OR REPLACE INTO claim_similarity_cache
                   (claim_id, claim_text, pinecone_vector_id, run_id, verdict, vector_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, datetime('now'))""",
                (claim_id, claim_text[:500], pinecone_vector_id, run_id, verdict, vector_json)
            )
            await db.execute("COMMIT")
        except Exception as e:
            try:
                await db.execute("ROLLBACK")
            except Exception:
                pass
            logger.error(f"Local SQLite claim_similarity_cache write failed: {e}")


async def search_similar_claims(
    claim_text: str,
    config: dict,
    top_k: int = 3,
    score_threshold: float = 0.92,
    db_path: str = "scrutin.db",
) -> list[dict]:
    """
    Search for semantically similar past claims.
    1. Tries Pinecone search if PINECONE_API_KEY is configured.
    2. Falls back to local cosine similarity search over SQLite claim_similarity_cache.
    Score >= 0.92 → fast-path episodic match.
    Returns list of {claim_id, run_id, verdict, score, text}.
    """
    google_key = config.get("GOOGLE_API_KEY")
    if not google_key:
        return []

    import json
    from loguru import logger

    try:
        vector = embed_claim(claim_text, google_key)
    except Exception as e:
        logger.warning(f"Claim embedding failed for search (non-fatal): {e}")
        return []

    # 1. Try Pinecone if key present
    if config.get("PINECONE_API_KEY"):
        try:
            pc = _get_pinecone(config["PINECONE_API_KEY"])
            index = pc.Index(PINECONE_INDEX_NAME)
            results = index.query(
                vector=vector,
                top_k=top_k,
                include_metadata=True,
                namespace=CLAIMS_NAMESPACE,
            )
            matches = []
            for m in results.get("matches", []):
                if m["score"] >= score_threshold:
                    matches.append({
                        "claim_id": m["id"],
                        "run_id": m["metadata"].get("run_id"),
                        "verdict": m["metadata"].get("verdict"),
                        "score": m["score"],
                        "text": m["metadata"].get("text"),
                    })
            if matches:
                return matches
        except Exception as e:
            logger.warning(f"Pinecone query failed (falling back to local vector search): {e}")

    # 2. Local vector search over SQLite claim_similarity_cache
    try:
        import aiosqlite
        async with aiosqlite.connect(db_path, timeout=30.0) as db:
            await db.execute("PRAGMA journal_mode=WAL")
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT claim_id, run_id, verdict, claim_text, vector_json FROM claim_similarity_cache WHERE vector_json IS NOT NULL"
            ) as cursor:
                rows = await cursor.fetchall()

        scored_matches = []
        for r in rows:
            try:
                cached_vec = json.loads(r["vector_json"])
                if cached_vec:
                    sim_score = cosine_similarity(vector, cached_vec)
                    if sim_score >= score_threshold:
                        scored_matches.append({
                            "claim_id": r["claim_id"],
                            "run_id": r["run_id"],
                            "verdict": r["verdict"],
                            "score": sim_score,
                            "text": r["claim_text"],
                        })
            except Exception:
                continue

        scored_matches.sort(key=lambda x: x["score"], reverse=True)
        return scored_matches[:top_k]
    except Exception as e:
        logger.warning(f"Local SQLite vector search failed (non-fatal): {e}")
        return []
