# Bug Report

## Bug Summary
El bot YABOT no se cierra correctamente al presionar Ctrl+C, requiriendo el uso de herramientas como `kill -9` para terminar el proceso. A pesar de intentos previos de corrección, el problema persiste.

## Bug Details

### Expected Behavior
Al presionar Ctrl+C (SIGINT), el bot debería:
1. Capturar la señal correctamente
2. Ejecutar un cierre ordenado de todos los servicios
3. Cancelar todas las tareas asíncronas pendientes
4. Liberar recursos (conexiones de base de datos, Redis, etc.)
5. Terminar el proceso limpiamente en máximo 5-10 segundos

### Actual Behavior
Al presionar Ctrl+C, el bot:
1. Recibe la señal pero no responde
2. Continúa ejecutándose en segundo plano
3. No libera recursos adecuadamente
4. Requiere terminación forzada con `kill -9`
5. Puede dejar conexiones abiertas y recursos sin liberar

### Steps to Reproduce
1. Ejecutar el bot con `python src/main.py` o `python -m src.main`
2. Esperar a que el bot se inicie correctamente
3. Presionar Ctrl+C en la terminal
4. Observar que el proceso no termina y continúa ejecutándose

### Environment
- **Version**: YABOT desarrollo actual (commit e967c89)
- **Platform**: Linux (específicamente Azure Ubuntu)
- **Python**: 3.12
- **Configuration**: Aiogram 3.0, FastAPI, MongoDB, SQLite, Redis

## Impact Assessment

### Severity
- [x] High - Major functionality broken
- [ ] Critical - System unusable
- [ ] Medium - Feature impaired but workaround exists
- [ ] Low - Minor issue or cosmetic

### Affected Users
- Desarrolladores ejecutando el bot localmente
- Administradores del sistema que necesitan reiniciar el servicio
- Procesos de deployment y CI/CD que requieren cierre limpio

### Affected Features
- Gestión del ciclo de vida de la aplicación
- Liberación de recursos del sistema
- Procesos de deployment y mantenimiento
- Potencialmente la integridad de datos si las conexiones no se cierran correctamente

## Additional Context

### Error Messages
No se generan mensajes de error específicos, pero los logs pueden mostrar:
```
INFO - Received signal 2, scheduling shutdown...
INFO - Starting YABOT application with atomic modules...
```
Sin embargo, el proceso nunca termina completamente.

### Screenshots/Media
N/A (problema de comportamiento en terminal)

### Related Issues
- Commits previos de corrección: e967c89, adf0603, 1a48319
- Archivo de análisis previo: `SHUTDOWN_FIX_SUMMARY.md`
- Scripts de prueba existentes: `test_shutdown_fix.py`, `test_shutdown_logic.py`
- Archivo de análisis: `fix_bot_shutdown.py`

## Initial Analysis

### Suspected Root Cause
Basado en la revisión del código y intentos previos de corrección, las posibles causas incluyen:

1. **Tareas asíncronas que no se cancelan**: Módulos como `menu_cache.py`, `database/manager.py`, y `events/bus.py` pueden tener tareas que no responden a la cancelación
2. **Bucles infinitos sin manejo de CancelledError**: Bucles de limpieza y monitoreo que no verifican cancelaciones
3. **Conexiones de red persistentes**: MongoDB, Redis, o SQLite pueden mantener conexiones activas
4. **Problemas con el event loop**: El manejo de señales puede no estar interrumpiendo correctamente el event loop principal
5. **Módulos no registrados para shutdown**: El sistema de registro de módulos puede no estar detienendo todos los servicios

### Affected Components
Basado en el análisis del código, los componentes potencialmente afectados incluyen:

- **src/main.py**: Manejo principal de señales y shutdown (líneas 47-101, 167-233)
- **src/core/application.py**: Método `BotApplication.stop()`
- **src/ui/menu_cache.py**: Tarea `_cleanup_task`
- **src/database/manager.py**: Tareas `_mongo_recovery_task`, `_sqlite_recovery_task`
- **src/events/bus.py**: Tareas de procesamiento de colas
- **src/shared/registry/module_registry.py**: Sistema de registro de módulos
- **Conexiones a servicios externos**: MongoDB, Redis, SQLite

### Previous Fix Attempts
Según `SHUTDOWN_FIX_SUMMARY.md`, se han implementado las siguientes correcciones:

1. Eliminación de `sys.exit(0)` de la función `shutdown_bot`
2. Implementación de `asyncio.Event` para coordinación de shutdown
3. Uso de `loop.call_soon_threadsafe()` para manejo thread-safe de señales
4. Agregado de mecanismo de cancelación de tareas en background
5. Mejora del manejo de errores en `BotApplication.stop()`
6. Definición de variable global `background_tasks`

**Sin embargo, el problema persiste**, indicando que hay componentes adicionales que no están siendo manejados correctamente durante el shutdown.

---