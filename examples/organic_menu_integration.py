"""
Ejemplo de Integración del Sistema de Menús Orgánicos - YABOT
Demuestra cómo usar el nuevo sistema en handlers reales.
"""

from typing import Dict, Any, Optional
import asyncio
from datetime import datetime

# Imports del sistema YABOT
from src.ui.menu_factory import MenuFactory, MenuType
from src.handlers.organic_restrictions import handle_organic_callback
from src.services.user import UserService
from src.core.models import CommandResponse


class OrganicMenuIntegrationExample:
    """Ejemplo completo de integración del sistema de menús orgánicos."""

    def __init__(self, user_service: UserService):
        """Inicializar con servicio de usuarios."""
        self.user_service = user_service
        self.menu_factory = MenuFactory()

    async def demonstrate_main_menu(self, user_id: str) -> Dict[str, Any]:
        """Demuestra el menú principal orgánico para diferentes tipos de usuarios."""

        # Ejemplo 1: Usuario gratuito novato
        free_user_context = {
            'user_id': user_id,
            'role': 'free_user',
            'has_vip': False,
            'narrative_level': 1,
            'worthiness_score': 0.1,
            'besitos_balance': 150,
            'user_archetype': 'explorer'
        }

        print("=== USUARIO GRATUITO NOVATO ===")
        free_menu = await self.menu_factory.create_menu(MenuType.MAIN, free_user_context)
        self._display_menu(free_menu, "Usuario Gratuito")

        # Ejemplo 2: Usuario gratuito avanzado
        advanced_free_context = {
            'user_id': user_id,
            'role': 'free_user',
            'has_vip': False,
            'narrative_level': 3,
            'worthiness_score': 0.45,
            'besitos_balance': 500,
            'user_archetype': 'analytical'
        }

        print("\n=== USUARIO GRATUITO AVANZADO ===")
        advanced_menu = await self.menu_factory.create_menu(MenuType.MAIN, advanced_free_context)
        self._display_menu(advanced_menu, "Usuario Gratuito Avanzado")

        # Ejemplo 3: Usuario VIP
        vip_user_context = {
            'user_id': user_id,
            'role': 'vip_user',
            'has_vip': True,
            'narrative_level': 5,
            'worthiness_score': 0.75,
            'besitos_balance': 1200,
            'user_archetype': 'patient'
        }

        print("\n=== USUARIO VIP ===")
        vip_menu = await self.menu_factory.create_menu(MenuType.MAIN, vip_user_context)
        self._display_menu(vip_menu, "Usuario VIP")

        return {
            'free_user_menu': free_menu,
            'advanced_free_menu': advanced_menu,
            'vip_menu': vip_menu
        }

    async def demonstrate_store_interactions(self, user_id: str) -> Dict[str, Any]:
        """Demuestra interacciones con la tienda orgánica."""

        user_context = {
            'user_id': user_id,
            'role': 'free_user',
            'has_vip': False,
            'narrative_level': 2,
            'worthiness_score': 0.3,
            'besitos_balance': 80,  # Insuficiente para algunos ítems
            'user_archetype': 'explorer'
        }

        print("\n=== TIENDA ORGÁNICA ===")
        store_menu = await self.menu_factory.create_organic_store_menu(user_context)
        self._display_menu(store_menu, "Tienda Unificada")

        # Simular clicks en ítems restringidos
        print("\n=== SIMULACIÓN DE INTERACCIONES ===")

        # 1. Click en Fragmentos Íntimos (requiere worthiness)
        worthiness_response = await handle_organic_callback(
            "worthiness_explanation:fragmentos_intimos:0.4",
            user_context,
            self.user_service
        )
        print(f"Click en Fragmentos Íntimos: {worthiness_response.content}")

        # 2. Click en Círculo Íntimo (requiere VIP)
        vip_response = await handle_organic_callback(
            "vip_invitation:circulo_intimo",
            user_context,
            self.user_service
        )
        print(f"Click en Círculo Íntimo: {vip_response.content}")

        # 3. Click en El Diván
        divan_response = await handle_organic_callback(
            "explain_divan_worthiness",
            user_context,
            self.user_service
        )
        print(f"Click en El Diván: {divan_response.content}")

        return {
            'store_menu': store_menu,
            'interactions': {
                'worthiness_explanation': worthiness_response,
                'vip_invitation': vip_response,
                'divan_explanation': divan_response
            }
        }

    async def demonstrate_progression_journey(self, user_id: str) -> Dict[str, Any]:
        """Demuestra cómo cambia la experiencia conforme el usuario progresa."""

        progression_stages = [
            {
                'name': 'Beginner',
                'context': {
                    'user_id': user_id,
                    'role': 'free_user',
                    'has_vip': False,
                    'narrative_level': 1,
                    'worthiness_score': 0.1,
                    'besitos_balance': 100,
                    'user_archetype': 'explorer'
                }
            },
            {
                'name': 'Developing',
                'context': {
                    'user_id': user_id,
                    'role': 'free_user',
                    'has_vip': False,
                    'narrative_level': 2,
                    'worthiness_score': 0.35,
                    'besitos_balance': 300,
                    'user_archetype': 'explorer'
                }
            },
            {
                'name': 'Advanced Free',
                'context': {
                    'user_id': user_id,
                    'role': 'free_user',
                    'has_vip': False,
                    'narrative_level': 3,
                    'worthiness_score': 0.55,
                    'besitos_balance': 600,
                    'user_archetype': 'analytical'
                }
            },
            {
                'name': 'New VIP',
                'context': {
                    'user_id': user_id,
                    'role': 'vip_user',
                    'has_vip': True,
                    'narrative_level': 4,
                    'worthiness_score': 0.65,
                    'besitos_balance': 800,
                    'user_archetype': 'patient'
                }
            },
            {
                'name': 'Elite VIP',
                'context': {
                    'user_id': user_id,
                    'role': 'vip_user',
                    'has_vip': True,
                    'narrative_level': 6,
                    'worthiness_score': 0.85,
                    'besitos_balance': 1500,
                    'user_archetype': 'persistent'
                }
            }
        ]

        journey_results = {}

        for stage in progression_stages:
            print(f"\n=== STAGE: {stage['name'].upper()} ===")

            menu = await self.menu_factory.create_menu(MenuType.MAIN, stage['context'])

            # Mostrar header de Lucien para este stage
            print(f"Lucien's Welcome: {menu.header_text}")
            print(f"Lucien's Footer: {menu.footer_text}")

            # Probar acceso a El Diván en cada stage
            divan_response = await handle_organic_callback(
                "explain_divan_worthiness",
                stage['context'],
                self.user_service
            )
            print(f"Diván Access: {divan_response.content[:100]}...")

            journey_results[stage['name']] = {
                'menu': menu,
                'divan_response': divan_response
            }

        return journey_results

    def _display_menu(self, menu, user_type: str) -> None:
        """Helper para mostrar estructura del menú."""
        print(f"\n--- {menu.title} ({user_type}) ---")
        print(f"Header: {menu.header_text}")

        for item in menu.items:
            icon = "✅" if not any(keyword in item.action_data for keyword in
                                ['explain', 'worthiness', 'invitation']) else "🔒"
            print(f"{icon} {item.text}")
            if hasattr(item, 'lucien_voice_text') and item.lucien_voice_text:
                print(f"    Lucien: {item.lucien_voice_text[:80]}...")

        print(f"Footer: {menu.footer_text}")

    async def demonstrate_a_b_testing_scenario(self, user_id: str) -> Dict[str, Any]:
        """Demuestra cómo sería A/B testing contra sistema tradicional."""

        user_context = {
            'user_id': user_id,
            'role': 'free_user',
            'has_vip': False,
            'narrative_level': 2,
            'worthiness_score': 0.3,
            'besitos_balance': 200,
            'user_archetype': 'direct'
        }

        print("\n=== A/B TESTING SIMULATION ===")

        # Versión A: Sistema Orgánico (nueva implementación)
        print("\n--- VERSIÓN A: SISTEMA ORGÁNICO ---")
        organic_menu = await self.menu_factory.create_menu(MenuType.MAIN, user_context)
        organic_store = await self.menu_factory.create_organic_store_menu(user_context)

        print("Menú Principal Orgánico:")
        visible_items_organic = len([item for item in organic_menu.items])
        restricted_items_organic = len([item for item in organic_menu.items
                                     if 'explain' in item.action_data or 'invitation' in item.action_data])

        print(f"  - Ítems visibles: {visible_items_organic}")
        print(f"  - Ítems con restricciones elegantes: {restricted_items_organic}")
        print(f"  - Porcentaje de visibilidad: 100%")
        print(f"  - Tone: Sofisticado y aspiracional")

        # Versión B: Sistema Tradicional Segregado (simulación)
        print("\n--- VERSIÓN B: SISTEMA TRADICIONAL ---")
        print("Menú Principal Segregado:")
        visible_items_traditional = len([item for item in organic_menu.items
                                       if not any(keyword in item.action_data for keyword in
                                                ['explain', 'worthiness', 'invitation'])])
        hidden_items_traditional = len(organic_menu.items) - visible_items_traditional

        print(f"  - Ítems visibles: {visible_items_traditional}")
        print(f"  - Ítems ocultos: {hidden_items_traditional}")
        print(f"  - Porcentaje de visibilidad: {(visible_items_traditional/len(organic_menu.items)*100):.1f}%")
        print(f"  - Tone: Funcional y directo")

        # Simular métricas
        metrics = {
            'organic_system': {
                'visibility_percentage': 100,
                'engagement_predicted': 85,  # Usuarios exploran más
                'frustration_level': 15,     # Baja por explicaciones elegantes
                'aspiration_level': 90,      # Alta por ver posibilidades
                'conversion_motivation': 80  # Alta por progresión natural
            },
            'traditional_system': {
                'visibility_percentage': (visible_items_traditional/len(organic_menu.items)*100),
                'engagement_predicted': 60,  # Usuarios ven menos opciones
                'frustration_level': 45,     # Media-alta por exclusión
                'aspiration_level': 40,      # Baja por no ver posibilidades
                'conversion_motivation': 30  # Baja por barreras percibidas
            }
        }

        return {
            'organic_menu': organic_menu,
            'organic_store': organic_store,
            'metrics_simulation': metrics
        }


