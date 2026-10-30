# Etapa base: sistema y dependencias de ejecución
FROM python:3.10-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Etapa de pruebas: docker build --target test -t inspeccion-botellas:test .
FROM base AS test

COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY . .

CMD ["python", "-m", "pytest", "-v", "tests"]

# Etapa final de producción
FROM base AS runtime

COPY model/ ./model/
COPY src/ ./src/
COPY frontend/ ./frontend/

RUN useradd --create-home --uid 1000 appuser
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/health', timeout=2)"]

CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
