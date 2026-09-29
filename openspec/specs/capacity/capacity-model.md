# Modelo de capacidad

La capacidad se calcula a partir de la programación real de técnicos, sus especialidades, turnos y ausencias.

## Regla de capacidad en dos etapas

1. Las horas asignadas por turno conforman las **H-H brutas**.
2. De las H-H brutas se toma el **80% como H-H efectivas**.
3. El **20% inicial no es correctivo**: representa tiempo operativo no programable asociado a cambio de ropa, charla de inicio, alistamiento, búsqueda de herramientas, desplazamientos y actividades similares.
4. Sobre las H-H efectivas se aplica una segunda distribución:
   - **80% para mantenimiento preventivo programable**.
   - **20% para correctivo / reserva operativa**.

Ejemplo:

- 200 H-H brutas.
- 40 H-H de tiempo operativo no programable.
- 160 H-H efectivas.
- 128 H-H objetivo preventivo.
- 32 H-H correctivo / reserva.

La fórmula implementada en `capacity_split` es:

```
effective = available * 0.80
preventive = effective * 0.80
corrective = effective * 0.20
initial_margin = available - effective
```

Por compatibilidad interna, el campo `initial_margin` conserva su nombre técnico, pero en la interfaz debe mostrarse como **Alistamiento / tiempo operativo no programable**.

## Especialidad del técnico

La especialidad importada del software se conserva en `tecnico.especialidad`.

Cuando el usuario cambia la especialidad desde Programación de técnicos, el valor se guarda en `tecnico.especialidad_app` y tiene prioridad para calcular `especialidad_efectiva`.

Esto permite mover un técnico entre MEC, ELE, MET o SER desde la aplicación sin perder la especialidad de origen del software.
