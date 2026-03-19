"""
论文翻译模块。
优先使用 Claude API，无 Key 时使用 Google Translate 非官方接口（无需认证，速度快）。
翻译结果缓存到数据库。
"""
import requests
import config
from database import get_paper, update_paper

ANTHROPIC_API  = "https://api.anthropic.com/v1/messages"
GOOGLE_TL_API  = "https://translate.googleapis.com/translate_a/single"


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

    api_key = config.get("anthropic_api_key", "")
    if api_key:
        result = _translate_with_claude(title, abstract, api_key)
    else:
        result = _translate_with_google(title, abstract)

    if result["ok"]:
        update_paper(paper_db_id,
                     title_zh=result["title_zh"],
                     abstract_zh=result["abstract_zh"])
    return result


# ── Google Translate（非官方，无需 Key）─────────────────────
def _google_translate(text: str) -> str:
    """单次翻译，Google 接口无硬性字符限制。"""
    if not text.strip():
        return text
    try:
        resp = requests.get(
            GOOGLE_TL_API,
            params={
                "client": "gtx",
                "sl": "en",
                "tl": "zh-CN",
                "dt": "t",
                "q": text,
            },
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        resp.raise_for_status()
        data = resp.json()
        # 返回结构: [[[译文片段, 原文片段], ...], ...]
        translated = "".join(seg[0] for seg in data[0] if seg[0])
        return translated
    except Exception as e:
        print(f"[Google Translate] error: {e}")
        return text


def _translate_with_google(title: str, abstract: str) -> dict:
    title_zh    = _google_translate(title)
    abstract_zh = _google_translate(abstract)
    return {
        "ok": True,
        "title_zh":    title_zh,
        "abstract_zh": abstract_zh,
        "cached": False,
    }


# ── Claude 翻译（有 API Key 时使用）────────────────────────
def _translate_with_claude(title: str, abstract: str, api_key: str) -> dict:
    prompt = f"""将以下学术论文的标题和摘要翻译成中文。
专业术语保留英文并用括号标注，语言流畅自然。

标题：{title}

摘要：{abstract}

输出格式（严格按此）：
===TITLE===
中文标题
===ABSTRACT===
中文摘要"""

    try:
        resp = requests.post(
            ANTHROPIC_API,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        resp.raise_for_status()
        raw = resp.json()["content"][0]["text"]

        def extract(tag):
            s = raw.find(f"==={tag}===")
            if s == -1:
                return ""
            s += len(f"==={tag}===")
            e = raw.find("===", s)
            return raw[s:e].strip() if e != -1 else raw[s:].strip()

        return {
            "ok": True,
            "title_zh":    extract("TITLE") or title,
            "abstract_zh": extract("ABSTRACT") or abstract,
            "cached": False,
        }
    except Exception as e:
        print(f"[Claude Translate] failed, fallback to Google: {e}")
        return _translate_with_google(title, abstract)
