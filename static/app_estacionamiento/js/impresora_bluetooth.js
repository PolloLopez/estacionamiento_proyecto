/**
 * impresora_bluetooth.js
 *
 * Conexión con impresora térmica 58mm vía Web Bluetooth API.
 * Chrome Android 85+ con HTTPS.
 *
 * Perfiles soportados (se prueban en orden):
 *   - Genérico 18f0 (más común en impresoras de 58mm)
 *   - Nordic UART Service / NUS (nRF51/nRF52)
 *   - Star Micronics BLE
 *   - Alternativo genérico
 *
 * Estrategia de reconexión (más confiable que llamar gatt.connect() en frío):
 *   1. getDevices() → obtiene el objeto device sin diálogo.
 *   2. watchAdvertisements() → espera que la impresora emita un anuncio BLE (5s timeout).
 *      Una vez detectada, gatt.connect() tiene altísima tasa de éxito.
 *   3. Si watchAdvertisements no disponible o timeout, intenta gatt.connect() directo (3 reintentos).
 *   4. Si getDevices() vacío → requestDevice() con filtro de nombre (diálogo con 1 dispositivo pre-seleccionado).
 *
 * Chrome bug: getDevices() puede devolver vacío al navegar entre páginas.
 * watchAdvertisements() mitiga esto porque refresca la referencia al dispositivo
 * y Chrome lo "recuerda" mejor tras la detección del anuncio.
 */

'use strict';

// ── Perfiles BLE ────────────────────────────────────────────────────────────

var PERFILES_BLE = [
  { servicio: '000018f0-0000-1000-8000-00805f9b34fb',
    caract:   '00002af1-0000-1000-8000-00805f9b34fb' },
  { servicio: '6e400001-b5a3-f393-e0a9-e50e24dcca9e',
    caract:   '6e400002-b5a3-f393-e0a9-e50e24dcca9e' },
  { servicio: 'e7810a71-73ae-499d-8c15-faa9aef0c3f2',
    caract:   'bef8d6c9-9c21-4c9e-b632-bd58c1009f9f' },
  { servicio: '49535343-fe7d-4ae5-8fa9-9fafd205e455',
    caract:   '49535343-8841-43f4-a8d4-ecbe34729bb3' },
];

var UUID_SERVICIOS_OPT = PERFILES_BLE.map(function(p) { return p.servicio; });
var CHUNK_SIZE = 20;

// ── Persistencia en localStorage ────────────────────────────────────────────

var _ALIAS_KEY = 'bleImpresoraAliases';
var _INFO_KEY  = 'bleImpresoraActiva';

/** Devuelve el alias guardado para un device.id, o null. */
function obtenerAlias(deviceId) {
  try {
    return JSON.parse(localStorage.getItem(_ALIAS_KEY) || '{}')[deviceId] || null;
  } catch (_) { return null; }
}

/**
 * Guarda alias personalizado para un dispositivo.
 * También actualiza el nombre en _INFO_KEY si es el dispositivo activo.
 */
function guardarAlias(deviceId, alias) {
  alias = alias.trim();
  try {
    var data = JSON.parse(localStorage.getItem(_ALIAS_KEY) || '{}');
    data[deviceId] = alias;
    localStorage.setItem(_ALIAS_KEY, JSON.stringify(data));
    var info = obtenerInfoImpresora();
    if (info && info.id === deviceId) {
      info.alias = alias;
      localStorage.setItem(_INFO_KEY, JSON.stringify(info));
    }
  } catch (_) {}
}

/** Nombre a mostrar: alias → nombre hardware → 'Impresora BLE'. */
function nombreMostrar(device) {
  return obtenerAlias(device.id) || device.name || 'Impresora BLE';
}

/**
 * Guarda info del dispositivo activo para reconexión posterior.
 * Se llama siempre que se conecta exitosamente.
 */
function guardarInfoImpresora(device) {
  try {
    localStorage.setItem(_INFO_KEY, JSON.stringify({
      id:    device.id,
      name:  device.name || '',
      alias: obtenerAlias(device.id) || device.name || 'Impresora BLE',
    }));
  } catch (_) {}
}

/** Devuelve {id, name, alias} del dispositivo guardado, o null. */
function obtenerInfoImpresora() {
  try {
    var data = localStorage.getItem(_INFO_KEY);
    return data ? JSON.parse(data) : null;
  } catch (_) { return null; }
}

// ── Conexión ────────────────────────────────────────────────────────────────

/**
 * Abre diálogo para seleccionar impresora (primera vez o cambio).
 * Retorna { device, caracteristica, perfil } o lanza error.
 */
