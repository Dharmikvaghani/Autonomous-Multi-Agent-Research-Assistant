"""
Academic Research Retrieval Tool Module
Integrates arXiv, Semantic Scholar, and Crossref APIs to retrieve high-fidelity scientific literature.
Includes citation counts, peer-reviewed indexing, latency logging, and score-based ranking.
"""

import time
import logging
import math
import re
import requests
import xml.etree.ElementTree as ET
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to sys.path to resolve 'tools' package correctly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force UTF-8 encoding for standard output/error on Windows to prevent console print crashes with emojis/unicode
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Setup module logger
logger = logging.getLogger(__name__)

# Constants
CURRENT_YEAR = 2026

def clean_title(title: str) -> str:
    """Helper to normalize paper titles for deduplication."""
    if not title:
        return ""
    return re.sub(r"[^a-z0-9]", "", title.lower())

def clean_abstract(abstract: str) -> str:
    """
    Cleans up JATS XML tags and other HTML-like tags commonly found in Crossref abstracts.
    Prevents markdown auto-link parser issues in Streamlit.
    """
    if not abstract:
        return "No abstract available."
        
    # Remove XML/HTML tags like <jats:p>, <jats:title>, etc.
    cleaned = re.sub(r"<[^>]+>", " ", abstract)
    
    # Normalize multiple spaces and newlines
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    
    # If the abstract is empty or just whitespace after cleaning
    if not cleaned or cleaned.lower() in ["no abstract", "no abstract available", "abstract"]:
        return "No abstract available."
        
    # Remove leading prefix like "Abstract: " or "abstract: " if present
    cleaned = re.sub(r"^abstract:\s*", "", cleaned, flags=re.IGNORECASE)
        
    return cleaned
import threading

# Thread locks and rate-limiting timestamp tracking for API query spacing
_arxiv_lock = threading.Lock()
_last_arxiv_time = 0.0

_semantic_scholar_lock = threading.Lock()
_last_semantic_scholar_time = 0.0

_crossref_lock = threading.Lock()
_last_crossref_time = 0.0


def search_arxiv(query: str, limit: int = 10) -> list:
    """
    Searches arXiv API using direct XML HTTP requests.
    Fails fast on HTTP 429 or network errors to prevent hanging.
    """
    global _last_arxiv_time
    with _arxiv_lock:
        elapsed = time.time() - _last_arxiv_time
        if elapsed < 1.5:
            sleep_needed = 1.5 - elapsed
            time.sleep(sleep_needed)
        _last_arxiv_time = time.time()

    start_time = time.perf_counter()
    papers = []
    print(f"[*] Academic Search: Starting arXiv query for: '{query}'")
    
    # Format query words as 'all:word1 AND all:word2' for valid arXiv Boolean parser syntax
    words = [w.strip() for w in query.split() if w.strip()]
    if not words:
        return []
    arxiv_query = " AND ".join([f"all:{w}" for w in words])
    
    url = "https://export.arxiv.org/api/query"
    params = {
        "search_query": arxiv_query,
        "max_results": limit,
        "sortBy": "relevance",
        "sortOrder": "descending"
    }
    
    # Use custom descriptive User-Agent to avoid blocks
    headers = {"User-Agent": "PrismResearchAssistant/1.0 (mailto:support@prism-ai.org)"}
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=4)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            
            for entry in root.findall('atom:entry', ns):
                title_elem = entry.find('atom:title', ns)
                title = title_elem.text.strip() if title_elem is not None and title_elem.text else "No Title"
                title = re.sub(r'\s+', ' ', title) # Clean linebreaks in XML titles
                
                summary_elem = entry.find('atom:summary', ns)
                abstract = summary_elem.text.strip() if summary_elem is not None and summary_elem.text else "No abstract available."
                abstract = re.sub(r'\s+', ' ', abstract)
                
                published_elem = entry.find('atom:published', ns)
                year = CURRENT_YEAR
                if published_elem is not None and published_elem.text:
                    year_match = re.match(r"^(\d{4})", published_elem.text)
                    if year_match:
                        year = int(year_match.group(1))
                        
                authors = []
                for author in entry.findall('atom:author', ns):
                    name_elem = author.find('atom:name', ns)
                    if name_elem is not None and name_elem.text:
                        authors.append(name_elem.text.strip())
                if not authors:
                    authors = ["Unknown Author"]
                    
                paper_url = "#"
                for link in entry.findall('atom:link', ns):
                    if link.attrib.get('rel') == 'alternate':
                        paper_url = link.attrib.get('href', '#')
                    elif link.attrib.get('title') == 'pdf':
                        paper_url = link.attrib.get('href', '#')
                        
                papers.append({
                    "title": title,
                    "authors": authors,
                    "abstract": abstract,
                    "year": year,
                    "citations": 0,
                    "url": paper_url,
                    "venue": "arXiv",
                    "source": "arXiv",
                    "doi": "N/A"
                })
                
            latency = time.perf_counter() - start_time
            print(f"[*] Academic Search: Successfully retrieved {len(papers)} papers from arXiv in {latency:.2f}s.")
            logger.info(f"arXiv retrieval: {len(papers)} papers, latency: {latency:.2f}s")
            return papers
        else:
            latency = time.perf_counter() - start_time
            print(f"[!] Academic Search Warning: arXiv API responded with code {response.status_code} (possibly rate-limited).")
            logger.warning(f"arXiv API status code {response.status_code}")
            return []
    except Exception as e:
        latency = time.perf_counter() - start_time
        print(f"[!] Academic Search Warning: arXiv query failed. Detail: {e}")
        logger.warning(f"arXiv query failed: {e}")
        return []

