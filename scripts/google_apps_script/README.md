# CEK Global MTTO · Sincronización automática Google Sheets → Vercel (sin Cloud)

Este sistema **no utiliza el Web App público de Apps Script** para leer órdenes. Google bloqueaba la solicitud POST entrante desde Vercel con HTTP 403. La integración ahora funciona únicamente como **agente de salida**: Apps Script tiene autorización del propietario del archivo para leer BASE DE DATOS y envía una fotografía validada a la API de CEK Global MTTO.

## Estado de la implementación
- El backend y el frontend de Vercel están preparados para recibir datos de Apps Script.
- La base de datos contiene una cola privada de solicitudes manuales y un registro de actividad del agente.
- La actualización real no se ejecuta hasta que la cuenta propietaria de Google **autorice una vez** `cekActivarSincronizacion`.
- El botón "Sincronizar ahora" crea una solicitud; Apps Script la procesa cada cinco minutos. La actualización diaria ocurre cerca de las 6:00 a. m. Colombia.
- Fuente única: `BASE DE DATOS!A:M`, cuatro especialidades MEC/ELE/MET/SER, deduplicación de OT, exclusión OPERACIÓN.
- No reabrir meses/semanas cerradas ni modificar horas o programaciones originales.

## ÚNICA ACTIVACIÓN NECESARIA EN TU CUENTA DE GOOGLE

1. Entra a tu proyecto privado <https://script.google.com/home> → **CEK Global MTTO Sync** → Editor.
2. Copia y pega el código completo y actualizado de [Code.gs](./Code.gs), reemplazando el anterior, y guarda.
3. En **Configuración del proyecto → Propiedades del script**, confirma que `SHEET_SYNC_SECRET` sea **exactamente el mismo** que configuraste en **Vercel → programacion-team-food → Settings → Environment Variables (Production)**. No compartas la clave, no la pegues en Github. La propiedad antigua `CEK_API_URL` ya no se usa: el código apunta directamente al dominio correcto `https://programacion-team-food.vercel.app`.
4. En el selector de funciones de Apps Script, elige **`cekActivarSincronizacion`** y pulsa **Ejecutar** una sola vez. Autoriza los permisos de acceso al Sheet y las solicitudes HTTPS. Verás el registro `Activado: solicitudes cada 5 min...`. **Esta activación no modifica OT**, sólo verifica lectura y configura activadores.
5. Regresa a <https://programacion-team-food.vercel.app/> → **Seguimiento de programación**. Presiona **Comprobar agente (sin modificar)**. Debe mostrar las filas y OT únicas del mes.
6. Ahora presiona **Sincronizar ahora**. Verás solicitud pendiente y, tras la revisión de Apps Script (aprox. 5 minutos), el estado completado y los indicadores actualizados.

**No necesitas volver a implementar un Web App ni editar el enlace /exec**. El error 403 entrante desaparece porque la aplicación ya no utiliza ese canal.

## Diagnósticos

- **Agente no conectado**: en el editor de Apps Script, ejecuta `cekActivarSincronizacion`; revisa Ejecuciones. Puede que no hayas autorizado o que hayas pegado una versión antigua de Code.gs.
- **HTTP 401 desde Apps Script**: `SHEET_SYNC_SECRET` no coincide con Vercel Production; corrígelo en los dos lugares. Nunca reveles la clave.
- **Lectura de BASE DE DATOS**: ejecuta `cekVerificarFuente` en Apps Script; revisa la cuenta autorizada, el ID del documento y el nombre de la pestaña.
- **Solicitud pendiente**: deja el navegador abierto o vuelve luego; el agente ejecuta la revisión cada cinco minutos. Si el activador falla, revisa el historial de Ejecuciones en Apps Script.
- **No existe la variable en Vercel**: añade `SHEET_SYNC_SECRET` como variable privada para Production y redespliega. Ya no hace falta `APPS_SCRIPT_WEBAPP_URL`.
- **Error de ejecución**: el backend registra la causa y mantiene los cierres anteriores sin alteración. La Lista de Calendario .xlsx sigue disponible como respaldo.

### Seguridad
No dar acceso de editor al proyecto privado de Apps Script a terceros. No compartir tokens por chat, capturas, URLs ni consola. El endpoint de envío requiere firma `Authorization: Bearer` y solo permite el mes actual. El panel sólo permite encolar solicitudes a administradores. La cola y los registros de agente viven en un esquema privado de Supabase.
