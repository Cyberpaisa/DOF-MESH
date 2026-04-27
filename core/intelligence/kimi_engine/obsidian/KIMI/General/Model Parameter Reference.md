# Model Parameter Reference
> [!NOTE]
> **URL Original:** [https://platform.kimi.ai/docs/models-overview](https://platform.kimi.ai/docs/models-overview)
> **Tópico:** #General
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

# Model Parameter Reference

export const DocTable = ({columns = [], rows = []}) => {
  return <div className="doc-table-wrap">
      <table className="doc-table">
        {columns.length > 0 ? <colgroup>
            {columns.map((column, index) => <col key={index} style={column.width ? {
    width: column.width
  } : undefined} />)}
          </colgroup> : null}
        <thead>
          <tr>
            {columns.map((column, index) => <th key={index}>{column.title}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => <tr key={rowIndex}>
              {row.map((cell, cellIndex) => <td key={cellIndex}>{cell}</td>)}
            </tr>)}
        </tbody>
      </table>
    </div>;
};

Different model families have different defaults and constraints for Chat Completions API parameters. For the full model list, see the [Model List](/models).

## Parameter Comparison

<DocTable
  columns={[
{ title: "Parameter", width: "18%" },
{ title: "kimi-k2.6", width: "18%" },
{ title: "kimi-k2 series", width: "20%" },
{ title: "kimi-k2-thinking series", width: "24%" },
{ title: "moonshot-v1 series", width: "20%" },
]}
  rows={[
[<code>temperature</code>, <strong>Cannot be modified</strong>, "0.6", "1.0", "0.0"],
[<code>top_p</code>, <>0.95 <strong>Cannot be modified</str... (Continúa en el archivo fuente)

## 🤖 Capacidades Agenticas (Análisis KIE)
- Detección automática de herramientas: No
- Soporte de Agentes: No

---
[[KIMI_INDEX|🏠 Volver al Índice]] | [[CHANGELOG|📜 Historial de Cambios]]
