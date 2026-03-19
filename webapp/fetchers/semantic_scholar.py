"""
Semantic Scholar fetcher — 只返回 CCF-A 及以上顶会/顶刊论文。
使用 venue 字段过滤，是三个数据源中最精准的。
"""
import requests
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import CCF_A_S2_VENUES

S2_SEARCH = "https://api.semanticscholar.org/graph/v1/paper/search"
FIELDS = "paperId,title,authors,abstract,year,publicationDate,openAccessPdf,url,venue,publicationVenue"

def fetch(keywords: list, max_results: int = 20) -> list:
    papers = []
    seen = set()

    for kw in keywords:
        try:
            resp = requests.get(
                S2_SEARCH,
                params={
                    "query": kw,
                    "fields": FIELDS,
                    "limit": 50,                    # 多拉，过滤后取够为止
                    "publicationDateOrYear": _last_365_days(),  # 顶会论文发表周期较长，扩大范围
                },
                timeout=15,
                headers={"User-Agent": "ResearchAssistant/1.0"}
            )
            resp.raise_for_status()
            data = resp.json().get("data", [])
        except Exception as e:
            print(f"[S2] error for '{kw}': {e}")
            continue

        for p in data:
            pid = p.get("paperId", "")
            if not pid or pid in seen:
                continue

            # 过滤：venue 必须是 CCF-A 顶会/刊
            venue = _get_venue(p)
            if not _is_ccf_a(venue):
                continue

            seen.add(pid)

            pdf_url = ""
            if p.get("openAccessPdf"):
                pdf_url = p["openAccessPdf"].get("url", "")

            matched = [k for k in keywords
                       if k.lower() in (p.get("title") or "").lower()
                       or k.lower() in (p.get("abstract") or "").lower()]

            papers.append({
                "paper_id": f"s2:{pid}",
                "title":    (p.get("title") or "").strip(),
                "authors":  ", ".join(a.get("name", "") for a in p.get("authors", [])),
                "abstract": (p.get("abstract") or "").strip(),
                "url":      p.get("url") or f"https://www.semanticscholar.org/paper/{pid}",
                "pdf_url":  pdf_url,
                "source":   "semantic_scholar",
                "published": p.get("publicationDate") or str(p.get("year", "")),
                "keywords": ", ".join(matched) + (f", {venue}" if venue else ""),
            })

        if len(papers) >= max_results:
            break

    return papers[:max_results]

def _get_venue(p: dict) -> str:
    """优先从 publicationVenue 取名称，退回到 venue 字段。"""
    pv = p.get("publicationVenue")
    if pv:
        return pv.get("name") or pv.get("alternateNames", [""])[0] or ""
    return p.get("venue") or ""

def _is_ccf_a(venue: str) -> bool:
    if not venue:
        return False
    venue_upper = venue.upper()
    return any(v.upper() in venue_upper for v in CCF_A_S2_VENUES)

def _last_365_days() -> str:
    end   = datetime.now()
    start = end - timedelta(days=365)
    return f"{start.strftime('%Y-%m-%d')}:{end.strftime('%Y-%m-%d')}"
