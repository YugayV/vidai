const state = { token: localStorage.getItem("token") || null, me: null, pollTimer: null };

const $ = (id) => document.getElementById(id);

function authHeaders() {
  return { Authorization: `Bearer ${state.token}` };
}

// ---------- Tabs ----------
document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    $(btn.dataset.tab + "-form").classList.add("active");
  });
});

// ---------- Auth ----------
$("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  $("login-error").textContent = "";
  const body = new URLSearchParams({
    username: $("login-email").value,
    password: $("login-password").value,
  });
  const res = await fetch("/auth/login", { method: "POST", body });
  const data = await res.json();
  if (!res.ok) return ($("login-error").textContent = data.detail || "Ошибка входа");
  state.token = data.access_token;
  localStorage.setItem("token", state.token);
  boot();
});

$("register-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  $("reg-error").textContent = "";
  const res = await fetch("/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: $("reg-email").value,
      password: $("reg-password").value,
      invite_code: $("reg-invite").value,
    }),
  });
  const data = await res.json();
  if (!res.ok) return ($("reg-error").textContent = data.detail || "Ошибка регистрации");
  state.token = data.access_token;
  localStorage.setItem("token", state.token);
  boot();
});

// ---------- Google ----------
async function handleGoogleCredential(response) {
  $("oauth-error").textContent = "";
  const invite = $("oauth-invite").value.trim();
  const res = await fetch("/auth/google", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id_token: response.credential, invite_code: invite }),
  });
  const data = await res.json();
  if (!res.ok) return ($("oauth-error").textContent = data.detail || "Ошибка входа через Google");
  state.token = data.access_token;
  localStorage.setItem("token", state.token);
  boot();
}

// ---------- Telegram ----------
window.onTelegramAuth = async function (tgUser) {
  $("oauth-error").textContent = "";
  const invite = $("oauth-invite").value.trim();
  const res = await fetch("/auth/telegram", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...tgUser, invite_code: invite }),
  });
  const data = await res.json();
  if (!res.ok) return ($("oauth-error").textContent = data.detail || "Ошибка входа через Telegram");
  state.token = data.access_token;
  localStorage.setItem("token", state.token);
  boot();
};

async function initOAuthButtons() {
  const res = await fetch("/config");
  const cfg = await res.json();

  if (cfg.google_client_id && window.google?.accounts?.id) {
    google.accounts.id.initialize({
      client_id: cfg.google_client_id,
      callback: handleGoogleCredential,
    });
    google.accounts.id.renderButton($("google-btn-container"), {
      theme: "outline",
      size: "large",
      width: 280,
    });
  }

  if (cfg.telegram_bot_username) {
    const script = document.createElement("script");
    script.src = "https://telegram.org/js/telegram-widget.js?22";
    script.setAttribute("data-telegram-login", cfg.telegram_bot_username);
    script.setAttribute("data-size", "large");
    script.setAttribute("data-onauth", "onTelegramAuth(user)");
    script.setAttribute("data-request-access", "write");
    script.async = true;
    $("telegram-btn-container").appendChild(script);
  }
}

$("logout-btn").addEventListener("click", () => {
  localStorage.removeItem("token");
  state.token = null;
  clearInterval(state.pollTimer);
  $("dashboard-screen").classList.add("hidden");
  $("user-badge").classList.add("hidden");
  $("auth-screen").classList.remove("hidden");
});

// ---------- Subscribe ----------
$("subscribe-btn").addEventListener("click", async () => {
  const res = await fetch("/billing/checkout", { method: "POST", headers: authHeaders() });
  const data = await res.json();
  if (data.checkout_url) window.location.href = data.checkout_url;
});

