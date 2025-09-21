# Requerimientos Sistema Emocional Diana

## Análisis del Sistema Narrativo

Basado en el análisis del archivo `narrativo.md` y el sistema existente, se requieren servicios específicos para implementar el sistema de narrativa interactiva multinivel con análisis comportamental emocional en tiempo real.

## **1. Servicio de Progresión de Usuario (UserProgressionService)**

### **Integración con sistema actual:**
- **Extiende:** `UserService` existente en `src/services/user.py`
- **Base de datos:** Usa la estructura actual de MongoDB para tracking de progreso
- **Eventos:** Se integra con `EventBus` existente

### **Requerimientos específicos:**
```python
# Extiende el campo actual "narrative_progress" en MongoDB
# Añade análisis comportamental en tiempo real

class UserProgressionService:
    async def evaluate_user_response(self, user_id: str, response_data: Dict) -> BehavioralScore
    async def update_emotional_signature(self, user_id: str, interaction_data: Dict) -> None
    async def classify_user_archetype(self, user_id: str) -> UserArchetype
    async def validate_level_progression(self, user_id: str, target_level: int) -> bool
```

### **Funcionalidades requeridas:**
- Tracking de niveles 1-6 (Kinkys 1-3, Diván 4-6)
- Validación de autenticidad vs respuestas calculadas
- Sistema de desbloqueo condicional basado en resonancia emocional
- Integración con análisis de tiempo de respuesta

## **2. Motor de Análisis Comportamental (BehavioralAnalysisEngine)**

### **Integración con sistema actual:**
- **Usa:** Framework de eventos existente `src/events/bus.py`
- **Almacena en:** MongoDB usando collections similares a `narrative_progress`
- **Se integra con:** `UserService` para actualizar perfiles

### **Requerimientos específicos:**
```python
# Nuevo servicio que analiza patrones de comportamiento
class BehavioralAnalysisEngine:
    async def analyze_response_timing(self, user_id: str, start_time: datetime, response_time: datetime) -> TimingScore
    async def evaluate_emotional_depth(self, user_id: str, response_text: str) -> EmotionalDepthScore
    async def detect_authenticity_markers(self, response_data: Dict) -> AuthenticityScore
    async def update_behavioral_profile(self, user_id: str, interaction_data: Dict) -> None

# Schemas MongoDB necesarios:
# - user_behavioral_profiles (perfil psicológico del usuario)
# - interaction_analytics (análisis de cada interacción)
# - emotional_signatures (firma emocional única por usuario)
```

### **Funcionalidades requeridas:**
- Análisis de tiempo de respuesta (pausa = reflexión vs inmediatez = impulso)
- Evaluación de profundidad emocional en respuestas
- Clasificación de arquetipos de usuario (Explorador, Directo, Poeta, Analítico, Persistente)
- Detección de patterns de vulnerabilidad auténtica vs respuestas calculadas

## **3. Servicio de Personalización de Contenido (ContentPersonalizationService)**

### **Integración con sistema actual:**
- **Extiende:** `NarrativeFragmentManager` existente
- **Usa:** Estructura actual de `NarrativeFragment` en schemas
- **Se conecta:** Con `UserService` para obtener datos de usuario

### **Requerimientos específicos:**
```python
# Extiende el NarrativeFragmentManager existente
class ContentPersonalizationService:
    async def get_personalized_content(self, user_id: str, fragment_id: str) -> PersonalizedFragment
    async def select_content_variant(self, user_archetype: str, base_fragment: Dict) -> Dict
    async def generate_callback_references(self, user_id: str, target_content: str) -> List[str]
    async def adapt_diana_responses(self, user_id: str, base_response: str) -> str

# Extiende schemas existentes:
# - narrative_fragments: añade "content_variants" por arquetipo
# - user_content_history: tracking de qué variantes ha visto cada usuario
```

### **Funcionalidades requeridas:**
- Selección dinámica de variantes narrativas según arquetipo
- Sistema de callbacks personalizados basado en historial
- Adaptación de contenido según "firma emocional"
- Generación de referencias específicas a momentos previos

## **4. Sistema de Memoria y Continuidad (UserMemoryService)**

