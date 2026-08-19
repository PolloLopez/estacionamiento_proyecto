/**
 * impresora_bluetooth.js
 *
 * Conexión directa con impresora térmica 58mm vía Web Bluetooth API (BLE).
 * Funciona en Chrome Android 85+ sobre HTTPS.
 * No requiere Mopria ni configuración de sistema — solo emparejar el dispositivo
 * una vez por teléfono usando el botón "Conectar impresora" del panel inspector.
 *
 * Protocolo: ESC/POS sobre GATT BLE.
 */

'use strict';

// UUIDs GATT de servicios de impresión (se prueban en orden hasta encontrar uno válido).
// La mayoría de impresoras térmicas BLE de 58mm usan el primero.
const UUID_SERVICIOS = [
  '000018f0-0000-1000-8000-00805f9b34fb',  // Genérico ESC/POS BLE (más común)
  'e7810a71-73ae-499d-8c15-faa9aef0c3f2',  // Star Micronics BLE
  '49535343-fe7d-4ae5-8fa9-9fafd205e455',  // Otro genérico
];

// UUID de características de escritura para cada servicio
const UUID_CARACTERISTICAS = [
  '00002af1-0000-1000-8000-00805f9b34fb',
  'bef8d6c9-9c21-4c9e-b632-bd58c1009f9f',
  '49535343-8841-43f4-a8d4-ecbe34729bb3',
];

// Tamaño de chunk BLE (MTU estándar = 20 bytes; la mayoría soporta hasta 512 con negociación)
const CHUNK_SIZE = 20;

/**
 * Abre el diálogo para que el usuario seleccione su impresora BLE.
 * Chrome recuerda el permiso para la misma origin → getDevices() funciona después.
 * Retorna { device, caracteristica } o lanza un error.
 */
async function conectarImpresora() {
  if (!navigator.bluetooth) {
    throw new Error('Web Bluetooth no disponible. Usá Chrome en Android.');
  }
  const device = await navigator.bluetooth.requestDevice({
    acceptAllDevices: true,
    optionalServices: UUID_SERVICIOS,
  });
  const caracteristica = await _conectarDispositivo(device);
  return { device, caracteristica };
}

/**
 * Intenta reconectar a una impresora ya autorizada anteriormente (sin diálogo).
 * Usa navigator.bluetooth.getDevices() — disponible en Chrome 85+.
 * Retorna { device, caracteristica } o null si no hay dispositivo autorizado.
 */
async function reconectarImpresora() {
  if (!navigator.bluetooth || typeof navigator.bluetooth.getDevices !== 'function') {
    return null;
  }
  const dispositivos = await navigator.bluetooth.getDevices();
  if (!dispositivos.length) return null;

  // Usar el primer dispositivo autorizado (hay una impresora por teléfono)
  const device = dispositivos[0];
  try {
    const caracteristica = await _conectarDispositivo(device);
    return { device, caracteristica };
  } catch (e) {
    console.warn('Reconexión BLE fallida:', e.message);
    return null;
  }
}

/**
 * Conecta al servidor GATT del dispositivo y busca la característica de escritura.
 * Prueba todos los pares servicio/característica conocidos.
 */
async function _conectarDispositivo(device) {
  const server = await device.gatt.connect();

  for (const uuidServicio of UUID_SERVICIOS) {
    let servicio;
    try {
      servicio = await server.getPrimaryService(uuidServicio);
    } catch (_) { continue; }

    for (const uuidCaract of UUID_CARACTERISTICAS) {
      try {
        const caract = await servicio.getCharacteristic(uuidCaract);
        console.log('[BLE] Impresora conectada. Servicio:', uuidServicio);
        return caract;
      } catch (_) {}
    }
  }

  // Si ningún UUID conocido funcionó, intentar descubrir servicios disponibles
  const servicios = await server.getPrimaryServices();
  for (const svc of servicios) {
    try {
      const caracts = await svc.getCharacteristics();
      for (const c of caracts) {
        if (c.properties.write || c.properties.writeWithoutResponse) {
          console.log('[BLE] Característica descubierta:', svc.uuid, c.uuid);
          return c;
        }
      }
    } catch (_) {}
  }

  throw new Error('No se encontró la característica de impresión en la impresora.');
}

/**
 * Envía un Uint8Array a la impresora en chunks de CHUNK_SIZE bytes.
 */
async function enviarImpresion(caracteristica, datos) {
  for (let i = 0; i < datos.length; i += CHUNK_SIZE) {
    const chunk = datos.slice(i, i + CHUNK_SIZE);
    try {
      await caracteristica.writeValue(chunk);
    } catch (_) {
      // writeWithoutResponse en algunas impresoras
      await caracteristica.writeValueWithoutResponse(chunk);
    }
  }
}

