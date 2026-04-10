import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, spring } from 'remotion';
import { BRAND } from '../brand';

// Scene 1 — THE HOOK (18s = 540 frames @ 30fps)
// Psychology: Loss aversion + visceral stat in 7s
// "$2 trillion. Zero proof." — anchoring then shock

export const SceneHookV2: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // "$2 trillion." appears at frame 15, holds until 120
  const trillionOpacity = interpolate(frame, [15, 45], [0, 1], { extrapolateRight: 'clamp' });
  const trillionScale = spring({ frame: frame - 15, fps, config: { damping: 18, stiffness: 80 } });

  // "$2 trillion." fades out at frame 120
  const trillionFadeOut = interpolate(frame, [120, 150], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const trillionFinal = frame < 120 ? trillionOpacity : trillionFadeOut;

  // "Zero proof." appears at frame 165, holds
  const zeroproofOpacity = interpolate(frame, [165, 210], [0, 1], { extrapolateRight: 'clamp' });
  const zeroproofScale = spring({ frame: frame - 165, fps, config: { damping: 18, stiffness: 80 } });

  // Logo + tagline at frame 300
  const logoOpacity = interpolate(frame, [300, 360], [0, 1], { extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ background: BRAND.black, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>

      {/* "$2 trillion." */}
      {frame < 165 && (
        <div style={{
          opacity: trillionFinal,
          transform: `scale(${Math.min(trillionScale, 1)})`,
          fontFamily: "'IBM Plex Mono', monospace",
          fontWeight: 700,
          fontSize: 96,
          color: BRAND.white,
          letterSpacing: '-0.02em',
          textAlign: 'center',
        }}>
          $2 trillion.
        </div>
      )}

      {/* "Zero proof." */}
      {frame >= 150 && (
        <div style={{
          opacity: zeroproofOpacity,
          transform: `scale(${Math.min(zeroproofScale, 1)})`,
          fontFamily: "'IBM Plex Mono', monospace",
          fontWeight: 700,
          fontSize: 96,
          color: BRAND.green,
          letterSpacing: '-0.02em',
          textAlign: 'center',
        }}>
          Zero proof.
        </div>
      )}

      {/* Logo + tagline */}
      {frame >= 290 && (
        <div style={{ opacity: logoOpacity, textAlign: 'center', marginTop: 80 }}>
          <div style={{
            fontFamily: "'IBM Plex Mono', monospace",
            fontWeight: 700,
            fontSize: 48,
            color: BRAND.white,
            letterSpacing: '0.08em',
          }}>
            DOF-MESH
          </div>
          <div style={{
            fontFamily: "'IBM Plex Mono', monospace",
            fontWeight: 400,
            fontSize: 22,
            color: 'rgba(255,255,255,0.65)',
            marginTop: 12,
            letterSpacing: '0.12em',
          }}>
            DETERMINISTIC GOVERNANCE FOR AUTONOMOUS AI AGENTS
          </div>
          <div style={{
            marginTop: 24,
            display: 'flex',
            gap: 32,
            justifyContent: 'center',
          }}>
            {['CONFLUX GLOBAL HACKFEST 2026', '@Cyber_paisa', 'dofmesh.com'].map((tag) => (
              <div key={tag} style={{
                fontFamily: "'IBM Plex Mono', monospace",
                fontSize: 13,
                color: BRAND.green,
                letterSpacing: '0.14em',
                padding: '4px 12px',
                border: `1px solid ${BRAND.green}44`,
                borderRadius: 2,
              }}>
                {tag}
              </div>
            ))}
          </div>
        </div>
      )}
    </AbsoluteFill>
  );
};
