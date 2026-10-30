const REASONS = {
  BAJO_LLENADO: "Nivel de llenado bajo",
  ALTO_LLENADO: "Nivel de llenado alto",
  SIN_ETIQUETA: "Etiqueta ausente",
  ALERTA_MODELO: "Alerta del modelo",
};

const form = document.getElementById("inspection-form");
const fillInput = document.getElementById("fill");
const submit = document.getElementById("submit");
const result = document.getElementById("result");
const verdict = document.getElementById("verdict");
const reasons = document.getElementById("reasons");
const details = document.getElementById("details");
const historyBody = document.getElementById("history");
const counters = document.getElementById("counters");
const healthBadge = document.getElementById("health");
const healthText = document.getElementById("health-text");

let inspected = 0;
let rejected = 0;

function showError(message) {
  result.dataset.state = "error";
  verdict.textContent = "No se pudo inspeccionar";
  reasons.textContent = message;
  details.hidden = true;
}

function describeReasons(data) {
  if (data.rejection_reasons.length === 0) return "Dentro de especificación";
  return data.rejection_reasons.map((code) => REASONS[code] || code).join(" · ");
}

function showResult(data) {
  result.dataset.state = data.target === 1 ? "bad" : "ok";
  verdict.textContent = data.status;
  reasons.textContent = describeReasons(data);
  document.getElementById("d-prob").textContent = `${(data.probability_reject * 100).toFixed(2)} %`;
  document.getElementById("d-rule").textContent = data.rule_rejected ? "Rechaza" : "Aprueba";
  document.getElementById("d-model").textContent = data.model_rejected ? "Rechaza" : "Aprueba";
  document.getElementById("d-time").textContent = `${data.inference_ms.toFixed(2)} ms`;
  details.hidden = false;
}

function addCell(row, text, className) {
  const cell = row.insertCell();
  cell.textContent = text;
  if (className) cell.className = className;
}

function addHistory(payload, data) {
  inspected += 1;
  if (data.target === 1) rejected += 1;
  counters.textContent = `${inspected} inspeccionadas · ${rejected} rechazadas`;

  document.getElementById("empty-row")?.remove();
  const row = historyBody.insertRow(0);
  addCell(row, new Date().toLocaleTimeString("es-MX"), "num");
  addCell(row, payload.fill_level_ml.toFixed(2), "num");
  addCell(row, payload.label_present_num === 1 ? "Presente" : "Ausente");
  addCell(row, data.status, data.target === 1 ? "bad" : "ok");
  addCell(row, data.target === 1 ? describeReasons(data) : "—");
}

function validationMessage(body) {
  if (Array.isArray(body.detail)) return body.detail.map((item) => item.msg).join("; ");
  return body.detail || "La API rechazó la solicitud.";
}

async function inspect() {
  const payload = {
    fill_level_ml: Number(fillInput.value),
    label_present_num: Number(form.elements.label.value),
  };
  if (fillInput.value === "" || !Number.isFinite(payload.fill_level_ml)) {
    showError("Captura un nivel de llenado numérico.");
    return;
  }

  submit.disabled = true;
  try {
    const response = await fetch("/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const body = await response.json();
    if (!response.ok) {
      showError(`HTTP ${response.status}: ${validationMessage(body)}`);
      return;
    }
    showResult(body);
    addHistory(payload, body);
  } catch (error) {
    showError("No hay conexión con la API.");
  } finally {
    submit.disabled = false;
  }
}

async function checkHealth() {
  try {
    const response = await fetch("/health");
    const body = await response.json();
    const ok = response.ok && body.model_loaded;
    healthBadge.dataset.state = ok ? "ok" : "down";
    healthText.textContent = ok ? "API en línea · modelo cargado" : "API sin modelo";
  } catch (error) {
    healthBadge.dataset.state = "down";
    healthText.textContent = "API sin conexión";
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  inspect();
});

document.getElementById("presets").addEventListener("click", (event) => {
  const preset = event.target.closest("button");
  if (!preset) return;
  fillInput.value = preset.dataset.fill;
  form.elements.label.value = preset.dataset.label;
  inspect();
});

const emptyRow = historyBody.insertRow();
emptyRow.id = "empty-row";
const emptyCell = emptyRow.insertCell();
emptyCell.colSpan = 5;
emptyCell.className = "empty";
emptyCell.textContent = "Aún no hay inspecciones en esta sesión.";

checkHealth();
setInterval(checkHealth, 15000);
