import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, Img, staticFile } from 'remotion';
import { BRAND } from '../brand';

// Scene 10 — TRACTION (18s = 540 frames)
// Psychology: Social proof + specificity (exact numbers) + on-chain = unfakeable
// Image fills left side, metrics panel on right

const METRICS = [
  { value: '147', label: 'on-chain proofs · Conflux', delay: 90 },
  { value: '8', label: 'active chains', delay: 180 },
  { value: '4,308', label: 'tests passing', delay: 270 },
  { value: '238+', label: 'autonomous agent cycles', delay: 360 },
  { value: '6/6', label: 'MCP tools operational', delay: 420 },
  { value: 'ERC-8004', label: 'submitted to Ethereum Magicians', delay: 480 },
];

export const SceneTractionV2: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={{ background: BRAND.black, display: 'flex' }}>

      {/* LEFT — screenshot fills half screen */}
      <div style={{ width: '52%', position: 'relative', overflow: 'hidden' }}>
        <Img
          src={staticFile('audit_v1_145proofs.png')}
          style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'top left' }}
        />
        {/* Gradient right edge to blend */}
        <div style={{
          position: 'absolute', top: 0, right: 0, bottom: 0, width: 120,
          background: 'linear-gradient(to right, transparent, #0d0d0d)',
        }} />
        {/* Bottom label strip */}
        <div style={{
          position: 'absolute', bottom: 0, left: 0, right: 0,
          background: 'rgba(0,0,0,0.80)',
          borderTop: `1px solid ${BRAND.green}55`,
          padding: '16px 28px',
        }}>
          <div style={{
            fontFamily: "'IBM Plex Mono', monospace", fontSize: 13,
            color: BRAND.green, letterSpacing: '0.14em',
          }}>
            DOFProofRegistryV1 · ConfluxScan · Live
          </div>
        </div>
      </div>

      {/* RIGHT — metrics panel */}
      <div style={{
        flex: 1,
        padding: '72px 64px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
      }}>
        <div style={{
          fontFamily: "'IBM Plex Mono', monospace",
          fontSize: 13,
          color: BRAND.green,
          letterSpacing: '0.20em',
          marginBottom: 48,
          opacity: interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' }),
        }}>
          TRACTION
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          {METRICS.map(({ value, label, delay }) => {
            const opacity = interpolate(frame, [delay, delay + 45], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
            const x = interpolate(frame, [delay, delay + 45], [20, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

            return (
              <div key={value} style={{ opacity, transform: `translateX(${x}px)`, display: 'flex', alignItems: 'baseline', gap: 20 }}>
                <div style={{
                  fontFamily: "'IBM Plex Mono', monospace",
                  fontWeight: 700,
                  fontSize: 44,
                  color: BRAND.white,
                  minWidth: 140,
                  lineHeight: 1,
                }}>
                  {value}
                </div>
                <div style={{
                  fontFamily: "'IBM Plex Mono', monospace",
                  fontSize: 18,
                  color: 'rgba(255,255,255,0.60)',
                }}>
                  {label}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};
