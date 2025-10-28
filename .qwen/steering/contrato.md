
## 📜 **CONTRATO DE SISTEMA: DIANABOT v1.0**

Este documento define las estructuras de datos, variables globales, interfaces y reglas de comunicación entre módulos. **Todo código generado por Qwen Code DEBE respetar este contrato.**

---

### 1. 🆔 **Estructura Canónica del Usuario (User Profile)**

Esta es la unidad fundamental de datos. Todos los módulos leen y escriben en esta estructura. Se almacena en la base de datos y se carga en memoria cuando un usuario interactúa con el bot.

```python
# Estructura en Python (Dict o Clase Dataclass)
user_profile = {
    "telegram_id": 123456789,          # int - ID único de Telegram. CLAVE PRIMARIA.
    "username": "@ejemplo",            # str - Nombre de usuario de Telegram (puede ser None).
    "first_name": "Nombre",            # str - Nombre del usuario en Telegram.
    "kisses": 50,                      # int - Saldo de besitos.
    "inventory": ["llave_jardin", "pista_01"], # list[str] - Lista de IDs de objetos poseídos.
    "achievements": ["primer_besito", "decision_valiente"], # list[str] - Lista de IDs de logros obtenidos.
    "role": "free",                    # str - Rol del usuario. Valores: "free" | "vip"
    "vip_expiry": None,                # datetime | None - Fecha de expiración de la suscripción VIP. None si es free.
    "last_daily_claim": "2024-05-27",  # str (YYYY-MM-DD) - Última fecha en que reclamó besitos diarios.
    "current_narrative_fragment": "L1_S1", # str - ID del último fragmento narrativo visto/activo.
    "narrative_choices": {             # dict - Registro de decisiones tomadas en la historia.
        "L1_S1": "opcion_A",
        "L2_S3": "opcion_C"
    },
    "metadata": {                      # dict - Datos adicionales para futuras expansiones.
        "last_interaction": "2024-05-27T10:30:00Z"
    }
}
```

> **Regla de Oro #1:** Esta es la única estructura de usuario. Cualquier módulo que necesite información del usuario debe cargar este perfil completo, modificarlo y guardarlo de vuelta. No se crean estructuras paralelas.

---

### 2. 📖 **Estructura Canónica del Fragmento Narrativo (Narrative Fragment)**

Define cómo se almacena y procesa cada parte de la historia. Se guarda en archivos `.json` dentro de la carpeta `narrative/`.

```json
{
  "fragment_id": "L1_S1",           // string - ID único del fragmento. DEBE coincidir con el nombre del archivo (L1_S1.json).
  "title": "El Salón de Lucien",    // string - Título del fragmento (opcional para UI).
  "text": "Lucien te da la bienvenida...", // string - El texto narrativo que se mostrará al usuario.
  "required_role": "free",          // string - Rol mínimo para ver este fragmento. "free" | "vip"
  "required_kisses": 0,             // int - Cantidad mínima de besitos necesarios. 0 si no se requiere.
  "required_items": [],             // list[string] - Lista de IDs de objetos que el usuario DEBE tener en su inventario.
  "required_achievements": [],      // list[string] - Lista de IDs de logros que el usuario DEBE tener.
  "options": [                      // list[Option] - Lista de opciones que el usuario puede elegir.
    {
      "option_id": "opcion_A",      // string - ID único de esta opción dentro del fragmento.
      "text": "Aceptar la invitación", // string - Texto del botón que verá el usuario.
      "next_fragment": "L1_S2A",    // string - ID del fragmento al que lleva esta opción.
      "rewards": {                  // dict - Recompensas que se otorgan al elegir esta opción.
        "kisses": 5,                // int - Besitos a añadir.
        "items": ["llave_jardin"],  // list[string] - IDs de objetos a añadir al inventario.
        "achievements": ["decision_valiente"] // list[string] - IDs de logros a desbloquear.
      },
      "conditions": {               // dict - Condiciones OCULTAS para que esta opción aparezca (opcional, para metajuego).
        "has_seen_fragment": ["pista_canal_01"]
      }
    },
    {
      "option_id": "opcion_B",
      "text": "Pedir más tiempo",
      "next_fragment": "L1_S2B",
      "rewards": {
        "kisses": 2,
        "items": []
      }
    }
  ],
  "is_final": false                 // boolean - Indica si este fragmento es un final de historia.
}
```

