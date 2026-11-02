import os, re, uuid, hmac
from datetime import datetime, timezone
import streamlit as st
import pandas as pd
import plotly.express as px
from analytics import build_frame, TARGETS
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from bson import json_util

st.set_page_config(page_title="Incidencias TI", page_icon="🛠️", layout="wide")
st.markdown("""<style>
.stApp {background: #f4f7fb; color:#172b4d;}
[data-testid="stSidebar"] {background:#e8eef8;}
[data-testid="stMetric"] {background:white; border:1px solid #dce5f2; border-radius:14px; padding:18px; box-shadow:0 3px 12px #172b4d08;}
[data-testid="stMetricLabel"] {color:#526581;}
[data-testid="stMetricValue"] {color:#123b70;}
.block-container {padding-top:2rem; max-width:1500px;}
.hero {background:linear-gradient(115deg,#102b50,#164c85); padding:28px 32px; border-radius:18px; color:white; margin-bottom:24px;}
.hero h1 {color:white; font-size:2rem; padding:0; margin:6px 0;}
.hero p {color:#d2e3f8; margin:0;}
.eyebrow {font-size:12px; letter-spacing:2px; color:#80dbe0; font-weight:700;}
</style><div class="hero"><span class="eyebrow">SOPORTE ANDINO / SERVICE DESK</span><h1>Centro de operaciones TI</h1><p>Incidencias, seguimiento y analítica operativa en un solo lugar.</p></div>""", unsafe_allow_html=True)
st.caption("Caso académico · Empresa ficticia · Datos sintéticos · Zona horaria de los análisis: UTC")
def get_setting(name):
    """Secrets de Streamlit Cloud o variables de entorno de Colab."""
    value = os.environ.get(name)
    if value:
        return value
    try:
        return str(st.secrets.get(name, ""))
    except FileNotFoundError:
        return ""

if not get_setting("MONGODB_URI") or not get_setting("APP_PASSWORD"):
    st.error("Falta configurar MONGODB_URI y APP_PASSWORD en los secretos del alojamiento.")
    st.stop()
password = st.sidebar.text_input("Clave de acceso a la demo", type="password")
if not password or not hmac.compare_digest(password.encode("utf-8"), get_setting("APP_PASSWORD").encode("utf-8")):
    st.info("Ingresa la clave de la demo en la barra lateral.")
    st.stop()

@st.cache_resource
def connect_to_mongodb():
    client = MongoClient(get_setting("MONGODB_URI"), serverSelectionTimeoutMS=10000, tz_aware=True)
    client.admin.command("ping")
    return client

try:
    col = connect_to_mongodb()["gestion_incidencias_ti"]["incidencias"]
except (PyMongoError, KeyError):
    st.error("No se pudo conectar. Revisa MONGODB_URI, el usuario y Network Access en Atlas.")
    st.stop()

states = ["Pendiente", "En atención", "Resuelta"]
priorities = ["Baja", "Media", "Alta"]
categories = ["Conectividad", "Hardware", "Software", "Impresión", "Accesos"]
st.sidebar.markdown("### Mesa de servicios")
mode = st.sidebar.radio("Navegación", ["Panel ejecutivo", "Consultar", "Registrar", "Actualizar y seguimiento", "Eliminar"])
st.sidebar.caption("MongoDB Atlas · Documentos embebidos")
if st.session_state.pop("saved", False):
    st.success("Operación completada en MongoDB Atlas.")
def done():
    st.session_state["saved"] = True
    st.rerun()
def now():
    return datetime.now(timezone.utc)

