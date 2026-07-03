# README_LOCAL.md — Local Indexed Search Engine

## 1. Objetivo del proyecto

`Local Indexed Search Engine` es un buscador local de archivos con indexación híbrida.

El sistema permite:

- Indexar archivos locales.
- Extraer texto y metadatos.
- Guardar registros persistentes en SQLite.
- Crear embeddings locales con SentenceTransformers.
- Persistir vectores en ChromaDB.
- Ejecutar búsqueda full-text.
- Ejecutar búsqueda semántica.
- Ejecutar búsqueda híbrida.
- Filtrar archivos por extensión, nombre, ruta o contenido.
- Consultar estado, métricas y logs.
- Usar una interfaz local con Gradio.

El sistema no usa Ollama ni LLM remoto.

---

## 2. Arquitectura local

Arquitectura validada:

```text
Local Indexed Search Engine
│
├── Backend FastAPI
│   ├── API REST
│   ├── endpoints de indexación
│   ├── endpoints de búsqueda
│   ├── endpoints de monitoreo
│   ├── endpoints de logs
│   └── watcher de filesystem
│
├── SQLite
│   ├── registro de archivos
│   ├── chunks indexados
│   └── SQLite FTS5 para búsqueda full-text
│
├── ChromaDB
│   ├── almacenamiento vectorial persistente
│   └── búsqueda semántica por embeddings
│
├── SentenceTransformers
│   └── modelo local intfloat/multilingual-e5-small
│
└── Gradio
    └── interfaz local de operación
```

---

## 3. Rutas principales

Ruta raíz del proyecto:

```cmd
E:\DesarrolloAI\local-ai-semantic-search
```

Estructura principal:

```text
local-ai-semantic-search
│
├── backend
│   ├── app
│   │   ├── main.py
│   │   ├── search_engine.py
│   │   ├── file_registry.py
│   │   ├── chroma_store.py
│   │   ├── indexer.py
│   │   ├── embedding_client.py
│   │   ├── chunker.py
│   │   ├── document_extractor.py
│   │   ├── image_metadata_extractor.py
│   │   ├── text_extractor.py
│   │   ├── watcher.py
│   │   ├── logger_config.py
│   │   └── metrics_store.py
│   │
│   └── data
│       ├── registry.sqlite
│       └── chroma
│
├── gradio_ui
│   └── app.py
│
├── logs
│   └── backend.log
│
├── test_docs
│
├── run_gradio.py
├── requirements.txt
└── requirements_gradio.txt
```

---

## 4. Puertos usados

Puertos definitivos del entorno local:

```text
FastAPI backend: 127.0.0.1:8000
Gradio UI:       127.0.0.1:7861
```

---

## 5. Activar entorno virtual

Abrir Windows CMD.

Ejecutar:

```cmd
cd /d E:\DesarrolloAI\local-ai-semantic-search
semantica310\Scripts\activate.bat
```

Resultado esperado en el prompt:

```text
(semantica310) E:\DesarrolloAI\local-ai-semantic-search>
```

---

## 6. Levantar backend FastAPI

Con el entorno `semantica310` activo:

```cmd
cd /d E:\DesarrolloAI\local-ai-semantic-search
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

Resultado esperado:

```text
Uvicorn running on http://127.0.0.1:8000
Application startup complete.
```

La ventana donde corre `uvicorn` debe permanecer abierta.

---

## 7. Validar backend

En una segunda ventana CMD:

```cmd
cd /d E:\DesarrolloAI\local-ai-semantic-search
semantica310\Scripts\activate.bat
curl http://127.0.0.1:8000/health
```

Resultado esperado:

```json
{"status":"ok","service":"local-indexed-search-engine","version":"0.13.1","llm":"disabled","ollama":"removed"}
```

Validar estado consolidado:

```cmd
curl http://127.0.0.1:8000/monitoring/status
```

Resultado esperado:

```text
api: ok
registry: ok
chroma: ok
runtime: ok
watcher: stopped
```

`watcher: stopped` es correcto si el watcher no fue iniciado manualmente.

---

## 8. Levantar Gradio

Con el backend activo, abrir otra ventana CMD:

```cmd
cd /d E:\DesarrolloAI\local-ai-semantic-search
semantica310\Scripts\activate.bat
python run_gradio.py
```

Resultado esperado:

```text
Running on local URL:  http://127.0.0.1:7861
```

Abrir en navegador:

```text
http://127.0.0.1:7861
```

---

## 9. Validar Gradio

En la pestaña `Estado`, validar:

```text
Health
SQLite
ChromaDB
API Base
Status
Metrics
Diagnostics
```

Resultado esperado:

```text
Health responde status ok.
SQLite muestra files_count y chunks_count.
ChromaDB responde status ok.
Metrics responde métricas consolidadas.
Diagnostics muestra rutas locales y estado del sistema.
```

---

## 10. Indexar archivo individual

Endpoint:

```text
POST /index-file
```

Ejemplo CMD:

```cmd
curl -X POST http://127.0.0.1:8000/index-file ^
  -H "Content-Type: application/json" ^
  -d "{\"file_path\":\"E:\\DesarrolloAI\\local-ai-semantic-search\\test_docs\\archivo.txt\"}"
