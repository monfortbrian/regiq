const API = "http://localhost:8000";

const SUGGESTIONS = [
  "What templates must banks submit daily?",
  "Penalty for late data submission",
  "Recovery plan governance requirements",
  "Independent director requirements",
];

const SOON_META = {
  cbk: { body: "Kenya Central Bank corpus is being ingested.\nWant early access or to discuss a deployment?" },
  bou: { body: "Bank of Uganda corpus is being prepared.\nWant early access or to discuss a deployment?" },
  bot: { body: "Bank of Tanzania corpus is being prepared.\nWant early access or to discuss a deployment?" },
  brb: { body: "Banque de la République du Burundi corpus is being prepared.\nWant early access?" },
  bcc: { body: "Banque Centrale du Congo corpus is being prepared.\nWant early access?" },
  cbs: { body: "Central Bank of Somalia corpus is being prepared.\nWant early access?" },
  bss: { body: "Bank of South Sudan corpus is being prepared.\nWant early access?" },
};

let currentJur  = "bnr";
let isLoading   = false;
let hasMessages = false;

const messagesEl  = document.getElementById("messages");
const emptyEl     = document.getElementById("empty");
const soonScreen  = document.getElementById("soon-screen");
const soonFlagImg = document.getElementById("soon-flag-img");
const soonTitle   = document.getElementById("soon-title");
const soonBody    = document.getElementById("soon-body");
const sGridEl     = document.getElementById("s-grid");
const qEl         = document.getElementById("q");
const sendBtn     = document.getElementById("send");
const statusDot   = document.getElementById("status-dot");
const srcDrawer   = document.getElementById("src-drawer");
const drawerClose = document.getElementById("drawer-close");
const drawerTitle = document.getElementById("drawer-title");
const drawerBody  = document.getElementById("drawer-body");
const inputBox    = document.getElementById("input-box");
const greetTitle  = document.getElementById("greeting-title");
const greetBody   = document.getElementById("greeting-body");
const logoWrap    = document.getElementById("logo-wrap");

