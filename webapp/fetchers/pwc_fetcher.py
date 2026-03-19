"""
Hugging Face Daily Papers fetcher（替代原 Papers With Code）。
HF Daily Papers 每日精选高质量论文，主要来源于 arXiv，与顶会高度重合。
再结合关键词过滤，确保相关性。
"""
import requests
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

HF_PAPERS_API = "https://huggingface.co/api/daily_papers"

def fetch(keywords: list, max_results: int = 20) -> list:
    papers = []
    seen = set()
    kw_set = set(kw.lower() for kw in keywords)

    # 抓最近 7 天的 HF 每日精选
    for days_ago in range(7):
        if len(papers) >= max_results:
            break
        date_str = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        try:
            resp = requests.get(
                HF_PAPERS_API,
                params={"date": date_str},
                timeout=15,
                headers={"User-Agent": "ResearchAssistant/1.0"},
            )
            if resp.status_code == 404:
                continue
            resp.raise_for_status()
            items = resp.json()
            if isinstance(items, dict):
                items = items.get("papers", [])
        except Exception as e:
            print(f"[HF] {date_str} error: {e}")
            continue

        for item in items:
            # HF API 结构: {paper: {...}, publishedAt, title, summary, ...}
            paper    = item.get("paper", {})
            pid      = paper.get("id", "")          # arXiv ID，如 "2603.14935"
            title    = (item.get("title") or paper.get("title") or "").strip()
            abstract = (item.get("summary") or paper.get("summary") or "").strip()

            if not pid or not title or pid in seen:
                continue

            # 关键词过滤
            text = (title + " " + abstract).lower()
            matched = [kw for kw in keywords if kw.lower() in text]
            if not matched:
                continue

            seen.add(pid)

            pdf_url = f"https://arxiv.org/pdf/{pid}.pdf"
            url     = f"https://arxiv.org/abs/{pid}"

            papers.append({
                "paper_id": f"hf:{pid}",
                "title":    title,
                "authors":  ", ".join(
                    a.get("name", "") for a in (paper.get("authors") or [])
                ),
                "abstract": abstract,
                "url":      url,
                "pdf_url":  pdf_url,
                "source":   "pwc",
                "published": (item.get("publishedAt") or paper.get("publishedAt") or date_str)[:10],
                "keywords": ", ".join(matched),
            })

    return papers[:max_results]
