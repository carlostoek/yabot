"""
Tests de integración entre handlers de Telegram y módulos del sistema.

Estos tests validan que los comandos de Telegram se procesen correctamente
y disparen los eventos apropiados en los módulos correspondientes.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from typing import Dict, Any

from src.handlers.telegram_commands import CommandHandler
from src.events.bus import EventBus
from src.services.user import UserService
from src.core.models import CommandResponse


class MockTelegramMessage:
    """Mock de mensaje de Telegram para tests"""

    def __init__(self, user_id: int = 123456789, username: str = "testuser",
                 text: str = "/start", message_id: int = 1):
        self.from_user = MagicMock()
        self.from_user.id = user_id
        self.from_user.username = username
        self.from_user.first_name = "Test"
        self.from_user.last_name = "User"
        self.from_user.language_code = "es"
        self.text = text
        self.message_id = message_id


class MockEventCapture:
    """Helper para capturar eventos durante los tests"""

    def __init__(self):
        self.captured_events = []

    async def capture_event(self, event_type: str, event_data: Dict[str, Any]):
        self.captured_events.append({
            "type": event_type,
            "data": event_data,
            "timestamp": datetime.utcnow()
        })

    def get_events_by_type(self, event_type: str):
        return [e for e in self.captured_events if e["type"] == event_type]

    def has_event_type(self, event_type: str) -> bool:
        return any(e["type"] == event_type for e in self.captured_events)


@pytest.fixture
def event_capture():
    return MockEventCapture()


@pytest.fixture
def mock_event_bus(event_capture):
    event_bus = AsyncMock(spec=EventBus)
    event_bus.publish.side_effect = event_capture.capture_event
    return event_bus


@pytest.fixture
def mock_user_service():
    service = AsyncMock(spec=UserService)
    service.get_user_context.return_value = {
        "user_id": "123456789",
        "telegram_id": 123456789,
        "vip_status": False,
        "diana_level": 1
    }
    service.create_user.return_value = {
        "user_id": "123456789",
        "created_at": datetime.utcnow()
    }
    return service


@pytest.fixture
def command_handler(mock_user_service, mock_event_bus):
    return CommandHandler(
        user_service=mock_user_service,
        event_bus=mock_event_bus
    )


class TestStartCommandIntegration:
    """Tests para el comando /start y su integración con módulos"""

    @pytest.mark.asyncio
    async def test_start_command_triggers_user_registration_events(
        self, command_handler, event_capture, mock_user_service
    ):
        """
        DADO: Un nuevo usuario que ejecuta /start
        CUANDO: Se procesa el comando
        ENTONCES: Se disparan eventos de registro y se inicializa el usuario en todos los módulos
        """
        # Configurar que el usuario no existe
        mock_user_service.get_user_context.side_effect = Exception("User not found")

        message = MockTelegramMessage()

        # Ejecutar comando /start
        response = await command_handler.handle_start(message)

        # Verificar que se intentó crear el usuario
        mock_user_service.create_user.assert_called_once()

        # Verificar que se publicó evento de interacción
        assert event_capture.has_event_type("user_interaction")

        # Verificar contenido del evento
        interaction_events = event_capture.get_events_by_type("user_interaction")
        assert len(interaction_events) == 1
        assert interaction_events[0]["data"]["action"] == "start"
        assert interaction_events[0]["data"]["user_id"] == "123456789"

        # Verificar respuesta del comando
        assert isinstance(response, CommandResponse)
        assert "Welcome" in response.text or "Bienvenido" in response.text.lower()

    @pytest.mark.asyncio
    async def test_start_command_for_existing_user(
        self, command_handler, event_capture, mock_user_service
    ):
        """
        DADO: Un usuario existente que ejecuta /start
        CUANDO: Se procesa el comando
        ENTONCES: Se actualiza información del usuario sin crear uno nuevo
        """
        # Usuario ya existe
        mock_user_service.get_user_context.return_value = {
            "user_id": "123456789",
            "telegram_id": 123456789,
            "created_at": datetime.utcnow()
        }

        message = MockTelegramMessage()

        # Ejecutar comando /start
        response = await command_handler.handle_start(message)

        # Verificar que NO se intentó crear un nuevo usuario
        mock_user_service.create_user.assert_not_called()

        # Verificar que se actualizó el perfil
        mock_user_service.update_user_profile.assert_called_once()

        # Verificar evento de interacción
        assert event_capture.has_event_type("user_interaction")

        # Verificar respuesta
        assert isinstance(response, CommandResponse)


class TestMenuCommandIntegration:
    """Tests para el comando /menu y navegación"""

    @pytest.mark.asyncio
    async def test_menu_command_triggers_navigation_events(
        self, command_handler, event_capture
    ):
        """
        DADO: Un usuario que ejecuta /menu
        CUANDO: Se procesa el comando
        ENTONCES: Se publican eventos de navegación y se muestra el menú apropiado
        """
        message = MockTelegramMessage(text="/menu")

        # Ejecutar comando /menu
        response = await command_handler.handle_menu(message)

        # Verificar evento de interacción
        assert event_capture.has_event_type("user_interaction")

        menu_events = event_capture.get_events_by_type("user_interaction")
        assert len(menu_events) == 1
        assert menu_events[0]["data"]["action"] == "menu"

        # Verificar respuesta contiene opciones de menú
        assert isinstance(response, CommandResponse)
        assert "Menu" in response.text or "Menú" in response.text


class TestUserInteractionEventFlow:
    """Tests para validar el flujo completo de eventos de interacción"""

    @pytest.mark.asyncio
    async def test_command_sequence_generates_consistent_events(
        self, command_handler, event_capture
    ):
        """
        DADO: Un usuario que ejecuta una secuencia de comandos
        CUANDO: Se procesan los comandos en orden
        ENTONCES: Se generan eventos consistentes para cada interacción
        """
        user_id = 123456789
        commands = [
            ("/start", "start"),
            ("/menu", "menu"),
            ("/help", "help")
        ]

        for command_text, expected_action in commands:
            message = MockTelegramMessage(
                user_id=user_id,
                text=command_text
            )

            if command_text == "/start":
                await command_handler.handle_start(message)
            elif command_text == "/menu":
                await command_handler.handle_menu(message)
            elif command_text == "/help":
                await command_handler.handle_help(message)

        # Verificar que se generaron todos los eventos
        interaction_events = event_capture.get_events_by_type("user_interaction")
        assert len(interaction_events) == 3

        # Verificar orden y contenido de eventos
        expected_actions = ["start", "menu", "help"]
        actual_actions = [e["data"]["action"] for e in interaction_events]
        assert actual_actions == expected_actions

        # Verificar que todos los eventos tienen el mismo user_id
        user_ids = [e["data"]["user_id"] for e in interaction_events]
        assert all(uid == str(user_id) for uid in user_ids)

    @pytest.mark.asyncio
    async def test_unknown_command_handling(
        self, command_handler, event_capture
    ):
        """
        DADO: Un usuario que envía un comando no reconocido
        CUANDO: Se procesa el comando
        ENTONCES: Se maneja apropiadamente y se publica evento de comando desconocido
        """
        message = MockTelegramMessage(text="/unknown_command")

        # Ejecutar comando desconocido
        response = await command_handler.handle_unknown(message)

        # Verificar evento de interacción
        assert event_capture.has_event_type("user_interaction")

        unknown_events = event_capture.get_events_by_type("user_interaction")
        assert len(unknown_events) == 1
        assert unknown_events[0]["data"]["action"] == "unknown"

        # Verificar respuesta de ayuda
        assert isinstance(response, CommandResponse)
        assert "Unknown" in response.text or "desconocido" in response.text.lower()


class TestErrorHandlingIntegration:
    """Tests para manejo de errores en la integración"""

    @pytest.mark.asyncio
    async def test_user_service_error_handling(
        self, mock_event_bus, event_capture
    ):
        """
        DADO: Un error en el UserService
        CUANDO: Se intenta procesar un comando
        ENTONCES: Se maneja el error apropiadamente sin afectar el evento bus
        """
        # Configurar UserService que falla
        failing_user_service = AsyncMock(spec=UserService)
        failing_user_service.get_user_context.side_effect = Exception("Database error")
        failing_user_service.create_user.side_effect = Exception("Database error")

        command_handler = CommandHandler(
            user_service=failing_user_service,
            event_bus=mock_event_bus
        )

        message = MockTelegramMessage()

        # Ejecutar comando que debería fallar en user service
        response = await command_handler.handle_start(message)

        # Verificar que aún se publica evento de interacción
        assert event_capture.has_event_type("user_interaction")

        # Verificar que se maneja graciosamente
        assert isinstance(response, CommandResponse)

    @pytest.mark.asyncio
    async def test_event_bus_error_handling(
        self, mock_user_service
    ):
        """
        DADO: Un error en el EventBus
        CUANDO: Se intenta publicar un evento
        ENTONCES: El comando se procesa normalmente sin fallar
        """
        # Configurar EventBus que falla
        failing_event_bus = AsyncMock(spec=EventBus)
        failing_event_bus.publish.side_effect = Exception("Event bus error")

        command_handler = CommandHandler(
            user_service=mock_user_service,
            event_bus=failing_event_bus
        )

        message = MockTelegramMessage()

        # Ejecutar comando
        response = await command_handler.handle_start(message)

        # Verificar que el comando se procesa a pesar del error en event bus
        assert isinstance(response, CommandResponse)
        mock_user_service.get_user_context.assert_called_once()


class TestConcurrentUserInteractions:
    """Tests para interacciones concurrentes de múltiples usuarios"""

    @pytest.mark.asyncio
    async def test_multiple_users_concurrent_commands(
        self, mock_user_service, mock_event_bus, event_capture
    ):
        """
        DADO: Múltiples usuarios ejecutando comandos concurrentemente
        CUANDO: Se procesan los comandos en paralelo
        ENTONCES: Cada usuario genera eventos independientes sin interferencia
        """
        import asyncio

        command_handler = CommandHandler(
            user_service=mock_user_service,
            event_bus=mock_event_bus
        )

        # Configurar múltiples usuarios
        users = [
            (111111111, "user1"),
            (222222222, "user2"),
            (333333333, "user3")
        ]

        # Configurar mock para retornar contextos diferentes por usuario
        def get_user_context_side_effect(user_id):
            return {
                "user_id": user_id,
                "telegram_id": int(user_id),
                "username": f"user_{user_id}"
            }

        mock_user_service.get_user_context.side_effect = get_user_context_side_effect

        # Crear tareas concurrentes
        tasks = []
        for user_id, username in users:
            message = MockTelegramMessage(user_id=user_id, username=username)
            task = command_handler.handle_start(message)
            tasks.append(task)

        # Ejecutar concurrentemente
        responses = await asyncio.gather(*tasks)

        # Verificar que se generaron eventos para todos los usuarios
        interaction_events = event_capture.get_events_by_type("user_interaction")
        assert len(interaction_events) == 3

        # Verificar que cada usuario tiene su evento
        user_ids_in_events = {e["data"]["user_id"] for e in interaction_events}
        expected_user_ids = {str(user_id) for user_id, _ in users}
        assert user_ids_in_events == expected_user_ids

        # Verificar que todas las respuestas son válidas
        assert all(isinstance(r, CommandResponse) for r in responses)