async def run_complete_demo():
    """Ejecuta demostración completa del sistema orgánico."""
    print("🌟 DEMOSTRACIÓN COMPLETA DEL SISTEMA DE MENÚS ORGÁNICOS 🌟")
    print("="*60)

    # Mock user service para la demo
    class MockUserService:
        async def get_user_context(self, user_id: str) -> Dict[str, Any]:
            return {'user_id': user_id, 'role': 'free_user'}

    user_service = MockUserService()
    demo = OrganicMenuIntegrationExample(user_service)

    user_id = "demo_user_123"

    try:
        # 1. Demostrar menús principales para diferentes usuarios
        main_menus = await demo.demonstrate_main_menu(user_id)

        # 2. Demostrar interacciones con tienda orgánica
        store_interactions = await demo.demonstrate_store_interactions(user_id)

        # 3. Demostrar journey de progresión
        progression_journey = await demo.demonstrate_progression_journey(user_id)

        # 4. Demostrar escenario A/B testing
        ab_testing = await demo.demonstrate_a_b_testing_scenario(user_id)

        print("\n🎯 RESUMEN DE BENEFICIOS DEL SISTEMA ORGÁNICO:")
        print("✅ Transparencia total: Todos ven todas las opciones")
        print("✅ Restricciones elegantes: Lucien explica con sofisticación")
        print("✅ Progresión natural: VIP como development, no como barrera")
        print("✅ Experiencia unificada: Una sola interfaz para todos")
        print("✅ Mayor engagement: Usuarios exploran más posibilidades")
        print("✅ Conversiones naturales: Upgrade motivado por aspiración")

        print("\n🚀 SISTEMA IMPLEMENTADO EXITOSAMENTE")

        return {
            'main_menus': main_menus,
            'store_interactions': store_interactions,
            'progression_journey': progression_journey,
            'ab_testing_results': ab_testing
        }

    except Exception as e:
        print(f"❌ Error en demostración: {e}")
        raise