```

Reemplazar `archivo.txt` por el nombre real del archivo.

Resultado esperado:

```json
{
  "status": "indexed",
  "file_path": "...",
  "chunks": 1
}
```

La indexación individual debe usar limpieza previa para evitar duplicación de chunks al reindexar el mismo archivo.

---

## 11. Indexar carpeta

Endpoint:

```text
POST /index-folder
```

Ejemplo CMD:

```cmd
curl -X POST http://127.0.0.1:8000/index-folder ^
  -H "Content-Type: application/json" ^
  -d "{\"folder_path\":\"E:\\DesarrolloAI\\local-ai-semantic-search\\test_docs\",\"recursive\":true,\"reindex_existing\":false,\"limit\":null}"
```

Campos:

```text
folder_path: ruta de carpeta a indexar
recursive: true o false
reindex_existing: true o false
limit: cantidad máxima de archivos o null
```

Resultado esperado:

```json
{
  "status": "ok",
  "mode": "index-folder",
  "files_found": 0,
  "indexed_count": 0,
  "skipped_count": 0,
  "errors_count": 0
}
```

---

## 12. Extensiones soportadas

Extensiones soportadas por el indexador:

```text
.txt
.pdf
.docx
.xlsx
.pptx
.png
.avif
```

---

## 13. Búsqueda full-text

Endpoint:

```text
POST /search/full-text
```

Ejemplo CMD:

```cmd
curl -X POST http://127.0.0.1:8000/search/full-text ^
  -H "Content-Type: application/json" ^
  -d "{\"query\":\"documento\",\"top_k\":5}"
```

Resultado esperado:

```json
{
  "status": "ok",
  "mode": "full-text",
  "query": "documento",
  "top_k": 5,
  "results_count": 0
}
```

---

## 14. Búsqueda semántica

Endpoint:

```text
POST /search/semantic
```

Ejemplo CMD:

```cmd
curl -X POST http://127.0.0.1:8000/search/semantic ^
  -H "Content-Type: application/json" ^
  -d "{\"query\":\"documento\",\"top_k\":5}"
```

Resultado esperado:

```json
{
  "status": "ok",
  "mode": "semantic",
  "query": "documento",
  "top_k": 5,
  "results_count": 0
}
```

La búsqueda semántica requiere query no vacía.

---

## 15. Búsqueda híbrida

Endpoint:

```text
POST /search/hybrid
```

Ejemplo CMD:

```cmd
curl -X POST http://127.0.0.1:8000/search/hybrid ^
  -H "Content-Type: application/json" ^
  -d "{\"query\":\"documento\",\"top_k\":5}"
```

Resultado esperado:

```json
{
  "status": "ok",
  "mode": "hybrid",
  "query": "documento",
  "top_k": 5,
  "results_count": 0
}
```

La búsqueda híbrida combina:

```text
SQLite FTS5
ChromaDB
score semántico
score textual
bonus por coincidencia en ambos motores
final_score
```

---

## 16. Filtrar archivos

Endpoint:

```text
POST /files/filter
```

Ejemplo por extensión:

```cmd
curl -X POST http://127.0.0.1:8000/files/filter ^
  -H "Content-Type: application/json" ^
  -d "{\"extension\":\".pdf\",\"filename\":null,\"path_contains\":null,\"text_contains\":null,\"limit\":20}"
```

Ejemplo por nombre:

```cmd
curl -X POST http://127.0.0.1:8000/files/filter ^
  -H "Content-Type: application/json" ^
  -d "{\"extension\":null,\"filename\":\"reporte\",\"path_contains\":null,\"text_contains\":null,\"limit\":20}"
```

Ejemplo por contenido:

```cmd
curl -X POST http://127.0.0.1:8000/files/filter ^
  -H "Content-Type: application/json" ^
  -d "{\"extension\":null,\"filename\":null,\"path_contains\":null,\"text_contains\":\"contrato\",\"limit\":20}"