def search_semantic_scholar(query: str, limit: int = 10) -> list:
    """
    Queries Semantic Scholar Graph API for metadata and citation counts.
    Fails fast on HTTP 429 or network errors to prevent hanging.
    Supports SEMANTIC_SCHOLAR_API_KEY environment variable to increase rate limits.
    """
    import os
    global _last_semantic_scholar_time
    with _semantic_scholar_lock:
        elapsed = time.time() - _last_semantic_scholar_time
        if elapsed < 1.05:
            sleep_needed = 1.05 - elapsed
            time.sleep(sleep_needed)
        _last_semantic_scholar_time = time.time()

    start_time = time.perf_counter()
    papers = []
    print(f"[*] Academic Search: Starting Semantic Scholar query for: '{query}'")
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": limit,
        "fields": "title,authors,abstract,year,citationCount,venue,url,externalIds"
    }
    headers = {}
    api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
    if api_key:
        headers["x-api-key"] = api_key.strip()
        
    try:
        max_attempts = 1
        response = None
        for attempt in range(max_attempts):
            response = requests.get(url, params=params, headers=headers, timeout=3)
            if response.status_code == 429:
                break
            break
            
        if response and response.status_code == 200:
            data = response.json()
            raw_papers = data.get("data", [])
            for p in raw_papers:
                authors = [a.get("name", "Unknown") for a in p.get("authors", [])]
                venue = p.get("venue") or ""
                
                # Check for arXiv preprint indicators
                external_ids = p.get("externalIds") or {}
                arxiv_id = external_ids.get("ArXiv")
                doi = external_ids.get("DOI")
                
                source = "Semantic Scholar"
                paper_url = p.get("url") or "#"
                
                if arxiv_id:
                    source = "arXiv"
                    paper_url = f"https://arxiv.org/abs/{arxiv_id}"
                elif venue.lower() == "arxiv" or "arxiv" in paper_url.lower():
                    source = "arXiv"
                
                papers.append({
                    "title": p.get("title", "No Title").strip(),
                    "authors": authors,
                    "abstract": p.get("abstract") or "No abstract available.",
                    "year": p.get("year") or CURRENT_YEAR,
                    "citations": p.get("citationCount") or 0,
                    "url": paper_url,
                    "venue": venue.strip() if venue else ("arXiv" if source == "arXiv" else ""),
                    "source": source,
                    "doi": doi or "N/A"
                })
            latency = time.perf_counter() - start_time
            print(f"[*] Academic Search: Successfully retrieved {len(papers)} papers from Semantic Scholar in {latency:.2f}s.")
            logger.info(f"Semantic Scholar retrieval: {len(papers)} papers, latency: {latency:.2f}s")
            return papers
        else:
            latency = time.perf_counter() - start_time
            print(f"[!] Academic Search Warning: Semantic Scholar API responded with code {response.status_code} (possibly rate-limited).")
            logger.warning(f"Semantic Scholar API status code {response.status_code}")
            return []
    except Exception as e:
        latency = time.perf_counter() - start_time
        print(f"[!] Academic Search Warning: Semantic Scholar query failed. Detail: {e}")
        logger.warning(f"Semantic Scholar query failed: {e}")
        return []

