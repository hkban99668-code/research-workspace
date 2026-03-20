/* ─── State ─── */
let currentFilter   = "";
let currentPage     = 1;
let allPapers       = [];
let searchQuery     = "";
let activeSessionId = null;
let currentPaperId  = null;
let currentView     = "papers";  // "papers" | "trending"
let activeTrendKw   = null;

/* ─── Init ─── */
document.addEventListener("DOMContentLoaded", () => {
  loadStats();
  loadPapers();

  // Nav buttons (handle view switching)
  document.querySelectorAll(".nav-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const view = btn.dataset.view || "papers";
      if (view === "trending") {
        switchView("trending");
      } else {
        currentFilter = btn.dataset.filter || "";
        currentPage = 1;
        switchView("papers");
        loadPapers();
      }
    });
  });

  // Search
  let searchTimer;
  document.getElementById("search-box").addEventListener("input", e => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      searchQuery = e.target.value.toLowerCase();
      renderPapers();
    }, 200);
  });
  document.getElementById("date-filter").addEventListener("change", () => {
    currentPage = 1; loadPapers();
  });

  document.getElementById("btn-fetch").addEventListener("click", triggerFetch);
  document.getElementById("btn-settings").addEventListener("click", openSettings);
  document.getElementById("btn-cancel-cfg").addEventListener("click", () => {
    document.getElementById("modal-settings").classList.add("hidden");
  });
  document.getElementById("btn-save-cfg").addEventListener("click", saveSettings);

  document.getElementById("drawer-close").addEventListener("click", closeDrawer);
  document.getElementById("drawer-overlay").addEventListener("click", closeDrawer);

  document.getElementById("btn-prev").addEventListener("click", () => {
    if (currentPage > 1) { currentPage--; loadPapers(); }
  });
  document.getElementById("btn-next").addEventListener("click", () => {
    currentPage++; loadPapers();
  });

  // Explore controls
  document.getElementById("explore-send-btn").addEventListener("click", sendExploreMessage);
  document.getElementById("explore-end-btn").addEventListener("click", endExploration);
  document.getElementById("explore-input").addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendExploreMessage(); }
  });

  // History toggle
  document.getElementById("history-toggle").addEventListener("click", () => {
    const header = document.getElementById("history-toggle");
    const list   = document.getElementById("history-list");
    header.classList.toggle("collapsed");
    list.style.display = header.classList.contains("collapsed") ? "none" : "";
  });

  // Trending search filter
  document.getElementById("trending-search").addEventListener("input", e => {
    filterTrendingKeywords(e.target.value.toLowerCase());
  });

  // Trending AI panel controls
  document.getElementById("trending-ai-close").addEventListener("click", () => {
    document.getElementById("trending-ai-panel").classList.add("hidden");
  });
  document.getElementById("trending-ai-search-btn").addEventListener("click", () => {
    if (activeTrendKw) trendingAiSearch(activeTrendKw);
  });
  document.getElementById("trending-ai-detail-btn").addEventListener("click", () => {
    if (activeTrendKw) trendingAiDetail(activeTrendKw);
  });
});

/* ─── View switcher ─── */
function switchView(view) {
  currentView = view;
  document.getElementById("view-papers").classList.toggle("hidden", view !== "papers");
  document.getElementById("view-trending").classList.toggle("hidden", view !== "trending");
  if (view === "trending") loadTrending();
}

/* ─── API helpers ─── */
async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts
  });
  return res.json();
}

/* ─── Stats ─── */
async function loadStats() {
  const d = await api("/api/stats");
  document.getElementById("s-total").textContent    = d.total    ?? "—";
  document.getElementById("s-today").textContent    = d.today    ?? "—";
  document.getElementById("s-starred").textContent  = d.starred  ?? "—";
  document.getElementById("s-analyzed").textContent = d.analyzed ?? "—";
}

/* ─── Papers ─── */
async function loadPapers() {
  document.getElementById("paper-list").innerHTML = '<div class="loading">加载中...</div>';
  const params = new URLSearchParams();
  if (currentFilter) currentFilter.split("&").forEach(p => {
    const [k, v] = p.split("="); params.set(k, v);
  });
  const date = document.getElementById("date-filter").value;
  if (date) params.set("date", date);
  params.set("page", currentPage);
  params.set("limit", 20);

  const data = await api(`/api/papers?${params}`);
  allPapers = data.papers || [];
  renderPapers();
  updatePagination();
}

