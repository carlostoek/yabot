# Tests de Flujos de Usuario - Integración de Módulos

Este directorio contiene tests end-to-end que validan la integración entre los módulos principales del sistema YABOT: **administración**, **gamificación**, **narrativa** y **emocional**.

## Archivos de Test

### 1. `test_user_flows.py`
**Propósito**: Valida los flujos completos de usuario que integran todos los módulos.

**Flujos Principales Testeados**:

#### **Flujo de Onboarding** (`TestOnboardingFlow`)
- ✅ Registro de usuario nuevo (`/start`)
- ✅ Inicialización de wallet de besitos
- ✅ Configuración de suscripción VIP
- ✅ Eventos: `user_registered`, `besitos_awarded`, `subscription_updated`, `vip_access_granted`

#### **Flujo de Experiencia Diaria** (`TestDailyExperienceFlow`)
- ✅ Reclamación de gift diario
- ✅ Completación de misiones
- ✅ Interacciones narrativas con análisis emocional
- ✅ Eventos: `daily_gift_claimed`, `mission_completed`, `emotional_signature_updated`

#### **Flujo de Progresión Emocional** (`TestEmotionalProgressionFlow`)
- ✅ Progresión a través de niveles de Diana (1→5)
- ✅ Desbloqueo automático de acceso VIP en nivel 4
- ✅ Acceso a contenido Diván (requiere VIP)
- ✅ Hitos emocionales y recompensas
- ✅ Eventos: `diana_level_progression`, `vip_access_granted`, `emotional_milestone_reached`

#### **Flujo de Economía Gamificada** (`TestGamifiedEconomyFlow`)
- ✅ Ganancia de besitos por actividades
- ✅ Gasto en tienda/contenido premium
- ✅ Desbloqueo de contenido narrativo por compras
- ✅ Eventos: `besitos_awarded`, `besitos_spent`, `narrative_hint_unlocked`

#### **Journey Completo** (`TestCrossModuleWorkflow`)
- ✅ Simulación integral desde registro hasta círculo íntimo
- ✅ 14 días de actividad sostenida
- ✅ Progresión emocional completa (nivel 1→5)
- ✅ Validación de todos los eventos en secuencia

### 2. `test_handler_module_integration.py`
**Propósito**: Valida la integración entre handlers de Telegram y módulos del sistema.

**Componentes Testeados**:

#### **Comandos de Telegram** (`TestStartCommandIntegration`, `TestMenuCommandIntegration`)
- ✅ `/start` - Registro y inicialización
- ✅ `/menu` - Navegación y eventos
- ✅ `/help` - Información y tracking
- ✅ Comandos desconocidos

#### **Manejo de Errores** (`TestErrorHandlingIntegration`)
- ✅ Errores en UserService
- ✅ Errores en EventBus
- ✅ Recuperación graceful

#### **Usuarios Concurrentes** (`TestConcurrentUserInteractions`)
- ✅ Múltiples usuarios simultáneos
- ✅ Aislamiento de eventos por usuario
- ✅ No interferencia entre sesiones

### 3. `test_event_flow_performance.py`
**Propósito**: Valida la performance y resiliencia del sistema bajo carga.

**Aspectos de Performance Testeados**:

#### **Event Bus Performance** (`TestEventBusPerformance`)
- ✅ 1000+ eventos concurrentes (>100 eventos/segundo)
- ✅ Carga sostenida por 10 segundos
- ✅ Manejo de memoria sin fugas

#### **Usuarios Concurrentes** (`TestConcurrentUserFlows`)
- ✅ 50 usuarios completando journeys simultáneamente
- ✅ Orden correcto de eventos por usuario
- ✅ No interferencia entre flujos

#### **Resiliencia del Sistema** (`TestSystemResilience`)
- ✅ Manejo de errores bajo carga (10% failure rate)
- ✅ Recuperación después de estrés
- ✅ Mantenimiento de throughput

## Ejecución de Tests

### Ejecutar Todos los Tests de Flujos
```bash
# Todos los tests de integración de flujos
pytest tests/integration/test_user_flows.py -v

# Tests de integración handlers-módulos
pytest tests/integration/test_handler_module_integration.py -v

# Tests de performance
pytest tests/integration/test_event_flow_performance.py -v
```

