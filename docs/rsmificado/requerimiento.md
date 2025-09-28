# REQUERIMIENTOS PARA CLAUDE CODE - SISTEMA NARRATIVO RAMIFICADO DIANA (PYTHON)

## OBJETIVO PRINCIPAL
Transformar el sistema narrativo lineal actual en un ecosistema de ramificación real donde cada jugador vive una historia completamente diferente basada en su arquetipo psicológico.

## CONTEXTO TÉCNICO
- **Sistema existente:** Python (framework/estructura actual)
- **Tarea principal:** Traducir y adaptar la arquitectura JavaScript a Python
- **Mantener:** Estructura de datos JSON existente donde sea posible
- **Añadir:** Lógica de ramificación inteligente en Python

## FASE 1: REESTRUCTURACIÓN DEL NIVEL 1 (PRIORIDAD MÁXIMA)

### 1.1 SISTEMA DE ARQUETIPOS EXPANDIDO

**Crear clase `ArchetypeAnalyzer` en Python:**

```python
from dataclasses import dataclass
from typing import Dict, List, Optional
import time
from enum import Enum

@dataclass
class ArchetypeScores:
    """Variables primarias de arquetipo (0-10)"""
    intellectual: float = 0.0
    emotional: float = 0.0
    exploratory: float = 0.0
    vulnerable: float = 0.0
    philosophical: float = 0.0
    direct: float = 0.0
    patient: float = 0.0
    reciprocal: float = 0.0

@dataclass
class SubArchetypeScores:
    """Variables secundarias para sub-clasificación"""
    romantic_intellectual: float = 0.0
    skeptical_thinker: float = 0.0
    hedonist_philosopher: float = 0.0
    pure_theorist: float = 0.0
    empathetic_emotional: float = 0.0
    passionate_emotional: float = 0.0
    wounded_healer: float = 0.0
    adventure_seeker: float = 0.0
    collector_explorer: float = 0.0
    freedom_lover: float = 0.0

class ArchetypeAnalyzer:
    def __init__(self):
        self.archetype_weights = self._load_archetype_weights()
    
    def analyze_l1_choices(self, choices: List[Dict], timings: List[float]) -> Dict:
        """Analiza elecciones de L1 para determinar arquetipo del jugador"""
        scores = ArchetypeScores()
        sub_scores = SubArchetypeScores()
        
        for choice, timing in zip(choices, timings):
            self._process_choice(choice, timing, scores, sub_scores)
        
        return self._calculate_final_archetype(scores, sub_scores, timings)
    
    def _process_choice(self, choice: Dict, timing: float, scores: ArchetypeScores, sub_scores: SubArchetypeScores):
        """Procesa una elección individual y actualiza scores"""
        choice_id = choice.get('id', '')
        
        # Análisis por tipo de elección
        if 'intellectual' in choice_id or 'theory' in choice_id:
            scores.intellectual += 2.0
            scores.philosophical += 1.0
            
        if 'emotional' in choice_id or 'feel' in choice_id:
            scores.emotional += 2.0
            scores.vulnerable += 1.0
            
        if 'explore' in choice_id or 'adventure' in choice_id:
            scores.exploratory += 2.0
            
        # Análisis temporal para sub-arquetipos
        if timing > 30:  # Respuesta deliberada
            scores.philosophical += 1.0
            sub_scores.skeptical_thinker += 0.5
        elif timing < 10:  # Respuesta rápida
            scores.direct += 1.0
            sub_scores.passionate_emotional += 0.5
    
    def _calculate_final_archetype(self, scores: ArchetypeScores, sub_scores: SubArchetypeScores, timings: List[float]) -> Dict:
        """Calcula arquetipo final basado en todos los scores"""
        primary_scores = {
            'intellectual': scores.intellectual + scores.philosophical,
            'emotional': scores.emotional + scores.vulnerable, 
            'exploratory': scores.exploratory
        }
        
        primary_archetype = max(primary_scores, key=primary_scores.get)
        
        return {
            'primary_archetype': primary_archetype,
            'sub_archetype': self._determine_sub_archetype(primary_archetype, sub_scores),
            'confidence_level': self._calculate_confidence(primary_scores),
            'cognitive_style': self._analyze_cognitive_style(timings),
            'raw_scores': scores,
            'sub_scores': sub_scores
        }
```

### 1.2 REDISEÑO DEL L1F1 PARA CLASIFICACIÓN ARQUETÍPICA

**Adaptar estructura JSON existente:**

