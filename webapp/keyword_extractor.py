"""
关键词提取模块 — 使用 Qwen 从论文标题/摘要提取结构化学术关键词。
"""
import json
import re
from datetime import datetime
import config
import llm_client
from database import get_paper

SYSTEM_PROMPT = """你是一位专业的机器学习/深度学习文献分析专家，精通从论文、代码、项目描述中提取规范化的学术关键词。
你熟悉 GitHub 热门项目命名规范和各大顶会（NeurIPS、ICML、ICLR、CVPR、ACL 等）的关键词体系。

处理规则：
1. 规范化：将非标准表述映射到标准术语（"图像分类"→"Image Classification"）
2. 去重合并：相近概念保留一个
3. 优先级排序：按重要性和相关度排序"""

EXTRACT_PROMPT = """请从以下论文信息中提取结构化关键词，严格输出 JSON，不要包含任何其他内容。

标题：{title}
摘要：{abstract}

JSON 格式：
{{
  "primary_domain": "Computer Vision",
  "tasks": ["Image Classification", "Object Detection"],
  "methods": ["Vision Transformer", "Self-Supervised Learning"],
  "models": ["ViT", "DINO"],
  "datasets": ["ImageNet", "COCO"],
  "trending": ["Foundation Model"],
  "github_topics": ["vision-transformer", "self-supervised-learning", "pytorch"],
  "suggested_venues": ["CVPR", "NeurIPS"],
  "arxiv_query": "abs:ViT AND (cat:cs.CV OR cat:cs.LG)"
}}"""

# 内存缓存（paper_id → result）
_cache: dict = {}


def extract_paper_keywords(paper_db_id: int, force: bool = False) -> dict:
    if not force and paper_db_id in _cache:
        return {"ok": True, "data": _cache[paper_db_id], "cached": True}

    paper = get_paper(paper_db_id)
    if not paper:
        return {"ok": False, "msg": "Paper not found"}

    api_key = config.get("normal_api_key", "")
    if not api_key:
        return {"ok": False, "msg": "未配置 API Key"}

    model       = config.get("normal_model", "qwen3.5-plus")
    temperature = 0.3   # 低温度确保输出稳定
    max_tokens  = 2048

    prompt = EXTRACT_PROMPT.format(
        title=paper["title"],
        abstract=paper.get("abstract", "无摘要"),
    )

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
        return {"ok": False, "msg": f"调用失败: {e}"}

    # 提取 JSON（模型有时会加 ```json ... ``` 包裹）
    json_str = raw.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", json_str)
    if m:
        json_str = m.group(1)

    try:
        result = json.loads(json_str)
    except json.JSONDecodeError:
        # 降级：返回原始文本
        result = {"raw": raw}

    _cache[paper_db_id] = result
    return {"ok": True, "data": result, "cached": False}