// ── Logo ──────────────────────────────────────────────────────────────────────
(function () {
  const img = new Image();
  img.onload = () => {
    img.style.cssText = "width:34px;height:34px;object-fit:cover;border-radius:9px;display:block";
    img.alt = "RegIQ";
    logoWrap.innerHTML = "";
    logoWrap.appendChild(img);
  };
  img.onerror = () => {
    logoWrap.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.8" aria-hidden="true">
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
    </svg>`;
  };
  img.src = "icons/icon48.png";
})();

// ── Greeting - single clean line, no duplication ──────────────────────────────
function buildGreeting() {
  const h = new Date().getHours();
  let title, body;

  if (h >= 5 && h < 12) {
    title = "Good morning.";
    body  = "Ask any compliance question about BNR directives.\nI'll give you a precise, cited answer.";
  } else if (h >= 12 && h < 17) {
    title = "Good afternoon.";
    body  = "Ask any compliance question about BNR directives.\nI'll give you a precise, cited answer.";
  } else if (h >= 17 && h < 21) {
    title = "Good evening.";
    body  = "Ask any compliance question about BNR directives.\nI'll give you a precise, cited answer.";
  } else {
    title = "Working late, noted.";
    body  = "Compliance doesn't sleep and neither do you.\nI'm here with cited answers whenever you need them.";
  }

  greetTitle.textContent = title;
  greetBody.textContent  = body;
}

// ── Suggestions ───────────────────────────────────────────────────────────────
function renderSuggestions() {
  sGridEl.innerHTML = "";
  SUGGESTIONS.forEach((text) => {
    const btn = document.createElement("button");
    btn.className = "s-chip";
    btn.setAttribute("role", "listitem");
    btn.setAttribute("aria-label", `Ask: ${text}`);
    btn.innerHTML = `
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
        <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
      </svg>
      ${escHtml(text)}`;
    btn.addEventListener("click", () => submit(text));
    sGridEl.appendChild(btn);
  });
}

// ── Jurisdiction tabs ─────────────────────────────────────────────────────────
document.querySelectorAll(".jur-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".jur-btn").forEach(b => {
      b.classList.remove("active");
      b.setAttribute("aria-selected", "false");
    });
    btn.classList.add("active");
    btn.setAttribute("aria-selected", "true");
    currentJur = btn.dataset.jur;

    if (btn.classList.contains("soon")) {
      showSoon(btn);
    } else {
      hideSoon();
    }
  });
});

function showSoon(btn) {
  const meta = SOON_META[btn.dataset.jur] || {};
  const cc   = btn.dataset.cc || "un";
  const name = btn.dataset.name || btn.dataset.jur.toUpperCase();

  soonFlagImg.src = `https://flagcdn.com/w80/${cc}.png`;
  soonFlagImg.alt = name;
  soonTitle.textContent = name;
  soonBody.textContent  = meta.body || "Coming soon.";

  soonScreen.classList.add("visible");
  emptyEl.style.display = "none";
  document.querySelectorAll(".msg").forEach(m => m.style.display = "none");

  inputBox.classList.add("disabled-jur");
  qEl.disabled = true;
  qEl.placeholder = "Not available yet - select Rwanda · BNR";
  sendBtn.disabled = true;
  sendBtn.setAttribute("aria-disabled", "true");
}

function hideSoon() {
  soonScreen.classList.remove("visible");
  if (!hasMessages) {
    emptyEl.style.display = "flex";
  } else {
    document.querySelectorAll(".msg").forEach(m => m.style.display = "flex");
  }
  inputBox.classList.remove("disabled-jur");
  qEl.disabled = false;
  qEl.placeholder = "Ask any compliance question…";
  updateSendBtn();
}

// ── Health check ─────────────────────────────────────────────────────────────
async function checkHealth() {
  try {
    const r = await fetch(`${API}/health`, { signal: AbortSignal.timeout(3000) });
    const d = await r.json();
    const ok = d.ready;
    statusDot.className = "status-dot" + (ok ? "" : " offline");
    statusDot.setAttribute("aria-label", ok ? "System online" : "System offline");
  } catch {
    statusDot.className = "status-dot offline";
    statusDot.setAttribute("aria-label", "System offline");
  }
}

// ── Source drawer ─────────────────────────────────────────────────────────────
function openDrawer(citation, preview) {
  drawerTitle.textContent = citation;
  drawerBody.textContent  = preview;
  srcDrawer.classList.add("open");
  srcDrawer.setAttribute("aria-hidden", "false");
  drawerClose.focus();
}
function closeDrawer() {
  srcDrawer.classList.remove("open");
  srcDrawer.setAttribute("aria-hidden", "true");
}
drawerClose.addEventListener("click", closeDrawer);
document.addEventListener("click", (e) => {
  if (srcDrawer.classList.contains("open") &&
      !srcDrawer.contains(e.target) &&
      !e.target.closest(".cite-chip"))
    closeDrawer();
});
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeDrawer(); });

// ── Message bubbles ───────────────────────────────────────────────────────────
function appendUser(text) {
  hideEmpty();
  const msg = document.createElement("div");
  msg.className = "msg user";
  msg.setAttribute("role", "article");
  msg.innerHTML = `
    <div class="av-user" aria-hidden="true">
      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#6b7585" stroke-width="2">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
        <circle cx="12" cy="7" r="4"/>
      </svg>
    </div>
    <div class="bbl" role="text">${escHtml(text)}</div>`;
  messagesEl.appendChild(msg);
  scrollBottom();
}

