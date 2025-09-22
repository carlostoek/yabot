#!/usr/bin/env python3
"""
Script para probar el bot con monitoreo integrado.
Este script ayuda a diagnosticar qué está impidiendo el cierre del bot.
"""

import asyncio
import signal
import sys
import os
import threading
import time
import traceback
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def log_with_timestamp(message):
    """Log con timestamp para seguimiento."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] {message}")
    sys.stdout.flush()

def print_process_info():
    """Imprime información del proceso actual."""
    pid = os.getpid()
    log_with_timestamp(f"PID del bot: {pid}")
    log_with_timestamp(f"Hilos activos: {threading.active_count()}")

    # Listar todos los hilos
    for thread in threading.enumerate():
        log_with_timestamp(f"  Hilo: {thread.name} - Vivo: {thread.is_alive()} - Daemon: {thread.daemon}")

async def start_bot_with_monitoring():
    """Inicia el bot con monitoreo de procesos."""
    log_with_timestamp("=== INICIANDO BOT CON MONITOREO ===")
    print_process_info()

    try:
        # Importar y configurar logging
        from src.utils.logger import get_logger
        logger = get_logger(__name__)
        log_with_timestamp("Logger configurado")

        # Importar componentes principales
        from src.main import main, background_tasks, shutdown_bot
        log_with_timestamp("Módulos principales importados")

        # Configurar manejadores de señales con monitoreo
        def signal_handler_with_monitoring(signum, frame):
            log_with_timestamp(f"=== SEÑAL RECIBIDA: {signum} ===")
            print_process_info()

            log_with_timestamp("Iniciando secuencia de shutdown monitoreada...")

            # Programar shutdown en el event loop
            try:
                loop = asyncio.get_running_loop()
                loop.call_soon_threadsafe(lambda: asyncio.create_task(monitored_shutdown(signum)))
                log_with_timestamp("Shutdown programado en el event loop")
            except Exception as e:
                log_with_timestamp(f"Error programando shutdown: {e}")
                # Fallback: shutdown inmediato
                asyncio.create_task(monitored_shutdown(signum))

        async def monitored_shutdown(signum):
            """Shutdown con monitoreo detallado."""
            log_with_timestamp("=== INICIANDO SHUTDOWN MONITOREADO ===")

            try:
                log_with_timestamp("Estado antes del shutdown:")
                print_process_info()
                log_with_timestamp(f"Background tasks activas: {len(background_tasks)}")

                # Listar background tasks
                for i, task in enumerate(background_tasks):
                    log_with_timestamp(f"  Task {i}: {task} - Done: {task.done()} - Cancelled: {task.cancelled()}")

                log_with_timestamp("Llamando a shutdown_bot()...")
                await shutdown_bot(signum)
                log_with_timestamp("shutdown_bot() completado")

                log_with_timestamp("Estado después del shutdown:")
                print_process_info()
                log_with_timestamp(f"Background tasks restantes: {len(background_tasks)}")

                # Intentar cancelar manualmente cualquier task restante
                if background_tasks:
                    log_with_timestamp("Cancelando tasks restantes manualmente...")
                    for task in list(background_tasks):
                        if not task.done():
                            task.cancel()
                            log_with_timestamp(f"Cancelada task: {task}")

                # Esperar un momento para que las tasks se cancelen
                await asyncio.sleep(1)

                log_with_timestamp("Estado final:")
                print_process_info()
                log_with_timestamp(f"Background tasks finales: {len(background_tasks)}")

                # Verificar si hay hilos no-daemon que puedan estar bloqueando
                non_daemon_threads = [t for t in threading.enumerate() if not t.daemon and t != threading.current_thread()]
                if non_daemon_threads:
                    log_with_timestamp("¡ATENCIÓN! Hilos no-daemon detectados que pueden impedir el cierre:")
                    for thread in non_daemon_threads:
                        log_with_timestamp(f"  Hilo bloqueante: {thread.name} - {thread}")

                log_with_timestamp("=== SHUTDOWN MONITOREADO COMPLETADO ===")

            except Exception as e:
                log_with_timestamp(f"ERROR durante shutdown monitoreado: {e}")
                traceback.print_exc()

        # Registrar manejadores de señales
        signal.signal(signal.SIGINT, signal_handler_with_monitoring)
        signal.signal(signal.SIGTERM, signal_handler_with_monitoring)
        log_with_timestamp("Manejadores de señales registrados")

        # Imprimir instrucciones
        print()
        log_with_timestamp("=== BOT LISTO PARA PRUEBAS ===")
        log_with_timestamp("El bot está corriendo con monitoreo completo")
        log_with_timestamp("Instrucciones:")
        log_with_timestamp("1. En otra terminal, ejecuta: ./diagnostic_bot.sh " + str(os.getpid()))
        log_with_timestamp("2. En otra terminal, ejecuta: ./monitor_bot_realtime.sh " + str(os.getpid()))
        log_with_timestamp("3. Presiona Ctrl+C para probar el shutdown")
        log_with_timestamp("4. Observa los logs para ver dónde se queda colgado")
        print()

        # Ejecutar el bot
        log_with_timestamp("Iniciando main()...")
        await main()

    except KeyboardInterrupt:
        log_with_timestamp("KeyboardInterrupt capturado en main")
    except Exception as e:
        log_with_timestamp(f"Error en start_bot_with_monitoring: {e}")
        traceback.print_exc()
    finally:
        log_with_timestamp("=== FINALIZANDO BOT CON MONITOREO ===")
        print_process_info()

def main_wrapper():
    """Wrapper principal para manejo de excepciones."""
    try:
        asyncio.run(start_bot_with_monitoring())
    except KeyboardInterrupt:
        log_with_timestamp("KeyboardInterrupt en main_wrapper")
    except Exception as e:
        log_with_timestamp(f"Error crítico: {e}")
        traceback.print_exc()
    finally:
        log_with_timestamp("=== PROCESO TERMINANDO ===")
        print_process_info()

        # Verificación final de hilos
        remaining_threads = threading.enumerate()
        if len(remaining_threads) > 1:  # MainThread siempre existe
            log_with_timestamp("HILOS AÚN ACTIVOS AL FINAL:")
            for thread in remaining_threads:
                log_with_timestamp(f"  {thread.name}: daemon={thread.daemon}, alive={thread.is_alive()}")

        log_with_timestamp("Script terminado")

if __name__ == "__main__":
    main_wrapper()