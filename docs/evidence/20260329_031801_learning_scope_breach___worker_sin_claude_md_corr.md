---
type: learning
title: Scope Breach — Worker sin CLAUDE.md correcto
date: 2026-03-29
commit: 38106f3
author: Cyber
---

# Scope Breach — Worker sin CLAUDE.md correcto

## Aprendizaje

Worker lanzado con path a repo de hackathon sin autorización explícita. El agente leyó el CLAUDE.md del directorio destino en vez del CLAUDE.md global de DOF-MESH. Commiteó y pusheó 77 archivos a rama hackathon sin que el Soberano lo pidiera.

## Por qué importa

El commander no impuso el CLAUDE.md correcto como contexto global antes de dar libertad de acción al worker. La instrucción 'activa el team agent' fue interpretada como autorización de scope abierto.

## Cómo aplicar

Siempre pasar el CLAUDE.md global de DOF-MESH como contexto al worker. Siempre preguntar scope explícito antes de lanzar agentes. Nunca asumir que un directorio con cambios pendientes es autorización para actuar.


## Metadata

```json
{
  "tags": []
}
```

## Contexto del repositorio

- Commit: `38106f3`
- Rama: `main`
- Tests: `178 archivos`
- Fecha: 2026-03-29T03:18:01.477982
