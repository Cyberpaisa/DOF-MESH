import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { BRAND } from '../brand';

// Scene 3 — THE SOLUTION (27s = 810 frames)
// Psychology: Contrast + Rule of 3 + specificity as credibility

const LAYERS = [
  {
    number: '01',
    name: 'CONSTITUTION',
    sub: 'Deterministic rules',
    badge: 'ZERO LLM',
    delay: 60,
  },
  {
    number: '02',
    name: 'Z3 SMT SOLVER',
    sub: '4/4 Theorems PROVEN',
    badge: 'Microsoft Research',
    delay: 240,
  },
  {
    number: '03',
    name: 'TRACER SCORE',
    sub: '5-dimensional behavioral quality',
    badge: 'threshold: 0.400',
    delay: 420,
  },
];

export const SceneSolutionV2: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={{ background: BRAND.black, padding: '0 100px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>

      {/* Label */}
      <div style={{
        fontFamily: "'IBM Plex Mono', monospace",
        fontSize: 13,
        color: BRAND.green,
        letterSpacing: '0.20em',
        marginBottom: 24,
        opacity: interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' }),
      }}>
        THE SOLUTION
      </div>

      {/* Headline */}
      <div style={{
        opacity: interpolate(frame, [0, 45], [0, 1], { extrapolateRight: 'clamp' }),
        fontFamily: "'IBM Plex Mono', monospace",
        fontWeight: 700,
        fontSize: 52,
        color: BRAND.white,
        marginBottom: 64,
        lineHeight: 1.2,
      }}>
        Math replaces trust.
      </div>

      {/* 3 layers */}
      <div style={{ display: 'flex', gap: 32 }}>
        {LAYERS.map(({ number, name, sub, badge, delay }) => {
          const opacity = interpolate(frame, [delay, delay + 45], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
          const y = interpolate(frame, [delay, delay + 45], [30, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

          return (
            <div key={number} style={{
              opacity,
              transform: `translateY(${y}px)`,
              flex: 1,
              background: 'rgba(255,255,255,0.04)',
              border: `1px solid rgba(255,255,255,0.10)`,
              borderRadius: 4,
              padding: '40px 32px',
            }}>
              <div style={{
                fontFamily: "'IBM Plex Mono', monospace",
                fontSize: 13,
                color: BRAND.green,
                letterSpacing: '0.20em',
                marginBottom: 16,
              }}>
                {number}
              </div>
              <div style={{
                fontFamily: "'IBM Plex Mono', monospace",
                fontWeight: 700,
                fontSize: 28,
                color: BRAND.white,
                marginBottom: 10,
                lineHeight: 1.2,
              }}>
                {name}
              </div>
              <div style={{
                fontFamily: "'IBM Plex Mono', monospace",
                fontSize: 18,
                color: 'rgba(255,255,255,0.60)',
                marginBottom: 24,
              }}>
                {sub}
              </div>
              <div style={{
                display: 'inline-block',
                fontFamily: "'IBM Plex Mono', monospace",
                fontSize: 13,
                color: BRAND.green,
                border: `1px solid ${BRAND.green}55`,
                padding: '5px 14px',
                borderRadius: 2,
                letterSpacing: '0.10em',
              }}>
                {badge}
              </div>
            </div>
          );
        })}
      </div>

      {/* Arrow chain at bottom */}
      {frame > 550 && (
        <div style={{
          opacity: interpolate(frame, [570, 630], [0, 1], { extrapolateRight: 'clamp' }),
          marginTop: 48,
          fontFamily: "'IBM Plex Mono', monospace",
          fontSize: 18,
          color: BRAND.green,
          display: 'flex',
          alignItems: 'center',
          gap: 20,
        }}>
          <span style={{ color: 'rgba(255,255,255,0.50)' }}>proof hash →</span>
          <span>keccak256</span>
          <span style={{ color: 'rgba(255,255,255,0.50)' }}>→ Conflux eSpace →</span>
          <span>tamper-proof forever</span>
          <span style={{ marginLeft: 8 }}>✅</span>
        </div>
      )}
    </AbsoluteFill>
  );
};
