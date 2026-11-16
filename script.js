const searchInput = document.getElementById("search");
const regionSelect = document.getElementById("region");
const searchForm = document.getElementById("searchForm");
const searchButton = document.getElementById("searchButton");
const gamesContainer = document.getElementById("games");

function showMessage(title, message, isError = false) {
  gamesContainer.innerHTML = `<div class="empty-state ${isError ? "error-state" : ""}"><h3>${title}</h3><p>${message}</p></div>`;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, char => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
  })[char]);
}

function renderGames(games) {
  if (!Array.isArray(games) || games.length === 0) {
    showMessage("No games found.", "Versuche einen anderen Suchbegriff.");
    return;
  }

  gamesContainer.innerHTML = games.map(game => {
    const name = escapeHtml(game.name);
    const image = escapeHtml(game.tiny_image || "");
    const price = escapeHtml(game.price?.final_formatted || "Preis ansehen");
    const url = `https://store.steampowered.com/app/${encodeURIComponent(game.id)}/`;
    return `<article class="game-card">
      <img class="game-image" src="${image}" alt="${name}" loading="lazy" onerror="this.style.display='none'">
      <div class="game-info"><h3 title="${name}">${name}</h3>
        <div class="game-bottom"><span class="game-price">${price}</span>
          <a class="game-link" href="${url}" target="_blank" rel="noopener noreferrer">VIEW DEAL ↗</a>
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
  showMessage("Scanning the store …", "Der Radar durchsucht gerade Steam.");
  try {
    const params = new URLSearchParams({ term, cc: regionSelect.value });
    const response = await fetch(`/api/search?${params.toString()}`);
    if (!response.ok) throw new Error(`Serverfehler (${response.status})`);
    const data = await response.json();
    renderGames(data);
  } catch (error) {
    showMessage("Radar signal lost.", `${error.message || "Die Suche ist fehlgeschlagen."} Bitte prüfe deine Internetverbindung.`, true);
  } finally {
    searchButton.disabled = false;
    searchButton.innerHTML = 'SEARCH <span>↗</span>';
  }
}

searchForm.addEventListener("submit", searchGames);
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("/service-worker.js").catch(() => {}));
}
