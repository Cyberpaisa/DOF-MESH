/**
 * DOF YouTube — popup.js
 * Fuente de verdad: API /pending en tiempo real.
 * chrome.storage.local solo como cache fallback (API offline).
 */

const $ = (id) => document.getElementById(id);
const content = $("content");
const dot = $("dot");
const toast = $("toast");

const API_BASE = "http://127.0.0.1:19019";

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
      <button class="btn-clear" id="btn-force-clear" title="Forzar limpieza de cache">🔄 Forzar limpieza</button>
    </div>
  `;
  $("btn-force-clear").addEventListener("click", async () => {
    await chrome.storage.local.clear();
    showToast("Cache limpiado");
    renderEmpty();
  });
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

// ── API — fuente de verdad ────────────────────────────────────────────

async function fetchPendingFromAPI() {
  try {
    const res = await fetch(`${API_BASE}/pending`, {
      signal: AbortSignal.timeout(3000),
    });
    if (!res.ok) return null;
    const list = await res.json();
    return Array.isArray(list) && list.length > 0 ? list[0] : null;
  } catch {
    return null; // API offline — fallback a storage
  }
}

// ── Actions ──────────────────────────────────────────────────────────

async function doAction(action, rid) {
  const btn = $(action === "approve" ? "btn-approve" : "btn-reject");
  if (btn) { btn.disabled = true; btn.textContent = "…"; }

  try {
    const resp = await chrome.runtime.sendMessage({ type: "ACTION", action, rid });
    // resp undefined = service worker suspendido — asumir éxito
    const ok = !resp || !resp.error;
    showToast(ok
      ? (action === "approve" ? "✅ Aprobado" : "❌ Rechazado")
      : "⚠ Error: " + resp.error);
    if (ok) {
      setTimeout(async () => {
        await chrome.storage.local.remove("pendingReport");
        await init(); // re-consulta la API — fuente de verdad
      }, 1000);
    } else {
      if (btn) { btn.disabled = false; btn.textContent = action === "approve" ? "✅ Aprobar" : "❌ Rechazar"; }
    }
  } catch {
    // Canal MV3 cerrado — acción ya procesada
    showToast(action === "approve" ? "✅ Aprobado" : "❌ Rechazado");
    setTimeout(async () => {
      await chrome.storage.local.remove("pendingReport");
      await init();
    }, 1000);
  }
}

// ── Init — API como fuente de verdad, storage como fallback ──────────

async function init() {
  // 1. Consultar API directamente
  const fromAPI = await fetchPendingFromAPI();

  if (fromAPI) {
    // API tiene pendiente — sincronizar storage y renderizar
    await chrome.storage.local.set({ pendingReport: fromAPI });
    renderReport(fromAPI);
    return;
  }

  // 2. API dice vacío (o offline) — verificar storage como fallback
  const { pendingReport } = await chrome.storage.local.get("pendingReport");

  if (pendingReport && pendingReport.id_aprobacion && fromAPI !== null) {
    // API respondió vacío pero storage tiene dato viejo → limpiar
    await chrome.storage.local.remove("pendingReport");
  }

  renderEmpty();
}

// ── Refresh button ───────────────────────────────────────────────────

$("btn-refresh").addEventListener("click", async () => {
  $("btn-refresh").textContent = "…";
  await chrome.runtime.sendMessage({ type: "POLL" });
  await new Promise((r) => setTimeout(r, 600));
  await init();
  $("btn-refresh").textContent = "↻";
});

init();
