# 📂 Estructura del Proyecto — {{NOMBRE_DEL_PROYECTO}}

## Organización de Directorios

```
src/
├── features/          # Features por dominio (auth, cart, admin)
│   └── {feature}/
│       ├── components/  # Componentes UI
│       ├── hooks/       # Hooks personalizados
│       ├── services/    # Lógica de negocio
│       ├── models/      # Tipos y validaciones
│       └── utils/       # Utilidades específicas del feature
├── shared/            # Código reutilizable entre features
│   ├── components/    # Componentes globales (Button, Modal)
│   ├── hooks/         # Hooks globales (useApi, useAuth)
│   └── utils/         # Utilidades globales (formatters, validators)
├── core/              # Infraestructura central
│   ├── config/        # Configuración (env, API endpoints)
│   ├── services/      # Servicios globales (API client, auth)
│   └── types/         # Tipos globales
├── assets/            # Imágenes, íconos, fuentes
└── tests/             # Pruebas (unit, integration, e2e)
```

## Convenciones de Nomenclatura

- **Archivos**: PascalCase para componentes (`LoginForm.tsx`), camelCase para utilidades (`formatDate.ts`).
- **Variables**: camelCase (`userProfile`, `isValidEmail`).
- **Constantes**: UPPER_SNAKE_CASE (`MAX_RETRY_ATTEMPTS`).
- **Hooks**: Prefijo `use` (`useAuth`, `useCart`).

## Estilo de Código
- **Indentación**: 2 espacios.
- **Comillas**: Comillas simples.
- **Punto y coma**: No usar.
- **Console.log**: Prohibido en código de producción (usar logger).

## Testing (TDD Enforced)
- **Unit Tests**: Cobertura mínima 80% en modelos y servicios. **Prueba primero, código después.**
- **Integration Tests**: Probar flujos completos con mocks reales.
- **E2E Tests**: Probar 3 flujos críticos de usuario (registro, compra, login).
- **Ubicación**: `tests/unit/`, `tests/integration/`, `tests/e2e/`.
- **Naming**: Archivos de prueba terminan en `.test.ts` o `.spec.ts`, ubicados junto al código o en `__tests__/`.

## Documentación
- **JSDoc**: Obligatorio en funciones públicas y hooks.
- **README.md**: En cada feature con propósito, props, y ejemplos.
- **CHANGELOG.md**: Actualizado en cada release.