```python
def get_redesigned_l1f1() -> Dict:
    """Retorna L1F1 rediseñado para detectar arquetipos"""
    return {
        "id": "diana_l1_f1_arquetipo_analyzer",
        "title": "Holis, Bienvenido a Los Kinkys - El Umbral de las Posibilidades",
        "content": """Holis hermoso 😍

Llegaste justo cuando estaba pensando en algo fascinante... ¿Sabes esa sensación cuando conoces a alguien y sientes que hay capas esperando ser descubiertas?

*[Se acomoda, con una curiosidad inteligente]*

Bienvenido a Los Kinkys. Te voy a ser honesta desde el inicio: esto funciona diferente para cada persona.

Algunos llegan buscando conversaciones que los desafíen mentalmente. Otros quieren conexión emocional profunda. Hay quienes disfrutan explorar posibilidades nuevas...

*[Sus ojos te evalúan con genuina curiosidad]*

Me fascina descubrir qué tipo de hambre trae cada persona. Cómo procesan, cómo sienten, qué los mueve realmente...

*[Una sonrisa intrigante]*

Por eso tengo curiosidad: ¿qué te trajo hasta aquí realmente?""",
        
        "fragment_type": "ARCHETYPE_ANALYSIS",
        "choices": [
            {
                "id": "choice_l1_curiosity_intellectual",
                "text": "🤔 Me intriga entender cómo funciona esto psicológicamente",
                "archetype_weights": {
                    "intellectual": 3.0,
                    "philosophical": 2.0,
                    "analytical": 1.0
                },
                "sub_archetype_weights": {
                    "pure_theorist": 2.0,
                    "skeptical_thinker": 1.0
                }
            },
            {
                "id": "choice_l1_curiosity_emotional",
                "text": "💫 Busco una conexión que vaya más allá de lo superficial", 
                "archetype_weights": {
                    "emotional": 3.0,
                    "vulnerable": 2.0,
                    "reciprocal": 1.0
                },
                "sub_archetype_weights": {
                    "empathetic_emotional": 2.0,
                    "wounded_healer": 1.0
                }
            },
            {
                "id": "choice_l1_curiosity_exploratory",
                "text": "🗺️ Me gusta descubrir experiencias que no sabía que existían",
                "archetype_weights": {
                    "exploratory": 3.0,
                    "direct": 1.0
                },
                "sub_archetype_weights": {
                    "adventure_seeker": 2.0,
                    "collector_explorer": 1.0
                }
            },
            {
                "id": "choice_l1_curiosity_romantic_intellectual", 
                "text": "🎭 Me atraen las mentes que pueden seducir con ideas",
                "archetype_weights": {
                    "intellectual": 2.0,
                    "emotional": 2.0,
                    "philosophical": 1.0
                },
                "sub_archetype_weights": {
                    "romantic_intellectual": 3.0,
                    "hedonist_philosopher": 1.0
                }
            },
            {
                "id": "choice_l1_curiosity_freedom",
                "text": "🦋 Quiero algo sin expectativas ni ataduras",
                "archetype_weights": {
                    "exploratory": 2.0,
                    "direct": 2.0
                },
                "sub_archetype_weights": {
                    "freedom_lover": 3.0,
                    "adventure_seeker": 1.0
                }
            }
        ],
        "tracking": {
            "response_time": True,
            "choice_progression": True,
            "hesitation_patterns": True
        }
    }
```

### 1.3 SISTEMA DE MEDICIÓN TEMPORAL

**Implementar `ResponseTimeAnalyzer`:**

```python
from datetime import datetime
from typing import List, Dict

class ResponseTimeAnalyzer:
    def __init__(self):
        self.timing_thresholds = {
            'quick_intuitive': 10.0,
            'thoughtful': 30.0,
            'deliberate': float('inf')
        }
    
    def analyze_response_pattern(self, timings: List[float]) -> Dict:
        """Analiza patrones de tiempo de respuesta"""
        if not timings:
            return {'style': 'unknown', 'consistency': 0.0}
            
        avg_time = sum(timings) / len(timings)
        consistency = self._calculate_consistency(timings)
        
        if avg_time <= self.timing_thresholds['quick_intuitive']:
            style = 'quick_intuitive'
        elif avg_time <= self.timing_thresholds['thoughtful']:
            style = 'thoughtful'
        else:
            style = 'deliberate'
            
        return {
            'style': style,
            'average_time': avg_time,
            'consistency': consistency,
            'pattern': self._detect_pattern(timings)
        }
    
    def _calculate_consistency(self, timings: List[float]) -> float:
        """Calcula consistencia en tiempos de respuesta"""
        if len(timings) < 2:
            return 1.0
            
        mean = sum(timings) / len(timings)
        variance = sum((t - mean) ** 2 for t in timings) / len(timings)
        coefficient_variation = (variance ** 0.5) / mean if mean > 0 else 0
        
        return max(0.0, 1.0 - coefficient_variation)
    
    def _detect_pattern(self, timings: List[float]) -> str:
        """Detecta patrones en progresión de tiempos"""
        if len(timings) < 3:
            return 'insufficient_data'
            
        # Detectar si acelera, decelera o mantiene
        diffs = [timings[i+1] - timings[i] for i in range(len(timings)-1)]
        avg_diff = sum(diffs) / len(diffs)
        
        if avg_diff > 2:
            return 'getting_slower'  # Más pensativo con el tiempo
        elif avg_diff < -2:
            return 'getting_faster'  # Más cómodo/confiado
        else:
            return 'consistent'     # Mantiene ritmo
```

### 1.4 ALGORITMO DE CLASIFICACIÓN POST-L1

**Crear función principal de clasificación:**