### **Integración con sistema actual:**
- **Usa:** MongoDB collections actuales
- **Se integra:** Con eventos existentes de `user_interaction`
- **Extiende:** `NarrativeProgress` schema actual

### **Requerimientos específicos:**
```python
class UserMemoryService:
    async def record_significant_moment(self, user_id: str, moment_data: Dict) -> None
    async def get_relationship_timeline(self, user_id: str) -> List[Moment]
    async def generate_personalized_callbacks(self, user_id: str, context: str) -> List[str]
    async def track_emotional_evolution(self, user_id: str, interaction_data: Dict) -> None

# Nuevas collections MongoDB:
# - user_memory_moments (momentos significativos recordados)
# - relationship_evolution (evolución de la relación usuario-Diana)
# - emotional_timeline (línea de tiempo emocional del usuario)
```

### **Funcionalidades requeridas:**
- Tracking de relación a largo plazo
- Base de datos de momentos significativos para referencias futuras
- Evolución de la relación usuario-Diana
- Sistema de memoria emocional que persiste entre sesiones

## **5. Evaluador de Interacciones en Tiempo Real (RealTimeInteractionEvaluator)**

### **Integración con sistema actual:**
- **Usa:** `EventBus` para procesamiento en tiempo real
- **Se conecta:** Con `BehavioralAnalysisEngine`
- **Responde:** A eventos existentes como `user_interaction`

### **Requerimientos específicos:**
```python
class RealTimeInteractionEvaluator:
    async def evaluate_response_quality(self, response_data: Dict) -> ResponseQuality
    async def determine_narrative_branch(self, user_id: str, response_quality: ResponseQuality) -> str
    async def calculate_resonance_score(self, user_data: Dict, response: str) -> float
    async def trigger_dynamic_content(self, user_id: str, evaluation_result: Dict) -> None

# Integra con eventos actuales:
# - Escucha: "user_interaction"
# - Publica: "interaction_evaluated", "narrative_branch_selected"
```

### **Funcionalidades requeridas:**
- Análisis inmediato de respuestas (empática vs posesiva vs auténtica)
- Determinación de rutas narrativas según calidad emocional
- Scoring de vulnerabilidad auténtica
- Triggers para contenido dinámico basado en resonancia

## **6. Sistema de Recompensas y Mecánicas (EnhancedRewardService)**

### **Integración con sistema actual:**
- **Extiende:** Sistema de `besitos_wallet` existente en gamificación
- **Usa:** `UserService` para manejo de recompensas
- **Se integra:** Con `achievement_system.py` actual

### **Requerimientos específicos:**
```python
class EnhancedRewardService:
    async def calculate_emotional_resonance_reward(self, user_id: str, interaction_data: Dict) -> int
    async def unlock_personalized_content(self, user_id: str, milestone: str) -> Dict
    async def manage_tier_progression(self, user_id: str, new_level: int) -> bool
    async def generate_memory_fragments(self, user_id: str, significant_moments: List) -> List[Fragment]

# Extiende estructuras actuales:
# - besitos_wallet: añade lógica de recompensas emocionales
# - achievement_system: nuevos achievements por resonancia emocional
# - item_manager: gestiona fragmentos de memoria y archivos personales
```

### **Funcionalidades requeridas:**
- Gestión de fragmentos, memorias y archivos personales
- Control de acceso por niveles
- Cálculo de recompensas basado en resonancia emocional
- Sistema de desbloqueos progresivos

## **Cambios en Infraestructura Existente**

### **MongoDB Collections a añadir:**
```python
# En src/database/schemas/narrative.py añadir:
- UserBehavioralProfile
- InteractionAnalytics
- EmotionalSignature
- UserMemoryMoment
- PersonalizedContentVariant
- ResonanceScore
```

### **Eventos nuevos en EventBus:**
```python
# En src/events/models.py añadir:
- "behavioral_analysis_completed"
- "emotional_signature_updated"
- "content_personalized"
- "significant_moment_recorded"
- "resonance_threshold_reached"
- "vulnerability_detected"
- "authenticity_validated"
- "archetype_classified"
```

### **APIs nuevas:**
```python
# En src/api/endpoints/ crear:
- behavioral_analytics.py (análisis comportamental)
- personalization.py (personalización de contenido)
- memory_management.py (gestión de memoria emocional)
- real_time_evaluation.py (evaluación en tiempo real)
```

