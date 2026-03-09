# Lessons Learned

## v0.2.7

- Lección: Los patrones de detección exacta son case-sensitive y literal — 'root access for this session' no matchea si el patrón dice otra cosa. Siempre verificar con el payload exacto del test antes de publicar en PyPI.

## v0.2.8

- Lección: Nunca subir a PyPI antes de correr el Colab de validación — el orden correcto es: fix → tests locales → PyPI → Colab → reporte.
