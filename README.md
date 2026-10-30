# Inspección de Botellas 600ml (XGBoost)

[![CI](https://github.com/inetshell/inspeccion-botellas-xgboost/actions/workflows/ci.yml/badge.svg)](https://github.com/inetshell/inspeccion-botellas-xgboost/actions/workflows/ci.yml)

Modelo desplegable de inspección de botellas de 600ml para detectar producto fuera de especificación de nivel de llenado y presencia de etiqueta.

Un panel web envía las lecturas de los sensores a una API REST (FastAPI), que responde `ACEPTADO` o `RECHAZADO`. Todo corre en un solo contenedor Docker, de forma local.

## Inicio rápido

Requisitos: Docker 24 o superior, Git y el puerto 8000 libre.

```bash
git clone https://github.com/inetshell/inspeccion-botellas-xgboost.git
cd inspeccion-botellas-xgboost
docker build -t inspeccion-botellas:v1.0 .
docker run -d -p 8000:8000 --name app inspeccion-botellas:v1.0
curl http://localhost:8000/health
```

Respuesta esperada: `{"status":"healthy","model_loaded":true}`

| Recurso | URL |
|---|---|
| Panel web (frontend) | http://localhost:8000/ |
| Documentación interactiva (Swagger) | http://localhost:8000/docs |
| Especificación OpenAPI | http://localhost:8000/openapi.json |

También se puede levantar con `docker compose up -d --build`. Para detenerlo: `docker rm -f app`.

## API

### `POST /predict`

```bash
curl -X POST http://localhost:8000/predict \
  -H 'Content-Type: application/json' \
  -d '{"fill_level_ml": 580.0, "label_present_num": 1}'
```

| Campo de entrada | Tipo | Valores |
|---|---|---|
| `fill_level_ml` | número | 0 a 2000 ml (especificación: 588 a 612) |
| `label_present_num` | entero | `1` presente, `0` ausente |

```json
{
  "status": "RECHAZADO",
  "target": 1,
  "probability_reject": 0.986382,
  "threshold": 0.9990915060043335,
  "rule_rejected": true,
  "model_rejected": false,
  "rejection_reasons": ["BAJO_LLENADO"],
  "model_version": "1.0.0",
  "inference_ms": 1.518
}
```

| Código | Significado |
|---|---|
| 200 | Inspección realizada |
| 422 | Entrada inválida (campo faltante, tipo incorrecto, fuera de rango, NaN) |
| 503 | Modelo no disponible |

### `GET /health`

Devuelve 200 con el modelo cargado y 503 si no lo está.

## Cómo se decide

Una botella se rechaza si lo indica **cualquiera** de estas capas:

1. **Regla de especificación:** llenado de 588 a 612 ml (600 ml ± 2 %) y etiqueta presente.
2. **Modelo XGBoost:** probabilidad de rechazo mayor o igual al umbral 0.999092.

La regla es imprescindible. El dataset no tiene ejemplos entre 581.82 y 590.28 ml ni entre 611.00 y 613.52 ml, y con ese umbral el modelo solo acepta todos los defectos de llenado. Con el umbral 0.5 rechaza botellas conformes entre 588 y 591.5 ml y entre 607.9 y 612 ml. Con el umbral actual, el resultado final coincide con la regla, y el modelo aporta la probabilidad para monitoreo. El detalle está en [docs/evidencia/evaluacion_modelo.txt](docs/evidencia/evaluacion_modelo.txt).

## Pruebas

```bash
docker build --target test -t inspeccion-botellas:test .
docker run --rm inspeccion-botellas:test
```

Con el contenedor en ejecución:

```bash
sh scripts/smoke_test.sh
python3 scripts/stress_test.py http://localhost:8000 100 100
```

La prueba de humo termina con error si alguna respuesta no es la esperada.

## Integración continua

El workflow [ci.yml](.github/workflows/ci.yml) se ejecuta en GitHub Actions con cada `push` o `pull request` hacia `main`, y también manualmente desde la pestaña **Actions**.

| Job | Qué hace |
|---|---|
| `pruebas` | Construye la etapa `test` del Dockerfile y ejecuta PyTest |
| `imagen` | Construye la imagen final, inicia el contenedor, ejecuta la prueba de humo, verifica el frontend y guarda la imagen como artefacto durante 7 días |

El job `imagen` solo corre si `pruebas` termina bien. Para usar la imagen generada, descarga el artefacto `imagen-docker` de la ejecución y cárgala con:

```bash
gunzip -c inspeccion-botellas-v1.0.tar.gz | docker load
```

## Reentrenar el modelo

```bash
docker build --target test -t inspeccion-botellas:test .
docker run --rm -v "$PWD/model:/app/model" inspeccion-botellas:test python -m src.train
docker build -t inspeccion-botellas:v1.0 .
```

## Estructura

```text
├── .github/workflows/       Workflow de pruebas y construcción de la imagen
├── data/                    Dataset con 0.2 % de rechazos
├── docs/                    Manual, validación, OpenAPI y evidencia
├── frontend/                Panel web (HTML, CSS y JavaScript)
├── model/                   Modelo serializado y sus metadatos
├── notebooks/               Notebook original de entrenamiento
├── scripts/                 Evaluación, prueba de humo y estrés
├── src/
│   ├── api.py               Endpoints y lógica de decisión
│   └── train.py             Reentrenamiento reproducible
├── tests/test_api.py        34 pruebas con PyTest
├── Dockerfile               Etapas base, test y runtime
├── docker-compose.yml
├── requirements.txt         Dependencias de producción con versión fija
├── requirements-dev.txt     Dependencias de pruebas y entrenamiento
└── validation_report.md     Resumen de pruebas
```

## Documentación

- [Manual de despliegue](docs/Manual_Despliegue_Local.docx)
- [Documento de validación y pruebas](docs/Documento_Validacion_Pruebas.docx)
- [Resumen de validación](validation_report.md)

## Limitaciones

Los datos son sintéticos, con solo 10 rechazos en 5,000 registros, y el sistema no se ha probado con sensores reales. El alcance es la ejecución local en Docker.

## Autoría

Raúl Flores Ceballos
