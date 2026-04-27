# Multi-modal Model Kimi K2.6 Pricing
> [!NOTE]
> **URL Original:** [https://platform.kimi.ai/docs/chat-k26](https://platform.kimi.ai/docs/chat-k26)
> **Tópico:** #Pricing
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

# Multi-modal Model Kimi K2.6 Pricing

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

## Product Pricing

**Explanation: Prices exclude applicable taxes. Specific tax obligations are subject to local tax regulations and will be calculated at checkout based on your jurisdiction.**

<DocTable
  columns={[
{ title: "Model", width: "24%" },
{ title: "Unit", width: "12%" },
{ title: "Input Price (Cache Hit)", width: "16%" },
{ title: "Input Price (Cache Miss)", width: "16%" },
{ title: "Output Price", width: "14%" },
{ title: "Context Window", width: "18%" },
]}
  rows={[
["kimi-k2.6", "1M tokens", <>{"$"}0.16</>, <>{"$"}0.95</>, <>{"$"}4.00</>, "262,144 t... (Continúa en el archivo fuente)

## 🤖 Capacidades Agenticas (Análisis KIE)
- Detección automática de herramientas: Sí
- Soporte de Agentes: Sí

---
[[KIMI_INDEX|🏠 Volver al Índice]] | [[CHANGELOG|📜 Historial de Cambios]]