function renderPapers(container = "paper-list", papers = null) {
  const list = document.getElementById(container);
  let ps = papers || allPapers;
  if (container === "paper-list" && searchQuery) {
    ps = ps.filter(p =>
      p.title.toLowerCase().includes(searchQuery) ||
      (p.abstract || "").toLowerCase().includes(searchQuery) ||
      (p.keywords || "").toLowerCase().includes(searchQuery)
    );
  }
  if (!ps.length) {
    list.innerHTML = '<div class="empty">暂无匹配论文</div>';
    return;
  }
  list.innerHTML = ps.map(p => paperCard(p)).join("");
  list.querySelectorAll(".paper-card").forEach(card => {
    card.addEventListener("click", e => {
      if (e.target.closest(".card-star")) return;
      openDrawer(parseInt(card.dataset.id));
    });
  });
  list.querySelectorAll(".card-star").forEach(btn => {
    btn.addEventListener("click", e => {
      e.stopPropagation();
      toggleStar(parseInt(btn.dataset.id), btn);
    });
  });
}

function paperCard(p) {
  const source   = { arxiv: "arXiv", semantic_scholar: "S2", pwc: "HF Papers" }[p.source] || p.source;
  const badgeCls = { arxiv: "badge-arxiv", semantic_scholar: "badge-s2", pwc: "badge-pwc" }[p.source] || "";
  const date     = p.published ? p.published.slice(0, 10) : "";
  const authors  = p.authors ? p.authors.split(",").slice(0, 3).join(", ") + (p.authors.split(",").length > 3 ? " et al." : "") : "";
  const keywords = p.keywords ? p.keywords.split(",").filter(Boolean).map(k =>
    `<span class="kw-tag">${k.trim()}</span>`).join("") : "";
  const starOn   = p.is_starred ? "on" : "";
  const readCls  = p.is_read ? "read" : "";
  const dlIcon   = p.is_downloaded
    ? `<span class="card-action-btn downloaded" title="已下载">✅</span>`
    : `<button class="card-action-btn" title="下载 PDF" onclick="event.stopPropagation();cardDownload(${p.id},this)">⬇</button>`;

  return `
    <div class="paper-card ${readCls}" data-id="${p.id}">
      <div class="card-header">
        <div class="card-title">${escHtml(p.title)}</div>
        <div class="card-actions">${dlIcon}
          <button class="card-star ${starOn}" data-id="${p.id}" title="收藏">⭐</button>
        </div>
      </div>
      <div class="card-meta">
        <span class="badge ${badgeCls}">${source}</span>
        ${date ? `<span class="card-date">${date}</span>` : ""}
        ${authors ? `<span class="card-authors">${escHtml(authors)}</span>` : ""}
      </div>
      ${p.abstract ? `<div class="card-abstract">${escHtml(p.abstract)}</div>` : ""}
      ${keywords ? `<div class="card-keywords">${keywords}</div>` : ""}
    </div>`;
}

