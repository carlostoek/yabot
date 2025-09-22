#!/usr/bin/env python3
"""
🎮 YABOT Test Playground - Interactive Test Runner
==================================================

Script interactivo para ejecutar y modificar tests de YABOT
con diferentes escenarios emocionales, económicos y de actividad.
"""

import os
import sys
import subprocess
import json
from typing import Dict, Any, List
from dataclasses import dataclass, asdict
from enum import Enum


class TestScenario(Enum):
    EMOTIONAL_FAST_PROGRESS = "1"
    EMOTIONAL_STUCK_USER = "2"
    EMOTIONAL_ARCHETYPE_CHANGE = "3"
    EMOTIONAL_CRISIS_RECOVERY = "4"
    ECONOMY_MILLIONAIRE = "5"
    ECONOMY_BROKE_USER = "6"
    ECONOMY_VIP_PROBLEMATIC = "7"
    ACTIVITY_SUPER_ACTIVE = "8"
    ACTIVITY_LAZY_USER = "9"
    CUSTOM_SCENARIO = "10"


@dataclass
class EmotionalMetrics:
    authenticity_score: float = 0.75
    vulnerability_depth: float = 0.65
    consistency_rating: float = 0.80
    signature_strength: float = 0.75


@dataclass
class TestParameters:
    user_id: str = "test_user_123"
    previous_level: int = 3
    new_level: int = 4
    emotional_metrics: EmotionalMetrics = None
    archetype: str = "Explorer"
    previous_archetype: str = "Novice"
    besitos_amount: int = 200
    besitos_balance: int = 350
    activity_days: int = 14
    interactions_per_day: int = 1

    def __post_init__(self):
        if self.emotional_metrics is None:
            self.emotional_metrics = EmotionalMetrics()