# Ejemplo de uso directo
if __name__ == "__main__":
    # Para ejecutar la demo:
    # python examples/organic_menu_integration.py

    async def main():
        results = await run_complete_demo()

        # Aquí podrías guardar resultados, generar reportes, etc.
        print(f"\n📊 Demo completada con {len(results)} secciones exitosas")

    asyncio.run(main())


# Ejemplos de integración en handlers existentes

class ExistingHandlerIntegration:
    """Muestra cómo integrar el sistema orgánico en handlers existentes."""

    def __init__(self, menu_factory: MenuFactory, user_service: UserService):
        self.menu_factory = menu_factory
        self.user_service = user_service

    async def handle_main_menu_command(self, message, user_context: Dict[str, Any]) -> CommandResponse:
        """Integrar menú orgánico en handler de comando /menu."""

        # Usar el nuevo sistema orgánico
        menu = await self.menu_factory.create_menu(MenuType.MAIN, user_context)

        # Convertir a formato de respuesta apropiado
        response_text = f"{menu.header_text}\n\n"

        # Generar botones inline con el nuevo sistema
        inline_buttons = []
        for item in menu.items:
            button_text = item.text
            callback_data = item.action_data
            inline_buttons.append([{"text": button_text, "callback_data": callback_data}])

        response_text += f"\n\n{menu.footer_text}"

        return CommandResponse(
            content=response_text,
            reply_markup={"inline_keyboard": inline_buttons}
        )

    async def handle_callback_query(self, callback_query, user_context: Dict[str, Any]) -> CommandResponse:
        """Integrar manejo de callbacks orgánicos."""

        callback_data = callback_query.data

        # Verificar si es un callback del sistema orgánico
        if any(prefix in callback_data for prefix in
               ["worthiness_explanation:", "vip_invitation:", "explain_restriction:", "explain_divan_worthiness"]):

            # Usar el nuevo handler orgánico
            return await handle_organic_callback(callback_data, user_context, self.user_service)

        # Continuar con lógica de callback existente para otros casos
        return await self._handle_traditional_callback(callback_query, user_context)

    async def _handle_traditional_callback(self, callback_query, user_context: Dict[str, Any]) -> CommandResponse:
        """Placeholder para lógica de callback existente."""
        return CommandResponse(content="Callback tradicional manejado")


