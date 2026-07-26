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
    body: JSON.stringify({ topic, source_url: $("job-url").value.trim() || null }),
  });
  if (res.ok) {
    $("job-topic").value = "";
    $("job-url").value = "";
    loadJobs();
  }
});

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

    card.innerHTML = `
      <div class="job-topic">${escapeHtml(job.topic)}</div>
      <div class="job-meta">статус: ${job.status}</div>
      ${isRunning ? `<div class="status-track"><div class="status-fill"></div></div>` : ""}
      ${job.status === "done" ? `<a class="job-download" href="/jobs/${job.id}/download">Скачать видео →</a>` : ""}
      ${job.error ? `<div class="job-error">${escapeHtml(job.error.slice(0, 400))}</div>` : ""}
    `;
    container.appendChild(card);
  }
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

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

  loadJobs();
  clearInterval(state.pollTimer);
  state.pollTimer = setInterval(loadJobs, 4000);
}

boot();
