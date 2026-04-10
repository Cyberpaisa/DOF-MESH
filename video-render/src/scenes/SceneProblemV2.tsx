import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, spring } from 'remotion';
import { BRAND } from '../brand';

// Scene 2 — THE PROBLEM (30s = 900 frames)
// Psychology: Rule of 3 + YOU language + visceral pain points

const PROBLEMS = [
  { icon: '❌', text: '"Trust us" is not a security model.', delay: 30 },
  { icon: '❌', text: 'LLMs hallucinate. A validator that lies cannot validate.', delay: 240 },
  { icon: '❌', text: 'Audit logs can be altered. On-chain proofs cannot.', delay: 450 },
];

export const SceneProblemV2: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <AbsoluteFill style={{
      background: BRAND.black,
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      padding: '0 120px',
      gap: 0,
    }}>

      {/* Section label */}
      <div style={{
        fontFamily: "'IBM Plex Mono', monospace",
        fontSize: 13,
        color: BRAND.green,
        letterSpacing: '0.20em',
        marginBottom: 64,
        opacity: interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' }),
      }}>
        THE PROBLEM
      </div>

      {PROBLEMS.map(({ icon, text, delay }, i) => {
        const itemOpacity = interpolate(frame, [delay, delay + 45], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
        const itemX = interpolate(frame, [delay, delay + 45], [-40, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

        return (
          <div key={i} style={{
            opacity: itemOpacity,
            transform: `translateX(${itemX}px)`,
            display: 'flex',
            alignItems: 'flex-start',
            gap: 32,
            marginBottom: 56,
          }}>
            {/* Red X */}
            <div style={{
              fontFamily: "'IBM Plex Mono', monospace",
              fontSize: 40,
              lineHeight: 1,
              flexShrink: 0,
              marginTop: 4,
            }}>
              {icon}
            </div>
            {/* Problem text */}
            <div style={{
              fontFamily: "'IBM Plex Mono', monospace",
              fontWeight: 600,
              fontSize: 40,
              color: BRAND.white,
              lineHeight: 1.3,
            }}>
              {text}
            </div>
          </div>
        );
      })}

      {/* Bottom emphasis line */}
      {frame > 600 && (
        <div style={{
          opacity: interpolate(frame, [620, 680], [0, 1], { extrapolateRight: 'clamp' }),
          borderTop: `1px solid rgba(255,255,255,0.12)`,
          paddingTop: 32,
          fontFamily: "'IBM Plex Mono', monospace",
          fontSize: 28,
          color: 'rgba(255,255,255,0.55)',
          fontStyle: 'italic',
        }}>
          The entire AI agent stack is built on trust — and trust is not a proof.
        </div>
      )}
    </AbsoluteFill>
  );
};
