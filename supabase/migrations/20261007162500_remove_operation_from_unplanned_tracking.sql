-- Corrige únicamente el seguimiento adicional creado el 2026-10-07.
-- La programación semanal original, backlog y cierres no se modifican.
delete from programacion.seguimiento_no_programado_v2 n
where regexp_replace(
        translate(upper(coalesce(n.plan_trabajo,'')),'Ó','O'),
        '^[[:space:]]*[0-9]+[[:space:]]*[^[:alnum:]]+[[:space:]]*',''
      ) ~ '^OPERACION([[:space:][:punct:]]|$)'
   or regexp_replace(
        translate(upper(ltrim(coalesce(n.plan_trabajo,''),' -–—:._/|')),'Ó','O'),
        '^[[:space:]]*[0-9]+[[:space:]]*[^[:alnum:]]+[[:space:]]*',''
      ) ~ '^OPERACION([[:space:][:punct:]]|$)'
   or exists (
        select 1
        from programacion.orden_mantenimiento o
        join programacion.plan_trabajo p on p.id=o.plan_trabajo_id
        where o.id=n.orden_mantenimiento_id
          and coalesce(p.es_operacion,false)=true
      );