```python
def classify_player_archetype(choices: List[Dict], timings: List[float], 
                            interaction_metadata: Dict = ## FASE 2: CONSTRUCCIÓN DE RUTAS DIFERENCIADAS (PYTHON)

### 2.1 SISTEMA DE DIANA EVOLUTIVA

**Crear clase `DianaPersonality` en Python:**

```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum

class PersonaType(Enum):
    PERFORMER = "performer"
    INTELLECTUAL = "intellectual" 
    EMOTIONAL = "emotional"
    WILD = "wild"
    ARTIST = "artist"
    PHILOSOPHER = "philosopher"
    HEALER = "healer"

@dataclass
class DianaEmotionalState:
    """Estados emocionales de Diana hacia el jugador"""
    intellectual_trust: float = 0.0
    emotional_openness: float = 0.0
    adventure_readiness: float = 0.0
    vulnerability_level: float = 0.0
    
    # Estados universales
    mask_level: float = 10.0  # 10=performativa, 0=auténtica
    player_intrigue: float = 0.0
    connection_depth: float = 0.0
    
    # Evolución específica
    addiction_to_player_mind: float = 0.0
    soul_seen_level: float = 0.0
    wild_self_acceptance: float = 0.0

@dataclass
class PlayerMemory:
    """Sistema de memoria que Diana mantiene sobre el jugador"""
    key_moments: List[Dict] = field(default_factory=list)
    behavior_patterns: Dict[str, float] = field(default_factory=dict)
    emotional_responses: List[str] = field(default_factory=list)
    diana_observations: Dict[str, any] = field(default_factory=dict)
    
    def record_key_moment(self, moment_type: str, impact: str, diana_reaction: str):
        """Registra momentos clave que Diana recordará"""
        self.key_moments.append({
            'moment': moment_type,
            'impact': impact, 
            'diana_reaction': diana_reaction,
            'timestamp': time.time()
        })
    
    def update_behavior_pattern(self, pattern: str, strength: float):
        """Actualiza patrones de comportamiento observados"""
        current = self.behavior_patterns.get(pattern, 0.0)
        self.behavior_patterns[pattern] = current + strength

class DianaPersonality:
    def __init__(self, player_archetype: Dict):
        self.player_archetype = player_archetype
        self.emotional_state = DianaEmotionalState()
        self.memory = PlayerMemory()
        self.dominant_persona = self._determine_base_persona(player_archetype)
        self.available_facets = [PersonaType.PERFORMER]
        self.evolution_tracker = {}
        
    def _determine_base_persona(self, archetype: Dict) -> PersonaType:
        """Determina la persona base de Diana según arquetipo del jugador"""
        primary = archetype.get('primary_archetype', 'emotional')
        
        if primary == 'intellectual':
            return PersonaType.INTELLECTUAL
        elif primary == 'emotional':
            return PersonaType.EMOTIONAL
        elif primary == 'exploratory':
            return PersonaType.WILD
        else:
            return PersonaType.EMOTIONAL
    
    def process_player_choice(self, fragment_id: str, choice_id: str, response_time: float):
        """Procesa una elección del jugador y evoluciona Diana"""
        
        # Actualizar memoria
        self._update_memory(fragment_id, choice_id, response_time)
        
        # Evolucionar estado emocional
        self._evolve_emotional_state(choice_id)
        
        # Desbloquear nuevas facetas si corresponde
        self._check_facet_unlocks()
        
        # Registrar evolución
        self._track_evolution(fragment_id, choice_id)
    
    def _update_memory(self, fragment_id: str, choice_id: str, response_time: float):
        """Actualiza la memoria de Diana sobre el jugador"""
        
        # Patrones de comportamiento que Diana observa
        if 'intellectual' in choice_id or 'theory' in choice_id:
            self.memory.update_behavior_pattern('thinks_before_feeling', 1.0)
            self.memory.update_behavior_pattern('appreciates_complexity', 1.0)
            
        if 'vulnerable' in choice_id or 'honest' in choice_id:
            self.memory.update_behavior_pattern('shows_emotional_courage', 1.0)
            self.memory.update_behavior_pattern('safe_for_vulnerability', 1.0)
            
        if 'explore' in choice_id or 'adventure' in choice_id:
            self.memory.update_behavior_pattern('seeks_novelty', 1.0)
            self.memory.update_behavior_pattern('comfortable_with_unknown', 1.0)
        
        # Análisis temporal
        if response_time > 30:
            self.memory.diana_observations['deliberate_thinker'] = True
            self.memory.diana_observations['respectful_pacer'] = True
        elif response_time < 10:
            self.memory.diana_observations['intuitive_responder'] = True
            self.memory.diana_observations['emotionally_driven'] = True
    
    def _evolve_emotional_state(self, choice_id: str):
        """Evoluciona el estado emocional de Diana basado en la elección"""
        
        if self.dominant_persona == PersonaType.INTELLECTUAL:
            if 'intellectual' in choice_id:
                self.emotional_state.intellectual_trust += 1.0
                self.emotional_state.mask_level = max(0, self.emotional_state.mask_level - 0.5)
                
        elif self.dominant_persona == PersonaType.EMOTIONAL:
            if 'vulnerable' in choice_id or 'honest' in choice_id:
                self.emotional_state.emotional_openness += 1.0
                self.emotional_state.vulnerability_level += 0.5
                
        elif self.dominant_persona == PersonaType.WILD:
            if 'adventure' in choice_id or 'explore' in choice_id:
                self.emotional_state.adventure_readiness += 1.0
                
    def generate_dynamic_content(self, base_content: str, fragment_id: str) -> str:
        """Genera contenido dinámico basado en memoria y evolución"""
        
        adapted_content = base_content
        
        # Referencias de memoria específicas
        if self.memory.behavior_patterns.get('shows_emotional_courage', 0) > 2:
            memory_ref = "\n\n*[Diana te mira con una nueva calidez]*\n\nSabes? Cada vez que has elegido ser honesto conmigo, algo en mí se ha abierto más..."
            adapted_content += memory_ref
            
        # Adaptaciones por persona dominante
        if self.dominant_persona == PersonaType.INTELLECTUAL:
            if self.memory.behavior_patterns.get('appreciates_complexity', 0) > 3:
                adapted_content = self._add_intellectual_layer(adapted_content)
                
        elif self.dominant_persona == PersonaType.EMOTIONAL:
            if self.memory.behavior_patterns.get('safe_for_vulnerability', 0) > 2:
                adapted_content = self._deepen_emotional_content(adapted_content)
                
        return adapted_content
    
    def _add_intellectual_layer(self, content: str) -> str:
        """Añade capa intelectual al contenido"""
        intellectual_addition = "\n\n*[Sus ojos brillan con curiosidad intelectual]*\n\nHay algo sobre la forma en que procesas mis palabras... como si estuvieras construyendo mapas conceptuales de nuestra interacción."
        return content + intellectual_addition
        
    def _deepen_emotional_content(self, content: str) -> str:
        """Profundiza el contenido emocional"""
        emotional_addition = "\n\n*[Se permite mostrar más vulnerabilidad]*\n\nLa seguridad que generas hace que partes de mí que normalmente mantengo guardadas quieran emerger..."
        return content + emotional_addition