> **Regla de Oro #2:** El motor narrativo carga un fragmento por su `fragment_id`, verifica TODAS las condiciones (`required_role`, `required_kisses`, etc.) contra el `user_profile`. Solo si todo coincide, se muestra. Luego, registra la elección en `user_profile["narrative_choices"]` y aplica las recompensas de la opción elegida.

---

### 3. 🎮 **Estructura Canónica de un Objeto de Inventario (Inventory Item)**

Se define en archivos `.json` dentro de la carpeta `items/`.

```json
{
  "item_id": "llave_jardin",        // string - ID único del objeto. DEBE coincidir con el nombre del archivo.
  "name": "Llave del Jardín",       // string - Nombre amigable del objeto.
  "description": "Una antigua llave de bronce que abre el jardín trasero.", // string - Descripción.
  "type": "key",                    // string - Tipo de objeto (key, consumable, collectible, etc.).
  "is_narrative_key": true          // boolean - Si es necesario para desbloquear fragmentos narrativos.
}
```

---

### 4. 🏆 **Estructura Canónica de un Logro (Achievement)**

Se define en archivos `.json` dentro de la carpeta `achievements/`.

```json
{
  "achievement_id": "decision_valiente", // string - ID único del logro.
  "name": "Decisión Valiente",      // string - Nombre del logro.
  "description": "Tomaste la decisión más arriesgada en el Salón de Lucien.", // string - Descripción.
  "reward_kisses": 10,              // int - Besitos que se otorgan al desbloquearlo.
  "reward_items": [],               // list[string] - Objetos que se otorgan.
  "unlocks_narrative": []           // list[string] - IDs de fragmentos que se desbloquean al obtener este logro.
}
```

---

### 5. 🔗 **Interfaces y Contratos entre Módulos**

Para evitar que los módulos se "pisen" entre sí, definimos funciones con contratos claros.

#### a) **Módulo de Base de Datos (`database/user_db.py`)**
```python
def get_user_profile(telegram_id: int) -> dict:
    """
    Contrato: Devuelve el perfil completo del usuario. Si no existe, lo crea con valores por defecto.
    Valores por defecto: kisses=5, role='free', inventory=[], achievements=[], etc.
    """

def save_user_profile(telegram_id: int, profile: dict) -> bool:
    """
    Contrato: Guarda el perfil completo del usuario en la base de datos.
    Devuelve True si tuvo éxito, False en caso de error.
    """

def update_user_kisses(telegram_id: int, delta: int) -> int:
    """
    Contrato: Añade (o resta, si delta es negativo) besitos al usuario.
    Devuelve el nuevo saldo total de besitos.
    Internamente, carga el perfil, modifica 'kisses', y lo guarda.
    """

def add_item_to_inventory(telegram_id: int, item_id: str) -> bool:
    """
    Contrato: Añade un item al inventario del usuario si no lo tiene ya.
    Devuelve True si se añadió, False si ya lo tenía o hubo error.
    """

def grant_achievement(telegram_id: int, achievement_id: str) -> bool:
    """
    Contrato: Otorga un logro al usuario si no lo tiene.
    Aplica las recompensas definidas en el archivo del logro (besitos, items, desbloqueos).
    Devuelve True si se otorgó, False si ya lo tenía o hubo error.
    """
```

