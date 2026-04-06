/**
 * DOF YouTube — content script
 * Se inyecta en youtube.com/watch?v=*
 * Agrega botón "⚡ DOF" junto a los controles del video.
 * Al hacer clic, envía la URL actual a knowledge_api (:19019)
 * vía background (ya que el content script no puede hacer fetch
 * a localhost por restricciones de CORS/CSP en YouTube).
 */

const DOF_BTN_ID = "dof-ingest-btn";
const DOF_STYLE_ID = "dof-style";
const API = "http://127.0.0.1:19019";

// ── Styles ────────────────────────────────────────────────────────────

function injectStyles() {
  if (document.getElementById(DOF_STYLE_ID)) return;
  const style = document.createElement("style");
  style.id = DOF_STYLE_ID;
  style.textContent = `
    #${DOF_BTN_ID} {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: #0052FF;
      color: #fff;
      border: none;
      border-radius: 18px;
      padding: 6px 14px;
      font-family: "YouTube Sans", "Roboto", sans-serif;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      margin-left: 8px;
      transition: background 0.15s, transform 0.1s;
      vertical-align: middle;
      flex-shrink: 0;
    }
    #${DOF_BTN_ID}:hover  { background: #003ecc; }
    #${DOF_BTN_ID}:active { transform: scale(0.96); }
    #${DOF_BTN_ID}.loading { background: #555; cursor: wait; }
    #${DOF_BTN_ID}.success { background: #00802b; }
    #${DOF_BTN_ID}.error   { background: #CC3300; }
  `;
  document.head.appendChild(style);
}

// ── Button ────────────────────────────────────────────────────────────

function createButton() {
  const btn = document.createElement("button");
  btn.id = DOF_BTN_ID;
  btn.innerHTML = "⚡ DOF";
  btn.title = "Ingestar en DOF Knowledge Pipeline";
  btn.addEventListener("click", handleClick);
  return btn;
}

function setButtonState(state, label) {
  const btn = document.getElementById(DOF_BTN_ID);
  if (!btn) return;
  btn.className = state;
  btn.innerHTML = label;
  if (state === "success" || state === "error") {
    setTimeout(() => {
      btn.className = "";
      btn.innerHTML = "⚡ DOF";
    }, 3000);
  }
}

// ── Inject into YouTube DOM ───────────────────────────────────────────

/**
 * YouTube SPA — el DOM cambia en cada navegación.
 * Buscamos el contenedor de botones de acción del video
 * (#actions, ytd-menu-renderer, etc.) y inyectamos ahí.
 */
function injectButton() {
  if (document.getElementById(DOF_BTN_ID)) return; // ya inyectado

  // Sólo en páginas /watch
  if (!location.pathname.startsWith("/watch")) return;

  // Selector: barra de acciones principal del video
  const selectors = [
    "ytd-watch-metadata #actions",
    "#actions.ytd-watch-metadata",
    "ytd-video-primary-info-renderer #top-level-buttons-computed",
    "#top-level-buttons-computed",
  ];

  let container = null;
  for (const sel of selectors) {
    container = document.querySelector(sel);
    if (container) break;
  }

  if (!container) return; // aún no renderizado

  const btn = createButton();
  container.appendChild(btn);
}

// ── Click handler ─────────────────────────────────────────────────────

async function handleClick() {
  const url = location.href;
  const videoId = new URLSearchParams(location.search).get("v");
  if (!videoId) {
    setButtonState("error", "⚠ Sin video ID");
    return;
  }

  setButtonState("loading", "⏳ Ingesting…");

  // Enviar al background para que haga el fetch (evita restricciones CSP)
  chrome.runtime.sendMessage(
    { type: "INGEST", url, videoId },
    (response) => {
      if (chrome.runtime.lastError || !response) {
        setButtonState("error", "⚠ API offline");
        return;
      }
      if (response.ok) {
        setButtonState("success", "✓ Encolado");
      } else {
        setButtonState("error", "⚠ " + (response.error || "Error"));
      }
    }
  );
}

// ── Observer — YouTube SPA navigation ────────────────────────────────

injectStyles();

// Intento inmediato
injectButton();

// Observar cambios del DOM para SPAs (navegación sin recarga)
const observer = new MutationObserver(() => {
  injectButton();
});

observer.observe(document.body, {
  childList: true,
  subtree: true,
});

// Escuchar mensajes del background (por si cambia la URL)
chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === "NAV") {
    // Pequeño delay para que YouTube termine de renderizar
    setTimeout(injectButton, 800);
  }
});
