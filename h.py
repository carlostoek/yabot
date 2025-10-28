## 🐍 SCRIPT COMPLETO: `qwen-spec-init.py`
#!/usr/bin/env python3
"""
qwen-spec-init.py — Inicializador de Estructura Spec-Driven para Qwen Code (con soporte TDD)

Ejecuta este script en la raíz de tu proyecto para generar toda la estructura
y archivos base necesarios para el flujo spec-driven con Qwen Code, incluyendo enfoque TDD.

Genera:
  .qwen/
    ├── steering/          → Documentos de dirección base
    ├── templates/         → Templates de requisitos, diseño, tareas (TDD)
    ├── specs/             → Directorio vacío para nuevas especificaciones
    ├── task/              → Para contextos de tareas individuales
    └── commands/          → Prompts de los comandos principales

Uso:
    python qwen-spec-init.py [--force]  # --force sobrescribe archivos existentes
"""

import os
import argparse
from pathlib import Path

def ensure_dir(path):
    """Crea directorio si no existe."""
    Path(path).mkdir(parents=True, exist_ok=True)

def write_file_if_not_exists(filepath, content, force=False):
    """Escribe archivo si no existe, o si force=True."""
    path = Path(filepath)
    if path.exists() and not force:
        print(f"⚠️  {filepath} ya existe. Usa --force para sobrescribir.")
        return False
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content.strip() + "\n")
    print(f"✅ Creado: {filepath}")
    return True

# ==============================================================================
# TEMPLATES COMPLETOS — LISTOS PARA USAR SIN ERRORES
# ==============================================================================

# -----------------------------------------------------------------------------
# STEERING DOCUMENTS
# -----------------------------------------------------------------------------

PRODUCT_MD = """
# 🎯 Visión del Producto — {{NOMBRE_DEL_PROYECTO}}

## Propósito Principal
[¿Qué problema resuelve este producto? ¿Cuál es su razón de ser?]

> **Ejemplo**:  
> _“Permitir a pequeñas empresas vender productos online sin necesidad de conocimientos técnicos.”_

## Usuarios Clave
- **Primarios**: [ej: “Dueños de tiendas pequeñas”]
- **Secundarios**: [ej: “Compradores, administradores de plataforma”]

## Objetivos de Negocio
1. [Objetivo 1: ej: “Aumentar conversiones en un 20% en 6 meses”]
2. [Objetivo 2: ej: “Reducir soporte técnico en un 30% con mejor UX”]
3. [Objetivo 3: ej: “Lanzar integración con 3 nuevos marketplaces”]

## Métricas de Éxito
- [Métrica 1: ej: “Tasa de conversión > 5%”]
- [Métrica 2: ej: “Tiempo de carga < 2s”]
- [Métrica 3: ej: “NPS > 70”]

## Features Clave Actuales
- [Feature 1: ej: “Catálogo con búsqueda y filtros”]
- [Feature 2: ej: “Checkout en 1 paso”]
- [Feature 3: ej: “Panel de administración con analytics”]

## Roadmap (Opcional)
- [Q3 2024: Integración con WhatsApp]
- [Q4 2024: Soporte multi-idioma]
"""

TECH_MD = """
# ⚙️ Estándares Técnicos — {{NOMBRE_DEL_PROYECTO}}

## Stack Tecnológico

### Frontend
- Framework: [ej: React 18 + TypeScript]
- UI Library: [ej: Tailwind CSS + Headless UI]
- State Management: [ej: Zustand]
- Routing: [ej: React Router v6]

### Backend
- Lenguaje: [ej: Node.js 18]
- Framework: [ej: Express.js]
- Base de Datos: [ej: PostgreSQL + Prisma ORM]
- Cache: [ej: Redis]

### Herramientas
- Build: [ej: Vite]
- Testing: [ej: Jest (unit), Playwright (E2E)]
- Linting: [ej: ESLint + Prettier]
- CI/CD: [ej: GitHub Actions]
- Contenedores: [ej: Docker + Docker Compose]

## Decisiones Técnicas Clave
- **Autenticación**: JWT con refresh tokens.
- **Manejo de Errores**: Código de error estandarizado + logging estructurado.
- **Internacionalización**: i18next con archivos JSON por idioma.
- **Performance**: Lazy loading en rutas, compresión Brotli.

## Restricciones y Políticas
- **Seguridad**: Todo password hasheado con bcrypt, CORS estricto, sanitización de inputs.
- **Rendimiento**: Máximo 2s de carga en mobile 3G.
- **Compatibilidad**: Soporte para Chrome, Firefox, Safari (últimas 2 versiones).
- **Dependencias**: Solo librerías auditadas y con > 10k downloads/semana en npm.

## Servicios Externos
- **Pagos**: Stripe
- **Email**: SendGrid
- **Mapas**: Google Maps API
- **Analytics**: Mixpanel
"""

