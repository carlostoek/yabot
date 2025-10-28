# Guía de Desarrollo - Sistema YABOT

## 📋 Tabla de Contenidos
1. [Estructura del Proyecto](#estructura-del-proyecto)
2. [Conexiones entre Módulos](#conexiones-entre-módulos)
3. [Expansión de Funciones](#expansión-de-funciones)
4. [Flujo de Desarrollo](#flujo-de-desarrollo)
5. [Mejores Prácticas](#mejores-prácticas)
6. [Comandos Útiles](#comandos-útiles)
7. [Solución de Problemas](#solución-de-problemas)
8. [Próximos Pasos](#próximos-pasos)

## 🏗️ Estructura del Proyecto

```
src/
├── api/                    # Endpoints de la API REST
│   ├── __init__.py        # App principal de FastAPI
│   ├── endpoints/         # Routers por módulo
│   └── cross_module.py    # Integración entre módulos
├── services/              # Lógica de negocio principal
│   ├── user.py           # Gestión de usuarios
│   ├── subscription.py   # Suscripciones VIP
│   ├── narrative.py      # Narrativa
│   └── cross_module.py   # Servicio de integración
├── modules/              # Módulos especializados
│   ├── admin/           # Administración
│   ├── gamification/    # Gamificación
│   └── narrative/       # Narrativa
├── database/            # Gestión de bases de datos
│   ├── manager.py       # Manager principal
│   ├── mongodb.py       # Operaciones MongoDB
│   └── sqlite.py        # Operaciones SQLite
├── events/              # Sistema de eventos
│   ├── bus.py          # EventBus principal
│   └── models.py       # Modelos de eventos
├── shared/             # Utilidades compartidas
└── utils/              # Utilidades generales
```

## 🔗 Conexiones entre Módulos

### 1. Comunicación Directa (Servicios)
```python
# Ejemplo: UserService usando SubscriptionService
class UserService:
    def __init__(self, subscription_service: SubscriptionService):
        self.subscription_service = subscription_service
    
    async def check_vip_access(self, user_id: str):
        return await self.subscription_service.is_user_vip(user_id)
```

### 2. Sistema de Eventos
```python
# Publicar evento
from src.events.models import create_event
event = create_event("user_interaction", user_id=user_id, action="click")
await event_bus.publish("user_interaction", event.dict())

# Suscribirse a eventos
@event_bus.subscribe("user_interaction")
async def handle_user_interaction(event_data):
    # Procesar evento
    pass
```

### 3. API REST entre Módulos
```python
# Llamar a otro módulo via HTTP
import httpx

async def call_gamification_module(user_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8001/gamification/award-besitos",
            json={"user_id": user_id, "amount": 10},
            headers={"Authorization": "Bearer API_KEY"}
        )
        return response.json()
```

## 🚀 Expansión de Funciones

### 1. Añadir Nuevo Endpoint
```python
# En src/api/nuevo_modulo.py
from fastapi import APIRouter, Depends
from src.services.nuevo_service import NuevoService, get_nuevo_service

router = APIRouter()

@router.post("/nuevo-endpoint/{user_id}")
async def nuevo_endpoint(
    user_id: str,
    service: NuevoService = Depends(get_nuevo_service)
):
    result = await service.procesar(user_id)
    return {"result": result}

# Registrar en src/api/__init__.py
from src.api.nuevo_modulo import router as nuevo_router
app.include_router(nuevo_router, prefix="/nuevo", tags=["nuevo"])
```

### 2. Crear Nuevo Servicio
```python
# En src/services/nuevo_service.py
from src.database.manager import DatabaseManager
from src.events.bus import EventBus

class NuevoService:
    def __init__(self, database: DatabaseManager, event_bus: EventBus):
        self.database = database
        self.event_bus = event_bus
    
    async def procesar(self, user_id: str):
        # Lógica del servicio
        return {"status": "processed"}

# Función de dependencia
async def get_nuevo_service(
    database: DatabaseManager = Depends(),
    event_bus: EventBus = Depends()
) -> NuevoService:
    return NuevoService(database, event_bus)
```

### 3. Integrar con Base de Datos
```python
# Operaciones MongoDB
db = database_manager.get_mongo_db()
collection = db["nueva_coleccion"]
await collection.insert_one({"data": "value"})

# Operaciones SQLite
conn = database_manager.get_sqlite_conn()
cursor = conn.cursor()
cursor.execute("INSERT INTO tabla (campo) VALUES (?)", ("valor",))
conn.commit()
```

## 🔄 Flujo de Desarrollo Típico

### 1. Planificar la Función
- Definir qué módulos afecta
- Determinar tipo de comunicación (directa/eventos/API)
- Diseñar interfaces y DTOs

### 2. Implementar
```bash
# 1. Crear servicio (si es necesario)
touch src/services/nuevo_service.py

# 2. Añadir endpoints  
touch src/api/nuevo_modulo.py

# 3. Configurar dependencias
# 4. Implementar lógica de negocio
# 5. Integrar con otros módulos
```

### 3. Probar
```bash
# Ejecutar servidor
uvicorn src.api:app --host 127.0.0.1 --port 8001

# Probar endpoints
curl -X POST http://127.0.0.1:8001/nuevo-endpoint/user123
```

## ✅ Mejores Prácticas

### 1. Gestión de Dependencias
```python
# Usar inyección de dependencias de FastAPI
async def get_service(
    db: DatabaseManager = Depends(),
    bus: EventBus = Depends()
) -> MiService:
    return MiService(db, bus)
```

### 2. Manejo de Errores
```python
from fastapi import HTTPException

try:
    result = await service.operacion()
except ServiceError as e:
    raise HTTPException(status_code=400, detail=str(e))
```

### 3. Logging
```python
from src.utils.logger import get_logger

logger = get_logger(__name__)

async def operacion():
    logger.info("Iniciando operación")
    # ...
    logger.debug("Operación completada")
```

### 4. Eventos para Acciones Cruzadas
```python
# En lugar de llamadas directas entre módulos, usar eventos
await event_bus.publish("narrative_choice_made", {
    "user_id": user_id,
    "fragment_id": fragment_id,
    "choice": choice_data
})
```

## 🛠️ Comandos Útiles

```bash
# Ejecutar servidor (puerto 8001)
uvicorn src.api:app --host 127.0.0.1 --port 8001

# Ejecutar en segundo plano
nohup uvicorn src.api:app --host 127.0.0.1 --port 8001 > server.log 2>&1 &

# Ver procesos en ejecución
ps aux | grep uvicorn

# Ver logs en tiempo real
tail -f server.log

# Detener servidor
pkill -f uvicorn

# Instalar dependencias faltantes
pip install python-dotenv  # Para tests
```

## ❗ Solución de Problemas

### Puerto ya en uso
```bash
# Encontrar proceso usando el puerto
sudo lsof -i :8001

# Matar proceso
kill -9 <PID>

# O usar otro puerto
uvicorn src.api:app --host 127.0.0.1 --port 8002
```

### Dependencias faltantes
```bash
# Instalar desde requirements.txt
pip install -r requirements.txt

# Instalar paquetes específicos
pip install python-dotenv httpx
```

### Error en tests
```bash
# Instalar dependencias de desarrollo
pip install pytest python-dotenv

# Ejecutar tests específicos
python -m pytest tests/test_narrative.py -v
```

## 📈 Próximos Pasos Recomendados

1. **Implementar autenticación JWT** para los endpoints
2. **Crear sistema de permisos** basado en roles VIP/free  
3. **Desarrollar la lógica real** de integración entre módulos
4. **Añadir tests automatizados** para nuevas funcionalidades
5. **Configurar variables de entorno** para configuración
6. **Implementar health checks** para monitoreo
7. **Crear documentación API** con Swagger/OpenAPI

## 📞 Soporte

Para problemas específicos:
1. Revisar logs en `server.log`
2. Verificar que todas las dependencias estén instaladas
3. Confirmar que los servicios de base de datos estén running
4. Revisar configuración de puertos y hosts

¡Happy coding! 🚀
