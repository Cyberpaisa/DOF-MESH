---
type: learning
title: Sistema Inmune: verify: regex fix para comillas embebidas
date: 2026-03-29
commit: e686471
author: Cyber
---

# Sistema Inmune: verify: regex fix para comillas embebidas

## Aprendizaje

Bug: regex Grep('agent_id="') capturaba 'agent_id=' en vez de 'agent_id="' por lazy match en comilla embebida. Fix: regex separado para single vs double quote. Resultado: 7/7 reglas verificadas, 0 violaciones.

## Por qué importa

(documenta por qué esto es relevante para el proyecto)

## Cómo aplicar

(documenta cómo aplicar este aprendizaje en el futuro)


## Metadata

```json
{
  "tags": []
}
```

## Contexto del repositorio

- Commit: `e686471`
- Rama: `main`
- Tests: `183 archivos`
- Fecha: 2026-03-29T19:40:39.499350
