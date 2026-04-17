---
name: obsidian-manager
description: Toolkit para gestionar notas, tareas y conocimiento en el vault de Obsidian. Úsalo para buscar contexto profundo, leer especificaciones (wiki) y registrar progresos (logs) en el Segundo Cerebro.
---

# Obsidian Manager Skill

Este skill permite al agente interactuar de forma soberana con el vault de Obsidian, siguiendo las reglas de la constitución de agentes.

## 1. Capacidades (Capabilities)
- `search_notes(query)`: Busca por nombre o contenido en las carpetas autorizadas (`wiki`, `raw`, `_agent/tasks`).
- `read_note(path)`: Recupera el contenido y metadatos (frontmatter) de una nota.
- `append_log(path, message)`: Registra eventos en notas de log existentes.

## 2. Instrucciones para el Agente (AI Instructions)
- **Soberanía Primero:** No crees archivos fuera de las áreas autorizadas.
- **RAG Precedencia:** Antes de preguntar al usuario algo que pueda estar documentado, usa `search_notes` o confía en el contexto RAG inyectado por el orquestador.
- **Formato:** Mantén siempre el frontmatter YAML en las notas que edites.
- **Tareas:** Si detectas una nota con `type: task` y `status: pending`, puedes proponer ejecutarla.

## 3. Comandos de Referencia
El skill puede ser invocado mediante el script de soporte:
```bash
python3 skills/obsidian-manager/scripts/vault_ops.py search "termino"
python3 skills/obsidian-manager/scripts/vault_ops.py read "wiki/especificacion.md"
```

## 4. Estructura del Vault Autorisada
- `wiki/`: Conocimiento estructurado, reglas, arquitectura.
- `raw/`: Notas rápidas, ingesta de datos sin procesar.
- `_agent/tasks/`: Tareas asignadas al sistema.
- `_agent/memory/`: Memoria persistente de sesiones.

---
*Obsidian Manager Authorized. Contextual synthesis ready.*
