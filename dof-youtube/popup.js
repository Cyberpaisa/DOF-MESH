/**
 * DOF YouTube — popup.js
 * Lee pendingReport de chrome.storage.local y renderiza la UI.
 * Approve/Reject → chrome.runtime.sendMessage → background → knowledge_api
 */

const $ = (id) => document.getElementById(id);
const content = $("content");
const dot = $("dot");
const toast = $("toast");

// ── Toast ────────────────────────────────────────────────────────────

let toastTimer;
function showToast(msg) {
  toast.textContent = msg;
  toast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("show"), 2500);
}

// ── Render ───────────────────────────────────────────────────────────

function relevanceClass(rel) {
  return ["alta", "media", "baja"].includes(rel) ? rel : "baja";
}

function esc(str) {
  const d = document.createElement("div");
  d.textContent = str;
  return d.innerHTML;
}

function renderEmpty() {
  dot.classList.add("offline");
  content.innerHTML = `
    <div class="empty">
      <div class="empty-icon">📭</div>
      <div class="empty-text">Sin videos pendientes.<br>El pipeline avisará cuando haya uno.</div>
    </div>
  `;
}

function renderReport(report) {
  dot.classList.remove("offline");
  const rel = relevanceClass(report.relevancia_dof || "baja");
  const ideas = (report.ideas_clave || [])
    .map((i) => `<li>${esc(i)}</li>`)
    .join("");
  const techs = (report.tecnologias || [])
    .map((t) => `<span class="tech-tag">${esc(t)}</span>`)
    .join("");

  content.innerHTML = `
    <div class="card">
      <div class="score-row">
        <span class="score-badge ${rel}">${rel.toUpperCase()}</span>
        <span class="score-num">Score ${report.score_dof || 0}/100</span>
      </div>
      <div class="titulo">${esc(report.titulo || "Sin título")}</div>
      <a class="url" href="${esc(report.url_video || "#")}" target="_blank">
        ${esc(report.url_video || "")}
      </a>
      <div class="section-label">Ideas clave</div>
      <ul class="ideas">${ideas}</ul>
      <div class="section-label">Tecnologías</div>
      <div class="techs">${techs}</div>
      <hr>
      <div class="actions">
        <button class="btn btn-approve" id="btn-approve">✅ Aprobar</button>
        <button class="btn btn-reject"  id="btn-reject">❌ Rechazar</button>
      </div>
      <div class="rid">ID: ${esc(report.id_aprobacion || "")}</div>
    </div>
  `;

  const rid = report.id_aprobacion;

  $("btn-approve").addEventListener("click", () => doAction("approve", rid));
  $("btn-reject").addEventListener("click", ()  => doAction("reject",  rid));
}

// ── Actions ──────────────────────────────────────────────────────────

async function doAction(action, rid) {
  const btn = $(action === "approve" ? "btn-approve" : "btn-reject");
  if (btn) { btn.disabled = true; btn.textContent = "…"; }

  const resp = await chrome.runtime.sendMessage({ type: "ACTION", action, rid });

  if (resp && !resp.error) {
    showToast(action === "approve" ? "✅ Aprobado" : "❌ Rechazado");
    setTimeout(() => {
      chrome.storage.local.remove("pendingReport");
      renderEmpty();
    }, 1200);
  } else {
    showToast("⚠ Error: " + (resp?.error || "desconocido"));
    if (btn) { btn.disabled = false; btn.textContent = action === "approve" ? "✅ Aprobar" : "❌ Rechazar"; }
  }
}

// ── Init ─────────────────────────────────────────────────────────────

async function init() {
  const { pendingReport } = await chrome.storage.local.get("pendingReport");
  if (pendingReport && pendingReport.id_aprobacion) {
    renderReport(pendingReport);
  } else {
    renderEmpty();
  }
}

$("btn-refresh").addEventListener("click", async () => {
  $("btn-refresh").textContent = "…";
  await chrome.runtime.sendMessage({ type: "POLL" });
  await new Promise((r) => setTimeout(r, 600));
  await init();
  $("btn-refresh").textContent = "↻";
});

init();
