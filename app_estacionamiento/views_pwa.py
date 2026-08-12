# app_estacionamiento/views_pwa.py
"""
Vistas para Progressive Web App (PWA).

- /manifest.json  → metadatos de la app (nombre, íconos, colores).
- /sw.js          → service worker básico (permite instalación en Android/iOS).

El service worker usa estrategia "network-first con fallback offline":
intenta la red; si falla, devuelve la página de offline del caché.
Ambas rutas deben estar en la raíz del sitio para tener scope completo.
"""

import json
from django.http import HttpResponse, JsonResponse
from django.templatetags.static import static


def manifest_json(request):
    """
    Devuelve el Web App Manifest que describe la app al navegador.
    Sirve como /manifest.json (ver urls.py).
    """
    base_url = request.build_absolute_uri("/")

    manifest = {
        "name":             "EstacionAR",
        "short_name":       "EstacionAR",
        "description":      "Sistema municipal de estacionamiento medido",
        "start_url":        "/",
        "display":          "standalone",
        "background_color": "#f0f2f0",
        "theme_color":      "#14883b",
        "lang":             "es-AR",
        "icons": [
            {
                "src":   request.build_absolute_uri(static("icons/icon-192.png")),
                "sizes": "192x192",
                "type":  "image/png",
                "purpose": "any maskable",
            },
            {
                "src":   request.build_absolute_uri(static("icons/icon-512.png")),
                "sizes": "512x512",
                "type":  "image/png",
                "purpose": "any maskable",
            },
        ],
    }

    return HttpResponse(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        content_type="application/manifest+json",
    )


def service_worker(request):
    """
    Service worker básico para habilitar el prompt de instalación en Chrome/Android.

    Estrategia: network-first.
    - Intenta cargar desde la red.
    - Si la red falla (sin internet), devuelve la respuesta cacheada si la hay.
    - Cachea el inicio (/) en la instalación para tener algo offline.
    """
    sw_js = """
const CACHE_NAME = 'estacionar-v1';
const OFFLINE_URL = '/';

// Al instalar: pre-cachear la página principal como fallback offline.
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.add(OFFLINE_URL))
  );
  self.skipWaiting();
});

// Al activar: limpiar caches viejas.
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

// Fetch: network-first, fallback a cache.
self.addEventListener('fetch', event => {
  // Solo interceptar peticiones GET de navegación (no API, no archivos estáticos).
  if (event.request.method !== 'GET') return;
  if (!event.request.headers.get('accept')?.includes('text/html')) return;

  event.respondWith(
    fetch(event.request)
      .then(response => {
        // Guardar una copia de respuestas exitosas de navegación en caché.
        if (response.ok) {
          const copy = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, copy));
        }
        return response;
      })
      .catch(() =>
        // Sin red: devolver la página de inicio del caché como fallback.
        caches.match(OFFLINE_URL)
      )
  );
});
""".strip()

    return HttpResponse(sw_js, content_type="application/javascript")
