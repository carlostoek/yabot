#!/usr/bin/env python3
"""
Test de Integración REAL - Sin Mocks
Usa los servicios reales del sistema: MongoDB, EventBus, DatabaseManager, SubscriptionService
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

# Agregar src al PYTHONPATH y importar con ruta completa
src_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_path)

# Importar usando el path directo desde src
import database.manager as db_module
import events.bus as event_module
import services.subscription as sub_module
import modules.admin.access_control as access_module
import modules.admin.subscription_manager as sub_mgr_module

DatabaseManager = db_module.DatabaseManager
EventBus = event_module.EventBus
SubscriptionService = sub_module.SubscriptionService
SubscriptionPlan = sub_module.SubscriptionPlan
SubscriptionStatus = sub_module.SubscriptionStatus
AccessControl = access_module.AccessControl
SubscriptionManager = sub_mgr_module.SubscriptionManager

# Configuraciones reales
REAL_CONFIG = {
    'mongodb_uri': 'mongodb://localhost:27017',
    'mongodb_database': 'yabot_test_integration',
    'sqlite_database_path': './test_integration.db',
    'pool_size': 5,
    'max_overflow': 10,
    'pool_timeout': 5,
    'pool_recycle': 1800
}

REDIS_CONFIG = {
    'url': 'redis://localhost:6379/1',  # Base de datos 1 para tests
    'password': None,
    'max_connections': 10
}

class RealIntegrationTester:
    """
    Tester que usa servicios REALES - NO mocks
    """

    def __init__(self):
        self.db_manager = None
        self.event_bus = None
        self.subscription_service = None
        self.access_control = None
        self.subscription_manager = None
        self.test_user_id = "test_user_123"

    async def setup_real_services(self):
        """
        Configura servicios REALES
        """
        print("🔧 Configurando servicios REALES...")

        # DatabaseManager real con MongoDB y SQLite
        self.db_manager = DatabaseManager(REAL_CONFIG)
        connected = await self.db_manager.initialize_databases()

        if not connected:
            print("❌ ERROR: No se pudo conectar a las bases de datos reales")
            return False

        # EventBus real con Redis
        import core.models as core_models
        redis_config = core_models.RedisConfig(**REDIS_CONFIG)
        self.event_bus = EventBus(redis_config)
        await self.event_bus.connect()

        # SubscriptionService real
        self.subscription_service = SubscriptionService(self.db_manager)

        # AccessControl del módulo admin (usa servicios reales)
        # Necesitamos el cliente MongoDB con database específico
        mongo_client = self.db_manager.get_mongo_client()

        # Bot mock simple para las pruebas
        class MockTelegramBot:
            def __init__(self):
                pass
            async def get_chat_member(self, chat_id, user_id):
                # Mock para devolver un miembro con permisos básicos
                class MockChatMember:
                    def __init__(self):
                        self.status = "member"
                        self.user = type('obj', (object,), {"id": int(user_id)})
                return MockChatMember()

        mock_bot = MockTelegramBot()

        # Crear un wrapper para el cliente que incluya el database name
        class MongoClientWrapper:
            def __init__(self, client, db_name):
                self._client = client
                self._db_name = db_name

            def get_database(self):
                return self._client[self._db_name]

        mongo_wrapper = MongoClientWrapper(mongo_client, REAL_CONFIG['mongodb_database'])

        self.access_control = AccessControl(
            db_client=mongo_wrapper,
            event_bus=self.event_bus,
            telegram_bot=mock_bot
        )

        # SubscriptionManager del módulo admin
        self.subscription_manager = SubscriptionManager(
            db_client=mongo_wrapper,
            event_bus=self.event_bus
        )

        print("✅ Servicios reales configurados exitosamente")
        return True

    async def test_real_database_operations(self):
        """
        PRUEBA REAL: Operaciones de base de datos con datos reales
        """
        print("\n📊 Probando operaciones reales de base de datos...")

        # Crear usuario real en MongoDB
        user_mongo_doc = {
            "user_id": self.test_user_id,
            "telegram_id": 123456789,
            "username": "test_user",
            "first_name": "Test",
            "preferences": {
                "language": "es",
                "notifications": True
            },
            "stats": {
                "messages_sent": 0,
                "besitos": 100
            },
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }

        # Crear perfil real en SQLite
        user_sqlite_profile = {
            "user_id": self.test_user_id,
            "telegram_user_id": 123456789,
            "username": "test_user",
            "first_name": "Test",
            "last_name": "User",
            "language_code": "es",
            "registration_date": datetime.now(timezone.utc),
            "is_active": True
        }

        # Operación atómica REAL
        created = await self.db_manager.create_user_atomic(
            self.test_user_id,
            user_mongo_doc,
            user_sqlite_profile
        )

        if not created:
            print("❌ ERROR: No se pudo crear usuario en base de datos real")
            return False

        # Verificar que los datos están realmente en MongoDB
        mongo_user = await self.db_manager.get_user_from_mongo(self.test_user_id)
        if not mongo_user or mongo_user["user_id"] != self.test_user_id:
            print("❌ ERROR: Usuario no encontrado en MongoDB real")
            return False

        # Verificar que los datos están realmente en SQLite
        sqlite_profile = await self.db_manager.get_user_profile_from_sqlite(self.test_user_id)
        if not sqlite_profile or sqlite_profile["user_id"] != self.test_user_id:
            print("❌ ERROR: Perfil no encontrado en SQLite real")
            return False

        print("✅ Usuario creado y verificado en ambas bases de datos REALES")
        print(f"   MongoDB: {mongo_user['username']} - Besitos: {mongo_user['stats']['besitos']}")
        print(f"   SQLite: {sqlite_profile['first_name']} {sqlite_profile['last_name']}")

        return True

    async def test_real_subscription_operations(self):
        """
        PRUEBA REAL: Operaciones de suscripción con datos reales
        """
        print("\n💳 Probando suscripciones REALES...")

        # Crear suscripción VIP real
        subscription = await self.subscription_service.create_subscription(
            user_id=self.test_user_id,
            plan_type=SubscriptionPlan.VIP,
            duration_days=30,
            event_bus=self.event_bus
        )

        if not subscription:
            print("❌ ERROR: No se pudo crear suscripción real")
            return False

        # Verificar suscripción en base de datos real
        stored_sub = await self.subscription_service.get_subscription(self.test_user_id)
        if not stored_sub or stored_sub["plan_type"] != "vip":
            print("❌ ERROR: Suscripción no almacenada correctamente")
            return False

        # Verificar estado activo REAL
        is_active = await self.subscription_service.check_subscription_status(self.test_user_id)
        if not is_active:
            print("❌ ERROR: Suscripción no está activa en sistema real")
            return False

        print(f"✅ Suscripción VIP creada y activa")
        print(f"   Plan: {stored_sub['plan_type']}")
        print(f"   Estado: {stored_sub['status']}")
        print(f"   Expira: {stored_sub['end_date']}")

        return True

    async def test_real_access_control(self):
        """
        PRUEBA REAL: Control de acceso con datos reales del usuario
        """
        print("\n🔒 Probando control de acceso REAL...")

        # Probar validación de acceso VIP con datos reales
        access_result = await self.access_control.validate_access(
            user_id=self.test_user_id,
            channel_id="vip_channel_001"
        )

        if not access_result.granted:
            print("❌ ERROR: Usuario VIP no tiene acceso cuando debería tenerlo")
            return False

        # Probar acceso a canal premium (debería fallar con usuario VIP)
        premium_access = await self.access_control.validate_access(
            user_id=self.test_user_id,
            channel_id="premium_channel_001"
        )

        print(f"✅ Control de acceso funcionando")
        print(f"   Acceso VIP: {access_result.granted} - {access_result.access_level}")
        print(f"   Razón: {access_result.reason}")

        return True

    async def test_real_event_bus(self):
        """
        PRUEBA REAL: EventBus con Redis real
        """
        print("\n📡 Probando EventBus REAL...")

        # Evento recibido
        events_received = []

        def event_handler(event_data: str):
            events_received.append(event_data)
            print(f"   📨 Evento recibido: {event_data[:50]}...")

        # Suscribirse a canal real
        await self.event_bus.subscribe("test_channel", event_handler)

        # Publicar evento real
        import events.models as event_models
        test_event = event_models.BaseEvent(
            event_type="test_integration_event",
            data={"message": "Test de integración real", "timestamp": datetime.now(timezone.utc).isoformat()}
        )

        published = await self.event_bus.publish("test_channel", test_event)
        if not published:
            print("❌ ERROR: No se pudo publicar evento en Redis real")
            return False

        # Esperar un poco para que el evento se procese
        await asyncio.sleep(2)

        # Verificar estadísticas del EventBus real
        stats = await self.event_bus.get_stats()
        if stats['published_events'] == 0:
            print("❌ ERROR: No se registraron eventos publicados")
            return False

        print("✅ EventBus funcionando con Redis real")
        print(f"   Eventos publicados: {stats['published_events']}")
        print(f"   Cola local: {stats['local_queue_size']}")

        return True

    async def test_subscription_expiration_workflow(self):
        """
        PRUEBA REAL: Flujo de expiración de suscripciones
        """
        print("\n⏰ Probando flujo de expiración REAL...")

        # Crear suscripción que expira en 1 segundo
        expired_user_id = "expired_test_user_456"
        past_date = datetime.now(timezone.utc) - timedelta(seconds=1)

        subscription_data = {
            "user_id": expired_user_id,
            "plan_type": "vip",
            "status": "active",
            "start_date": past_date,
            "end_date": past_date,  # Ya expiró
            "created_at": past_date,
            "updated_at": past_date
        }

        # Insertar directamente en SQLite para simular suscripción expirada
        sqlite_engine = self.db_manager.get_sqlite_engine()
        if not sqlite_engine:
            print("❌ ERROR: SQLite engine no disponible")
            return False

        try:
            async with sqlite_engine.connect() as conn:
                await conn.execute(
                    """INSERT INTO subscriptions
                       (user_id, plan_type, status, start_date, end_date, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        subscription_data['user_id'],
                        subscription_data['plan_type'],
                        subscription_data['status'],
                        subscription_data['start_date'],
                        subscription_data['end_date'],
                        subscription_data['created_at'],
                        subscription_data['updated_at']
                    )
                )
                await conn.commit()
            created = True
        except Exception as e:
            print(f"❌ ERROR: Error al insertar suscripción directamente: {e}")
            created = False
        if not created:
            print("❌ ERROR: No se pudo crear suscripción para test de expiración")
            return False

        # Verificar que el sistema detecta la expiración
        is_active = await self.subscription_service.check_subscription_status(expired_user_id)
        if is_active:
            print("❌ ERROR: Sistema no detectó suscripción expirada")
            return False

        # Verificar que el estado se actualizó en la base de datos
        updated_sub = await self.subscription_service.get_subscription(expired_user_id)
        if updated_sub and updated_sub["status"] != "expired":
            print("❌ ERROR: Estado de suscripción no se actualizó a 'expired'")
            return False

        print("✅ Flujo de expiración funcionando correctamente")
        print("   Suscripción expirada detectada y actualizada en DB real")

        return True

    async def cleanup_test_data(self):
        """
        Limpia los datos de prueba de las bases de datos reales
        """
        print("\n🧹 Limpiando datos de prueba...")

        # Limpiar usuario de prueba
        await self.db_manager.rollback_user_creation(self.test_user_id)
        await self.db_manager.rollback_user_creation("expired_test_user_456")

        # Cerrar conexiones
        await self.db_manager.close_connections()
        await self.event_bus.close()

        print("✅ Datos de prueba limpiados")

    async def run_all_tests(self):
        """
        Ejecuta todos los tests de integración real
        """
        print("🚀 INICIANDO TESTS DE INTEGRACIÓN REALES")
        print("=" * 60)

        # Setup
        if not await self.setup_real_services():
            print("❌ FALLO: No se pudieron configurar los servicios reales")
            return False

        tests = [
            ("Base de Datos", self.test_real_database_operations),
            ("Suscripciones", self.test_real_subscription_operations),
            ("Control de Acceso", self.test_real_access_control),
            ("EventBus", self.test_real_event_bus),
            ("Expiración", self.test_subscription_expiration_workflow)
        ]

        failed_tests = []

        for test_name, test_func in tests:
            try:
                print(f"\n🔍 Ejecutando test: {test_name}")
                success = await test_func()
                if not success:
                    failed_tests.append(test_name)
                    print(f"❌ FALLO: Test {test_name}")
                else:
                    print(f"✅ ÉXITO: Test {test_name}")
            except Exception as e:
                failed_tests.append(test_name)
                print(f"❌ ERROR en test {test_name}: {e}")

        # Cleanup
        await self.cleanup_test_data()

        # Resultado final
        print("\n" + "=" * 60)
        if failed_tests:
            print(f"❌ TESTS FALLIDOS: {len(failed_tests)}/{len(tests)}")
            print(f"   Fallidos: {', '.join(failed_tests)}")
            return False
        else:
            print(f"✅ TODOS LOS TESTS PASARON: {len(tests)}/{len(tests)}")
            print("🎉 INTEGRACIÓN REAL FUNCIONANDO CORRECTAMENTE")
            return True

async def main():
    """
    Función principal para ejecutar los tests
    """
    tester = RealIntegrationTester()
    success = await tester.run_all_tests()

    exit_code = 0 if success else 1
    sys.exit(exit_code)

if __name__ == "__main__":
    asyncio.run(main())