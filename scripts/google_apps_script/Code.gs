/**
 * CEK Global MTTO · Google Apps Script
 * Sin Google Cloud Console, tarjeta ni APIs avanzadas.
 * Fuente ÚNICA: BASE DE DATOS (A:M).
 *
 * RECOMENDADO: crear proyecto Apps Script independiente/privado (no vinculado\n * al Sheet compartido) para proteger las propiedades frente a otros editores.\n *\n * CONFIGURACIÓN (Propiedades del script):
 *   SHEET_SYNC_SECRET: token aleatorio idéntico al de Vercel (mínimo 32 caracteres)
 *   CEK_API_URL: https://programacion-team-food-cek-global.vercel.app
 *
 * Web App: ejecutar como "Yo"; acceso "Cualquier persona" (URL no pública).
 * El contenido de la hoja NO se revela sin validar SHEET_SYNC_SECRET.
 */
const CEK_SPREADSHEET_ID = '1Or0L7epumDQUsUuLjb4FXt-7FRbC16pJ8-b0VwROwdo';
const CEK_SHEET_TITLE = 'BASE DE DATOS';
const CEK_TZ = 'America/Bogota';
const CEK_MONTHS = [
  'ENERO', 'FEBRERO', 'MARZO', 'ABRIL', 'MAYO', 'JUNIO',
  'JULIO', 'AGOSTO', 'SEPTIEMBRE', 'OCTUBRE', 'NOVIEMBRE', 'DICIEMBRE'
];
const CEK_SPECIALTIES = ['ELE', 'MEC', 'MET', 'SER'];
const CEK_MAX_ROWS = 15000;

function cekProps_() {
  const p = PropertiesService.getScriptProperties();
  const secret = p.getProperty('SHEET_SYNC_SECRET') || '';
  const appUrl = (p.getProperty('CEK_API_URL') || '').replace(/\/+$/, '');
  if (secret.length < 32) throw new Error('Configure SHEET_SYNC_SECRET con 32 o más caracteres.');
  if (!/^https:\/\/[a-z0-9.-]+(?:\:[0-9]+)?$/i.test(appUrl)) {
    throw new Error('Configure CEK_API_URL con un origen HTTPS, sin rutas.');
  }
  return { secret: secret, appUrl: appUrl };
}

function cekNormalizar_(value) {
  return String(value || '')
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .trim().toUpperCase();
}

function cekSnapshot_(year, month) {
  if (!Number.isInteger(year) || year < 2026 || year > 2100 ||
      !Number.isInteger(month) || month < 1 || month > 12) {
    throw new Error('Período de sincronización inválido.');
  }
  const book = SpreadsheetApp.openById(CEK_SPREADSHEET_ID);
  const sheet = book.getSheetByName(CEK_SHEET_TITLE);
  if (!sheet) throw new Error('No se encuentra la pestaña BASE DE DATOS.');
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) throw new Error('BASE DE DATOS no contiene órdenes.');
  const values = sheet.getRange(1, 1, lastRow, 13).getDisplayValues();
  const header = values[0].concat(['__ORIGINAL_ROW']);
  const items = [header];

  const monthName = CEK_MONTHS[month - 1];
  for (let i = 1; i < values.length; i++) {
    const row = values[i];
    if (cekNormalizar_(row[0]) !== monthName) continue;
    if (CEK_SPECIALTIES.indexOf(cekNormalizar_(row[3])) < 0) continue;
    if (!row[2]) continue;
    // AÑO puede estar vacío. Las OT heredadas -25/-24 siguen siendo elegibles
    // si se encuentran explícitamente dentro del mes seleccionado.
    const explicitYear = String(row[10] || '').trim();
    if (/^20\d\d$/.test(explicitYear) && Number(explicitYear) !== year) continue;
    items.push(row.concat([i + 1]));
    if (items.length > CEK_MAX_ROWS) throw new Error('Demasiadas filas del período; revisar límite CEK_MAX_ROWS.');
  }
  if (items.length <= 1) throw new Error('No se encontraron OT para el período solicitado.');
  return items;
}

function cekJson_(data) {
  return ContentService.createTextOutput(JSON.stringify(data))
    .setMimeType(ContentService.MimeType.JSON);
}

/**
 * La aplicación llama este Web App mediante POST para el botón manual.
 * El token se envía en el CUERPO HTTPS, nunca en la URL.
 */
function doPost(e) {
  try {
    const body = JSON.parse((e && e.postData && e.postData.contents) || '{}');
    const cfg = cekProps_();
    if (body.action !== 'snapshot' || !body.secret ||
        body.secret !== cfg.secret) {
      return cekJson_({ok: false, error: 'No autorizado'});
    }
    const year = Number(body.year);
    const month = Number(body.month);
    const rows = cekSnapshot_(year, month);
    return cekJson_({ok: true, year: year, month: month, values: rows});
  } catch (err) {
    // No incluir secretos ni contenido de las órdenes en el mensaje.
    return cekJson_({ok: false, error: 'Error al leer BASE DE DATOS. Revise las ejecuciones de Apps Script.'});
  }
}

function doGet() {
  return cekJson_({ok: false, error: 'No autorizado'});
}

/**
 * Sincronización automática push: Google Sheets → API CEK Global MTTO.
 * Se invoca mediante activador de reloj, aproximadamente a las 06:00.
 */
function cekSincronizacionDiaria() {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(1000)) return;
  try {
    const cfg = cekProps_();
    const now = new Date();
    const year = Number(Utilities.formatDate(now, CEK_TZ, 'yyyy'));
    const month = Number(Utilities.formatDate(now, CEK_TZ, 'M'));
    const snapshot = cekSnapshot_(year, month);
    const response = UrlFetchApp.fetch(cfg.appUrl + '/api/v2/sheet-sync/push', {
      method: 'post',
      contentType: 'application/json',
      headers: {'Authorization': 'Bearer ' + cfg.secret},
      payload: JSON.stringify({year: year, month: month, values: snapshot}),
      muteHttpExceptions: true,
      followRedirects: true,
    });
    const status = response.getResponseCode();
    const output = JSON.parse(response.getContentText() || '{}');
    if (status < 200 || status >= 300 || !output.ok) {
      throw new Error('La API CEK Global MTTO rechazó la sincronización (HTTP ' + status + ').');
    }
    console.log('Sincronización registrada, ID: ' + output.sincronizacion_id +
                ', OT válidas: ' + output.ots_validas);
  } finally {
    lock.releaseLock();
  }
}

/**
 * Ejecutar UNA sola vez desde el editor Apps Script.
 * Elimina exclusivamente triggers anteriores de cekSincronizacionDiaria.
 * Apps Script puede ejecutar ±15 min respecto de las 6:00 a. m.
 */
function cekInstalarTriggerDiario() {
  cekProps_();
  ScriptApp.getProjectTriggers()
    .filter(function(t) { return t.getHandlerFunction() === 'cekSincronizacionDiaria'; })
    .forEach(function(t) { ScriptApp.deleteTrigger(t); });
  ScriptApp.newTrigger('cekSincronizacionDiaria')
    .timeBased()
    .atHour(6)
    .nearMinute(0)
    .everyDays(1)
    .inTimezone(CEK_TZ)
    .create();
  console.log('Activador diario configurado alrededor de las 06:00 de Colombia.');
}

/** Ejecutar opcionalmente desde Apps Script para probar sin esperar al trigger. */
function cekProbarAhora() {
  cekSincronizacionDiaria();
}
