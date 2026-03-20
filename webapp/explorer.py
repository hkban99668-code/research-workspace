"""
Advanced exploration mode — multi-turn chat with a powerful model (e.g. Claude Sonnet/Opus).
Prompt and output style follow the "高级探索" mode spec.
"""
import os
import re
from datetime import datetime
import config
import llm_client
import database

NOTES_DIR = r"D:\research\papers\notes"

SYSTEM_PROMPT = """# 系统提示词 - 高级探索模式

## 角色
你是一位资深的机器学习/深度学习研究专家，具备深厚的理论功底和丰富的科研经验，\
能够进行深度分析、严谨推导和关键决策支持。

## 专业领域
- 深度学习理论与前沿：Transformer 架构演进、Diffusion 理论、Scaling Laws、Emergence
- 优化理论：凸优化、非凸优化、收敛性分析、泛化理论
- 机器学习理论：PAC 学习、VC 维、Rademacher 复杂度、信息论
- 框架精通：PyTorch 底层机制、自动微分原理、分布式训练
- 顶会论文：NeurIPS、ICML、ICLR、CVPR 等顶会的深度解读

## 工作原则
1. **深度优先**：提供深入、全面、严谨的分析
2. **准确至上**：确保数学推导和代码逻辑的正确性
3. **批判思维**：客观评价方法的优缺点和适用范围
4. **启发引导**：不仅给答案，还要启发思考

## 能力范围
你专门处理：
- **深度论文分析**：全文精读、创新点深挖、方法论评价
- **复杂数学推导**：收敛性证明、最优性分析、泛化界推导
- **多论文综合分析**：技术路线对比、发展脉络梳理
- **架构设计决策**：权衡分析、方案选择建议
- **关键代码审查**：核心算法正确性验证
- **论文写作指导**：Introduction、Method、Experiment 的写作策略
- **审稿意见回复**：回复策略制定、实验补充建议
- **研究方向建议**：前沿趋势分析、选题建议

## 交互风格
- 语气专业、严谨、有深度
- 分析全面系统，主动提供批判性视角
- 鼓励深入思考，适时给出延伸阅读建议"""

INITIAL_PROMPT = """请对以下论文进行深度分析：

**标题：** {title}
**作者：** {authors}
**发布时间：** {published}
**摘要：**
{abstract}

请按以下结构进行深度分析：

## 元信息
- **作者/机构**：
- **发表venue**：
- **核心贡献**：（一句话）

## 研究动机
（详细分析问题背景、现有方法的不足、本文的切入点）

## 方法论深度解析

### 核心思想
（用直觉解释方法的本质）

### 技术细节
（逐步拆解，重要公式请用 LaTeX 格式）

### 与现有方法的联系
（和哪些工作相关，有何超越）

## 实验分析
（实验设计的亮点和不足，结果的解读）

## 批判性评价

### 优点
### 局限性
### 潜在改进方向

## 对研究的启发
（具体的后续研究建议）"""

DIGEST_PROMPT = """以下是关于一篇论文的高级探索对话记录，请生成简洁的会话提要：

1. 探索的主要话题（2-3句）
2. 关键发现和洞见（3-5条，用 • 列出）
3. 确定的研究方向（1-3条，用 → 标注）

对话记录：
{conversation}

用中文撰写，专业术语保留英文。"""


def _ensure_notes_dir(subdir: str) -> str:
    path = os.path.join(NOTES_DIR, subdir)
    os.makedirs(path, exist_ok=True)
    return path


def _safe_filename(title: str) -> str:
    return re.sub(r'[^\w\s-]', '', title[:50]).strip().replace(' ', '_')


