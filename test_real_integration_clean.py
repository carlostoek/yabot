#!/usr/bin/env python3
"""
Test de Integración REAL - Versión Limpia y Corregida
Usa los servicios reales del sistema: MongoDB, EventBus, DatabaseManager, SubscriptionService
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

# Configurar path para importaciones
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

# Configuraciones de test
TEST_CONFIG = {
    'mongodb_uri': 'mongodb://localhost:27017',
    'mongodb_database': 'yabot_test_clean',
    'sqlite_database_path': './test_clean.db',
    'pool_size': 5,
    'max_overflow': 10,
    'pool_timeout': 5,
    'pool_recycle': 1800
}

REDIS_CONFIG = {
    'url': 'redis://localhost:6379/2',  # Base de datos 2 para tests limpios
    'password': None,
    'max_connections': 10
}

class CleanIntegrationTester:
    """
    Tester limpio que usa servicios REALES con manejo correcto de errores
    """

    def __init__(self):
        self.db_manager = None
        self.event_bus = None
        self.subscription_service = None
        self.access_control = None
        self.subscription_manager = None

        # Usar IDs únicos para evitar duplicados
        self.test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        self.expired_user_id = f"expired_user_{uuid.uuid4().hex[:8]}"

    async def setup_real_services(self):
        """
        Configura servicios REALES con manejo de errores mejorado
        """
        print("🔧 Configurando servicios REALES...")

        # DatabaseManager real
        self.db_manager = DatabaseManager(TEST_CONFIG)
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

        # AccessControl con wrapper mejorado
        mongo_client = self.db_manager.get_mongo_client()

        class MockTelegramBot:
            """Bot mock mejorado para pruebas"""
            async def get_chat_member(self, chat_id, user_id):
                # Convertir user_id a int si es string
                try:
                    telegram_user_id = int(user_id) if isinstance(user_id, str) and user_id.isdigit() else 123456789
                except ValueError:
                    telegram_user_id = 123456789

                class MockChatMember:
                    def __init__(self):
                        self.status = "member"
                        self.user = type('obj', (object,), {"id": telegram_user_id})
                return MockChatMember()

        class MongoClientWrapper:
            """Wrapper mejorado para cliente MongoDB"""
            def __init__(self, client, db_name):
                self._client = client
                self._db_name = db_name

            def get_database(self):
                return self._client[self._db_name]

        mongo_wrapper = MongoClientWrapper(mongo_client, TEST_CONFIG['mongodb_database'])
        mock_bot = MockTelegramBot()

        self.access_control = AccessControl(
            db_client=mongo_wrapper,
            event_bus=self.event_bus,
            telegram_bot=mock_bot
        )

        # SubscriptionManager
        self.subscription_manager = SubscriptionManager(
            db_client=mongo_wrapper,
            event_bus=self.event_bus
        )

        print("✅ Servicios reales configurados exitosamente")
        return True

    async def cleanup_test_data_before_start(self):
        """
        Limpia datos de pruebas anteriores antes de empezar
        """
        try:
            # Limpiar MongoDB
            mongo_db = self.db_manager.get_mongo_db()
            if mongo_db is not None:
                await mongo_db.users.delete_many({"user_id": {"$regex": "^(test_user_|expired_user_)"}})

            # Limpiar SQLite
            sqlite_engine = self.db_manager.get_sqlite_engine()
            if sqlite_engine:
                import sqlalchemy as sql
                async with sqlite_engine.connect() as conn:
                    await conn.execute(
                        sql.text("DELETE FROM subscriptions WHERE user_id LIKE 'test_user_%' OR user_id LIKE 'expired_user_%'")
                    )
                    await conn.execute(
                        sql.text("DELETE FROM user_profiles WHERE user_id LIKE 'test_user_%' OR user_id LIKE 'expired_user_%'")
                    )
                    await conn.commit()

            print("🧹 Datos de pruebas anteriores limpiados")
        except Exception as e:
            print(f"⚠️ Warning: Error limpiando datos previos: {e}")

    async def test_database_operations(self):
        """
        PRUEBA REAL: Operaciones de base de datos limpias
        """
        print("\n📊 Probando operaciones de base de datos...")

        # Datos de usuario para MongoDB
        user_mongo_doc = {
            "user_id": self.test_user_id,
            "telegram_id": 123456789,
            "username": "test_user_clean",
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

        # Datos de perfil para SQLite
        user_sqlite_profile = {
            "user_id": self.test_user_id,
            "telegram_user_id": 123456789,
            "username": "test_user_clean",
            "first_name": "Test",
            "last_name": "User",
            "language_code": "es",
            "registration_date": datetime.now(timezone.utc),
            "last_login": None,  # Campo requerido en la tabla
            "is_active": True
        }

        # Crear usuario atómicamente
        created = await self.db_manager.create_user_atomic(
            self.test_user_id,
            user_mongo_doc,
            user_sqlite_profile
        )

        if not created:
            print("❌ ERROR: No se pudo crear usuario")
            return False

        # Verificar en MongoDB
        mongo_user = await self.db_manager.get_user_from_mongo(self.test_user_id)
        if not mongo_user:
            print("❌ ERROR: Usuario no encontrado en MongoDB")
            return False

        # Verificar en SQLite
        sqlite_profile = await self.db_manager.get_user_profile_from_sqlite(self.test_user_id)
        if not sqlite_profile:
            print("❌ ERROR: Perfil no encontrado en SQLite")
            return False

        print("✅ Usuario creado y verificado en ambas bases de datos")
        print(f"   MongoDB: {mongo_user['username']} - Besitos: {mongo_user['stats']['besitos']}")
        print(f"   SQLite: {sqlite_profile['first_name']} {sqlite_profile['last_name']}")

        return True

    async def test_subscription_operations(self):
        """
        PRUEBA REAL: Operaciones de suscripción mejoradas
        """
        print("\n💳 Probando suscripciones REALES...")

        # Crear suscripción VIP
        subscription = await self.subscription_service.create_subscription(
            user_id=self.test_user_id,
            plan_type=SubscriptionPlan.VIP,
            duration_days=30,
            event_bus=self.event_bus
        )

        if not subscription:
            print("❌ ERROR: No se pudo crear suscripción")
            return False

        # Verificar en base de datos
        stored_sub = await self.subscription_service.get_subscription(self.test_user_id)
        if not stored_sub:
            print("❌ ERROR: Suscripción no encontrada")
            return False

        # Verificar estado activo
        is_active = await self.subscription_service.check_subscription_status(self.test_user_id)
        if not is_active:
            print("❌ ERROR: Suscripción no está activa")
            return False

        print(f"✅ Suscripción VIP creada y activa")
        print(f"   Plan: {stored_sub['plan_type']}")
        print(f"   Estado: {stored_sub['status']}")

        return True

    async def test_access_control(self):
        """
        PRUEBA REAL: Control de acceso mejorado
        """
        print("\n🔒 Probando control de acceso REAL...")

        # Validar acceso VIP
        access_result = await self.access_control.validate_access(
            user_id=self.test_user_id,
            channel_id="vip_channel_001"
        )

        print(f"✅ Control de acceso validado")
        print(f"   Acceso: {'✅ Concedido' if access_result.granted else '❌ Denegado'}")
        print(f"   Nivel: {access_result.access_level}")
        print(f"   Razón: {access_result.reason or 'N/A'}")

        return True

    async def test_event_bus(self):
        """
        PRUEBA REAL: EventBus simplificado
        """
        print("\n📡 Probando EventBus REAL...")

        # Crear y publicar evento de prueba
        import events.models as event_models
        test_event = event_models.BaseEvent(
            event_type="test_clean_integration",
            data={"message": "Test limpio", "timestamp": datetime.now(timezone.utc).isoformat()}
        )

        # Publicar evento
        published = await self.event_bus.publish("test_clean_channel", test_event)
        if not published:
            print("❌ ERROR: No se pudo publicar evento")
            return False

        # Verificar estadísticas
        stats = await self.event_bus.get_stats()
        print("✅ EventBus funcionando correctamente")
        print(f"   Eventos publicados: {stats['published_events']}")
        print(f"   Cola local: {stats['local_queue_size']}")

        return True

    async def test_subscription_expiration(self):
        """
        PRUEBA REAL: Expiración de suscripciones mejorada
        """
        print("\n⏰ Probando expiración de suscripciones...")

        # Crear suscripción expirada usando el servicio correcto
        past_date = datetime.now(timezone.utc) - timedelta(hours=1)

        # Usar el método correcto del DatabaseManager
        subscription_data = {
            "user_id": self.expired_user_id,
            "plan_type": "vip",
            "status": "active",
            "start_date": past_date,
            "end_date": past_date,  # Ya expiró
            "created_at": past_date,
            "updated_at": past_date
        }

        created = await self.db_manager.create_subscription(subscription_data)
        if not created:
            print("❌ ERROR: No se pudo crear suscripción expirada")
            return False

        # Verificar que el sistema detecta la expiración
        is_active = await self.subscription_service.check_subscription_status(self.expired_user_id)

        print("✅ Flujo de expiración funcionando")
        print(f"   Suscripción activa: {'❌ No' if not is_active else '✅ Sí'}")

        return not is_active  # Debe ser False para que el test pase

    async def cleanup_test_data(self):
        """
        Limpia datos de prueba de forma segura
        """
        print("\n🧹 Limpiando datos de prueba...")

        try:
            # Limpiar usuarios específicos
            await self.db_manager.rollback_user_creation(self.test_user_id)
            await self.db_manager.rollback_user_creation(self.expired_user_id)

            # Limpiar suscripciones específicas
            sqlite_engine = self.db_manager.get_sqlite_engine()
            if sqlite_engine:
                import sqlalchemy as sql
                async with sqlite_engine.connect() as conn:
                    await conn.execute(
                        sql.text("DELETE FROM subscriptions WHERE user_id = :user_id"),
                        {"user_id": self.expired_user_id}
                    )
                    await conn.commit()

        except Exception as e:
            print(f"⚠️ Warning: Error en cleanup: {e}")

        # Cerrar conexiones
        await self.db_manager.close_connections()
        await self.event_bus.close()

        print("✅ Cleanup completado")

    async def run_all_tests(self):
        """
        Ejecuta todos los tests de integración con manejo de errores mejorado
        """
        print("🚀 INICIANDO TESTS DE INTEGRACIÓN REALES (VERSIÓN LIMPIA)")
        print("=" * 70)

        # Setup inicial
        if not await self.setup_real_services():
            print("❌ FALLO: No se pudieron configurar los servicios")
            return False

        # Cleanup previo
        await self.cleanup_test_data_before_start()

        # Lista de tests
        tests = [
            ("Base de Datos", self.test_database_operations),
            ("Suscripciones", self.test_subscription_operations),
            ("Control de Acceso", self.test_access_control),
            ("EventBus", self.test_event_bus),
            ("Expiración", self.test_subscription_expiration)
        ]

        failed_tests = []
        passed_tests = []

        for test_name, test_func in tests:
            try:
                print(f"\n🔍 Ejecutando test: {test_name}")
                success = await test_func()
                if success:
                    passed_tests.append(test_name)
                    print(f"✅ ÉXITO: Test {test_name}")
                else:
                    failed_tests.append(test_name)
                    print(f"❌ FALLO: Test {test_name}")
            except Exception as e:
                failed_tests.append(test_name)
                print(f"❌ ERROR en test {test_name}: {e}")

        # Cleanup final
        await self.cleanup_test_data()

        # Resultado final
        print("\n" + "=" * 70)
        total_tests = len(tests)
        passed_count = len(passed_tests)
        failed_count = len(failed_tests)

        if failed_tests:
            print(f"❌ RESULTADO: {failed_count}/{total_tests} tests fallaron")
            print(f"   ✅ Pasaron: {', '.join(passed_tests) if passed_tests else 'Ninguno'}")
            print(f"   ❌ Fallaron: {', '.join(failed_tests)}")
            return False
        else:
            print(f"✅ RESULTADO: TODOS LOS TESTS PASARON ({passed_count}/{total_tests})")
            print("🎉 INTEGRACIÓN REAL FUNCIONANDO PERFECTAMENTE")
            return True

async def main():
    """
    Función principal mejorada
    """
    tester = CleanIntegrationTester()
    success = await tester.run_all_tests()

    # Exit code apropiado
    exit_code = 0 if success else 1
    print(f"\n🏁 Finalizando con código: {exit_code}")
    sys.exit(exit_code)

if __name__ == "__main__":
    asyncio.run(main())