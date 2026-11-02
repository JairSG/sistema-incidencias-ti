# Sistema de Gestión de Incidencias de TI
Aplicación académica de Soporte Andino, empresa ficticia. Streamlit, MongoDB Atlas y Plotly. CRUD con solicitante, equipo y técnico embebidos, más historial de actuaciones. Panel ejecutivo, filtros y exportación CSV.

## Publicar en Streamlit Community Cloud
1. Sube los archivos de esta carpeta a la raíz de tu repositorio. Conserva `.streamlit/config.toml` y no subas archivos con secretos reales.
2. En https://share.streamlit.io inicia sesión con GitHub y crea una app desde el repositorio: rama `main`, archivo principal `app.py`.
3. En Advanced settings → Secrets pega (con valores reales):
```toml
MONGODB_URI = "TU_URI_COMPLETA_DE_ATLAS"
APP_PASSWORD = "TU_CLAVE_PARA_LA_DEMO"
```
4. En Atlas autoriza en Network Access las IP de salida de Streamlit Cloud, según la lista oficial vigente: https://docs.streamlit.io/deploy/streamlit-community-cloud/status . Añade cada una como dirección /32. No basta la IP de Colab. Las IP pueden cambiar.
5. Usa un usuario de base de datos con lectura/escritura sobre `gestion_incidencias_ti`. La colección es `incidencias`. Conserva el índice único de `codigo` creado por el notebook.
6. Pulsa Deploy. Configura la visibilidad pública si es necesario y comparte la URL que entregue Streamlit junto con la clave de demo. No compartas la URI de Atlas.

Los datos ya cargados por Colab permanecen en Atlas: no necesitas importarlos otra vez. Esta app no carga ni restablece semillas automáticamente. Tampoco necesita Colab ni Cloudflare para ejecutarse en Community Cloud.

La clave es compartida y concede acceso al CRUD: los compañeros que la reciban podrán modificar o eliminar los registros. Se trata de una demostración con datos sintéticos, sin roles de producción. Community Cloud puede suspender apps inactivas; conserva el enlace, pero el primer acceso puede requerir esperar su reactivación.

## Ejecutar localmente
`python -m pip install -r requirements.txt`

Copia `.streamlit/secrets.toml.example` a `.streamlit/secrets.toml`, completa los secretos y ejecuta `python -m streamlit run app.py`. También se admiten variables de entorno `MONGODB_URI` y `APP_PASSWORD`.

## Métricas y alcance
Estados actuales y cohortes por fecha de registro. Resolución media y P90 se calculan desde la última entrada Resuelta del historial para casos actualmente resueltos. Antigüedad: horas corridas desde el registro. Objetivos académicos: Alta 4 h, Media 24 h y Baja 72 h, no SLA contractual. Los cierres de las semillas originales son a 6 horas: no representan desempeño real. Máximo de análisis: 10 000 documentos; para mayor volumen se requiere agregación en MongoDB.

Fuentes oficiales: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy y https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management
