import json
import os

# Dispatcher
def dispatch_task(task):
    # Lee el archivo JSON y lo procesa
    with open(task, 'r') as f:
        data = json.load(f)
    # Llama al proveedor correspondiente
    if data['provider'] == 'Gemini':
        gemini_handler(data)
    # ...

# Handler de Gemini native
def gemini_handler(data):
    # Procesa la tarea con Gemini
    # ...
    # Escribe el resultado en un archivo JSON
    with open('resultado.json', 'w') as f:
        json.dump(resultado, f)