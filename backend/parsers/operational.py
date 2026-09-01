from __future__ import annotations

from collections import Counter
from datetime import date
from backend.parsers.common import ParsedWorkbook, as_date, as_datetime, as_float, canonical_plan_name, cell_by_header, find_header_row, header_mapping, normalize_order, normalize_text, normalize_turn, stable_sha256, workbook_from_bytes

MONTHS={"ENERO":1,"FEBRERO":2,"MARZO":3,"ABRIL":4,"MAYO":5,"JUNIO":6,"JULIO":7,"AGOSTO":8,"SEPTIEMBRE":9,"OCTUBRE":10,"NOVIEMBRE":11,"DICIEMBRE":12}

def _sheet_with_headers(wb,required):
    for ws in wb.worksheets:
        if normalize_text(ws.title)=="LEEME": continue
        try:
            hr,_=find_header_row(ws,required); return ws,hr
        except ValueError: pass
    raise ValueError("No se encontró una hoja válida")

def parse_monthly_planning(content: bytes) -> ParsedWorkbook:
    wb=workbook_from_bytes(content); ws,hr=_sheet_with_headers(wb,["Activo","Especialidad","Orden","PlanTrabajo","TiempoPlaneado","Estado"]); m=header_mapping(ws,hr)
    result=ParsedWorkbook(metadata={"sheet":ws.title}); occurrence=Counter()
    for n,row in enumerate(ws.iter_rows(min_row=hr+1,values_only=True),start=hr+1):
        asset=str(cell_by_header(row,m,"Activo") or "").strip(); plan_raw=str(cell_by_header(row,m,"PlanTrabajo","Plan de Trabajo") or "").strip(); specialty=normalize_text(cell_by_header(row,m,"Especialidad")); order=normalize_order(cell_by_header(row,m,"Orden"))
        if not asset and not plan_raw and not order: continue
        start=as_date(cell_by_header(row,m,"FechaPlaneadaInicio")); end=as_date(cell_by_header(row,m,"FechaPlaneadaFin")); canonical=canonical_plan_name(plan_raw)
        base=stable_sha256([start,end,asset,specialty,canonical,cell_by_header(row,m,"Título","Titulo"),cell_by_header(row,m,"CronogramaPlaneacion"),cell_by_header(row,m,"OrdenTipo")]); occurrence[base]+=1
        result.rows.append({"excel_row":n,"source_key":stable_sha256([base,occurrence[base]]),"title":cell_by_header(row,m,"Título","Titulo"),"comment":cell_by_header(row,m,"Comentario"),"alert":cell_by_header(row,m,"Alerta"),"planned_start":start,"planned_end":end,"order_finished_at":as_datetime(cell_by_header(row,m,"FechaFinOrden")),"asset_code":asset,"asset_description":cell_by_header(row,m,"DescripciónActivo","DescripcionActivo"),"specialty":specialty,"order_type":cell_by_header(row,m,"OrdenTipo"),"order_number":"" if order=="SIN ASIGNAR" else order,"responsible":cell_by_header(row,m,"Responsable"),"plan_raw":plan_raw,"plan_canonical":canonical,"planning_schedule":cell_by_header(row,m,"CronogramaPlaneacion"),"planned_minutes":as_float(cell_by_header(row,m,"TiempoPlaneado")),"state":normalize_text(cell_by_header(row,m,"Estado")) or "PENDIENTE"})
    return result

def _scan_roster_metadata(ws,header_row):
    year=month=None
    for row in ws.iter_rows(min_row=1,max_row=max(1,header_row-1),values_only=True):
        vals=list(row)
        for i,v in enumerate(vals):
            key=normalize_text(v); nxt=vals[i+1] if i+1<len(vals) else None
            if key in {"ANO","AÑO"}:
                try: year=int(nxt)
                except: pass
            elif key=="MES":
                txt=normalize_text(nxt)
                if txt in MONTHS: month=MONTHS[txt]
                else:
                    try: month=int(nxt)
                    except: pass
    return year,month

def parse_technician_roster(content: bytes,*,year=None,month=None) -> ParsedWorkbook:
    wb=workbook_from_bytes(content); selected=None; hr=None
    for ws in wb.worksheets:
        for idx,row in enumerate(ws.iter_rows(min_row=1,max_row=50,values_only=True),start=1):
            first=normalize_text(row[0] if row else None); days=sum(1 for v in row if isinstance(v,(int,float)) and 1<=int(v)<=31)
            if first in {"TECNICO","TÉCNICO","NOMBRE"} and days>=5: selected=ws; hr=idx; break
        if selected: break
    if not selected: raise ValueError("No se encontró una matriz de técnicos con días 1..31")
    iy,im=_scan_roster_metadata(selected,hr); year=year or iy; month=month or im
    if not year or not month: raise ValueError("No fue posible determinar año y mes del roster")
    header=next(selected.iter_rows(min_row=hr,max_row=hr,values_only=True)); daycols={}
    for idx,v in enumerate(header):
        try:
            day=int(v)
            if 1<=day<=31: daycols[day]=idx
        except: pass
    result=ParsedWorkbook(metadata={"sheet":selected.title,"year":year,"month":month})
    for n,row in enumerate(selected.iter_rows(min_row=hr+1,values_only=True),start=hr+1):
        name=str(row[0] or "").strip()
        if not name or "EJEMPLO" in normalize_text(name): continue
        for day,col in daycols.items():
            if col>=len(row): continue
            raw=row[col]; code=normalize_turn(raw)
            if not code: continue
            try: work_date=date(year,month,day)
            except ValueError: continue
            result.rows.append({"excel_row":n,"technician_name":name,"technician_normalized":normalize_text(name),"date":work_date,"turn_code":code,"turn_raw":normalize_text(raw)})
    return result

def parse_order_states(content: bytes) -> ParsedWorkbook:
    wb=workbook_from_bytes(content); ws,hr=_sheet_with_headers(wb,["Orden","Estado"]); m=header_mapping(ws,hr); result=ParsedWorkbook(metadata={"sheet":ws.title})
    for n,row in enumerate(ws.iter_rows(min_row=hr+1,values_only=True),start=hr+1):
        order=normalize_order(cell_by_header(row,m,"Orden")); state=normalize_text(cell_by_header(row,m,"Estado"))
        if not order or order=="SIN ASIGNAR": continue
        if state not in {"PENDIENTE","FINALIZADA"}:
            result.warnings.append(f"Fila {n}: estado '{state}' ignorado"); continue
        result.rows.append({"excel_row":n,"order_number":order,"state":state,"finished_at":as_datetime(cell_by_header(row,m,"FechaFinOrden"))})
    return result
