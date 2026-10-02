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
    Devuelve el Web App Manifest con el nombre e ícono del municipio correcto.

    Prioridad para elegir el municipio:
      1. El municipio del usuario autenticado (garantiza que la PWA instalada
         muestre el ícono del municipio en el que el usuario está registrado).
      2. Si no hay sesión activa: el primer municipio activo (para la pantalla
         de login, donde el prompt de instalación puede aparecer antes de loguearse).
    """
    from .models import Municipio

    if request.user.is_authenticated and getattr(request.user, "municipio_id", None):
        # Usuario logueado: usa su propio municipio.
        municipio = request.user.municipio
    else:
        # Sin sesión: fallback al primero activo (ej. página de login).
        municipio = Municipio.objects.filter(activo=True).first()

    nombre = (getattr(municipio, "nombre_sistema", None) or "Estacionamiento").strip() or "Estacionamiento"
    color  = getattr(municipio, "color_primario", None) or "#14883b"

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

    # start_url depende del rol: cada rol arranca en su pantalla principal.
    # Sin esto, todos (incluso inspectores) veían el dashboard de conductor.
    if request.user.is_authenticated:
        if getattr(request.user, "es_inspector", False):
            start_url = "/inspectores/"
        elif getattr(request.user, "es_admin", False):
            start_url = "/admin-estacionamientos/"
        elif getattr(request.user, "es_vendedor", False):
            start_url = "/vendedor/"
        elif getattr(request.user, "es_tesorero", False):
            start_url = "/tesorero/"
        else:
            start_url = "/inicio/"
    else:
        start_url = "/inicio/"

    manifest = {
        "name":             nombre,
        "short_name":       nombre,
        "description":      "Sistema municipal de estacionamiento medido",
        "start_url":        start_url,
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
    Service worker con estrategia network-first para páginas HTML
    y soporte de Web Push para notificaciones del sistema operativo.

    - Intenta la red primero en navegación HTML.
    - Si falla (sin conexión), devuelve la página cacheada.
    - No intercepta requests de API ni archivos estáticos.
    - Maneja el evento 'push': muestra notificación del SO.
    - Maneja 'notificationclick': abre la URL adjunta al pulsar la notificación.
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

// ── Web Push: muestra la notificación del SO al recibir un push ──────────────
// El payload es JSON: { title, body, url }
self.addEventListener('push', event => {
  if (!event.data) return;

  let datos = {};
  try { datos = event.data.json(); } catch(e) { datos = { title: 'Estacionamiento', body: event.data.text(), url: '/' }; }

  const titulo = datos.title || 'Estacionamiento';
  const opciones = {
    body:    datos.body  || '',
    icon:    '/static/icons/icon-192.png',
    badge:   '/static/icons/icon-192.png',
    data:    { url: datos.url || '/' },
    // vibrate: patrón de vibración en ms (vibra - pausa - vibra)
    vibrate: [200, 100, 200],
  };

  event.waitUntil(
    self.registration.showNotification(titulo, opciones)
  );
});

// ── Notificationclick: abre la URL al tocar la notificación ──────────────────
self.addEventListener('notificationclick', event => {
  event.notification.close();
  const url = event.notification.data?.url || '/';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(ventanas => {
      // Si hay una pestaña ya abierta en la app, enfocarla y navegar ahí
      for (const ventana of ventanas) {
        if (ventana.url.includes(self.location.origin) && 'focus' in ventana) {
          ventana.focus();
          ventana.navigate(url);
          return;
        }
      }
      // Si no hay pestaña abierta, abrir una nueva
      if (clients.openWindow) {
        return clients.openWindow(url);
      }
    })
  );
});
""".strip()

    return HttpResponse(sw_js, content_type="application/javascript")
