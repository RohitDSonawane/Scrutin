from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field
from app.tools.lib import http


# ── Schemas ────────────────────────────────────────────────────────────────────

class FactCheckRequest(BaseModel):
    query: str = Field(description="Claim keywords to look up in the Google Fact Check index")
    language_code: str = "en"
    max_results: int = 5


class FactCheckItem(BaseModel):
    claim_text: str
    claimant: Optional[str] = None
    verdict: str                    # "True" | "False" | "Misleading" | etc.
    review_publisher: str           # e.g. "Snopes", "PolitiFact"
    review_url: str
    review_date: Optional[str] = None


class FactCheckResponse(BaseModel):
    matches_found: int
    verdicts: list[FactCheckItem]
    query_used: str


# ── Tool function ──────────────────────────────────────────────────────────────

FACT_CHECK_API_URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"

def query_factcheck_db(request: FactCheckRequest, config: dict) -> FactCheckResponse:
    """
    Query the Google Fact Check Tools API for existing ClaimReview verdicts.
    This is the Evidence agent's fast-path: if a matching verdict already exists,
    no web search is needed.
    Config keys: GOOGLE_FACT_CHECK_API_KEY
    Returns empty list on any failure — never raises.
    """
    api_key = config.get("GOOGLE_FACT_CHECK_API_KEY", "")
    if not api_key:
        return FactCheckResponse(matches_found=0, verdicts=[], query_used=request.query)

    try:
        data = http.get(FACT_CHECK_API_URL, params={
            "key": api_key,
            "query": request.query,
            "languageCode": request.language_code,
            "pageSize": request.max_results,
        })
    except Exception:
        return FactCheckResponse(matches_found=0, verdicts=[], query_used=request.query)

    claims = data.get("claims", [])
    verdicts = []
    for claim in claims:
        for review in claim.get("claimReview", []):
            verdicts.append(FactCheckItem(
                claim_text=claim.get("text", ""),
                claimant=claim.get("claimant"),
                verdict=review.get("textualRating", "unknown"),
                review_publisher=review.get("publisher", {}).get("name", "unknown"),
                review_url=review.get("url", ""),
                review_date=review.get("reviewDate"),
            ))

    return FactCheckResponse(
        matches_found=len(verdicts),
        verdicts=verdicts,
        query_used=request.query,
    )


# ── Academic & Literature Tools ───────────────────────────────────────────────

class AcademicSearchRequest(BaseModel):
    query: str = Field(description="Scientific or medical claim keywords to search in academic literature")
    max_results: int = 5


class AcademicPaperItem(BaseModel):
    title: str
    authors: list[str] = Field(default_factory=list)
    journal_or_publisher: str = ""
    published_year: Optional[int] = None
    abstract_snippet: str = ""
    doi_or_url: str = ""
    is_retracted: bool = False


class AcademicSearchResponse(BaseModel):
    matches_found: int
    papers: list[AcademicPaperItem]
    query_used: str
    source_database: str


