from __future__ import annotations

from backend.parsers.common import ParsedWorkbook, as_float, canonical_plan_name, cell_by_header, find_header_row, header_mapping, normalize_text, normalize_turn, workbook_from_bytes

def _pick_sheet(wb, required, preferred=None):
    preferred = preferred or []
    sheets = sorted(wb.worksheets, key=lambda ws: (normalize_text(ws.title) not in {normalize_text(x) for x in preferred}, ws.title))
    for ws in sheets:
        if normalize_text(ws.title) == "LEEME": continue
        try:
            hr,_=find_header_row(ws,required)
            return ws,hr
        except ValueError: pass
    raise ValueError(f"No se encontró una hoja con: {', '.join(required)}")

def parse_master_assets(content: bytes) -> ParsedWorkbook:
    wb=workbook_from_bytes(content); ws,hr=_pick_sheet(wb,["Código","Descripción"],["ACTIVOS"]); m=header_mapping(ws,hr)
    result=ParsedWorkbook(metadata={"sheet":ws.title})
    for n,row in enumerate(ws.iter_rows(min_row=hr+1,values_only=True),start=hr+1):
        code=str(cell_by_header(row,m,"Código","Codigo") or "").strip()
        if not code: continue
        result.rows.append({"excel_row":n,"code":code,"description":cell_by_header(row,m,"Descripción","Descripcion"),"parent_code":str(cell_by_header(row,m,"ActivoPadre") or "").strip(),"area":cell_by_header(row,m,"Área","Area"),"line":cell_by_header(row,m,"Línea / Subárea","Linea / Subarea","Linea"),"criticality":normalize_text(cell_by_header(row,m,"Criticidad")),"specialty":normalize_text(cell_by_header(row,m,"Especialidad")),"state":normalize_text(cell_by_header(row,m,"Estado"))})
    return result

def parse_master_plans(content: bytes) -> ParsedWorkbook:
    wb=workbook_from_bytes(content); ws,hr=_pick_sheet(wb,["Especialidad","Plan de Trabajo"],["PLANES_TRABAJO"]); m=header_mapping(ws,hr)
    result=ParsedWorkbook(metadata={"sheet":ws.title})
    for n,row in enumerate(ws.iter_rows(min_row=hr+1,values_only=True),start=hr+1):
        specialty=normalize_text(cell_by_header(row,m,"Especialidad")); plan=str(cell_by_header(row,m,"Plan de Trabajo","PlanTrabajo") or "").strip()
        if not specialty or not plan: continue
        result.rows.append({"excel_row":n,"specialty":specialty,"group":str(cell_by_header(row,m,"Grupo / Ruta","DescripcionGrupo","Grupo") or "SIN GRUPO").strip(),"plan_raw":plan,"plan_canonical":canonical_plan_name(plan),"persons":max(1.0,as_float(cell_by_header(row,m,"Número de Personas","NumeroPersonas"),1.0))})
    return result

def parse_master_classification(content: bytes) -> ParsedWorkbook:
    wb=workbook_from_bytes(content); ws,hr=_pick_sheet(wb,["Especialidad","Plan de Trabajo"],["CLASIFICACION_PLANES"]); m=header_mapping(ws,hr)
    result=ParsedWorkbook(metadata={"sheet":ws.title})
    for n,row in enumerate(ws.iter_rows(min_row=hr+1,values_only=True),start=hr+1):
        specialty=normalize_text(cell_by_header(row,m,"Especialidad")); plan=str(cell_by_header(row,m,"Plan de Trabajo","Plan_Trabajo") or "").strip()
        if not specialty or not plan: continue
        result.rows.append({"excel_row":n,"specialty":specialty,"plan_raw":plan,"plan_canonical":canonical_plan_name(plan),"persons":max(1.0,as_float(cell_by_header(row,m,"Personas_Usar","Personas_Programar","Personas_Software"),1.0)),"condition":normalize_text(cell_by_header(row,m,"Condición","Condicion_Seleccionada")) or "SIN CLASIFICAR","observation":cell_by_header(row,m,"Observación","Observacion_Clasificacion")})
    return result

def parse_master_personnel_turns(content: bytes):
    wb=workbook_from_bytes(content)
    wsp,hrp=_pick_sheet(wb,["Nombre","Especialidad"],["PERSONAL"]); pm=header_mapping(wsp,hrp); persons=ParsedWorkbook(metadata={"sheet":wsp.title})
    for n,row in enumerate(wsp.iter_rows(min_row=hrp+1,values_only=True),start=hrp+1):
        name=str(cell_by_header(row,pm,"Nombre") or "").strip(); specialty=normalize_text(cell_by_header(row,pm,"Especialidad"))
        if name and specialty: persons.rows.append({"excel_row":n,"name":name,"normalized":normalize_text(name),"specialty":specialty})
    wst,hrt=_pick_sheet(wb,["Código","HH disponibles"],["MAESTRO_TURNOS"]); tm=header_mapping(wst,hrt); turns=ParsedWorkbook(metadata={"sheet":wst.title})
    for n,row in enumerate(wst.iter_rows(min_row=hrt+1,values_only=True),start=hrt+1):
        raw=normalize_text(cell_by_header(row,tm,"Código","Codigo"))
        if not raw: continue
        turns.rows.append({"excel_row":n,"code":normalize_turn(raw),"raw_code":raw,"hours":max(0.0,as_float(cell_by_header(row,tm,"HH disponibles")))})
    return {"personnel":persons,"turns":turns}