STRUCTURE_MD = """
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
"""

# -----------------------------------------------------------------------------
# TEMPLATES DE FLUJO (CON ENFOQUE TDD)
# -----------------------------------------------------------------------------

REQUIREMENTS_TEMPLATE = """
# 📄 Documento de Requisitos — {{NOMBRE_DEL_FEATURE}}

> **Generado por el flujo spec-driven — Fase 1 de 4**  
> *No avanzar sin aprobación explícita del usuario.*

## 📌 Introducción

_Breve descripción del propósito de la funcionalidad, su valor para el usuario o negocio, y contexto general._

## 🧭 Alineación con la Visión del Producto

_Explica cómo este feature contribuye a los objetivos estratégicos del producto (según `steering/product.md`)._

## ⚙️ Requisitos Funcionales

### 🧩 Requisito 1

**Historia de Usuario**:  
> Como **[rol]**, quiero **[acción concreta]**, para **[beneficio medible]**.

**Criterios de Aceptación (Formato EARS — Listos para convertir en pruebas TDD)**:
1. `CUANDO` [evento disparador], `ENTONCES` el sistema `DEBE` [comportamiento esperado].
2. `SI` [condición previa], `ENTONCES` el sistema `DEBE` [comportamiento esperado].
3. `CUANDO` [evento] `Y` [condición adicional], `ENTONCES` el sistema `DEBE` [comportamiento esperado].

**Restricciones Técnicas / Reutilización**:
> _Ej: “Debe integrarse con el servicio Auth existente en `/services/auth.py`. No crear nuevo hashing, usar `bcrypt_hash`.”_

## 🚫 Casos Límite y Manejo de Errores

_Especifica comportamientos en situaciones excepcionales o inválidas — cada uno debe ser cubierto por una prueba._

> **Ejemplos**:
> - `CUANDO` el usuario ingresa un email ya registrado, `ENTONCES` el sistema `DEBE` mostrar el mensaje: “Este email ya está en uso.”
> - `SI` la contraseña tiene menos de 8 caracteres, `ENTONCES` el sistema `DEBE` rechazar el registro y mostrar error específico.

## 📊 Requisitos No Funcionales

### ⚡ Rendimiento
- Tiempo máximo de respuesta: [ej: < 500ms para registro].
- Capacidad de concurrencia: [ej: soportar 1000 solicitudes/min].

### 🔐 Seguridad
- Todos los passwords deben almacenarse hasheados (usar bcrypt).
- Validar CSRF en formularios de registro/login.
- Sesiones deben expirar tras 30 minutos de inactividad.

### 🧱 Confiabilidad
- El sistema debe registrar errores críticos en `logs/auth-errors.log`.
- Debe existir reintento automático (hasta 3 veces) en fallos de conexión a DB.

### 👥 Usabilidad
- Mensajes de error deben ser claros y en lenguaje natural.
- Formulario debe tener validación en tiempo real (frontend).
- Accesible según estándar WCAG 2.1 AA.

## 🧩 Referencias Cruzadas

- **Documento de Producto**: `steering/product.md` → [breve resumen de alineación]
- **Estándares Técnicos**: `steering/tech.md` → [ej: “Cumple con política de hashing definida en Sección 3.2”]
- **Estructura del Proyecto**: `steering/structure.md` → [ej: “Componentes ubicados en `/features/auth/` según convención”]

## ✅ Checklist de Validación (Para Agente o Autovalidación)

Antes de presentar al usuario, verificar:

- [ ] Todas las historias de usuario siguen el formato “Como... quiero... para...”.
- [ ] Todos los criterios de aceptación usan formato EARS (`WHEN/IF/THEN`).
- [ ] Cada requisito incluye restricciones técnicas o referencias a código reutilizable.
- [ ] Se especifican al menos 3 casos límite.
- [ ] Todos los requisitos no funcionales están completos y medibles.
- [ ] Existe alineación explícita con documentos de dirección (`product.md`, `tech.md`, `structure.md`).

## 📝 Notas para el Usuario

> “Por favor, revisa este documento detenidamente. Asegúrate de que:  
> - Las historias reflejan lo que realmente necesitas.  
> - Los criterios de aceptación son claros y verificables — **cada uno debe poder convertirse en una prueba TDD**.  
> - Los casos límite cubren los escenarios críticos.  
>   
> **Responde ‘aprobado’ solo si todo está correcto. Si hay cambios, indícalos específicamente.**”

## ✅ Estado del Flujo

```text
[ ] Requisitos aprobados → Esperando aprobación del usuario
```
"""