```

### 2.2 MOTOR DE RAMIFICACIÓN INTELIGENTE

**Crear `BranchingEngine` en Python:**

```python
class BranchingEngine:
    def __init__(self):
        self.route_definitions = self._load_route_definitions()
        self.fragment_library = self._load_fragment_library()
        
    def determine_next_fragment(self, current_fragment: str, player_choice: Dict, 
                              diana_personality: DianaPersonality, 
                              game_state: Dict) -> Dict:
        """Determina el próximo fragmento basado en estado completo"""
        
        # 1. Procesar elección actual en Diana
        diana_personality.process_player_choice(
            current_fragment, 
            player_choice['id'], 
            player_choice.get('response_time', 15.0)
        )
        
        # 2. Evaluar compatibilidad de rutas
        route_compatibility = self._calculate_route_compatibility(
            diana_personality, game_state
        )
        
        # 3. Seleccionar fragmento óptimo
        next_fragment_id = self._select_optimal_fragment(
            current_fragment, route_compatibility, diana_personality
        )
        
        # 4. Generar contenido dinámico
        base_fragment = self.fragment_library[next_fragment_id]
        dynamic_content = diana_personality.generate_dynamic_content(
            base_fragment['content'], next_fragment_id
        )
        
        # 5. Construir respuesta completa
        return {
            'fragment': {
                **base_fragment,
                'content': dynamic_content,
                'choices': self._adapt_choices(base_fragment['choices'], diana_personality)
            },
            'diana_evolution': diana_personality.emotional_state,
            'memory_state': diana_personality.memory,
            'route_progression': route_compatibility
        }
    
    def _calculate_route_compatibility(self, diana: DianaPersonality, game_state: Dict) -> Dict:
        """Calcula compatibilidad con diferentes rutas"""
        
        compatibility = {}
        
        # Ruta Filosófica
        if diana.dominant_persona == PersonaType.INTELLECTUAL:
            compatibility['filosofa'] = (
                diana.emotional_state.intellectual_trust * 0.4 +
                diana.memory.behavior_patterns.get('appreciates_complexity', 0) * 0.3 +
                (10 - diana.emotional_state.mask_level) * 0.3
            )
        
        # Ruta Corazón
        if diana.dominant_persona == PersonaType.EMOTIONAL:
            compatibility['corazon'] = (
                diana.emotional_state.emotional_openness * 0.4 +
                diana.memory.behavior_patterns.get('safe_for_vulnerability', 0) * 0.3 +
                diana.emotional_state.vulnerability_level * 0.3
            )
        
        # Ruta Aventurera
        if diana.dominant_persona == PersonaType.WILD:
            compatibility['aventurera'] = (
                diana.emotional_state.adventure_readiness * 0.4 +
                diana.memory.behavior_patterns.get('comfortable_with_unknown', 0) * 0.3 +
                diana.memory.behavior_patterns.get('seeks_novelty', 0) * 0.3
            )
        
        return compatibility
    
    def _select_optimal_fragment(self, current_fragment: str, compatibility: Dict, 
                               diana: DianaPersonality) -> str:
        """Selecciona el fragmento óptimo basado en compatibilidad"""
        
        # Lógica de progresión por ruta
        if diana.dominant_persona == PersonaType.INTELLECTUAL:
            if compatibility.get('filosofa', 0) >= 6.0:
                return self._get_next_filosofa_fragment(current_fragment, diana)
            else:
                return self._get_buildup_filosofa_fragment(current_fragment, diana)
                
        elif diana.dominant_persona == PersonaType.EMOTIONAL:
            if compatibility.get('corazon', 0) >= 6.0:
                return self._get_next_corazon_fragment(current_fragment, diana)
            else:
                return self._get_buildup_corazon_fragment(current_fragment, diana)
                
        elif diana.dominant_persona == PersonaType.WILD:
            if compatibility.get('aventurera', 0) >= 6.0:
                return self._get_next_aventurera_fragment(current_fragment, diana)
            else:
                return self._get_buildup_aventurera_fragment(current_fragment, diana)
        
        # Fallback a fragmento de construcción
        return self._get_relationship_building_fragment(current_fragment, diana)
