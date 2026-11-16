const searchInput = document.getElementById("search");
const regionSelect = document.getElementById("region");
const searchForm = document.getElementById("searchForm");
const searchButton = document.getElementById("searchButton");
const gamesContainer = document.getElementById("games");
let selectedPlatform = "steam";

const providerNames = {
  steam: "Steam", epic: "Epic Games", gog: "GOG",
  instantgaming: "Instant Gaming", g2a: "G2A", xbox: "Xbox", psn: "PlayStation"
};

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, char => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
  })[char]);
}
function showMessage(title, message, error = false) {
  gamesContainer.innerHTML = `<div class="empty-state ${error ? "error-state" : ""}"><h3>${escapeHtml(title)}</h3><p>${escapeHtml(message)}</p></div>`;
}
function formatPrice(item) {
  if (item.price === null || item.price === undefined) return "Preis nicht verfügbar";
  const amount = Number(item.price);
  if (!Number.isFinite(amount)) return `${item.price} ${item.currency || ""}`;
  try {
    return new Intl.NumberFormat("de-DE", { style: "currency", currency: item.currency || "EUR" }).format(amount);
  } catch {
    return `${amount.toFixed(2)} ${item.currency || ""}`;
  }
}
function renderGames(items) {
  if (!items.length) {
    showMessage("Keine Treffer gefunden.", "Versuche einen anderen Suchbegriff oder wähle alle Stores.");
    return;
  }
  gamesContainer.innerHTML = items.map(item => {
    const name = escapeHtml(item.name);
    const image = escapeHtml(item.image || "");
    const provider = item.provider_name || providerNames[item.provider] || item.provider || "Store";
    const discount = Number(item.discount);
    const discountBadge = Number.isFinite(discount) && discount > 0 ? `<span class="deal-badge">-${discount}%</span>` : "";
    const link = /^https:\/\//i.test(item.url || "") ? item.url : "#";
    return `<article class="game-card">
      <div class="game-art">${discountBadge}<img class="game-image" src="${image}" alt="${name}" loading="lazy" onerror="this.style.display='none'"></div>
      <div class="game-info"><div class="store-label">${escapeHtml(provider)}</div><h3 title="${name}">${name}</h3>
        <div class="game-bottom"><span class="game-price">${escapeHtml(formatPrice(item))}</span>
          <a class="game-link" href="${escapeHtml(link)}" target="_blank" rel="noopener noreferrer">VIEW DEAL ↗</a>
        </div>
      </div>
    </article>`;
  }).join("");
}
async function searchGames(event) {
  if (event) event.preventDefault();
  const term = searchInput.value.trim();
  if (!term) {
    showMessage("Ready when you are.", "Gib oben einen Spieletitel ein und starte den Radar.");
    searchInput.focus();
    return;
  }
  searchButton.disabled = true;
  searchButton.innerHTML = "SCANNING …";
  showMessage("Scanning selected store …", `GameRadar sucht bei ${providerNames[selectedPlatform] || 'dem ausgewählten Store'}.`);
  try {
    const params = new URLSearchParams({ term, country: regionSelect.value, platform: selectedPlatform });
    const response = await fetch(`/api/search?${params}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || `Serverfehler (${response.status})`);
    renderGames(data.items || []);
  } catch (error) {
    showMessage("Radar signal lost.", error.message || "Die Suche ist fehlgeschlagen.", true);
  } finally {
    searchButton.disabled = false;
    searchButton.innerHTML = 'SEARCH <span>↗</span>';
  }
}
searchForm.addEventListener("submit", searchGames);
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("/service-worker.js").catch(() => {}));
}


// Account UI: accounts, sessions, favourites and search history are stored server-side.
const accountButton = document.getElementById('accountButton');
const authBackdrop = document.getElementById('authBackdrop');
const authClose = document.getElementById('authClose');
const authForm = document.getElementById('authForm');
const authMessage = document.getElementById('authMessage');
const authTitle = document.getElementById('authTitle');
const authSubmit = document.getElementById('authSubmit');
const usernameInput = document.getElementById('authUsername');
const usernameLabel = document.getElementById('usernameLabel');
let authMode = 'login';
function setAuthMode(mode) {
  authMode = mode;
  document.querySelectorAll('.auth-tab').forEach(b => b.classList.toggle('active', b.dataset.mode === mode));
  const registering = mode === 'register';
  usernameInput.hidden = usernameLabel.hidden = !registering;
  usernameInput.required = registering;
  document.getElementById('authPassword').autocomplete = registering ? 'new-password' : 'current-password';
  authTitle.textContent = registering ? 'Konto erstellen.' : 'Willkommen zurück.';
  authSubmit.textContent = registering ? 'Konto erstellen' : 'Einloggen';
  authMessage.textContent = registering ? 'Mindestens 10 Zeichen beim Passwort.' : '';
}
document.querySelectorAll('.auth-tab').forEach(b => b.addEventListener('click', () => setAuthMode(b.dataset.mode)));
function openAuth() { authBackdrop.hidden = false; authMessage.textContent = ''; }
function closeAuth() { authBackdrop.hidden = true; }
accountButton?.addEventListener('click', () => openAuth());
authClose?.addEventListener('click', closeAuth);
authBackdrop?.addEventListener('click', e => { if (e.target === authBackdrop) closeAuth(); });
async function refreshAccount() {
  try {
    const r = await fetch('/api/me', { credentials: 'same-origin' });
    const d = await r.json();
    if (d.user) {
      accountButton.textContent = `${d.user.username} · ${d.user.role === 'owner' ? 'OWNER' : d.user.tier.toUpperCase()}`;
      accountButton.title = `${d.user.email} · angemeldet`;
      accountButton.onclick = async () => {
        if (!confirm('Möchtest du dich abmelden?')) return;
        await fetch('/api/logout', { method: 'POST', credentials: 'same-origin' });
        location.reload();
      };
    } else {
      accountButton.textContent = 'LOGIN / REGISTER';
      accountButton.onclick = openAuth;
    }
  } catch (_) { accountButton.textContent = 'LOGIN / REGISTER'; }
}
authForm?.addEventListener('submit', async e => {
  e.preventDefault(); authSubmit.disabled = true; authMessage.textContent = 'Bitte warten …';
  const payload = { email: document.getElementById('authEmail').value, password: document.getElementById('authPassword').value };
  if (authMode === 'register') payload.username = usernameInput.value;
  try {
    const r = await fetch(`/api/${authMode === 'register' ? 'register' : 'login'}`, {
      method: 'POST', headers: {'Content-Type':'application/json'}, credentials: 'same-origin', body: JSON.stringify(payload)
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.message || 'Anmeldung fehlgeschlagen.');
    closeAuth(); authForm.reset(); await refreshAccount();
  } catch (err) { authMessage.textContent = err.message; }
  finally { authSubmit.disabled = false; }
});
refreshAccount();


// Platform picker: keeps the existing region and search defaults unchanged.
document.querySelectorAll('[data-platform]').forEach(card => {
  card.addEventListener('click', () => {
    selectedPlatform = card.dataset.platform;
    document.querySelectorAll('[data-platform]').forEach(x => {
      x.classList.toggle('platform-active', x === card);
    });
    const labels = {steam:'STEAM STORE',epic:'EPIC GAMES',gog:'GOG',instantgaming:'INSTANT GAMING',g2a:'G2A',xbox:'XBOX',psn:'PLAYSTATION'};
    const resultLabel = document.querySelector('.results-label');
    if (resultLabel) resultLabel.textContent = labels[selectedPlatform] || 'STORE';
    if (searchInput.value.trim()) searchGames();
    else showMessage('Plattform ausgewählt.', `Suche nach einem Spiel bei ${labels[selectedPlatform] || 'diesem Store'}.`);
  });
});
