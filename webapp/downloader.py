import os
import re
import time
import requests
from database import get_paper, update_paper
import config

ARXIV_MIRRORS = [
    "https://arxiv.org",
    "https://export.arxiv.org",
]

S2_API = "https://api.semanticscholar.org/graph/v1/paper"


def sanitize_filename(name: str) -> str:
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    return name[:120].strip()


def _get_candidate_urls(pdf_url: str) -> list:
    candidates = [pdf_url]
    if "arxiv.org/pdf/" in pdf_url:
        arxiv_id = pdf_url.split("/pdf/")[-1].replace(".pdf", "").split("v")[0]
        for mirror in ARXIV_MIRRORS:
            url = f"{mirror}/pdf/{arxiv_id}.pdf"
            if url not in candidates:
                candidates.append(url)
    return candidates


def _find_pdf_url_for_s2(paper: dict) -> str:
    """
    Try to find a PDF URL for a Semantic Scholar paper that has no pdf_url.
    1. Query S2 API for openAccessPdf / externalIds.ArXiv
    2. Rate-limit friendly: single request with 1s sleep
    """
    url = paper.get("url", "")
    if "/paper/" not in url:
        return ""

    s2_hash = url.split("/paper/")[-1].split("/")[0]
    try:
        time.sleep(1)  # S2 rate limit
        resp = requests.get(
            f"{S2_API}/{s2_hash}",
            params={"fields": "openAccessPdf,externalIds"},
            timeout=10,
            headers={"User-Agent": "ResearchAssistant/1.0"},
        )
        if not resp.ok:
            return ""
        data = resp.json()

        # Priority 1: S2 open-access PDF
        oap = data.get("openAccessPdf")
        if oap and oap.get("url"):
            return oap["url"]

        # Priority 2: arXiv ID → construct PDF URL
        ext = data.get("externalIds") or {}
        arxiv_id = ext.get("ArXiv")
        if arxiv_id:
            return f"https://arxiv.org/pdf/{arxiv_id}.pdf"

    except Exception as e:
        print(f"[Downloader] S2 API lookup failed: {e}")

    return ""


def _stream_download(url: str, save_path: str) -> bool:
    """Download URL to save_path. Returns True on success."""
    resp = requests.get(
        url,
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0 (compatible; ResearchAssistant/1.0)"},
        stream=True,
    )
    resp.raise_for_status()
    content_type = resp.headers.get("content-type", "")
    if "html" in content_type:
        return False
    with open(save_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=65536):
            if chunk:
                f.write(chunk)
    return True


def download_pdf(paper_db_id: int) -> dict:
    paper = get_paper(paper_db_id)
    if not paper:
        return {"ok": False, "msg": "论文不存在"}

    if paper.get("is_downloaded") and paper.get("local_path") and os.path.exists(paper["local_path"]):
        return {"ok": True, "msg": "Already downloaded", "path": paper["local_path"]}

    save_dir = config.get("papers_dir", r"D:\research\papers\downloaded")
    os.makedirs(save_dir, exist_ok=True)
    filename  = sanitize_filename(paper["title"]) + ".pdf"
    save_path = os.path.join(save_dir, filename)

    pdf_url = paper.get("pdf_url") or ""

    # S2 论文没有 pdf_url 时，动态查询
    if not pdf_url and paper.get("source") == "semantic_scholar":
        pdf_url = _find_pdf_url_for_s2(paper)
        if pdf_url:
            # 缓存到数据库，下次无需再查
            update_paper(paper_db_id, pdf_url=pdf_url)

    if not pdf_url:
        return {"ok": False, "msg": "未找到可用的 PDF 链接（该论文可能未开放获取）"}

    candidates = _get_candidate_urls(pdf_url)
    last_err   = ""

    for url in candidates:
        try:
            ok = _stream_download(url, save_path)
            if ok:
                update_paper(paper_db_id, is_downloaded=1, local_path=save_path)
                return {"ok": True, "msg": "Downloaded", "path": save_path}
            last_err = f"{url} 返回了 HTML，跳过"
        except Exception as e:
            last_err = str(e)
            continue

    return {"ok": False, "msg": f"下载失败：{last_err}"}