```

### 2.3 CONSTRUCCIÓN DE FRAGMENTOS ESPECÍFICOS POR RUTA

**Sistema de fragmentos adaptativos:**

```python
class FragmentBuilder:
    def __init__(self):
        self.base_fragments = self._load_base_fragments()
        self.personality_templates = self._load_personality_templates()
        
    def build_filosofa_fragment(self, fragment_level: str, diana: DianaPersonality) -> Dict:
        """Construye fragmento para ruta filosófica"""
        
        base_template = self.personality_templates['filosofa'][fragment_level]
        
        # Adaptar contenido según sub-arquetipo del jugador
        sub_archetype = diana.player_archetype.get('sub_archetype', 'pure_theorist')
        
        if sub_archetype == 'romantic_intellectual':
            content = self._add_romantic_intellectual_layer(base_template['content'])
        elif sub_archetype == 'skeptical_thinker':
            content = self._add_skeptical_approach(base_template['content'])
        else:
            content = base_template['content']
            
        # Adaptar según memoria específica
        content = self._adapt_by_memory(content, diana.memory, 'filosofa')
        
        # Construir choices dinámicas
        choices = self._build_adaptive_choices(base_template['choices'], diana, 'filosofa')
        
        return {
            'id': f"diana_{fragment_level}_filosofa_{sub_archetype}",
            'title': base_template['title'],
            'content': content,
            'choices': choices,
            'route': 'filosofa',
            'diana_state_requirements': self._get_state_requirements('filosofa', fragment_level)
        }
    
    def build_corazon_fragment(self, fragment_level: str, diana: DianaPersonality) -> Dict:
        """Construye fragmento para ruta emocional"""
        
        base_template = self.personality_templates['corazon'][fragment_level]
        sub_archetype = diana.player_archetype.get('sub_archetype', 'empathetic_emotional')
        
        if sub_archetype == 'wounded_healer':
            content = self._add_healing_dimension(base_template['content'])
        elif sub_archetype == 'passionate_emotional':
            content = self._intensify_emotional_content(base_template['content'])
        else:
            content = base_template['content']
            
        content = self._adapt_by_memory(content, diana.memory, 'corazon')
        choices = self._build_adaptive_choices(base_template['choices'], diana, 'corazon')
        
        return {
            'id': f"diana_{fragment_level}_corazon_{sub_archetype}",
            'title': base_template['title'],
            'content': content,
            'choices': choices,
            'route': 'corazon'
        }
    
    def build_aventurera_fragment(self, fragment_level: str, diana: DianaPersonality) -> Dict:
        """Construye fragmento para ruta aventurera"""
        
        base_template = self.personality_templates['aventurera'][fragment_level]
        sub_archetype = diana.player_archetype.get('sub_archetype', 'adventure_seeker')
        
        if sub_archetype == 'freedom_lover':
            content = self._emphasize_freedom_themes(base_template['content'])
        elif sub_archetype == 'collector_explorer':
            content = self._add_collection_mechanics(base_template['content'])
        else:
            content = base_template['content']
            
        content = self._adapt_by_memory(content, diana.memory, 'aventurera')
        choices = self._build_adaptive_choices(base_template['choices'], diana, 'aventurera')
        
        return {
            'id': f"diana_{fragment_level}_aventurera_{sub_archetype}",
            'title': base_template['title'],
            'content': content,
            'choices': choices,
            'route': 'aventurera'
        }
