#!/bin/sh
# Prueba de humo contra un contenedor en ejecución.
# Termina con error si alguna respuesta no es la esperada.
# Uso: sh scripts/smoke_test.sh [url_base]
BASE_URL="${1:-http://localhost:8000}"
failures=0

check() {
  method="$1"; path="$2"; expected_code="$3"; expected_text="$4"; body="$5"
  echo "\$ $method $path $body"
  output=$(curl -s -w '\n%{http_code}' -X "$method" "$BASE_URL$path" -H 'Content-Type: application/json' ${body:+-d "$body"})
  code=$(printf '%s\n' "$output" | tail -n 1)
  response=$(printf '%s\n' "$output" | sed '$d')
  echo "$response"
  echo "HTTP $code"
  if [ "$code" != "$expected_code" ] || ! printf '%s' "$response" | grep -q "$expected_text"; then
    echo "FALLO: se esperaba HTTP $expected_code con $expected_text"
    failures=$((failures + 1))
  fi
  echo
}

check GET /health 200 '"model_loaded":true'
check POST /predict 200 '"status":"ACEPTADO"' '{"fill_level_ml": 598.35, "label_present_num": 1}'
check POST /predict 200 '"status":"RECHAZADO"' '{"fill_level_ml": 580.00, "label_present_num": 1}'
check POST /predict 200 '"status":"RECHAZADO"' '{"fill_level_ml": 618.50, "label_present_num": 1}'
check POST /predict 200 '"status":"RECHAZADO"' '{"fill_level_ml": 600.00, "label_present_num": 0}'
check POST /predict 200 '"status":"RECHAZADO"' '{"fill_level_ml": 575.00, "label_present_num": 0}'
check POST /predict 200 '"status":"ACEPTADO"' '{"fill_level_ml": 588.00, "label_present_num": 1}'
check POST /predict 200 '"status":"RECHAZADO"' '{"fill_level_ml": 999.00, "label_present_num": 1}'
check POST /predict 422 '"type":"missing"' '{"label_present_num": 1}'
check POST /predict 422 '"type":"finite_number"' '{"fill_level_ml": NaN, "label_present_num": 1}'

if [ "$failures" -gt 0 ]; then
  echo "Prueba de humo: $failures fallos"
  exit 1
fi
echo "Prueba de humo: 10 verificaciones correctas"