/* ─── Drawer ─── */
async function openDrawer(id) {
  currentPaperId = id;
  activeSessionId = null;
  const data = await api(`/api/papers/${id}`);
  const p = data.paper;
  const a = data.analysis;
  if (!p) return;

  api(`/api/papers/${id}/read`, { method: "POST" });
  const card = document.querySelector(`.paper-card[data-id="${id}"]`);
  if (card) card.classList.add("read");

  const source = { arxiv: "arXiv", semantic_scholar: "Semantic Scholar", pwc: "Papers With Code" }[p.source] || p.source;
  const date   = p.published ? p.published.slice(0, 10) : "未知";
  const hasTranslation = !!(p.title_zh && p.abstract_zh);

  document.getElementById("drawer-content").innerHTML = `
    <h2>${escHtml(p.title)}</h2>
    <div class="drawer-meta">
      <span>${source}</span><span>${date}</span>
      ${p.authors ? `<span>${escHtml(p.authors)}</span>` : ""}
    </div>
    ${p.abstract ? `<div class="drawer-abstract">${escHtml(p.abstract)}</div>` : ""}

    <div class="translation-block" id="translation-block">
      <div class="translation-block-header">
        <span class="translation-block-title">🌐 中文翻译</span>
        <button class="btn-ghost btn-sm" id="translate-btn" onclick="translatePaper(${p.id})">
          ${hasTranslation ? "重新翻译" : "点击翻译"}
        </button>
      </div>
      <div id="translation-content">
        ${hasTranslation ? `
          <div class="translation-title">${escHtml(p.title_zh)}</div>
          <div class="translation-abstract">${escHtml(p.abstract_zh)}</div>
        ` : `<div class="translation-placeholder">点击右上角「点击翻译」获取中文翻译</div>`}
      </div>
    </div>

    <div class="drawer-actions" style="margin-top:18px">
      ${p.url ? `<a href="${p.url}" target="_blank" class="btn-ghost btn-sm" style="text-decoration:none">🔗 原文页面</a>` : ""}
      ${p.is_downloaded
        ? `<button class="btn-ghost btn-sm" disabled>✅ 已下载</button>`
        : `<button class="btn-ghost btn-sm" id="dl-btn" onclick="downloadPaper(${p.id}, this)">⬇ 下载 PDF</button>`}
      <button class="btn-ghost btn-sm" onclick="extractKeywords(${p.id})">🏷️ 关键词</button>
      <button class="btn-primary btn-sm" onclick="analyzePaper(${p.id})">
        🔍 ${a ? "重新普通分析" : "普通分析"}
      </button>
      <button class="btn-advanced btn-sm" onclick="startExploration(${p.id})">🧠 高级探索</button>
    </div>
    <div id="analysis-area">${a ? buildAnalysisHtml(a) : ""}</div>
  `;

  document.getElementById("keyword-area").innerHTML = "";
  document.getElementById("explore-panel").classList.add("hidden");
  document.getElementById("explore-messages").innerHTML = "";
  document.getElementById("explore-input").value = "";
  document.getElementById("explore-digest-area").classList.add("hidden");
  document.getElementById("drawer").classList.remove("hidden");
  loadPaperHistory(id);
}

function closeDrawer() {
  document.getElementById("drawer").classList.add("hidden");
  currentPaperId = null;
  activeSessionId = null;
}

/* ─── Normal Analysis ─── */
async function analyzePaper(id) {
  const area = document.getElementById("analysis-area");
  area.innerHTML = '<div class="loading">🔍 普通分析中（Qwen）...</div>';
  const data = await api(`/api/papers/${id}/analyze`, {
    method: "POST", body: JSON.stringify({ force: true })
  });
  if (data.ok) {
    area.innerHTML = buildAnalysisHtml(data.data);
    loadStats(); loadPaperHistory(id);
  } else {
    area.innerHTML = `<div class="empty" style="color:var(--danger)">分析失败: ${escHtml(data.msg)}</div>`;
  }
}

/* ─── Keyword Extraction ─── */
async function extractKeywords(id) {
  const area = document.getElementById("keyword-area");
  area.innerHTML = '<div class="loading">🏷️ 提取关键词中...</div>';
  const data = await api(`/api/papers/${id}/keywords`, {
    method: "POST", body: JSON.stringify({})
  });
  if (!data.ok) {
    area.innerHTML = `<div class="empty" style="color:var(--danger)">提取失败: ${escHtml(data.msg)}</div>`;
    return;
  }
  area.innerHTML = buildKeywordHtml(data.data);
}

function buildKeywordHtml(kw) {
  if (kw.raw) {
    return `<div class="keyword-card"><div class="keyword-card-title">🏷️ 关键词提取</div><pre style="white-space:pre-wrap;font-size:.84rem">${escHtml(kw.raw)}</pre></div>`;
  }
  const groups = [
    { key: "tasks",    label: "任务类型",  cls: "tag-task"     },
    { key: "methods",  label: "方法/范式", cls: "tag-method"   },
    { key: "models",   label: "模型/架构", cls: "tag-model"    },
    { key: "datasets", label: "数据集",   cls: "tag-dataset"  },
    { key: "trending", label: "热门概念", cls: "tag-trending" },
    { key: "github_topics", label: "GitHub Topics", cls: "tag-github" },
  ];
  const tagsHtml = groups
    .filter(g => kw[g.key] && kw[g.key].length)
    .map(g => `
      <div class="keyword-group">
        <div class="keyword-group-label">${g.label}</div>
        <div class="keyword-tags">
          ${kw[g.key].map(t => `<span class="keyword-tag ${g.cls}">${escHtml(t)}</span>`).join("")}
        </div>
      </div>`).join("");

  const venues   = kw.suggested_venues ? kw.suggested_venues.join(" · ") : "";
  const arxivQ   = kw.arxiv_query || "";

  return `
    <div class="keyword-card">
      <div class="keyword-card-title">🏷️ 关键词提取</div>
      ${kw.primary_domain ? `<div class="keyword-domain">领域：<b>${escHtml(kw.primary_domain)}</b></div>` : ""}
      ${tagsHtml}
      ${venues ? `<div class="keyword-venues">推荐投稿：${escHtml(venues)}</div>` : ""}
      ${arxivQ ? `<div class="keyword-arxiv">arXiv 检索：${escHtml(arxivQ)}</div>` : ""}
    </div>`;
}