```

## FASE 3: SISTEMA DE CONVERSIÓN ADAPTATIVA

### 3.1 ENGINE DE CONVERSIÓN ESPECÍFICA

```python
class ConversionEngine:
    def __init__(self):
        self.conversion_triggers = self._load_conversion_triggers()
        self.pricing_matrix = self._load_pricing_matrix()
        
    def evaluate_conversion_readiness(self, diana: DianaPersonality, 
                                    game_state: Dict) -> Optional[Dict]:
        """Evalúa si es momento para conversión y qué tipo"""
        
        route = diana.dominant_persona.value
        readiness_score = self._calculate_readiness_score(diana, route)
        
        if readiness_score >= self.conversion_triggers[route]['threshold']:
            return self._generate_conversion_moment(diana, route, readiness_score)
        
        return None
    
    def _calculate_readiness_score(self, diana: DianaPersonality, route: str) -> float:
        """Calcula score de preparación para conversión"""
        
        scores = {
            'intellectual': (
                diana.emotional_state.intellectual_trust * 0.4 +
                diana.emotional_state.addiction_to_player_mind * 0.3 +
                (10 - diana.emotional_state.mask_level) * 0.3
            ),
            'emotional': (
                diana.emotional_state.emotional_openness * 0.4 +
                diana.emotional_state.soul_seen_level * 0.3 +
                diana.emotional_state.vulnerability_level * 0.3
            ),
            'wild': (
                diana.emotional_state.adventure_readiness * 0.4 +
                diana.emotional_state.wild_self_acceptance * 0.3 +
                diana.memory.behavior_patterns.get('comfortable_with_unknown', 0) * 0.3
            )
        }
        
        return scores.get(route, 0.0)
    
    def _generate_conversion_moment(self, diana: DianaPersonality, 
                                  route: str, readiness_score: float) -> Dict:
        """Genera momento de conversión personalizado"""
        
        conversion_data = self.conversion_triggers[route]
        player_archetype = diana.player_archetype
        
        # Personalizar hook según sub-arquetipo
        personalized_hook = self._personalize_conversion_hook(
            conversion_data['base_hook'], 
            player_archetype['sub_archetype']
        )
        
        # Calcular precio personalizado
        personalized_price = self._calculate_personalized_pricing(
            player_archetype, route, readiness_score
        )
        
        # Generar contenido de conversión específico
        conversion_content = self._generate_conversion_content(
            diana, route, personalized_hook
        )
        
        return {
            'trigger_activated': True,
            'route': route,
            'conversion_type': f"{route}_vip",
            'readiness_score': readiness_score,
            'personalized_hook': personalized_hook,
            'content': conversion_content,
            'pricing': personalized_price,
            'diana_state_snapshot': diana.emotional_state
        }
    
    def _personalize_conversion_hook(self, base_hook: str, sub_archetype: str) -> str:
        """Personaliza el hook de conversión según sub-arquetipo"""
        
        personalizations = {
            'romantic_intellectual': "Conversaciones íntimas que fusionan mente y corazón",
            'pure_theorist': "Laboratorio mental donde exploramos ideas prohibidas",
            'skeptical_thinker': "Espacio donde puedo ser vulnerable sin perder mi mente crítica",
            'empathetic_emotional': "Jardín donde nuestras almas pueden sanarse mutuamente",
            'passionate_emotional': "Santuario donde la intensidad emocional es celebrada",
            'wounded_healer': "Espacio sagrado de vulnerabilidad y sanación compartida",
            'adventure_seeker': "Atlas infinito de aventuras que nadie más vivirá",
            'freedom_lover': "Territorio sin límites donde puedo ser todas mis versiones",
            'collector_explorer': "Acceso completo a todos mis universos internos"
        }
        
        return personalizations.get(sub_archetype, base_hook)
```

## FASE 4: ESTRUCTURA DE ARCHIVOS PYTHON

```
src/
├── core/
│   ├── __init__.py
│   ├── archetype_analyzer.py      # ArchetypeAnalyzer class
│   ├── diana_personality.py       # DianaPersonality system
│   ├── branching_engine.py        # BranchingEngine class
│   ├── fragment_builder.py        # FragmentBuilder class
│   ├── conversion_engine.py       # ConversionEngine class
│   └── response_time_analyzer.py  # ResponseTimeAnalyzer class
├── data/
│   ├── __init__.py
│   ├── fragments/
│   │   ├── level1_fragments.py
│   │   ├── level2_filosofa.py
│   │   ├── level2_corazon.py
│   │   └── level2_aventurera.py
│   ├── personality_templates.py
│   ├── archetype_weights.py
│   └── conversion_triggers.py
├── routes/
│   ├── __init__.py
│   ├── filosofa_route.py
│   ├── corazon_route.py
│   └── aventurera_route.py
├── utils/
│   ├── __init__.py
│   ├── timing_utils.py
│   ├── pattern_detection.py
│   └── content_adaptation.py
└── tests/
    ├── test_archetype_analysis.py
    ├── test_branching_logic.py
    ├── test_diana_evolution.py
    └── test_conversion_triggers.py
```

## INTEGRACIÓN CON SISTEMA EXISTENTE

### Punto de Entrada Principal:

```python
from src.core.archetype_analyzer import ArchetypeAnalyzer
from src.core.diana_personality import DianaPersonality
from src.core.branching_engine import BranchingEngine
from src.core.conversion_engine import ConversionEngine

