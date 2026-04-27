# Best Practices for Benchmarking
> [!NOTE]
> **URL Original:** [https://platform.kimi.ai/docs/benchmark-best-practice](https://platform.kimi.ai/docs/benchmark-best-practice)
> **Tópico:** #API
> **Sincronización:** 2026-04-23 20:53:23

## 📝 Resumen Ejecutivo
Analizando contenido estructurado...

## ⚙️ Detalles Técnicos
- **Endpoints detectados:** Ninguno
- **Tablas de datos:** 0 detectadas.

## 💎 Contenido Destilado
> ## Documentation Index
> Fetch the complete documentation index at: https://platform.kimi.ai/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Best Practices for Benchmarking

Benchmarking is an **engineering task** that needs stability and reproducibility. You'll be calling the model thousands of times; even tiny drifts in system setup or network latency can compromise result accuracy. Here's what we've learned to keep things reproducible and trustworthy.

**Quick notes**

* For any **unlisted** or **closed-source** benchmark:  set`temperature = 1.0`, `stream = true`, `top_p = 0.95`
* **Reasoning benchmarks**: `max_tokens = 128k`, and run at least **500–1000 samples** to get low variance (e.g. `AIME 2025`: 32 runs -> 30 × 32 = 960 questions)
* **Coding benchmarks**: `max_tokens = 256k`
* **Agentic task benchmarks:**
  * For multi-hop search: `max_tokens = 256k` + context management
  * Others: `max_tokens ≥ 16k–64k`

## K2.6 Models Benchmark Recommended Settings

<div style={{ overflowX: 'auto' }}>
  <table style={{ minWidth: '900px' }}>
    <thead>
      <tr>
        <th style={{ whiteSpace: 'nowrap' }}>Benchmark Category</th>
        <th style={{ whiteSpace: 'nowrap' }}>Benchmark</th>
        <th style={{ whiteSpace: 'nowrap' }}>Temperature</th>
        <th style={{ whiteSpace: 'nowrap' }}>Recommended max tokens</th>
        <th style={{ whiteSpace: 'nowrap' }}>Recommended runs</th>
        <th style={{ whiteSpace: 'nowrap' }}>Top... (Continúa en el archivo fuente)

## 🤖 Capacidades Agenticas (Análisis KIE)
- Detección automática de herramientas: Sí
- Soporte de Agentes: Sí

---
[[KIMI_INDEX|🏠 Volver al Índice]] | [[CHANGELOG|📜 Historial de Cambios]]