DESIGN_TEMPLATE = """
# 🏗️ Documento de Diseño — {{NOMBRE_DEL_FEATURE}}

> **Generado por el flujo spec-driven — Fase 2 de 4**  
> *Basado en los requisitos aprobados en `requirements.md`.*  
> *No avanzar sin aprobación explícita del usuario.*

## 📌 Resumen Ejecutivo

_Descripción de alto nivel de la funcionalidad, su rol dentro del sistema general, y cómo satisface los requisitos definidos en la Fase 1._

## 🧭 Alineación con Documentos de Dirección

### ⚙️ Estándares Técnicos (`tech.md`)
_Cómo este diseño sigue los patrones, tecnologías y convenciones técnicas documentadas._

### 📂 Estructura del Proyecto (`structure.md`)
_Cómo se organizarán los archivos y componentes según las convenciones del proyecto._

## 🔍 Análisis de Reutilización de Código

_Lista de componentes, utilidades o servicios existentes que se aprovecharán, extenderán o integrarán._

### ✅ Componentes/Utilidades a Reutilizar
- **`validateEmail` (utils/validators.js)**:  
  _Se usará para validar formato de email en registro. Ya implementado y testeado._
- **`bcryptHash` (utils/security.js)**:  
  _Se extenderá para incluir salting automático, siguiendo estándar de seguridad actual._
- **`SessionService` (services/session.js)**:  
  _Se integrará directamente para crear y gestionar sesiones post-login._

### 🔄 Puntos de Integración
- **API Gateway (`/api/auth`)**:  
  _Las nuevas rutas se registrarán aquí, siguiendo convención de versionado v1._
- **Base de Datos (`users` collection)**:  
  _Se extenderá el esquema existente con campos `password_hash` y `email_verified`._
- **Servicio de Notificaciones**:  
  _Se llamará para enviar emails de bienvenida tras registro exitoso._

## 🧩 Decisiones de Diseño Clave

_Cada decisión debe incluir: problema, alternativas consideradas, elección final y justificación._

> **Ejemplo**:
> - **Problema**: ¿Dónde manejar la lógica de validación de contraseña?
> - **Alternativas**:  
>   a) En el controlador (rápido, pero rompe SRP)  
>   b) En un servicio dedicado (reutilizable, testable)  
>   c) En middleware (genérico, pero menos específico)  
> - **Elección**: Servicio dedicado (`PasswordService`)  
> - **Justificación**: Permite reutilización en otros features (ej: cambio de contraseña), facilita testing unitario, y cumple con principio de responsabilidad única.

## 🏛️ Arquitectura General

_Descripción de patrones arquitectónicos, flujos de datos y dependencias entre componentes._

```mermaid
graph TD
    A[AuthController] --> B[AuthService]
    B --> C[UserModel]
    B --> D[PasswordService]
    D --> E[bcryptHash]
    B --> F[SessionService]
    F --> G[RedisStore]
```

> **Leyenda**:  
> - `AuthController`: Recibe peticiones HTTP.  
> - `AuthService`: Orquesta lógica de negocio.  
> - `UserModel`: Acceso a datos de usuario.  
> - `PasswordService`: Hashing y verificación segura.  
> - `SessionService`: Gestión de sesiones en Redis.

## 🧱 Componentes e Interfaces

Cada componente debe definir: propósito, interfaces públicas, dependencias y reutilización.

---

### 🧩 Componente 1: `AuthService`

- **Propósito**:  
  _Orquestar el flujo de registro/login, validar credenciales, y gestionar sesiones._

- **Interfaces Públicas**:  
  ```ts
  register(userData: { email: string, password: string }): Promise<User>
  login(credentials: { email: string, password: string }): Promise<Session>
  ```

- **Dependencias**:  
  - `UserModel` (para persistencia)  
  - `PasswordService` (para hashing/verificación)  
  - `SessionService` (para crear sesión)

- **Reutiliza**:  
  - `validateEmail` desde `utils/validators`  
  - `logError` desde `utils/logger`

---

### 🧩 Componente 2: `PasswordService`

- **Propósito**:  
  _Gestionar hashing seguro de contraseñas y verificación._

- **Interfaces Públicas**:  
  ```ts
  hash(password: string): Promise<string>
  verify(password: string, hash: string): Promise<boolean>
  ```

- **Dependencias**:  
  - Librería `bcrypt` (ya en package.json)

- **Reutiliza**:  
  - Configuración de rounds desde `config/security.js`

## 📊 Modelos de Datos

_Definición clara de estructuras de datos, con tipos y restricciones._

### 🧾 Modelo: `User`

```ts
interface User {
  id: string;           // UUID v4
  email: string;        // Único, validado con RFC 5322
  password_hash: string; // bcrypt hash, min 60 chars
  created_at: Date;     // ISO 8601
  email_verified: boolean; // default: false
}
```

### 🧾 Modelo: `Session`

```ts
interface Session {
  token: string;        // JWT firmado
  user_id: string;      // referencia a User.id
  expires_at: Date;     // +30min desde creación
  ip_address: string;   // para auditoría
}
```

## 🚫 Manejo de Errores

_Especificación de escenarios de error, cómo se manejan y qué ve el usuario._

### 🚨 Escenarios Clave

1. **Email ya registrado**  
   - **Manejo**: Devolver error 409 Conflict con código `EMAIL_EXISTS`.  
   - **Impacto Usuario**: Mensaje: “Este email ya está registrado. ¿Olvidaste tu contraseña?”

2. **Contraseña incorrecta**  
   - **Manejo**: Devolver error 401 Unauthorized con código `INVALID_CREDENTIALS`.  
   - **Impacto Usuario**: Mensaje: “Email o contraseña incorrectos.”

3. **Error de conexión a DB**  
   - **Manejo**: Reintentar hasta 3 veces, luego loggear y devolver 503 Service Unavailable.  
   - **Impacto Usuario**: Mensaje: “Servicio temporalmente no disponible. Inténtalo más tarde.”

## 🧪 Estrategia de Pruebas (TDD Enforced)

_Cómo se validará que el diseño funciona correctamente — **prueba primero, código después**._

### ✅ Pruebas Unitarias
- **Enfoque**: Mockear dependencias, probar lógica de cada componente en aislamiento.
- **Componentes Clave**:  
  - `PasswordService.hash/verify` → Validar que genera hashes válidos y verifica correctamente.  
  - `AuthService.register` → Validar que rechaza emails inválidos o duplicados.

### 🔗 Pruebas de Integración
- **Enfoque**: Probar flujos completos con servicios reales (DB, Redis en modo test).
- **Flujos Clave**:  
  - Registro → Login → Obtención de perfil → Cierre de sesión.  
  - Registro con email duplicado → debe fallar elegantemente.

### 🌐 Pruebas End-to-End (E2E)
- **Enfoque**: Simular usuario real con navegador o cliente HTTP.
- **Escenarios Clave**:  
  - Usuario nuevo se registra, recibe email, inicia sesión y accede a su perfil.  
  - Usuario intenta login con credenciales erróneas → ve mensaje de error claro.

## 🔄 Alternativas Consideradas (Opcional pero Recomendado)

_Documentar brevemente opciones descartadas y por qué._

> **Ejemplo**:  
> - **JWT vs Sesiones en DB**: Se eligió JWT por escalabilidad y simplicidad, aunque sesiones en DB ofrecen mejor control de revocación.  
> - **OAuth2 vs Auth básica**: Se descartó OAuth2 por complejidad innecesaria para MVP.

## ✅ Checklist de Validación (Para Agente o Autovalidación)

Antes de presentar al usuario, verificar:

- [ ] El diseño cubre **todos** los requisitos funcionales y no funcionales de `requirements.md`.
- [ ] Todos los componentes definen claramente interfaces, dependencias y reutilización.
- [ ] Los diagramas Mermaid reflejan fielmente las dependencias y flujos.
- [ ] Los modelos de datos incluyen tipos, restricciones y ejemplos.
- [ ] Cada escenario de error tiene manejo definido e impacto de usuario claro.
- [ ] La estrategia de pruebas cubre unitario, integración y E2E — **con enfoque TDD**.
- [ ] Existe alineación explícita con `tech.md` y `structure.md`.
- [ ] Se documentaron decisiones clave y alternativas consideradas.

## 📝 Notas para el Usuario

> “Por favor, revisa este diseño detenidamente. Asegúrate de que:  
> - La arquitectura es técnicamente sólida y escalable.  
> - Se reutiliza adecuadamente el código existente.  
> - Los componentes y modelos están claramente definidos.  
> - Los escenarios de error están bien manejados.  
> - **La estrategia de pruebas permite implementar con TDD (prueba primero, código después).**  
>   
> **Responde ‘aprobado’ solo si todo está correcto. Si hay cambios, indícalos específicamente.**”

## ✅ Estado del Flujo

```text
[ ] Diseño aprobado → Esperando aprobación del usuario
```
"""

