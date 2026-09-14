const CACHE = "lottery-app-v1";
const ASSETS = ["./", "./index.html", "./manifest.json"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(ASSETS)).catch(() => {}));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  const url = new URL(event.request.url);
  const isData = url.pathname.includes("/data/");

  if (isData) {
    // 당첨번호 데이터는 항상 최신을 우선 시도, 실패 시 캐시로 폴백 (network-first)
    event.respondWith(
      fetch(event.request)
        .then((res) => { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(event.request, copy)); return res; })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  event.respondWith(
    caches.match(event.request).then((cached) => {
      const network = fetch(event.request)
        .then((res) => { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(event.request, copy)); return res; })
        .catch(() => cached);
      return cached || network;
    })
  );
});