/**
 * Normaliza texto para ASCII puro (ESC/POS no suele manejar UTF-8 sin configuración extra).
 */
function _normalizar(texto) {
  return String(texto || '')
    .replace(/[áàâä]/g, 'a').replace(/[ÁÀÂÄ]/g, 'A')
    .replace(/[éèêë]/g, 'e').replace(/[ÉÈÊË]/g, 'E')
    .replace(/[íìîï]/g, 'i').replace(/[ÍÌÎÏ]/g, 'I')
    .replace(/[óòôö]/g, 'o').replace(/[ÓÒÔÖ]/g, 'O')
    .replace(/[úùûü]/g, 'u').replace(/[ÚÙÛÜ]/g, 'U')
    .replace(/ñ/g, 'n').replace(/Ñ/g, 'N')
    .replace(/[^\x20-\x7E]/g, '?');  // reemplaza cualquier otro carácter no ASCII
}

/**
 * Genera el buffer ESC/POS completo para un acta de infracción.
 *
 * datos: {
 *   municipio, acta, patente, tipo_vehiculo,
 *   subcuadra, motivo, fecha, hora,
 *   monto, inspector, legajo, url_pago
 * }
 */
function generarTicketInfraccion(datos) {
  const ESC = 27, GS = 29, LF = 10;
  const ANCHO = 32;
  const SEP = '-'.repeat(ANCHO);

  const buf = [];

  function push() {
    for (let i = 0; i < arguments.length; i++) buf.push(arguments[i]);
  }

  function escribir(texto) {
    const s = _normalizar(texto);
    for (let i = 0; i < s.length; i++) buf.push(s.charCodeAt(i));
    buf.push(LF);
  }

  function centrar(texto) {
    const s = _normalizar(texto).substring(0, ANCHO);
    const pad = Math.max(0, Math.floor((ANCHO - s.length) / 2));
    return ' '.repeat(pad) + s;
  }

  function campo(etiq, valor) {
    const linea = _normalizar(etiq + ': ' + valor);
    // Si es muy largo, cortar en múltiples líneas
    if (linea.length <= ANCHO) {
      escribir(linea);
    } else {
      escribir(linea.substring(0, ANCHO));
      escribir('  ' + linea.substring(ANCHO));
    }
  }

  // ── Inicializar impresora
  push(ESC, 0x40);

  // ── Encabezado centrado
  push(ESC, 0x61, 0x01);          // alinear centro
  push(ESC, 0x45, 0x01);          // negrita on
  escribir('ACTA DE INFRACCION');
  push(ESC, 0x45, 0x00);          // negrita off
  escribir(_normalizar(datos.municipio));
  escribir(SEP);

  // ── Número de acta
  push(ESC, 0x45, 0x01);
  escribir('N ' + datos.acta);
  push(ESC, 0x45, 0x00);
  escribir(SEP);

  // ── Patente en tamaño grande
  push(GS, 0x21, 0x11);           // doble alto + doble ancho
  escribir(centrar(datos.patente));
  push(GS, 0x21, 0x00);           // tamaño normal
  escribir(centrar(_normalizar(datos.tipo_vehiculo)));
  escribir(SEP);

  // ── Datos (alineación izquierda)
  push(ESC, 0x61, 0x00);
  campo('Subcuadra', datos.subcuadra);
  campo('Motivo', datos.motivo);
  escribir(SEP);
  campo('Fecha', datos.fecha + ' ' + datos.hora + 'hs');
  escribir(SEP);

  // ── Monto centrado y grande
  push(ESC, 0x61, 0x01);
  push(GS, 0x21, 0x11);
  escribir(centrar('$' + datos.monto));
  push(GS, 0x21, 0x00);
  escribir(SEP);

  // ── Inspector
  push(ESC, 0x61, 0x00);
  push(ESC, 0x45, 0x01);
  escribir('Inspector:');
  push(ESC, 0x45, 0x00);
  escribir(_normalizar(datos.inspector));
  if (datos.legajo) campo('Legajo', datos.legajo);
  escribir(SEP);

  // ── Pie: URL de pago (sin QR porque BLE no imprime imágenes)
  push(ESC, 0x61, 0x01);
  escribir('Paga online:');
  escribir(_normalizar(datos.url_pago));

  // ── Avanzar papel y cortar
  push(LF, LF, LF, LF);
  push(GS, 0x56, 0x42, 0x10);    // corte parcial con avance

  return new Uint8Array(buf);
}