#### b) **Módulo Narrativo (`handlers/narrative_engine.py`)**
```python
def load_narrative_fragment(fragment_id: str) -> dict:
    """
    Contrato: Carga y devuelve el diccionario del fragmento desde su archivo JSON.
    Lanza una excepción si el archivo no existe.
    """

def can_user_access_fragment(user_profile: dict, fragment: dict) -> tuple[bool, str]:
    """
    Contrato: Verifica si el usuario puede acceder al fragmento.
    Devuelve una tupla: (puede_acceder: bool, mensaje_de_error: str)
    Ejemplo: (False, "Necesitas 10 besitos para continuar.")
    Verifica: role, kisses, required_items, required_achievements.
    """

def process_narrative_choice(user_profile: dict, fragment_id: str, option_id: str) -> dict:
    """
    Contrato: Procesa la elección del usuario en un fragmento.
    1. Registra la elección en user_profile['narrative_choices'].
    2. Aplica las recompensas (kisses, items, achievements) definidas en la opción.
    3. Devuelve el user_profile MODIFICADO (pero NO guardado en DB).
    Es responsabilidad del handler guardar el perfil después.
    """
```

#### c) **Módulo de Gamificación (`handlers/gamification.py`)**
```python
def claim_daily_reward(telegram_id: int) -> dict:
    """
    Contrato: Intenta otorgar la recompensa diaria.
    Devuelve un dict con: {"success": bool, "message": str, "kisses_awarded": int}
    Verifica last_daily_claim. Si ya lo reclamó hoy, success=False.
    """

def start_trivia(telegram_id: int, question_id: str) -> dict:
    """
    Contrato: Inicia una trivia para el usuario.
    Devuelve la pregunta y opciones. Guarda en el perfil que la trivia está activa.
    """
```

---

### 6. 🔄 **Flujo de Trabajo Estándar para una Interacción**

Cuando un usuario hace algo (por ejemplo, elige una opción en la historia), el flujo DEBE ser:

1.  **Cargar:** `user_profile = get_user_profile(telegram_id)`
2.  **Procesar:** `user_profile = process_narrative_choice(user_profile, fragment_id, option_id)`
3.  **Guardar:** `save_user_profile(telegram_id, user_profile)`
4.  **Mostrar:** Enviar el siguiente fragmento o mensaje de confirmación al usuario.

> **Regla de Oro #3:** Nunca modificar el perfil sin cargarlo primero y guardarlo después. Siempre se trabaja con la versión más reciente de la base de datos.

---

### 7. 📂 **Estructura de Archivos y Carpetas Definitiva**

```
dianabot/
├── main.py
├── config.py
├── database/
│   ├── user_db.py          # TODAS las operaciones CRUD del perfil de usuario.
│   └── db.json             # (O SQLite) - Almacenamiento.
├── handlers/
│   ├── start.py
│   ├── help.py
│   ├── narrative_engine.py # Motor narrativo central.
│   ├── gamification.py     # Misiones, trivias, tienda.
│   └── admin.py            # Gestión de roles VIP, canales.
├── narrative/
│   ├── L1_S1.json          # Fragmentos narrativos.
│   ├── L1_S2A.json
│   └── L1_S2B.json
├── items/
│   ├── llave_jardin.json   # Definiciones de objetos.
│   └── pista_01.json
├── achievements/
│   ├── decision_valiente.json # Definiciones de logros.
│   └── primer_besito.json
└── utils/
    └── validators.py       # Funciones de validación reutilizables.
```

---

Este contrato elimina la ambigüedad. Cuando le pidas a Qwen Code que haga algo, puedes referirte a este documento.

**Ejemplo de Instrucción para Qwen Code:**
> "Qwen, en el archivo `handlers/narrative_engine.py`, implementa la función `can_user_access_fragment` según el Contrato de Sistema. Debe verificar el rol, los besitos, los items y los logros del `user_profile` contra los requisitos del `fragment`. Devuelve `(True, "")` si puede acceder, o `(False, "Mensaje de error específico")` si no."