def _save_exploration_file(session_id: int, digest: str = "") -> str:
    session = database.get_session(session_id)
    if not session:
        return ""
    paper    = database.get_paper(session["paper_id"])
    messages = database.get_session_messages(session_id)

    notes_dir = _ensure_notes_dir("advanced")
    date_str  = session["created_at"][:10]
    filename  = f"{_safe_filename(paper['title'])}_{date_str}_s{session_id}.md"
    file_path = os.path.join(notes_dir, filename)

    ended = bool(session.get("ended_at"))
    lines = [
        f"# 高级探索 - {paper['title']}",
        "",
        f"**日期**: {date_str}",
        f"**模型**: {session['model']}",
        f"**状态**: {'已完成' if ended else '进行中'}",
        f"**来源**: {paper.get('url', 'N/A')}",
        "",
        "---",
        "",
        "## 对话记录",
        "",
    ]
    for m in messages:
        label = "**[用户]**" if m["role"] == "user" else "**[AI 探索]**"
        lines += [label, "", m["content"], "", "---", ""]

    if digest:
        lines += ["## 会话提要", "", digest, "", "---", ""]

    lines.append(f"*自动记录于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return file_path


def _get_keys():
    model   = config.get("advanced_model", "claude-sonnet-4-6")
    api_key = config.get("advanced_api_key", "")
    return model, api_key


def start_exploration(paper_id: int) -> dict:
    paper = database.get_paper(paper_id)
    if not paper:
        return {"ok": False, "msg": "Paper not found"}

    model, api_key = _get_keys()
    if not api_key:
        return {"ok": False, "msg": "未配置高级探索 API Key，请在设置中填入"}

    temperature = config.get("advanced_temperature", 0.5)
    max_tokens  = config.get("advanced_max_tokens", 8192)

    session_id = database.create_session(paper_id, "advanced", model)

    user_content = INITIAL_PROMPT.format(
        title=paper["title"],
        authors=paper.get("authors", "N/A"),
        published=paper.get("published", "N/A"),
        abstract=paper.get("abstract", "无摘要"),
    )
    database.add_session_message(session_id, "user", user_content)

    try:
        ai_content = llm_client.call_llm(
            model=model,
            messages=[{"role": "user", "content": user_content}],
            system=SYSTEM_PROMPT,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as e:
        database.update_session(session_id, ended_at=datetime.now().isoformat())
        return {"ok": False, "msg": f"调用失败: {e}"}

    database.add_session_message(session_id, "assistant", ai_content)
    _save_exploration_file(session_id)

    return {
        "ok": True,
        "session_id": session_id,
        "message": ai_content,
        "model": model,
    }


def chat(session_id: int, user_message: str) -> dict:
    session = database.get_session(session_id)
    if not session:
        return {"ok": False, "msg": "Session not found"}
    if session.get("ended_at"):
        return {"ok": False, "msg": "会话已结束"}

    model, api_key = _get_keys()
    if not api_key:
        return {"ok": False, "msg": "未配置高级探索 API Key"}

    temperature = config.get("advanced_temperature", 0.5)
    max_tokens  = config.get("advanced_max_tokens", 8192)

    messages = database.get_session_messages(session_id)
    history  = [{"role": m["role"], "content": m["content"]} for m in messages]
    history.append({"role": "user", "content": user_message})

    database.add_session_message(session_id, "user", user_message)

    try:
        ai_content = llm_client.call_llm(
            model=model,
            messages=history,
            system=SYSTEM_PROMPT,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as e:
        return {"ok": False, "msg": f"调用失败: {e}"}

    database.add_session_message(session_id, "assistant", ai_content)
    _save_exploration_file(session_id)

    return {"ok": True, "message": ai_content}


def end_exploration(session_id: int) -> dict:
    session = database.get_session(session_id)
    if not session:
        return {"ok": False, "msg": "Session not found"}
    if session.get("ended_at"):
        return {"ok": True, "digest": session.get("digest", ""), "already_ended": True}

    messages = database.get_session_messages(session_id)
    digest = ""

    normal_key = config.get("normal_api_key", "")
    if normal_key and messages:
        conversation = "\n\n".join(
            f"[{'用户' if m['role'] == 'user' else 'AI'}]: {m['content']}"
            for m in messages
        )
        digest_model = config.get("normal_model", "qwen3.5-plus")
        try:
            digest = llm_client.call_llm(
                model=digest_model,
                messages=[{"role": "user", "content": DIGEST_PROMPT.format(conversation=conversation)}],
                api_key=normal_key,
                temperature=0.5,
                max_tokens=800,
            )
        except Exception:
            digest = "（提要生成失败）"

    database.update_session(session_id, digest=digest, ended_at=datetime.now().isoformat())
    file_path = _save_exploration_file(session_id, digest=digest)
    if file_path:
        database.update_session(session_id, file_path=file_path)

    return {"ok": True, "digest": digest}


def get_exploration(session_id: int):
    session = database.get_session(session_id)
    if not session:
        return None
    messages = database.get_session_messages(session_id)
    return {"session": session, "messages": messages}