# Configuración para testing
class OrganicMenuTestConfiguration:
    """Configuración para testing del sistema orgánico."""

    @staticmethod
    def get_test_user_contexts() -> List[Dict[str, Any]]:
        """Contextos de usuario para testing comprehensivo."""
        return [
            # Usuario completamente nuevo
            {
                'user_id': 'test_new_user',
                'role': 'free_user',
                'has_vip': False,
                'narrative_level': 1,
                'worthiness_score': 0.0,
                'besitos_balance': 50,
                'user_archetype': 'explorer'
            },
            # Usuario gratuito activo
            {
                'user_id': 'test_active_free',
                'role': 'free_user',
                'has_vip': False,
                'narrative_level': 3,
                'worthiness_score': 0.4,
                'besitos_balance': 400,
                'user_archetype': 'persistent'
            },
            # Usuario en threshold de VIP
            {
                'user_id': 'test_vip_threshold',
                'role': 'free_user',
                'has_vip': False,
                'narrative_level': 3,
                'worthiness_score': 0.6,
                'besitos_balance': 800,
                'user_archetype': 'analytical'
            },
            # Usuario VIP nuevo
            {
                'user_id': 'test_new_vip',
                'role': 'vip_user',
                'has_vip': True,
                'narrative_level': 4,
                'worthiness_score': 0.5,
                'besitos_balance': 600,
                'user_archetype': 'patient'
            },
            # Usuario VIP elite
            {
                'user_id': 'test_elite_vip',
                'role': 'vip_user',
                'has_vip': True,
                'narrative_level': 6,
                'worthiness_score': 0.9,
                'besitos_balance': 2000,
                'user_archetype': 'direct'
            }
        ]

    @staticmethod
    def get_test_scenarios() -> List[Dict[str, Any]]:
        """Escenarios de testing para validar el sistema."""
        return [
            {
                'name': 'Worthiness Progression',
                'description': 'Usuario progresa gradualmente en worthiness',
                'test_callbacks': [
                    'worthiness_explanation:fragmentos_intimos:0.4',
                    'worthiness_explanation:joyas_intimidad:0.6'
                ]
            },
            {
                'name': 'VIP Conversion Journey',
                'description': 'Usuario considera y convierte a VIP',
                'test_callbacks': [
                    'vip_invitation:circulo_intimo',
                    'explain_divan_worthiness'
                ]
            },
            {
                'name': 'Elite User Experience',
                'description': 'Usuario VIP elite con acceso completo',
                'test_callbacks': [
                    'access_granted:fragmentos_intimos',
                    'vip_access:circulo_intimo'
                ]
            }
        ]