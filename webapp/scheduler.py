"""
定时任务：每天定时从三个数据源抓取论文。
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import config
import database
from fetchers import arxiv_fetcher, semantic_scholar, pwc_fetcher

_scheduler = BackgroundScheduler(timezone="Asia/Shanghai")

def run_fetch():
    """手动或定时触发的抓取任务"""
    cfg = config.load_config()
    keywords = cfg.get("keywords", [])
    max_per = cfg.get("max_papers_per_source", 20)
    sources = cfg.get("sources", {})

    results = {"arxiv": 0, "semantic_scholar": 0, "pwc": 0}

    if sources.get("arxiv", True):
        try:
            papers = arxiv_fetcher.fetch(keywords, max_per)
            for p in papers:
                database.upsert_paper(p)
            results["arxiv"] = len(papers)
            database.log_fetch("arxiv", len(papers), "ok")
        except Exception as e:
            database.log_fetch("arxiv", 0, f"error: {e}")

    if sources.get("semantic_scholar", True):
        try:
            papers = semantic_scholar.fetch(keywords, max_per)
            for p in papers:
                database.upsert_paper(p)
            results["semantic_scholar"] = len(papers)
            database.log_fetch("semantic_scholar", len(papers), "ok")
        except Exception as e:
            database.log_fetch("semantic_scholar", 0, f"error: {e}")

    if sources.get("papers_with_code", True):
        try:
            papers = pwc_fetcher.fetch(keywords, max_per)
            for p in papers:
                database.upsert_paper(p)
            results["pwc"] = len(papers)
            database.log_fetch("pwc", len(papers), "ok")
        except Exception as e:
            database.log_fetch("pwc", 0, f"error: {e}")

    total = sum(results.values())
    print(f"[Scheduler] Fetched {total} papers: {results}")
    return results

def start(hour: int = None):
    cfg = config.load_config()
    h = hour if hour is not None else cfg.get("schedule_hour", 8)
    _scheduler.add_job(run_fetch, CronTrigger(hour=h, minute=0), id="daily_fetch", replace_existing=True)
    if not _scheduler.running:
        _scheduler.start()
    print(f"[Scheduler] Started — daily fetch at {h:02d}:00 (Asia/Shanghai)")

def stop():
    if _scheduler.running:
        _scheduler.shutdown()
