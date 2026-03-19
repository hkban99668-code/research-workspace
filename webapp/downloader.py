import os
import re
import requests
from database import get_paper, update_paper
import config

# arXiv 国内可用镜像，按速度优先级排列
ARXIV_MIRRORS = [
    "https://arxiv.org",
    "https://ar5iv.labs.arxiv.org",   # HTML 版，仅备用
    "https://export.arxiv.org",
]

def sanitize_filename(name: str) -> str:
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    return name[:120].strip()

def _get_candidate_urls(pdf_url: str) -> list:
    """
    生成备用下载地址列表。
    arXiv PDF 格式：https://arxiv.org/pdf/XXXX.XXXXX.pdf
    替换域名即可走镜像。
    """
    candidates = [pdf_url]

    if "arxiv.org/pdf/" in pdf_url:
        arxiv_id = pdf_url.split("/pdf/")[-1].replace(".pdf", "").split("v")[0]
        for mirror in ARXIV_MIRRORS:
            url = f"{mirror}/pdf/{arxiv_id}.pdf"
            if url not in candidates:
                candidates.append(url)

    return candidates

def download_pdf(paper_db_id: int) -> dict:
    paper = get_paper(paper_db_id)
    if not paper:
        return {"ok": False, "msg": "论文不存在"}

    if paper.get("is_downloaded") and paper.get("local_path") and os.path.exists(paper["local_path"]):
        return {"ok": True, "msg": "Already downloaded", "path": paper["local_path"]}

    pdf_url = paper.get("pdf_url")
    if not pdf_url:
        return {"ok": False, "msg": "该论文没有可用的 PDF 链接"}

    save_dir = config.get("papers_dir", r"D:\research\papers\downloaded")
    os.makedirs(save_dir, exist_ok=True)

    filename  = sanitize_filename(paper["title"]) + ".pdf"
    save_path = os.path.join(save_dir, filename)

    candidates = _get_candidate_urls(pdf_url)
    last_err   = ""

    for url in candidates:
        try:
            resp = requests.get(
                url,
                timeout=20,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; ResearchAssistant/1.0)",
                },
                stream=True,
            )
            resp.raise_for_status()

            # 确认是 PDF 而不是 HTML 错误页
            content_type = resp.headers.get("content-type", "")
            if "html" in content_type:
                last_err = f"{url} 返回了 HTML，跳过"
                continue

            with open(save_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):  # 64KB 块，更快
                    if chunk:
                        f.write(chunk)

            update_paper(paper_db_id, is_downloaded=1, local_path=save_path)
            return {"ok": True, "msg": "Downloaded", "path": save_path}

        except Exception as e:
            last_err = str(e)
            continue  # 尝试下一个镜像

    return {"ok": False, "msg": f"所有下载源均失败：{last_err}"}
