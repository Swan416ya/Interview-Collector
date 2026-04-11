// ==UserScript==
// @name         Interview Collector · 牛客面经一键入库
// @namespace    https://github.com/local/interview-collector
// @version      1.0.0
// @description  在牛客面试经验列表/讨论页注入「+」，调用本地 Interview Collector 后端的 /api/import/preview 与 /api/import/commit
// @author       Interview-Collector
// @match        https://www.nowcoder.com/interview/center*
// @match        https://www.nowcoder.com/discuss/*
// @match        https://ac.nowcoder.com/discuss/*
// @connect      127.0.0.1
// @connect      localhost
// @connect      www.nowcoder.com
// @connect      ac.nowcoder.com
// @grant        GM_xmlhttpRequest
// @grant        GM_addStyle
// @run-at       document-idle
// ==/UserScript==

(function () {
  "use strict";

  /** 与前端 VITE_API_BASE_URL 一致；若改端口请同步修改 */
  const API_BASE = "http://127.0.0.1:8000";

  const PREVIEW_TIMEOUT_MS = 120_000;
  const COMMIT_TIMEOUT_MS = 180_000;

  GM_addStyle(`
    .ic-nc-import-btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 22px;
      height: 22px;
      margin-left: 6px;
      padding: 0 6px;
      border: none;
      border-radius: 4px;
      background: #00b894;
      color: #fff !important;
      font-size: 14px;
      font-weight: 700;
      line-height: 1;
      cursor: pointer;
      vertical-align: middle;
      box-shadow: 0 1px 3px rgba(0,0,0,.2);
    }
    .ic-nc-import-btn:hover { filter: brightness(1.08); }
    .ic-nc-import-btn:disabled { opacity: .55; cursor: not-allowed; }
    .ic-nc-fab {
      position: fixed;
      right: 20px;
      bottom: 24px;
      z-index: 2147483640;
      min-width: 48px;
      height: 48px;
      border: none;
      border-radius: 50%;
      background: #00b894;
      color: #fff;
      font-size: 26px;
      font-weight: 700;
      cursor: pointer;
      box-shadow: 0 4px 14px rgba(0,0,0,.25);
    }
    .ic-nc-fab:hover { filter: brightness(1.08); }
    .ic-nc-fab:disabled { opacity: .55; cursor: not-allowed; }
    .ic-nc-overlay {
      position: fixed;
      inset: 0;
      z-index: 2147483646;
      background: rgba(0,0,0,.45);
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 16px;
      box-sizing: border-box;
    }
    .ic-nc-panel {
      width: min(720px, 100%);
      max-height: min(88vh, 900px);
      background: #fff;
      border-radius: 10px;
      box-shadow: 0 12px 40px rgba(0,0,0,.2);
      display: flex;
      flex-direction: column;
      overflow: hidden;
      color: #1a1a1a;
      font-family: system-ui, -apple-system, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
    }
    .ic-nc-panel header {
      padding: 14px 16px;
      border-bottom: 1px solid #eee;
      font-size: 16px;
      font-weight: 600;
    }
    .ic-nc-panel .ic-nc-body {
      padding: 12px 16px;
      overflow: auto;
      flex: 1;
    }
    .ic-nc-panel footer {
      padding: 12px 16px;
      border-top: 1px solid #eee;
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }
    .ic-nc-panel footer button {
      padding: 8px 14px;
      border-radius: 6px;
      border: 1px solid #ccc;
      background: #f7f7f7;
      cursor: pointer;
      font-size: 14px;
    }
    .ic-nc-panel footer button.ic-nc-primary {
      background: #00b894;
      border-color: #00a383;
      color: #fff;
    }
    .ic-nc-panel footer button:disabled { opacity: .5; cursor: not-allowed; }
    .ic-nc-q {
      display: flex;
      gap: 10px;
      align-items: flex-start;
      padding: 10px 0;
      border-bottom: 1px solid #f0f0f0;
      font-size: 13px;
    }
    .ic-nc-q:last-child { border-bottom: none; }
    .ic-nc-q input[type=checkbox] { margin-top: 4px; }
    .ic-nc-q .ic-nc-meta { color: #666; font-size: 12px; margin-top: 4px; }
    .ic-nc-q .ic-nc-stem { white-space: pre-wrap; word-break: break-word; }
    .ic-nc-toast {
      position: fixed;
      left: 50%;
      bottom: 32px;
      transform: translateX(-50%);
      z-index: 2147483647;
      max-width: min(520px, 92vw);
      padding: 10px 16px;
      border-radius: 8px;
      background: #2d3436;
      color: #fff;
      font-size: 14px;
      box-shadow: 0 4px 20px rgba(0,0,0,.3);
    }
    .ic-nc-toast.err { background: #c0392b; }
  `);

  function toast(msg, isErr) {
    const el = document.createElement("div");
    el.className = "ic-nc-toast" + (isErr ? " err" : "");
    el.textContent = msg;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 4200);
  }

  function gmRequest(opts) {
    return new Promise((resolve, reject) => {
      GM_xmlhttpRequest({
        method: opts.method || "GET",
        url: opts.url,
        headers: opts.headers || {},
        data: opts.data,
        timeout: opts.timeout ?? 60_000,
        onload(res) {
          resolve(res);
        },
        onerror(err) {
          reject(err);
        },
        ontimeout() {
          reject(new Error("请求超时"));
        },
      });
    });
  }

  function parseJsonResponse(res) {
    const text = res.responseText || "";
    try {
      return JSON.parse(text);
    } catch {
      throw new Error("响应不是合法 JSON: " + text.slice(0, 200));
    }
  }

  async function apiPost(path, body, timeout) {
    const res = await gmRequest({
      method: "POST",
      url: API_BASE + path,
      headers: { "Content-Type": "application/json" },
      data: JSON.stringify(body),
      timeout,
    });
    if (res.status < 200 || res.status >= 300) {
      let detail = res.responseText || res.statusText;
      try {
        const j = JSON.parse(detail);
        detail = typeof j.detail === "object" ? JSON.stringify(j.detail) : j.detail || detail;
      } catch {
        /* keep text */
      }
      throw new Error(`HTTP ${res.status}: ${detail}`);
    }
    return parseJsonResponse(res);
  }

  async function apiGet(url, timeout) {
    const res = await gmRequest({ method: "GET", url, timeout: timeout ?? 60_000 });
    if (res.status < 200 || res.status >= 300) {
      throw new Error(`拉取页面失败 HTTP ${res.status}`);
    }
    return res.responseText;
  }

  function discussIdFromHref(href) {
    if (!href) return null;
    const m = String(href).match(/\/discuss\/(\d+)/);
    return m ? m[1] : null;
  }

  function normalizeDiscussUrl(href) {
    const id = discussIdFromHref(href);
    if (!id) return null;
    try {
      const u = new URL(href, "https://www.nowcoder.com");
      if (!u.hostname.endsWith("nowcoder.com")) return null;
      return `${u.origin}/discuss/${id}`;
    } catch {
      return null;
    }
  }

  /** 从讨论页 Document 中尽量抽取正文（列表页抓取或当前页） */
  function extractDiscussPlainText(doc) {
    const selectors = [
      ".post-topic-main",
      ".topic-main",
      ".topic-content",
      ".topic-des",
      ".nc-post-content",
      "[class*='postDetail'] [class*='content']",
      "[class*='rich-text']",
      ".ql-editor",
      "article",
      ".markdown-body",
      "#markdown-body",
      "main",
    ];
    for (const sel of selectors) {
      const el = doc.querySelector(sel);
      if (el) {
        const t = el.innerText.replace(/\u00a0/g, " ").trim();
        if (t.length >= 40) return t.slice(0, 80_000);
      }
    }
    const titleEl = doc.querySelector("h1, .topic-title, [class*='topic-title']");
    const title = titleEl ? titleEl.innerText.trim() : "";
    const body = (doc.body && doc.body.innerText) ? doc.body.innerText.trim() : "";
    const combined = [title, body].filter(Boolean).join("\n\n");
    return combined.slice(0, 80_000);
  }

  function parseHtmlToDocument(html) {
    const p = new DOMParser();
    return p.parseFromString(html, "text/html");
  }

  function closeOverlay(overlay) {
    overlay.remove();
  }

  function openSelectModal(questions, onConfirm) {
    const overlay = document.createElement("div");
    overlay.className = "ic-nc-overlay";
    const panel = document.createElement("div");
    panel.className = "ic-nc-panel";
    panel.addEventListener("click", (e) => e.stopPropagation());
    overlay.addEventListener("click", () => closeOverlay(overlay));

    const header = document.createElement("header");
    header.textContent = `AI 提取到 ${questions.length} 道题，勾选后入库`;
    const body = document.createElement("div");
    body.className = "ic-nc-body";

    const selected = questions.map(() => true);

    questions.forEach((q, idx) => {
      const row = document.createElement("div");
      row.className = "ic-nc-q";
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.checked = true;
      cb.addEventListener("change", () => {
        selected[idx] = cb.checked;
      });
      const right = document.createElement("div");
      const stem = document.createElement("div");
      stem.className = "ic-nc-stem";
      stem.textContent = q.stem || "(无题干)";
      const meta = document.createElement("div");
      meta.className = "ic-nc-meta";
      const roles = Array.isArray(q.roles) ? q.roles.join("、") : "";
      const comps = Array.isArray(q.companies) ? q.companies.join("、") : "";
      meta.textContent = [
        q.category_name ? `分类: ${q.category_name}` : "",
        roles ? `岗位: ${roles}` : "",
        comps ? `公司: ${comps}` : "",
        q.difficulty != null ? `难度: ${q.difficulty}` : "",
      ]
        .filter(Boolean)
        .join(" · ");
      right.appendChild(stem);
      if (meta.textContent) right.appendChild(meta);
      row.appendChild(cb);
      row.appendChild(right);
      body.appendChild(row);
    });

    const footer = document.createElement("footer");
    const btnAll = document.createElement("button");
    btnAll.type = "button";
    btnAll.textContent = "全选";
    const btnNone = document.createElement("button");
    btnNone.type = "button";
    btnNone.textContent = "全不选";
    const btnCancel = document.createElement("button");
    btnCancel.type = "button";
    btnCancel.textContent = "取消";
    const btnOk = document.createElement("button");
    btnOk.type = "button";
    btnOk.className = "ic-nc-primary";
    btnOk.textContent = "入库选中项";

    const checkboxes = () => body.querySelectorAll('input[type="checkbox"]');

    btnAll.addEventListener("click", () => {
      checkboxes().forEach((c, i) => {
        c.checked = true;
        selected[i] = true;
      });
    });
    btnNone.addEventListener("click", () => {
      checkboxes().forEach((c, i) => {
        c.checked = false;
        selected[i] = false;
      });
    });
    btnCancel.addEventListener("click", () => closeOverlay(overlay));

    btnOk.addEventListener("click", async () => {
      const picked = questions.filter((_, i) => selected[i]);
      if (!picked.length) {
        toast("请至少选择一道题", true);
        return;
      }
      const payload = {
        questions: picked.map((q) => ({
          stem: String(q.stem || "").trim(),
          category_name: q.category_name,
          roles: Array.isArray(q.roles) ? q.roles : [],
          companies: Array.isArray(q.companies) ? q.companies : [],
          difficulty: typeof q.difficulty === "number" ? q.difficulty : 3,
        })),
      };
      btnOk.disabled = true;
      try {
        const r = await apiPost("/api/import/commit", payload, COMMIT_TIMEOUT_MS);
        toast(`入库完成：新增题目 ${r.created_questions ?? 0} 道`);
        closeOverlay(overlay);
        if (typeof onConfirm === "function") onConfirm();
      } catch (e) {
        toast(String(e.message || e), true);
        btnOk.disabled = false;
      }
    });

    footer.appendChild(btnAll);
    footer.appendChild(btnNone);
    footer.appendChild(btnCancel);
    footer.appendChild(btnOk);
    panel.appendChild(header);
    panel.appendChild(body);
    panel.appendChild(footer);
    overlay.appendChild(panel);
    document.body.appendChild(overlay);
  }

  async function runPreviewWithText(rawText, sourceLabel) {
    const t = String(rawText || "").trim();
    if (t.length < 10) {
      toast("正文过短，无法提取（请确认页面已加载或已登录）", true);
      return;
    }
    toast(`「${sourceLabel}」正在请求 AI 解析…（可能需要 1～2 分钟）`);
    try {
      const data = await apiPost("/api/import/preview", { raw_text: t }, PREVIEW_TIMEOUT_MS);
      const qs = data.questions || [];
      if (!qs.length) {
        toast("未提取到题目", true);
        return;
      }
      openSelectModal(qs);
    } catch (e) {
      toast(String(e.message || e), true);
    }
  }

  async function runFromDiscussUrl(pageUrl, btn) {
    if (btn) btn.disabled = true;
    try {
      const html = await apiGet(pageUrl, 45_000);
      const doc = parseHtmlToDocument(html);
      const text = extractDiscussPlainText(doc);
      await runPreviewWithText(text, pageUrl);
    } catch (e) {
      toast(String(e.message || e), true);
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  function injectPlusAfterLink(anchor, pageUrl) {
    const id = discussIdFromHref(pageUrl);
    if (id) {
      const existing = document.querySelector(`.ic-nc-import-btn[data-ic-discuss-id="${id}"]`);
      if (existing && document.body.contains(existing)) return;
    }
    const next = anchor.nextElementSibling;
    if (next && next.classList.contains("ic-nc-import-btn")) return;

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "ic-nc-import-btn";
    if (id) btn.dataset.icDiscussId = id;
    btn.title = "Interview Collector：AI 提取本题并入库";
    btn.textContent = "+";
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      void runFromDiscussUrl(pageUrl, btn);
    });
    anchor.insertAdjacentElement("afterend", btn);
  }

  function scanInterviewCenterList() {
    if (!location.pathname.includes("/interview/center")) return;

    const anchors = [...document.querySelectorAll('a[href*="/discuss/"]')];
    /** @type {Map<string, HTMLAnchorElement>} */
    const bestById = new Map();

    function scoreAnchor(a) {
      const t = (a.textContent || "").trim().length;
      const inHeading = a.closest("h1,h2,h3,h4,[class*='title'],[class*='Title']");
      return t + (inHeading ? 80 : 0);
    }

    for (const a of anchors) {
      const href = a.getAttribute("href");
      const id = discussIdFromHref(href);
      if (!id) continue;
      const pageUrl = normalizeDiscussUrl(href);
      if (!pageUrl) continue;
      const prev = bestById.get(id);
      if (!prev || scoreAnchor(a) > scoreAnchor(prev)) bestById.set(id, a);
    }

    bestById.forEach((a) => {
      const pageUrl = normalizeDiscussUrl(a.getAttribute("href"));
      if (pageUrl) injectPlusAfterLink(a, pageUrl);
    });
  }

  function injectDiscussPageFab() {
    if (!/\/discuss\/\d+/.test(location.pathname)) return;
    if (document.querySelector(".ic-nc-fab")) return;

    const fab = document.createElement("button");
    fab.type = "button";
    fab.className = "ic-nc-fab";
    fab.title = "Interview Collector：提取当前面经正文";
    fab.textContent = "+";
    fab.addEventListener("click", async () => {
      fab.disabled = true;
      try {
        const text = extractDiscussPlainText(document);
        await runPreviewWithText(text, "当前页");
      } finally {
        fab.disabled = false;
      }
    });
    document.body.appendChild(fab);
  }

  function tick() {
    try {
      scanInterviewCenterList();
      injectDiscussPageFab();
    } catch (e) {
      console.warn("[ic-nc]", e);
    }
  }

  const mo = new MutationObserver(() => {
    window.clearTimeout(mo._t);
    mo._t = window.setTimeout(tick, 400);
  });

  mo.observe(document.documentElement, { childList: true, subtree: true });
  tick();
})();
