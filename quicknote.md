# 快速笔记

## 2026-03-19

### 今日工作提要

**目标：** 从零搭建科研工作流 + 论文检索系统

---

#### 一、搭建科研工作流框架
- 在 `D:\research\` 创建完整工作流文件结构
  - `board.md` 课题看板、`decisions.md` 决策记录、`quicknote.md` 快速笔记、`retrospective.md` 周回顾
  - `papers/downloaded/`、`papers/notes/`、`papers/ideas/` 论文管理目录
  - `.claude/preferences.json` 偏好配置（持续学习）

#### 二、开发论文检索网页（`D:\research\webapp\`）

**技术栈：** Python + Flask + SQLite + APScheduler

**数据源（三个）：**
- arXiv：通过 `journal_ref/comment` 字段过滤顶会论文
- Semantic Scholar：通过 `publicationVenue` 精确匹配 CCF-A 会议/期刊
- HF Daily Papers（原计划 Papers With Code，API 已停用，改用 Hugging Face）

**质量标准：** CCF-A 及以上，覆盖 NeurIPS、ICML、ICLR、CVPR、ICCV、AAAI、IJCAI、ACL、EMNLP、KDD、TPAMI、JMLR 等

**功能：**
- 每天早 8 点自动抓取，也可手动触发
- 论文卡片：标题、来源、作者、摘要预览、关键词标签
- 收藏 ⭐、标记已读、分页浏览
- 侧边栏按来源/收藏/未读过滤

**翻译功能：**
- 论文详情页原文下方有独立「🌐 中文翻译」模块
- 有 Claude API Key 时用 Claude 翻译，否则自动用 Google Translate（国内可用，速度快）
- 翻译结果缓存到数据库，不重复请求

**下载功能：**
- 卡片上直接有 ⬇ 按钮，下载到 `D:\research\papers\downloaded\`
- 自动尝试多个镜像源（arxiv.org → export.arxiv.org），20 秒超时自动切换

**AI 分析功能（预留，待有 API Key 后启用）：**
- 核心摘要、关键步骤、创新点、延伸 Ideas 四个模块

**服务地址：** `http://localhost:5001`（运行 `start.bat` 启动）

---

#### 三、待办
- [ ] 填入 Anthropic API Key，测试 AI 分析 + 高质量翻译
- [ ] 确定第一个具体科研课题方向
- [ ] 如需加速下载，配置本地代理端口