// ---------- Jobs ----------
$("create-job-btn").addEventListener("click", async () => {
  const topic = $("job-topic").value.trim();
  if (!topic) return;
  const res = await fetch("/jobs", {
    method: "POST",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify({
      topic,
      source_url: $("job-url").value.trim() || null,
      aspect_ratio: $("job-aspect").value,
    }),
  });
  if (res.ok) {
    $("job-topic").value = "";
    $("job-url").value = "";
    loadJobs();
  }
});

const STEP_ORDER = [
  { key: "queued", label: "Очередь" },
  { key: "script", label: "Сценарий" },
  { key: "images", label: "Кадры" },
  { key: "video", label: "Видео" },
  { key: "voice", label: "Озвучка" },
  { key: "assembling", label: "Сборка" },
  { key: "done", label: "Готово" },
];

function renderStepper(status) {
  const baseStatus = status.split(":")[0]; // "images:2/5" -> "images"
  const currentIdx = STEP_ORDER.findIndex((s) => s.key === baseStatus);
  return `<div class="stepper">${STEP_ORDER.map((s, i) => {
    let cls = "step";
    if (i < currentIdx) cls += " done";
    else if (i === currentIdx) cls += " active";
    return `<div class="${cls}"><div class="step-dot"></div><div class="step-label">${s.label}</div></div>`;
  }).join("")}</div>`;
}

async function loadJobs() {
  const res = await fetch("/jobs", { headers: authHeaders() });
  if (!res.ok) return;
  const jobs = await res.json();
  const container = $("jobs-container");
  container.innerHTML = "";

  if (jobs.length === 0) {
    container.innerHTML = `<p style="color:var(--text-dim); font-size:14px;">Пока пусто. Запусти первый ролик выше.</p>`;
    return;
  }

  for (const job of jobs) {
    const card = document.createElement("div");
    card.className = "job-card";
    const isRunning = !["done", "error"].includes(job.status);
    const publicUrl = job.share_token
      ? `${window.location.origin}/jobs/${job.id}/public/${job.share_token}`
      : null;

    card.innerHTML = `
      <div class="job-topic">${escapeHtml(job.topic)}</div>
      <div class="job-meta">${job.aspect_ratio || "9:16"} · статус: ${job.status}</div>
      ${isRunning ? renderStepper(job.status) : ""}
      ${job.status === "done" ? `
        ${publicUrl ? `<video class="job-preview" src="${publicUrl}" controls preload="metadata"></video>` : ""}
        <div class="job-actions">
          <a class="job-download" href="/jobs/${job.id}/download">Скачать видео →</a>
          <button class="ghost-btn copy-link-btn" data-url="${publicUrl}">Скопировать ссылку</button>
          <button class="ghost-btn toggle-clip-btn">Нарезать клип</button>
        </div>
        <div class="clip-row hidden">
          <input type="number" class="clip-start" placeholder="от, сек" min="0" step="0.5" />
          <input type="number" class="clip-end" placeholder="до, сек" min="0" step="0.5" />
          <button class="ghost-btn do-clip-btn" data-job-id="${job.id}">Скачать клип</button>
          <span class="clip-status"></span>
        </div>
      ` : ""}
      ${job.error ? `<div class="job-error">${escapeHtml(job.error.slice(0, 400))}</div>` : ""}
    `;
    container.appendChild(card);
  }

  container.querySelectorAll(".copy-link-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await navigator.clipboard.writeText(btn.dataset.url);
      const original = btn.textContent;
      btn.textContent = "Скопировано ✓";
      setTimeout(() => (btn.textContent = original), 1500);
    });
  });

  container.querySelectorAll(".toggle-clip-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      btn.closest(".job-card").querySelector(".clip-row").classList.toggle("hidden");
    });
  });

  container.querySelectorAll(".do-clip-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const card = btn.closest(".job-card");
      const start = parseFloat(card.querySelector(".clip-start").value);
      const end = parseFloat(card.querySelector(".clip-end").value);
      const statusEl = card.querySelector(".clip-status");

      if (isNaN(start) || isNaN(end) || end <= start) {
        statusEl.textContent = "Укажи корректный диапазон";
        return;
      }

      statusEl.textContent = "Режу...";
      btn.disabled = true;
      try {
        const res = await fetch(`/jobs/${btn.dataset.jobId}/clip`, {
          method: "POST",
          headers: { ...authHeaders(), "Content-Type": "application/json" },
          body: JSON.stringify({ start_sec: start, end_sec: end }),
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          statusEl.textContent = err.detail || "Ошибка нарезки";
          return;
        }
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `clip_${btn.dataset.jobId}.mp4`;
        a.click();
        URL.revokeObjectURL(url);
        statusEl.textContent = "Готово ✓";
      } catch {
        statusEl.textContent = "Ошибка сети";
      } finally {
        btn.disabled = false;
      }
    });
  });
}

