# 🎮 Ejemplos Prácticos: Modificación de Tests

Esta guía contiene ejemplos paso a paso para modificar los tests y probar diferentes escenarios.

## 🧠 Modificar Estados Emocionales de Diana

### Ejemplo 1: Usuario Que Progresa Muy Rápido

**Archivo a modificar:** `tests/integration/test_user_flows.py`
**Función:** `test_diana_level_progression_to_vip_access` (línea ~387)

```python
# ANTES (progresión normal)
await mock_event_bus.publish("diana_level_progression", {
    "user_id": user_id,
    "previous_level": 3,
    "new_level": 4,
    "emotional_metrics": {
        "authenticity_score": 0.82,
        "vulnerability_depth": 0.75,
        "consistency_rating": 0.88
    }
})

# DESPUÉS (progresión súper rápida)
await mock_event_bus.publish("diana_level_progression", {
    "user_id": user_id,
    "previous_level": 1,  # 🔧 Desde nivel 1
    "new_level": 6,       # 🔧 Directo a círculo íntimo
    "emotional_metrics": {
        "authenticity_score": 0.98,  # 🔧 Muy auténtico
        "vulnerability_depth": 0.95,  # 🔧 Muy vulnerable
        "consistency_rating": 0.97    # 🔧 Muy consistente
    }
})
```

**Ejecutar:**
```bash
pytest tests/integration/test_user_flows.py::TestEmotionalProgressionFlow::test_diana_level_progression_to_vip_access -v -s
```

### Ejemplo 2: Usuario Que Se Queda Estancado

```python
# Usuario con baja autenticidad (se queda en nivel 2)
await mock_event_bus.publish("diana_level_progression", {
    "user_id": user_id,
    "previous_level": 1,
    "new_level": 2,        # 🔧 Progreso lento
    "emotional_metrics": {
        "authenticity_score": 0.35,  # 🔧 Baja autenticidad
        "vulnerability_depth": 0.25,  # 🔧 Poco vulnerable
        "consistency_rating": 0.40    # 🔧 Inconsistente
    },
    "vip_access_required": False  # 🔧 No necesita VIP aún
})

# Agregar verificación de que NO se otorga VIP
assert not event_capture.has_event_type("vip_access_granted")
```

### Ejemplo 3: Cambio de Arquetipo Emocional

**Función:** `test_narrative_interaction_triggers_emotional_analysis` (línea ~354)

```python
# ANTES (arquetipo Explorer → Vulnerable_Explorer)
await mock_event_bus.publish("emotional_signature_updated", {
    "user_id": user_id,
    "archetype": "Vulnerable_Explorer",
    "authenticity_score": 0.78,
    "previous_archetype": "Explorer"
})

# DESPUÉS (cambio dramático a Deep_Authentic)
await mock_event_bus.publish("emotional_signature_updated", {
    "user_id": user_id,
    "archetype": "Deep_Authentic",     # 🔧 Cambio mayor
    "authenticity_score": 0.92,       # 🔧 Score muy alto
    "signature_strength": 0.95,       # 🔧 Muy confiable
    "previous_archetype": "Explorer"  # 🔧 Salto grande
})

# Verificar el cambio dramático
emotional_events = event_capture.get_events_by_type("emotional_signature_updated")
assert emotional_events[0]["archetype"] == "Deep_Authentic"
assert emotional_events[0]["authenticity_score"] > 0.9
```

## 💰 Modificar Economía de Besitos

### Ejemplo 4: Usuario Millonario

**Archivo:** `tests/integration/test_user_flows.py`
**Función:** `test_besitos_economy_full_cycle` (línea ~488)

```python
# ANTES (economía normal)
await mock_event_bus.publish("besitos_awarded", {
    "user_id": user_id,
    "amount": 200,
    "balance_after": 350
})

# DESPUÉS (usuario millonario)
await mock_event_bus.publish("besitos_awarded", {
    "user_id": user_id,
    "amount": 10000,      # 🔧 Mega recompensa
    "reason": "diamond_achievement_bonus",  # 🔧 Razón especial
    "source": "special_event_system",
    "balance_after": 10000
})

# Usuario gasta mucho también
await mock_event_bus.publish("besitos_spent", {
    "user_id": user_id,
    "amount": 5000,       # 🔧 Gasto alto
    "reason": "exclusive_diana_sessions", # 🔧 Contenido premium
    "item_id": "ultimate_access_pass",
    "balance_after": 5000  # 🔧 Aún queda mucho
})
```

### Ejemplo 5: Usuario Que Se Queda Sin Besitos

**Función:** Crear nueva función en `TestGamifiedEconomyFlow`

