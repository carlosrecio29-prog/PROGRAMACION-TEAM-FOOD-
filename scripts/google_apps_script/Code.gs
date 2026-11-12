/**
 * CEK Global MTTO · Sincronización SOLO ENVÍO Google Apps Script → Vercel.
 * No depende de publicar un Web App ni de solicitudes POST de Vercel hacia Google.
 * Sin Google Cloud ni tarjeta. No comparte secretos en URLs, GitHub ni logs.
 *
 * Una vez pegado: ejecutar cekActivarSincronizacion (solicitará autorización).
 * El botón de CEK Global MTTO encola solicitudes que procesa este script cada 5 min.
 * La actualización diaria de todo el mes se ejecuta cerca de las 6 a. m. Bogotá.
 */
const CEK_SPREADSHEET_ID = '1Or0L7epumDQUsUuLjb4FXt-7FRbC16pJ8-b0VwROwdo';
const CEK_SHEET_TITLE = 'BASE DE DATOS';
const CEK_API_URL = 'https://programacion-team-food.vercel.app';
const CEK_TZ = 'America/Bogota';
const CEK_MONTHS = ['ENERO','FEBRERO','MARZO','ABRIL','MAYO','JUNIO',
                    'JULIO','AGOSTO','SEPTIEMBRE','OCTUBRE','NOVIEMBRE','DICIEMBRE'];
const CEK_SPECIALTIES = ['ELE','MEC','MET','SER'];
const CEK_MAX_ROWS = 15000;