function statCard(value, label, tone = "") {
  return `<div class="stat-card"><div class="stat-value ${tone}">${value}</div><div class="stat-label">${label}</div></div>`;
}

function renderTimeline(container, timeline) {
  container.innerHTML = "";
  const max = Math.max(1, ...timeline.map((d) => d.count));
  for (const point of timeline) {
    const bar = document.createElement("div");
    bar.className = "chart-bar";
    bar.style.height = `${Math.max(4, (point.count / max) * 100)}%`;
    bar.title = `${point.date}: ${point.count}`;
    container.appendChild(bar);
  }
}

async function loadMyAnalytics() {
  const res = await fetch("/analytics/me", { headers: authHeaders() });
  if (!res.ok) return;
  const a = await res.json();

  $("my-stats").innerHTML = [
    statCard(a.total, "всего роликов"),
    statCard(a.done, "готово", "success"),
    statCard(a.in_progress, "в процессе", "ember"),
    statCard(a.error, "с ошибкой", "danger"),
    statCard(a.avg_duration_sec ? `${Math.round(a.avg_duration_sec)}с` : "—", "средняя генерация"),
  ].join("");

  renderTimeline($("my-timeline"), a.timeline);
}

async function loadAdminAnalytics() {
  const res = await fetch("/analytics/overview", { headers: authHeaders() });
  if (!res.ok) return;
  const a = await res.json();

  $("admin-stats").innerHTML = [
    statCard(a.total_users, "пользователей"),
    statCard(a.active_subscriptions, "активных подписок", "success"),
    statCard(a.total_jobs, "всего роликов"),
    statCard(a.done, "готово", "success"),
    statCard(a.error, "с ошибкой", "danger"),
    statCard(a.avg_duration_sec ? `${Math.round(a.avg_duration_sec)}с` : "—", "средняя генерация"),
  ].join("");

  renderTimeline($("admin-timeline"), a.timeline);
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// ---------- Admin ----------
async function loadAdminPanel() {
  const res = await fetch("/admin/users", { headers: authHeaders() });
  if (!res.ok) return;
  const users = await res.json();
  const container = $("admin-users-container");
  container.innerHTML = "";

  for (const u of users) {
    const row = document.createElement("div");
    row.className = "admin-row";
    const statusLabel = u.is_admin ? "админ" : u.subscription_status;
    row.innerHTML = `
      <div>
        <div class="admin-row-email">${escapeHtml(u.email)}</div>
        <div class="job-meta">${escapeHtml(u.auth_provider)} · ${escapeHtml(statusLabel)}</div>
      </div>
      <div class="admin-row-actions"></div>
    `;
    const actions = row.querySelector(".admin-row-actions");

    if (!u.is_admin) {
      const grantBtn = document.createElement("button");
      grantBtn.className = "ghost-btn";
      grantBtn.textContent = "Выдать доступ";
      grantBtn.onclick = async () => {
        await fetch(`/admin/users/${u.id}/grant`, { method: "POST", headers: authHeaders() });
        loadAdminPanel();
      };

      const revokeBtn = document.createElement("button");
      revokeBtn.className = "ghost-btn";
      revokeBtn.textContent = "Забрать доступ";
      revokeBtn.onclick = async () => {
        await fetch(`/admin/users/${u.id}/revoke`, { method: "POST", headers: authHeaders() });
        loadAdminPanel();
      };

      actions.append(grantBtn, revokeBtn);
    }

    container.appendChild(row);
  }
}

// ---------- AI-ассистент ----------
let assistantHistory = [];

function renderAssistantLog() {
  const log = $("assistant-log");
  log.innerHTML = assistantHistory.map((m) => `
    <div class="chat-msg chat-${m.role}">
      <div class="chat-bubble">${escapeHtml(m.content)}</div>
      ${m.role === "assistant" ? `<button class="ghost-btn use-topic-btn" data-text="${escapeHtml(extractTopic(m.content))}">Вставить в тему</button>` : ""}
    </div>
  `).join("");
  log.scrollTop = log.scrollHeight;

  log.querySelectorAll(".use-topic-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      $("job-topic").value = btn.dataset.text;
      $("job-topic").scrollIntoView({ behavior: "smooth", block: "center" });
    });
  });
}