/* ─── Advanced Exploration ─── */
async function startExploration(id) {
  const panel    = document.getElementById("explore-panel");
  const messages = document.getElementById("explore-messages");
  const badge    = document.getElementById("explore-model-badge");
  const digestArea = document.getElementById("explore-digest-area");

  panel.classList.remove("hidden");
  digestArea.classList.add("hidden");
  messages.innerHTML = '<div class="explore-loading">🧠 深度分析中（Claude）...</div>';
  document.getElementById("explore-input-area").style.display = "none";
  panel.scrollIntoView({ behavior: "smooth", block: "start" });

  const data = await api(`/api/papers/${id}/explore/start`, { method: "POST" });
  if (!data.ok) {
    messages.innerHTML = `<div class="empty" style="color:var(--danger)">启动失败: ${escHtml(data.msg)}</div>`;
    return;
  }
  activeSessionId = data.session_id;
  badge.textContent = data.model || "claude-sonnet-4-6";
  messages.innerHTML = "";
  appendExploreMessage("user", "（初始深度分析请求）");
  appendExploreMessage("assistant", data.message);
  document.getElementById("explore-input-area").style.display = "";
  document.getElementById("explore-input").focus();
}

async function sendExploreMessage() {
  if (!activeSessionId) return;
  const input = document.getElementById("explore-input");
  const text  = input.value.trim();
  if (!text) return;
  input.value = "";
  appendExploreMessage("user", text);

  const messages  = document.getElementById("explore-messages");
  const loadingEl = document.createElement("div");
  loadingEl.className = "explore-loading";
  loadingEl.textContent = "思考中...";
  messages.appendChild(loadingEl);
  messages.scrollTop = messages.scrollHeight;

  const data = await api(`/api/sessions/${activeSessionId}/chat`, {
    method: "POST", body: JSON.stringify({ message: text })
  });
  loadingEl.remove();
  appendExploreMessage(data.ok ? "assistant" : "assistant", data.ok ? data.message : `❌ ${data.msg}`);
}

async function endExploration() {
  if (!activeSessionId) return;
  const btn = document.getElementById("explore-end-btn");
  btn.textContent = "生成提要中...";
  btn.disabled = true;

  const data = await api(`/api/sessions/${activeSessionId}/end`, { method: "POST" });
  btn.textContent = "已结束";
  document.getElementById("explore-input-area").style.display = "none";

  if (data.ok && data.digest) {
    const digestArea = document.getElementById("explore-digest-area");
    digestArea.innerHTML = `
      <div class="explore-digest-title">📋 会话提要</div>
      <div class="explore-digest-body">${escHtml(data.digest)}</div>`;
    digestArea.classList.remove("hidden");
  }
  if (currentPaperId) loadPaperHistory(currentPaperId);
  showToast("会话已保存到本地");
}

function appendExploreMessage(role, content) {
  const messages = document.getElementById("explore-messages");
  const label    = role === "user" ? "用户" : "AI 探索";
  const div      = document.createElement("div");
  div.className  = `explore-msg ${role}`;
  div.innerHTML  = `
    <div class="explore-msg-label">${escHtml(label)}</div>
    <div class="explore-msg-body">${escHtml(content)}</div>`;
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
}

/* ─── History ─── */
async function loadPaperHistory(paperId) {
  const section = document.getElementById("history-section");
  const list    = document.getElementById("history-list");
  const data    = await api(`/api/papers/${paperId}/sessions`);
  const sessions = data.sessions || [];

  if (!sessions.length) { section.classList.add("hidden"); return; }
  section.classList.remove("hidden");
  list.innerHTML = sessions.map(s => {
    const typeLabel = s.type === "advanced" ? "高级探索" : "普通分析";
    const status    = s.ended_at ? "已完成" : "进行中";
    const date      = s.created_at ? s.created_at.slice(0, 16).replace("T", " ") : "";
    const preview   = s.digest ? s.digest.slice(0, 60) + (s.digest.length > 60 ? "..." : "") : "暂无提要";
    return `
      <div class="history-item" onclick="loadHistorySession(${s.id}, '${s.type}')">
        <span class="history-badge ${s.type}">${typeLabel}</span>
        <div class="history-item-info">
          <div class="history-item-date">${date}</div>
          <div class="history-item-digest">${escHtml(preview)}</div>
        </div>
        <span class="history-item-status">${status}</span>
      </div>`;
  }).join("");
}

