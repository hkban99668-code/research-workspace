"""
论文翻译模块。
使用 Microsoft Edge 免费翻译 token（无需 API Key，支持长文本，国内可用）。
翻译结果缓存到数据库。
"""
import time
import requests
from database import get_paper, update_paper

_EDGE_AUTH_URL  = "https://edge.microsoft.com/translate/auth"
_MS_TRANSLATE   = "https://api.cognitive.microsofttranslator.com/translate"

# 简单内存缓存 token（有效期约 10 分钟）
_token_cache = {"token": "", "expires": 0}


def _get_token() -> str:
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires"]:
        return _token_cache["token"]
    resp = requests.get(_EDGE_AUTH_URL, timeout=10)
    resp.raise_for_status()
    _token_cache["token"]   = resp.text.strip()
    _token_cache["expires"] = now + 540  # 9 分钟后过期（留 1 分钟余量）
    return _token_cache["token"]


def _ms_translate(text: str) -> str:
    if not text.strip():
        return text
    token = _get_token()
    resp = requests.post(
        _MS_TRANSLATE,
        params={"api-version": "3.0", "to": "zh-Hans"},
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json=[{"text": text}],
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()[0]["translations"][0]["text"]


def translate_paper(paper_db_id: int, force: bool = False) -> dict:
    paper = get_paper(paper_db_id)
    if not paper:
        return {"ok": False, "msg": "论文不存在"}

    if not force and paper.get("title_zh") and paper.get("abstract_zh"):
        return {
            "ok": True,
            "title_zh":    paper["title_zh"],
            "abstract_zh": paper["abstract_zh"],
            "cached": True,
        }

    title    = paper.get("title", "")
    abstract = paper.get("abstract", "")

    try:
        title_zh    = _ms_translate(title)
        abstract_zh = _ms_translate(abstract)
    except Exception as e:
        return {"ok": False, "msg": f"翻译失败: {e}"}

    update_paper(paper_db_id, title_zh=title_zh, abstract_zh=abstract_zh)
    return {"ok": True, "title_zh": title_zh, "abstract_zh": abstract_zh, "cached": False}
