const CACHE_NAME = 'nova-ai-shell-v1';
const SHELL_ASSETS = [
  './app.css',
  './app.js',
  './widget.css',
  './widget.js',
  './manifest.json'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[SW] Caching shell assets');
      const promises = SHELL_ASSETS.map((asset) => {
        return fetch(asset)
          .then((response) => {
            if (!response.ok) {
              throw new Error(`Failed to fetch ${asset}`);
            }
            return cache.put(asset, response);
          })
          .catch((error) => {
            console.warn(`[SW] Failed to cache ${asset}:`, error);
          });
      });
      return Promise.all(promises);
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.filter((key) => key.startsWith('nova-ai-shell') && key !== CACHE_NAME).map((key) => caches.delete(key))
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  if (url.pathname.includes('/')) {
    return; // Never cache API calls
  }
  if (request.method !== 'GET') {
    return;
  }

  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) {
        return cached;
      }
      return fetch(request).then((response) => {
        if (!response || response.status !== 200 || response.type !== 'basic') {
          return response;
        }
        const clone = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
        return response;
      });
    })
  );
});