def search_pubmed(request: AcademicSearchRequest) -> AcademicSearchResponse:
    """
    Search NCBI PubMed API for biomedical and clinical literature.
    Never raises — returns empty list on network failure.
    """
    try:
        import requests
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        resp = requests.get(url, params={"db": "pubmed", "term": request.query, "retmode": "json", "retmax": request.max_results}, timeout=10)
        data = resp.json()
        id_list = data.get("esearchresult", {}).get("idlist", [])
        if not id_list:
            return AcademicSearchResponse(matches_found=0, papers=[], query_used=request.query, source_database="pubmed")

        # Fetch paper summaries
        summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        sum_resp = requests.get(summary_url, params={"db": "pubmed", "id": ",".join(id_list), "retmode": "json"}, timeout=10)
        sum_data = sum_resp.json().get("result", {})

        papers = []
        for uid in id_list:
            item = sum_data.get(uid, {})
            if item and "title" in item:
                authors = [a.get("name", "") for a in item.get("authors", []) if "name" in a]
                pub_date = item.get("pubdate", "")
                year = int(pub_date.split()[0]) if pub_date and pub_date.split()[0].isdigit() else None
                papers.append(AcademicPaperItem(
                    title=item.get("title", ""),
                    authors=authors[:3],
                    journal_or_publisher=item.get("source", "PubMed"),
                    published_year=year,
                    abstract_snippet=f"PMID: {uid}. {item.get('title', '')}",
                    doi_or_url=f"https://pubmed.ncbi.nlm.nih.gov/{uid}/",
                    is_retracted="retracted" in item.get("title", "").lower(),
                ))
        return AcademicSearchResponse(matches_found=len(papers), papers=papers, query_used=request.query, source_database="pubmed")
    except Exception:
        return AcademicSearchResponse(matches_found=0, papers=[], query_used=request.query, source_database="pubmed")


def search_arxiv(request: AcademicSearchRequest) -> AcademicSearchResponse:
    """
    Search ArXiv API for preprints in physics, computer science, mathematics, climate.
    Never raises — returns empty list on network failure.
    """
    try:
        import requests
        import xml.etree.ElementTree as ET
        url = "http://export.arxiv.org/api/query"
        resp = requests.get(url, params={"search_query": f"all:{request.query}", "max_results": request.max_results}, timeout=10)
        root = ET.fromstring(resp.content)

        ns = {"atom": "http://www.w3.org/2005/Atom"}
        papers = []
        for entry in root.findall("atom:entry", ns):
            title = (entry.findtext("atom:title", "", ns) or "").strip().replace("\n", " ")
            summary = (entry.findtext("atom:summary", "", ns) or "").strip().replace("\n", " ")
            link = entry.findtext("atom:id", "", ns) or ""
            published = entry.findtext("atom:published", "", ns) or ""
            year = int(published[:4]) if len(published) >= 4 and published[:4].isdigit() else None
            authors = [a.findtext("atom:name", "", ns) for a in entry.findall("atom:author", ns)]

            papers.append(AcademicPaperItem(
                title=title,
                authors=authors[:3],
                journal_or_publisher="ArXiv",
                published_year=year,
                abstract_snippet=summary[:300],
                doi_or_url=link,
                is_retracted="withdrawn" in title.lower() or "retracted" in title.lower(),
            ))
        return AcademicSearchResponse(matches_found=len(papers), papers=papers, query_used=request.query, source_database="arxiv")
    except Exception:
        return AcademicSearchResponse(matches_found=0, papers=[], query_used=request.query, source_database="arxiv")


def search_semantic_scholar(request: AcademicSearchRequest) -> AcademicSearchResponse:
    """
    Search Semantic Scholar Graph API for academic citations and impact details.
    Never raises — returns empty list on network failure.
    """
    try:
        import requests
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        resp = requests.get(url, params={"query": request.query, "limit": request.max_results, "fields": "title,authors,year,abstract,externalIds,isPublicationType"}, timeout=10)
        data = resp.json()
        raw_papers = data.get("data", [])

        papers = []
        for p in raw_papers:
            authors = [a.get("name", "") for a in p.get("authors", [])]
            paper_id = p.get("paperId", "")
            papers.append(AcademicPaperItem(
                title=p.get("title", ""),
                authors=authors[:3],
                journal_or_publisher="Semantic Scholar",
                published_year=p.get("year"),
                abstract_snippet=(p.get("abstract") or "")[:300],
                doi_or_url=f"https://www.semanticscholar.org/paper/{paper_id}",
                is_retracted=False,
            ))
        return AcademicSearchResponse(matches_found=len(papers), papers=papers, query_used=request.query, source_database="semantic_scholar")
    except Exception:
        return AcademicSearchResponse(matches_found=0, papers=[], query_used=request.query, source_database="semantic_scholar")