TASKS_TEMPLATE = """
# 📋 Plan de Implementación — {{NOMBRE_DEL_FEATURE}}

> **Generado por el flujo spec-driven — Fase 3 de 4**  
> *Basado en el diseño aprobado en `design.md` y los requisitos en `requirements.md`.*  
> *Cada tarea debe ser ATÓMICA, VALIDADA y APROBADA antes de ejecutar.*  
> *NO avanzar sin aprobación explícita del usuario.*  
> **PRINCIPIO TDD OBLIGATORIO: Toda tarea de implementación DEBE estar precedida por una tarea de prueba que falle.**

## 📌 Resumen de Implementación

_Breve descripción del enfoque de implementación, priorizando **TDD estricto**: cada comportamiento se inicia con una prueba fallida, seguida de la implementación mínima para pasarla, y luego refactor._

> **Ejemplo**:  
> _“La implementación seguirá el ciclo TDD: para cada requisito, primero se escribirá una prueba fallida que describa el comportamiento esperado, luego se implementará el código mínimo para pasarla, y finalmente se refactorizará si es necesario. Cada tarea toca máximo 3 archivos (prueba + implementación + utilidad), es ejecutable en <30 min, y se enfoca en un único comportamiento verificable.”_

## 🧭 Cumplimiento de Documentos de Dirección

_Cómo las tareas siguen las convenciones de `structure.md` y patrones de `tech.md`, con énfasis en **pruebas unitarias, aislamiento y cobertura**._

> **Ejemplo**:  
> _“Todas las tareas respetan la estructura de carpetas por capa (`/models`, `/services`, `/api`). Las pruebas se ubican en `__tests__/` o `*.test.ts` junto a su implementación. Se siguen patrones de mocking y aislamiento definidos en tech.md Sección 6.1.”_

## ⚠️ REQUISITOS DE ATOMICIDAD + TDD (NO NEGOCIABLES)

Cada tarea **DEBE** cumplir:

- **Alcance de Archivo**: Máximo **1-3 archivos relacionados** (ej: `feature.test.ts` + `feature.ts` + `utils.ts`).
- **Tiempo Estimado**: **15-30 minutos** por tarea (incluye escribir prueba + implementación + refactor).
- **Propósito Único**: **Un solo comportamiento comprobable** por tarea.
- **Archivos Específicos**: **Ruta exacta** de archivos a crear/modificar — **SIEMPRE incluir archivo de prueba**.
- **Amigable para Agentes**: Entrada/salida clara, **sin cambio de contexto**.
- **Evitar términos vagos**: No usar “sistema”, “integración completa”, “refactor global”.
- **PRINCIPIO TDD**: **Ninguna tarea de implementación sin su correspondiente tarea de prueba previa.**

## 📝 FORMATO DE TAREAS (SEGUIR EXACTAMENTE)

```md
- [ ] {{NÚMERO_SECUENCIAL}}. {{TÍTULO CLARO Y ESPECÍFICO}}
  - **Archivo(s)**: `ruta/exacta/al/archivo.ext`, `ruta/exacta/al/archivo.test.ext`
  - **Descripción**: [Qué se hará, en 1-2 frases — especificar si es prueba o implementación]
  - **Detalles de Implementación**:
    - [ ] Punto 1: acción concreta
    - [ ] Punto 2: dependencia o validación
  - **Propósito**: [Resultado verificable — para pruebas: “Definir comportamiento esperado”, para impl: “Hacer pasar prueba X”]
  - _Requisitos: X.Y, Z.A_  ← Referencia a `requirements.md` (para pruebas: vincular a criterio EARS)
  - _Reutiliza: ruta/a/componente.ext, ruta/a/util.ext_ ← Código existente (especialmente test utils, mocks, fixtures)
```

## ✅ EJEMPLOS DE TAREAS ATÓMICAS (TDD)

### ❌ MALAS (Violan TDD o son demasiado amplias)

- “Implementar sistema de autenticación” → Afecta muchos archivos, no sigue TDD.
- “Añadir gestión de usuarios” → Alcance indefinido, sin prueba asociada.
- “Escribir pruebas para el modelo” → Demasiado vago, no es atómico.

### ✅ BUENAS (Atómicas y TDD-compliant)

- “Escribir prueba fallida para validación de email en `utils/__tests__/validateEmail.test.ts`”  
  → Propósito: “Definir comportamiento: email inválido debe retornar false”  
  → _Requisitos: 2.1 (CUANDO email inválido, ENTONCES rechazar)_

- “Implementar validateEmail en `utils/validateEmail.ts` para hacer pasar prueba”  
  → Propósito: “Hacer pasar prueba de email inválido”  
  → _Requisitos: 2.1_  
  → _Depende de: Tarea 3 (prueba)_

- “Añadir prueba para hashing de password en `services/__tests__/PasswordService.test.ts`”  
  → Propósito: “Verificar que hash no sea igual a texto plano”  
  → _Requisitos: 3.2_

- “Implementar método hash en `services/PasswordService.ts`”  
  → Propósito: “Hacer pasar prueba de hashing”  
  → _Requisitos: 3.2_  
  → _Depende de: Tarea 5 (prueba)_

## 🧩 LISTA DE TAREAS (GENERADA AUTOMÁTICAMENTE)

> **NOTA PARA EL MODELO/AGENTE**:  
> - Sigue el formato exacto.  
> - Numera secuencialmente (1, 2, 3...).  
> - **Cada tarea de implementación DEBE tener una tarea de prueba ANTES en la lista.**  
> - Si una tarea es demasiado grande, divídela en pares prueba + implementación.  
> - Siempre referencia requisitos y código reutilizable.  
> - **Etiqueta claramente si la tarea es de prueba o de implementación.**

---

- [ ] 1. Escribir prueba fallida para interfaz de usuario de login en `components/__tests__/LoginForm.test.tsx`
  - **Archivo(s)**: `components/__tests__/LoginForm.test.tsx`
  - **Descripción**: Definir comportamiento: formulario debe mostrar error si email es inválido.
  - **Detalles de Implementación**:
    - [ ] Mockear validación de email
    - [ ] Simular submit con email inválido
    - [ ] Verificar que se muestra mensaje de error
  - **Propósito**: Definir comportamiento esperado para requisito 1.2.
  - _Requisitos: 1.2 (CUANDO email inválido, ENTONCES mostrar error)_
  - _Reutiliza: tests/mocks/validators.ts, tests/utils/renderComponent.tsx_

- [ ] 2. Implementar validación en LoginForm en `components/LoginForm.tsx` para hacer pasar prueba
  - **Archivo(s)**: `components/LoginForm.tsx`
  - **Descripción**: Añadir lógica de validación de email en submit.
  - **Detalles de Implementación**:
    - [ ] Importar `validateEmail` de `utils/validators.ts`
    - [ ] Añadir estado de error
    - [ ] Mostrar mensaje si validación falla
  - **Propósito**: Hacer pasar prueba de validación de email (Tarea 1).
  - _Requisitos: 1.2_
  - _Reutiliza: utils/validators.ts_
  - _Depende de: Tarea 1_

- [ ] 3. Escribir prueba para servicio de registro en `services/__tests__/AuthService.test.ts`
  - **Archivo(s)**: `services/__tests__/AuthService.test.ts`
  - **Descripción**: Verificar que register lanza error si email ya existe.
  - **Detalles de Implementación**:
    - [ ] Mockear UserModel para simular email duplicado
    - [ ] Verificar que se lanza error con código `EMAIL_EXISTS`
  - **Propósito**: Definir comportamiento para requisito 2.3.
  - _Requisitos: 2.3 (CUANDO email duplicado, ENTONCES error)_
  - _Reutiliza: tests/mocks/UserModelMock.ts, tests/utils/errorCodes.ts_

- [ ] 4. Implementar manejo de email duplicado en AuthService en `services/AuthService.ts`
  - **Archivo(s)**: `services/AuthService.ts`
  - **Descripción**: Añadir verificación de email existente antes de crear usuario.
  - **Detalles de Implementación**:
    - [ ] Llamar a `UserModel.findByEmail`
    - [ ] Lanzar `AppError` con código `EMAIL_EXISTS` si existe
  - **Propósito**: Hacer pasar prueba de email duplicado (Tarea 3).
  - _Requisitos: 2.3_
  - _Reutiliza: models/UserModel.ts, utils/AppError.ts_
  - _Depende de: Tarea 3_

- [ ] 5. Escribir prueba E2E para flujo de registro en `tests/e2e/registerFlow.test.ts`
  - **Archivo(s)**: `tests/e2e/registerFlow.test.ts`
  - **Descripción**: Simular flujo completo: abrir formulario, ingresar datos válidos, submit, redirección.
  - **Detalles de Implementación**:
    - [ ] Usar Playwright para simular usuario real
    - [ ] Verificar redirección a /dashboard tras registro exitoso
  - **Propósito**: Validar experiencia de usuario final para requisito 1.1.
  - _Requisitos: 1.1_
  - _Reutiliza: tests/helpers/pageObjects.ts, tests/fixtures/userData.ts_

- [ ] 6. Implementar redirección post-registro en controlador (si no existe)
  - **Archivo(s)**: `controllers/AuthController.ts`
  - **Descripción**: Tras registro exitoso, redirigir a /dashboard.
  - **Detalles de Implementación**:
    - [ ] Añadir `res.redirect('/dashboard')` tras `userService.register()`
  - **Propósito**: Hacer pasar prueba E2E de redirección (Tarea 5).
  - _Requisitos: 1.1_
  - _Depende de: Tarea 5_

## ✅ CHECKLIST DE VALIDACIÓN (PARA AGENTE O AUTOVALIDACIÓN)

Antes de presentar al usuario, verificar **cada tarea**:

- [ ] Tiene número secuencial único.
- [ ] Toca máximo 3 archivos (siempre incluye archivo de prueba si aplica).
- [ ] Tiempo estimado < 30 min (incluye prueba + impl).
- [ ] Propósito único y verificable.
- [ ] Rutas de archivo exactas y existentes (o a crear).
- [ ] Referencia a requisitos específicos (para pruebas: criterios EARS).
- [ ] Referencia a código reutilizable (especialmente test utils, mocks).
- [ ] **Toda tarea de implementación tiene su tarea de prueba ANTES en la lista.**
- [ ] No contiene términos vagos (“sistema”, “completo”, “integración”).
- [ ] Las tareas de prueba definen claramente el comportamiento esperado.

## 📝 NOTAS PARA EL USUARIO

> “Por favor, revisa esta lista de tareas detenidamente. Asegúrate de que:  
> - **Cada comportamiento comienza con una prueba.**  
> - **Ninguna línea de producción se escribe sin una prueba fallida primero.**  
> - Las referencias a requisitos y código existente son **correctas**.  
> - No hay tareas demasiado amplias o ambiguas.  
>   
> **Responde ‘aprobado’ solo si todo está correcto. Si hay cambios, indícalos específicamente.**  
>   
> **Después de aprobar, dime si deseas que genere comandos individuales para cada tarea (ej: `/task-{feature}-1`, `/task-{feature}-2`, etc.).**”

## ✅ ESTADO DEL FLUJO

```text
[ ] Tareas aprobadas → Esperando aprobación del usuario
[ ] Comandos generados → Pendiente de solicitud del usuario
```
"""