```python
@pytest.mark.asyncio
async def test_broke_user_scenario(self, cross_module_service, mock_event_bus, event_capture):
    """Test usuario que se queda sin besitos"""
    user_id = "broke_user_123"

    # Usuario empieza con pocos besitos
    await mock_event_bus.publish("besitos_awarded", {
        "user_id": user_id,
        "amount": 50,
        "reason": "registration_bonus",
        "balance_after": 50
    })

    # Usuario gasta todo
    await mock_event_bus.publish("besitos_spent", {
        "user_id": user_id,
        "amount": 50,
        "reason": "impulse_purchase",
        "item_id": "mystery_box",
        "balance_after": 0  # 🔧 Se queda en 0
    })

    # Verificar que el usuario se quedó sin dinero
    spent_events = event_capture.get_events_by_type("besitos_spent")
    assert spent_events[0]["balance_after"] == 0

    # Usuario no puede acceder a contenido premium
    # (esto activaría lógica de "necesitas más besitos")
```

## 📅 Modificar Actividad Diaria

### Ejemplo 6: Usuario Súper Activo (30 días)

**Función:** `test_complete_user_journey_integration` (línea ~563)

```python
# ANTES (2 semanas)
for day in range(1, 15):  # 2 semanas de actividad

# DESPUÉS (30 días de actividad intensa)
for day in range(1, 31):  # 🔧 Un mes completo
    # Gift diario
    await mock_event_bus.publish("daily_gift_claimed", {
        "user_id": user_id,
        "gift_type": "besitos",
        "gift_amount": 25 + (day * 2)  # 🔧 Recompensa incremental
    })

    # Múltiples interacciones por día
    for interaction in range(3):  # 🔧 3 interacciones por día
        await mock_event_bus.publish("user_interaction", {
            "user_id": user_id,
            "action": "narrative_choice",
            "context": {
                "authenticity_score": 0.7 + (day * 0.01),
                "daily_interaction": interaction + 1
            }
        })

# Verificar actividad sostenida
gift_events = event_capture.get_events_by_type("daily_gift_claimed")
assert len(gift_events) >= 30  # 30 días de gifts

interaction_events = event_capture.get_events_by_type("user_interaction")
assert len(interaction_events) >= 90  # 3 por día x 30 días
```

### Ejemplo 7: Usuario Perezoso (actividad mínima)

```python
@pytest.mark.asyncio
async def test_lazy_user_journey(self, cross_module_service, mock_event_bus, event_capture):
    """Test usuario con actividad mínima"""
    user_id = "lazy_user_123"

    # Solo registrarse
    await mock_event_bus.publish("user_registered", {
        "user_id": user_id,
        "telegram_user_id": 999999999
    })

    # Solo 3 días de actividad en 2 semanas
    active_days = [1, 7, 14]  # 🔧 Solo 3 días activos

    for day in active_days:
        await mock_event_bus.publish("daily_gift_claimed", {
            "user_id": user_id,
            "gift_type": "besitos",
            "gift_amount": 25
        })

        # Solo 1 interacción por día activo
        await mock_event_bus.publish("user_interaction", {
            "user_id": user_id,
            "action": "narrative_choice",
            "context": {"authenticity_score": 0.3}  # 🔧 Baja por inactividad
        })

    # Verificar progresión lenta
    gift_events = event_capture.get_events_by_type("daily_gift_claimed")
    assert len(gift_events) == 3  # Solo 3 días

    interaction_events = event_capture.get_events_by_type("user_interaction")
    assert len(interaction_events) == 3  # Mínima interacción
```

## 🎭 Crear Escenarios Personalizados

### Ejemplo 8: Test de Crisis Emocional

```python
@pytest.mark.asyncio
async def test_emotional_crisis_recovery(self, mock_event_bus, event_capture):
    """Test usuario que tiene crisis pero se recupera"""
    user_id = "crisis_user_123"

    # Usuario progresa normalmente
    await mock_event_bus.publish("diana_level_progression", {
        "user_id": user_id,
        "previous_level": 2,
        "new_level": 3,
        "emotional_metrics": {"authenticity_score": 0.75}
    })

    # Crisis emocional - baja autenticidad
    await mock_event_bus.publish("emotional_signature_updated", {
        "user_id": user_id,
        "archetype": "Withdrawn_Explorer",  # 🔧 Arquetipo de crisis
        "authenticity_score": 0.25,        # 🔧 Score muy bajo
        "signature_strength": 0.30,
        "previous_archetype": "Trusting_Sharer"
    })

    # Recuperación después de apoyo
    await mock_event_bus.publish("emotional_signature_updated", {
        "user_id": user_id,
        "archetype": "Healing_Connector",   # 🔧 Arquetipo de sanación
        "authenticity_score": 0.80,        # 🔧 Se recupera
        "signature_strength": 0.85,
        "previous_archetype": "Withdrawn_Explorer"
    })

    # Verificar el ciclo crisis-recuperación
    emotional_events = event_capture.get_events_by_type("emotional_signature_updated")
    assert len(emotional_events) == 2
    assert emotional_events[0]["authenticity_score"] < 0.3  # Crisis
    assert emotional_events[1]["authenticity_score"] > 0.7  # Recuperación
```