async function loadHistorySession(sessionId, type) {
  if (type !== "advanced") return;
  const data = await api(`/api/sessions/${sessionId}`);
  if (!data.session) return;

  const panel      = document.getElementById("explore-panel");
  const messages   = document.getElementById("explore-messages");
  const badge      = document.getElementById("explore-model-badge");
  const digestArea = document.getElementById("explore-digest-area");
  const ended      = !!data.session.ended_at;

  panel.classList.remove("hidden");
  messages.innerHTML = "";
  badge.textContent  = data.session.model || "claude-sonnet-4-6";

  for (const m of data.messages) {
    if (m.role === "user" || m.role === "assistant") appendExploreMessage(m.role, m.content);
  }

  if (ended && data.session.digest) {
    digestArea.innerHTML = `
      <div class="explore-digest-title">📋 会话提要</div>
      <div class="explore-digest-body">${escHtml(data.session.digest)}</div>`;
    digestArea.classList.remove("hidden");
    document.getElementById("explore-input-area").style.display = "none";
    document.getElementById("explore-end-btn").textContent = "已结束";
    document.getElementById("explore-end-btn").disabled = true;
  } else {
    activeSessionId = sessionId;
    digestArea.classList.add("hidden");
    document.getElementById("explore-input-area").style.display = "";
    document.getElementById("explore-end-btn").textContent = "结束会话 & 保存";
    document.getElementById("explore-end-btn").disabled = false;
  }
  panel.scrollIntoView({ behavior: "smooth", block: "start" });
}

/* ─── Trending ─── */
let _trendingData = [];

async function loadTrending() {
  if (_trendingData.length) { renderTrendingGrid(_trendingData); return; }
  const data = await api("/api/trending");
  _trendingData = data.keywords || [];
  renderTrendingGrid(_trendingData);
}

function renderTrendingGrid(keywords) {
  const grid = document.getElementById("trending-grid");
  const tiers = [
    { tier: 1, label: "Tier 1 · 顶级热词 (95-100)", medals: ["🥇","🥈","🥉","4","5"] },
    { tier: 2, label: "Tier 2 · 高热词 (85-94)",    medals: [] },
    { tier: 3, label: "Tier 3 · 中热词 (75-84)",    medals: [] },
    { tier: 4, label: "Tier 4 · 基础热词 (60-74)",  medals: [] },
  ];

  const trendIcon = t => ({ up: "🔺", up2: "🔺🔺", flat: "➡️", down: "🔻" }[t] || "");

  grid.innerHTML = tiers.map(({ tier, label }) => {
    const kws = keywords.filter(k => k.tier === tier);
    if (!kws.length) return "";
    return `
      <div class="trending-tier">
        <div class="trending-tier-label">${label}</div>
        <div class="trending-keywords">
          ${kws.map(k => `
            <button class="trending-kw tier-${tier}" data-kw="${escHtml(k.name)}" onclick="selectTrendKeyword(this, '${escHtml(k.name)}')">
              ${escHtml(k.name)}
              <span class="trending-kw-score">${k.score}</span>
              <span class="trending-kw-trend">${trendIcon(k.trend)}</span>
            </button>`).join("")}
        </div>
      </div>`;
  }).join("");
}

function filterTrendingKeywords(query) {
  document.querySelectorAll(".trending-kw").forEach(btn => {
    const name = btn.dataset.kw.toLowerCase();
    btn.style.display = (!query || name.includes(query)) ? "" : "none";
  });
}