async function conectarImpresora() {
  if (!navigator.bluetooth) {
    throw new Error('Web Bluetooth no disponible. Usá Chrome en Android con HTTPS.');
  }
  var device = await navigator.bluetooth.requestDevice({
    acceptAllDevices: true,
    optionalServices: UUID_SERVICIOS_OPT,
  });
  var conexion = await _abrirConexion(device);
  guardarInfoImpresora(device);   // persiste para reconexiones futuras
  return conexion;
}

/**
 * Reconecta a la impresora guardada SIN mostrar diálogo de selección (si es posible).
 *
 * Estrategia en orden:
 *   1. getDevices() + watchAdvertisements → espera el anuncio BLE antes de conectar.
 *      La tasa de éxito es muy alta porque la conexión se hace cuando el dispositivo
 *      ya está activamente emitiendo.
 *   2. Si watchAdvertisements no disponible o timeout, reintenta gatt.connect() directo.
 *   3. Si getDevices() vacío → requestDevice() filtrado por nombre (diálogo mínimo
 *      con la impresora ya pre-seleccionada: el inspector toca una vez).
 *
 * Retorna { device, caracteristica, perfil } o null.
 */
async function reconectarImpresora() {
  if (!navigator.bluetooth) return null;

  // Intento 1: getDevices() + watchAdvertisements (reconexión completamente silenciosa)
  if (typeof navigator.bluetooth.getDevices === 'function') {
    try {
      var devs = await navigator.bluetooth.getDevices();
      if (devs.length) {
        var device = devs[0];
        guardarInfoImpresora(device);

        // Esperamos el anuncio BLE (5s) antes de conectar: mucho más confiable
        // que llamar gatt.connect() en frío, especialmente después de navegar entre páginas.
        try {
          var cx = await _conectarViaAnuncio(device, 5000);
          return cx;
        } catch (eAnuncio) {
          console.warn('[BLE] watchAdvertisements falló o timeout:', eAnuncio.message);
        }

        // Fallback dentro del mismo dispositivo: connect directo con reintentos
        try {
          return await _abrirConexionConReintentos(device, 3);
        } catch (eDirecto) {
          console.warn('[BLE] connect directo falló tras reintentos:', eDirecto.message);
        }
      }
    } catch (e) {
      console.warn('[BLE] getDevices falló:', e.message);
    }
  }

  // Intento 2: requestDevice filtrado por nombre conocido.
  // Muestra diálogo, pero pre-filtrado a UNA impresora → el inspector toca una vez.
  var info = obtenerInfoImpresora();
  if (info && info.name) {
    try {
      var device = await navigator.bluetooth.requestDevice({
        filters: [{ name: info.name }],
        optionalServices: UUID_SERVICIOS_OPT,
      });
      var conexion = await _abrirConexionConReintentos(device, 2);
      guardarInfoImpresora(device);
      return conexion;
    } catch (e) {
      console.warn('[BLE] reconexión por nombre falló:', e.message);
      return null;
    }
  }

  return null;
}

/**
 * Espera que el dispositivo emita un anuncio BLE y luego conecta.
 * Esto es mucho más confiable que gatt.connect() en frío, especialmente
 * tras navegar entre páginas o después de un disconnect explícito.
 *
 * @param {BluetoothDevice} device - Dispositivo obtenido de getDevices()
 * @param {number} timeoutMs - Tiempo máximo de espera (default 5000ms)
 * @returns Promise<{device, caracteristica, perfil}>
 */
async function _conectarViaAnuncio(device, timeoutMs) {
  timeoutMs = timeoutMs || 5000;
  if (typeof device.watchAdvertisements !== 'function') {
    throw new Error('watchAdvertisements no disponible');
  }
  return new Promise(function(resolve, reject) {
    var controller = new AbortController();
    var timer = setTimeout(function() {
      try { controller.abort(); } catch (_) {}
      reject(new Error('timeout esperando anuncio BLE'));
    }, timeoutMs);

    device.addEventListener('advertisementreceived', function onAnuncio() {
      clearTimeout(timer);
      device.removeEventListener('advertisementreceived', onAnuncio);
      try { controller.abort(); } catch (_) {}
      // Dispositivo está activamente emitiendo → conectar GATT
      _abrirConexion(device).then(resolve).catch(reject);
    }, { once: true });

    device.watchAdvertisements({ signal: controller.signal }).catch(function(e) {
      clearTimeout(timer);
      reject(e);
    });
  });
}

