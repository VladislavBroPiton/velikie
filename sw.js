// Service worker: офлайн-кэш и ежедневные push-уведомления
const CACHE = "velikie-v1";
const SHELL = ["./", "index.html", "data/people.json", "manifest.webmanifest", "icons/icon-192.png", "icons/badge-96.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET" || new URL(req.url).origin !== location.origin) return;
  const isPhoto = /\/(photos|icons)\//.test(req.url);
  if (isPhoto) {
    // Фото не меняются: сначала кэш
    e.respondWith(caches.match(req).then(hit => hit || fetch(req).then(res => {
      const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy)); return res;
    })));
  } else {
    // Страница и истории: сначала сеть, без сети — кэш
    e.respondWith(fetch(req).then(res => {
      const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy)); return res;
    }).catch(() => caches.match(req, {ignoreSearch: true})));
  }
});

self.addEventListener("push", e => {
  let d = {};
  try { d = e.data.json(); } catch { d = {title: "Великие", body: e.data ? e.data.text() : ""}; }
  e.waitUntil(self.registration.showNotification(d.title || "Великие", {
    body: d.body || "",
    icon: "icons/icon-192.png",
    badge: "icons/badge-96.png",
    image: d.image,
    tag: "daily",
    data: {url: d.url || "./"}
  }));
});

self.addEventListener("notificationclick", e => {
  e.notification.close();
  const url = new URL(e.notification.data.url, self.registration.scope).href;
  e.waitUntil(clients.matchAll({type: "window", includeUncontrolled: true}).then(list => {
    for (const c of list) {
      if (c.url.startsWith(self.registration.scope) && "navigate" in c) return c.navigate(url).then(w => (w || c).focus());
    }
    return clients.openWindow(url);
  }));
});
