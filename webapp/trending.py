"""
热度排行与 AI 论文检索模块。
静态关键词排行直接返回，AI 检索/详情通过 Qwen 生成。
"""
import config
import llm_client

# ── 静态热度关键词库（来自 v2 配置）────────────────────────────────
TRENDING_KEYWORDS = [
    # Tier 1
    {"name": "Large Language Model", "zh": "大语言模型",   "score": 100, "domain": "NLP",       "trend": "up",    "tier": 1},
    {"name": "AI Agent",             "zh": "AI Agent",    "score": 98,  "domain": "General",   "trend": "up2",   "tier": 1},
    {"name": "Multimodal LLM",       "zh": "多模态大模型", "score": 97,  "domain": "Multimodal","trend": "up",    "tier": 1},
    {"name": "Diffusion Model",      "zh": "扩散模型",     "score": 96,  "domain": "CV",        "trend": "flat",  "tier": 1},
    {"name": "RAG",                  "zh": "检索增强生成", "score": 95,  "domain": "NLP",       "trend": "up",    "tier": 1},
    # Tier 2
    {"name": "Mixture of Experts",   "zh": "混合专家",     "score": 94,  "domain": "Arch",      "trend": "up",    "tier": 2},
    {"name": "Video Generation",     "zh": "视频生成",     "score": 93,  "domain": "CV",        "trend": "up2",   "tier": 2},
    {"name": "Chain-of-Thought",     "zh": "思维链",       "score": 92,  "domain": "Reasoning", "trend": "flat",  "tier": 2},
    {"name": "Long Context",         "zh": "长上下文",     "score": 91,  "domain": "LLM",       "trend": "up",    "tier": 2},
    {"name": "Code Generation",      "zh": "代码生成",     "score": 90,  "domain": "NLP/SE",    "trend": "flat",  "tier": 2},
    {"name": "World Model",          "zh": "世界模型",     "score": 89,  "domain": "RL/CV",     "trend": "up",    "tier": 2},
    {"name": "RLHF",                 "zh": "RLHF/对齐",   "score": 88,  "domain": "LLM",       "trend": "flat",  "tier": 2},
    {"name": "Efficient Inference",  "zh": "高效推理",     "score": 87,  "domain": "System",    "trend": "up",    "tier": 2},
    {"name": "Gaussian Splatting",   "zh": "3D生成",       "score": 86,  "domain": "CV",        "trend": "up",    "tier": 2},
    {"name": "Embodied AI",          "zh": "具身智能",     "score": 85,  "domain": "Robotics",  "trend": "up",    "tier": 2},
    # Tier 3
    {"name": "Small Language Model", "zh": "小模型",       "score": 84,  "domain": "LLM",       "trend": "up",    "tier": 3},
    {"name": "Mamba / SSM",          "zh": "Mamba",        "score": 83,  "domain": "Arch",      "trend": "up",    "tier": 3},
    {"name": "LoRA / PEFT",          "zh": "LoRA",         "score": 82,  "domain": "Training",  "trend": "flat",  "tier": 3},
    {"name": "Text-to-Image",        "zh": "文生图",       "score": 81,  "domain": "CV",        "trend": "flat",  "tier": 3},
    {"name": "Autonomous Driving",   "zh": "自动驾驶",     "score": 80,  "domain": "CV/Robot",  "trend": "flat",  "tier": 3},
    {"name": "Medical AI",           "zh": "医学AI",       "score": 79,  "domain": "Medical",   "trend": "up",    "tier": 3},
    {"name": "Graph Neural Network", "zh": "图神经网络",   "score": 78,  "domain": "Graph",     "trend": "flat",  "tier": 3},
    {"name": "Knowledge Distillation","zh": "知识蒸馏",    "score": 77,  "domain": "Compress",  "trend": "flat",  "tier": 3},
    {"name": "Contrastive Learning", "zh": "对比学习",     "score": 76,  "domain": "SSL",       "trend": "down",  "tier": 3},
    {"name": "NeRF",                 "zh": "神经辐射场",   "score": 75,  "domain": "3D",        "trend": "down",  "tier": 3},
    # Tier 4
    {"name": "Transformer",          "zh": "Transformer",  "score": 74,  "domain": "Arch",      "trend": "flat",  "tier": 4},
    {"name": "Object Detection",     "zh": "目标检测",     "score": 72,  "domain": "CV",        "trend": "flat",  "tier": 4},
    {"name": "Semantic Segmentation","zh": "语义分割",     "score": 70,  "domain": "CV",        "trend": "flat",  "tier": 4},
    {"name": "Reinforcement Learning","zh": "强化学习",    "score": 68,  "domain": "RL",        "trend": "flat",  "tier": 4},
    {"name": "Self-Supervised Learning","zh": "自监督学习","score": 67,  "domain": "SSL",       "trend": "flat",  "tier": 4},
    {"name": "Quantization",         "zh": "量化",         "score": 64,  "domain": "Compress",  "trend": "flat",  "tier": 4},
    {"name": "Federated Learning",   "zh": "联邦学习",     "score": 62,  "domain": "Privacy",   "trend": "flat",  "tier": 4},
]

