"""
arXiv fetcher — 只抓 CCF-A 及以上顶会/顶刊论文。
策略：在搜索词中加入顶会名称，并对结果按 journal_ref/comment 做二次过滤。
"""
import requests
import feedparser
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import CCF_A_ARXIV_TERMS

ARXIV_API = "http://export.arxiv.org/api/query"
CS_CATEGORIES = ["cs.LG", "cs.CV", "cs.AI", "cs.NE", "stat.ML", "cs.CL"]

def fetch(keywords: list, max_results: int = 20) -> list:
    papers = []
    seen = set()

    # 构造顶会过滤词：搜索摘要/标题中提到顶会的论文
    venue_query = " OR ".join(f'co:"{v}"' for v in CCF_A_ARXIV_TERMS)
    kw_query    = " OR ".join(f'ti:"{kw}" OR abs:"{kw}"' for kw in keywords[:6])
    cat_query   = " OR ".join(f"cat:{c}" for c in CS_CATEGORIES)
    query = f"({kw_query}) AND ({cat_query}) AND ({venue_query})"

    params = {
        "search_query": query,
        "start": 0,
        "max_results": max_results * 2,   # 多抓一些，过滤后可能减少
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }

    try:
        resp = requests.get(ARXIV_API, params=params, timeout=15)
        resp.raise_for_status()
        feed = feedparser.parse(resp.text)
    except Exception as e:
        print(f"[arXiv] fetch error: {e}")
        return []

    for entry in feed.entries:
        arxiv_id = entry.id.split("/abs/")[-1].split("v")[0]
        if arxiv_id in seen:
            continue

        # 二次过滤：journal_ref 或 comment 中包含顶会名
        journal_ref = entry.get("arxiv_journal_ref", "") or ""
        comment     = entry.get("arxiv_comment", "") or ""
        venue_text  = (journal_ref + " " + comment).upper()
        if not _is_top_venue(venue_text):
            continue

        seen.add(arxiv_id)

        pdf_url = next(
            (l.href for l in entry.get("links", []) if l.get("type") == "application/pdf"),
            f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        )
        matched = [kw for kw in keywords
                   if kw.lower() in entry.title.lower()
                   or kw.lower() in entry.get("summary", "").lower()]

        # 从 journal_ref/comment 提取会议标签
        venue_tag = _extract_venue_tag(journal_ref + " " + comment)

        papers.append({
            "paper_id": f"arxiv:{arxiv_id}",
            "title":    entry.title.replace("\n", " ").strip(),
            "authors":  ", ".join(a.name for a in entry.get("authors", [])),
            "abstract": entry.get("summary", "").replace("\n", " ").strip(),
            "url":      f"https://arxiv.org/abs/{arxiv_id}",
            "pdf_url":  pdf_url,
            "source":   "arxiv",
            "published": entry.get("published", ""),
            "keywords": ", ".join(matched) + (f", {venue_tag}" if venue_tag else ""),
        })

        if len(papers) >= max_results:
            break

    return papers

def _is_top_venue(text: str) -> bool:
    text = text.upper()
    return any(v.upper() in text for v in CCF_A_ARXIV_TERMS)

def _extract_venue_tag(text: str) -> str:
    text_upper = text.upper()
    for v in CCF_A_ARXIV_TERMS:
        if v.upper() in text_upper:
            return v
    return ""
