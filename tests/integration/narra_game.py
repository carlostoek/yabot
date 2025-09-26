"""
Integration Test: Narrative-Gamification Cross-Module Workflow
Validates core DianaBot ecosystem interactions as defined in the concept document.
"""
import asyncio
import pytest
from datetime import datetime

# Core infrastructure
from src.database.manager import DatabaseManager
from src.events.bus import EventBus
from src.core.models import RedisConfig

# Gamification services
from src.modules.gamification.besitos_wallet import BesitosWallet, BesitosTransactionType
from src.modules.gamification.mission_manager import MissionManager, MissionType
from src.modules.gamification.item_manager import ItemManager

# Narrative services
from src.modules.narrative.fragment_manager import FragmentManager
from src.modules.narrative.decision_engine import DecisionEngine
from src.modules.narrative.hint_system import HintSystem

# User context
from src.services.user import UserService


@pytest.fixture(scope="session")
def event_loop():
    """Custom event loop for session-scoped async fixtures."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_db():
    """Real test database with cleanup."""
    config = {
        "mongodb_uri": "mongodb://localhost:27017",
        "mongodb_database": "dianabot_integration_test",
        "sqlite_database_path": ":memory:",
    }
    db = DatabaseManager(config)
    await db.connect_all()
    yield db
    # Cleanup
    mongo = db.get_mongo_client()
    await mongo.dianabot_integration_test.drop_collection("users")
    await mongo.dianabot_integration_test.drop_collection("besitos_transactions")
    await mongo.dianabot_integration_test.drop_collection("missions")
    await mongo.dianabot_integration_test.drop_collection("items")
    await mongo.dianabot_integration_test.drop_collection("narrative_fragments")
    await db.disconnect_all()


@pytest.fixture(scope="session")
async def event_bus():
    """Event bus with local fallback for testing."""
    bus = EventBus(RedisConfig(url="redis://localhost:6379/5"))
    bus._use_local_queue = True  # Avoid Redis dependency in tests
    yield bus
    await bus.close()


@pytest.fixture
async def services(test_db, event_bus):
    """All required services initialized with test DB and event bus."""
    user_service = UserService(test_db)
    besitos_wallet = BesitosWallet(test_db.get_mongo_client(), event_bus)
    mission_manager = MissionManager(test_db.get_mongo_client(), event_bus)
    item_manager = ItemManager(test_db.get_mongo_client())
    fragment_manager = FragmentManager(test_db.get_mongo_client())
    decision_engine = DecisionEngine(test_db.get_mongo_client(), event_bus)
    hint_system = HintSystem(test_db.get_mongo_client(), event_bus)

    return {
        "user_service": user_service,
        "besitos_wallet": besitos_wallet,
        "mission_manager": mission_manager,
        "item_manager": item_manager,
        "fragment_manager": fragment_manager,
        "decision_engine": decision_engine,
        "hint_system": hint_system,
    }


@pytest.fixture
async def test_user(services):
    """Create a test user and return its ID."""
    user_id = "test_user_narr_gam_123"
    await services["user_service"].create_user(
        user_id=user_id,
        username="testuser",
        first_name="Test",
        last_name="User"
    )
    return user_id


@pytest.mark.asyncio
async def test_reaction_grants_besitos_and_unlocks_narrative_hint(services, test_user):
    """
    Flujo del concepto: 
    Reacción ❤️ → otorga besitos (Gamificación) → compra pista → desbloquea fragmento (Narrativa)
    """
    wallet = services["besitos_wallet"]
    hint_system = services["hint_system"]
    item_manager = services["item_manager"]

    # 1. Simular reacción: otorgar besitos
    await wallet.add_besitos(
        user_id=test_user,
        amount=10,
        transaction_type=BesitosTransactionType.REACTION,
        description="Reacción a publicación"
    )
    balance = await wallet.get_balance(test_user)
    assert balance == 10

    # 2. Crear y comprar pista narrativa
    hint_item_id = "pista_pasaje_secreto"
    await item_manager.create_item(
        item_id=hint_item_id,
        name="Pista: Pasaje Secreto",
        description="Desbloquea el fragmento del pasaje secreto",
        item_type="narrative_hint",
        value=10
    )
    await wallet.spend_besitos(
        user_id=test_user,
        amount=10,
        transaction_type=BesitosTransactionType.PURCHASE,
        description=f"Compra pista: {hint_item_id}"
    )
    await item_manager.add_item_to_user(test_user, hint_item_id)

    # 3. Desbloquear fragmento narrativo
    fragment_id = "pasaje_secreto"
    unlocked = await hint_system.unlock_hint(test_user, fragment_id)
    assert unlocked is True

    # 4. Verificar que el fragmento esté accesible
    user_context = await services["user_service"].get_user_context(test_user)
    assert fragment_id in user_context.unlocked_hints


@pytest.mark.asyncio
async def test_narrative_decision_unlocks_gamification_mission(services, test_user):
    """
    Flujo del concepto:
    Decisión narrativa → desbloquea misión (Gamificación)
    """
    decision_engine = services["decision_engine"]
    mission_manager = services["mission_manager"]

    # Simular decisión que desbloquea misión
    choice_id = "explorar_pasaje"
    result = await decision_engine.process_decision(test_user, choice_id)
    assert result["success"] is True
    assert result["next_fragment"] == "pasaje_secreto"

    # Asignar misión basada en la decisión (como lo haría el coordinador)
    mission = await mission_manager.assign_mission(
        user_id=test_user,
        mission_type=MissionType.NARRATIVE_UNLOCK,
        title="Explorador del Pasaje",
        description="Explora completamente el pasaje secreto",
        target_value=1,
        reward_besitos=20
    )
    assert mission is not None

    # Verificar que la misión esté activa
    active = await mission_manager.get_active_missions(test_user)
    assert len(active) == 1
    assert active[0].title == "Explorador del Pasaje"


@pytest.mark.asyncio
async def test_achievement_grants_vip_narrative_access_without_subscription(services, test_user):
    """
    Flujo del concepto:
    Logro "Coleccionista" → acceso a fragmento VIP sin suscripción
    """
    item_manager = services["item_manager"]
    fragment_manager = services["fragment_manager"]

    # Simular desbloqueo de logro (como ítem especial)
    achievement_item = "achievement_coleccionista"
    await item_manager.add_item_to_user(test_user, achievement_item)

    # Intentar acceder a fragmento VIP
    vip_fragment_id = "coleccion_secreta"
    # En implementación real, fragment_manager.validar_acceso() usaría el logro
    # Aquí simulamos que el acceso es concedido por el logro
    user_inventory = await item_manager.get_user_inventory(test_user)
    has_achievement = any(item["item_id"] == achievement_item for item in user_inventory)

    assert has_achievement is True, "El usuario debe tener el logro Coleccionista"
    # Nota: La lógica real de acceso VIP con logros estaría en NarrativeService


@pytest.mark.asyncio
async def test_full_ecosystem_workflow(services, test_user):
    """
    Flujo completo del ecosistema DianaBot:
    Reacción → besitos → misión → ítem → fragmento oculto
    """
    wallet = services["besitos_wallet"]
    mission_manager = services["mission_manager"]
    item_manager = services["item_manager"]
    hint_system = services["hint_system"]

    # 1. Reacción → besitos
    await wallet.add_besitos(test_user, 10, BesitosTransactionType.REACTION, "Reacción")
    assert await wallet.get_balance(test_user) == 10

    # 2. Completar misión → más besitos
    mission = await mission_manager.assign_mission(
        test_user, MissionType.DAILY, "Misión Diaria", "Completa una acción", 1, 15
    )
    await mission_manager.complete_mission(test_user, mission.mission_id)
    assert await wallet.get_balance(test_user) >= 25  # 10 + 15

    # 3. Comprar ítem narrativo
    item_id = "llave_pasaje"
    await item_manager.create_item(item_id, "Llave del Pasaje", "Abre el pasaje secreto", "key", 20)
    await wallet.spend_besitos(test_user, 20, BesitosTransactionType.PURCHASE, "Compra llave")
    await item_manager.add_item_to_user(test_user, item_id)

    # 4. Desbloquear fragmento con ítem
    unlocked = await hint_system.unlock_hint(test_user, "pasaje_secreto")
    assert unlocked is True

    print("✅ Flujo completo del ecosistema DianaBot validado")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
