import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { BRAND } from '../brand';

// Scene 4 — WHY NOW (17s = 510 frames)
// Psychology: FOMO + anchoring with big numbers + scarcity ("zero frameworks")

const STATS = [
  { number: '327M', label: 'AI agents deployed by 2027', delay: 60 },
  { number: '$47B', label: 'AI governance market by 2030', delay: 200 },
  { number: '0', label: 'frameworks with formal mathematical proof', delay: 340, highlight: true },
];

export const SceneWhyNowV2: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={{
      background: BRAND.black,
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      alignItems: 'center',
      padding: '0 100px',
    }}>

      {/* Label */}
      <div style={{
        fontFamily: "'IBM Plex Mono', monospace",
        fontSize: 13,
        color: BRAND.green,
        letterSpacing: '0.20em',
        marginBottom: 72,
        opacity: interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' }),
      }}>
        WHY NOW
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 52, width: '100%', maxWidth: 960 }}>
        {STATS.map(({ number, label, delay, highlight }) => {
          const opacity = interpolate(frame, [delay, delay + 45], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
          const x = interpolate(frame, [delay, delay + 45], [-60, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

          return (
            <div key={number} style={{
              opacity,
              transform: `translateX(${x}px)`,
              display: 'flex',
              alignItems: 'baseline',
              gap: 40,
            }}>
              <div style={{
                fontFamily: "'IBM Plex Mono', monospace",
                fontWeight: 700,
                fontSize: 96,
                lineHeight: 1,
                color: highlight ? '#EF4444' : BRAND.white,
                minWidth: 260,
                textAlign: 'right',
              }}>
                {number}
              </div>
              <div style={{
                fontFamily: "'IBM Plex Mono', monospace",
                fontSize: 32,
                color: highlight ? 'rgba(239,68,68,0.80)' : 'rgba(255,255,255,0.65)',
                lineHeight: 1.3,
              }}>
                {label}
              </div>
            </div>
          );
        })}
      </div>

      {/* CTA line */}
      {frame > 420 && (
        <div style={{
          opacity: interpolate(frame, [440, 490], [0, 1], { extrapolateRight: 'clamp' }),
          marginTop: 72,
          fontFamily: "'IBM Plex Mono', monospace",
          fontSize: 26,
          color: BRAND.green,
          textAlign: 'center',
          letterSpacing: '0.04em',
        }}>
          The infrastructure gap is open. We built the solution.
        </div>
      )}
    </AbsoluteFill>
  );
};
