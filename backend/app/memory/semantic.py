from __future__ import annotations
import os
from typing import Optional

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
    Generate a 768-dim embedding for a claim text using gemini-embedding-001.
    IMPORTANT: Do NOT use 'text-embedding-3-small' — that is an OpenAI model name.
    """
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    result = genai.embed_content(
        model="models/gemini-embedding-001",
        content=text,
        task_type="retrieval_query",
    )
    return result["embedding"]


async def upsert_claim(
    claim_id: str,
    claim_text: str,
    run_id: str,
    verdict: str,
    config: dict,
    db_path: str = "scrutin.db",
) -> None:
    """
    Store a verified claim embedding in Pinecone AND write metadata to claim_similarity_cache.
    Called by Orchestrator at run completion.

    Two-store pattern:
    1. Pinecone: vector for semantic similarity search
    2. SQLite claim_similarity_cache: metadata for fast offline lookup + stats
    """
    api_key = config.get("PINECONE_API_KEY") or config.get("GOOGLE_API_KEY")
    if not api_key or not config.get("PINECONE_API_KEY"):
        return  # Skip if Pinecone not configured

    try:
        vector = embed_claim(claim_text, config["GOOGLE_API_KEY"])
        pc = _get_pinecone(config["PINECONE_API_KEY"])
        index = pc.Index(PINECONE_INDEX_NAME)
        pinecone_vector_id = f"{run_id}_{claim_id}"
        index.upsert(
            vectors=[{
                "id": pinecone_vector_id,
                "values": vector,
                "metadata": {"run_id": run_id, "verdict": verdict, "text": claim_text[:200]}
            }],
            namespace=CLAIMS_NAMESPACE,
        )
        # Write metadata to SQLite claim_similarity_cache (Table 4 in database-schema.md)
        import aiosqlite
        async with aiosqlite.connect(db_path, timeout=30.0, isolation_level=None) as db:
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("BEGIN IMMEDIATE")
            try:
                await db.execute(
                    """INSERT OR REPLACE INTO claim_similarity_cache
                       (claim_id, claim_text, pinecone_vector_id, run_id, verdict, created_at)
                       VALUES (?, ?, ?, ?, ?, datetime('now'))""",
                    (claim_id, claim_text[:500], pinecone_vector_id, run_id, verdict)
                )
                await db.execute("COMMIT")
            except Exception as e:
                try:
                    await db.execute("ROLLBACK")
                except Exception:
                    pass
                raise e
    except Exception as e:
        from loguru import logger
        logger.warning(f"Pinecone upsert failed (non-fatal): {e}")


async def search_similar_claims(
    claim_text: str,
    config: dict,
    top_k: int = 3,
    score_threshold: float = 0.92,
) -> list[dict]:
    """
    Search Pinecone for semantically similar past claims.
    Score >= 0.92 → very likely the same claim (use as fast-path).
    Returns list of {claim_id, run_id, verdict, score, text}.
    """
    if not config.get("PINECONE_API_KEY") or not config.get("GOOGLE_API_KEY"):
        return []

    try:
        vector = embed_claim(claim_text, config["GOOGLE_API_KEY"])
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
        return matches
    except Exception as e:
        from loguru import logger
        logger.warning(f"Pinecone search failed (non-fatal): {e}")
        return []
