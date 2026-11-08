// Minimal offline cache for Home Bar. Bump CACHE when you publish a new index.html or cocktaildb.json.
const CACHE = 'homebar-v10';
const FILES = ['./', './index.html', './library.json', './cocktaildb.json'];
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(async c => { for (const f of FILES) { try { await c.add(f); } catch (_) {} } }));
  self.skipWaiting();
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))));
  self.clients.claim();
});
self.addEventListener('fetch', e => {
  const u = new URL(e.request.url);
  if (e.request.mode === 'navigate' || u.pathname.endsWith('/index.html') || u.pathname.endsWith('/cocktaildb.json') || u.pathname.endsWith('/library.json')) {
    e.respondWith(fetch(e.request).then(r => { if (r.ok) caches.open(CACHE).then(c => c.put(e.request, r.clone())); return r; })
      .catch(() => caches.match(e.request).then(m => m || caches.match('./index.html'))));
  }
});
