import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { BRAND } from '../brand';

// Scene 11 — TEAM + ASK + FINAL (15s = 450 frames)
// Psychology: Authority (solo founder credibility) + Contrast CTA + memorable final line
// The last thing judges see = what they remember

const ASK_ITEMS = [
  { arrow: '→', text: 'Recognize this as AI × Blockchain infrastructure', delay: 120 },
  { arrow: '→', text: 'Conflux mainnet deployment support', delay: 240 },
  { arrow: '→', text: 'Connect us with regulated-industry partners', delay: 330 },
];

export const SceneTeamCTAV2: React.FC = () => {
  const frame = useCurrentFrame();

  // Final quote appears at frame 300
  const quoteOpacity = interpolate(frame, [290, 360], [0, 1], { extrapolateRight: 'clamp' });
  // Card fades out
  const cardOpacity = interpolate(frame, [260, 310], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const showQuote = frame >= 280;

  return (
    <AbsoluteFill style={{ background: BRAND.black, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '0 100px' }}>

      {/* MAIN CONTENT — team + ask */}
      {!showQuote && (
        <div style={{ opacity: cardOpacity, display: 'flex', gap: 80, width: '100%' }}>

          {/* LEFT — team card */}
          <div style={{
            opacity: interpolate(frame, [0, 45], [0, 1], { extrapolateRight: 'clamp' }),
            flex: '0 0 380px',
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.10)',
            borderRadius: 4,
            padding: '48px 40px',
          }}>
            <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 13, color: BRAND.green, letterSpacing: '0.18em', marginBottom: 24 }}>TEAM</div>
            <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontWeight: 700, fontSize: 32, color: BRAND.white, marginBottom: 10 }}>Juan Carlos Quiceno</div>
            <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 18, color: BRAND.green, marginBottom: 24 }}>@Cyber_paisa</div>
            <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 17, color: 'rgba(255,255,255,0.55)', lineHeight: 1.6, marginBottom: 28 }}>
              Solo founder<br />
              Medellín, Colombia<br />
              Smart Contracts · Full-Stack · AI
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {['dofmesh.com', 'github.com/Cyberpaisa', 'ERC-8004 · Ethereum Magicians'].map(link => (
                <div key={link} style={{
                  fontFamily: "'IBM Plex Mono', monospace", fontSize: 14, color: 'rgba(255,255,255,0.45)',
                  borderLeft: `2px solid ${BRAND.green}55`, paddingLeft: 12,
                }}>
                  {link}
                </div>
              ))}
            </div>
          </div>

          {/* RIGHT — ask */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
            <div style={{
              fontFamily: "'IBM Plex Mono', monospace", fontSize: 13, color: BRAND.green,
              letterSpacing: '0.20em', marginBottom: 52,
              opacity: interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' }),
            }}>
              THE ASK
            </div>

            {ASK_ITEMS.map(({ arrow, text, delay }) => {
              const opacity = interpolate(frame, [delay, delay + 45], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
              const x = interpolate(frame, [delay, delay + 45], [-30, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

              return (
                <div key={text} style={{
                  opacity, transform: `translateX(${x}px)`,
                  display: 'flex', alignItems: 'flex-start', gap: 28, marginBottom: 40,
                }}>
                  <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 36, color: BRAND.green, lineHeight: 1.2, flexShrink: 0 }}>{arrow}</div>
                  <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontWeight: 600, fontSize: 28, color: BRAND.white, lineHeight: 1.3 }}>{text}</div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* FINAL SCREEN — punch line + CTA */}
      {showQuote && (
        <div style={{ opacity: quoteOpacity, textAlign: 'center', width: '100%', padding: '0 80px' }}>

          {/* Canonical contrast quote */}
          <div style={{
            fontFamily: "'IBM Plex Mono', monospace",
            fontWeight: 700,
            fontSize: 52,
            color: 'rgba(255,255,255,0.38)',
            lineHeight: 1.25,
            marginBottom: 8,
            letterSpacing: '-0.01em',
          }}>
            Most frameworks verify what happened.
          </div>
          <div style={{
            fontFamily: "'IBM Plex Mono', monospace",
            fontWeight: 700,
            fontSize: 64,
            color: BRAND.white,
            lineHeight: 1.2,
            marginBottom: 56,
            letterSpacing: '-0.02em',
          }}>
            DOF verifies what is{' '}
            <span style={{ color: BRAND.green }}>about to happen.</span>
          </div>

          {/* Divider */}
          <div style={{
            width: 80, height: 2,
            background: BRAND.green,
            margin: '0 auto 40px',
            borderRadius: 1,
          }} />

          {/* Builder credit — punch line */}
          <div style={{
            fontFamily: "'IBM Plex Mono', monospace",
            fontWeight: 600,
            fontSize: 28,
            color: BRAND.white,
            marginBottom: 8,
            letterSpacing: '0.02em',
          }}>
            Built by{' '}
            <span style={{ color: BRAND.green }}>@Cyber_paisa</span>
            {' '}· Blockchain builder · Medellín, Colombia
          </div>

          {/* URL — large, impossible to miss */}
          <div style={{
            fontFamily: "'IBM Plex Mono', monospace",
            fontWeight: 700,
            fontSize: 44,
            color: BRAND.white,
            letterSpacing: '0.04em',
            marginBottom: 48,
          }}>
            <span style={{ color: 'rgba(255,255,255,0.40)' }}>→ </span>
            dofmesh.com
          </div>

          {/* Tags row */}
          <div style={{ display: 'flex', justifyContent: 'center', gap: 20, flexWrap: 'wrap' }}>
            {[
              'pip install dof-sdk',
              'github.com/Cyberpaisa/DOF-MESH',
              'Conflux Global Hackfest 2026',
            ].map(tag => (
              <div key={tag} style={{
                fontFamily: "'IBM Plex Mono', monospace",
                fontSize: 15,
                color: BRAND.green,
                border: `1px solid ${BRAND.green}44`,
                background: `${BRAND.green}0A`,
                padding: '8px 22px',
                borderRadius: 2,
                letterSpacing: '0.06em',
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