# -----------------------------------------------------------------------------
# COMMANDS (PROMPTS PARA GEMINI CLI FORK)
# -----------------------------------------------------------------------------

SPEC_STEERING_SETUP_MD = """
# 🧭 Comando de Configuración de Documentos de Dirección

> **Comando sugerido**: \`/spec-steering-setup\`

## 📌 Propósito

Este comando configura los **documentos de dirección del proyecto** — archivos persistentes que definen:

- **Visión del producto** → ¿Para qué existe este proyecto? ¿Quién lo usa? ¿Qué problema resuelve?
- **Estándares técnicos** → ¿Qué tecnologías, patrones y restricciones técnicas se usan?
- **Estructura del proyecto** → ¿Cómo se organizan los archivos, componentes y convenciones?

Estos documentos serán **referenciados automáticamente** en todas las fases del flujo spec-driven (requisitos, diseño, tareas) para garantizar alineación, calidad y consistencia.

## 🔄 Proceso Completo

1. 🔍 Verificar Documentos Existentes
2. 🧠 Analizar el Proyecto (Inferencia Automática)
3. 📊 Presentar Inferencias al Usuario
4. ❓ Recopilar Información Faltante
5. 📄 Generar Documentos de Dirección
6. ✅ Revisión y Confirmación Final

## ⚠️ Notas Importantes

- **Steering documents are persistent** - they will be referenced in all future spec commands
- **Keep documents focused** - each should cover its specific domain
- **Update regularly** - steering docs should evolve with the project
- **Never include sensitive data** - no passwords, API keys, or credentials
"""

