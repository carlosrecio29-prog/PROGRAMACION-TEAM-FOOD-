CREATE SCHEMA IF NOT EXISTS maestro;
CREATE SCHEMA IF NOT EXISTS programacion;
CREATE SCHEMA IF NOT EXISTS sistema;
CREATE SCHEMA IF NOT EXISTS reportes;

-- MAESTRO
ALTER TABLE IF EXISTS mantenimiento.especialidad SET SCHEMA maestro;
ALTER TABLE IF EXISTS mantenimiento.activo SET SCHEMA maestro;
ALTER TABLE IF EXISTS mantenimiento.grupo_plan_trabajo SET SCHEMA maestro;
ALTER TABLE IF EXISTS mantenimiento.plan_trabajo SET SCHEMA maestro;
ALTER TABLE IF EXISTS mantenimiento.actividad_maestra SET SCHEMA maestro;
ALTER TABLE IF EXISTS mantenimiento.tecnico SET SCHEMA maestro;
ALTER TABLE IF EXISTS mantenimiento.turno SET SCHEMA maestro;

-- SISTEMA / auxiliares técnicos
ALTER TABLE IF EXISTS mantenimiento.importacion SET SCHEMA sistema;
ALTER TABLE IF EXISTS mantenimiento.importacion_error SET SCHEMA sistema;
ALTER TABLE IF EXISTS mantenimiento.sincronizacion_fuente_maestra SET SCHEMA sistema;
ALTER TABLE IF EXISTS mantenimiento.tecnico_alias SET SCHEMA sistema;
ALTER TABLE IF EXISTS mantenimiento.turno_alias SET SCHEMA sistema;

-- PROGRAMACIÓN / operación
ALTER TABLE IF EXISTS mantenimiento.motivo_no_ejecucion SET SCHEMA programacion;
ALTER TABLE IF EXISTS mantenimiento.programacion_tecnico SET SCHEMA programacion;
ALTER TABLE IF EXISTS mantenimiento.periodo_mensual SET SCHEMA programacion;
ALTER TABLE IF EXISTS mantenimiento.pmp SET SCHEMA programacion;
ALTER TABLE IF EXISTS mantenimiento.orden_mantenimiento SET SCHEMA programacion;
ALTER TABLE IF EXISTS mantenimiento.orden_estado_historial SET SCHEMA programacion;
ALTER TABLE IF EXISTS mantenimiento.periodo_semanal SET SCHEMA programacion;
ALTER TABLE IF EXISTS mantenimiento.programacion_semanal SET SCHEMA programacion;
ALTER TABLE IF EXISTS mantenimiento.programacion_version SET SCHEMA programacion;
ALTER TABLE IF EXISTS mantenimiento.programacion_item SET SCHEMA programacion;
ALTER TABLE IF EXISTS mantenimiento.cierre_semanal SET SCHEMA programacion;
ALTER TABLE IF EXISTS mantenimiento.cierre_item SET SCHEMA programacion;

-- REPORTES / vistas
ALTER VIEW IF EXISTS mantenimiento.vw_backlog SET SCHEMA reportes;
ALTER VIEW IF EXISTS mantenimiento.vw_catalogo_actividades_planta SET SCHEMA reportes;
ALTER VIEW IF EXISTS mantenimiento.vw_hh_tecnico_dia SET SCHEMA reportes;
ALTER VIEW IF EXISTS mantenimiento.vw_maestro_planes SET SCHEMA reportes;
ALTER VIEW IF EXISTS mantenimiento.vw_pmp_calculado SET SCHEMA reportes;

-- Función heredada del modelo anterior
DROP FUNCTION IF EXISTS mantenimiento.sincronizar_actividad_maestra_desde_pmp(bigint);

COMMENT ON SCHEMA maestro IS
  'Datos maestros TEAM FOOD: activos, planes, grupos, personal y turnos.';
COMMENT ON SCHEMA programacion IS
  'PMP, órdenes, disponibilidad y programación/cierre semanal.';
COMMENT ON SCHEMA sistema IS
  'Importaciones, auditoría, aliases técnicos e historial de migraciones.';
COMMENT ON SCHEMA reportes IS
  'Vistas de consulta y reportes para la aplicación.';
