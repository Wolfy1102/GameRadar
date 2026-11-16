const searchInput = document.getElementById("search");
const regionSelect = document.getElementById("region");
const searchButton = document.getElementById("searchButton");
const gamesContainer = document.getElementById("games");

async function searchGames() {
    const query = searchInput.value.trim();
    const region = regionSelect.value;

    if (!query) {
        gamesContainer.innerHTML = "<p>Bitte gib einen Spielnamen ein.</p>";
        return;
    }

    gamesContainer.innerHTML = "<p>🔍 Suche nach Steam-Angeboten...</p>";
    searchButton.disabled = true;

    try {
        const url = `/api/search?term=${encodeURIComponent(query)}&cc=${region}`;

        const response = await fetch(url);

        if (!response.ok) {
            throw new Error("Steam ist momentan nicht erreichbar.");
        }

        const data = await response.json();

        if (!data.items || data.items.length === 0) {
            gamesContainer.innerHTML = "<p>Keine Spiele gefunden.</p>";
            return;
        }

        gamesContainer.innerHTML = "";

        data.items.forEach(game => {
            const card = document.createElement("article");
            card.className = "game-card";

            const image = document.createElement("img");
            image.src = game.tiny_image || "";
            image.alt = game.name;

            const info = document.createElement("div");
            info.className = "game-info";

            const title = document.createElement("h3");
            title.textContent = game.name;

            const price = document.createElement("p");
            price.className = "price";
            price.textContent = game.price
                ? game.price.final_formatted
                : "Preis nicht verfügbar";

            const link = document.createElement("a");
            link.href = `https://store.steampowered.com/app/${game.id}/`;
            link.target = "_blank";
            link.rel = "noopener noreferrer";
            link.textContent = "Auf Steam ansehen";

            info.append(title, price, link);
            card.append(image, info);
            gamesContainer.append(card);
        });

    } catch (error) {
        gamesContainer.textContent =
            "Fehler beim Laden. Öffne die Seite über einen lokalen Webserver und versuche es erneut.";
        console.error(error);
    } finally {
        searchButton.disabled = false;
    }
}

searchButton.addEventListener("click", searchGames);

searchInput.addEventListener("keydown", event => {
    if (event.key === "Enter") {
        searchGames();
    }
});