### Ejemplo 9: Test de Usuario VIP Problemático

```python
@pytest.mark.asyncio
async def test_problematic_vip_user(self, mock_event_bus, event_capture):
    """Test usuario VIP que abusa del sistema"""
    user_id = "problematic_vip_123"

    # Usuario obtiene VIP
    await mock_event_bus.publish("vip_access_granted", {
        "user_id": user_id,
        "reason": "subscription_activated"
    })

    # Abuso: gasta besitos irresponsablemente
    for purchase in range(10):  # 🔧 10 compras seguidas
        await mock_event_bus.publish("besitos_spent", {
            "user_id": user_id,
            "amount": 500,
            "reason": f"impulsive_purchase_{purchase}",
            "item_id": f"luxury_item_{purchase}",
            "balance_after": max(0, 5000 - (purchase * 500))
        })

    # Sistema detecta patrón problemático
    await mock_event_bus.publish("user_behavior_alert", {  # 🔧 Evento personalizado
        "user_id": user_id,
        "alert_type": "excessive_spending",
        "purchases_in_hour": 10,
        "total_spent": 5000
    })

    # Verificar detección de abuso
    spent_events = event_capture.get_events_by_type("besitos_spent")
    assert len(spent_events) == 10

    # Verificar que se detectó el patrón
    assert event_capture.has_event_type("user_behavior_alert")
```

## 🔧 Modificar Configuración de Mocks

### Ejemplo 10: Cambiar Recompensas de Misiones

**Archivo:** `tests/integration/test_user_flows.py`
**Función:** `mock_mission_manager` (línea ~142)

```python
# ANTES (recompensa normal)
reward_mock = type('Reward', (), {'besitos': 30, 'items': []})()

# DESPUÉS (recompensas variables según dificultad)
@pytest.fixture
def mock_mission_manager_advanced():
    """Mock con diferentes tipos de misiones"""
    manager = AsyncMock(spec=MissionManager)

    # Misiones de diferentes dificultades
    manager.get_user_missions.return_value = [
        {
            "mission_id": "easy_daily",
            "difficulty": "easy",
            "reward_besitos": 10    # 🔧 Recompensa baja
        },
        {
            "mission_id": "medium_weekly",
            "difficulty": "medium",
            "reward_besitos": 50    # 🔧 Recompensa media
        },
        {
            "mission_id": "hard_emotional",
            "difficulty": "hard",
            "reward_besitos": 200   # 🔧 Recompensa alta
        }
    ]

    # Diferentes recompensas según misión
    def complete_mission_side_effect(user_id, mission_id):
        if "easy" in mission_id:
            return type('Reward', (), {'besitos': 10, 'items': []})()
        elif "medium" in mission_id:
            return type('Reward', (), {'besitos': 50, 'items': ['boost_item']})()
        elif "hard" in mission_id:
            return type('Reward', (), {'besitos': 200, 'items': ['rare_item', 'emotional_boost']})()

    manager.complete_mission.side_effect = complete_mission_side_effect
    return manager
```

## 🚀 Ejecutar Tests Modificados

### Comandos Específicos

```bash
# Test individual con output detallado
pytest tests/integration/test_user_flows.py::TestEmotionalProgressionFlow::test_diana_level_progression_to_vip_access -v -s

# Ver todos los eventos capturados
pytest tests/integration/test_user_flows.py::TestOnboardingFlow -v -s --capture=no

# Ejecutar con prints de debug
pytest tests/integration/test_user_flows.py -v -s --tb=short

# Generar reporte HTML con resultados
pytest tests/integration/test_user_flows.py --html=mi_test_report.html --self-contained-html
```

### Debug Avanzado

```python
# Agregar al final de cualquier test para debug
def debug_test_results(event_capture):
    print("\\n" + "="*50)
    print("🔍 DEBUG: EVENTOS CAPTURADOS")
    print("="*50)

    for i, event_type in enumerate(event_capture.event_types):
        event_data = event_capture.events[i]
        print(f"\\n{i+1}. 📡 {event_type}")
        print(f"   📊 Data: {event_data}")

    print(f"\\n📈 Total eventos: {len(event_capture.events)}")
    print("="*50)

# Usar en cualquier test:
debug_test_results(event_capture)
```

¡Con estos ejemplos puedes modificar cualquier aspecto de los tests para probar diferentes escenarios del sistema YABOT!