SPEC_CREATE_MD = """
# 🧭 Flujo de Creación de Especificación — Inicio del Proceso

> **Comando de activación sugerido**:  
> \`/spec-create <nombre-del-feature> [descripción-opcional]\`

## 🎯 Filosofía del Flujo

Eres un **agente especializado en desarrollo guiado por especificaciones (spec-driven development)**. Tu rol es guiar al usuario a través de un proceso estructurado, secuencial y validado para construir nuevas funcionalidades con calidad, trazabilidad y alineación técnica.

## 🔄 Secuencia Completa del Flujo (CRÍTICO — SEGUIR AL PIE DE LA LETRA)

**Fase 1 → Requisitos**  
 → Validación → Aprobación  
**Fase 2 → Diseño**  
 → Validación → Aprobación  
**Fase 3 → Tareas**  
 → Validación → Análisis de dependencias → Aprobación → Generación de comandos  
**Fase 4 → Implementación**

## 🚫 REGLAS CRÍTICAS

- **Solo crear UNA spec a la vez**
- **Siempre usar kebab-case para nombres de features**
- **MANDATORIO**: Siempre analizar código existente antes de empezar cualquier fase
- **Seguir estructuras exactas de plantillas**
- **No proceder sin aprobación explícita del usuario entre fases**
- **No saltar fases**

## ✅ Criterios de Éxito

Una especificación completada con éxito incluye:
- [x] Requisitos completos con historias y criterios de aceptación
- [x] Diseño técnico detallado con arquitectura y componentes
- [x] Lista de tareas atómicas con referencias a requisitos
- [x] Todas las fases explícitamente aprobadas por el usuario
- [x] Comandos de tarea generados (si el usuario elige)
- [x] Lista lista para la fase de implementación
"""

# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Inicializa la estructura spec-driven para Qwen Code con soporte TDD.")
    parser.add_argument('--force', action='store_true', help="Sobrescribe archivos existentes")
    args = parser.parse_args()

    print("🚀 Inicializando estructura spec-driven para Qwen Code (con soporte TDD)...")

    # Base directory: .qwen/
    base_dir = Path(".qwen")

    # Crear directorios
    dirs = [
        base_dir / "steering",
        base_dir / "templates",
        base_dir / "specs",
        base_dir / "task",
        base_dir / "commands"
    ]

    for d in dirs:
        ensure_dir(d)

    # Crear archivos en steering/
    steering_files = {
        "product.md": PRODUCT_MD,
        "tech.md": TECH_MD,
        "structure.md": STRUCTURE_MD
    }

    for filename, content in steering_files.items():
        filepath = base_dir / "steering" / filename
        write_file_if_not_exists(filepath, content, args.force)

    # Crear archivos en templates/
    template_files = {
        "requirements-template.md": REQUIREMENTS_TEMPLATE,
        "design-template.md": DESIGN_TEMPLATE,
        "tasks-template.md": TASKS_TEMPLATE
    }

    for filename, content in template_files.items():
        filepath = base_dir / "templates" / filename
        write_file_if_not_exists(filepath, content, args.force)

    # Crear archivos en commands/
    command_files = {
        "spec-steering-setup.md": SPEC_STEERING_SETUP_MD,
        "spec-create.md": SPEC_CREATE_MD
    }

    for filename, content in command_files.items():
        filepath = base_dir / "commands" / filename
        write_file_if_not_exists(filepath, content, args.force)

    print("\n🎉 ¡Estructura spec-driven con soporte TDD inicializada con éxito dentro de .qwen/!")
    print("\n📁 Estructura generada:")
    print("  .qwen/")
    print("    ├── steering/       → Documentos de dirección base")
    print("    ├── templates/      → Templates de flujo (¡con enfoque TDD!)")
    print("    ├── specs/          → Para nuevas features")
    print("    ├── task/           → Contextos de tareas individuales")
    print("    └── commands/       → Prompts de comandos principales")
    print("\n📌 Próximos pasos:")
    print("1. Edita los archivos en `.qwen/steering/` para reflejar tu proyecto real.")
    print("2. Usa los prompts en `.qwen/commands/` para configurar tus comandos en el fork de Gemini CLI.")
    print("3. ¡Comienza a usar el flujo spec-driven con Qwen Code y TDD estricto!")

if __name__ == "__main__":
    main()