function cekSecret_() {
  const secret = PropertiesService.getScriptProperties().getProperty('SHEET_SYNC_SECRET') || '';
  if (secret.length < 32) {
    throw new Error('Falta SHEET_SYNC_SECRET en Propiedades del script (mínimo 32 caracteres).');
  }
  return secret;
}
function cekNorm_(value) {
  return String(value || '').normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '').trim().toUpperCase();
}
function cekTiempo_() {
  const now = new Date();
  return {
    year: Number(Utilities.formatDate(now, CEK_TZ, 'yyyy')),
    month: Number(Utilities.formatDate(now, CEK_TZ, 'M'))
  };
}
function cekLeerDatos_(year, month, targets) {
  if (!Number.isInteger(year) || year < 2026 || year > 2100 ||
      !Number.isInteger(month) || month < 1 || month > 12) {
    throw new Error('Periodo inválido.');
  }
  const book = SpreadsheetApp.openById(CEK_SPREADSHEET_ID);
  const sheet = book.getSheetByName(CEK_SHEET_TITLE);
  if (!sheet) throw new Error('No existe BASE DE DATOS en la hoja maestra.');
  const count = sheet.getLastRow();
  if (count < 2) throw new Error('BASE DE DATOS sin filas.');
  const raw = sheet.getRange(1, 1, count, 13).getDisplayValues();
  const items = [raw[0].concat(['__ORIGINAL_ROW'])];
  const target = CEK_MONTHS[month - 1];
  const needed = Object.create(null);
  (targets || []).forEach(function(ot) {
    const code = cekNorm_(ot.numero_ot);
    if (code) needed[code] = ot;
  });
  const latestEarlier = Object.create(null);
  for (let i = 1; i < raw.length; i++) {
    const row = raw[i];
    const rowMonth = CEK_MONTHS.indexOf(cekNorm_(row[0])) + 1;
    const rowYear = Number(String(row[10] || '').trim());
    const ot = cekNorm_(row[2]);
    const previous = needed[ot];
    if (previous && rowMonth > 0 && Number.isInteger(rowYear) &&
        rowYear >= 2020 && (rowYear < year || (rowYear === year && rowMonth < month)) &&
        cekNorm_(row[3]) === cekNorm_(previous.especialidad) &&
        cekNorm_(row[4]) === cekNorm_(previous.activo_codigo) &&
        cekNorm_(row[12]) === cekNorm_(previous.plan_trabajo)) {
      const rank = rowYear * 12 + rowMonth;
      const candidate = {
        numero_ot: ot, especialidad: cekNorm_(row[3]),
        activo_codigo: String(row[4]), plan_trabajo: String(row[12]),
        estado: cekNorm_(row[7]), mes_fuente: rowMonth,
        anio_fuente: rowYear, rank: rank, conflicto: false
      };
      const old = latestEarlier[ot];
      if (!old || candidate.rank > old.rank) {
        latestEarlier[ot] = candidate;
      } else if (old.rank === rank && old.estado !== candidate.estado) {
        old.conflicto = true;
      }
    }
    if (cekNorm_(row[0]) !== target || CEK_SPECIALTIES.indexOf(cekNorm_(row[3])) < 0) continue;
    if (!row[2]) continue;
    const explicitYear = String(row[10] || '').trim();
    if (/^20\d{2}$/.test(explicitYear) && Number(explicitYear) !== year) continue;
    // El modelo Pydantic de la API admite exclusivamente celdas de texto.
    items.push(row.concat([String(i + 1)]));
    if (items.length > CEK_MAX_ROWS) throw new Error('El mes supera el límite permitido de filas.');
  }
  if (items.length < 2) throw new Error('No hay órdenes en el mes seleccionado.');
  const historicos = Object.keys(latestEarlier).map(function(ot) { return latestEarlier[ot]; })
    .filter(function(item) {
      const plan = cekNorm_(item.plan_trabajo).replace(/^\d+\s*[-–—:._/|]+\s*/, '');
      return !item.conflicto && item.estado === 'FINALIZADA' &&
             !/^OPERACION(?:\b|\s|[-–—:._/|])/.test(plan);
    })
    .map(function(item) {
      return {
        numero_ot: item.numero_ot, especialidad: item.especialidad,
        activo_codigo: item.activo_codigo, plan_trabajo: item.plan_trabajo,
        estado: item.estado, mes_fuente: item.mes_fuente,
        anio_fuente: item.anio_fuente
      };
    });
  return {values: items, historicos: historicos};
}
function cekSnapshot_(year, month) {
  return cekLeerDatos_(year, month, []).values;
}
function cekResumen_(values, year, month) {
  const seen = Object.create(null);
  const conflicting = Object.create(null);
  const summary = {
    year: year, month: month, filas: values.length - 1,
    unicas: 0, repetidas: 0, conflictos: 0, operaciones: 0,
    porEspecialidad: {}
  };
  for (let i = 1; i < values.length; i++) {
    const row = values[i];
    const ot = cekNorm_(row[2]);
    const spec = cekNorm_(row[3]);
    const status = cekNorm_(row[7]);
    const signature = [spec, cekNorm_(row[4]), cekNorm_(row[12]), status].join('|');
    if (seen[ot]) {
      summary.repetidas++;
      if (seen[ot] !== signature) conflicting[ot] = true;
    } else {
      summary.unicas++;
      seen[ot] = signature;
    }
    summary.porEspecialidad[spec] = (summary.porEspecialidad[spec] || 0) + 1;
    const plan = cekNorm_(row[12]).replace(/^\d+\s*[-–—:._/|]+\s*/, '');
    if (/^OPERACION(?:\b|\s|[-–—:._/|])/.test(plan)) summary.operaciones++;
  }
  summary.conflictos = Object.keys(conflicting).length;
  return summary;
}
function cekApi_(path, method, payload) {
  const options = {
    method: method,
    headers: {'Authorization': 'Bearer ' + cekSecret_()},
    contentType: 'application/json',
    muteHttpExceptions: true,
    followRedirects: true
  };
  if (payload !== undefined) options.payload = JSON.stringify(payload);
  const response = UrlFetchApp.fetch(CEK_API_URL + path, options);
  const code = response.getResponseCode();
  let body;
  try {
    body = JSON.parse(response.getContentText() || '{}');
  } catch (err) {
    throw new Error('La API CEK Global MTTO devolvió una respuesta no JSON (HTTP ' + code + ').');
  }
  if (code < 200 || code >= 300 || !body.ok) {
    // No registrar payload, token ni número de OT en errores.
    const reason = (body && body.detail && String(body.detail).slice(0, 180)) ||
                   ('HTTP ' + code);
    throw new Error('No se pudo comunicar con CEK Global MTTO: ' + reason);
  }
  return body;
}

