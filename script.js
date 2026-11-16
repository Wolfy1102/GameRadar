const searchInput = document.getElementById("search");
const regionSelect = document.getElementById("region");
const searchForm = document.getElementById("searchForm");
const searchButton = document.getElementById("searchButton");
const gamesContainer = document.getElementById("games");

const providerNames = {
  steam: "Steam", epic: "Epic Games", gog: "GOG", xbox: "Xbox",
  psn: "PlayStation", nintendo: "Nintendo", ea: "EA app",
  ubisoft: "Ubisoft", bnet: "Battle.net"
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
  showMessage("Scanning all stores …", "GameRadar vergleicht verfügbare Angebote.");
  try {
    const params = new URLSearchParams({ term, country: regionSelect.value });
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