class TestPlayground:
    def __init__(self):
        self.current_params = TestParameters()
        self.scenarios = {
            TestScenario.EMOTIONAL_FAST_PROGRESS: {
                "name": "👨‍💻 Usuario Progresión Súper Rápida",
                "description": "Usuario que salta del nivel 1 al 6 con métricas muy altas",
                "test_function": "test_diana_level_progression_to_vip_access"
            },
            TestScenario.EMOTIONAL_STUCK_USER: {
                "name": "😔 Usuario Estancado",
                "description": "Usuario con baja autenticidad que se queda en nivel 2",
                "test_function": "test_diana_level_progression_to_vip_access"
            },
            TestScenario.EMOTIONAL_ARCHETYPE_CHANGE: {
                "name": "🎭 Cambio de Arquetipo Dramático",
                "description": "Usuario cambia de Explorer a Deep_Authentic",
                "test_function": "test_narrative_interaction_triggers_emotional_analysis"
            },
            TestScenario.EMOTIONAL_CRISIS_RECOVERY: {
                "name": "💔 Crisis y Recuperación Emocional",
                "description": "Usuario tiene crisis emocional pero se recupera",
                "test_function": "test_emotional_crisis_recovery"
            },
            TestScenario.ECONOMY_MILLIONAIRE: {
                "name": "💰 Usuario Millonario",
                "description": "Usuario con muchísimos besitos y gastos altos",
                "test_function": "test_besitos_economy_full_cycle"
            },
            TestScenario.ECONOMY_BROKE_USER: {
                "name": "💸 Usuario Sin Besitos",
                "description": "Usuario que se queda sin dinero",
                "test_function": "test_broke_user_scenario"
            },
            TestScenario.ECONOMY_VIP_PROBLEMATIC: {
                "name": "⚠️ Usuario VIP Problemático",
                "description": "Usuario VIP que abusa del sistema",
                "test_function": "test_problematic_vip_user"
            },
            TestScenario.ACTIVITY_SUPER_ACTIVE: {
                "name": "🔥 Usuario Súper Activo (30 días)",
                "description": "Usuario activo durante 30 días con múltiples interacciones",
                "test_function": "test_complete_user_journey_integration"
            },
            TestScenario.ACTIVITY_LAZY_USER: {
                "name": "😴 Usuario Perezoso",
                "description": "Usuario con actividad mínima (solo 3 días)",
                "test_function": "test_lazy_user_journey"
            },
            TestScenario.CUSTOM_SCENARIO: {
                "name": "⚙️ Escenario Personalizado",
                "description": "Configura tus propios parámetros",
                "test_function": "custom"
            }
        }

    def clear_screen(self):
        os.system('clear' if os.name == 'posix' else 'cls')

    def show_header(self):
        print("🎮" + "="*60 + "🎮")
        print("    YABOT TEST PLAYGROUND - Interactive Test Runner")
        print("🎮" + "="*60 + "🎮")
        print()

    def show_main_menu(self):
        self.clear_screen()
        self.show_header()

        print("📋 ESCENARIOS DISPONIBLES:")
        print("-" * 40)

        for scenario, info in self.scenarios.items():
            print(f"{scenario.value:>2}. {info['name']}")
            print(f"    {info['description']}")
            print()

        print("0. 🚪 Salir")
        print("-" * 40)

    def get_scenario_parameters(self, scenario: TestScenario) -> TestParameters:
        """Retorna parámetros predefinidos para cada escenario"""
        params = TestParameters()

        if scenario == TestScenario.EMOTIONAL_FAST_PROGRESS:
            params.user_id = "fast_progress_user"
            params.previous_level = 1
            params.new_level = 6
            params.emotional_metrics = EmotionalMetrics(
                authenticity_score=0.98,
                vulnerability_depth=0.95,
                consistency_rating=0.97,
                signature_strength=0.96
            )

        elif scenario == TestScenario.EMOTIONAL_STUCK_USER:
            params.user_id = "stuck_user"
            params.previous_level = 1
            params.new_level = 2
            params.emotional_metrics = EmotionalMetrics(
                authenticity_score=0.35,
                vulnerability_depth=0.25,
                consistency_rating=0.40,
                signature_strength=0.30
            )

        elif scenario == TestScenario.EMOTIONAL_ARCHETYPE_CHANGE:
            params.user_id = "archetype_change_user"
            params.archetype = "Deep_Authentic"
            params.previous_archetype = "Explorer"
            params.emotional_metrics = EmotionalMetrics(
                authenticity_score=0.92,
                signature_strength=0.95
            )

        elif scenario == TestScenario.EMOTIONAL_CRISIS_RECOVERY:
            params.user_id = "crisis_user"
            params.archetype = "Withdrawn_Explorer"
            params.previous_archetype = "Trusting_Sharer"
            params.emotional_metrics = EmotionalMetrics(
                authenticity_score=0.25,
                signature_strength=0.30
            )

        elif scenario == TestScenario.ECONOMY_MILLIONAIRE:
            params.user_id = "millionaire_user"
            params.besitos_amount = 10000
            params.besitos_balance = 10000

        elif scenario == TestScenario.ECONOMY_BROKE_USER:
            params.user_id = "broke_user"
            params.besitos_amount = 50
            params.besitos_balance = 0

        elif scenario == TestScenario.ECONOMY_VIP_PROBLEMATIC:
            params.user_id = "problematic_vip"
            params.besitos_amount = 500
            params.besitos_balance = 5000

        elif scenario == TestScenario.ACTIVITY_SUPER_ACTIVE:
            params.user_id = "super_active_user"
            params.activity_days = 30
            params.interactions_per_day = 3

        elif scenario == TestScenario.ACTIVITY_LAZY_USER:
            params.user_id = "lazy_user"
            params.activity_days = 3
            params.interactions_per_day = 1
            params.emotional_metrics = EmotionalMetrics(
                authenticity_score=0.30
            )

        return params

    def show_parameters(self, params: TestParameters):
        """Muestra los parámetros actuales del test"""
        print("📊 PARÁMETROS ACTUALES:")
        print("-" * 30)
        print(f"👤 User ID: {params.user_id}")
        print(f"📈 Nivel anterior: {params.previous_level}")
        print(f"📈 Nivel nuevo: {params.new_level}")
        print(f"🎭 Arquetipo: {params.archetype}")
        print(f"🎭 Arquetipo anterior: {params.previous_archetype}")
        print(f"💰 Besitos cantidad: {params.besitos_amount}")
        print(f"💰 Besitos balance: {params.besitos_balance}")
        print(f"📅 Días de actividad: {params.activity_days}")
        print(f"🔄 Interacciones/día: {params.interactions_per_day}")
        print()
        print("🧠 MÉTRICAS EMOCIONALES:")
        print(f"   Autenticidad: {params.emotional_metrics.authenticity_score:.2f}")
        print(f"   Vulnerabilidad: {params.emotional_metrics.vulnerability_depth:.2f}")
        print(f"   Consistencia: {params.emotional_metrics.consistency_rating:.2f}")
        print(f"   Fuerza firma: {params.emotional_metrics.signature_strength:.2f}")
        print("-" * 30)

    def modify_parameters_menu(self, params: TestParameters) -> TestParameters:
        """Menu para modificar parámetros"""
        while True:
            self.clear_screen()
            self.show_header()
            print("⚙️ MODIFICAR PARÁMETROS")
            print()
            self.show_parameters(params)
            print()
            print("¿Qué quieres modificar?")
            print("1. 👤 User ID")
            print("2. 📈 Niveles (anterior/nuevo)")
            print("3. 🎭 Arquetipos")
            print("4. 💰 Economía (besitos)")
            print("5. 📅 Actividad (días/interacciones)")
            print("6. 🧠 Métricas emocionales")
            print("7. ✅ Continuar con estos parámetros")
            print("0. ↩️ Volver al menú principal")

            choice = input("\nElige una opción [0-7]: ").strip()

            if choice == "0":
                return None
            elif choice == "1":
                params.user_id = input(f"Nuevo User ID [{params.user_id}]: ").strip() or params.user_id
            elif choice == "2":
                try:
                    prev = input(f"Nivel anterior [{params.previous_level}]: ").strip()
                    if prev:
                        params.previous_level = int(prev)
                    new = input(f"Nivel nuevo [{params.new_level}]: ").strip()
                    if new:
                        params.new_level = int(new)
                except ValueError:
                    print("❌ Por favor ingresa números válidos")
                    input("Presiona Enter para continuar...")
            elif choice == "3":
                params.archetype = input(f"Arquetipo [{params.archetype}]: ").strip() or params.archetype
                params.previous_archetype = input(f"Arquetipo anterior [{params.previous_archetype}]: ").strip() or params.previous_archetype
            elif choice == "4":
                try:
                    amount = input(f"Cantidad besitos [{params.besitos_amount}]: ").strip()
                    if amount:
                        params.besitos_amount = int(amount)
                    balance = input(f"Balance besitos [{params.besitos_balance}]: ").strip()
                    if balance:
                        params.besitos_balance = int(balance)
                except ValueError:
                    print("❌ Por favor ingresa números válidos")
                    input("Presiona Enter para continuar...")
            elif choice == "5":
                try:
                    days = input(f"Días de actividad [{params.activity_days}]: ").strip()
                    if days:
                        params.activity_days = int(days)
                    interactions = input(f"Interacciones por día [{params.interactions_per_day}]: ").strip()
                    if interactions:
                        params.interactions_per_day = int(interactions)
                except ValueError:
                    print("❌ Por favor ingresa números válidos")
                    input("Presiona Enter para continuar...")
            elif choice == "6":
                self.modify_emotional_metrics(params.emotional_metrics)
            elif choice == "7":
                return params

    def modify_emotional_metrics(self, metrics: EmotionalMetrics):
        """Modificar métricas emocionales"""
        print("\n🧠 MODIFICAR MÉTRICAS EMOCIONALES")
        print("(Valores entre 0.0 y 1.0)")

        try:
            auth = input(f"Autenticidad [{metrics.authenticity_score:.2f}]: ").strip()
            if auth:
                metrics.authenticity_score = float(auth)

            vuln = input(f"Vulnerabilidad [{metrics.vulnerability_depth:.2f}]: ").strip()
            if vuln:
                metrics.vulnerability_depth = float(vuln)

            cons = input(f"Consistencia [{metrics.consistency_rating:.2f}]: ").strip()
            if cons:
                metrics.consistency_rating = float(cons)

            strength = input(f"Fuerza firma [{metrics.signature_strength:.2f}]: ").strip()
            if strength:
                metrics.signature_strength = float(strength)

        except ValueError:
            print("❌ Por favor ingresa números válidos entre 0.0 y 1.0")
            input("Presiona Enter para continuar...")

    def generate_test_code(self, scenario: TestScenario, params: TestParameters) -> str:
        """Genera el código de test modificado según el escenario"""
        if scenario == TestScenario.EMOTIONAL_FAST_PROGRESS:
            return f'''
# Test: Usuario Progresión Súper Rápida
await mock_event_bus.publish("diana_level_progression", {{
    "user_id": "{params.user_id}",
    "previous_level": {params.previous_level},
    "new_level": {params.new_level},
    "emotional_metrics": {{
        "authenticity_score": {params.emotional_metrics.authenticity_score},
        "vulnerability_depth": {params.emotional_metrics.vulnerability_depth},
        "consistency_rating": {params.emotional_metrics.consistency_rating}
    }}
}})
'''
        elif scenario == TestScenario.EMOTIONAL_STUCK_USER:
            return f'''
# Test: Usuario Estancado
await mock_event_bus.publish("diana_level_progression", {{
    "user_id": "{params.user_id}",
    "previous_level": {params.previous_level},
    "new_level": {params.new_level},
    "emotional_metrics": {{
        "authenticity_score": {params.emotional_metrics.authenticity_score},
        "vulnerability_depth": {params.emotional_metrics.vulnerability_depth},
        "consistency_rating": {params.emotional_metrics.consistency_rating}
    }},
    "vip_access_required": False
}})

# Verificar que NO se otorga VIP
assert not event_capture.has_event_type("vip_access_granted")
'''

        elif scenario == TestScenario.EMOTIONAL_ARCHETYPE_CHANGE:
            return f'''
# Test: Cambio de Arquetipo Dramático
await mock_event_bus.publish("emotional_signature_updated", {{
    "user_id": "{params.user_id}",
    "archetype": "{params.archetype}",
    "authenticity_score": {params.emotional_metrics.authenticity_score},
    "signature_strength": {params.emotional_metrics.signature_strength},
    "previous_archetype": "{params.previous_archetype}"
}})

# Verificar el cambio dramático
emotional_events = event_capture.get_events_by_type("emotional_signature_updated")
assert emotional_events[0]["archetype"] == "{params.archetype}"
assert emotional_events[0]["authenticity_score"] > 0.9
'''

        elif scenario == TestScenario.EMOTIONAL_CRISIS_RECOVERY:
            return f'''
# Test: Crisis y Recuperación Emocional
# Crisis emocional
await mock_event_bus.publish("emotional_signature_updated", {{
    "user_id": "{params.user_id}",
    "archetype": "{params.archetype}",
    "authenticity_score": {params.emotional_metrics.authenticity_score},
    "signature_strength": {params.emotional_metrics.signature_strength},
    "previous_archetype": "{params.previous_archetype}"
}})

# Recuperación
await mock_event_bus.publish("emotional_signature_updated", {{
    "user_id": "{params.user_id}",
    "archetype": "Healing_Connector",
    "authenticity_score": 0.80,
    "signature_strength": 0.85,
    "previous_archetype": "{params.archetype}"
}})
'''

        elif scenario == TestScenario.ECONOMY_MILLIONAIRE:
            return f'''
# Test: Usuario Millonario
await mock_event_bus.publish("besitos_awarded", {{
    "user_id": "{params.user_id}",
    "amount": {params.besitos_amount},
    "reason": "diamond_achievement_bonus",
    "source": "special_event_system",
    "balance_after": {params.besitos_balance}
}})

# Usuario gasta mucho también
await mock_event_bus.publish("besitos_spent", {{
    "user_id": "{params.user_id}",
    "amount": 5000,
    "reason": "exclusive_diana_sessions",
    "item_id": "ultimate_access_pass",
    "balance_after": {params.besitos_balance - 5000}
}})
'''

        elif scenario == TestScenario.ECONOMY_BROKE_USER:
            return f'''
# Test: Usuario Sin Besitos
await mock_event_bus.publish("besitos_awarded", {{
    "user_id": "{params.user_id}",
    "amount": {params.besitos_amount},
    "reason": "registration_bonus",
    "balance_after": {params.besitos_amount}
}})

# Usuario gasta todo
await mock_event_bus.publish("besitos_spent", {{
    "user_id": "{params.user_id}",
    "amount": {params.besitos_amount},
    "reason": "impulse_purchase",
    "item_id": "mystery_box",
    "balance_after": {params.besitos_balance}
}})
'''

        elif scenario == TestScenario.ECONOMY_VIP_PROBLEMATIC:
            return f'''
# Test: Usuario VIP Problemático
await mock_event_bus.publish("vip_access_granted", {{
    "user_id": "{params.user_id}",
    "reason": "subscription_activated"
}})

# Múltiples compras impulsivas
for purchase in range(10):
    await mock_event_bus.publish("besitos_spent", {{
        "user_id": "{params.user_id}",
        "amount": {params.besitos_amount},
        "reason": f"impulsive_purchase_{{purchase}}",
        "item_id": f"luxury_item_{{purchase}}",
        "balance_after": max(0, {params.besitos_balance} - (purchase * {params.besitos_amount}))
    }})
'''

        elif scenario == TestScenario.ACTIVITY_SUPER_ACTIVE:
            return f'''
# Test: Usuario Súper Activo ({params.activity_days} días)
for day in range(1, {params.activity_days + 1}):
    # Gift diario
    await mock_event_bus.publish("daily_gift_claimed", {{
        "user_id": "{params.user_id}",
        "gift_type": "besitos",
        "gift_amount": 25 + (day * 2)
    }})

    # Múltiples interacciones por día
    for interaction in range({params.interactions_per_day}):
        await mock_event_bus.publish("user_interaction", {{
            "user_id": "{params.user_id}",
            "action": "narrative_choice",
            "context": {{
                "authenticity_score": 0.7 + (day * 0.01),
                "daily_interaction": interaction + 1
            }}
        }})
'''

        elif scenario == TestScenario.ACTIVITY_LAZY_USER:
            return f'''
# Test: Usuario Perezoso (solo {params.activity_days} días activos)
active_days = [1, 7, 14]  # Solo días específicos

for day in active_days:
    await mock_event_bus.publish("daily_gift_claimed", {{
        "user_id": "{params.user_id}",
        "gift_type": "besitos",
        "gift_amount": 25
    }})

    # Solo 1 interacción por día activo
    await mock_event_bus.publish("user_interaction", {{
        "user_id": "{params.user_id}",
        "action": "narrative_choice",
        "context": {{"authenticity_score": {params.emotional_metrics.authenticity_score}}}
    }})
'''

        # Código personalizado por defecto
        return f'''
# Test personalizado para {params.user_id}
# Modifica este código según tus necesidades específicas
await mock_event_bus.publish("user_interaction", {{
    "user_id": "{params.user_id}",
    "action": "custom_action",
    "context": {{
        "authenticity_score": {params.emotional_metrics.authenticity_score}
    }}
}})
'''

    def run_test(self, scenario: TestScenario, params: TestParameters):
        """Ejecuta el test con los parámetros especificados"""
        self.clear_screen()
        self.show_header()

        scenario_info = self.scenarios[scenario]
        print(f"🚀 EJECUTANDO: {scenario_info['name']}")
        print("-" * 50)

        # Mostrar parámetros que se van a usar
        self.show_parameters(params)

        # Mostrar código generado
        print("\n📝 CÓDIGO GENERADO:")
        print("-" * 30)
        test_code = self.generate_test_code(scenario, params)
        print(test_code)

        print("\n🔧 COMANDO A EJECUTAR:")
        if scenario_info['test_function'] == 'custom':
            test_cmd = "pytest tests/integration/test_user_flows.py -v -s -k 'user_interaction'"
        else:
            test_cmd = f"pytest tests/integration/test_user_flows.py::{scenario_info['test_function']} -v -s"
        print(test_cmd)

        print("\n¿Quieres ejecutar este test?")
        choice = input("(y/n): ").strip().lower()

        if choice == 'y':
            print("\n🏃‍♂️ Ejecutando test...")
            print("=" * 50)

            try:
                # Ejecutar el comando pytest
                result = subprocess.run(
                    test_cmd.split(),
                    capture_output=True,
                    text=True,
                    cwd="/home/azureuser/repos/yabot"
                )

                print("📊 RESULTADO:")
                print("-" * 20)
                print("STDOUT:")
                print(result.stdout)
                if result.stderr:
                    print("\nSTDERR:")
                    print(result.stderr)

                print(f"\nCódigo de salida: {result.returncode}")

                if result.returncode == 0:
                    print("✅ Test ejecutado exitosamente!")
                else:
                    print("❌ Test falló o hubo errores")

            except Exception as e:
                print(f"❌ Error ejecutando test: {e}")

        input("\nPresiona Enter para continuar...")

    def run(self):
        """Función principal del programa"""
        while True:
            self.show_main_menu()

            choice = input("Elige una opción [0-10]: ").strip()

            if choice == "0":
                print("👋 ¡Hasta luego!")
                break

            try:
                scenario = TestScenario(choice)
                scenario_info = self.scenarios[scenario]

                self.clear_screen()
                self.show_header()
                print(f"🎯 ESCENARIO SELECCIONADO: {scenario_info['name']}")
                print(f"📝 {scenario_info['description']}")
                print()

                # Obtener parámetros para este escenario
                params = self.get_scenario_parameters(scenario)

                # Mostrar parámetros actuales
                self.show_parameters(params)

                print("¿Qué quieres hacer?")
                print("1. ▶️ Ejecutar con estos parámetros")
                print("2. ⚙️ Modificar parámetros")
                print("0. ↩️ Volver al menú principal")

                action = input("\nElige una opción [0-2]: ").strip()

                if action == "0":
                    continue
                elif action == "1":
                    self.run_test(scenario, params)
                elif action == "2":
                    modified_params = self.modify_parameters_menu(params)
                    if modified_params:
                        self.run_test(scenario, modified_params)

            except ValueError:
                print("❌ Opción inválida. Presiona Enter para continuar...")
                input()


if __name__ == "__main__":
    playground = TestPlayground()
    playground.run()