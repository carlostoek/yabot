# Sistema de Ramificación Narrativa - Diana Los Kinkys

## 1. ARQUITECTURA DE VARIABLES DE ESTADO

### Variables Núcleo del Jugador
```javascript
playerArchetype = {
  // Arquetipos Primarios (0-10)
  observer: 0,        // Qué tanto analiza vs actúa
  intimate: 0,        // Busca cercanía vs mantiene distancia  
  explorer: 0,        // Curiosidad vs satisfacción actual
  vulnerable: 0,      // Apertura emocional vs protección
  authentic: 0,       // Honestidad vs performance social
  
  // Arquetipos Secundarios
  philosophical: 0,   // Abstracto vs concreto
  artistic: 0,        // Aprecia proceso vs resultado
  reciprocal: 0,      // Da tanto como recibe
  committed: 0,       // Busca profundidad vs variedad
  budgetConscious: 0  // Considera costo vs impulso
}

dianaState = {
  // Estado Emocional de Diana
  trust: 0,           // Qué tanto confía en el jugador
  vulnerability: 0,   // Qué tanto se abre
  intrigue: 0,        // Qué tanto le interesa conocerlo
  comfort: 0,         // Qué tan cómoda se siente
  
  // Estados Relacionales
  seenLevel: 0,       // Qué tanto siente que la entienden
  reciprocityDesire: 0, // Cuánto quiere conocerlo a él
  intimacyReadiness: 0, // Preparación para mayor cercanía
  
  // Estados Narrativos
  maskLevel: 10,      // Qué tan performativa está (10=máximo, 0=auténtica)
  revelationCount: 0, // Cuántas capas ha mostrado
  connectionDepth: 0  // Profundidad de conexión alcanzada
}
```

## 2. SISTEMA DE RAMIFICACIÓN POR ARQUETIPOS

### Ejemplo: Nivel 1, Fragmento 1
**Elección Original:** "Me intriga eso de 'crear una posibilidad'"

**Nueva Ramificación:**

```javascript
// Si player.observer > 5 && player.philosophical > 3
→ RAMA_FILOSOFICA: "Diana profundiza en teorías de percepción"

// Si player.observer > 5 && player.philosophical <= 3  
→ RAMA_ANALITICA: "Diana explica mecánicamente cómo lee a las personas"

// Si player.observer <= 5 && player.intimate > 4
→ RAMA_EXPERIENCIAL: "Diana propone experimentar en lugar de explicar"
```

### Consecuencias Diferidas Ejemplo:

**L1F1:** Jugador muestra alta vulnerabilidad
→ **L2F2:** Diana recuerda esta apertura y se arriesga más
→ **L3F1:** Diana revela miedos personales
→ **L4F2:** Se abre sobre experiencias pasadas dolorosas

## 3. VARIABLES DE ESTADO EVOLUTIVAS

### Sistema de Memoria Narrativa
```javascript
narrativeMemory = {
  // Momentos Clave Recordados
  firstImpression: "analytical" | "intimate" | "mysterious",
  deepestMoment: "L2F3_vulnerability" | "L3F1_reciprocity" | null,
  repeatedPatterns: ["always_chooses_depth", "avoids_commitment"],
  
  // Evolución del Personaje  
  dianaEvolution: {
    initialMask: "performative_seductive",
    currentMask: "authentic_curious", 
    unlocked_aspects: ["artist", "philosopher", "wounded_healer"]
  }
}
```

## 4. ESTRUCTURA DE RAMIFICACIÓN REAL

### Nivel 2 Rediseñado - Múltiples Rutas

#### RUTA A: Para Observadores Filosóficos
```
L2F1_A: "El Laboratorio de Percepciones"
- Diana muestra su proceso mental de lectura de personas
- Elecciones sobre teorías de conexión humana
- Lleva a L2F2_A: Experimentos de percepción mutua

L2F2_A: "Espejos Dobles" 
- Diana y el jugador analizan cómo se ven mutuamente
- Introduce elementos de psicología profunda
- Lleva a L2F3_A: Reconocimiento intelectual

L2F3_A: "La Mente Compartida"
- Conversión: "Acceso VIP Intelectual" - sesiones de análisis profundo
```

