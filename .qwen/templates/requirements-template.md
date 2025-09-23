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
