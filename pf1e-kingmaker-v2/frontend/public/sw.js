const CACHE_VERSION = "pf1e-v2-shell-v2";
const SHELL_ASSETS = [
  "/",
  "/index.html",
  "/manifest.webmanifest",
  "/icon.svg",
  "/icon-192.svg",
  "/icon-512.svg",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_VERSION).then((cache) => cache.addAll(SHELL_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_VERSION)
          .map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

async function cacheFirst(request) {
  const cache = await caches.open(CACHE_VERSION);
  const cached = await cache.match(request);
  if (cached) {
    return cached;
  }

  const response = await fetch(request);
  if (response && response.ok && new URL(request.url).origin === self.location.origin) {
    cache.put(request, response.clone());
  }
  return response;
}

async function networkThenCache(request) {
  const cache = await caches.open(CACHE_VERSION);
  try {
    const response = await fetch(request);
    if (response && response.ok && new URL(request.url).origin === self.location.origin) {
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await cache.match(request);
    if (cached) {
      return cached;
    }
    return caches.match("/index.html");
  }
}

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") {
    return;
  }

  const requestUrl = new URL(event.request.url);
  if (requestUrl.origin !== self.location.origin) {
    return;
  }

  if (event.request.mode === "navigate") {
    event.respondWith(networkThenCache(event.request));
    return;
  }

  const destination = event.request.destination;
  if (destination === "script" || destination === "style" || destination === "font" || destination === "image") {
    event.respondWith(cacheFirst(event.request));
    return;
  }

  event.respondWith(networkThenCache(event.request));
});