def search_crossref(query: str, limit: int = 10) -> list:
    """
    Queries Crossref Rest API via requests to find peer-reviewed papers.
    Fails fast on HTTP 429 or network errors to prevent hanging.
    """
    global _last_crossref_time
    with _crossref_lock:
        elapsed = time.time() - _last_crossref_time
        if elapsed < 1.05:
            sleep_needed = 1.05 - elapsed
            time.sleep(sleep_needed)
        _last_crossref_time = time.time()

    start_time = time.perf_counter()
    papers = []
    print(f"[*] Academic Search: Starting Crossref query for: '{query}'")
    url = "https://api.crossref.org/works"
    params = {"query": query, "rows": limit}
    headers = {"User-Agent": "PrismResearchAssistant/1.0 (mailto:support@prism-ai.org)"}
    try:
        response = requests.get(url, params=params, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            items = data.get("message", {}).get("items", [])
            for item in items:
                titles = item.get("title", [])
                title = titles[0] if titles else "No Title"
                
                authors = []
                for auth in item.get("author", []):
                    given = auth.get("given", "")
                    family = auth.get("family", "")
                    name = f"{given} {family}".strip()
                    if name:
                        authors.append(name)
                if not authors:
                    authors = ["Unknown Author"]
                    
                issued = item.get("issued", {})
                date_parts = issued.get("date-parts", [[]])
                year = CURRENT_YEAR
                if date_parts and date_parts[0] and len(date_parts[0]) > 0:
                    raw_year = date_parts[0][0]
                    try:
                        year = int(raw_year)
                    except (TypeError, ValueError):
                        year = CURRENT_YEAR
                
                container = item.get("container-title", [])
                venue = container[0] if container else (item.get("publisher") or "")
                
                # Clean JATS XML tags from abstract immediately at construction time
                raw_abstract = item.get("abstract") or ""
                cleaned_abstract = clean_abstract(raw_abstract)
                
                papers.append({
                    "title": title.strip(),
                    "authors": authors,
                    "abstract": cleaned_abstract,
                    "year": year,
                    "citations": item.get("is-referenced-by-count") or 0,
                    "url": item.get("URL") or "#",
                    "venue": venue.strip(),
                    "source": "Crossref",
                    "doi": item.get("DOI") or "N/A"
                })
            latency = time.perf_counter() - start_time
            print(f"[*] Academic Search: Successfully retrieved {len(papers)} papers from Crossref in {latency:.2f}s.")
            logger.info(f"Crossref retrieval: {len(papers)} papers, latency: {latency:.2f}s")
            return papers
        else:
            latency = time.perf_counter() - start_time
            print(f"[!] Academic Search Warning: Crossref API responded with code {response.status_code} (possibly rate-limited).")
            logger.warning(f"Crossref API status code {response.status_code}")
            return []
    except Exception as e:
        latency = time.perf_counter() - start_time
        print(f"[!] Academic Search Warning: Crossref query failed. Detail: {e}")
        logger.warning(f"Crossref query failed: {e}")
        return []

def rank_and_deduplicate_papers(papers: list, target_limit: int = 10, query: str = "") -> list:
    """
    Ranks papers based on citation counts, recency, peer-reviewed status, and keyword relevance.
    Deduplicates records based on title similarity.
    Ensures source diversification by using a round-robin selection across
    different databases (arXiv, Semantic Scholar, Crossref).
    """
    # Parse query keywords
    query_words = []
    if query:
        stopwords = {"in", "on", "the", "a", "of", "and", "for", "to", "with", "by", "an", "at", "from", "using", "through", "about", "study"}
        raw_words = re.findall(r'[a-z0-9]+', query.lower())
        query_words = [w for w in raw_words if len(w) >= 2 and w not in stopwords]

    filtered_papers = []

    # 1. Calculate ranking score for all retrieved papers first
    for paper in papers:
        # Clean abstract first to remove XML/HTML tags
        paper["abstract"] = clean_abstract(paper.get("abstract", ""))
        
        title = paper.get("title", "")
        abstract = paper.get("abstract", "")
        
        # Calculate keyword relevance match
        relevance_score = 0.0
        matched_count = 0
        
        if query_words:
            title_lower = title.lower()
            abstract_lower = abstract.lower()
            
            for qw in query_words:
                matched_in_title = False
                matched_in_abstract = False
                
                if qw in title_lower:
                    matched_in_title = True
                else:
                    t_words = re.findall(r'[a-z0-9]+', title_lower)
                    for tw in t_words:
                        if len(tw) >= 3 and (tw.startswith(qw) or qw.startswith(tw)):
                            matched_in_title = True
                            break
                            
                if qw in abstract_lower:
                    matched_in_abstract = True
                else:
                    a_words = re.findall(r'[a-z0-9]+', abstract_lower)
                    for aw in a_words:
                        if len(aw) >= 3 and (aw.startswith(qw) or qw.startswith(aw)):
                            matched_in_abstract = True
                            break
                            
                if matched_in_title:
                    matched_count += 1
                    relevance_score += 12.0  # High weight for title match
                elif matched_in_abstract:
                    matched_count += 1
                    relevance_score += 5.0   # Medium weight for abstract match

            # Strict relevance filter: if query has keywords and we match 0 of them,
            # we discard this paper completely as unrelated to enforce 100% matched rule.
            if query_words and matched_count == 0:
                continue
                
            # Extra boost for higher keyword match ratio
            match_ratio = matched_count / len(query_words)
            relevance_score += match_ratio * 20.0
            
        citations = paper.get("citations", 0)
        citation_score = math.log1p(citations) * 1.5
        
        year = paper.get("year")
        if year is None:
            year = CURRENT_YEAR
            paper["year"] = CURRENT_YEAR
        age = max(0, CURRENT_YEAR - year)
        recency_score = max(0, 10 - age) * 0.4
        
        venue = paper.get("venue", "")
        peer_reviewed_bonus = 2.0 if (venue and venue.lower() != "arxiv") else 0.0
        
        # Abstract bonus: reward papers that actually provide an abstract (critical for RAG)
        abstract_bonus = 3.0 if (abstract and abstract != "No abstract available.") else 0.0
        
        # Source priority bonus: prioritize Semantic Scholar (best URLs/accuracy) and arXiv over Crossref
        src = paper.get("source", "")
        source_bonus = 2.0 if src == "Semantic Scholar" else (1.0 if src == "arXiv" else 0.0)
        
        paper["ranking_score"] = (
            citation_score 
            + recency_score 
            + peer_reviewed_bonus 
            + abstract_bonus 
            + source_bonus 
            + relevance_score
        )
        filtered_papers.append(paper)

    # 2. Sort all papers by ranking score descending so we keep the highest-scoring version during deduplication
    filtered_papers.sort(key=lambda x: x.get("ranking_score", 0), reverse=True)
    
    seen_titles = {}
    for paper in filtered_papers:
        normalized_title = clean_title(paper["title"])
        if normalized_title:
            if normalized_title not in seen_titles:
                seen_titles[normalized_title] = paper
            else:
                existing = seen_titles[normalized_title]
                # Merge abstract if the higher scoring one is missing it
                if paper.get("ranking_score", 0) > existing.get("ranking_score", 0):
                    if not paper.get("abstract") or paper.get("abstract") == "No abstract available.":
                        if existing.get("abstract") and existing.get("abstract") != "No abstract available.":
                            paper["abstract"] = existing["abstract"]
                    seen_titles[normalized_title] = paper
                else:
                    if not existing.get("abstract") or existing.get("abstract") == "No abstract available.":
                        if paper.get("abstract") and paper.get("abstract") != "No abstract available.":
                            existing["abstract"] = paper["abstract"]

    unique_papers = list(seen_titles.values())
    
    # 3. Group papers by source
    by_source = {
        "arXiv": [],
        "Semantic Scholar": [],
        "Crossref": []
    }
    
    for paper in unique_papers:
        src = paper.get("source", "Semantic Scholar")
        if src not in by_source:
            by_source[src] = []
        by_source[src].append(paper)
        
    # 4. Round-robin selection to guarantee source diversification
    diversified_papers = []
    sources = ["Semantic Scholar", "arXiv", "Crossref"]
    source_indices = {src: 0 for src in by_source.keys()}
    
    while len(diversified_papers) < target_limit:
        added_in_round = False
        for src in sources:
            if src in by_source and source_indices[src] < len(by_source[src]):
                idx = source_indices[src]
                diversified_papers.append(by_source[src][idx])
                source_indices[src] += 1
                added_in_round = True
                if len(diversified_papers) >= target_limit:
                    break
        if not added_in_round:
            break
            
    # Also handle any other sources just in case
    for src, papers_list in by_source.items():
        if src not in sources:
            while len(diversified_papers) < target_limit and source_indices[src] < len(papers_list):
                idx = source_indices[src]
                diversified_papers.append(papers_list[idx])
                source_indices[src] += 1
                
    # 5. Sort final selection by score descending for presentation
    diversified_papers.sort(key=lambda x: x.get("ranking_score", 0), reverse=True)
    return diversified_papers


def optimize_search_query(query: str) -> str:
    """
    Optimizes a conversational research topic into a clean, keyword-focused
    academic query suitable for arXiv, Semantic Scholar, and Crossref.
    Uses ultra-fast local keyword extraction to prevent external API lag and timeouts.
    """
    if not query or not query.strip():
        return ""
        
    stopwords = {
        "a", "about", "above", "across", "after", "again", "against", "all", "an", "and",
        "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
        "between", "both", "but", "by", "can", "cannot", "could", "couldn't", "did",
        "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during", "each",
        "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have",
        "haven't", "having", "he", "her", "here", "hers", "herself", "him", "himself",
        "his", "how", "i", "if", "in", "into", "is", "isn't", "it", "its", "itself",
        "me", "more", "most", "my", "myself", "no", "nor", "not", "of", "off", "on",
        "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over",
        "own", "same", "she", "should", "shouldn't", "so", "some", "such", "than", "that",
        "the", "their", "theirs", "them", "themselves", "then", "there", "these", "they",
        "this", "those", "through", "to", "too", "under", "until", "up", "very", "was",
        "wasn't", "we", "were", "weren't", "what", "when", "where", "which", "while", "who",
        "whom", "why", "with", "won't", "would", "wouldn't", "you", "your", "yours", "yourself",
        "yourselves", "give", "me", "tell", "study", "analysis", "investigate", "research",
        "overview", "summary", "report"
    }

    cleaned = re.sub(r'[^a-zA-Z0-9\s-]', ' ', query)
    tokens = [w.strip() for w in cleaned.split() if w.strip()]
    meaningful = [w for w in tokens if w.lower() not in stopwords and len(w) > 2]

    if len(meaningful) >= 2:
        optimized = " ".join(meaningful[:5])
    elif tokens:
        optimized = " ".join(tokens[:5])
    else:
        optimized = query

    return optimized


def search_academic_literature(query: str, limit: int = 10) -> list:
    """
    Orchestrates searches across arXiv, Semantic Scholar, and Crossref.
    Aggregates, dedups, and ranks results. Returns list of papers.
    Queries Crossref only as a fallback if arXiv and Semantic Scholar yield insufficient results.
    Guaranteed bounded execution with strict timeouts.
    """
    if not query or not query.strip():
        return []
        
    start_time = time.perf_counter()
    
    # Optimize query for academic databases
    search_term = optimize_search_query(query)
    
    # Fetch more candidates to ensure we can filter and find the best ones
    fetch_limit = limit + 5
    
    # Run API retrievals concurrently in a thread pool to avoid sequential HTTP blocking
    from concurrent.futures import ThreadPoolExecutor
    print(f"[*] Academic Search: Querying arXiv and Semantic Scholar concurrently for '{search_term}'...")
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_arxiv = executor.submit(search_arxiv, search_term, fetch_limit)
        future_scholar = executor.submit(search_semantic_scholar, search_term, fetch_limit)
        
        try:
            arxiv_results = future_arxiv.result(timeout=6.0)
        except Exception as e:
            print(f"[Academic Search] arXiv fetch skipped or timed out: {e}")
            arxiv_results = []

        try:
            scholar_results = future_scholar.result(timeout=6.0)
        except Exception as e:
            print(f"[Academic Search] Semantic Scholar fetch skipped or timed out: {e}")
            scholar_results = []
    
    combined_results = arxiv_results + scholar_results
    final_papers = rank_and_deduplicate_papers(combined_results, target_limit=limit, query=search_term)
    
    # Fallback to Crossref if we have fewer unique papers than requested limit
    if len(final_papers) < limit:
        needed = limit - len(final_papers)
        print(f"[*] Academic Search: Only found {len(final_papers)} papers from arXiv/Semantic Scholar. Querying Crossref as fallback for {needed} more papers.")
        try:
            crossref_results = search_crossref(search_term, limit=needed + 5)
        except Exception as e:
            print(f"[Academic Search] Crossref fallback failed: {e}")
            crossref_results = []
        
        # Combine all and re-rank/dedup
        all_results = combined_results + crossref_results
        final_papers = rank_and_deduplicate_papers(all_results, target_limit=limit, query=search_term)
    else:
        print(f"[*] Academic Search: Retrieved {len(final_papers)} high-quality papers from arXiv/Semantic Scholar. Skipping Crossref fallback.")
        
    total_latency = time.perf_counter() - start_time
    print(f"[*] Academic Search: Consolidated, ranked, and deduped to {len(final_papers)} papers. Total Latency: {total_latency:.2f}s.")
    logger.info(f"Consolidated academic search: {len(final_papers)} papers, total latency: {total_latency:.2f}s")
    
    return final_papers

def format_academic_context(papers: list) -> str:
    """
    Formats a list of academic papers into a structured markdown context block for LLM prompt ingestion.
    """
    if not papers:
        return "No peer-reviewed academic literature found."
        
    formatted = "### RETRIEVED PEER-REVIEWED ACADEMIC LITERATURE & GROUND TRUTH ###\n\n"
    for idx, p in enumerate(papers):
        authors_str = ", ".join(p["authors"][:3])
        if len(p["authors"]) > 3:
            authors_str += " et al."
            
        formatted += f"[{idx + 1}] Title: {p['title']}\n"
        formatted += f"    Authors: {authors_str}\n"
        formatted += f"    Published: {p['year']} | Citations: {p['citations']} | Journal/Venue: {p['venue'] or 'N/A'}\n"
        formatted += f"    Source URL: {p['url']}\n"
        formatted += f"    Abstract: {p['abstract']}\n\n"
        
    formatted += "--- Please use the above academic abstracts, citation metrics, and peer-reviewed reference details as your absolute source of truth. Integrate these technical details directly into your generated report. ---\n"
    return formatted

if __name__ == "__main__":
    print("=== Testing Academic Search Tool ===")
    test_query = "Quantum Machine Learning Algorithms"
    results = search_academic_literature(test_query)
    for p in results:
        print(f"\n- Title: {p['title']}")
        print(f"  Authors: {p['authors']}")
        print(f"  Year: {p['year']} | Citations: {p['citations']} | Venue: {p['venue']}")
        print(f"  URL: {p['url']}")
        print(f"  Score: {p['ranking_score']:.2f}")
