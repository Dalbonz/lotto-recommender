const CACHE = "lottery-app-v3";
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

  // 항상 네트워크를 먼저 시도해 최신 콘텐츠를 받고, 오프라인/실패 시에만 캐시로
  // 폴백한다(network-first). 예전에는 앱 셸(HTML/JS)을 캐시 우선으로 서빙해서 배포
  // 직후에도 새로고침 한 번으로는 새 버전이 안 보이는 문제가 있었다.
  event.respondWith(
    fetch(event.request)
      .then((res) => {
        if (res.ok) { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(event.request, copy)); }
        return res;
      })
      .catch(() => caches.match(event.request))
  );
});
