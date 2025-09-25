# Integration Tests - Narrative & Gamification Modules

Este directorio contiene las pruebas de integración para validar la comunicación entre los módulos de Narrativa y Gamificación de YABOT.

## 🎯 Objetivo

Verificar que los eventos entre módulos funcionen correctamente y que los datos se mantengan consistentes durante las interacciones cross-module.

## 🧪 Pruebas Implementadas

### 1. **Reacción ❤️ → Besitos → Pista narrativa**
- **Archivo**: `test_narrative_gamification.py::test_reaction_to_besitos_to_hint_unlock`
- **Flujo**: Usuario reacciona → obtiene 10 besitos → compra pista → desbloquea contenido narrativo
- **Verifica**: Balance de besitos, inventario de usuario, integración EventBus

### 2. **Decisión narrativa → Misión desbloqueada**
- **Archivo**: `test_narrative_gamification.py::test_narrative_decision_to_mission_unlock`
- **Flujo**: Usuario elige "explorar_pasaje" → avanza narrativa → se asigna misión "Explorador"
- **Verifica**: Progreso narrativo, misiones activas, eventos publicados

### 3. **Logro desbloqueado → Beneficio narrativo**
- **Archivo**: `test_narrative_gamification.py::test_achievement_unlock_to_narrative_benefit`
- **Flujo**: Usuario completa 5 misiones → desbloquea "Coleccionista" → accede a contenido VIP sin suscripción
- **Verifica**: Sistema de logros, permisos de acceso, inventario

### 4. **Flujo completo de integración**
- **Archivo**: `test_narrative_gamification.py::test_full_integration_workflow`
- **Flujo**: Combinación de todos los workflows en una sola prueba
- **Verifica**: Consistencia de datos a través de múltiples operaciones

### 5. **Integración EventBus**
- **Archivo**: `test_narrative_gamification.py::test_event_bus_integration`
- **Flujo**: Publicación y consumo de eventos entre módulos
- **Verifica**: Comunicación asíncrona, manejo de errores

## 🚀 Ejecución de Pruebas

### Opción 1: Script dedicado (Recomendado)
```bash
# Desde el directorio raíz de yabot
python run_integration_tests.py

# Con salida verbose
python run_integration_tests.py --verbose

# Prueba específica
python run_integration_tests.py --test "reaction_to_besitos"
```

### Opción 2: Pytest directo
```bash
# Todas las pruebas de integración
pytest tests/integration/test_narrative_gamification.py -v

# Prueba específica
pytest tests/integration/test_narrative_gamification.py::TestNarrativeGamificationIntegration::test_reaction_to_besitos_to_hint_unlock -v

# Con cobertura
pytest tests/integration/test_narrative_gamification.py --cov=src/modules/gamification --cov=src/modules/narrative
```

## 📋 Prerrequisitos

### Servicios requeridos:
- **MongoDB**: Para almacenamiento de datos de prueba
- **Redis** (opcional): Para EventBus, si no está disponible usa cola local

### Configuración de entorno:
```bash
export MONGODB_DATABASE="yabot_integration_test"
export REDIS_URL="redis://localhost:6379/1"
export PYTEST_RUNNING="true"
```

### Dependencias Python:
```bash
pip install pytest pytest-asyncio pytest-cov
```

## 🔧 Estructura de Fixtures

### Fixtures principales:
- `event_bus`: EventBus configurado para pruebas
- `db_client`: Cliente MongoDB con base de datos de prueba
- `besitos_wallet`: Wallet de besitos con dependencias mockeadas
- `mission_manager`: Gestor de misiones
- `reaction_detector`: Detector de reacciones
- `clean_test_database`: Limpieza automática de datos de prueba

## ✅ Criterios de Éxito

### Test 1: Reacción → Besitos → Pista
- ✅ Balance de besitos = 0 tras compra
- ✅ Pista aparece en inventario del usuario
- ✅ Transacciones registradas correctamente

### Test 2: Decisión → Misión
- ✅ Misión "Explorador del Pasaje" está activa
- ✅ Evento NarrativeProgressUpdated publicado
- ✅ Progreso narrativo actualizado

### Test 3: Logro → Beneficio
- ✅ Fragmento "coleccion_secreta" accesible sin VIP
- ✅ Item de logro en inventario
- ✅ 5 misiones completadas registradas

## 🐛 Debugging

### Logs de prueba:
Los logs se generan con nivel DEBUG durante las pruebas. Para verlos:
```bash
pytest tests/integration/test_narrative_gamification.py -v -s --log-cli-level=DEBUG
```

### Datos de prueba:
Los datos se almacenan en la base de datos `yabot_integration_test` y se limpian automáticamente.

### Errores comunes:
1. **MongoDB no disponible**: Verificar que MongoDB esté ejecutándose
2. **Redis no disponible**: Las pruebas usan fallback a cola local
3. **Servicios no encontrados**: Algunos servicios se mockean automáticamente si no existen

## 📊 Métricas de Rendimiento

Las pruebas incluyen validaciones de tiempo de respuesta:
- Reacción → Besitos: < 500ms
- Decisión → Misión: < 2s
- Logro → Beneficio: < 1s
- EventBus publish/consume: < 100ms

## 🔄 CI/CD Integration

Estas pruebas están diseñadas para ejecutarse en pipelines de CI/CD:

```yaml
# Ejemplo para GitHub Actions
- name: Run Integration Tests
  run: |
    python run_integration_tests.py
  env:
    MONGODB_URI: ${{ secrets.MONGODB_TEST_URI }}
    REDIS_URL: ${{ secrets.REDIS_TEST_URL }}
```

## 📝 Notas Técnicas

- **Aislamiento**: Cada prueba usa datos independientes
- **Cleanup**: Limpieza automática de datos de prueba
- **Mocking**: Servicios externos mockeados cuando es necesario
- **Async**: Todas las pruebas son asíncronas usando pytest-asyncio
- **Fixtures**: Reutilización de componentes entre pruebas
- **Error Handling**: Validación de casos de error y recuperación