# Context Monitoring & Slash Commands Research
**Date:** 2026-03-13
**Scope:** Claude Code agents, context detection, /rewind, orchestrator patterns

---

## Question 1: ¿Pueden los agentes spawneados ejecutar slash commands como /compact, /clear, /rewind?

### Respuesta corta: SÍ — con una excepción importante

Los agentes spawneados (subagentes o teammates) pueden ejecutar `/compact` y `/clear` programáticamente, pero **NO pueden ejecutar `/rewind`**.

### Evidencia

La documentación oficial del Agent SDK (`platform.claude.com/docs/en/agent-sdk/slash-commands`) documenta explícitamente cómo los agentes pueden enviar slash commands:

```python
from claude_agent_sdk import query

# Un agente puede ejecutar /compact así:
async for message in query(prompt="/compact", options={"max_turns": 1}):
    if message.type == "system" and message.subtype == "compact_boundary":
        print("Pre-compaction tokens:", message.compact_metadata.pre_tokens)
```

Los slash commands disponibles para agentes vía SDK incluyen `/compact`, `/clear`, y `/help`. El SDK expone la lista en el mensaje de inicialización del sistema (`message.slash_commands`).

### La excepción crítica: /rewind y /init

La documentación oficial de Skills (`code.claude.com/docs/en/skills`) contiene esta nota literal:

> **"Built-in commands like `/compact` and `/init` are not available through the Skill tool."**

Y el sistema de checkpointing/rewind está diseñado exclusivamente como interfaz interactiva humana:
- Se activa con `Esc + Esc` o el comando `/rewind`
- Muestra una lista scrollable donde el humano selecciona el punto de restauración
- Requiere interacción de teclado para elegir entre opciones (restaurar código, conversación, ambos, o summarizar)

**Conclusión sobre Pregunta 1:**
- `/compact` → **SÍ, disponible para agentes vía Agent SDK**
- `/clear` → **SÍ, disponible para agentes vía Agent SDK**
- `/rewind` → **NO, es UI interactiva humana exclusivamente**
- Skills no pueden invocar `/compact` ni `/init` (pero el SDK sí puede)

---

## Question 2: ¿Puede un agente detectar su propio porcentaje de uso de contexto programáticamente?

### Respuesta corta: PARCIALMENTE — solo vía StatusLine hook, no directamente desde dentro del agente

### Mecanismo disponible: StatusLine

La única vía documentada para acceder al porcentaje de contexto en tiempo real es el **StatusLine hook** (`code.claude.com/docs/en/statusline`). Este hook recibe JSON con los siguientes campos relevantes:

```json
{
  "context_window": {
    "total_input_tokens": 15234,
    "total_output_tokens": 4521,
    "context_window_size": 200000,
    "used_percentage": 8,
    "remaining_percentage": 92,
    "current_usage": {
      "input_tokens": 8500,
      "cache_creation_input_tokens": 5000,
      "cache_read_input_tokens": 2000
    }
  }
}
```

El campo `context_window.used_percentage` está pre-calculado. El script de StatusLine puede leerlo y tomar acciones (escribir a un archivo, trigger externo, etc.).

### Limitación crítica

La fuente `claudefa.st/blog/guide/mechanics/context-buffer-management` documenta:

> **"StatusLine is the only live context monitor — Other hooks don't receive token counts."**

Y:

> **"hooks cannot inject /clear commands — they can only add context, not replace user input."**

Esto significa que:
1. Un agente **no puede consultar su propio porcentaje de contexto** mediante ninguna herramienta interna
2. La única forma de obtener el dato es **externamente** mediante StatusLine
3. StatusLine puede escribir el dato a un archivo que el agente lea via Bash
4. Los hooks no pueden disparar `/compact` ni `/clear` directamente

### Workaround documentado

El patrón que emerge de la comunidad:

```bash
# StatusLine escribe porcentaje a archivo temporal
#!/bin/bash
input=$(cat)
PCT=$(echo "$input" | jq -r '.context_window.used_percentage // 0' | cut -d. -f1)
echo "$PCT" > /tmp/claude-context-pct
```

Un agente puede entonces leer este archivo vía Bash para obtener una aproximación:
```bash
cat /tmp/claude-context-pct
```

Aunque este enfoque es indirecto y el valor puede estar desfasado (StatusLine se actualiza cada mensaje de asistente, debounced a 300ms).

### Auto-compaction automática

Claude Code tiene auto-compaction integrada que se dispara al ~83.5% de uso del contexto (aproximadamente 167K tokens en una ventana de 200K). Desde early 2026, el buffer reservado bajó de ~45K a ~33K tokens (16.5%), dando 12K tokens adicionales por sesión.