/** Sólo lee el origen; no escribe OT, H-H ni cierres. */
function cekVerificarFuente() {
  const date = cekTiempo_();
  const counts = cekResumen_(cekSnapshot_(date.year, date.month), date.year, date.month);
  console.log('BASE DE DATOS · Verificación sólo lectura: ' + JSON.stringify(counts));
  return counts;
}

/** Valida lectura de la fuente y conexión con el servidor SIN actualizar las OT. */
function cekVerificarServidor() {
  const report = cekVerificarFuente();
  const result = cekApi_('/api/v2/sheet-sync/heartbeat', 'post', report);
  console.log('Servidor CEK Global MTTO conectado. No se alteraron OT. Mes: ' + result.periodo);
  return report;
}

function cekEnviarMes_(year, month, requestId) {
  // The signed API returns only prior-month OT actually scheduled in
  // an unclosed week. Previous closures remain read-only.
  const response = cekApi_('/api/v2/sheet-sync/historical-targets', 'get');
  const loaded = cekLeerDatos_(year, month, response.targets || []);
  const body = {year: year, month: month, values: loaded.values,
                historicos: loaded.historicos};
  console.log('Estados históricos finalizados detectados para programación abierta: ' +
              loaded.historicos.length);
  if (requestId) body.request_id = requestId;
  const result = cekApi_('/api/v2/sheet-sync/push', 'post', body);
  console.log('Sincronización completada. Solicitud: ' + (requestId || 'diaria') +
              '; OT válidas: ' + result.ots_validas +
              '; estados modificados: ' + result.estados_cambiados);
  return result;
}

/** El activador de cada cinco minutos procesa las solicitudes del administrador. */
function cekAtenderSolicitudes() {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(1000)) return;
  try {
    cekVerificarServidor();
    const response = cekApi_('/api/v2/sheet-sync/pending', 'get');
    const pending = response.requests || [];
    pending.forEach(function(item) {
      const today = cekTiempo_();
      if (item.year !== today.year || item.month !== today.month) return;
      cekEnviarMes_(item.year, item.month, item.id);
    });
    if (!pending.length) console.log('CEK Global MTTO conectado; ninguna solicitud pendiente.');
  } finally {
    lock.releaseLock();
  }
}

/** Sincronización diaria de las cuatro especialidades, aproximadamente a las 06:00. */
function cekSincronizacionDiaria() {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(1000)) return;
  try {
    const today = cekTiempo_();
    cekVerificarServidor();
    cekEnviarMes_(today.year, today.month, null);
  } finally {
    lock.releaseLock();
  }
}

/**
 * ACTIVAR UNA SOLA VEZ DESDE APPS SCRIPT.
 * Instala trigger de 5 minutos para solicitudes + trigger diario 06:00 Bogotá.
 * Antes verifica hoja, permisos y token sin tocar OT.
 */
function cekActivarSincronizacion() {
  cekVerificarServidor();
  const names = [
    'cekAtenderSolicitudes', 'cekSincronizacionDiaria',
    'cekInstalarTriggerDiario'
  ];
  ScriptApp.getProjectTriggers().forEach(function(t) {
    if (names.indexOf(t.getHandlerFunction()) >= 0) {
      ScriptApp.deleteTrigger(t);
    }
  });
  ScriptApp.newTrigger('cekAtenderSolicitudes')
    .timeBased().everyMinutes(5).create();
  ScriptApp.newTrigger('cekSincronizacionDiaria')
    .timeBased().atHour(6).nearMinute(0).everyDays(1)
    .inTimezone(CEK_TZ).create();
  console.log('Activado: solicitudes cada 5 min y actualización diaria cerca de las 06:00 Colombia.');
}

/** Compatibilidad con versiones anteriores. */
function cekInstalarTriggerDiario() {
  cekActivarSincronizacion();
}

/** Prueba segura: NO actualizar OT, solo confirmar conexión. */
function cekProbarAhora() {
  return cekVerificarServidor();
}

/** Funciones Web App antiguas inhabilitadas: no se usa POST desde Vercel. */
function doGet() {
  return ContentService.createTextOutput(JSON.stringify({ok: false, error: 'Servicio deshabilitado; utiliza el agente de salida'}))
    .setMimeType(ContentService.MimeType.JSON);
}
function doPost() {
  return doGet();
}
