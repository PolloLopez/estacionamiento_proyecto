/**
 * impresora_bluetooth.js
 *
 * Conexión con impresora térmica 58mm vía Web Bluetooth API.
 * Soporta los perfiles GATT más comunes para impresoras ESC/POS BLE:
 *   - Genérico 18f0 (el más común en impresoras chinas de 58mm)
 *   - Nordic UART Service / NUS (nRF51822, muy común en módulos BLE baratos)
 *   - Star Micronics BLE
 * Chrome Android 85+ con HTTPS.
 */

'use strict';

// Perfiles conocidos: { servicio, caracteristica }
// Se prueban en orden hasta que uno funcione.
var PERFILES_BLE = [
  // Genérico ESC/POS BLE — el más común en impresoras térmicas de 58mm
  { servicio: '000018f0-0000-1000-8000-00805f9b34fb',
    caract:   '00002af1-0000-1000-8000-00805f9b34fb' },
  // Nordic UART Service (NUS) — módulos nRF51/nRF52 muy usados en impresoras portátiles
  { servicio: '6e400001-b5a3-f393-e0a9-e50e24dcca9e',
    caract:   '6e400002-b5a3-f393-e0a9-e50e24dcca9e' },
  // Star Micronics BLE
  { servicio: 'e7810a71-73ae-499d-8c15-faa9aef0c3f2',
    caract:   'bef8d6c9-9c21-4c9e-b632-bd58c1009f9f' },
  // Alternativo genérico
  { servicio: '49535343-fe7d-4ae5-8fa9-9fafd205e455',
    caract:   '49535343-8841-43f4-a8d4-ecbe34729bb3' },
];

// Lista de todos los UUIDs de servicio para declarar en requestDevice
var UUID_SERVICIOS_OPT = PERFILES_BLE.map(function(p) { return p.servicio; });

// Tamaño máximo de chunk BLE (MTU estándar 20 bytes)
var CHUNK_SIZE = 20;

/**
 * Abre el diálogo para seleccionar impresora.
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
  return _abrirConexion(device);
}

/**
 * Reconecta a impresora previamente autorizada (sin diálogo).
 * Usa getDevices() — disponible en Chrome 85+.
 * Retorna { device, caracteristica, perfil } o null.
 */
async function reconectarImpresora() {
  if (!navigator.bluetooth || typeof navigator.bluetooth.getDevices !== 'function') {
    return null;
  }
  var dispositivos = await navigator.bluetooth.getDevices();
  if (!dispositivos.length) return null;
  try {
    return await _abrirConexion(dispositivos[0]);
  } catch (e) {
    console.warn('[BLE] Reconexión fallida:', e.message);
    return null;
  }
}

/**
 * Conecta al GATT server y encuentra la primera característica de escritura disponible.
 */
async function _abrirConexion(device) {
  var server = await device.gatt.connect();

  // Probar perfiles conocidos primero (más rápido)
  for (var i = 0; i < PERFILES_BLE.length; i++) {
    var perfil = PERFILES_BLE[i];
    try {
      var svc   = await server.getPrimaryService(perfil.servicio);
      var caract = await svc.getCharacteristic(perfil.caract);
      console.log('[BLE] Perfil encontrado:', perfil.servicio);
      return { device: device, caracteristica: caract, perfil: perfil };
    } catch (_) {}
  }

  // Descubrimiento automático: listar todos los servicios y buscar write
  console.log('[BLE] Perfiles conocidos no encontrados, descubriendo servicios...');
  var servicios = await server.getPrimaryServices();
  for (var s = 0; s < servicios.length; s++) {
    try {
      var caracts = await servicios[s].getCharacteristics();
      for (var c = 0; c < caracts.length; c++) {
        var props = caracts[c].properties;
        if (props.write || props.writeWithoutResponse) {
          console.log('[BLE] Característica descubierta:', servicios[s].uuid, caracts[c].uuid);
          return {
            device: device,
            caracteristica: caracts[c],
            perfil: { servicio: servicios[s].uuid, caract: caracts[c].uuid }
          };
        }
      }
    } catch (_) {}
  }

  throw new Error('No se encontró característica de escritura. Revisá los logs de la consola.');
}