/**
 * Intenta gatt.connect() hasta `intentos` veces con pausa entre reintentos.
 * Útil para el caso donde el dispositivo está en estado "desconectando"
 * (ej: copia 1 recién terminó y llamamos para copia 2).
 */
async function _abrirConexionConReintentos(device, intentos) {
  intentos = intentos || 3;
  var ultimoError;
  for (var i = 0; i < intentos; i++) {
    try {
      return await _abrirConexion(device);
    } catch (e) {
      ultimoError = e;
      console.warn('[BLE] gatt.connect() intento ' + (i + 1) + ' falló:', e.message);
      if (i < intentos - 1) {
        await new Promise(function(r) { setTimeout(r, 600); });
      }
    }
  }
  throw ultimoError;
}

/**
 * Conecta al GATT server y encuentra la primera característica de escritura.
 */
async function _abrirConexion(device) {
  var server = await device.gatt.connect();

  // Probar perfiles conocidos primero
  for (var i = 0; i < PERFILES_BLE.length; i++) {
    var perfil = PERFILES_BLE[i];
    try {
      var svc   = await server.getPrimaryService(perfil.servicio);
      var caract = await svc.getCharacteristic(perfil.caract);
      console.log('[BLE] Perfil:', perfil.servicio);
      return { device: device, caracteristica: caract, perfil: perfil };
    } catch (_) {}
  }

  // Descubrimiento automático
  console.log('[BLE] Descubriendo servicios...');
  var servicios = await server.getPrimaryServices();
  for (var s = 0; s < servicios.length; s++) {
    try {
      var caracts = await servicios[s].getCharacteristics();
      for (var c = 0; c < caracts.length; c++) {
        var props = caracts[c].properties;
        if (props.write || props.writeWithoutResponse) {
          console.log('[BLE] Encontrado:', servicios[s].uuid, caracts[c].uuid);
          return {
            device: device,
            caracteristica: caracts[c],
            perfil: { servicio: servicios[s].uuid, caract: caracts[c].uuid }
          };
        }
      }
    } catch (_) {}
  }

  throw new Error('No se encontró característica de escritura.');
}

/**
 * Diagnóstico: lista todos los servicios y características del dispositivo.
 */
async function diagnosticarImpresora() {
  var device = await navigator.bluetooth.requestDevice({
    acceptAllDevices: true,
    optionalServices: UUID_SERVICIOS_OPT,
  });
  var server   = await device.gatt.connect();
  var servicios = await server.getPrimaryServices();
  var resultado = 'Dispositivo: ' + device.name + '\n\n';

  for (var s = 0; s < servicios.length; s++) {
    resultado += 'Servicio: ' + servicios[s].uuid + '\n';
    try {
      var caracts = await servicios[s].getCharacteristics();
      for (var c = 0; c < caracts.length; c++) {
        var p = caracts[c].properties;
        var flags = [];
        if (p.read)                 flags.push('read');
        if (p.write)                flags.push('write');
        if (p.writeWithoutResponse) flags.push('writeNoResp');
        if (p.notify)               flags.push('notify');
        resultado += '  Char: ' + caracts[c].uuid + ' [' + flags.join(', ') + ']\n';
      }
    } catch (e) {
      resultado += '  (sin acceso)\n';
    }
    resultado += '\n';
  }
  device.gatt.disconnect();
  return resultado;
}

/**
 * Reconexión silenciosa: solo usa getDevices() + watchAdvertisements, sin diálogos.
 * Usar cuando NO hay gesto de usuario disponible (ej: entre copias en modo automático).
 *
 * Estrategia:
 *   1. getDevices() → obtiene el device sin diálogo.
 *   2. watchAdvertisements → espera anuncio BLE (4s) y conecta.
 *   3. Si timeout o no disponible → connect directo con reintentos.
 *   4. Si getDevices() vacío → null (el caller puede mostrar botón con gesto).
 *
 * Retorna { device, caracteristica, perfil } o null.
 */
async function reconectarSilencioso() {
  if (!navigator.bluetooth) return null;
  if (typeof navigator.bluetooth.getDevices !== 'function') return null;
  try {
    var devs = await navigator.bluetooth.getDevices();
    if (!devs.length) return null;
    var device = devs[0];
    guardarInfoImpresora(device);

    // Intentar vía anuncio BLE (más confiable, especialmente post-disconnect de copia 1)
    try {
      return await _conectarViaAnuncio(device, 4000);
    } catch (eAnuncio) {
      console.warn('[BLE] watchAdvertisements silencioso falló:', eAnuncio.message);
    }

    // Fallback: connect directo con reintentos
    return await _abrirConexionConReintentos(device, 3);
  } catch (e) {
    console.warn('[BLE] reconexión silenciosa falló:', e.message);
    return null;
  }
}

