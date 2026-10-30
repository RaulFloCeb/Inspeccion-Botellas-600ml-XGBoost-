"""Pruebas de integración de la API (matriz §9 de la documentación técnica)."""
import pytest
from fastapi.testclient import TestClient

from src import api


@pytest.fixture(scope="module")
def client():
    with TestClient(api.app) as test_client:
        yield test_client


def post(client, fill, label):
    return client.post("/predict", json={"fill_level_ml": fill, "label_present_num": label})


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "model_loaded": True}


def test_frontend_servido(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Inspección de Botellas 600ml" in response.text
    assert client.get("/static/app.js").status_code == 200


def test_openapi_expone_endpoints(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/predict" in paths and "/health" in paths


@pytest.mark.parametrize(
    "case, fill, label, status, reasons",
    [
        ("TC-01", 598.35, 1, "ACEPTADO", []),
        ("TC-02", 580.00, 1, "RECHAZADO", ["BAJO_LLENADO"]),
        ("TC-03", 618.50, 1, "RECHAZADO", ["ALTO_LLENADO"]),
        ("TC-04", 600.00, 0, "RECHAZADO", ["SIN_ETIQUETA"]),
        ("TC-05", 575.00, 0, "RECHAZADO", ["BAJO_LLENADO", "SIN_ETIQUETA"]),
    ],
)
def test_matriz_funcional(client, case, fill, label, status, reasons):
    response = post(client, fill, label)
    assert response.status_code == 200, case
    body = response.json()
    assert body["status"] == status, case
    assert body["target"] == (1 if status == "RECHAZADO" else 0), case
    assert body["rejection_reasons"] == reasons, case


@pytest.mark.parametrize(
    "fill, status",
    [
        (587.99, "RECHAZADO"),
        (588.0, "ACEPTADO"),
        (612.0, "ACEPTADO"),
        (612.01, "RECHAZADO"),
        (999.0, "RECHAZADO"),
        (0.0, "RECHAZADO"),
    ],
)
def test_limites_y_outliers(client, fill, status):
    assert post(client, fill, 1).json()["status"] == status


@pytest.mark.parametrize(
    "payload",
    [
        {"label_present_num": 1},
        {"fill_level_ml": 600.0},
        {"fill_level_ml": None, "label_present_num": 1},
        {"fill_level_ml": "abc", "label_present_num": 1},
        {"fill_level_ml": -1, "label_present_num": 1},
        {"fill_level_ml": 2000.01, "label_present_num": 1},
        {"fill_level_ml": 600.0, "label_present_num": 2},
        {"fill_level_ml": 600.0, "label_present_num": "SI"},
        {"fill_level_ml": 600.0, "label_present_num": True},
        {"fill_level_mm": 600.0, "label_present_num": 1},
        {"fill_level_ml": 600.0, "label_present_num": 1, "extra": True},
        {},
    ],
)
def test_entradas_invalidas_devuelven_422(client, payload):
    assert client.post("/predict", json=payload).status_code == 422


@pytest.mark.parametrize("raw", ["NaN", "Infinity", "-Infinity"])
def test_valores_no_finitos_devuelven_422(client, raw):
    response = client.post(
        "/predict",
        content=f'{{"fill_level_ml": {raw}, "label_present_num": 1}}',
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


def test_json_malformado_devuelve_422(client):
    response = client.post(
        "/predict", content="{no es json", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422


def test_el_servicio_sigue_vivo_tras_entradas_invalidas(client):
    client.post("/predict", json={})
    assert post(client, 600.0, 1).json()["status"] == "ACEPTADO"


def test_regla_protege_defectos_que_el_modelo_acepta(client):
    body = post(client, 580.0, 1).json()
    assert body["rule_rejected"] is True
    assert body["model_rejected"] is False
    assert body["status"] == "RECHAZADO"


def test_alerta_del_modelo_rechaza_aunque_la_regla_apruebe(client, monkeypatch):
    monkeypatch.setitem(api.state, "metadata", {**api.state["metadata"], "threshold": 0.0})
    body = post(client, 600.0, 1).json()
    assert body["rule_rejected"] is False
    assert body["model_rejected"] is True
    assert body["status"] == "RECHAZADO"
    assert body["rejection_reasons"] == ["ALERTA_MODELO"]


def test_sin_modelo_devuelve_503(client, monkeypatch):
    monkeypatch.setitem(api.state, "model", None)
    assert client.get("/health").status_code == 503
    assert post(client, 600.0, 1).status_code == 503
