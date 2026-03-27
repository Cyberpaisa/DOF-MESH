#!/bin/bash
# DOF Mesh Voice — Auto-start script
# Se agrega como Login Item en System Settings > General > Login Items

cd /Users/jquiceva/DOF-MESH

# Esperar a que Ollama esté listo
echo "Esperando Ollama..."
for i in {1..30}; do
    curl -s http://localhost:11434/api/tags > /dev/null 2>&1 && break
    sleep 2
done

echo "Iniciando DOF Mesh Voice Realtime..."
exec /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 \
    /Users/jquiceva/DOF-MESH/interfaces/voice_realtime.py \
    --provider ollama
