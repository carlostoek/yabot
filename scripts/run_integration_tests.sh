#!/bin/bash

# run_integration_tests.sh
# Ejecuta pruebas de integración reales de DianaBot con cobertura

set -e  # Detener si hay error

echo "🚀 Iniciando pruebas de integración de DianaBot..."
echo "==============================================="

# Verificar que MongoDB y Redis estén corriendo
echo "🔍 Verificando dependencias..."

if ! pgrep mongod > /dev/null; then
    echo "❌ MongoDB no está corriendo. Inicia mongod y vuelve a intentar."
    exit 1
fi

if ! pgrep redis-server > /dev/null; then
    echo "❌ Redis no está corriendo. Inicia redis-server y vuelve a intentar."
    exit 1
fi

echo "✅ MongoDB y Redis están activos."

# Asegurar que src/ está en el path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Ruta al test
TEST_FILE="tests/integration/test_real_narrative_gamification.py"

if [ ! -f "$TEST_FILE" ]; then
    echo "❌ Archivo de prueba no encontrado: $TEST_FILE"
    exit 1
fi

echo "🧪 Ejecutando pruebas de integración con cobertura..."

# Ejecutar pytest con cobertura
python -m pytest \
  "$TEST_FILE" \
  --cov=src.modules.gamification \
  --cov=src.modules.narrative \
  --cov-report=term-missing \
  --cov-report=html:htmlcov \
  --cov-fail-under=85 \
  -v \
  --tb=short

echo ""
echo "📊 Reporte de cobertura guardado en: htmlcov/index.html"
echo "✅ Pruebas de integración completadas con éxito."