// ── Envío de datos ──────────────────────────────────────────────────────────

/** Envía datos en chunks de CHUNK_SIZE bytes con pausa entre cada uno. */
async function enviarImpresion(caracteristica, datos) {
  for (var i = 0; i < datos.length; i += CHUNK_SIZE) {
    var chunk = datos.slice(i, i + CHUNK_SIZE);
    try {
      await caracteristica.writeValue(chunk);
    } catch (_) {
      await caracteristica.writeValueWithoutResponse(chunk);
    }
    await new Promise(function(r) { setTimeout(r, 20); });
  }
}

// ── Generación de tickets ESC/POS ───────────────────────────────────────────

/** Normaliza texto a ASCII puro (impresoras básicas no soportan UTF-8). */
function _norm(s) {
  return String(s || '')
    .replace(/[áàâä]/gi, function(m) { return /[A-Z]/.test(m) ? 'A' : 'a'; })
    .replace(/[éèêë]/gi, function(m) { return /[A-Z]/.test(m) ? 'E' : 'e'; })
    .replace(/[íìîï]/gi, function(m) { return /[A-Z]/.test(m) ? 'I' : 'i'; })
    .replace(/[óòôö]/gi, function(m) { return /[A-Z]/.test(m) ? 'O' : 'o'; })
    .replace(/[úùûü]/gi, function(m) { return /[A-Z]/.test(m) ? 'U' : 'u'; })
    .replace(/ñ/g, 'n').replace(/Ñ/g, 'N')
    .replace(/[^\x20-\x7E]/g, '?');
}

/**
 * Genera bytes ESC/POS para un código QR nativo (comando GS ( k).
 * Compatible con la mayoría de impresoras térmicas modernas.
 * tamano: 1–16 (4 = ~4 dots por módulo, recomendado para 58mm).
 */
function _qrEscPos(texto, tamano) {
  tamano = tamano || 4;
  var GS = 29, cn = 49;
  var buf = [];

  // Convertir texto a bytes UTF-8
  var bytes = [];
  for (var i = 0; i < texto.length; i++) {
    var code = texto.charCodeAt(i);
    if (code < 0x80) {
      bytes.push(code);
    } else if (code < 0x800) {
      bytes.push(0xC0 | (code >> 6), 0x80 | (code & 0x3F));
    } else {
      bytes.push(
        0xE0 | (code >> 12),
        0x80 | ((code >> 6) & 0x3F),
        0x80 | (code & 0x3F)
      );
    }
  }

  // 1. Modelo QR 2
  buf.push(GS, 0x28, 0x6B, 4, 0, cn, 65, 50, 0);
  // 2. Tamaño del módulo
  buf.push(GS, 0x28, 0x6B, 3, 0, cn, 67, tamano);
  // 3. Nivel de corrección L
  buf.push(GS, 0x28, 0x6B, 3, 0, cn, 69, 48);
  // 4. Almacenar datos (pL, pH incluyen los 3 bytes de cn+fn+m)
  var len = bytes.length + 3;
  buf.push(GS, 0x28, 0x6B, len & 0xFF, (len >> 8) & 0xFF, cn, 80, 48);
  for (var j = 0; j < bytes.length; j++) buf.push(bytes[j]);
  // 5. Imprimir
  buf.push(GS, 0x28, 0x6B, 3, 0, cn, 81, 48);

  return buf;
}

/**
 * Genera un Uint8Array ESC/POS para el acta de infracción.
 * Siempre imprime QR nativo + URL como texto (doble seguridad).
 */
