# 🧪 Guía Rápida: Tests de Flujos de Usuario

Esta guía te permite ejecutar y modificar los tests de integración para validar diferentes escenarios del sistema YABOT.

## 🚀 Ejecución Básica

### Ejecutar Todos los Tests
```bash
# Script automático con resumen completo
python run_user_flow_tests.py

# Ejecutar manualmente (más control)
pytest tests/integration/test_user_flows.py -v
```

### Tests Específicos por Flujo
```bash
# Onboarding de usuario
pytest tests/integration/test_user_flows.py::TestOnboardingFlow -v

# Experiencia diaria (gifts + misiones)
pytest tests/integration/test_user_flows.py::TestDailyExperienceFlow -v

# Progresión emocional Diana
pytest tests/integration/test_user_flows.py::TestEmotionalProgressionFlow -v

# Economía de besitos
pytest tests/integration/test_user_flows.py::TestGamifiedEconomyFlow -v

# Journey completo (registro → círculo íntimo)
pytest tests/integration/test_user_flows.py::TestCrossModuleWorkflow -v
```

### Tests de Integración con Handlers
```bash
# Comandos de Telegram (/start, /menu, etc.)
pytest tests/integration/test_handler_module_integration.py::TestStartCommandIntegration -v

# Manejo de errores
pytest tests/integration/test_handler_module_integration.py::TestErrorHandlingIntegration -v
```

## 🎛️ Modificar Parámetros de Test

### 1. Cambiar Estado Emocional de Diana

**Archivo:** `tests/integration/test_user_flows.py`

**Ubicación:** Línea ~387, función `test_diana_level_progression_to_vip_access`

```python
# ORIGINAL
await mock_event_bus.publish("diana_level_progression", {
    "user_id": user_id,
    "previous_level": 3,
    "new_level": 4,  # 🔧 CAMBIAR AQUÍ
    "progression_reason": "authentic_vulnerability_reached",
    "emotional_metrics": {
        "authenticity_score": 0.82,  # 🔧 CAMBIAR AQUÍ (0.0-1.0)
        "vulnerability_depth": 0.75,  # 🔧 CAMBIAR AQUÍ (0.0-1.0)
        "consistency_rating": 0.88   # 🔧 CAMBIAR AQUÍ (0.0-1.0)
    },
    "vip_access_required": True  # 🔧 CAMBIAR AQUÍ
})
```

**Ejemplos de modificación:**
```python
# Progresión a nivel máximo
"new_level": 6,  # Círculo íntimo
"authenticity_score": 0.95,
"vulnerability_depth": 0.90,

# Progresión lenta (sin VIP)
"new_level": 2,
"vip_access_required": False,
"authenticity_score": 0.45,
```

### 2. Modificar Recompensas de Besitos

**Archivo:** `tests/integration/test_user_flows.py`

**Ubicación:** Línea ~270, función `test_daily_gift_and_mission_completion_flow`

```python
# Mock del daily gift system
system.claim_daily_gift.return_value = type('GiftResult', (), {
    'success': True,
    'message': 'Gift claimed',
    'gift_claimed': {
        "gift_type": "besitos",
        "amount": 25,  # 🔧 CAMBIAR CANTIDAD AQUÍ
        "next_claim_time": datetime.now() + timedelta(days=1)
    }
})()

# Mock del mission manager
reward_mock = type('Reward', (), {
    'besitos': 30,  # 🔧 CAMBIAR RECOMPENSA AQUÍ
    'items': []
})()
```

### 3. Cambiar Arquetipo Emocional

**Ubicación:** Línea ~354, función `test_narrative_interaction_triggers_emotional_analysis`

```python
# Simular análisis emocional resultante
await mock_event_bus.publish("emotional_signature_updated", {
    "user_id": user_id,
    "archetype": "Vulnerable_Explorer",  # 🔧 CAMBIAR AQUÍ
    "authenticity_score": 0.78,         # 🔧 CAMBIAR AQUÍ
    "signature_strength": 0.85,         # 🔧 CAMBIAR AQUÍ
    "previous_archetype": "Explorer"    # 🔧 CAMBIAR AQUÍ
})
```

**Arquetipos disponibles:**
- `"Explorer"` - Inicial, curioso
- `"Curious_Explorer"` - Más involucrado
- `"Trusting_Sharer"` - Comienza a compartir
- `"Vulnerable_Connector"` - Abre corazón
- `"Deep_Authentic"` - Muy auténtico
- `"Intimate_Circle"` - Círculo íntimo

## 🔧 Crear Tests Personalizados

