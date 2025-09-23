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