SYSTEM_PROMPT = """你是一位 AI/ML 领域的热点追踪专家，精通学术界和工业界的最新趋势。
你能够根据关键词推荐相关论文，并提供领域发展分析。
回答使用中文，论文标题和专业术语保留英文。"""

SEARCH_PROMPT = """请列出「{keyword}」相关的重要论文，包括经典论文和近期热门论文。

输出格式：

## 🏆 必读经典

### 1. [论文标题]
- **发表**：Conference/Journal Year
- **核心贡献**：[一句话]
- **为什么重要**：[简要说明]

### 2. ...

## 📈 近期热门（近1-2年）

### 1. [论文标题]
- **时间**：202x
- **亮点**：[为什么值得关注]

## 📖 推荐阅读顺序

**入门**：...
**进阶**：...

## 🔗 ArXiv 检索
```
abs:{keyword_en} AND (cat:cs.CV OR cat:cs.CL OR cat:cs.LG)
```"""

DETAIL_PROMPT = """请提供「{keyword}」的详细信息。

## 基本信息
（定义、所属领域、热度趋势）

## 发展历程
（关键时间节点 + 里程碑工作，表格形式）

## 核心技术栈
（层次化列出核心技术组件）

## 代表模型/方法
（表格：名称、机构/作者、特点）

## 与相关方向的关系
（和其他热词的关联）

## 入门建议
（推荐论文 + 学习路线）"""


def get_trending_list() -> list:
    return TRENDING_KEYWORDS


def ai_search_papers(keyword: str) -> dict:
    api_key = config.get("normal_api_key", "")
    if not api_key:
        return {"ok": False, "msg": "未配置 API Key"}
    try:
        text = llm_client.call_llm(
            model=config.get("normal_model", "qwen3.5-plus"),
            messages=[{"role": "user", "content": SEARCH_PROMPT.format(keyword=keyword, keyword_en=keyword)}],
            system=SYSTEM_PROMPT,
            api_key=api_key,
            temperature=0.5,
            max_tokens=4096,
        )
        return {"ok": True, "text": text}
    except Exception as e:
        return {"ok": False, "msg": str(e)}


def ai_keyword_detail(keyword: str) -> dict:
    api_key = config.get("normal_api_key", "")
    if not api_key:
        return {"ok": False, "msg": "未配置 API Key"}
    try:
        text = llm_client.call_llm(
            model=config.get("normal_model", "qwen3.5-plus"),
            messages=[{"role": "user", "content": DETAIL_PROMPT.format(keyword=keyword)}],
            system=SYSTEM_PROMPT,
            api_key=api_key,
            temperature=0.5,
            max_tokens=4096,
        )
        return {"ok": True, "text": text}
    except Exception as e:
        return {"ok": False, "msg": str(e)}
