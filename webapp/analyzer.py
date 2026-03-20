"""
Normal analysis mode — uses cheaper/faster model (e.g. Qwen) for quick paper reading.
Prompt and output format follow the "一般讨论" mode spec.
"""
import os
import re
from datetime import datetime
import config
import llm_client
from database import get_paper, save_analysis, get_analysis, create_session, add_session_message, update_session

NOTES_DIR = r"D:\research\papers\notes"

SYSTEM_PROMPT = """# 系统提示词 - 一般讨论模式

## 角色
你是一位专业的机器学习/深度学习科研助手，擅长高效解答日常科研问题。

## 专业领域
- 深度学习：CNN、Transformer、Diffusion Model、GAN、VAE、Flow
- 机器学习：监督学习、无监督学习、强化学习、优化理论
- 框架工具：PyTorch、TensorFlow、JAX、HuggingFace、Lightning
- 论文来源：ArXiv、NeurIPS、ICML、ICLR、CVPR、ECCV、ACL、EMNLP

## 工作原则
1. **高效优先**：快速给出准确答案，避免冗余
2. **代码实用**：提供可直接运行的代码，含维度注释
3. **公式清晰**：使用 LaTeX 格式，步骤简洁
4. **中文为主**：除专业术语外使用中文回答

## 能力范围
你擅长处理：论文快速阅读与摘要提取、PyTorch 代码实现与调试、常规数学推导、\
模型架构解释与对比、实验设计建议、Bug 排查、概念解释、文献检索建议。

⚠️ 复杂任务（超长论文深度分析、复杂数学证明、多论文交叉对比、论文核心章节写作）建议切换到「高级探索」模式。"""

ANALYSIS_PROMPT = """请对以下论文进行快速阅读分析：

**标题：** {title}
**作者：** {authors}
**发布时间：** {published}
**摘要：**
{abstract}

请严格按以下格式输出，每节用 === 标记分隔：

===SUMMARY===
一句话总结核心贡献，然后用3-4句话说明：解决什么问题、怎么解决的、主要结论。

===KEY_STEPS===
论文方法的核心步骤（3-6步）：
① 步骤名称：具体说明
② 步骤名称：具体说明
……

===INNOVATION===
相比已有工作的创新点（2-4条）：
🔬 创新点名称：详细说明（与已有方法的具体区别）
……

===IDEAS===
有研究价值的延伸方向（3条）：
💡 方向名称：具体说明（为什么有价值，如何实现）
……
"""


def _ensure_notes_dir(subdir: str) -> str:
    path = os.path.join(NOTES_DIR, subdir)
    os.makedirs(path, exist_ok=True)
    return path


def _safe_filename(title: str) -> str:
    return re.sub(r'[^\w\s-]', '', title[:50]).strip().replace(' ', '_')


def _save_normal_note(paper: dict, analysis: dict, session_id: int, model: str):
    notes_dir = _ensure_notes_dir("normal")
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"{_safe_filename(paper['title'])}_{date_str}.md"
    file_path = os.path.join(notes_dir, filename)

    lines = [
        f"# 普通分析 - {paper['title']}",
        "",
        f"**日期**: {date_str}",
        f"**模型**: {model}",
        f"**来源**: {paper.get('url', 'N/A')}",
        "",
        "---",
        "",
        "## 一句话总结 / 核心摘要",
        "",
        analysis.get("summary", ""),
        "",
        "## 关键步骤",
        "",
        analysis.get("key_steps", ""),
        "",
        "## 创新点",
        "",
        analysis.get("innovation", ""),
        "",
        "## 延伸 Ideas",
        "",
        analysis.get("ideas", ""),
        "",
        "---",
        "",
        f"*自动记录于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
    ]
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    update_session(session_id, file_path=file_path)
    return file_path


def analyze_paper(paper_db_id: int, force: bool = False) -> dict:
    existing = get_analysis(paper_db_id)
    if existing and not force:
        return {"ok": True, "data": existing, "cached": True}

    paper = get_paper(paper_db_id)
    if not paper:
        return {"ok": False, "msg": "Paper not found"}

    model   = config.get("normal_model", "qwen3.5-plus")
    api_key = config.get("normal_api_key", "")
    if not api_key:
        return {"ok": False, "msg": "未配置普通分析 API Key，请在设置中填入"}

    temperature = config.get("normal_temperature", 0.7)
    max_tokens  = config.get("normal_max_tokens", 4096)

    prompt = ANALYSIS_PROMPT.format(
        title=paper['title'],
        authors=paper.get('authors', 'N/A'),
        published=paper.get('published', 'N/A'),
        abstract=paper.get('abstract', '无摘要'),
    )

    session_id = create_session(paper_db_id, "normal", model)
    add_session_message(session_id, "user", prompt)

    try:
        raw = llm_client.call_llm(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            system=SYSTEM_PROMPT,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as e:
        update_session(session_id, ended_at=datetime.now().isoformat())
        return {"ok": False, "msg": f"调用失败: {e}"}

    add_session_message(session_id, "assistant", raw)
    update_session(session_id, ended_at=datetime.now().isoformat())

    summary, key_steps, innovation, ideas = _parse_response(raw)
    save_analysis(paper_db_id, summary, "", key_steps, innovation, ideas, analysis_type="normal")

    result = {
        "summary": summary,
        "key_steps": key_steps,
        "innovation": innovation,
        "ideas": ideas,
        "analysis_type": "normal",
    }
    _save_normal_note(paper, result, session_id, model)
    return {"ok": True, "data": result, "cached": False}


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