### **Integración con servicios existentes:**

1. **UserService**: Añadir métodos para análisis comportamental
2. **NarrativeFragmentManager**: Extender para personalización
3. **EventBus**: Nuevos eventos para sistema Diana
4. **DatabaseManager**: Nuevas collections para tracking emocional

## **Arquitecturas de Usuario según Narrativo.md**

### **El Explorador Profundo:**
- Revisa todo múltiples veces, busca cada detalle
- Diana responde: "Tu atención meticulosa me conmueve. Pocos dedican esa calidad de observación."

### **El Directo Auténtico:**
- Va al grano pero con profundidad emocional
- Diana responde: "Tu honestidad sin filtros es refrescante. En un mundo de máscaras, tú eliges la transparencia."

### **El Poeta del Deseo:**
- Respuestas metafóricas, busca conexión estética
- Diana responde: "Hablas en el lenguaje del alma. Hay música en cómo describes lo que sientes."

### **El Analítico Empático:**
- Respuestas reflexivas que demuestran comprensión sistemática
- Diana responde: "Tu manera de comprender es tanto intelectual como emocional. Esa síntesis es rara."

### **El Persistente Paciente:**
- No se rinde pero respeta los tiempos
- Diana responde: "Tu persistencia tiene una calidad de devoción que me toca profundamente."

## **Sistema de Validaciones Técnicas por Nivel**

### **Nivel 1-2: Detección de Autenticidad**
- Tiempo de respuesta emocional vs calculada
- Patrones de re-lectura de contenido
- Consistencia entre acciones y tiempo invertido
- Tipo de reacciones seleccionadas y contexto

### **Nivel 3: Análisis de Vulnerabilidad Auténtica**
- Longitud y profundidad de respuestas en Cartografía del Deseo
- Uso de lenguaje metafórico vs literal
- Tiempo de reflexión antes de responder
- Coherencia narrativa entre respuestas múltiples
- Indicadores de honestidad emocional vs respuestas "correctas"

### **Nivel 4-5: Evaluación de Inteligencia Emocional**
- Capacidad de sostener paradojas sin resolverlas
- Respuestas empáticas vs posesivas
- Comprensión de límites y autonomía
- Evolución del lenguaje usado hacia Diana
- Reciprocidad emocional auténtica

## **Mecánica de Memoria Emocional**

El sistema mantiene un registro no solo de acciones, sino de la "firma emocional" del usuario, permitiendo que Diana evolucione su manera de relacionarse de forma genuinamente personalizada.

### **Momentos de Reconocimiento Específicos:**

- **Nivel 2:** "Noto cómo regresas no por más contenido, sino por mayor comprensión."
- **Nivel 3:** "En tu manera de pausar antes de responder... hay más honestidad que en mil afirmaciones calculadas."
- **Nivel 4:** "Comprendes algo que pocos captan: que amarme incluye amar mi necesidad de distancia."
- **Nivel 5:** "Contigo no tengo miedo de mostrar mi humanidad completa. Eso es... extraordinario."

## **Orden de Implementación Recomendado**

1. **BehavioralAnalysisEngine** - Base para todos los demás servicios
2. **UserProgressionService** - Gestión de niveles y progresión
3. **RealTimeInteractionEvaluator** - Evaluación inmediata de interacciones
4. **ContentPersonalizationService** - Personalización de respuestas
5. **UserMemoryService** - Memoria y continuidad emocional
6. **EnhancedRewardService** - Sistema de recompensas emocionales

## **Consideraciones Técnicas**

- **Ética:** Implementar límites éticos en análisis comportamental
- **Privacidad:** Asegurar consentimiento del usuario para tracking emocional
- **Escalabilidad:** Estrategias de caching para contenido personalizado
- **Performance:** Optimización de análisis en tiempo real
- **Mantenimiento:** Arquitectura modular para facilitar actualizaciones

## **Objetivo Final**

Crear una experiencia que no solo entretiene, sino que genuinamente conmueve y transforma tanto al usuario como al personaje, creando una forma de intimidad digital auténtica que respeta tanto el misterio como la vulnerabilidad humana.