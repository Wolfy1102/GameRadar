const CACHE_NAME = "steam-deal-radar-v1";

const FILES_TO_CACHE = [
  "/",
    "/index.html",
      "/style.css",
        "/script.js",
          "/manifest.webmanifest",
            "/icon.svg"
            ];

            // App-Dateien beim Installieren speichern
            self.addEventListener("install", (event) => {
              event.waitUntil(
                  caches.open(CACHE_NAME).then((cache) => {
                        return cache.addAll(FILES_TO_CACHE);
                            })
                              );

                                self.skipWaiting();
                                });

                                // Alte Cache-Versionen entfernen
                                self.addEventListener("activate", (event) => {
                                  event.waitUntil(
                                      caches.keys().then((keys) =>
                                            Promise.all(
                                                    keys
                                                              .filter((key) => key !== CACHE_NAME)
                                                                        .map((key) => caches.delete(key))
                                                                              )
                                                                                  )
                                                                                    );

                                                                                      self.clients.claim();
                                                                                      });

                                                                                      // Dateien aus dem Cache laden, wenn möglich
                                                                                      self.addEventListener("fetch", (event) => {
                                                                                        const url = new URL(event.request.url);

                                                                                          // Steam-Suchanfragen immer direkt übers Netzwerk laden
                                                                                            if (url.pathname.startsWith("/api/")) {
                                                                                                return;
                                                                                                  }

                                                                                                    if (event.request.method !== "GET") {
                                                                                                        return;
                                                                                                          }

                                                                                                            event.respondWith(
                                                                                                                fetch(event.request)
                                                                                                                      .then((response) => {
                                                                                                                              if (response.ok && url.origin === self.location.origin) {
                                                                                                                                        const copy = response.clone();
                                                                                                                                                  caches.open(CACHE_NAME).then((cache) => {
                                                                                                                                                              cache.put(event.request, copy);
                                                                                                                                                                        });
                                                                                                                                                                                }
                                                                                                                                                                                        return response;
                                                                                                                                                                                              })
                                                                                                                                                                                                    .catch(() => caches.match(event.request))
                                                                                                                                                                                                      );
                                                                                                                                                                                                      });
