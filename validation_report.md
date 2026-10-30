# Resumen de validación

Fecha: 30 de octubre de 2026. Imagen `inspeccion-botellas:v1.0`, ejecutada en Docker 28.3.0 (linux/arm64). El informe completo está en [docs/Documento_Validacion_Pruebas.docx](docs/Documento_Validacion_Pruebas.docx).

## Resultado

| Área | Resultado | Evidencia |
|---|---|---|
| Pruebas automatizadas | 34 de 34 aprobadas | [pytest.txt](docs/evidencia/pytest.txt) |
| Contenedor | Construido, en ejecución y `healthy`, con usuario sin privilegios | [ejecucion_local.txt](docs/evidencia/ejecucion_local.txt) |
| Integración frontend y API | Correcta | [frontend_panel.jpg](docs/evidencia/frontend_panel.jpg) |
| Endpoints documentados | `/health` y `/predict` | [swagger_endpoints.jpg](docs/evidencia/swagger_endpoints.jpg), [openapi.json](docs/openapi.json) |
| Imagen `linux/amd64` | Construida y probada con emulación | Sección 6 del informe completo |
| Integración continua | Workflow con PyTest, construcción de imagen y prueba de humo | [ci.yml](.github/workflows/ci.yml) |

## Matriz funcional

| ID | Llenado (ml) | Etiqueta | Esperado | Obtenido API | Modelo solo |
|---|---|---|---|---|---|
| TC-01 | 598.35 | 1 | ACEPTADO | ACEPTADO | ACEPTADO |
| TC-02 | 580.00 | 1 | RECHAZADO | RECHAZADO | **ACEPTADO** |
| TC-03 | 618.50 | 1 | RECHAZADO | RECHAZADO | **ACEPTADO** |
| TC-04 | 600.00 | 0 | RECHAZADO | RECHAZADO | RECHAZADO |
| TC-05 | 575.00 | 0 | RECHAZADO | RECHAZADO | RECHAZADO |

## Latencia medida

Medida desde el host contra el contenedor.

| Carga | Solicitudes | Media (ms) | p99 (ms) | Errores |
|---|---|---|---|---|
| Secuencial (5 repeticiones) | 1,000 c/u | 2.5 a 2.7 | 5.7 a 8.6 | 0 |
| 10 concurrentes (3 repeticiones) | 200 c/u | 17.7 a 20.3 | 55.3 a 88.8 | 0 |
| 100 simultáneas (3 repeticiones) | 100 c/u | 213.5 a 339.2 | 326.0 a 435.1 | 0 |

## Conclusión

La solución funciona en ejecución local, que es el alcance del proyecto. No está lista para operar en planta: faltan datos reales, pruebas con sensores y PLC, y verificar la latencia en el hardware final.