/**
 * Devuelve un string con los servicios/características del dispositivo (para diagnóstico).
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
        if (p.read)               flags.push('read');
        if (p.write)              flags.push('write');
        if (p.writeWithoutResponse) flags.push('writeNoResp');
        if (p.notify)             flags.push('notify');
        resultado += '  Char: ' + caracts[c].uuid + ' [' + flags.join(', ') + ']\n';
      }
    } catch (e) {
      resultado += '  (sin acceso a características)\n';
    }
    resultado += '\n';
  }

  device.gatt.disconnect();
  return resultado;
}

/**
 * Envía datos en chunks de CHUNK_SIZE bytes.
 */
async function enviarImpresion(caracteristica, datos) {
  for (var i = 0; i < datos.length; i += CHUNK_SIZE) {
    var chunk = datos.slice(i, i + CHUNK_SIZE);
    try {
      await caracteristica.writeValue(chunk);
    } catch (_) {
      await caracteristica.writeValueWithoutResponse(chunk);
    }
    // Pequeña pausa entre chunks para no saturar el buffer BLE
    await new Promise(function(r) { setTimeout(r, 20); });
  }
}

/**
 * Normaliza texto a ASCII puro (las impresoras térmicas básicas no soportan UTF-8).
 */
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
 * Genera un Uint8Array ESC/POS para el ticket de infracción.
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
    var norm = _norm(s).substring(0, ANCHO * 2);  // máximo 2 líneas
    for (var i = 0; i < norm.length; i++) buf.push(norm.charCodeAt(i));
    buf.push(LF);
  }

  function centrar(s) {
    var norm = _norm(s).substring(0, ANCHO);
    var pad  = Math.max(0, Math.floor((ANCHO - norm.length) / 2));
    return Array(pad + 1).join(' ') + norm;
  }

  // Inicializar
  push(ESC, 0x40);

  // Encabezado
  push(ESC, 0x61, 0x01);          // centro
  push(ESC, 0x45, 0x01);          // negrita
  linea('ACTA DE INFRACCION');
  push(ESC, 0x45, 0x00);
  linea(_norm(d.municipio));
  linea(SEP);

  push(ESC, 0x45, 0x01);
  linea('N ' + d.acta);
  push(ESC, 0x45, 0x00);
  linea(SEP);

  // Patente grande
  push(GS, 0x21, 0x11);           // doble alto+ancho
  linea(centrar(d.patente));
  push(GS, 0x21, 0x00);
  linea(centrar(_norm(d.tipo_vehiculo)));
  linea(SEP);

  // Datos
  push(ESC, 0x61, 0x00);          // izquierda
  linea(_norm('Subcuadra: ' + d.subcuadra));
  linea(_norm('Motivo: ' + d.motivo));
  linea(SEP);
  linea('Fecha: ' + d.fecha + ' ' + d.hora + 'hs');
  linea(SEP);

  // Monto
  push(ESC, 0x61, 0x01);
  push(GS, 0x21, 0x11);
  push(ESC, 0x45, 0x01);
  linea(centrar('$' + d.monto));
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

  // URL pago
  push(ESC, 0x61, 0x01);
  linea('Paga online:');
  linea(_norm(d.url_pago));

  // Avance y corte
  push(LF, LF, LF, LF);
  push(GS, 0x56, 0x42, 0x10);

  return new Uint8Array(buf);
}

/**
 * Genera un ticket de prueba mínimo para verificar que la impresora recibe datos.
 */
function generarTicketPrueba() {
  var buf = [];
  function push() { for (var i=0;i<arguments.length;i++) buf.push(arguments[i]); }
  function linea(s) { for(var i=0;i<s.length;i++) buf.push(s.charCodeAt(i)); buf.push(10); }

  push(27, 0x40);                  // init
  push(27, 0x61, 0x01);            // centro
  push(27, 0x45, 0x01);            // negrita
  linea('--- PRUEBA ---');
  push(27, 0x45, 0x00);
  linea('Impresora OK');
  linea(new Date().toLocaleTimeString());
  push(10, 10, 10, 10);
  push(29, 0x56, 0x42, 0x10);     // corte

  return new Uint8Array(buf);
}
