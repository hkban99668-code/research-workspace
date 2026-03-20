import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "user_config.json")

CCF_A_VENUES = [
    "NeurIPS", "ICML", "ICLR",
    "CVPR", "ICCV", "ECCV",
    "AAAI", "IJCAI",
    "ACL", "EMNLP", "NAACL",
    "KDD", "SIGIR", "WWW",
    "TPAMI", "IJCV", "JMLR",
    "IEEE Transactions on Neural Networks",
    "Artificial Intelligence",
]

CCF_A_ARXIV_TERMS = [
    "NeurIPS", "ICML", "ICLR", "CVPR", "ICCV", "ECCV",
    "AAAI", "IJCAI", "ACL", "EMNLP", "NAACL", "KDD",
    "TPAMI", "JMLR",
]

CCF_A_S2_VENUES = [
    "Neural Information Processing Systems",
    "International Conference on Machine Learning",
    "International Conference on Learning Representations",
    "Computer Vision and Pattern Recognition",
    "International Conference on Computer Vision",
    "European Conference on Computer Vision",
    "AAAI Conference on Artificial Intelligence",
    "International Joint Conference on Artificial Intelligence",
    "Annual Meeting of the Association for Computational Linguistics",
    "Empirical Methods in Natural Language Processing",
    "North American Chapter of the Association for Computational Linguistics",
    "Knowledge Discovery and Data Mining",
    "IEEE Transactions on Pattern Analysis and Machine Intelligence",
    "International Journal of Computer Vision",
    "Journal of Machine Learning Research",
    "NeurIPS", "ICML", "ICLR", "CVPR", "ICCV", "ECCV",
    "AAAI", "IJCAI", "ACL", "EMNLP", "KDD", "TPAMI", "JMLR",
]

CCF_A_PWC_CONFS = [
    "neurips", "icml", "iclr", "cvpr", "iccv", "eccv",
    "aaai", "ijcai", "acl", "emnlp", "naacl", "kdd",
]

DEFAULT_CONFIG = {
    "keywords": [
        "deep learning", "neural network", "transformer",
        "large language model", "computer vision",
        "reinforcement learning", "diffusion model",
        "generative model", "self-supervised learning",
        "contrastive learning"
    ],
    "schedule_hour": 8,
    "max_papers_per_source": 20,
    "papers_dir": r"D:\research\papers\downloaded",
    "auto_download": False,

    # ── 普通分析模式（一般讨论） ──────────────────────────────────
    "normal_model":       "qwen3.5-plus",   # qwen3.5-plus / qwen-flash / 其他
    "normal_api_key":     "",               # DashScope API Key
    "normal_temperature": 0.7,
    "normal_max_tokens":  4096,

    # ── 高级探索模式 ──────────────────────────────────────────────
    "advanced_model":       "claude-sonnet-4-6",  # claude-sonnet-4-6 / claude-opus-4-6
    "advanced_api_key":     "",                   # Anthropic API Key
    "advanced_temperature": 0.5,
    "advanced_max_tokens":  8192,

    "sources": {
        "arxiv": True,
        "semantic_scholar": True,
        "papers_with_code": True
    }
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
        merged = DEFAULT_CONFIG.copy()
        merged.update(saved)
        # 向后兼容旧字段名
        if not merged["normal_api_key"] and merged.get("anthropic_api_key"):
            merged["normal_api_key"] = merged["anthropic_api_key"]
        if not merged["advanced_api_key"]:
            merged["advanced_api_key"] = (
                merged.get("anthropic_api_key_advanced")
                or merged.get("anthropic_api_key", "")
            )
        return merged
    return DEFAULT_CONFIG.copy()


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def get(key, default=None):
    return load_config().get(key, default)