### Ejecutar Tests Específicos
```bash
# Solo flujo de onboarding
pytest tests/integration/test_user_flows.py::TestOnboardingFlow -v

# Solo journey completo
pytest tests/integration/test_user_flows.py::TestCrossModuleWorkflow::test_complete_user_journey_integration -v

# Solo tests de performance de event bus
pytest tests/integration/test_event_flow_performance.py::TestEventBusPerformance -v
```

### Ejecutar con Métricas Detalladas
```bash
# Con tiempo de ejecución y coverage
pytest tests/integration/ -v --durations=10 --cov=src

# Solo los tests que tardan menos de 30 segundos
pytest tests/integration/ -v -m "not slow"
```

## Eventos Validados

Los tests validan que se disparen correctamente estos eventos de integración:

### **Eventos de Usuario**
- `user_registered` - Registro inicial
- `user_interaction` - Todas las interacciones
- `user_updated` - Actualizaciones de perfil

### **Eventos de Gamificación**
- `besitos_awarded` - Recompensas otorgadas
- `besitos_spent` - Gastos realizados
- `daily_gift_claimed` - Gifts diarios
- `mission_completed` - Misiones completadas
- `achievement_unlocked` - Logros desbloqueados

### **Eventos de Narrativa**
- `decision_made` - Elecciones narrativas
- `narrative_hint_unlocked` - Contenido desbloqueado
- `reaction_detected` - Reacciones a contenido

### **Eventos de Administración**
- `subscription_updated` - Cambios de suscripción
- `vip_access_granted` - Acceso VIP otorgado
- `notification_sent` - Notificaciones enviadas

### **Eventos Emocionales**
- `emotional_signature_updated` - Análisis emocional
- `diana_level_progression` - Progresión de niveles
- `emotional_milestone_reached` - Hitos alcanzados

## Criterios de Éxito

### **Funcionalidad**
- ✅ Todos los eventos esperados se disparan
- ✅ Los datos de eventos son correctos y completos
- ✅ La secuencia de eventos sigue el orden lógico
- ✅ No hay eventos duplicados o perdidos

### **Performance**
- ✅ >100 eventos por segundo bajo carga
- ✅ <10ms tiempo promedio por evento
- ✅ Soporte para 50+ usuarios concurrentes
- ✅ Recuperación <5 segundos después de estrés

### **Resiliencia**
- ✅ >80% success rate con 10% failure rate
- ✅ No fugas de memoria durante carga prolongada
- ✅ Aislamiento completo entre usuarios
- ✅ Manejo graceful de errores en módulos

## Estructura de Datos de Test

### **Mock User Context**
```python
{
    "user_id": "test_user_123",
    "telegram_id": 123456789,
    "vip_status": False,
    "diana_level": 1,
    "emotional_archetype": "Explorer"
}
```

### **Event Data Example**
```python
{
    "user_id": "test_user_123",
    "event_type": "diana_level_progression",
    "new_level": 4,
    "vip_access_required": True,
    "emotional_metrics": {
        "authenticity_score": 0.82,
        "vulnerability_depth": 0.75
    }
}
```

## Debugging y Troubleshooting

### **Ver Eventos Capturados**
```python
# En un test, usar event_capture fixture
def test_example(event_capture):
    # ... ejecutar acciones ...

    # Ver todos los eventos
    print("Eventos capturados:", event_capture.events)

    # Ver eventos por tipo
    user_events = event_capture.get_events_by_type("user_interaction")
    print("Interacciones:", user_events)
```

### **Métricas de Performance**
```python
# En test de performance
print(f"Eventos procesados: {performance_metrics.events_processed}")
print(f"Eventos/segundo: {performance_metrics.events_per_second:.2f}")
print(f"Tiempo promedio: {performance_metrics.average_processing_time:.4f}s")
print(f"Errores: {len(performance_metrics.errors)}")
```

### **Logs de Debug**
```bash
# Ejecutar tests con logs detallados
pytest tests/integration/ -v -s --log-cli-level=DEBUG
```

## Notas Importantes

1. **Aislamiento**: Cada test usa mocks independientes para evitar interferencias
2. **Datos de Test**: Se usan IDs consistentes (`test_user_123`) para facilitar debugging
3. **Timeouts**: Tests de performance tienen timeouts apropiados para CI/CD
4. **Cleanup**: Los mocks se limpian automáticamente entre tests
5. **Determinismo**: Los tests son deterministas y repetibles

Estos tests garantizan que el sistema completo funciona correctamente cuando los módulos trabajan juntos, validando tanto la funcionalidad como la performance bajo condiciones reales de uso.