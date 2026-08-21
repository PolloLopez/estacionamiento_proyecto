# app_estacionamiento/views_pwa.py
"""
Vistas para Progressive Web App (PWA).

- /manifest.json  → metadatos de la app (nombre, íconos, colores).
- /sw.js          → service worker con estrategia network-first.

Ambas rutas deben estar en la raíz del sitio para tener scope completo.
"""

import json

from django.http import HttpResponse, JsonResponse
from django.templatetags.static import static


def manifest_json(request):
    """
    Devuelve el Web App Manifest.
    Nombre y color primario se toman del municipio activo si existe.
    """
    from .models import Municipio

    municipio = Municipio.objects.filter(activo=True).first()
    nombre    = (getattr(municipio, "nombre_sistema", None) or "Estacionamiento").strip() or "Estacionamiento"
    color     = getattr(municipio, "color_primario", None) or "#14883b"

    # Si el municipio tiene ícono propio lo usamos; si no, los íconos estáticos del repo.
    icono = getattr(municipio, "icono_app", None)
    if icono:
        icono_url = request.build_absolute_uri(icono.url)
        icons = [
            {"src": icono_url, "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": icono_url, "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ]
    else:
        icons = [
            {"src": request.build_absolute_uri(static("icons/icon-192.png")), "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": request.build_absolute_uri(static("icons/icon-512.png")), "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ]

    manifest = {
        "name":             nombre,
        "short_name":       nombre,
        "description":      "Sistema municipal de estacionamiento medido",
        "start_url":        "/inicio/",
        "display":          "standalone",
        "background_color": "#ffffff",
        "theme_color":      color,
        "lang":             "es-AR",
        "icons":            icons,
    }

    return HttpResponse(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        content_type="application/manifest+json",
    )


def service_worker(request):
    """
    Service worker con estrategia network-first para páginas HTML.
    - Intenta la red primero.
    - Si falla (sin conexión), devuelve la página cacheada.
    - No intercepta requests de API ni archivos estáticos.
    """
    sw_js = """
const CACHE_NAME = 'estacionar-v1';
const OFFLINE_URL = '/';

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.add(OFFLINE_URL))
  );
  self.skipWaiting();
});

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

// Network-first solo para navegación HTML (no API, no estáticos)
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  if (!event.request.headers.get('accept')?.includes('text/html')) return;

  event.respondWith(
    fetch(event.request)
      .then(response => {
        if (response.ok) {
          const copy = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, copy));
        }
        return response;
      })
      .catch(() => caches.match(OFFLINE_URL))
  );
});
""".strip()

    return HttpResponse(sw_js, content_type="application/javascript")