### Test Personalizado: Progresión Rápida
```python
@pytest.mark.asyncio
async def test_fast_diana_progression(mock_event_bus, event_capture):
    """Test progresión acelerada de Diana"""
    user_id = "speed_user_123"

    # Progresión directa a nivel 5
    await mock_event_bus.publish("diana_level_progression", {
        "user_id": user_id,
        "previous_level": 1,
        "new_level": 5,  # Salto directo
        "progression_reason": "exceptional_authenticity",
        "emotional_metrics": {
            "authenticity_score": 0.98,  # Muy alto
            "vulnerability_depth": 0.95,
            "consistency_rating": 0.92
        },
        "vip_access_required": True
    })

    # Verificar que se dispara VIP
    assert event_capture.has_event_type("diana_level_progression")

    progression_events = event_capture.get_events_by_type("diana_level_progression")
    assert progression_events[0]["new_level"] == 5
    assert progression_events[0]["authenticity_score"] > 0.9
```

### Test Personalizado: Usuario Con Muchos Besitos
```python
@pytest.mark.asyncio
async def test_rich_user_economy(mock_event_bus, event_capture):
    """Test usuario con muchos besitos"""
    user_id = "rich_user_123"

    # Usuario gana muchos besitos
    await mock_event_bus.publish("besitos_awarded", {
        "user_id": user_id,
        "amount": 5000,  # Cantidad alta
        "reason": "special_event_bonus",
        "source": "admin_system",
        "balance_after": 5000
    })

    # Usuario gasta en contenido premium
    await mock_event_bus.publish("besitos_spent", {
        "user_id": user_id,
        "amount": 1000,
        "reason": "exclusive_content_pack",
        "item_id": "premium_diana_sessions",
        "balance_after": 4000
    })

    # Verificar transacciones
    besitos_events = event_capture.get_events_by_type("besitos_awarded")
    spent_events = event_capture.get_events_by_type("besitos_spent")

    assert besitos_events[0]["amount"] == 5000
    assert spent_events[0]["balance_after"] == 4000
```

## 📊 Verificar Eventos Específicos

### Ver Todos los Eventos Capturados
```python
# En cualquier test, agregar al final:
def test_debug_events(event_capture):
    # ... ejecutar acciones ...

    # Ver todos los eventos
    print("\\n=== EVENTOS CAPTURADOS ===")
    for i, (event_type, event_data) in enumerate(zip(event_capture.event_types, event_capture.events)):
        print(f"{i+1}. {event_type}: {event_data}")

    # Ver eventos específicos
    diana_events = event_capture.get_events_by_type("diana_level_progression")
    print(f"\\nEventos de Diana: {diana_events}")
```

### Ejecutar con Debug
```bash
# Ver output detallado
pytest tests/integration/test_user_flows.py::TestOnboardingFlow -v -s

# Ver logs del sistema
pytest tests/integration/test_user_flows.py -v --log-cli-level=DEBUG
```

## 🎯 Escenarios de Prueba Sugeridos

### 1. Usuario Que No Progresa
```python
# Modificar en test_diana_level_progression_to_vip_access
"authenticity_score": 0.30,  # Muy bajo
"new_level": 1,  # Se queda en nivel 1
"vip_access_required": False
```

### 2. Usuario Super Activo
```python
# En test_complete_user_journey_integration, cambiar:
for day in range(1, 30):  # 30 días en lugar de 14
    # Más actividad diaria
```

### 3. Usuario Con Problemas Técnicos
```python
# Simular errores en el event bus
failing_event_bus.publish.side_effect = Exception("Network error")
```

## 🔍 Análisis de Resultados

### Ver Métricas de Performance
```bash
# Test con métricas de tiempo
pytest tests/integration/test_event_flow_performance.py -v --durations=10
```

### Generar Reporte HTML
```bash
# Instalar pytest-html si no está
pip install pytest-html

# Generar reporte
pytest tests/integration/ --html=test_report.html --self-contained-html
```

## 🆘 Troubleshooting

### Error: "Mock object has no attribute"
**Problema:** El mock no tiene el método esperado
**Solución:** Verificar nombres de métodos en los archivos del módulo real

```bash
# Ver métodos disponibles
grep "def " src/modules/gamification/daily_gift.py
```

### Error: "AttributeError in event creation"
**Problema:** Campos faltantes en eventos
**Solución:** Verificar estructura en `src/events/models.py`

### Tests Muy Lentos
**Solución:** Reducir número de eventos o usuarios:
```python
# En test de performance
num_events = 100  # En lugar de 1000
num_users = 10    # En lugar de 50
```

## 📝 Comandos Útiles

```bash
# Ejecutar solo tests que pasaron la última vez
pytest --lf tests/integration/

# Ejecutar solo tests que fallaron
pytest --ff tests/integration/

# Parar en el primer fallo
pytest -x tests/integration/

# Ejecutar en paralelo (si tienes pytest-xdist)
pytest -n 4 tests/integration/

# Ver cobertura de código
pytest --cov=src tests/integration/
```

¡Con esta guía puedes modificar cualquier aspecto de los tests para validar diferentes escenarios del sistema YABOT!