**Conclusión sobre Pregunta 2:**
- No existe API ni variable de entorno que un agente pueda consultar directamente para obtener su % de contexto
- El único mecanismo oficial es StatusLine → archivo → Bash read (indirecto)
- La auto-compaction ocurre automáticamente, el agente no necesita monitorearlo para sobrevivir
- El Agent SDK expone `compact_metadata.pre_tokens` al recibir el evento `compact_boundary`, que al menos confirma cuándo ocurrió una compactación

---

## Question 3: ¿Qué es exactamente /rewind? ¿Cómo es diferente de /compact?

### Definición oficial

`/rewind` (alias `/checkpoint`) es el comando de checkpointing de Claude Code. Se activa con `Esc + Esc` o escribiendo `/rewind`. Abre un menú interactivo con la lista de prompts del usuario en la sesión actual.

**Fuente:** `code.claude.com/docs/en/checkpointing` y `code.claude.com/docs/en/interactive-mode`

### ¿Qué permite hacer?

Desde el menú de rewind, el usuario puede seleccionar cualquier punto previo de la conversación y elegir una de 5 acciones:

| Opción | Efecto |
|--------|--------|
| **Restore code and conversation** | Revierte ambos al estado previo al punto seleccionado |
| **Restore conversation** | Retrocede la conversación, mantiene cambios de código |
| **Restore code** | Deshace cambios de archivos, mantiene conversación |
| **Summarize from here** | Comprime la conversación desde ese punto hacia adelante (sin cambiar archivos) |
| **Never mind** | Cancela sin cambios |

### ¿Cómo funciona internamente?

- Cada prompt del usuario crea automáticamente un checkpoint
- Los checkpoints persisten entre sesiones (disponibles al hacer `--continue` o `--resume`)
- Se limpian automáticamente a los 30 días (configurable)
- Solo trackea cambios hechos por las **herramientas de edición de archivos de Claude**
- **NO trackea** cambios hechos por bash commands (rm, mv, cp, etc.)
- **NO trackea** cambios externos (manual, otras sesiones)

### Diferencias clave con /compact

| Dimensión | /rewind | /compact |
|-----------|---------|----------|
| **Propósito** | Restaurar estado anterior (deshacer) | Reducir tokens del contexto actual |
| **Disponible para agentes** | NO (solo UI interactiva humana) | SÍ (vía Agent SDK) |
| **Afecta archivos en disco** | SÍ (puede restaurar código) | NO |
| **Afecta conversación** | SÍ (puede restaurar o comprimir) | SÍ (comprime historial) |
| **Invocación** | Esc+Esc o `/rewind` | `/compact [instrucciones]` |
| **Opción "Summarize from here"** | Disponible como sub-opción | No disponible como sub-opción |
| **Reversible** | NO (el rewind en sí no se puede deshacer fácilmente) | Parcialmente |

### Cuándo usar cada uno

- **`/rewind`**: Claude fue en la dirección equivocada y necesitas deshacer cambios de código o limpiar historial desde un punto específico
- **`/compact`**: El contexto se está llenando pero el trabajo va bien; solo necesitas liberar espacio preservando el progreso
- **`/rewind` > Summarize from here**: Útil para comprimir solo una parte de la conversación (debugging verbose) sin perder el contexto inicial

---

## Question 4: ¿Cuál es la mejor práctica verificada para que un orchestrator maneje el riesgo de quedarse sin contexto durante multi-round?

### Respuesta: No existe un patrón establecido de auto-monitoreo. La estrategia es preventiva y arquitectural.

### Hallazgos verificados en fuentes oficiales y comunidad

#### 4.1 Auto-compaction: el safety net básico

Claude Code auto-compacta al ~83.5% de uso del contexto. Los planes y To-Do items persisten a través de compactaciones. La documentación oficial (`code.claude.com/docs/en/best-practices`) confirma:

> "Claude Code automatically compacts conversation history when you approach context limits, which preserves important code and decisions while freeing space."

**Para el orchestrator:** La auto-compaction es el mecanismo de último recurso. No requiere código especial del agente. Sin embargo, la performance de Claude degrada antes del threshold de compaction.

#### 4.2 Compactación manual estratégica en checkpoints lógicos

La práctica más documentada es que el orchestrator ejecute `/compact` en puntos lógicos del workflow (entre rounds, no al borde del límite):

```python
# Agente puede programáticamente compactar vía Agent SDK
async for message in query(prompt="/compact Focus on the API changes completed in Round 1", options={"max_turns": 1}):
    if message.type == "system" and message.subtype == "compact_boundary":
        round_1_done = True
```

**Patrón recomendado:** Customizar el comportamiento de compactación en CLAUDE.md:
```markdown
# Compact Instructions
When compacting, always preserve:
- Current round number and completed tasks
- Full list of modified files
- Any pending verification commands
- Key architectural decisions made in this session
```

#### 4.3 Subagentes para investigación: el patrón más efectivo

