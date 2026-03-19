import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "user_config.json")

# CCF-A 级别及以上的 AI/ML 顶会顶刊（含 ICLR，业内公认顶会但未入 CCF 评级）
CCF_A_VENUES = [
    # 机器学习
    "NeurIPS", "ICML", "ICLR",
    # 计算机视觉
    "CVPR", "ICCV", "ECCV",
    # 人工智能综合
    "AAAI", "IJCAI",
    # 自然语言处理
    "ACL", "EMNLP", "NAACL",
    # 数据挖掘
    "KDD", "SIGIR", "WWW",
    # 顶刊
    "TPAMI", "IJCV", "JMLR",
    "IEEE Transactions on Neural Networks",
    "Artificial Intelligence",
]

# arXiv 搜索时使用的缩写（用于 comment/journal_ref 字段匹配）
CCF_A_ARXIV_TERMS = [
    "NeurIPS", "ICML", "ICLR", "CVPR", "ICCV", "ECCV",
    "AAAI", "IJCAI", "ACL", "EMNLP", "NAACL", "KDD",
    "TPAMI", "JMLR",
]

# Semantic Scholar venue 精确匹配列表
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
    # 缩写也加上，S2 venue 字段有时用缩写
    "NeurIPS", "ICML", "ICLR", "CVPR", "ICCV", "ECCV",
    "AAAI", "IJCAI", "ACL", "EMNLP", "KDD", "TPAMI", "JMLR",
]

# Papers With Code conference slug 列表
CCF_A_PWC_CONFS = [
    "neurips", "icml", "iclr", "cvpr", "iccv", "eccv",
    "aaai", "ijcai", "acl", "emnlp", "naacl", "kdd",
]

DEFAULT_CONFIG = {
    "keywords": [
        "deep learning",
        "neural network",
        "transformer",
        "large language model",
        "computer vision",
        "reinforcement learning",
        "diffusion model",
        "generative model",
        "self-supervised learning",
        "contrastive learning"
    ],
    "schedule_hour": 8,          # 每天几点推送（24小时制）
    "max_papers_per_source": 20, # 每个数据源最多抓取多少篇
    "papers_dir": r"D:\research\papers\downloaded",
    "auto_download": False,       # 是否自动下载所有论文（False=手动选择）
    "anthropic_api_key": "",      # Claude API Key
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
        # 合并默认值（保证新字段不丢失）
        merged = DEFAULT_CONFIG.copy()
        merged.update(saved)
        return merged
    return DEFAULT_CONFIG.copy()

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def get(key, default=None):
    return load_config().get(key, default)