function generarTicketInfraccion(d) {
  var ESC = 27, GS = 29, LF = 10;
  var ANCHO = 32;
  var SEP = '--------------------------------';

  var buf = [];

  function push() {
    for (var i = 0; i < arguments.length; i++) buf.push(arguments[i]);
  }

  function linea(s) {
    var norm = _norm(s).substring(0, ANCHO * 2);
    for (var i = 0; i < norm.length; i++) buf.push(norm.charCodeAt(i));
    buf.push(LF);
  }

  // ancho: número de columnas disponibles. Para modo doble-ancho usar ANCHO/2.
  function centrar(s, ancho) {
    ancho = ancho !== undefined ? ancho : ANCHO;
    var norm = _norm(s).substring(0, ancho);
    var pad  = Math.max(0, Math.floor((ancho - norm.length) / 2));
    return Array(pad + 1).join(' ') + norm;
  }

  // Init
  push(ESC, 0x40);

  // Encabezado
  push(ESC, 0x61, 0x01);      // centro
  push(ESC, 0x45, 0x01);      // negrita
  linea('ACTA DE INFRACCION');
  push(ESC, 0x45, 0x00);
  linea(_norm(d.municipio));
  linea(SEP);

  push(ESC, 0x45, 0x01);
  linea('N ' + d.acta);
  push(ESC, 0x45, 0x00);
  linea(SEP);

  // Patente grande — en modo doble-ancho entran ANCHO/2 columnas
  push(GS, 0x21, 0x11);       // doble alto+ancho
  linea(centrar(d.patente, Math.floor(ANCHO / 2)));
  push(GS, 0x21, 0x00);
  linea(centrar(_norm(d.tipo_vehiculo)));    // modo normal: ANCHO completo
  linea(SEP);

  // Datos
  push(ESC, 0x61, 0x00);      // izquierda
  linea(_norm('Subcuadra: ' + d.subcuadra));
  linea(_norm('Motivo: ' + d.motivo));
  linea(SEP);
  linea('Fecha: ' + d.fecha + ' ' + d.hora + 'hs');
  linea(SEP);

  // Monto — también en doble-ancho, idem patente
  push(ESC, 0x61, 0x01);
  push(GS, 0x21, 0x11);
  push(ESC, 0x45, 0x01);
  linea(centrar('$' + d.monto, Math.floor(ANCHO / 2)));
  push(ESC, 0x45, 0x00);
  push(GS, 0x21, 0x00);
  linea(SEP);

  // Inspector
  push(ESC, 0x61, 0x00);
  push(ESC, 0x45, 0x01);
  linea('Inspector:');
  push(ESC, 0x45, 0x00);
  linea(_norm(d.inspector));
  if (d.legajo) linea('Legajo: ' + d.legajo);
  linea(SEP);

  // Divide un texto largo en líneas de ancho máximo `ancho` chars.
  function wrap(s, ancho) {
    var norm  = _norm(s);
    var words = norm.split(' ');
    var lines = [];
    var cur   = '';
    for (var wi = 0; wi < words.length; wi++) {
      var w = words[wi];
      if (!w) continue;
      if (cur.length === 0) {
        cur = w.substring(0, ancho);
      } else if (cur.length + 1 + w.length <= ancho) {
        cur += ' ' + w;
      } else {
        lines.push(cur);
        cur = w.substring(0, ancho);
      }
    }
    if (cur.length) lines.push(cur);
    return lines;
  }

  // Leyenda de horarios y texto de ordenanza (si el municipio los configuró)
  if (d.leyenda_horarios) {
    push(ESC, 0x61, 0x00);
    linea(SEP);
    var hLines = wrap(d.leyenda_horarios, ANCHO);
    for (var hi = 0; hi < hLines.length; hi++) linea(hLines[hi]);
  }
  if (d.texto_ordenanza) {
    linea(SEP);
    var oLines = wrap(d.texto_ordenanza, ANCHO);
    for (var oi = 0; oi < oLines.length; oi++) linea(oLines[oi]);
  }

  // QR nativo ESC/POS + URL como texto de respaldo
  push(ESC, 0x61, 0x01);      // centro
  linea('Paga online:');
  var qrBytes = _qrEscPos(d.url_pago, 4);
  for (var qi = 0; qi < qrBytes.length; qi++) buf.push(qrBytes[qi]);
  buf.push(LF);
  // URL en texto (por si el modelo no soporta GS(k)
  push(ESC, 0x61, 0x01);
  linea(_norm(d.url_pago));

  // Avance y corte
  push(LF, LF, LF, LF);
  push(GS, 0x56, 0x42, 0x10);

  return new Uint8Array(buf);
}

/** Ticket de prueba mínimo para verificar que la impresora recibe datos. */
function generarTicketPrueba() {
  var buf = [];
  function push() { for (var i = 0; i < arguments.length; i++) buf.push(arguments[i]); }
  function linea(s) { for (var i = 0; i < s.length; i++) buf.push(s.charCodeAt(i)); buf.push(10); }

  push(27, 0x40);
  push(27, 0x61, 0x01);
  push(27, 0x45, 0x01);
  linea('--- PRUEBA ---');
  push(27, 0x45, 0x00);
  linea('Impresora OK');
  linea(new Date().toLocaleTimeString());
  push(10, 10, 10, 10);
  push(29, 0x56, 0x42, 0x10);

  return new Uint8Array(buf);
}
