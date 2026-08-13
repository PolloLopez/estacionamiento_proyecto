# app_estacionamiento/views_pwa.py
"""
Vistas para Progressive Web App (PWA).

Sirve el manifest.json y el service worker desde Django para que
queden bajo el mismo dominio y scope que la app (requerido por los browsers).
"""

import json

from django.conf import settings
from django.http import HttpResponse, JsonResponse


def manifest_json(request):
    """
    Devuelve el manifest de la PWA.
    El nombre y colores se toman del primer municipio activo si existe,
    con valores de fallback hardcodeados.
    """
    from .models import Municipio

    municipio = Municipio.objects.filter(activo=True).first()
    nombre    = getattr(municipio, "nombre_sistema", None) or "Estacionamiento"
    color     = getattr(municipio, "color_primario", None) or "#14883b"

    manifest = {
        "name":             nombre,
        "short_name":       nombre,
        "description":      "Sistema de estacionamiento medido municipal",
        "start_url":        "/inicio/",
        "display":          "standalone",
        "background_color": "#ffffff",
        "theme_color":      color,
        "icons": [
            {
                "src":   "/static/icons/icon-192.png",
                "sizes": "192x192",
                "type":  "image/png",
            },
            {
                "src":   "/static/icons/icon-512.png",
                "sizes": "512x512",
                "type":  "image/png",
            },
        ],
    }

    return JsonResponse(manifest, content_type="application/manifest+json")


def service_worker(request):
    """
    Devuelve el service worker mínimo.
    Solo registra el SW para habilitar la instalación PWA —
    sin caché offline por ahora para no servir datos viejos al inspector.
    """
    js = """
// Service Worker mínimo — habilita instalación PWA
// Sin caché offline: los datos siempre vienen del servidor.
self.addEventListener('install', function(e) {
  self.skipWaiting();
});
self.addEventListener('activate', function(e) {
  e.waitUntil(self.clients.claim());
});
// No interceptamos fetch: comportamiento de red normal.
"""
    return HttpResponse(js, content_type="application/javascript")