function appendBot() {
  const wrap = document.createElement("div");
  wrap.className = "msg bot";
  wrap.setAttribute("role", "article");
  wrap.setAttribute("aria-label", "RegIQ response");

  const av  = document.createElement("div");
  av.className = "av";
  av.setAttribute("aria-hidden", "true");
  av.textContent = "R";

  const bbl = document.createElement("div");
  bbl.className = "bbl";
  bbl.setAttribute("role", "text");
  bbl.innerHTML = `<div class="dots" aria-label="RegIQ is thinking"><span></span><span></span><span></span></div>`;

  wrap.appendChild(av);
  wrap.appendChild(bbl);
  messagesEl.appendChild(wrap);
  scrollBottom();

  return {
    stream(text) { bbl.innerHTML = `<div>${formatAnswer(text)}</div>`; scrollBottom(); },
    finalize(text, sources) {
      bbl.innerHTML = `<div>${formatAnswer(text)}</div>`;
      if (sources && sources.length) {
        const cites = document.createElement("div");
        cites.className = "cites";
        sources.forEach(src => {
          const chip = document.createElement("button");
          chip.className = "cite-chip";
          chip.setAttribute("aria-label", `View source: ${src.citation}`);
          chip.innerHTML = `<span class="cite-dot" aria-hidden="true"></span>${shortCite(src.citation)}`;
          chip.addEventListener("click", () => openDrawer(src.citation, src.preview));
          cites.appendChild(chip);
        });
        bbl.appendChild(cites);
      }
      scrollBottom();
    },
    error(msg) {
      bbl.innerHTML = `<p style="color:#b91c1c;font-size:12px">${escHtml(msg)}</p>`;
      scrollBottom();
    }
  };
}

// ── Submit ────────────────────────────────────────────────────────────────────
async function submit(text) {
  const q = (text || qEl.value).trim();
  if (!q || isLoading || currentJur !== "bnr") return;

  isLoading = true;
  sendBtn.disabled = true;
  sendBtn.setAttribute("aria-disabled", "true");
  qEl.value = "";
  autoResize();

  appendUser(q);
  const bot = appendBot();
  let fullText = "";

  try {
    const res = await fetch(`${API}/ask/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: q, jurisdiction: currentJur }),
    });
    if (!res.ok) throw new Error(`Server ${res.status}`);

    const reader  = res.body.getReader();
    const decoder = new TextDecoder();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      for (const line of decoder.decode(value).split("\n")) {
        if (!line.startsWith("data: ")) continue;
        try {
          const p = JSON.parse(line.slice(6));
          if (p.token !== undefined) { fullText += p.token; bot.stream(fullText); }
          if (p.done) bot.finalize(fullText, p.sources || []);
        } catch {}
      }
    }
  } catch {
    bot.error("Cannot connect to RegIQ server. Make sure it's running on localhost:8000.");
  } finally {
    isLoading = false;
    updateSendBtn();
    qEl.focus();
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function hideEmpty() {
  if (!hasMessages) { hasMessages = true; emptyEl.style.display = "none"; }
}
function updateSendBtn() {
  const ok = qEl.value.trim().length > 0 && !isLoading && currentJur === "bnr";
  sendBtn.disabled = !ok;
  sendBtn.setAttribute("aria-disabled", String(!ok));
}
function scrollBottom() { messagesEl.scrollTop = messagesEl.scrollHeight; }
function escHtml(s) {
  return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}
function formatAnswer(text) {
  return text
    .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
    .replace(/\*\*(.*?)\*\*/g,"<strong>$1</strong>")
    .replace(/\n\n/g,"</p><p>").replace(/\n/g,"<br>")
    .replace(/^/,"<p>").replace(/$/, "</p>");
}
function shortCite(c) {
  const m = c.match(/Directive\s+(No\.\s*[\w/]+)/i);
  if (m) return m[1];
  const a = c.match(/Article\s+\d+/i);
  return a ? a[0] : c.slice(0, 28);
}
function autoResize() {
  qEl.style.height = "auto";
  qEl.style.height = Math.min(qEl.scrollHeight, 90) + "px";
}

// ── Input listeners ───────────────────────────────────────────────────────────
qEl.addEventListener("input", () => { autoResize(); updateSendBtn(); });
qEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); }
});
sendBtn.addEventListener("click", () => submit());

// ── Init ──────────────────────────────────────────────────────────────────────
buildGreeting();
renderSuggestions();
checkHealth();
setInterval(checkHealth, 30000);