#### RUTA B: Para Íntimos Vulnerables  
```
L2F1_B: "El Jardín Secreto"
- Diana comparte un espacio emocional personal
- Elecciones sobre reciprocidad emocional  
- Lleva a L2F2_B: Intercambio de vulnerabilidades

L2F2_B: "Confesiones Cruzadas"
- Diana revela miedos, jugador debe hacer lo mismo
- Estado emocional afecta futuras interacciones
- Lleva a L2F3_B: Intimidad auténtica

L2F3_B: "El Abrazo Invisible"
- Conversión: "Acceso VIP Íntimo" - conexión emocional profunda
```

#### RUTA C: Para Exploradores Curiosos
```
L2F1_C: "El Mapa de Posibilidades"  
- Diana presenta múltiples facetas de sí misma
- Elecciones sobre qué explorar primero
- Lleva a L2F2_C: Aventura de descubrimiento

L2F2_C: "Puertas Múltiples"
- Cada elección abre rutas completamente diferentes
- Sistema de colección: aspectos de Diana a descubrir
- Lleva a L2F3_C: Maestría exploratoria

L2F3_C: "El Explorador Experto"  
- Conversión: "Acceso VIP Explorador" - contenido variado y sorpresivo
```

## 5. SISTEMA DE CONSECUENCIAS REALES

### Efectos de Arquetipos en Contenido Futuro

**Si Jugador = Alto Observer + Alto Vulnerable:**
- Diana desarrolla lado "profesora íntima"
- Contenido: Explicaciones profundas + apertura emocional
- Finales disponibles: "Almas Gemelas Analíticas"

**Si Jugador = Alto Intimate + Bajo Reciprocal:**
- Diana se vuelve gradualmente más cerrada
- Contenido: Frustraciones sutiles, tests de reciprocidad
- Finales disponibles: "Límites Saludables"

**Si Jugador = Alto Explorer + Alto Budget Conscious:**
- Diana crea experiencias de "máximo valor"
- Contenido: Variedad dentro de nivel gratuito
- Finales disponibles: "Compañeros de Aventura"

## 6. IMPLEMENTACIÓN TÉCNICA

### Función de Evaluación de Ruta
```javascript
function determineNextFragment(currentFragment, playerChoice, gameState) {
  // Evaluar arquetipos primarios
  const primaryArchetype = getPrimaryArchetype(gameState.playerArchetype);
  
  // Verificar variables de estado de Diana
  const dianaReadiness = evaluateDianaState(gameState.dianaState);
  
  // Calcular ruta basada en historial + elección actual
  const routeWeight = calculateRouteCompatibility(
    gameState.narrativeMemory,
    playerChoice,
    primaryArchetype
  );
  
  return selectOptimalFragment(routeWeight, dianaReadiness);
}
```

### Sistema de Puntos Rediseñado
- **Puntos de Superficie:** Lo que ve el jugador
- **Puntos de Arquetipos:** Variables ocultas que afectan contenido
- **Puntos de Estado:** Cómo se siente Diana hacia el jugador
- **Puntos de Momento:** Impacto emocional de decisiones específicas

## 7. EJEMPLOS DE RAMIFICACIÓN EXTREMA

### Escenario: L3F2 "La Evaluación del Alma"

**Jugador Tipo A (Vulnerable + Honesto):**
- Diana pregunta sobre heridas más profundas
- Contenido sobre sanación mutua
- Ruta hacia "Diván Terapéutico"

**Jugador Tipo B (Filosófico + Cerrado):**
- Diana pregunta sobre teorías de amor y deseo  
- Contenido sobre exploración intelectual de la intimidad
- Ruta hacia "Diván Académico"

**Jugador Tipo C (Exploratorio + Impaciente):**
- Diana acelera el proceso, muestra múltiples facetas rápidamente
- Contenido de alta variación y sorpresa
- Ruta hacia "Diván Aventura"

## 8. VARIABLES DE CONVERSIÓN ADAPTATIVAS

### Conversión Basada en Arquetipo Real
- **Observer:** "Contenido que otros no pueden interpretar"
- **Intimate:** "Conexión que trasciende lo físico"  
- **Explorer:** "Acceso a todas mis facetas"
- **Vulnerable:** "Espacio seguro para ser reales"
- **Authentic:** "Sin máscaras, sin performance"

Esta arquitectura asegura que cada jugador viva una historia completamente diferente, donde sus elecciones realmente importan y where Diana evoluciona de manera coherente basada en quién es él realmente.
