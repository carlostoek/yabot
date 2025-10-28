"""
Tests de performance para flujos de eventos entre módulos.

Estos tests validan que el sistema puede manejar cargas altas de eventos
y que los flujos de integración se mantienen estables bajo presión.
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor

from src.events.bus import EventBus
from src.events.models import create_event


class PerformanceMetrics:
    """Recolector de métricas de performance"""

    def __init__(self):
        self.events_processed = 0
        self.start_time = None
        self.end_time = None
        self.errors = []
        self.processing_times = []

    def start_measurement(self):
        self.start_time = time.time()

    def end_measurement(self):
        self.end_time = time.time()

    def record_event_processed(self, processing_time: float = 0):
        self.events_processed += 1
        if processing_time > 0:
            self.processing_times.append(processing_time)

    def record_error(self, error: str):
        self.errors.append(error)

    @property
    def total_time(self) -> float:
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0

    @property
    def events_per_second(self) -> float:
        if self.total_time > 0:
            return self.events_processed / self.total_time
        return 0

    @property
    def average_processing_time(self) -> float:
        if self.processing_times:
            return sum(self.processing_times) / len(self.processing_times)
        return 0


class MockEventBusWithMetrics:
    """Mock del EventBus que recolecta métricas de performance"""

    def __init__(self, metrics: PerformanceMetrics):
        self.metrics = metrics
        self.published_events = []
        self.processing_delay = 0.001  # 1ms delay por defecto

    async def publish(self, event_type: str, event_data: Dict[str, Any]):
        start_time = time.time()

        # Simular tiempo de procesamiento
        await asyncio.sleep(self.processing_delay)

        # Registrar evento
        self.published_events.append({
            "type": event_type,
            "data": event_data,
            "timestamp": datetime.utcnow()
        })

        processing_time = time.time() - start_time
        self.metrics.record_event_processed(processing_time)


@pytest.fixture
def performance_metrics():
    return PerformanceMetrics()


@pytest.fixture
def mock_event_bus_with_metrics(performance_metrics):
    return MockEventBusWithMetrics(performance_metrics)


class TestEventBusPerformance:
    """Tests de performance del event bus"""

    @pytest.mark.asyncio
    async def test_high_volume_event_publishing(
        self, mock_event_bus_with_metrics, performance_metrics
    ):
        """
        DADO: Un sistema bajo carga alta de eventos
        CUANDO: Se publican 1000 eventos concurrentemente
        ENTONCES: El sistema mantiene performance aceptable (>100 eventos/segundo)
        """
        event_bus = mock_event_bus_with_metrics
        num_events = 1000

        # Crear eventos de diferentes tipos
        event_types = [
            "user_interaction", "besitos_awarded", "mission_completed",
            "narrative_hint_unlocked", "emotional_signature_updated"
        ]

        performance_metrics.start_measurement()

        # Crear tareas para publicar eventos concurrentemente
        tasks = []
        for i in range(num_events):
            event_type = event_types[i % len(event_types)]
            event_data = {
                "user_id": f"user_{i % 100}",  # 100 usuarios diferentes
                "event_id": f"event_{i}",
                "timestamp": datetime.utcnow()
            }

            task = event_bus.publish(event_type, event_data)
            tasks.append(task)

        # Ejecutar todas las tareas
        await asyncio.gather(*tasks)

        performance_metrics.end_measurement()

        # Verificar métricas de performance
        assert performance_metrics.events_processed == num_events
        assert performance_metrics.events_per_second > 100, \
            f"Performance insuficiente: {performance_metrics.events_per_second:.2f} eventos/segundo"
        assert performance_metrics.total_time < 20, \
            f"Tiempo total excesivo: {performance_metrics.total_time:.2f} segundos"
        assert performance_metrics.average_processing_time < 0.01, \
            f"Tiempo promedio por evento excesivo: {performance_metrics.average_processing_time:.4f} segundos"

    @pytest.mark.asyncio
    async def test_sustained_load_over_time(
        self, mock_event_bus_with_metrics, performance_metrics
    ):
        """
        DADO: Un sistema que debe manejar carga sostenida
        CUANDO: Se publican eventos continuamente por 10 segundos
        ENTONCES: El sistema mantiene throughput estable sin degradación
        """
        event_bus = mock_event_bus_with_metrics
        duration_seconds = 10
        target_events_per_second = 50

        performance_metrics.start_measurement()

        start_time = time.time()
        event_count = 0

        while time.time() - start_time < duration_seconds:
            # Publicar eventos a ritmo controlado
            batch_size = 10
            tasks = []

            for i in range(batch_size):
                event_data = {
                    "user_id": f"user_{event_count % 50}",
                    "event_id": f"sustained_event_{event_count}",
                    "timestamp": datetime.utcnow()
                }

                task = event_bus.publish("user_interaction", event_data)
                tasks.append(task)
                event_count += 1

            await asyncio.gather(*tasks)

            # Pequeña pausa para controlar el ritmo
            await asyncio.sleep(batch_size / target_events_per_second)

        performance_metrics.end_measurement()

        # Verificar que se mantuvo el throughput
        actual_events_per_second = performance_metrics.events_per_second
        assert actual_events_per_second >= target_events_per_second * 0.8, \
            f"Throughput insuficiente: {actual_events_per_second:.2f} eventos/segundo"

    @pytest.mark.asyncio
    async def test_memory_usage_under_load(
        self, mock_event_bus_with_metrics, performance_metrics
    ):
        """
        DADO: Un sistema procesando eventos intensivamente
        CUANDO: Se publican muchos eventos con datos grandes
        ENTONCES: El sistema no tiene fugas de memoria significativas
        """
        import gc
        import sys

        event_bus = mock_event_bus_with_metrics

        # Medir memoria inicial
        gc.collect()
        initial_objects = len(gc.get_objects())

        # Publicar eventos con payloads grandes
        num_events = 500
        large_payload = {"data": "x" * 1000}  # 1KB por evento

        performance_metrics.start_measurement()

        for i in range(num_events):
            event_data = {
                "user_id": f"user_{i}",
                "event_id": f"large_event_{i}",
                "payload": large_payload,
                "timestamp": datetime.utcnow()
            }

            await event_bus.publish("user_interaction", event_data)

        performance_metrics.end_measurement()

        # Limpiar y medir memoria final
        gc.collect()
        final_objects = len(gc.get_objects())

        # Verificar que no hay fuga significativa de memoria
        object_growth = final_objects - initial_objects
        max_acceptable_growth = num_events * 2  # Permitir hasta 2 objetos por evento

        assert object_growth < max_acceptable_growth, \
            f"Posible fuga de memoria: {object_growth} objetos adicionales"


class TestConcurrentUserFlows:
    """Tests de performance para flujos de usuarios concurrentes"""

    @pytest.mark.asyncio
    async def test_multiple_users_simultaneous_journeys(
        self, mock_event_bus_with_metrics, performance_metrics
    ):
        """
        DADO: Múltiples usuarios completando journeys simultáneamente
        CUANDO: 50 usuarios ejecutan flujos completos al mismo tiempo
        ENTONCES: El sistema mantiene performance sin interferencias entre usuarios
        """
        event_bus = mock_event_bus_with_metrics
        num_users = 50

        async def simulate_user_journey(user_id: int):
            """Simula el journey completo de un usuario"""
            events_sequence = [
                ("user_registered", {"telegram_user_id": user_id}),
                ("besitos_awarded", {"amount": 50, "reason": "registration"}),
                ("daily_gift_claimed", {"gift_type": "besitos", "amount": 25}),
                ("user_interaction", {"action": "narrative_choice"}),
                ("mission_completed", {"mission_id": "daily_task", "reward_besitos": 30}),
                ("diana_level_progression", {"new_level": 2, "previous_level": 1}),
                ("emotional_signature_updated", {"archetype": "Explorer"}),
            ]

            for event_type, event_data in events_sequence:
                event_data["user_id"] = f"user_{user_id}"
                await event_bus.publish(event_type, event_data)
                # Pequeña pausa entre eventos del mismo usuario
                await asyncio.sleep(0.01)

        performance_metrics.start_measurement()

        # Crear tareas para todos los usuarios
        user_tasks = [
            simulate_user_journey(user_id)
            for user_id in range(num_users)
        ]

        # Ejecutar todos los journeys concurrentemente
        await asyncio.gather(*user_tasks)

        performance_metrics.end_measurement()

        # Verificar métricas
        expected_total_events = num_users * 7  # 7 eventos por usuario
        assert performance_metrics.events_processed == expected_total_events

        # Verificar que se completó en tiempo razonable
        assert performance_metrics.total_time < 10, \
            f"Tiempo total excesivo para {num_users} usuarios: {performance_metrics.total_time:.2f}s"

        # Verificar que se mantuvieron eventos por usuario
        events_by_user = {}
        for event in event_bus.published_events:
            user_id = event["data"].get("user_id")
            if user_id:
                events_by_user.setdefault(user_id, 0)
                events_by_user[user_id] += 1

        # Cada usuario debe tener exactamente 7 eventos
        assert len(events_by_user) == num_users
        assert all(count == 7 for count in events_by_user.values())

    @pytest.mark.asyncio
    async def test_event_ordering_under_load(
        self, mock_event_bus_with_metrics, performance_metrics
    ):
        """
        DADO: Eventos que deben mantener orden lógico
        CUANDO: Se publican eventos secuenciales bajo carga alta
        ENTONCES: El orden se mantiene para cada usuario individual
        """
        event_bus = mock_event_bus_with_metrics
        num_users = 20

        async def simulate_ordered_sequence(user_id: int):
            """Simula secuencia ordenada de eventos para un usuario"""
            sequence = [
                ("user_registered", {"step": 1}),
                ("besitos_awarded", {"step": 2, "amount": 50}),
                ("diana_level_progression", {"step": 3, "new_level": 2}),
                ("vip_access_granted", {"step": 4}),
                ("emotional_milestone_reached", {"step": 5, "milestone_type": "final"})
            ]

            for event_type, event_data in sequence:
                event_data["user_id"] = f"user_{user_id}"
                await event_bus.publish(event_type, event_data)

        performance_metrics.start_measurement()

        # Ejecutar secuencias para todos los usuarios
        tasks = [
            simulate_ordered_sequence(user_id)
            for user_id in range(num_users)
        ]

        await asyncio.gather(*tasks)

        performance_metrics.end_measurement()

        # Verificar orden por usuario
        events_by_user = {}
        for event in event_bus.published_events:
            user_id = event["data"].get("user_id")
            if user_id:
                events_by_user.setdefault(user_id, [])
                events_by_user[user_id].append(event)

        # Verificar orden secuencial para cada usuario
        for user_id, user_events in events_by_user.items():
            steps = [event["data"]["step"] for event in user_events]
            expected_steps = [1, 2, 3, 4, 5]
            assert steps == expected_steps, \
                f"Orden incorrecto para {user_id}: {steps} != {expected_steps}"


class TestSystemResilience:
    """Tests de resiliencia del sistema bajo carga"""

    @pytest.mark.asyncio
    async def test_error_handling_under_load(
        self, performance_metrics
    ):
        """
        DADO: Un sistema bajo carga con errores ocasionales
        CUANDO: Algunos eventos fallan al procesarse
        ENTONCES: El sistema continúa procesando eventos exitosamente
        """
        class UnreliableEventBus(MockEventBusWithMetrics):
            def __init__(self, metrics, failure_rate=0.1):
                super().__init__(metrics)
                self.failure_rate = failure_rate
                self.failures = 0

            async def publish(self, event_type: str, event_data: Dict[str, Any]):
                # Simular falla ocasional
                import random
                if random.random() < self.failure_rate:
                    self.failures += 1
                    self.metrics.record_error(f"Simulated failure for {event_type}")
                    raise Exception(f"Simulated network error for {event_type}")

                await super().publish(event_type, event_data)

        unreliable_bus = UnreliableEventBus(performance_metrics, failure_rate=0.1)
        num_events = 200

        performance_metrics.start_measurement()

        successful_events = 0
        failed_events = 0

        # Intentar publicar eventos con manejo de errores
        for i in range(num_events):
            try:
                await unreliable_bus.publish("test_event", {
                    "event_id": f"resilience_test_{i}",
                    "user_id": f"user_{i % 10}"
                })
                successful_events += 1
            except Exception:
                failed_events += 1

        performance_metrics.end_measurement()

        # Verificar resiliencia
        assert successful_events > 0, "Ningún evento se procesó exitosamente"
        assert failed_events > 0, "No se simularon fallas como esperado"

        success_rate = successful_events / num_events
        assert success_rate > 0.8, \
            f"Tasa de éxito muy baja: {success_rate:.2%}"

        # Verificar que los eventos exitosos se procesaron correctamente
        assert len(unreliable_bus.published_events) == successful_events

    @pytest.mark.asyncio
    async def test_recovery_after_system_stress(
        self, mock_event_bus_with_metrics, performance_metrics
    ):
        """
        DADO: Un sistema que ha estado bajo estrés alto
        CUANDO: La carga se reduce a niveles normales
        ENTONCES: El sistema se recupera y mantiene performance normal
        """
        event_bus = mock_event_bus_with_metrics

        # Fase 1: Estrés alto
        event_bus.processing_delay = 0.005  # 5ms delay por evento

        performance_metrics.start_measurement()

        # Eventos de estrés
        stress_tasks = []
        for i in range(100):
            task = event_bus.publish("stress_event", {
                "event_id": f"stress_{i}",
                "user_id": f"user_{i % 10}"
            })
            stress_tasks.append(task)

        await asyncio.gather(*stress_tasks)

        stress_end_time = time.time()
        stress_events = performance_metrics.events_processed

        # Fase 2: Recuperación a carga normal
        event_bus.processing_delay = 0.001  # Volver a 1ms normal

        # Eventos normales
        normal_tasks = []
        for i in range(100):
            task = event_bus.publish("normal_event", {
                "event_id": f"normal_{i}",
                "user_id": f"user_{i % 10}"
            })
            normal_tasks.append(task)

        await asyncio.gather(*normal_tasks)

        performance_metrics.end_measurement()

        # Verificar recuperación
        total_events = performance_metrics.events_processed
        normal_events = total_events - stress_events

        assert normal_events == 100, "No se procesaron todos los eventos normales"
        assert total_events == 200, "Total de eventos incorrecto"

        # La fase normal debería ser significativamente más rápida
        total_time = performance_metrics.total_time
        stress_time = stress_end_time - performance_metrics.start_time
        normal_time = total_time - stress_time

        if normal_time > 0:
            normal_throughput = normal_events / normal_time
            stress_throughput = stress_events / stress_time

            # El throughput normal debería ser al menos 3x mejor
            assert normal_throughput > stress_throughput * 3, \
                f"Recuperación insuficiente: {normal_throughput:.2f} vs {stress_throughput:.2f}"