class NarrativeSystem:
    def __init__(self):
        self.archetype_analyzer = ArchetypeAnalyzer()
        self.branching_engine = BranchingEngine()
        self.conversion_engine = ConversionEngine()
        self.diana_personality = None
        
    def initialize_player_session(self, l1_choices: List[Dict], timings: List[float]):
        """Inicializa sesión del jugador basada en L1"""
        
        # Analizar arquetipo del jugador
        player_archetype = self.archetype_analyzer.analyze_l1_choices(l1_choices, timings)
        
        # Inicializar Diana personalizada
        self.diana_personality = DianaPersonality(player_archetype)
        
        # Determinar ruta inicial
        initial_route = self._determine_initial_route(player_archetype)
        
        return {
            'player_archetype': player_archetype,
            'diana_initial_state': self.diana_personality.emotional_state,
            'recommended_route': initial_route
        }
    
    def process_player_interaction(self, fragment_id: str, choice: Dict) -> Dict:
        """Procesa interacción del jugador y retorna próximo fragmento"""
        
        # Determinar próximo fragmento
        next_fragment_data = self.branching_engine.determine_next_fragment(
            fragment_id, choice, self.diana_personality, {}
        )
        
        # Verificar conversión
        conversion_moment = self.conversion_engine.evaluate_conversion_readiness(
            self.diana_personality, {}
        )
        
        if conversion_moment:
            next_fragment_data['conversion'] = conversion_moment
            
        return next_fragment_data
```

## COMANDOS ESPECÍFICOS PARA CLAUDE CODE

**Para implementar esto en tu sistema Python existente:**

1. **Comando inicial:**
```bash
"Implementa la FASE 1 completa: crear archetype_analyzer.py con la clase ArchetypeAnalyzer, response_time_analyzer.py con ResponseTimeAnalyzer, y adapta el fragmento L1F1 existente para incluir las nuevas elecciones de análisis arquetípico. Mantén la estructura JSON existente pero añade los campos archetype_weights y tracking."
```

2. **Comando de integración:**
```bash
"Integra el nuevo sistema con la estructura existente, creando el punto de entrada NarrativeSystem que pueda recibir las elecciones de L1 actuales y clasificar al jugador en uno de los tres arquetipos principales (intellectual, emotional, exploratory) con sub-clasificaciones."
```

3. **Comando de testing:**
```bash
"Crea tests unitarios que validen que diferentes combinaciones de elecciones L1 produzcan clasificaciones arquetípicas distintas y coherentes."
```

¿Te sirve esta especificación técnica completa en Python?) -> Dict:
    """Función principal para clasificar arquetipo del jugador"""
    
    analyzer = ArchetypeAnalyzer()
    timing_analyzer = ResponseTimeAnalyzer()
    
    # Análisis de elecciones
    archetype_result = analyzer.analyze_l1_choices(choices, timings)
    
    # Análisis temporal
    timing_result = timing_analyzer.analyze_response_pattern(timings)
    
    # Análisis de progresión (cómo evolucionan las elecciones)
    progression_result = analyze_choice_progression(choices)
    
    # Integrar todos los análisis
    final_classification = {
        'primary_archetype': archetype_result['primary_archetype'],
        'sub_archetype': refine_sub_archetype(
            archetype_result['sub_archetype'],
            timing_result['style'],
            progression_result
        ),
        'cognitive_style': timing_result['style'],
        'confidence_level': archetype_result['confidence_level'],
        'behavioral_patterns': {
            'decision_speed': timing_result['average_time'],
            'consistency': timing_result['consistency'],
            'evolution_pattern': progression_result['pattern']
        },
        'recommended_route': determine_optimal_route(archetype_result, timing_result)
    }
    
    return final_classification

def analyze_choice_progression(choices: List[Dict]) -> Dict:
    """Analiza cómo progresionan las elecciones del jugador"""
    if len(choices) < 2:
        return {'pattern': 'insufficient_data'}
    
    # Detectar patrones de cambio en tipo de elecciones
    choice_types = [categorize_choice_type(choice['id']) for choice in choices]
    
    patterns = {
        'pattern': detect_progression_pattern(choice_types),
        'consistency': calculate_choice_consistency(choice_types),
        'risk_taking': analyze_risk_progression(choices)
    }
    
    return patterns
```

## FASE 2: CONSTRUCCIÓN DE RUTAS DIFERENCIADAS

### 2.1 SISTEMA DE DIANA EVOLUTIVA

**Crear clase `DianaPersonality` con estados:**

```javascript
class DianaPersonality {
  constructor(playerArchetype) {
    this.basePersona = this.determineBasePersona(playerArchetype);
    this.emotionalState = new EmotionalState();
    this.memorySystem = new PlayerMemory();
    this.evolutionTracker = new PersonalityEvolution();
  }
  
  // Estados específicos por arquetipo
  intellectual_trust: 0,
  emotional_openness: 0, 
  adventure_readiness: 0,
  vulnerability_level: 0,
  
  // Estados universales
  mask_level: 10, // Performance vs Autenticidad
  player_intrigue: 0,
  connection_depth: 0
}
```