try:
    if mode == "Panel ejecutivo":
        st.subheader("Panorama del servicio")
        st.caption("Indicadores calculados sobre registros filtrados; estados actuales, no reconstrucción histórica.")
        docs=list(col.find({}).limit(10001))
        if len(docs)>10000:
            st.warning("El panel admite hasta 10 000 registros en esta versión académica. Se requiere agregación en servidor para mayor volumen.")
            st.stop()
        if not docs:
            st.info("Registra incidencias o ejecuta la carga inicial del notebook.")
            st.stop()
        # El corte nunca antecede al momento actual para no presentar estados actuales como históricos.
        reference=datetime.now(timezone.utc)
        df=build_frame(docs, reference)
        if df.empty:
            st.info("No hay registros válidos para analizar.")
            st.stop()
        st.caption("Actualizado: "+reference.strftime("%d/%m/%Y %H:%M UTC")+" · Pulsa Actualizar para releer Atlas.")
        if st.button("Actualizar panel"): st.rerun()
        with st.expander("Filtros del panel",expanded=True):
            c1,c2,c3=st.columns(3)
            areas=c1.multiselect("Áreas",sorted(df["Área"].unique()))
            cats=c2.multiselect("Categorías",sorted(df["Categoría"].unique()))
            priorities=c3.multiselect("Prioridades",priorities)
            date_range=st.date_input("Periodo de registro (UTC)",value=(df["Registro"].min().date(),df["Registro"].max().date()))
        if areas: df=df[df["Área"].isin(areas)]
        if cats: df=df[df["Categoría"].isin(cats)]
        if priorities: df=df[df["Prioridad"].isin(priorities)]
        if len(date_range)!=2:
            st.info("Selecciona inicio y fin del periodo.")
            st.stop()
        df=df[(df["Registro"].dt.date>=date_range[0]) & (df["Registro"].dt.date<=date_range[1])]
        if df.empty:
            st.info("No hay resultados para estos filtros.")
            st.stop()
        opened=df[df["Estado"]!="Resuelta"]
        solved=df[df["Estado"]=="Resuelta"]
        valid=solved.dropna(subset=["Horas resolución"])
        eligible=valid[valid["Cumple objetivo"].notna()]
        k=st.columns(4)
        k[0].metric("Incidencias",len(df))
        k[1].metric("Abiertas",len(opened))
        k[2].metric("Resueltas",len(solved))
        k[3].metric("Tasa de resolución",f"{len(solved)/len(df)*100:.1f}%")
        k=st.columns(4)
        k[0].metric("Resolución media",f"{valid['Horas resolución'].mean():.1f} h" if len(valid) else "Sin datos")
        k[1].metric("Resolución P90",f"{valid['Horas resolución'].quantile(.9):.1f} h" if len(valid) else "Sin datos")
        k[2].metric("Abiertas fuera de objetivo",int(opened["Vencida"].sum()))
        k[3].metric("Cumplimiento en resueltas",f"{eligible['Cumple objetivo'].astype(bool).mean()*100:.1f}%" if len(eligible) else "Sin datos")
        st.caption("Objetivos académicos en horas corridas: Alta 4 h · Media 24 h · Baja 72 h. No representan un SLA contractual. P90: tiempo por debajo del cual se resuelve el 90% de los casos medidos.")
        tabs=st.tabs(["Demanda y estados", "Tiempos y capacidad", "Casos que requieren atención", "Datos y metodología"])
        colors={"Pendiente":"#f2ad45","En atención":"#3987dc","Resuelta":"#20a78e"}
        def chart(fig):
            fig.update_layout(template="plotly_white",paper_bgcolor="white",font_color="#172b4d",margin=dict(l=20,r=20,t=55,b=20),legend_title_text="")
            st.plotly_chart(fig,width="stretch")
        with tabs[0]:
            c1,c2=st.columns(2)
            with c1:
                counts=df.groupby("Estado").size().reset_index(name="Cantidad")
                chart(px.pie(counts,names="Estado",values="Cantidad",hole=.65,color="Estado",color_discrete_map=colors,title="Distribución actual por estado"))
            with c2:
                counts=df.groupby(["Categoría","Estado"]).size().reset_index(name="Cantidad")
                chart(px.bar(counts,x="Cantidad",y="Categoría",color="Estado",orientation="h",color_discrete_map=colors,title="Demanda por categoría"))
            created=df.set_index("Registro").resample("D").size().rename("Registradas")
            closed=valid.set_index("Resolución").resample("D").size().rename("Resueltas") if len(valid) else pd.Series(dtype=float,name="Resueltas")
            trend=pd.concat([created,closed],axis=1).fillna(0).rename_axis("Día").reset_index()
            chart(px.line(trend,x="Día",y=["Registradas","Resueltas"],markers=True,title="Entradas y resoluciones por día (cohorte seleccionada)",color_discrete_sequence=["#3987dc","#20a78e"]))
            st.caption("Las resoluciones corresponden únicamente a incidencias actualmente resueltas del periodo de registro elegido. La gráfica no representa un backlog histórico.")
        with tabs[1]:
            c1,c2=st.columns(2)
            with c1:
                if len(valid): chart(px.box(valid,x="Prioridad",y="Horas resolución",color="Prioridad",points="all",category_orders={"Prioridad":["Alta","Media","Baja"]},title="Distribución de tiempos de resolución"))
                else: st.info("Sin resoluciones con fechas válidas.")
            with c2:
                if len(opened):
                    load=opened.groupby(["Técnico","Estado"]).size().reset_index(name="Abiertas")
                    chart(px.bar(load,x="Abiertas",y="Técnico",color="Estado",orientation="h",color_discrete_map=colors,title="Carga abierta actual por técnico"))
                else: st.info("Sin incidencias abiertas.")
            if len(opened):
                age=opened.copy()
                age["Antigüedad"]=pd.cut(age["Horas abiertas"],bins=[-1,24,72,168,float("inf")],labels=["Hasta 24 h","1–3 días","3–7 días","Más de 7 días"])
                ages=age.groupby("Antigüedad",observed=False).size().reset_index(name="Cantidad")
                chart(px.bar(ages,x="Antigüedad",y="Cantidad",title="Antigüedad de incidencias abiertas",color_discrete_sequence=["#3987dc"]))
            st.caption("Carga asignada no equivale a productividad: no se dispone de horas trabajadas ni complejidad de los casos.")
        with tabs[2]:
            overdue=opened[opened["Vencida"]].sort_values("Horas abiertas",ascending=False)
            if len(overdue):
                st.warning(f"{len(overdue)} incidencias abiertas exceden el objetivo académico.")
                st.dataframe(overdue[["Código","Prioridad","Área","Técnico","Horas abiertas","Objetivo horas"]].round(1),hide_index=True,width="stretch")
            else: st.success("No hay incidencias abiertas fuera del objetivo.")
            st.markdown("**Equipos con más incidencias registradas**")
            repeat=df.groupby("Equipo").size().sort_values(ascending=False).head(10).reset_index(name="Incidencias")
            st.dataframe(repeat,hide_index=True,width="stretch")
        with tabs[3]:
            st.write("Tasa de resolución = resueltas / incidencias filtradas. Tiempo de resolución = última entrada Resuelta del historial menos fecha de registro, solo para casos actualmente resueltos. Antigüedad = momento actual menos registro para casos abiertos. Se usan horas corridas y UTC.")
            st.write("Se excluyen registros sin fecha de creación válida o futura. Resueltas sin cierre válido no se incluyen en promedios, P90 ni cumplimiento. El porcentaje de cumplimiento usa únicamente resueltas con cierre y objetivo válidos.")
            st.info("Los datos iniciales son sintéticos y sus cierres se generaron a las 6 horas. Esa regularidad es una propiedad de la simulación; no es evidencia de desempeño de una empresa real. La antigüedad sigue creciendo hasta la fecha actual.")
            st.dataframe(df,hide_index=True,width="stretch")
            st.download_button("Descargar datos filtrados CSV",data=df.to_csv(index=False).encode("utf-8-sig"),file_name="analitica_incidencias.csv",mime="text/csv")
    elif mode == "Consultar":
        a,b,c=st.columns(3)
        a.metric("Total",col.count_documents({}))
        b.metric("Pendientes",col.count_documents({"estado":"Pendiente"}))
        c.metric("En atención",col.count_documents({"estado":"En atención"}))
        area=st.text_input("Área del solicitante (búsqueda parcial)")
        equipo=st.text_input("Código del equipo (búsqueda parcial)")
        state=st.selectbox("Estado",["Todos"]+states)
        query={}
        if area.strip(): query["solicitante.area"]={"$regex":re.escape(area.strip()),"$options":"i"}
        if equipo.strip(): query["equipo.codigo"]={"$regex":re.escape(equipo.strip()),"$options":"i"}
        if state!="Todos": query["estado"]=state
        total=col.count_documents(query)
        st.write(f"Resultados: {total}")
        page=st.number_input("Página (20 registros)", min_value=1, max_value=max(1,(total+19)//20),value=1)
        docs=list(col.find(query).sort("fecha_registro",-1).skip((page-1)*20).limit(20))
        if docs:
            rows=[{"Código":d["codigo"],"Descripción":d["descripcion"],"Estado":d["estado"],"Prioridad":d["prioridad"],"Área":d["solicitante"]["area"],"Equipo":d["equipo"]["codigo"]} for d in docs]
            st.dataframe(pd.DataFrame(rows),width="stretch",hide_index=True)
            for d in docs:
                with st.expander(d["codigo"]+" — "+d["descripcion"]):
                    st.json(__import__('json').loads(json_util.dumps(d)))
                    st.write("Historial de atención")
                    st.dataframe(pd.DataFrame(d["seguimiento"]),hide_index=True)
        else: st.info("No hay incidencias para esos filtros.")
    elif mode == "Registrar":
        with st.form("new",clear_on_submit=True):
            name=st.text_input("Nombre del solicitante *")
            area=st.text_input("Área *")
            mail=st.text_input("Correo *")
            equipment=st.text_input("Código del equipo *")
            brand=st.selectbox("Marca",["Lenovo","HP","Dell","Otra"])
            cat=st.selectbox("Categoría",categories)
            desc=st.text_area("Descripción *",max_chars=2000)
            priority=st.selectbox("Prioridad",priorities,index=1)
            submit=st.form_submit_button("Registrar incidencia")
        if submit:
            if not all(x.strip() for x in [name,area,mail,equipment,desc]): st.warning("Completa todos los campos obligatorios.")
            elif not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+",mail.strip()): st.warning("Ingresa un correo válido.")
            else:
                dt=now()
                col.insert_one({"codigo":"INC-"+uuid.uuid4().hex[:12].upper(),"categoria":cat,"descripcion":desc.strip(),"prioridad":priority,"estado":"Pendiente","solicitante":{"nombre":name.strip(),"area":area.strip(),"correo":mail.strip()},"equipo":{"codigo":equipment.strip().upper(),"tipo":"Computadora","marca":brand},"tecnico":{"codigo":"SIN-ASIGNAR","nombre":"Sin asignar"},"fecha_registro":dt,"fecha_actualizacion":dt,"seguimiento":[{"fecha":dt,"estado":"Pendiente","comentario":"Incidencia registrada","autor":"Mesa de ayuda"}],"origen":"demo_academica"})
                done()
    else:
        code=st.text_input("Código exacto de la incidencia",placeholder="INC-0001").strip().upper()
        doc=col.find_one({"codigo":code}) if code else None
        if code and not doc: st.warning("Incidencia no encontrada.")
        if doc:
            st.write(doc["descripcion"])
            st.caption(f"Estado actual: {doc['estado']} | Equipo: {doc['equipo']['codigo']}")
            if mode=="Actualizar y seguimiento":
                with st.form("edit_"+str(doc["_id"])):
                    state=st.selectbox("Nuevo estado",states,index=states.index(doc["estado"]))
                    priority=st.selectbox("Prioridad",priorities,index=priorities.index(doc["prioridad"]))
                    description=st.text_area("Descripción",value=doc["descripcion"],max_chars=2000)
                    technician=st.selectbox("Técnico",["Sin asignar","Luis Pérez","Sofía Medina","Marco Salas"],index=["Sin asignar","Luis Pérez","Sofía Medina","Marco Salas"].index(doc["tecnico"]["nombre"]))
                    comment=st.text_area("Comentario de seguimiento obligatorio",max_chars=2000)
                    submit=st.form_submit_button("Guardar cambios y seguimiento")
                if submit:
                    if not comment.strip() or not description.strip(): st.warning("Completa descripción y comentario.")
                    elif state!="Pendiente" and technician=="Sin asignar": st.warning("Asigna un técnico antes de atender o resolver.")
                    else:
                        dt=now(); codes={"Sin asignar":"SIN-ASIGNAR","Luis Pérez":"TEC-001","Sofía Medina":"TEC-002","Marco Salas":"TEC-003"}
                        result=col.update_one({"_id":doc["_id"],"fecha_actualizacion":doc["fecha_actualizacion"]},{"$set":{"estado":state,"prioridad":priority,"descripcion":description.strip(),"tecnico.nombre":technician,"tecnico.codigo":codes[technician],"fecha_actualizacion":dt},"$push":{"seguimiento":{"fecha":dt,"estado":state,"comentario":comment.strip(),"autor":technician if technician!="Sin asignar" else "Mesa de ayuda"}}})
                        if result.matched_count: done()
                        else: st.warning("El registro cambió o fue eliminado. Recarga y vuelve a intentarlo.")
            else:
                st.warning("Esta acción eliminará la incidencia y todo su historial.")
                confirm=st.checkbox("Confirmo que deseo eliminar este registro",key="confirm_"+code)
                if st.button("Eliminar definitivamente",disabled=not confirm):
                    result=col.delete_one({"_id":doc["_id"],"fecha_actualizacion":doc["fecha_actualizacion"]})
                    if result.deleted_count: done()
                    else: st.warning("El registro cambió. Recarga antes de eliminar.")
except PyMongoError:
    st.error("La operación no se completó. Verifica conexión y permisos; consulta Atlas antes de reintentar.")
