from datetime import date, datetime, timezone
from io import BytesIO

import pytest
from openpyxl import load_workbook

from backend.services import v2_closure_service as service


class Result:
    def __init__(self, rows=None, one=None):
        self.rows = rows or []
        self.one = one
    def mappings(self):
        return self
    def first(self):
        return self.one
    def all(self):
        return self.rows


def _engine(operations=False, closed=False):
    class Conn:
        def execute(self, stmt, params):
            query = str(stmt)
            if "SELECT ps.id,ps.semana_inicio" in query:
                return Result(one={
                    "id":50, "semana_inicio":date(2026,11,5),
                    "semana_fin":date(2026,11,11),
                    "especialidad":"ELE",
                    "estado":"CERRADA" if closed else "GUARDADA",
                })
            if "FROM programacion.google_sheet_sync_run_v2" in query:
                return Result(one={
                    "id":20,
                    "terminado_en":datetime(2026,11,12,19,0,tzinfo=timezone.utc),
                })
            if "historico_finalizada" in query:
                return Result(rows=[
                    {"programacion_item_id":1,"numero_ot":"OT-12907-26",
                     "activo_codigo":"BA-SI-IG-AA28",
                     "plan_clave_software":"48-RUTINA DE MANTENIMIENTO DE REFRIGERACION",
                     "fuente_estado":None,"fuente_activo":None,
                     "fuente_plan":None,"fuente_operacion":None,
                     "historico_finalizada":"FINALIZADA"},
                    {"programacion_item_id":2,"numero_ot":"OT-20000-26",
                     "activo_codigo":"BA-SI-IG-AA32",
                     "plan_clave_software":"48-RUTINA",
                     "fuente_estado":"PENDIENTE","fuente_activo":"BA-SI-IG-AA32",
                     "fuente_plan":"48-RUTINA","fuente_operacion":False,
                     "historico_finalizada":None},
                    {"programacion_item_id":3,"numero_ot":"OT-13187-26",
                     "activo_codigo":"BA-WF-IG-AL03-MO02",
                     "plan_clave_software":"44-RESISTENCIA",
                     "fuente_estado":"PENDIENTE" if operations else None,
                     "fuente_activo":"BA-WF-IG-AL03-MO02" if operations else None,
                     "fuente_plan":"44-OPERACIÓN - RUTINA ELÉCTRICA SEMESTRAL MOTOR CONSUMO" if operations else None,
                     "fuente_operacion":operations,
                     "historico_finalizada":None},
                ])
            raise AssertionError("Unexpected SQL: "+query[:180])
        def __enter__(self):
            return self
        def __exit__(self, *_):
            return False
    class Engine:
        def connect(self):
            return Conn()
    return Engine()


def test_api_closure_calendar_only_uses_source_and_validated_historical_snapshot(monkeypatch):
    monkeypatch.setattr(service,"get_engine",lambda:_engine())
    content,meta=service._api_closure_calendar(50)
    workbook=load_workbook(BytesIO(content),read_only=True,data_only=True)
    rows=list(workbook.active.values)
    assert rows[0] == ("Orden","Activo","PlanTrabajo","Estado")
    assert rows[1][0] == "OT-12907-26"
    assert rows[1][-1] == "FINALIZADA"
    assert rows[2][0] == "OT-20000-26"
    assert rows[2][-1] == "PENDIENTE"
    assert len(rows)==3
    assert meta["sync_id"]==20
    assert meta["historic_finalized"]==1
    assert meta["from_month"]==1
    assert meta["not_in_source"]==1
    assert meta["programmed"]==3


def test_api_closure_rejects_operations_in_saved_week(monkeypatch):
    monkeypatch.setattr(service,"get_engine",lambda:_engine(operations=True))
    with pytest.raises(service.V2ClosureError,match="OT-13187-26"):
        service._api_closure_calendar(50)


def test_api_closure_rejects_previously_closed_week(monkeypatch):
    monkeypatch.setattr(service,"get_engine",lambda:_engine(closed=True))
    with pytest.raises(service.V2ClosureError,match="ya está cerrada"):
        service._api_closure_calendar(50)


def test_api_close_requires_matching_sync_id(monkeypatch):
    monkeypatch.setattr(service,"_api_closure_calendar",
                        lambda _: (b"fake",{"sync_id":21}))
    with pytest.raises(service.V2ClosureError,match="fuente cambió"):
        service.close_week_from_api(programming_id=50,expected_sync_id=20)


def test_api_close_requires_explicit_approval_of_missing(monkeypatch):
    monkeypatch.setattr(service,"_api_closure_calendar",
                        lambda _: (b"fake",{"sync_id":20}))
    monkeypatch.setattr(service,"preview_week_closure",
                        lambda **_: {"summary":{"conflicts":0,"blank_states":0,"missing":3},
                                    "rows":[]})
    with pytest.raises(service.V2ClosureError,match="Autoriza expresamente"):
        service.close_week_from_api(programming_id=50,expected_sync_id=20)