La documentación oficial (`best-practices`) es explícita:

> "Use subagents for investigation. Delegate research with 'use subagents to investigate X'. They explore in a separate context, keeping your main conversation clean for implementation."

Para un orchestrator multi-round, esto significa:
- El orchestrator mantiene solo el estado de alto nivel (qué rounds completados, resultados)
- Toda investigación/implementación se delega a subagentes/teammates con su propio contexto
- Los subagentes reportan resúmenes de vuelta, no sus conversaciones completas

#### 4.4 CLAUDE.md: reducción de contexto upfront

La documentación de agent-teams (`claudefa.st/blog/guide/agents/agent-teams`) confirma:

> "Three teammates reading a clear CLAUDE.md is far cheaper than three teammates exploring the codebase independently."

Un CLAUDE.md bien estructurado con límites de módulos, comandos de verificación y contexto operacional reduce significativamente el costo de contexto por teammate.

#### 4.5 Monitoreo indirecto vía StatusLine + archivo compartido

El único mecanismo para que un agente "sepa" cuánto contexto tiene es el workaround de StatusLine:

1. StatusLine escribe el porcentaje a `/tmp/claude-context-pct`
2. El agente (via Bash) lee ese archivo periódicamente
3. Si el porcentaje supera un threshold (ej. 70%), el agente envía un mensaje al team lead vía SendMessage

Ejemplo de instrucción en prompt del orchestrator:
```
If you detect your context usage exceeds 70% (check via: cat /tmp/claude-context-pct),
send a message to "claude-main" with: "CONTEXT WARNING: Context at [PCT]%.
Requesting /compact before next round."
```

#### 4.6 Handoff proactivo entre rounds: patrón documental

El patrón más robusto documentado en la comunidad para multi-round es escribir un **handoff document** al final de cada round:

```markdown
# Round N Completion Handoff

## Completed
- [lista específica]

## Files Modified
- [lista exacta con paths]

## Next Round Objective
- [instrucción clara]

## Context State
- Estimated context usage: [PCT]%
- Auto-compact triggered: [YES/NO]
```

El orchestrator puede entonces iniciar la siguiente ronda con `/clear` + inyección del handoff document, en lugar de mantener todo en un solo contexto creciente. Esto es más confiable que el monitoreo en tiempo real.

### Resumen de patrones por prioridad

| Prioridad | Patrón | Costo |
|-----------|--------|-------|
| P1 | CLAUDE.md detallado con instrucciones de compactación | Upfront, una vez |
| P2 | Subagentes para todas las tareas de investigación | Por tarea |
| P3 | `/compact` manual al final de cada round lógico | Por round |
| P4 | Handoff document + `/clear` entre rounds | Por round |
| P5 | StatusLine → archivo → Bash read para monitoreo indirecto | Overhead constante |
| Fallback | Auto-compaction (83.5%) + degradación de performance | Automático |

---

## Conclusiones Generales

1. **Los agentes pueden ejecutar /compact y /clear vía Agent SDK**, pero `/rewind` es exclusivo de la interfaz interactiva humana y no está disponible para agentes.

2. **No existe mecanismo directo para que un agente detecte su % de contexto**. El único mecanismo oficial es StatusLine, que escribe al stdout y puede escribirse a un archivo que el agente lea vía Bash (workaround indirecto).

3. **`/rewind` es un sistema de checkpointing con restauración selectiva** (código, conversación, o ambos) más poderoso que `/compact`. La opción "Summarize from here" de `/rewind` es la más similar a `/compact` pero dirigida a un segmento específico.

4. **La mejor práctica para orchestrators multi-round no es el auto-monitoreo de contexto sino la arquitectura preventiva**: CLAUDE.md con instrucciones de compactación, delegation de investigación a subagentes, `/compact` manual entre rounds, y handoff documents para reinicios limpios entre rounds largos.

---

## Fuentes

- [Claude Code Slash Commands Official](https://code.claude.com/docs/en/slash-commands)
- [Agent SDK Slash Commands](https://platform.claude.com/docs/en/agent-sdk/slash-commands)
- [Claude Code Checkpointing](https://code.claude.com/docs/en/checkpointing)
- [Claude Code Best Practices](https://code.claude.com/docs/en/best-practices)
- [Claude Code Interactive Mode](https://code.claude.com/docs/en/interactive-mode)
- [Claude Code Skills Documentation](https://code.claude.com/docs/en/skills)
- [Claude Code StatusLine](https://code.claude.com/docs/en/statusline)
- [Context Buffer Management - claudefa.st](https://claudefa.st/blog/guide/mechanics/context-buffer-management)
- [Agent Teams - claudefa.st](https://claudefa.st/blog/guide/agents/agent-teams)
- [Claude Code Context Window Issue #28962](https://github.com/anthropics/claude-code/issues/28962)
