import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { BRAND } from '../brand';

// Scene 8 — BUSINESS MODEL + MARKET (35s = 1050 frames)
// Psychology: Specificity ($99 not "subscription"), Rule of 3, TAM/SAM/SOM anchoring

const REVENUE = [
  {
    num: '01',
    title: 'Open-Source SDK',
    cmd: 'pip install dof-sdk',
    desc: 'Developer adoption → Conflux integration included',
    tag: 'PyPI · 6,000+ downloads',
    delay: 60,
  },
  {
    num: '02',
    title: 'Compliance API (SaaS)',
    cmd: '$99–$999 / month per team',
    desc: 'Finance · Healthcare · Legal · DAO operators',
    tag: 'Regulated industries',
    delay: 240,
  },
  {
    num: '03',
    title: 'Enterprise White-Label',
    cmd: '$50K–$500K / year',
    desc: 'Full governance stack · DeFi protocols · Agent fleets',
    tag: 'Custom deployment',
    delay: 420,
  },
];

const MARKET = [
  { ring: 'TAM', value: '$18B', label: 'AI Governance & Compliance (2028)', color: 'rgba(255,255,255,0.18)', delay: 630 },
  { ring: 'SAM', value: '$3.2B', label: 'Blockchain AI Agent Compliance', color: 'rgba(59,130,246,0.35)', delay: 720 },
  { ring: 'SOM', value: '$160M', label: 'DeFi & DAO Governance Tooling — Year 3', color: `${BRAND.green}55`, delay: 810 },
];

export const SceneBusinessV2: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={{ background: BRAND.black, padding: '60px 100px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>

      {/* Business Model section */}
      {frame < 570 && (
        <>
          <div style={{
            fontFamily: "'IBM Plex Mono', monospace",
            fontSize: 13,
            color: BRAND.green,
            letterSpacing: '0.20em',
            marginBottom: 52,
            opacity: interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' }),
          }}>
            BUSINESS MODEL
          </div>

          <div style={{ display: 'flex', gap: 28 }}>
            {REVENUE.map(({ num, title, cmd, desc, tag, delay }) => {
              const opacity = interpolate(frame, [delay, delay + 45], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
              const y = interpolate(frame, [delay, delay + 45], [24, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

              return (
                <div key={num} style={{
                  opacity, transform: `translateY(${y}px)`, flex: 1,
                  background: 'rgba(255,255,255,0.04)',
                  border: '1px solid rgba(255,255,255,0.10)',
                  borderRadius: 4, padding: '36px 28px',
                }}>
                  <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 13, color: BRAND.green, letterSpacing: '0.18em', marginBottom: 14 }}>{num}</div>
                  <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontWeight: 700, fontSize: 26, color: BRAND.white, marginBottom: 12 }}>{title}</div>
                  <div style={{
                    fontFamily: "'IBM Plex Mono', monospace", fontSize: 18, color: BRAND.green,
                    background: 'rgba(0,204,85,0.08)', border: `1px solid ${BRAND.green}33`,
                    padding: '8px 14px', borderRadius: 2, marginBottom: 16,
                  }}>{cmd}</div>
                  <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 17, color: 'rgba(255,255,255,0.60)', marginBottom: 20, lineHeight: 1.4 }}>{desc}</div>
                  <div style={{
                    fontFamily: "'IBM Plex Mono', monospace", fontSize: 12, color: 'rgba(255,255,255,0.40)',
                    border: '1px solid rgba(255,255,255,0.12)', padding: '4px 10px', borderRadius: 2, display: 'inline-block',
                  }}>{tag}</div>
                </div>
              );
            })}
          </div>
        </>
      )}

      {/* Market Size section — TAM/SAM/SOM */}
      {frame >= 590 && (
        <>
          <div style={{
            fontFamily: "'IBM Plex Mono', monospace",
            fontSize: 13,
            color: BRAND.green,
            letterSpacing: '0.20em',
            marginBottom: 52,
            opacity: interpolate(frame, [600, 640], [0, 1], { extrapolateRight: 'clamp' }),
          }}>
            MARKET SIZE
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 36 }}>
            {MARKET.map(({ ring, value, label, color, delay }) => {
              const opacity = interpolate(frame, [delay, delay + 45], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
              const x = interpolate(frame, [delay, delay + 45], [-40, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

              return (
                <div key={ring} style={{ opacity, transform: `translateX(${x}px)`, display: 'flex', alignItems: 'center', gap: 40 }}>
                  {/* Ring label */}
                  <div style={{
                    fontFamily: "'IBM Plex Mono', monospace", fontWeight: 700, fontSize: 20,
                    color: BRAND.white, minWidth: 60,
                    background: color, border: '1px solid rgba(255,255,255,0.15)',
                    padding: '10px 18px', borderRadius: 2, textAlign: 'center',
                  }}>{ring}</div>
                  {/* Value */}
                  <div style={{
                    fontFamily: "'IBM Plex Mono', monospace", fontWeight: 700, fontSize: 72,
                    color: BRAND.white, lineHeight: 1, minWidth: 220,
                  }}>{value}</div>
                  {/* Label */}
                  <div style={{
                    fontFamily: "'IBM Plex Mono', monospace", fontSize: 26,
                    color: 'rgba(255,255,255,0.65)', lineHeight: 1.3,
                  }}>{label}</div>
                </div>
              );
            })}
          </div>
        </>
      )}
    </AbsoluteFill>
  );
};