```

---

## 17. Monitoreo

Estado general:

```cmd
curl http://127.0.0.1:8000/monitoring/status
```

Métricas consolidadas:

```cmd
curl http://127.0.0.1:8000/monitoring/metrics
```

Diagnóstico extendido:

```cmd
curl http://127.0.0.1:8000/monitoring/diagnostics
```

Runtime:

```cmd
curl http://127.0.0.1:8000/monitoring/runtime
```

---

## 18. Logs

Resumen de logs:

```cmd
curl http://127.0.0.1:8000/logs/summary
```

Últimas 100 líneas:

```cmd
curl "http://127.0.0.1:8000/logs?lines=100"
```

Logs locales:

```text
E:\DesarrolloAI\local-ai-semantic-search\logs\backend.log
```

---

## 19. Watcher

Estado del watcher:

```cmd
curl http://127.0.0.1:8000/watcher/status
```

Iniciar watcher:

```cmd
curl -X POST http://127.0.0.1:8000/watcher/start ^
  -H "Content-Type: application/json" ^
  -d "{\"folder_path\":\"E:\\DesarrolloAI\\local-ai-semantic-search\\test_docs\"}"
```

Detener watcher:

```cmd
curl -X POST http://127.0.0.1:8000/watcher/stop ^
  -H "Content-Type: application/json" ^
  -d "{}"
```

---

## 20. Validación de consistencia del índice

Consultar métricas antes de indexar:

```cmd
curl http://127.0.0.1:8000/monitoring/metrics
```

Reindexar archivo individual.

Consultar métricas después:

```cmd
curl http://127.0.0.1:8000/monitoring/metrics
```

Resultado esperado:

```text
No debe crecer artificialmente el número de chunks al reindexar el mismo archivo.
```

---

## 21. Problemas conocidos y solución

### 21.1 Backend no responde en puerto 8000

Error:

```text
curl: (7) Failed to connect to 127.0.0.1 port 8000
```

Causa:

```text
FastAPI/Uvicorn no está ejecutándose.
```

Solución:

```cmd
cd /d E:\DesarrolloAI\local-ai-semantic-search
semantica310\Scripts\activate.bat
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

### 21.2 Gradio no levanta por puerto 7860 ocupado

Error:

```text
OSError: Cannot find empty port in range: 7860-7860
```

Corrección permanente:

```text
run_gradio.py debe usar server_port=7861.
```

Validación:

```cmd
python run_gradio.py
```

Resultado esperado:

```text
Running on local URL:  http://127.0.0.1:7861
```

---

### 21.3 Query vacía en búsqueda semántica o híbrida

Error probable:

```text
ValueError: Empty text
```

Causa:

```text
La generación de embeddings requiere texto no vacío.
```

Corrección:

```text
Enviar query no vacía.
El backend debe validar query vacía y responder HTTP 400.
```

---

### 21.4 Reindexación duplica chunks

Causa:

```text
Indexar el mismo archivo sin limpieza previa.
```

Corrección:

```text
/index-file debe llamar index_file(..., cleanup_existing=True).
```

---

## 22. Dependencias

Archivo principal:

```text
requirements.txt
```

Dependencias críticas:

```text
fastapi
uvicorn
chromadb
sentence-transformers
torch
pypdf
python-docx
python-pptx
openpyxl
pillow
pillow-avif-plugin
watchdog
requests
gradio
```

Archivo UI:

```text
requirements_gradio.txt
```

Dependencias UI:

```text
gradio
requests
pillow
```

---

## 23. Checklist de validación local

Antes de considerar el proyecto como estable:

```text
[ ] Entorno semantica310 activa correctamente.
[ ] Backend levanta en 127.0.0.1:8000.
[ ] /health responde status ok.
[ ] /monitoring/status responde api, registry, chroma y runtime ok.
[ ] Gradio levanta en 127.0.0.1:7861.
[ ] UI Gradio muestra Health correctamente.
[ ] UI Gradio muestra SQLite correctamente.
[ ] UI Gradio muestra ChromaDB correctamente.
[ ] Búsqueda full-text devuelve respuesta válida.
[ ] Búsqueda semántica devuelve respuesta válida.
[ ] Búsqueda híbrida devuelve respuesta válida.
[ ] Filtros estructurados devuelven respuesta válida.
[ ] Logs responden correctamente.
[ ] Reindexación individual no duplica chunks.
[ ] requirements.txt no fija starlette manualmente.
[ ] requirements_gradio.txt usa versiones controladas.
```

---

## 24. Cierre operacional local

Para detener el backend o Gradio:

```text
CTRL + C
```

Ejecutar en la ventana CMD donde está corriendo el proceso.

---

## 25. Estado actual validado

Estado observado en validación local:

```text
Backend: ok
API: ok
Registry SQLite: ok
ChromaDB: ok
Runtime: ok
Watcher: stopped
FastAPI port: 8000
Gradio port previsto: 7861
files_count: 31
chunks_count: 35
```
