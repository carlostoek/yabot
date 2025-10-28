# Investigación para el Desarrollo de DianaBot

## Índice
1. [Introducción](#introducción)
2. [Arquitectura General del Sistema](#arquitectura-general-del-sistema)
3. [Plataforma y Tecnologías](#plataforma-y-tecnologías)
4. [Módulo de Narrativa Inmersiva](#módulo-de-narrativa-inmersiva)
5. [Módulo de Gamificación](#módulo-de-gamificación)
6. [Módulo de Administración de Canales](#módulo-de-administración-de-canales)
7. [Integración y Flujos Cruzados](#integración-y-flujos-cruzados)
8. [Sistema de Configuración Unificada](#sistema-de-configuración-unificada)
9. [Seguridad y Escalabilidad](#seguridad-y-escalabilidad)
10. [Monetización y Roles](#monetización-y-roles)
11. [Consideraciones Finales](#consideraciones-finales)

## Introducción

DianaBot es un ecosistema integral que combina narrativa inmersiva, gamificación y administración de canales en un entorno de Telegram. Esta investigación detalla los fundamentos técnicos, arquitectónicos y de diseño necesarios para su implementación, con énfasis en un sistema de configuración centralizado que permita gestionar todos los aspectos desde una interfaz unificada.

## Arquitectura General del Sistema

### Arquitectura Propuesta: Arquitectura Hexagonal (Puerto y Adaptadores)

**Capa de Dominio**:
- Contiene la lógica de negocio central
- Define interfaces (puertos) que describen cómo interactúan los módulos entre sí
- Representa el corazón del sistema sin dependencias externas

**Capa de Aplicación**:
- Implementa casos de uso específicos
- Orquesta la interacción entre diferentes módulos
- Contiene reglas de negocio específicas de la aplicación

**Capa de Adaptadores**:
- Adaptadores de infraestructura (bases de datos, API externas)
- Adaptadores de interfaz (API REST, bot de Telegram)
- Adaptadores de presentación (panel de administración)

### Patrones de Comunicación

**Patrón de eventos (Event-Driven Architecture)**:
- Sistema de mensajería interna para comunicación entre módulos
- Publisher-Subscriber para notificar cambios en estado
- Ejemplo: Cuando un usuario completa una misión → evento emitido → sistema de narrativa actualiza estado → sistema de gamificación otorga recompensas

**API Gateway**:
- Punto único de entrada para todas las interacciones externas
- Gestión de autenticación, autorización y enrutamiento
- Balanceo de carga y protección contra abusos

### Diagrama Conceptual de Componentes

```
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway                              │
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                    Servicio de Orquestación                 │
└─────────────────────────────────────────────────────────────┘
    │              │              │              │
    ▼              ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ Narrativa   │ │ Gamificación│ │ Administración│ │ Config.   │
│ Inmersiva   │ │             │ │ de Canales  │ │ Unificada │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

## Plataforma y Tecnologías

### Lenguaje de Programación
- **Python 3.11+**: Ideal para desarrollo de bots de Telegram, con excelente soporte para frameworks web y manejo de datos complejos

### Framework Principal
- **FastAPI**: Alto rendimiento, soporte para WebSockets, documentación automática, inferencia de tipos
- **aiogram**: Framework especializado para bots de Telegram con soporte completo para todas las funcionalidades

### Base de Datos
- **PostgreSQL**: Base de datos relacional robusta para datos estructurados
- **Redis**: Almacenamiento en caché y colas de tareas
- **MongoDB**: Almacenamiento de documentos para narrativa ramificada (opcional para estructuras complejas)

### Otras Tecnologías
- **Celery**: Gestión de tareas asíncronas (recordatorios, publicaciones programadas)
- **Docker**: Contenerización para despliegue consistente
- **SQLAlchemy**: ORM para manejo de datos estructurados
- **Pydantic**: Validación de datos y serialización
- **PyYAML**: Para definición de narrativas ramificadas
- **WebSockets**: Para actualizaciones en tiempo real en el panel de administración

### Infraestructura
- **Docker Compose**: Orquestación de contenedores
- **NGINX**: Proxy inverso y balanceador de carga
- **Certbot**: Certificados SSL automáticos

## Módulo de Narrativa Inmersiva

### Sistema de Narrativa Ramificada

**Modelo de Datos**:
```
- Historia (Id, título, descripción, nivel_acceso)
  - Capítulo (Id, historia_id, título, contenido, orden)
    - Fragmento (Id, capítulo_id, contenido, tipo: texto/audio/video)
      - Decisión (Id, fragmento_id, texto_opción, consecuencia_id)
        - Consecuencia (Id, fragmento_id, tipo: estado_usuario, recompensa, desbloqueo)
```

**Estructura de Contenido**:
- Formato YAML para definición de narrativas
- Sistema de variables dinámicas basado en estado del usuario
- Referencias cruzadas entre fragmentos para reutilización de contenido

**Motor de Narrativa**:
- Sistema de estados persistentes por usuario
- Evaluador de condiciones (besitos, logros, ítems, rol VIP)
- Sistema de "memoria" para recordar decisiones anteriores
- Algoritmo de recomendación para sugerir rutas narrativas

### Persistencia de Estado
- Estado de progreso por usuario (capítulo actual, decisiones tomadas)
- Variables de contexto (relación con personajes, reputación)
- Bandas sonoras y archivos multimedia asociados

### Motores de Desbloqueo
- Desbloqueos condicionales basados en:
  - Número de besitos obtenidos
  - Logros específicos
  - Objetos en la mochila
  - Nivel de suscripción (VIP/Gratuito)
  - Progreso narrativo previo

## Módulo de Gamificación

### Economía Interna: "Besitos"

**Modelo de Economía**:
- Moneda virtual no convertible a dinero real
- Sistema de acuñación controlada para prevenir inflación
- Reglas de circulación y redistribución

**Fuentes de Ganancia**:
- Completar misiones diarias/semanales
- Participar en trivias
- Reacciones a contenido
- Regalos diarios (bonificación de fidelidad)
- Eventos especiales

**Usos**:
- Desbloquear contenido narrativo
- Comprar ítems en la tienda
- Participar en subastas
- Obtener pistas narrativas

### Sistema de Misiones

**Tipos de Misiones**:
- Diarias: Recompensas consistentes, rotan cada 24 horas
- Semanales: Recompensas más sustanciales, desafíos complejos
- Narrativas: Relacionadas directamente con la historia
- Evento: Temporales, confeccionadas para fechas especiales
- Personalizadas: Configuradas por administradores

**Estructura de Misión**:
```
Misión {Id, título, descripción, tipo, recompensas, condiciones}
```

### Inventario y Tienda Virtual

**Sistema de Mochila**:
- Límite configurable de capacidad
- Categorías de ítems (coleccionables, utilitarios, narrativos)
- Efectos temporales o permanentes
- Ítems necesarios para desbloqueos narrativos

**Tienda Virtual**:
- Categorías personalizables
- Precios dinámicos (ofertas temporales)
- Ítems únicos y limitados
- Sistema de venta de suscripciones VIP

### Subastas y Trivias

**Subastas**:
- Temporización configurable
- Sistema de pujas en tiempo real
- Ítems exclusivos o limitados
- Registro de ganadores y transacciones

**Trivias**:
- Preguntas con múltiples formatos (opción múltiple, respuesta abierta)
- Temas narrativos o generales
- Recompensas variables basadas en dificultad
- Sistema de temporización y competencia

## Módulo de Administración de Canales

### Gestión de Suscripciones VIP

**Sistema de Suscripciones**:
- Varios niveles de membresía (VIP Básico, VIP Avanzado, VIP Premium)
- Integración con sistemas de pago externos (Stripe, PayU, etc.)
- Pruebas gratuitas limitadas
- Renovación automática con recordatorios

**Control de Acceso**:
- Validación automática de suscripciones activas
- Expulsión automática al expirar
- Sincronización con roles de Telegram
- Sistema de reintegración para suscriptores renovados

**Recordatorios**:
- Notificaciones proactivas antes de expirar
- Ofertas personalizadas para retención
- Seguimiento de comportamiento de usuarios en riesgo de cancelar

### Publicación de Contenido

**Programación de Mensajes**:
- Panel de calendario para planificación
- Publicaciones recurrentes (diarias, semanales)
- Control de versiones de contenido
- Vista previa antes de publicar

**Protección de Contenido**:
- Sistemas anti-reenvío
- Control de descarga de archivos multimedia
- Validación de usuarios antes de acceder a contenido
- Watermarks dinámicos

## Integración y Flujos Cruzados

### Sistema de Eventos

**Modelo de Eventos**:
```
Evento {tipo, origen, destino, datos, fecha}
```

**Ejemplos de Eventos**:
- `usuario_completo_mision` → desbloquea fragmento narrativo
- `usuario_reacciono_contenido` → otorga besitos
- `usuario_desbloqueo_vip` → actualiza acceso a contenido
- `decision_narrativa_tomada` → activa misiones relacionadas

### Conexiones entre Módulos

**Narrativa ↔ Gamificación**:
- Decisiones narrativas → desbloqueo de misiones específicas
- Logros obtenidos → desbloqueo de rutas narrativas alternativas
- Ítems en mochila → acceso a contenido narrativo condicional

**Narrativa ↔ Administración**:
- Progreso narrativo → verificación de roles VIP
- Contenido narrativo → programación automática en canales
- Decisiones clave → generación de eventos narrativos en tiempo real

**Gamificación ↔ Administración**:
- Participación en trivias → actualización de estadísticas
- Compras en tienda → registro de transacciones
- Ranking de usuarios → promoción en canales

## Sistema de Configuración Unificada

### Arquitectura de Configuración Centralizada

**Base de Datos Relacional de Configuración**:

```
Tabla: elementos_configurables
- id
- tipo (misión, fragmento_narrativo, producto_tienda, etc.)
- nombre
- descripción
- metadata (JSON)

Tabla: relaciones_configuracion
- id
- origen_id
- destino_id
- tipo_relacion
- condiciones

Tabla: configuraciones_activas
- id
- elemento_id
- activo
- fecha_inicio
- fecha_fin
```

### Panel de Administración Unificado

**Características Principales**:
1. **Vista de Tablero**: Estado general del ecosistema, métricas clave
2. **Constructor Visual**: Arrastrar y soltar para crear experiencias integradas
3. **Asistentes de Configuración**: Flujos paso a paso para configuraciones complejas
4. **Validación en Tiempo Real**: Verificación de dependencias y conflictos
5. **Historial de Cambios**: Registro completo de configuraciones

### Flujos de Configuración Unificada

**Flujo "Crear Experiencia Narrativa-Gamificada"**:

1. **Seleccionar Tipo**: "Experiencia Integrada"
2. **Definir Contenido Narrativo**:
   - Titulo y sinopsis
   - Contenido multimedia
   - Decisiones y ramificaciones
3. **Configurar Sistema de Recompensas**:
   - Besitos otorgados
   - Ítems desbloqueados
   - Logros relacionados
4. **Especificar Condiciones de Acceso**:
   - Nivel VIP requerido
   - Besitos necesarios
   - Logros previos
5. **Programar Publicación**:
   - Fecha de lanzamiento
   - Canal de distribución
   - Recordatorio automático
6. **Previsualizar y Activar**: Vista previa completa y activación

**Flujo "Configurar Evento de Canal"**:

1. **Seleccionar Tipo**: "Evento de Canal"
2. **Definir Contenido**:
   - Mensaje principal
   - Multimedia adjunto
   - Botones interactivos
3. **Configuración de Interacción**:
   - Reacciones contabilizadas
   - Misiones asociadas
   - Recompensas automáticas
4. **Especificar Duración y Condiciones**:
   - Fechas de vigencia
   - Roles requeridos
   - Límites de participación
5. **Activar y Monitorear**: Sistema de reporte y seguimiento

### API de Configuración Centralizada

**Endpoints Clave**:
- `GET /api/configuracion/elementos`: Listar todos los elementos configurables
- `POST /api/configuracion/elementos`: Crear nuevo elemento configurable
- `PUT /api/configuracion/elementos/{id}`: Actualizar elemento existente
- `DELETE /api/configuracion/elementos/{id}`: Desactivar elemento
- `POST /api/configuracion/relacionar`: Crear relación entre elementos
- `GET /api/configuracion/validar`: Validar consistencia de configuración

### Validación y Propagación Automática

**Sistema de Validación**:
- Verificación de dependencias circulares
- Validación de tipos de datos
- Comprobación de acceso a recursos
- Simulación de flujos antes de activar

**Sistema de Propagación**:
- Actualización automática en todos los módulos afectados
- Mecanismos de rollback en caso de errores
- Notificación a todos los sistemas interesados
- Registro de propagación y posibles errores

## Seguridad y Escalabilidad

### Seguridad

**Protección de Datos**:
- Cifrado de datos sensibles en reposo y en tránsito
- Autenticación y autorización por roles
- Auditoría completa de acciones administrativas
- Política de retención de datos

**Prevención de Abusos**:
- Límites de velocidad para prevención de fraudes
- Sistema de detección de manipulación de puntos
- Monitoreo de patrones de comportamiento anómalos
- Validación de integridad de transacciones

**Control de Acceso**:
- Sistema de roles jerárquico
- Autenticación multifactor para administradores
- Sesiones seguras con expiración
- Registro de intentos de acceso no autorizados

### Escalabilidad

**Arquitectura Horizontal**:
- Contenedores desacoplados para cada módulo
- Balanceo de carga para servicios críticos
- Caché distribuido para contenidos frecuentes
- Base de datos replicada para lectura

**Manejo de Carga**:
- Colas de tareas para operaciones pesadas
- Sistema de notificaciones eficiente
- Gestión de archivos multimedia en CDN
- Procesamiento asíncrono de eventos

## Monetización y Roles

### Modelos de Monetización

**Suscripciones VIP**:
- Planes diferenciados con contenido exclusivo
- Pruebas gratuitas controladas
- Descuentos por compromiso largo plazo
- Beneficios acumulativos por antigüedad

**Tienda Virtual**:
- Ítems cosméticos y personalización
- Accesos anticipados a contenido
- Paquetes de besitos
- Coleccionables limitados

**Eventos Especiales**:
- Contenido exclusivo por temporadas
- Experiencias interactivas limitadas
- Subastas de ítems únicos
- Interacciones personalizadas con personajes

### Sistema de Roles

**Jerarquía de Usuarios**:
- Anónimo: Acceso limitado a contenido promocional
- Registrado: Acceso al contenido gratuito (niveles 1-3)
- VIP Básico: Niveles 4-6 de narrativa + contenido exclusivo
- VIP Avanzado: Todo el contenido narrativo + eventos exclusivos
- VIP Premium: Contenido personalizado + interacciones directas

**Roles Administrativos**:
- Administrador: Acceso total al panel de control
- Editor de Contenido: Creación y edición de narrativa
- Moderador: Gestión de usuarios y contenido
- Analista: Acceso a métricas y reportes

## Consideraciones Finales

### Recomendaciones Técnicas

1. **Desarrollo Iterativo**: Implementar módulos de forma incremental, validando cada componente por separado antes de integrar
2. **Pruebas Automatizadas**: Implementar cobertura extensiva de pruebas unitarias, de integración y end-to-end
3. **Monitoreo Continuo**: Sistema de telemetría para monitorear rendimiento, errores y métricas de usuario
4. **Documentación Completa**: Documentación técnica y de usuario para facilitar el mantenimiento y uso

### Consideraciones de Diseño

1. **Experiencia de Usuario**: Priorizar la usabilidad tanto para usuarios como para administradores
2. **Accesibilidad**: Asegurar que tanto el bot como el panel de administración sean accesibles
3. **Consistencia Visual**: Mantener coherencia visual entre todos los módulos
4. **Rendimiento**: Optimizar tiempos de respuesta para mantener la inmersión narrativa

### Plan de Implementación

1. **Fase 1**: Implementación del núcleo (autenticación, base de datos, bot básico)
2. **Fase 2**: Módulo de gamificación básico (besitos, misiones simples)
3. **Fase 3**: Módulo de narrativa inmersiva (historias ramificadas)
4. **Fase 4**: Sistema de administración de canales
5. **Fase 5**: Panel de administración unificado
6. **Fase 6**: Integraciones avanzadas y optimizaciones

### Riesgos y Mitigaciones

- **Riesgo de Escalabilidad**: Implementar pruebas de carga desde las primeras fases
- **Riesgo de Seguridad**: Revisión de seguridad por terceros antes del lanzamiento
- **Riesgo de Complejidad**: Desarrollo modular para facilitar el mantenimiento
- **Riesgo de Experiencia de Usuario**: Pruebas de usabilidad con usuarios reales

---

*Esta investigación proporciona las bases técnicas, arquitectónicas y de diseño necesarias para el desarrollo de DianaBot, con especial énfasis en el sistema de configuración unificada que permitirá una gestión coherente y eficiente de todos los módulos del sistema.*
