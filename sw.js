// Service worker: офлайн-кэш и ежедневные push-уведомления
const CACHE = "velikie-v7";
const STATE = "velikie-state"; // отложенные из уведомления истории — не удалять при обновлении
const SHELL = ["./", "index.html", "data/people.json", "data/facts.json", "data/extra.json", "data/shelves.json", "data/world.json", "data/links.json", "data/look.json", "data/map.svg", "manifest.webmanifest", "icons/icon-192.png", "icons/badge-96.png",
  "fonts/pf-cyr.woff2", "fonts/pf-lat.woff2", "fonts/pf-italic-cyr.woff2", "fonts/pf-italic-lat.woff2"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k !== CACHE && k !== STATE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET" || new URL(req.url).origin !== location.origin) return;
  const isPhoto = /\/(photos|icons|fonts)\//.test(req.url);
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
    data: {url: d.url || "./", id: d.id || (d.url || "").split("/p/")[1]},
    actions: [{action: "read", title: "Читать"}, {action: "later", title: "Позже"}]
  }));
});

// «Позже»: запоминаем историю, приложение покажет её на главном экране
async function addLater(id) {
  if (!id) return;
  const c = await caches.open(STATE), r = await c.match("later");
  const list = r ? await r.json() : [];
  await c.put("later", new Response(JSON.stringify([id, ...list.filter(x => x !== id)].slice(0, 10))));
}

self.addEventListener("notificationclick", e => {
  e.notification.close();
  if (e.action === "later") { e.waitUntil(addLater(e.notification.data.id)); return; }
  const url = new URL(e.notification.data.url, self.registration.scope).href;
  e.waitUntil(clients.matchAll({type: "window", includeUncontrolled: true}).then(list => {
    for (const c of list) {
      if (c.url.startsWith(self.registration.scope) && "navigate" in c) return c.navigate(url).then(w => (w || c).focus());
    }
    return clients.openWindow(url);
  }));
});
