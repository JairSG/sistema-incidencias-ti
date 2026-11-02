"""Indicadores calculados desde documentos MongoDB; sin datos inventados."""
import pandas as pd
TARGETS = {'Alta':4, 'Media':24, 'Baja':72}
def build_frame(docs, reference):
    reference=pd.Timestamp(reference)
    reference=reference.tz_localize('UTC') if reference.tzinfo is None else reference.tz_convert('UTC')
    rows=[]
    for d in docs:
        created=pd.to_datetime(d.get('fecha_registro'),utc=True,errors='coerce')
        if pd.isna(created) or created>reference: continue
        # No se reconstruyen estados históricos: reference es únicamente el corte de edad.
        events=[pd.to_datetime(e.get('fecha'),utc=True,errors='coerce') for e in d.get('seguimiento',[]) if e.get('estado')=='Resuelta']
        valid=[t for t in events if not pd.isna(t) and created<=t<=reference]
        closed=max(valid) if valid and d.get('estado')=='Resuelta' else pd.NaT
        hours=(closed-created).total_seconds()/3600 if not pd.isna(closed) else float('nan')
        age=(reference-created).total_seconds()/3600 if d.get('estado')!='Resuelta' else float('nan')
        target=TARGETS.get(d.get('prioridad'))
        rows.append({'Código':d.get('codigo'), 'Descripción':d.get('descripcion',''), 'Estado':d.get('estado'), 'Prioridad':d.get('prioridad'), 'Categoría':d.get('categoria','Sin categoría'), 'Área':d.get('solicitante',{}).get('area','Sin área'), 'Equipo':d.get('equipo',{}).get('codigo',''), 'Técnico':d.get('tecnico',{}).get('nombre','Sin asignar'), 'Registro':created, 'Resolución':closed, 'Horas resolución':hours, 'Horas abiertas':age, 'Objetivo horas':target, 'Vencida':bool(target and pd.notna(age) and age>target), 'Cumple objetivo': bool(hours<=target) if target and pd.notna(hours) else None, 'Seguimientos':len(d.get('seguimiento',[]))})
    return pd.DataFrame(rows)