function extractTopic(text) {
  const match = text.match(/ТЕМА:\s*(.+)/i);
  return match ? match[1].trim() : text.trim();
}

async function sendAssistantMessage() {
  const input = $("assistant-input");
  const text = input.value.trim();
  if (!text) return;

  assistantHistory.push({ role: "user", content: text });
  renderAssistantLog();
  input.value = "";

  const sendBtn = $("assistant-send-btn");
  sendBtn.disabled = true;
  sendBtn.textContent = "Думаю...";

  try {
    const res = await fetch("/assistant/chat", {
      method: "POST",
      headers: { ...authHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify({ messages: assistantHistory }),
    });
    const data = await res.json();
    if (!res.ok) {
      assistantHistory.push({ role: "assistant", content: data.detail || "Ошибка ассистента" });
    } else {
      assistantHistory.push({ role: "assistant", content: data.reply });
    }
  } catch {
    assistantHistory.push({ role: "assistant", content: "Не получилось связаться с сервером" });
  } finally {
    sendBtn.disabled = false;
    sendBtn.textContent = "Спросить";
    renderAssistantLog();
  }
}

$("assistant-send-btn").addEventListener("click", sendAssistantMessage);
$("assistant-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendAssistantMessage();
});

// ---------- Boot ----------
async function boot() {
  if (!state.token) {
    $("auth-screen").classList.remove("hidden");
    $("dashboard-screen").classList.add("hidden");
    $("user-badge").classList.add("hidden");
    return;
  }

  const res = await fetch("/auth/me", { headers: authHeaders() });
  if (!res.ok) {
    localStorage.removeItem("token");
    state.token = null;
    return boot();
  }
  state.me = await res.json();

  $("auth-screen").classList.add("hidden");
  $("dashboard-screen").classList.remove("hidden");
  $("user-badge").classList.remove("hidden");
  $("user-email").textContent = state.me.email;

  const pill = $("sub-pill");
  pill.textContent = state.me.has_active_subscription ? "активна" : "нет подписки";
  pill.className = "pill " + (state.me.has_active_subscription ? "active" : "inactive");

  $("paywall").classList.toggle("hidden", state.me.has_active_subscription);
  $("create-job-btn").disabled = !state.me.has_active_subscription;

  $("admin-panel").classList.toggle("hidden", !state.me.is_admin);
  if (state.me.is_admin) {
    loadAdminPanel();
    loadAdminAnalytics();
  }

  loadJobs();
  loadMyAnalytics();
  clearInterval(state.pollTimer);
  state.pollTimer = setInterval(() => {
    loadJobs();
    loadMyAnalytics();
    if (state.me.is_admin) loadAdminAnalytics();
  }, 4000);
}

initOAuthButtons();
boot();
