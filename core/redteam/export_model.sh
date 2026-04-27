#!/bin/bash
# export_model.sh - Exportar modelo local de Mac host a formato portable
# Ejecutar en macOS (host), no en la VM

set -euo pipefail

MODEL_NAME="${1:-dof-coder}"
EXPORT_DIR="${HOME}/dof-mesh-export"
VM_IP="${2:-10.10.10.2}"

echo "=== Exportando modelo: $MODEL_NAME ==="

mkdir -p "$EXPORT_DIR"

if ! ollama list | grep -q "$MODEL_NAME"; then
    echo "ERROR: Modelo $MODEL_NAME no encontrado en Ollama local."
    exit 1
fi

echo ">>> Extrayendo manifesto..."
ollama show "$MODEL_NAME" --modelfile > "$EXPORT_DIR/Modelfile.vm"

# Localizar el blob GGUF principal (el archivo de mayor tamaño en el store)
echo ">>> Localizando blob GGUF..."
OLLAMA_BLOBS="$HOME/.ollama/models/blobs"
GGUF_BLOB=$(ls -S "$OLLAMA_BLOBS" | head -n 1)

if [[ -n "$GGUF_BLOB" ]]; then
    echo ">>> Copiando blob: $GGUF_BLOB (~$(du -sh "$OLLAMA_BLOBS/$GGUF_BLOB" | cut -f1))..."
    cp "$OLLAMA_BLOBS/$GGUF_BLOB" "$EXPORT_DIR/model.gguf"
    echo ">>> Blob copiado correctamente."
else
    echo "AVISO: No se encontró blob GGUF. Transfiere el .gguf original manualmente."
fi

echo "=== Exportación completada ==="
echo "Archivos en: $EXPORT_DIR"
echo ""
echo "Para transferir a la VM, usa UTM Shared Folder o:"
echo "  scp -r $EXPORT_DIR dofoperator@${VM_IP}:/opt/dof-mesh/models/"
echo ""
echo "En la VM, para importar el modelo:"
echo "  cp /opt/dof-mesh/models/model.gguf ~/.ollama/models/blobs/\$(sha256sum model.gguf | cut -d' ' -f1)"
echo "  ollama create dof-coder -f /opt/dof-mesh/models/Modelfile.vm"
