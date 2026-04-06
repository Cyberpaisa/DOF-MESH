/**
 * DOF YouTube — background service worker
 * Polling cada 30s a knowledge_api (localhost:19019/latest)
 * Badge rojo "1" cuando hay pending, vacío cuando no.
 */

const API = "http://127.0.0.1:19019";
const ALARM_NAME = "dof-poll";
const POLL_MINUTES = 0.5; // 30 segundos

// ── Polling ──────────────────────────────────────────────────────────

async function fetchLatest() {
  try {
    const res = await fetch(`${API}/latest`, { signal: AbortSignal.timeout(5000) });
    if (res.status === 404) {
      await clearPending();
      return;
    }
    if (!res.ok) return;
    const report = await res.json();
    await setPending(report);
  } catch (_) {
    // API no disponible — no modificar badge
  }
}

async function setPending(report) {
  await chrome.storage.local.set({ pendingReport: report, lastCheck: Date.now() });
  await chrome.action.setBadgeText({ text: "1" });
  await chrome.action.setBadgeBackgroundColor({ color: "#E53E3E" });

  // Notificación solo si el report cambió
  const prev = await chrome.storage.local.get("lastNotifiedId");
  if (prev.lastNotifiedId !== report.id_aprobacion) {
    chrome.notifications.create(`dof-${report.id_aprobacion}`, {
      type: "basic",
      iconUrl: "icons/icon48.png",
      title: `DOF: ${report.titulo}`,
      message: `Score ${report.score_dof}/100 · ${report.relevancia_dof.toUpperCase()}`,
    });
    await chrome.storage.local.set({ lastNotifiedId: report.id_aprobacion });
  }
}

async function clearPending() {
  await chrome.storage.local.remove("pendingReport");
  await chrome.action.setBadgeText({ text: "" });
}

// ── Approve / Reject (llamados desde popup) ──────────────────────────

async function doAction(action, rid) {
  const res = await fetch(`${API}/${action}/${rid}`, {
    method: "POST",
    signal: AbortSignal.timeout(8000),
  });
  const data = await res.json();
  if (data.status === action + "d" || data.status === "rejected") {
    await clearPending();
  }
  return data;
}

// ── Alarm setup ──────────────────────────────────────────────────────

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === ALARM_NAME) fetchLatest();
});

chrome.runtime.onInstalled.addListener(() => {
  chrome.alarms.create(ALARM_NAME, { periodInMinutes: POLL_MINUTES });
  fetchLatest();
});

chrome.runtime.onStartup.addListener(() => {
  chrome.alarms.create(ALARM_NAME, { periodInMinutes: POLL_MINUTES });
  fetchLatest();
});

// ── Ingest (llamado desde content.js) ───────────────────────────────

async function ingestUrl(url) {
  const res = await fetch(`${API}/ingest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
    signal: AbortSignal.timeout(8000),
  });
  return res.json();
}

// ── Message bridge (popup + content.js → background) ─────────────────

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type === "ACTION") {
    doAction(msg.action, msg.rid)
      .then(sendResponse)
      .catch((e) => sendResponse({ error: e.message }));
    return true; // async
  }
  if (msg.type === "POLL") {
    fetchLatest().then(() => sendResponse({ ok: true }));
    return true;
  }
  if (msg.type === "INGEST") {
    ingestUrl(msg.url)
      .then((data) => sendResponse({ ok: true, data }))
      .catch((e) => sendResponse({ ok: false, error: e.message }));
    return true; // async
  }
});
