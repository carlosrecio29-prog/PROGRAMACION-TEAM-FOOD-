from io import BytesIO
from openpyxl import Workbook
from backend.parsers.operational import parse_order_states, parse_monthly_planning

def xlsx(rows):
    wb=Workbook(); ws=wb.active
    for row in rows: ws.append(row)
    b=BytesIO(); wb.save(b); return b.getvalue()

def test_order_states():
    p=parse_order_states(xlsx([["Orden","Estado"],[123,"FINALIZADA"],[124,"PENDIENTE"]]))
    assert len(p.rows)==2 and p.rows[0]["order_number"]=="123"

def test_planning():
    headers=["Activo","Especialidad","Orden","PlanTrabajo","TiempoPlaneado","Estado","FechaPlaneadaInicio"]
    p=parse_monthly_planning(xlsx([headers,["A1","MEC","SIN ASIGNAR","100-RUTINA",60,"PENDIENTE","2026-09-01"]]))
    assert len(p.rows)==1 and p.rows[0]["plan_canonical"]=="RUTINA"
