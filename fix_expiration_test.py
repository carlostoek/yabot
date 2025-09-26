#!/usr/bin/env python3
\"\"\"Fix the expiration test in the integration test file\"\"\"

with open('test_real_integration_clean.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the expiration test method with correct dates to ensure expiration
old_method = '''    async def test_subscription_expiration(self):
        \"\"\"
        PRUEBA REAL: Expiración de suscripciones mejorada
        \"\"\"
        print(\"\\n⏰ Probando expiración de suscripciones...\")

        # Crear suscripción expirada usando el servicio correcto
        past_date = datetime.now(timezone.utc) - timedelta(hours=1)

        # Usar el método correcto del DatabaseManager
        subscription_data = {
            \"user_id\": self.expired_user_id,
            \"plan_type\": \"vip\",
            \"status\": \"active\",
            \"start_date\": past_date,
            \"end_date\": past_date,  # Ya expiró
            \"created_at\": past_date,
            \"updated_at\": past_date
        }

        created = await self.db_manager.create_subscription(subscription_data)
        if not created:
            print(\"❌ ERROR: No se pudo crear suscripción expirada\")
            return False

        # Verificar que el sistema detecta la expiración
        is_active = await self.subscription_service.check_subscription_status(self.expired_user_id)

        print(\"✅ Flujo de expiración funcionando\")
        print(f\"   Suscripción activa: {'❌ No' if not is_active else '✅ Sí'}\")

        return not is_active  # Debe ser False para que el test pase'''

new_method = '''    async def test_subscription_expiration(self):
        \"\"\"
        PRUEBA REAL: Expiración de suscripciones mejorada
        \"\"\"
        print(\"\\n⏰ Probando expiración de suscripciones...\")

        # Crear suscripción expirada usando el servicio correcto
        start_date = datetime.now(timezone.utc) - timedelta(days=2)  # Started 2 days ago
        end_date = datetime.now(timezone.utc) - timedelta(days=1)    # Ended 1 day ago (expired)

        # Usar el método correcto del DatabaseManager
        subscription_data = {
            \"user_id\": self.expired_user_id,
            \"plan_type\": \"vip\",
            \"status\": \"active\",  # Initially set as active but should be expired based on dates
            \"start_date\": start_date,
            \"end_date\": end_date,  # Expired yesterday
            \"created_at\": start_date,
            \"updated_at\": start_date
        }

        created = await self.db_manager.create_subscription(subscription_data)
        if not created:
            print(\"❌ ERROR: No se pudo crear suscripción expirada\")
            return False

        # Verificar que el sistema detecta la expiración
        is_active = await self.subscription_service.check_subscription_status(self.expired_user_id)

        print(\"✅ Flujo de expiración funcionando\")
        print(f\"   Suscripción activa: {'❌ No' if not is_active else '✅ Sí'}\")

        return not is_active  # Debe ser False para que el test pase'''

# Replace the old method with the new one
content = content.replace(old_method, new_method)

# Write the file back
with open('test_real_integration_clean.py', 'w', encoding='utf-8') as f:
    f.write(content)

print(\"Fixed the expiration test in test_real_integration_clean.py\")