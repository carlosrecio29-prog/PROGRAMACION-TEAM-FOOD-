# Activar CEK Global MTTO con Google Apps Script (sin Google Cloud ni tarjeta)

## 1. Crear un script privado para leer Google Sheets
1. Desde tu cuenta de Google abre https://script.google.com/home/projects/create y crea un proyecto independiente llamado **CEK Global MTTO Sync**.
2. Reemplaza su `Code.gs` por el contenido de [Code.gs](./Code.gs) y guarda. Si ya publicaste el Web App, entra en **Implementar → Gestionar implementaciones → Editar → Nueva versión → Implementar** para que la URL /exec ejecute el código actualizado.
3. El script utiliza `SpreadsheetApp.openById` para leer tu hoja, por lo que no es necesario vincularlo directamente al libro. La lectura manual usa solamente `SHEET_SYNC_SECRET`; `CEK_API_URL` es necesario para el trigger diario.
4. Se recomienda un proyecto **privado independiente** para que otros editores del Google Sheets no puedan ver las claves del script.
5. Solo consulta `BASE DE DATOS`; no modifica la hoja ni lee las pestañas por especialidad.

## 2. Configurar el secreto y destino
En Apps Script, **Configuración del proyecto → Propiedades del script**:
- `SHEET_SYNC_SECRET`: genera una clave privada aleatoria de al menos 32 caracteres (idealmente 48+ con gestor de contraseñas).
- `CEK_API_URL`: `https://programacion-team-food.vercel.app`

No compartas la clave privada en chats, capturas, Github, Google Sheets ni con usuarios de solo lectura. Ten presente que otras personas con acceso de editor al proyecto de Apps Script podrían acceder a sus propiedades; limita el acceso de editores.

## 3. Publicar Web App para el botón manual
1. **Implementar → Nueva implementación → Aplicación web**.
2. Ejecutar como: **Yo**.
3. Quién tiene acceso: **Cualquier persona** (esta opción permite peticiones del servidor de Vercel; no hace público el contenido de Google Sheets).
4. Autoriza los permisos que solicita Apps Script.
5. Copia la URL `https://script.google.com/macros/s/.../exec`.

**Seguridad**: `doPost` exige un secreto privado antes de devolver datos y `doGet` jamás muestra órdenes. No publiques el secreto junto con la URL. La URL no debería difundirse públicamente. Si tu organización no permite el acceso «Cualquier persona» para apps web, el botón bajo esta arquitectura no funcionará; el trigger diario puede seguir funcionando.

## 4. Configurar Vercel (Production)
En **CEK GLOBAL → programacion-team-food → Settings → Environment Variables** añade:

| Clave | Valor |
|---|---|
| `SHEET_SYNC_SECRET` | El MISMO secreto privado de Apps Script |
| `APPS_SCRIPT_WEBAPP_URL` | URL del paso 3, terminada en `/exec` |

Marca el entorno **Production**, configura como *Sensitive/Encrypted* cuando esté disponible y **redepliega** la aplicación para aplicar las variables. No agregues estas claves al repositorio.

No se necesita `GOOGLE_SHEETS_SERVICE_ACCOUNT_JSON` ni `CRON_SECRET` (claves del diseño anterior). No activamos Vercel Cron.

## 5. Probar
1. Ejecuta primero **`cekVerificarFuente`**. Es **solo lectura**: muestra por especialidad cuántas filas, OT únicas, repetidas y OPERACIÓN encontró, sin modificar la aplicación.
2. Confirma que el resultado corresponde al mes esperado. Si no corresponde, **no ejecutes** la prueba de envío.
3. Después ejecuta **`cekProbarAhora`** y autoriza Apps Script si Google te lo solicita. Esta función **sí** actualiza el seguimiento real de noviembre.
4. Comprueba en **Ejecuciones** que aparezca el ID de sincronización sin errores.
5. Entra a CEK Global MTTO como administrador → **Seguimiento de programación** → pulsa **Sincronizar ahora**.
6. Verifica la bitácora, duplicados y cierres históricos. Luego ejecuta **`cekInstalarTriggerDiario`** una sola vez y revisa el panel «Desencadenadores».

El activador se programa en torno a **06:00 America/Bogota**, con tolerancia temporal de Google, aproximadamente ±15 minutos. Una sincronización manual no reemplaza la ejecución diaria.

## Manejo de fallos
- Si falta una variable, el botón estará deshabilitado y mostrará la configuración pendiente.
- Si Apps Script no responde, no se reemplazan las órdenes por información incompleta.
- Si hay OT duplicada con estados contradictorios, se señala para revisión y no se cambia esa OT.
- El sistema solo registra avances provisionales en semanas abiertas. Los cierres aprobados permanecen protegidos.
- Si el Web App cambia de implementación, actualiza `APPS_SCRIPT_WEBAPP_URL` en Vercel.
- Si sospechas filtración de `SHEET_SYNC_SECRET`, genera otro y actualízalo en ambas plataformas.

## Diagnóstico sin riesgo
En la aplicación, botón **Probar conexión (sin modificar)**. Se consulta el Apps Script con la clave de Vercel y se muestran los conteos sin escribir en Supabase. Solo después de que el resultado sea correcto se habilita **Sincronizar ahora**. Si responde que la clave no coincide, actualiza `SHEET_SYNC_SECRET` en ambos entornos sin enviarla por chat. Si responde que no fue posible leer la hoja, vuelve a autorizar Apps Script y revisa su registro de Ejecuciones.