### 2.2 CONSTRUCCIÓN DE FRAGMENTOS ADAPTATIVOS

**Para cada ruta principal crear:**

```
RUTA_FILOSOFA/
├── fragments/
│   ├── l2_f1_laboratorio_intimidad.js
│   ├── l2_f2_teoria_deseo.js
│   └── l2_f3_fusion_mental.js
├── personality/
│   ├── diana_filosofa_base.js
│   ├── diana_filosofa_romantica.js
│   └── diana_filosofa_pura.js
└── evolution/
    ├── trust_evolution.js
    ├── intellectual_intimacy.js
    └── mind_fusion_progression.js
```

### 2.3 SISTEMA DE MEMORIA NARRATIVA

**Implementar `PlayerMemorySystem`:**

```javascript
class PlayerMemorySystem {
  constructor() {
    this.key_moments = [];
    this.behavior_patterns = {};
    this.emotional_responses = [];
    this.diana_observations = {};
  }
  
  recordKeyMoment(fragmentId, choiceId, impact) {
    // Momentos que Diana recordará específicamente
  }
  
  updateBehaviorPattern(pattern, strength) {
    // Patrones que afectan contenido futuro
  }
  
  generateMemoryReference(currentContext) {
    // Referencias específicas a decisiones pasadas
  }
}
```

## FASE 3: ALGORITMO DE RAMIFICACIÓN INTELIGENTE

### 3.1 MOTOR DE DECISIÓN DE FRAGMENTOS

**Crear `BranchingEngine`:**

```javascript
class BranchingEngine {
  determineNextFragment(currentFragment, playerChoice, gameState) {
    // 1. Evaluar arquetipo del jugador
    const archetype = this.analyzePlayerArchetype(gameState);
    
    // 2. Consultar estado de Diana
    const dianaState = this.getDianaCurrentState(gameState);
    
    // 3. Verificar memoria de interacciones
    const memory = this.getPlayerMemory(gameState);
    
    // 4. Calcular compatibilidad de rutas
    const routeCompatibility = this.calculateRouteCompatibility(
      archetype, dianaState, memory
    );
    
    // 5. Seleccionar fragmento óptimo
    return this.selectOptimalFragment(routeCompatibility);
  }
}
```

### 3.2 GENERACIÓN DE CONTENIDO DINÁMICO

**Sistema que adapte contenido base según:**
- Memoria específica del jugador
- Evolución de Diana
- Patrones de interacción pasados
- Estado emocional actual

## FASE 4: SISTEMA DE CONVERSIÓN ADAPTATIVA

### 4.1 TRIGGERS DE CONVERSIÓN ESPECÍFICOS

**Por cada ruta crear condiciones específicas:**

```javascript
const conversionTriggers = {
  FILOSOFA: {
    condition: dianaState.intellectual_trust >= 6,
    content_hook: "Laboratorio Mental VIP",
    emotional_hook: "Conversaciones que otros no entienden"
  },
  CORAZON: {
    condition: dianaState.emotional_openness >= 6,
    content_hook: "Jardín Secreto VIP", 
    emotional_hook: "Mi vulnerabilidad real"
  },
  AVENTURERA: {
    condition: dianaState.adventure_readiness >= 6,
    content_hook: "Atlas Infinito VIP",
    emotional_hook: "Aventuras únicas juntos"
  }
};
```

## ESTRUCTURA DE ARCHIVOS REQUERIDA

```
src/
├── core/
│   ├── ArchetypeAnalyzer.js
│   ├── DianaPersonality.js
│   ├── BranchingEngine.js
│   ├── PlayerMemorySystem.js
│   └── ConversionEngine.js
├── routes/
│   ├── filosofa/
│   ├── corazon/
│   └── aventurera/
├── fragments/
│   ├── level1/
│   ├── level2/
│   └── level3/
├── data/
│   ├── player_profiles.js
│   ├── diana_states.js
│   └── memory_templates.js
└── utils/
    ├── timing_analyzer.js
    ├── pattern_detector.js
    └── content_generator.js
```

## TESTING Y VALIDACIÓN

**Crear sistema de testing que valide:**
1. Diferentes arquetipos generan rutas distintas
2. Memoria de Diana funciona correctamente
3. Evolución de personalidad es coherente
4. Conversiones son relevantes por arquetipo
5. No hay "fugas" entre rutas

## MÉTRICAS DE ÉXITO

**El sistema debe lograr:**
- 85%+ de jugadores clasificados correctamente en arquetipo
- 3+ rutas completamente diferentes en contenido
- 70%+ de referencias de memoria funcionando
- Conversiones específicas por ruta con 40%+ más efectividad

## PRIORIDAD DE IMPLEMENTACIÓN

1. **CRÍTICO:** ArchetypeAnalyzer + L1F1 rediseñado
2. **ALTO:** DianaPersonality + BranchingEngine básico  
3. **MEDIO:** PlayerMemorySystem + contenido dinámico
4. **BAJO:** Optimizaciones + sub-arquetipos avanzados

¿Te sirve este nivel de especificidad para Claude Code?
