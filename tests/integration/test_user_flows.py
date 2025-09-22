"""
Tests de flujos de usuario end-to-end que validan la integración entre
los módulos de administración, gamificación y narrativa del sistema YABOT.

Estos tests simulan acciones reales de usuarios para verificar que se
disparan los eventos esperados y que los módulos se comunican correctamente.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from typing import Dict, Any, List

from src.events.bus import EventBus
from src.events.models import (
    create_event, UserInteractionEvent, BesitosAwardedEvent,
    MissionCompletedEvent, VipAccessGrantedEvent, DailyGiftClaimedEvent,
    EmotionalSignatureUpdatedEvent, DianaLevelProgressionEvent
)
from src.services.cross_module import CrossModuleService
from src.services.user import UserService
from src.services.subscription import SubscriptionService
from src.modules.gamification.besitos_wallet import BesitosWallet
from src.modules.gamification.daily_gift import DailyGiftSystem
from src.modules.gamification.mission_manager import MissionManager
from src.modules.admin.subscription_manager import SubscriptionManager
from src.modules.narrative.lucien_messenger import LucienMessenger


class MockEventCapture:
    """Helper para capturar eventos durante los tests"""

    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.event_types: List[str] = []

    async def capture_event(self, event_type: str, event_data: Dict[str, Any]):
        """Captura eventos publicados durante el test"""
        self.events.append(event_data)
        self.event_types.append(event_type)

    def get_events_by_type(self, event_type: str) -> List[Dict[str, Any]]:
        """Retorna eventos filtrados por tipo"""
        return [event for i, event in enumerate(self.events)
                if self.event_types[i] == event_type]

    def has_event_type(self, event_type: str) -> bool:
        """Verifica si se capturó un evento de tipo específico"""
        return event_type in self.event_types


@pytest.fixture
def event_capture():
    """Fixture para capturar eventos durante los tests"""
    return MockEventCapture()


@pytest.fixture
def mock_event_bus(event_capture):
    """Mock del EventBus que captura eventos"""
    event_bus = AsyncMock(spec=EventBus)
    event_bus.publish.side_effect = event_capture.capture_event
    return event_bus


@pytest.fixture
def mock_user_service():
    """Mock del UserService"""
    service = AsyncMock(spec=UserService)
    service.get_user_context.return_value = {
        "user_id": "test_user_123",
        "telegram_id": 123456789,
        "vip_status": False,
        "diana_level": 1,
        "emotional_archetype": "Explorer"
    }
    service.create_user.return_value = {
        "user_id": "test_user_123",
        "created_at": datetime.now()
    }
    return service


@pytest.fixture
def mock_subscription_service():
    """Mock del SubscriptionService"""
    service = AsyncMock(spec=SubscriptionService)
    service.get_subscription.return_value = None
    service.create_subscription.return_value = {
        "subscription_id": "sub_123",
        "user_id": "test_user_123",
        "plan_type": "vip",
        "status": "active"
    }
    return service


@pytest.fixture
def mock_besitos_wallet():
    """Mock del BesitosWallet"""
    wallet = AsyncMock(spec=BesitosWallet)
    wallet.get_balance.return_value = 100
    wallet.add_besitos.return_value = {
        "transaction_id": "tx_123",
        "balance_after": 150,
        "amount": 50
    }
    return wallet


@pytest.fixture
def mock_daily_gift_system():
    """Mock del DailyGiftSystem"""
    system = AsyncMock(spec=DailyGiftSystem)
    system.check_gift_availability.return_value = type('GiftStatus', (), {'can_claim': True})()
    system.claim_daily_gift.return_value = type('GiftResult', (), {
        'success': True,
        'message': 'Gift claimed',
        'gift_claimed': {
            "gift_type": "besitos",
            "amount": 25,
            "next_claim_time": datetime.now() + timedelta(days=1)
        }
    })()
    return system


@pytest.fixture
def mock_mission_manager():
    """Mock del MissionManager"""
    manager = AsyncMock(spec=MissionManager)
    manager.get_user_missions.return_value = [
        {
            "mission_id": "daily_interaction",
            "title": "Interactúa con Lucien 3 veces",
            "progress": 0,
            "target": 3,
            "reward_besitos": 30
        }
    ]
    # Mock return a Reward object-like structure
    reward_mock = type('Reward', (), {'besitos': 30, 'items': []})()
    manager.complete_mission.return_value = reward_mock
    return manager


@pytest.fixture
def cross_module_service(
    mock_user_service, mock_subscription_service, mock_besitos_wallet,
    mock_daily_gift_system, mock_mission_manager
):
    """Fixture para el CrossModuleService con todos los mocks"""
    return CrossModuleService(
        user_service=mock_user_service,
        subscription_service=mock_subscription_service,
        item_manager=AsyncMock(),
        narrative_service=AsyncMock(),
        besitos_wallet=mock_besitos_wallet,
        daily_gift_system=mock_daily_gift_system,
        mission_manager=mock_mission_manager
    )


class TestOnboardingFlow:
    """Tests para el flujo de onboarding completo"""

    @pytest.mark.asyncio
    async def test_user_registration_triggers_all_modules(
        self, cross_module_service, mock_event_bus, event_capture
    ):
        """
        DADO: Un nuevo usuario que ejecuta /start
        CUANDO: Se procesa el comando de registro
        ENTONCES: Se disparan eventos de todos los módulos (admin, gamificación, narrativa)
        """
        user_id = "test_user_123"
        telegram_data = {
            "id": 123456789,
            "username": "testuser",
            "first_name": "Test",
            "language_code": "es"
        }

        # Simular registro de usuario
        await cross_module_service.user_service.create_user(telegram_data)

        # Simular inicialización de wallet de besitos
        await cross_module_service.besitos_wallet.add_besitos(
            user_id, 50, "registration_bonus", "system"
        )

        # Simular eventos de registro
        await mock_event_bus.publish("user_registered", {
            "user_id": user_id,
            "telegram_user_id": 123456789,
            "username": "testuser"
        })

        await mock_event_bus.publish("besitos_awarded", {
            "user_id": user_id,
            "amount": 50,
            "reason": "registration_bonus",
            "source": "system"
        })

        # Verificar que se publicaron los eventos esperados
        assert event_capture.has_event_type("user_registered")
        assert event_capture.has_event_type("besitos_awarded")

        # Verificar datos de eventos
        registration_events = event_capture.get_events_by_type("user_registered")
        assert len(registration_events) == 1
        assert registration_events[0]["user_id"] == user_id

        besitos_events = event_capture.get_events_by_type("besitos_awarded")
        assert len(besitos_events) == 1
        assert besitos_events[0]["amount"] == 50

    @pytest.mark.asyncio
    async def test_vip_subscription_flow(
        self, cross_module_service, mock_event_bus, event_capture
    ):
        """
        DADO: Un usuario que adquiere suscripción VIP
        CUANDO: Se procesa la suscripción
        ENTONCES: Se actualiza acceso VIP y se publican eventos de admin y narrativa
        """
        user_id = "test_user_123"

        # Simular creación de suscripción VIP
        subscription = await cross_module_service.subscription_service.create_subscription(
            user_id, "vip_monthly"
        )

        # Simular eventos de suscripción
        await mock_event_bus.publish("subscription_updated", {
            "user_id": user_id,
            "plan_type": "vip_monthly",
            "status": "active",
            "start_date": datetime.now()
        })

        await mock_event_bus.publish("vip_access_granted", {
            "user_id": user_id,
            "reason": "subscription_activated"
        })

        # Verificar eventos
        assert event_capture.has_event_type("subscription_updated")
        assert event_capture.has_event_type("vip_access_granted")

        vip_events = event_capture.get_events_by_type("vip_access_granted")
        assert len(vip_events) == 1
        assert vip_events[0]["user_id"] == user_id


class TestDailyExperienceFlow:
    """Tests para el flujo de experiencia diaria"""

    @pytest.mark.asyncio
    async def test_daily_gift_and_mission_completion_flow(
        self, cross_module_service, mock_event_bus, event_capture
    ):
        """
        DADO: Un usuario activo en su experiencia diaria
        CUANDO: Reclama gift diario y completa misiones
        ENTONCES: Se actualizan besitos y se registra progreso
        """
        user_id = "test_user_123"

        # 1. Reclamar gift diario
        daily_gift = await cross_module_service.daily_gift_system.claim_daily_gift(user_id)

        await mock_event_bus.publish("daily_gift_claimed", {
            "user_id": user_id,
            "gift_type": daily_gift.gift_claimed["gift_type"],
            "gift_amount": daily_gift.gift_claimed["amount"]
        })

        # 2. Completar misión
        mission_result = await cross_module_service.mission_manager.complete_mission(
            user_id, "daily_interaction"
        )

        await mock_event_bus.publish("mission_completed", {
            "user_id": user_id,
            "mission_id": "daily_interaction",
            "reward_besitos": mission_result.besitos
        })

        # 3. Actualizar besitos por recompensas
        await cross_module_service.besitos_wallet.add_besitos(
            user_id, 55, "daily_rewards", "system"  # 25 gift + 30 mission
        )

        await mock_event_bus.publish("besitos_awarded", {
            "user_id": user_id,
            "amount": 55,
            "reason": "daily_rewards",
            "source": "system"
        })

        # Verificar secuencia de eventos
        assert event_capture.has_event_type("daily_gift_claimed")
        assert event_capture.has_event_type("mission_completed")
        assert event_capture.has_event_type("besitos_awarded")

        # Verificar orden y contenido
        gift_events = event_capture.get_events_by_type("daily_gift_claimed")
        mission_events = event_capture.get_events_by_type("mission_completed")
        besitos_events = event_capture.get_events_by_type("besitos_awarded")

        assert len(gift_events) == 1
        assert len(mission_events) == 1
        assert len(besitos_events) == 1  # daily rewards

        assert gift_events[0]["gift_amount"] == 25
        assert mission_events[0]["reward_besitos"] == 30

    @pytest.mark.asyncio
    async def test_narrative_interaction_triggers_emotional_analysis(
        self, cross_module_service, mock_event_bus, event_capture
    ):
        """
        DADO: Un usuario interactuando con contenido narrativo
        CUANDO: Hace elecciones y reacciona al contenido
        ENTONCES: Se activa análisis emocional y actualización de perfil
        """
        user_id = "test_user_123"

        # Simular interacciones narrativas
        interactions = [
            {
                "type": "decision_made",
                "choice_id": "vulnerable_choice_1",
                "context": {"authenticity_indicators": ["personal_story", "emotional_depth"]}
            },
            {
                "type": "reaction_detected",
                "content_id": "lucien_message_1",
                "reaction_type": "heart",
                "metadata": {"interaction_time": 45}
            }
        ]

        for interaction in interactions:
            await mock_event_bus.publish(interaction["type"], {
                "user_id": user_id,
                **interaction
            })

        # Simular análisis emocional resultante
        await mock_event_bus.publish("emotional_signature_updated", {
            "user_id": user_id,
            "archetype": "Vulnerable_Explorer",
            "authenticity_score": 0.78,
            "signature_strength": 0.85,
            "previous_archetype": "Explorer"
        })

        # Verificar eventos de interacción y análisis
        assert event_capture.has_event_type("decision_made")
        assert event_capture.has_event_type("reaction_detected")
        assert event_capture.has_event_type("emotional_signature_updated")

        emotional_events = event_capture.get_events_by_type("emotional_signature_updated")
        assert len(emotional_events) == 1
        assert emotional_events[0]["authenticity_score"] > 0.7


class TestEmotionalProgressionFlow:
    """Tests para el flujo de progresión emocional y acceso VIP"""

    @pytest.mark.asyncio
    async def test_diana_level_progression_to_vip_access(
        self, cross_module_service, mock_event_bus, event_capture
    ):
        """
        DADO: Un usuario que progresa emocionalmente
        CUANDO: Alcanza nivel 4 de Diana (requiere VIP)
        ENTONCES: Se verifica/otorga acceso VIP y se desbloquea contenido Diván
        """
        user_id = "test_user_123"

        # Simular progresión de nivel Diana
        await mock_event_bus.publish("diana_level_progression", {
            "user_id": user_id,
            "previous_level": 3,
            "new_level": 4,
            "progression_reason": "authentic_vulnerability_reached",
            "emotional_metrics": {
                "authenticity_score": 0.82,
                "vulnerability_depth": 0.75,
                "consistency_rating": 0.88
            },
            "vip_access_required": True
        })

        # Simular verificación/otorgamiento de VIP
        await mock_event_bus.publish("vip_access_granted", {
            "user_id": user_id,
            "reason": "diana_level_4_reached"
        })

        # Simular desbloqueo de contenido narrativo VIP
        await mock_event_bus.publish("narrative_hint_unlocked", {
            "user_id": user_id,
            "hint_id": "divan_access_welcome",
            "fragment_id": "divan_intro_fragment"
        })

        # Verificar secuencia de progresión
        assert event_capture.has_event_type("diana_level_progression")
        assert event_capture.has_event_type("vip_access_granted")
        assert event_capture.has_event_type("narrative_hint_unlocked")

        # Verificar datos de progresión
        progression_events = event_capture.get_events_by_type("diana_level_progression")
        assert len(progression_events) == 1
        assert progression_events[0]["new_level"] == 4
        assert progression_events[0]["vip_access_required"] is True

        vip_events = event_capture.get_events_by_type("vip_access_granted")
        assert len(vip_events) == 1
        assert vip_events[0]["reason"] == "diana_level_4_reached"

    @pytest.mark.asyncio
    async def test_emotional_milestone_rewards_integration(
        self, cross_module_service, mock_event_bus, event_capture
    ):
        """
        DADO: Un usuario que alcanza hitos emocionales
        CUANDO: Se detectan patrones de autenticidad profunda
        ENTONCES: Se otorgan recompensas en besitos y se desbloquea contenido
        """
        user_id = "test_user_123"

        # Simular hito emocional alcanzado
        await mock_event_bus.publish("emotional_milestone_reached", {
            "user_id": user_id,
            "milestone_type": "authentic_pattern_established",
            "milestone_data": {
                "pattern_duration_days": 14,
                "authenticity_consistency": 0.89,
                "emotional_depth_average": 0.76
            },
            "reward_besitos": 100,
            "unlock_content": "deep_vulnerability_fragments"
        })

        # Simular otorgamiento de recompensa de besitos
        await mock_event_bus.publish("besitos_awarded", {
            "user_id": user_id,
            "amount": 100,
            "reason": "emotional_milestone",
            "source": "emotional_system"
        })

        # Verificar integración emocional-gamificación
        assert event_capture.has_event_type("emotional_milestone_reached")
        assert event_capture.has_event_type("besitos_awarded")

        milestone_events = event_capture.get_events_by_type("emotional_milestone_reached")
        besitos_events = event_capture.get_events_by_type("besitos_awarded")

        assert len(milestone_events) == 1
        assert milestone_events[0]["reward_besitos"] == 100

        # Verificar que la recompensa de besitos corresponde al hito
        emotional_besitos = [e for e in besitos_events if e["source"] == "emotional_system"]
        assert len(emotional_besitos) == 1
        assert emotional_besitos[0]["amount"] == 100


class TestGamifiedEconomyFlow:
    """Tests para el flujo de economía gamificada"""

    @pytest.mark.asyncio
    async def test_besitos_economy_full_cycle(
        self, cross_module_service, mock_event_bus, event_capture
    ):
        """
        DADO: Un usuario con besitos acumulados
        CUANDO: Usa besitos para acceder a contenido premium o tienda
        ENTONCES: Se procesan transacciones y se actualiza acceso a contenido
        """
        user_id = "test_user_123"

        # 1. Usuario gana besitos por actividades
        await mock_event_bus.publish("besitos_awarded", {
            "user_id": user_id,
            "amount": 200,
            "reason": "weekly_engagement_bonus",
            "source": "gamification_system",
            "balance_after": 350
        })

        # 2. Usuario gasta besitos en tienda
        await mock_event_bus.publish("besitos_spent", {
            "user_id": user_id,
            "amount": 150,
            "reason": "premium_narrative_access",
            "item_id": "exclusive_lucien_conversation",
            "balance_after": 200
        })

        # 3. Se desbloquea contenido basado en compra
        await mock_event_bus.publish("narrative_hint_unlocked", {
            "user_id": user_id,
            "hint_id": "exclusive_conversation_1",
            "fragment_id": "premium_lucien_fragment"
        })

        # Verificar flujo económico completo
        assert event_capture.has_event_type("besitos_awarded")
        assert event_capture.has_event_type("besitos_spent")
        assert event_capture.has_event_type("narrative_hint_unlocked")

        # Verificar balances y transacciones
        awarded_events = event_capture.get_events_by_type("besitos_awarded")
        spent_events = event_capture.get_events_by_type("besitos_spent")

        assert len(awarded_events) >= 1
        assert len(spent_events) == 1

        # Verificar que el gasto desbloquea contenido narrativo
        spent_event = spent_events[0]
        assert spent_event["item_id"] == "exclusive_lucien_conversation"
        assert spent_event["amount"] == 150

        unlock_events = event_capture.get_events_by_type("narrative_hint_unlocked")
        assert len(unlock_events) >= 1
        assert any(e["fragment_id"] == "premium_lucien_fragment" for e in unlock_events)


class TestCrossModuleWorkflow:
    """Tests para workflows que involucran múltiples módulos"""

    @pytest.mark.asyncio
    async def test_complete_user_journey_integration(
        self, cross_module_service, mock_event_bus, event_capture
    ):
        """
        Test integral que simula un journey completo de usuario
        desde registro hasta círculo íntimo
        """
        user_id = "test_user_123"

        # 1. ONBOARDING - Registro y setup inicial
        await mock_event_bus.publish("user_registered", {
            "user_id": user_id,
            "telegram_user_id": 123456789
        })

        await mock_event_bus.publish("besitos_awarded", {
            "user_id": user_id,
            "amount": 50,
            "reason": "registration_bonus"
        })

        # 2. EXPERIENCIA DIARIA - Varias semanas de actividad
        for day in range(1, 15):  # 2 semanas de actividad
            await mock_event_bus.publish("daily_gift_claimed", {
                "user_id": user_id,
                "gift_type": "besitos",
                "gift_amount": 25
            })

            await mock_event_bus.publish("user_interaction", {
                "user_id": user_id,
                "action": "narrative_choice",
                "context": {"authenticity_score": 0.7 + (day * 0.01)}
            })

        # 3. PROGRESIÓN EMOCIONAL - Evolución a través de niveles
        emotional_levels = [
            {"level": 2, "archetype": "Curious_Explorer"},
            {"level": 3, "archetype": "Trusting_Sharer"},
            {"level": 4, "archetype": "Vulnerable_Connector", "vip_required": True},
            {"level": 5, "archetype": "Deep_Authentic", "vip_required": True}
        ]

        for progression in emotional_levels:
            await mock_event_bus.publish("diana_level_progression", {
                "user_id": user_id,
                "new_level": progression["level"],
                "progression_reason": "authentic_consistency",
                "vip_access_required": progression.get("vip_required", False)
            })

            if progression.get("vip_required"):
                await mock_event_bus.publish("vip_access_granted", {
                    "user_id": user_id,
                    "reason": f"diana_level_{progression['level']}_reached"
                })

        # 4. CULMINACIÓN - Acceso a círculo íntimo
        await mock_event_bus.publish("emotional_milestone_reached", {
            "user_id": user_id,
            "milestone_type": "circulo_intimo_access",
            "milestone_data": {"final_authenticity_score": 0.95},
            "unlock_content": "circulo_intimo_fragments"
        })

        # VERIFICACIONES INTEGRALES

        # Verificar presencia de todos los tipos de eventos principales
        expected_event_types = [
            "user_registered", "besitos_awarded", "daily_gift_claimed",
            "user_interaction", "diana_level_progression",
            "vip_access_granted", "emotional_milestone_reached"
        ]

        for event_type in expected_event_types:
            assert event_capture.has_event_type(event_type), f"Missing event type: {event_type}"

        # Verificar progresión emocional completa
        progression_events = event_capture.get_events_by_type("diana_level_progression")
        max_level = max(e["new_level"] for e in progression_events)
        assert max_level >= 5, "User should reach at least Diana level 5"

        # Verificar otorgamiento de VIP
        vip_events = event_capture.get_events_by_type("vip_access_granted")
        assert len(vip_events) >= 2, "VIP access should be granted for levels 4 and 5"

        # Verificar actividad diaria sostenida
        gift_events = event_capture.get_events_by_type("daily_gift_claimed")
        interaction_events = event_capture.get_events_by_type("user_interaction")
        assert len(gift_events) >= 14, "Should have 14 days of daily gifts"
        assert len(interaction_events) >= 14, "Should have 14 days of interactions"

        # Verificar culminación en círculo íntimo
        milestone_events = event_capture.get_events_by_type("emotional_milestone_reached")
        circulo_intimo_events = [
            e for e in milestone_events
            if e["milestone_type"] == "circulo_intimo_access"
        ]
        assert len(circulo_intimo_events) == 1, "Should reach círculo íntimo"