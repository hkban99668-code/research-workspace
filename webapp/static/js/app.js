/* ─── State ─── */
let currentFilter = "";
let currentPage   = 1;
let allPapers     = [];
let searchQuery   = "";

/* ─── Init ─── */
document.addEventListener("DOMContentLoaded", () => {
  loadStats();
  loadPapers();

  // Nav buttons
  document.querySelectorAll(".nav-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentFilter = btn.dataset.filter || "";
      currentPage = 1;
      loadPapers();
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

  // Date filter
  document.getElementById("date-filter").addEventListener("change", e => {
    currentPage = 1;
    loadPapers();
  });

  // Fetch button
  document.getElementById("btn-fetch").addEventListener("click", triggerFetch);

  // Settings
  document.getElementById("btn-settings").addEventListener("click", openSettings);
  document.getElementById("btn-cancel-cfg").addEventListener("click", () => {
    document.getElementById("modal-settings").classList.add("hidden");
  });
  document.getElementById("btn-save-cfg").addEventListener("click", saveSettings);

  // Drawer close
  document.getElementById("drawer-close").addEventListener("click", closeDrawer);
  document.getElementById("drawer-overlay").addEventListener("click", closeDrawer);

  // Pagination
  document.getElementById("btn-prev").addEventListener("click", () => {
    if (currentPage > 1) { currentPage--; loadPapers(); }
  });
  document.getElementById("btn-next").addEventListener("click", () => {
    currentPage++; loadPapers();
  });
});

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

function renderPapers() {
  const list = document.getElementById("paper-list");
  let papers = allPapers;

  if (searchQuery) {
    papers = papers.filter(p =>
      p.title.toLowerCase().includes(searchQuery) ||
      (p.abstract || "").toLowerCase().includes(searchQuery) ||
      (p.keywords || "").toLowerCase().includes(searchQuery)
    );
  }

  if (!papers.length) {
    list.innerHTML = '<div class="empty">暂无论文，点击「立即抓取」获取最新内容</div>';
    return;
  }

  list.innerHTML = papers.map(p => paperCard(p)).join("");

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
  const source = { arxiv: "arXiv", semantic_scholar: "S2", pwc: "HF Papers" }[p.source] || p.source;
  const badgeCls = { arxiv: "badge-arxiv", semantic_scholar: "badge-s2", pwc: "badge-pwc" }[p.source] || "";
  const date = p.published ? p.published.slice(0, 10) : "";
  const authors = p.authors ? p.authors.split(",").slice(0, 3).join(", ") + (p.authors.split(",").length > 3 ? " et al." : "") : "";
  const keywords = p.keywords ? p.keywords.split(",").filter(Boolean).map(k =>
    `<span class="kw-tag">${k.trim()}</span>`
  ).join("") : "";
  const starOn = p.is_starred ? "on" : "";
  const readCls = p.is_read ? "read" : "";
  const dlIcon = p.is_downloaded
    ? `<span class="card-action-btn downloaded" title="已下载">✅</span>`
    : (p.pdf_url
        ? `<button class="card-action-btn" data-id="${p.id}" title="下载 PDF" onclick="event.stopPropagation();cardDownload(${p.id},this)">⬇</button>`
        : "");

  return `
    <div class="paper-card ${readCls}" data-id="${p.id}">
      <div class="card-header">
        <div class="card-title">${escHtml(p.title)}</div>
        <div class="card-actions">
          ${dlIcon}
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
  const data = await api(`/api/papers/${id}`);
  const p = data.paper;
  const a = data.analysis;
  if (!p) return;

  // mark as read
  api(`/api/papers/${id}/read`, { method: "POST" });
  const card = document.querySelector(`.paper-card[data-id="${id}"]`);
  if (card) card.classList.add("read");

  const source = { arxiv: "arXiv", semantic_scholar: "Semantic Scholar", pwc: "Papers With Code" }[p.source] || p.source;
  const date = p.published ? p.published.slice(0, 10) : "未知";

  let analysisHtml = "";
  if (a) {
    analysisHtml = buildAnalysisHtml(a);
  }

  const hasTranslation = !!(p.title_zh && p.abstract_zh);

  document.getElementById("drawer-content").innerHTML = `
    <h2>${escHtml(p.title)}</h2>
    <div class="drawer-meta">
      <span>${source}</span>
      <span>${date}</span>
      ${p.authors ? `<span>${escHtml(p.authors)}</span>` : ""}
    </div>

    <!-- 原文摘要 -->
    ${p.abstract ? `<div class="drawer-abstract">${escHtml(p.abstract)}</div>` : ""}

    <!-- 翻译模块 -->
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

    <div class="drawer-actions">
      ${p.url ? `<a href="${p.url}" target="_blank" class="btn-ghost btn-sm" style="text-decoration:none">🔗 原文页面</a>` : ""}
      ${p.pdf_url ? `<button class="btn-ghost btn-sm" id="dl-btn" onclick="downloadPaper(${p.id}, this)">
        ${p.is_downloaded ? "✅ 已下载" : "⬇ 下载 PDF"}
      </button>` : ""}
      <button class="btn-primary btn-sm" onclick="analyzePaper(${p.id})">
        🤖 ${a ? "重新分析" : "AI 分析"}
      </button>
    </div>
    <div id="analysis-area">${analysisHtml}</div>
  `;

  document.getElementById("drawer").classList.remove("hidden");
}

function closeDrawer() {
  document.getElementById("drawer").classList.add("hidden");
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

async function analyzePaper(id) {
  const area = document.getElementById("analysis-area");
  area.innerHTML = '<div class="loading">AI 分析中，请稍候...</div>';
  const data = await api(`/api/papers/${id}/analyze`, {
    method: "POST",
    body: JSON.stringify({ force: true })
  });
  if (data.ok) {
    area.innerHTML = buildAnalysisHtml(data.data);
    loadStats();
  } else {
    area.innerHTML = `<div class="empty" style="color:var(--danger)">分析失败: ${data.msg}</div>`;
  }
}

async function triggerFetch() {
  const btn = document.getElementById("btn-fetch");
  btn.textContent = "抓取中...";
  btn.disabled = true;
  const data = await api("/api/fetch", { method: "POST" });
  btn.textContent = "⬇ 立即抓取";
  btn.disabled = false;
  if (data.ok) {
    const r = data.results;
    showToast(`抓取完成：arXiv ${r.arxiv} | S2 ${r.semantic_scholar} | PWC ${r.pwc}`);
    loadPapers();
    loadStats();
  } else {
    showToast("抓取失败", true);
  }
}

/* ─── Translate ─── */
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

/* ─── Card download (quick download from card) ─── */
async function cardDownload(id, btn) {
  btn.textContent = "⏳";
  btn.disabled = true;
  const data = await api(`/api/papers/${id}/download`, { method: "POST" });
  if (data.ok) {
    btn.outerHTML = `<span class="card-action-btn downloaded" title="已下载到 ${escHtml(data.path)}">✅</span>`;
    showToast("已保存: " + data.path);
  } else {
    btn.textContent = "⬇";
    btn.disabled = false;
    showToast("下载失败: " + data.msg, true);
  }
}

/* ─── Settings ─── */
async function openSettings() {
  const cfg = await api("/api/config");
  document.getElementById("cfg-hour").value     = cfg.schedule_hour ?? 8;
  document.getElementById("cfg-max").value      = cfg.max_papers_per_source ?? 20;
  document.getElementById("cfg-keywords").value = (cfg.keywords || []).join("\n");
  document.getElementById("modal-settings").classList.remove("hidden");
}

async function saveSettings() {
  const apiKey  = document.getElementById("cfg-api-key").value.trim();
  const hour    = parseInt(document.getElementById("cfg-hour").value);
  const maxP    = parseInt(document.getElementById("cfg-max").value);
  const keywords = document.getElementById("cfg-keywords").value
    .split("\n").map(s => s.trim()).filter(Boolean);

  const payload = { schedule_hour: hour, max_papers_per_source: maxP, keywords };
  if (apiKey) payload.anthropic_api_key = apiKey;

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

/* ─── Analysis HTML builder ─── */
function buildAnalysisHtml(a) {
  const sections = [
    { key: "summary",    icon: "📋", label: "核心摘要" },
    { key: "key_steps",  icon: "🔢", label: "关键步骤" },
    { key: "innovation", icon: "🔬", label: "创新点" },
    { key: "ideas",      icon: "💡", label: "延伸 Ideas" },
  ];
  const inner = sections
    .filter(s => a[s.key] && a[s.key].trim())
    .map(s => `
      <div class="analysis-section">
        <h3>${s.icon} ${s.label}</h3>
        <div class="analysis-text">${escHtml(a[s.key])}</div>
      </div>`)
    .join("");
  return `<div class="analysis-box">${inner}</div>`;
}

/* ─── Utils ─── */
function escHtml(str) {
  return (str || "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}
