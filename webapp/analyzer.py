"""
Paper analyzer — calls Anthropic API directly via requests (no SDK dependency).
"""
import requests
import config
from database import get_paper, save_analysis, get_analysis

ANTHROPIC_API = "https://api.anthropic.com/v1/messages"

SYSTEM_PROMPT = """你是一位深度学习/机器学习领域的资深研究员。
阅读论文信息后，请用中文进行分析，但保留专业术语的英文原文。
回答要简洁专业，突出对研究者最有价值的信息。"""

def analyze_paper(paper_db_id: int, force: bool = False) -> dict:
    existing = get_analysis(paper_db_id)
    if existing and not force:
        return {"ok": True, "data": existing, "cached": True}

    paper = get_paper(paper_db_id)
    if not paper:
        return {"ok": False, "msg": "Paper not found"}

    api_key = config.get("anthropic_api_key", "")
    if not api_key:
        return {"ok": False, "msg": "未配置 Anthropic API Key，请在设置中填入"}

    prompt = f"""请分析以下论文：

**标题：** {paper['title']}
**作者：** {paper.get('authors', 'N/A')}
**发布时间：** {paper.get('published', 'N/A')}
**摘要：**
{paper.get('abstract', '无摘要')}

请严格按以下格式输出，每节用 === 标记分隔：

===SUMMARY===
用3-4句话概括这篇论文要解决的问题、采用的方法和主要结论。语言简明，适合快速了解论文价值。

===KEY_STEPS===
列出论文方法的核心步骤或流程（3-6步），格式：
① 步骤名称：具体说明
② 步骤名称：具体说明
……

===INNOVATION===
列出本文相比已有工作的创新点（2-4条），格式：
🔬 创新点名称：详细说明（与已有方法的具体区别）
……

===IDEAS===
基于这篇论文，提出3个有研究价值的延伸方向或新 idea，格式：
💡 Idea名称：具体说明（为什么有价值，如何实现）
……
"""

    try:
        resp = requests.post(
            ANTHROPIC_API,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 2000,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60,
        )
        resp.raise_for_status()
        raw = resp.json()["content"][0]["text"]
    except requests.HTTPError as e:
        msg = e.response.json().get("error", {}).get("message", str(e)) if e.response else str(e)
        return {"ok": False, "msg": f"API 错误: {msg}"}
    except Exception as e:
        return {"ok": False, "msg": f"请求失败: {e}"}

    summary, key_steps, innovation, ideas = _parse_response(raw)
    save_analysis(paper_db_id, summary, "", key_steps, innovation, ideas)

    return {
        "ok": True,
        "data": {
            "summary": summary,
            "key_steps": key_steps,
            "innovation": innovation,
            "ideas": ideas,
        },
        "cached": False,
    }

def _parse_response(text: str) -> tuple:
    def extract(tag: str) -> str:
        start = text.find(f"==={tag}===")
        if start == -1:
            return ""
        start += len(f"==={tag}===")
        end = text.find("===", start)
        return text[start:end].strip() if end != -1 else text[start:].strip()

    return (
        extract("SUMMARY"),
        extract("KEY_STEPS"),
        extract("INNOVATION"),
        extract("IDEAS"),
    )