async function selectTrendKeyword(btn, keyword) {
  // Toggle active
  document.querySelectorAll(".trending-kw").forEach(b => b.classList.remove("active"));
  btn.classList.add("active");
  activeTrendKw = keyword;

  // Update AI panel header
  document.getElementById("trending-ai-title").textContent = `🔍 ${keyword}`;
  document.getElementById("trending-ai-content").innerHTML = '<div class="loading">搜索本地论文中...</div>';
  document.getElementById("trending-ai-panel").classList.remove("hidden");

  // Search local papers
  const q = keyword.toLowerCase().replace(/\s+/g, "|");
  const data = await api(`/api/papers?limit=100`);
  const all  = data.papers || [];
  const kws  = keyword.toLowerCase().split(/\s+/);
  const matched = all.filter(p => {
    const text = ((p.title || "") + " " + (p.abstract || "") + " " + (p.keywords || "")).toLowerCase();
    return kws.some(w => w.length > 2 && text.includes(w));
  });

  document.getElementById("trending-ai-content").innerHTML =
    `<span style="color:var(--muted);font-size:.84rem">本地匹配 ${matched.length} 篇 · 点击上方按钮获取 AI 推荐</span>`;

  const section = document.getElementById("trending-papers-section");
  const title   = document.getElementById("trending-papers-title");
  const count   = document.getElementById("trending-papers-count");
  const list    = document.getElementById("trending-paper-list");

  if (matched.length) {
    section.classList.remove("hidden");
    title.textContent = `「${keyword}」本地论文`;
    count.textContent = `共 ${matched.length} 篇`;
    list.innerHTML = "";
    matched.slice(0, 20).forEach(p => {
      const div = document.createElement("div");
      div.innerHTML = paperCard(p);
      const card = div.firstElementChild;
      card.addEventListener("click", e => {
        if (e.target.closest(".card-star")) return;
        openDrawer(p.id);
      });
      card.querySelectorAll(".card-star").forEach(b => {
        b.addEventListener("click", e => { e.stopPropagation(); toggleStar(p.id, b); });
      });
      list.appendChild(card);
    });
  } else {
    section.classList.add("hidden");
  }
}

async function trendingAiSearch(keyword) {
  const content = document.getElementById("trending-ai-content");
  content.innerHTML = '<div class="loading">🤖 AI 检索论文中...</div>';
  const data = await api("/api/trending/search", {
    method: "POST", body: JSON.stringify({ keyword })
  });
  content.textContent = data.ok ? data.text : `错误: ${data.msg}`;
}

async function trendingAiDetail(keyword) {
  const content = document.getElementById("trending-ai-content");
  content.innerHTML = '<div class="loading">🤖 生成详情中...</div>';
  const data = await api("/api/trending/detail", {
    method: "POST", body: JSON.stringify({ keyword })
  });
  content.textContent = data.ok ? data.text : `错误: ${data.msg}`;
}

/* ─── Actions ─── */
async function toggleStar(id, btn) {
  const data = await api(`/api/papers/${id}/star`, { method: "POST" });
  btn.classList.toggle("on", !!data.is_starred);
  loadStats();
}

async function downloadPaper(id, btn) {
  btn.textContent = "下载中...";
  btn.disabled = true;
  const data = await api(`/api/papers/${id}/download`, { method: "POST" });
  if (data.ok) {
    btn.textContent = "✅ 已下载";
    showToast(`已保存到: ${data.path}`);
  } else {
    btn.textContent = "⬇ 下载 PDF";
    btn.disabled = false;
    showToast("下载失败: " + data.msg, true);
  }
}

async function triggerFetch() {
  const btn = document.getElementById("btn-fetch");
  btn.textContent = "抓取中..."; btn.disabled = true;
  const data = await api("/api/fetch", { method: "POST" });
  btn.textContent = "⬇ 立即抓取"; btn.disabled = false;
  if (data.ok) {
    const r = data.results;
    showToast(`抓取完成：arXiv ${r.arxiv} | S2 ${r.semantic_scholar} | PWC ${r.pwc}`);
    loadPapers(); loadStats();
  } else {
    showToast("抓取失败", true);
  }
}

async function translatePaper(id) {
  const btn     = document.getElementById("translate-btn");
  const content = document.getElementById("translation-content");
  if (btn) { btn.textContent = "翻译中..."; btn.disabled = true; }
  if (content) content.innerHTML = `<div class="translation-loading">⏳ 正在翻译，请稍候...</div>`;

  const data = await api(`/api/papers/${id}/translate`, { method: "POST", body: JSON.stringify({}) });
  if (btn) { btn.textContent = "重新翻译"; btn.disabled = false; }
  if (!data.ok) {
    if (content) content.innerHTML = `<div class="translation-placeholder" style="color:var(--danger)">翻译失败：${escHtml(data.msg)}</div>`;
    showToast("翻译失败: " + data.msg, true);
    return;
  }
  if (content) {
    content.innerHTML = `
      <div class="translation-title">${escHtml(data.title_zh)}</div>
      <div class="translation-abstract">${escHtml(data.abstract_zh)}</div>`;
  }
  showToast(data.cached ? "已显示缓存翻译" : "翻译完成");
}

