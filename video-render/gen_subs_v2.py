"""
Lee captions_v2.json (generado por generate_voice_v2_hackathon.py)
y produce src/components/SubtitlesV2.tsx con los captions sincronizados.

Uso:
  python gen_subs_v2.py
"""

import json
from pathlib import Path

BASE      = Path(__file__).parent
JSON_IN   = BASE / "public" / "captions_v2.json"
TSX_OUT   = BASE / "src" / "components" / "SubtitlesV2.tsx"

def ms2f(ms: float, fps: int = 30) -> int:
    return int(ms / 1000 * fps)

def main():
    if not JSON_IN.exists():
        print(f"ERROR: {JSON_IN} no existe. Corre generate_voice_v2_hackathon.py primero.")
        return

    data = json.loads(JSON_IN.read_text())
    sentences = data["sentences"]
    fps = data.get("fps", 30)

    # Generar líneas de SUBS array
    lines = []
    for s in sentences:
        sf = s.get("start_f", ms2f(s["start_ms"], fps))
        ef = s.get("end_f",   ms2f(s["end_ms"],   fps))
        # Ampliar ligeramente end para que no parpadee
        ef = ef + 3
        text = s["text"].replace('"', '\\"')
        lines.append(f'  {{ start: {sf:5d}, end: {ef:5d}, text: "{text}" }},')

    total_frames = max(s.get("end_f", ms2f(s["end_ms"], fps)) for s in sentences) + 60

    tsx = f'''\
import React from 'react';
import {{ interpolate, useCurrentFrame }} from 'remotion';
import {{ BRAND }} from '../brand';

// SubtitlesV2 — generado automáticamente por gen_subs_v2.py
// Voice: {data.get("voice","en-US-AndrewNeural")}  Rate: {data.get("rate","-10%")}
// {len(sentences)} sentences · {total_frames} frames total @ {fps}fps
// MÉTRICAS CORRECTAS: 4,308 tests · 8 chains · 147 proofs · V2 0x8B6B...

interface Sub {{ start: number; end: number; text: string; }}

export const SUBS_V2: Sub[] = [
{chr(10).join(lines)}
];

export const SubtitlesV2: React.FC = () => {{
  const frame = useCurrentFrame();
  const active = SUBS_V2.find(s => frame >= s.start && frame <= s.end);
  if (!active) return null;

  const opacity = interpolate(
    frame,
    [active.start, active.start + 5, active.end - 5, active.end],
    [0, 1, 1, 0],
    {{ extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }}
  );

  return (
    <div style={{{{
      position:   'absolute',
      bottom:     56,
      left:       '50%',
      transform:  'translateX(-50%)',
      opacity,
      maxWidth:   '80%',
      textAlign:  'center',
    }}}}>
      {{/* Dark pill — legible sobre cualquier fondo */}}
      <div style={{{{
        display:        'inline-block',
        background:     'rgba(0,0,0,0.82)',
        backdropFilter: 'blur(8px)',
        border:         '1px solid rgba(255,255,255,0.12)',
        borderRadius:   4,
        padding:        '12px 32px',
      }}}}>
        <div style={{{{
          fontFamily:    "'IBM Plex Mono', monospace",
          fontWeight:    600,
          fontSize:      26,
          color:         '#FFFFFF',   // blanco puro — nunca gris
          letterSpacing: '0.01em',
          lineHeight:    1.3,
          whiteSpace:    'nowrap',
        }}}}>
          {{active.text}}
        </div>
      </div>
    </div>
  );
}};
'''

    TSX_OUT.write_text(tsx)
    print(f"SubtitlesV2.tsx generado: {TSX_OUT}")
    print(f"  {len(sentences)} subtítulos · {total_frames} frames")
    print(f"  Duración: ~{total_frames/fps:.0f}s ({total_frames/fps/60:.1f} min)")

if __name__ == "__main__":
    main()
