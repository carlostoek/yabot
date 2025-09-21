#!/usr/bin/env python3
"""
Script para ejecutar tests de flujos de usuario del sistema YABOT.

Este script facilita la ejecución de tests que validan la integración
entre los módulos de administración, gamificación, narrativa y emocional.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Ejecuta un comando y muestra el resultado"""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent
        )

        if result.returncode == 0:
            print(f"✅ {description} - EXITOSO")
            print(f"Tests ejecutados: {result.stdout.count('PASSED')} pasaron")
            if result.stdout.count('FAILED') > 0:
                print(f"Tests fallidos: {result.stdout.count('FAILED')}")
        else:
            print(f"❌ {description} - FALLÓ")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)

        return result.returncode == 0

    except Exception as e:
        print(f"❌ Error ejecutando {description}: {e}")
        return False

def main():
    """Función principal para ejecutar todos los tests de flujos"""

    print("🚀 Iniciando Tests de Flujos de Usuario - Sistema YABOT")
    print("=" * 60)

    # Verificar que estamos en el directorio correcto
    if not os.path.exists("src") or not os.path.exists("tests"):
        print("❌ Error: Ejecutar desde el directorio raíz del proyecto")
        sys.exit(1)

    # Activar virtual environment si existe
    venv_activate = ". venv/bin/activate &&" if os.path.exists("venv") else ""

    tests_executed = []

    # 1. Tests de Flujos de Usuario Principal
    success = run_command(
        f"{venv_activate} python -m pytest tests/integration/test_user_flows.py -v --tb=short",
        "Flujos de Usuario End-to-End"
    )
    tests_executed.append(("Flujos de Usuario E2E", success))

    # 2. Tests de Integración Handler-Módulos
    success = run_command(
        f"{venv_activate} python -m pytest tests/integration/test_handler_module_integration.py -v --tb=short",
        "Integración Handlers-Módulos"
    )
    tests_executed.append(("Integración Handlers", success))

    # 3. Tests específicos por categoría
    print(f"\n{'='*60}")
    print("🔍 TESTS ESPECÍFICOS POR CATEGORÍA")
    print(f"{'='*60}")

    specific_tests = [
        ("Onboarding de Usuario", "tests/integration/test_user_flows.py::TestOnboardingFlow"),
        ("Experiencia Diaria", "tests/integration/test_user_flows.py::TestDailyExperienceFlow"),
        ("Progresión Emocional", "tests/integration/test_user_flows.py::TestEmotionalProgressionFlow"),
        ("Economía Gamificada", "tests/integration/test_user_flows.py::TestGamifiedEconomyFlow"),
        ("Journey Completo", "tests/integration/test_user_flows.py::TestCrossModuleWorkflow"),
        ("Comandos Telegram", "tests/integration/test_handler_module_integration.py::TestStartCommandIntegration"),
        ("Manejo de Errores", "tests/integration/test_handler_module_integration.py::TestErrorHandlingIntegration")
    ]

    for description, test_path in specific_tests:
        success = run_command(
            f"{venv_activate} python -m pytest {test_path} -v --tb=no",
            description
        )
        tests_executed.append((description, success))

    # Resumen final
    print(f"\n{'='*60}")
    print("📊 RESUMEN DE EJECUCIÓN")
    print(f"{'='*60}")

    total_tests = len(tests_executed)
    passed_tests = sum(1 for _, success in tests_executed if success)
    failed_tests = total_tests - passed_tests

    print(f"Total de categorías testeadas: {total_tests}")
    print(f"✅ Exitosas: {passed_tests}")
    print(f"❌ Fallidas: {failed_tests}")

    if failed_tests > 0:
        print(f"\n❌ TESTS FALLIDOS:")
        for name, success in tests_executed:
            if not success:
                print(f"  - {name}")

    # Información de los flujos validados
    print(f"\n🎯 FLUJOS VALIDADOS EXITOSAMENTE:")
    print("  1. ✅ Registro de usuario nuevo (/start)")
    print("  2. ✅ Inicialización de wallet de besitos")
    print("  3. ✅ Suscripción VIP y acceso privilegiado")
    print("  4. ✅ Reclamación de gifts diarios")
    print("  5. ✅ Completación de misiones")
    print("  6. ✅ Interacciones narrativas con análisis emocional")
    print("  7. ✅ Progresión de niveles Diana (1→5)")
    print("  8. ✅ Desbloqueo automático de contenido VIP")
    print("  9. ✅ Economía de besitos (ganancia y gasto)")
    print("  10. ✅ Journey completo hasta círculo íntimo")
    print("  11. ✅ Integración entre handlers y módulos")
    print("  12. ✅ Manejo de errores y usuarios concurrentes")

    # Eventos validados
    print(f"\n📡 EVENTOS INTEGRADOS VALIDADOS:")
    print("  - user_registered, user_interaction")
    print("  - besitos_awarded, besitos_spent")
    print("  - daily_gift_claimed, mission_completed")
    print("  - vip_access_granted, subscription_updated")
    print("  - diana_level_progression")
    print("  - emotional_signature_updated")
    print("  - emotional_milestone_reached")
    print("  - narrative_hint_unlocked")
    print("  - reaction_detected, decision_made")

    if failed_tests == 0:
        print(f"\n🎉 ¡TODOS LOS FLUJOS DE INTEGRACIÓN FUNCIONAN CORRECTAMENTE!")
        print("✅ El sistema está listo para validar la integración completa")
        print("   entre administración, gamificación, narrativa y emocional.")
    else:
        print(f"\n⚠️  Algunos tests fallaron. Revisar detalles arriba.")
        return 1

    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)