async function cardDownload(id, btn) {
  btn.textContent = "⏳"; btn.disabled = true;
  const data = await api(`/api/papers/${id}/download`, { method: "POST" });
  if (data.ok) {
    btn.outerHTML = `<span class="card-action-btn downloaded" title="已下载">✅</span>`;
    showToast("已保存: " + data.path);
  } else {
    btn.textContent = "⬇"; btn.disabled = false;
    showToast("下载失败: " + data.msg, true);
  }
}

/* ─── Settings ─── */
async function openSettings() {
  const cfg = await api("/api/config");
  document.getElementById("cfg-normal-model").value   = cfg.normal_model   ?? "qwen3.5-plus";
  document.getElementById("cfg-advanced-model").value = cfg.advanced_model ?? "claude-sonnet-4-6";
  document.getElementById("cfg-hour").value           = cfg.schedule_hour  ?? 8;
  document.getElementById("cfg-max").value            = cfg.max_papers_per_source ?? 20;
  document.getElementById("cfg-keywords").value       = (cfg.keywords || []).join("\n");
  document.getElementById("modal-settings").classList.remove("hidden");
}

async function saveSettings() {
  const normalKey     = document.getElementById("cfg-normal-key").value.trim();
  const normalModel   = document.getElementById("cfg-normal-model").value.trim();
  const advancedKey   = document.getElementById("cfg-advanced-key").value.trim();
  const advancedModel = document.getElementById("cfg-advanced-model").value.trim();
  const hour    = parseInt(document.getElementById("cfg-hour").value);
  const maxP    = parseInt(document.getElementById("cfg-max").value);
  const keywords = document.getElementById("cfg-keywords").value
    .split("\n").map(s => s.trim()).filter(Boolean);

  const payload = { schedule_hour: hour, max_papers_per_source: maxP, keywords };
  if (normalKey)    payload.normal_api_key    = normalKey;
  if (normalModel)  payload.normal_model      = normalModel;
  if (advancedKey)  payload.advanced_api_key  = advancedKey;
  if (advancedModel) payload.advanced_model   = advancedModel;

  const data = await api("/api/config", { method: "POST", body: JSON.stringify(payload) });
  if (data.ok) {
    showToast("设置已保存");
    document.getElementById("modal-settings").classList.add("hidden");
  } else {
    showToast("保存失败", true);
  }
}

/* ─── Pagination ─── */
function updatePagination() {
  document.getElementById("page-info").textContent = `第 ${currentPage} 页`;
  document.getElementById("btn-prev").disabled = currentPage <= 1;
  document.getElementById("btn-next").disabled = allPapers.length < 20;
}

/* ─── Toast ─── */
function showToast(msg, isErr = false) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.style.borderColor = isErr ? "var(--danger)" : "var(--border)";
  t.classList.remove("hidden");
  setTimeout(() => t.classList.add("hidden"), 3500);
}

/* ─── Analysis HTML ─── */
function buildAnalysisHtml(a) {
  const typeLabel = a.analysis_type === "advanced" ? "高级探索" : "普通分析";
  const typeCls   = a.analysis_type === "advanced" ? "advanced" : "normal";
  const sections  = [
    { key: "summary",    icon: "📋", label: "核心摘要" },
    { key: "key_steps",  icon: "🔢", label: "关键步骤" },
    { key: "innovation", icon: "🔬", label: "创新点"   },
    { key: "ideas",      icon: "💡", label: "延伸 Ideas" },
  ];
  const inner = sections.filter(s => a[s.key] && a[s.key].trim())
    .map(s => `
      <div class="analysis-section">
        <h3>${s.icon} ${s.label}</h3>
        <div class="analysis-text">${escHtml(a[s.key])}</div>
      </div>`).join("");
  return `<div class="analysis-box">
    <span class="analysis-type-badge ${typeCls}">${typeLabel}</span>${inner}</div>`;
}

/* ─── Utils ─── */
function escHtml(str) {
  return (str || "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}
