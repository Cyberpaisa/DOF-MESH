import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, Img, staticFile } from 'remotion';
import { BRAND } from '../brand';

// Scene 6 — CONFLUX PROOF ON-CHAIN (25s = 750 frames)
// Psychology: Social proof + specificity = credibility
// Rule: image fills screen, text in bottom strip only (never over main content)

export const SceneConfluxProofV2: React.FC = () => {
  const frame = useCurrentFrame();

  // First image: V1 145 proofs (0-375)
  const img1Opacity = interpolate(frame, [0, 30, 330, 375], [0, 1, 1, 0], { extrapolateRight: 'clamp' });
  // Second image: V2 TX (375-750)
  const img2Opacity = interpolate(frame, [375, 420], [0, 1], { extrapolateRight: 'clamp' });

  // Bottom strip label for each image
  const strip1Opacity = interpolate(frame, [60, 105, 330, 375], [0, 1, 1, 0], { extrapolateRight: 'clamp' });
  const strip2Opacity = interpolate(frame, [435, 480], [0, 1], { extrapolateRight: 'clamp' });

  // "Math earns economic privilege" line
  const taglineOpacity = interpolate(frame, [570, 630], [0, 1], { extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ background: BRAND.black }}>

      {/* IMAGE 1: V1 — 145 proofs */}
      <AbsoluteFill style={{ opacity: img1Opacity }}>
        <Img
          src={staticFile('screenshot_confluxscan_146txs.png')}
          style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'top' }}
        />
        {/* Dark overlay to make image readable but visible */}
        <AbsoluteFill style={{ background: 'rgba(0,0,0,0.35)' }} />
      </AbsoluteFill>

      {/* IMAGE 2: V2 — gaslessGranted=true */}
      <AbsoluteFill style={{ opacity: img2Opacity }}>
        <Img
          src={staticFile('confluxscan_v2_proof_tx.png')}
          style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'top' }}
        />
        <AbsoluteFill style={{ background: 'rgba(0,0,0,0.35)' }} />
      </AbsoluteFill>

      {/* STRIP 1 — bottom, dark bar, white text */}
      <div style={{
        position: 'absolute',
        bottom: 0, left: 0, right: 0,
        background: 'rgba(0,0,0,0.82)',
        borderTop: `2px solid ${BRAND.green}`,
        padding: '28px 80px',
        opacity: strip1Opacity,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div>
          <div style={{
            fontFamily: "'IBM Plex Mono', monospace",
            fontSize: 13,
            color: BRAND.green,
            letterSpacing: '0.18em',
            marginBottom: 6,
          }}>
            DOFProofRegistryV1 · Conflux eSpace Testnet
          </div>
          <div style={{
            fontFamily: "'IBM Plex Mono', monospace",
            fontWeight: 700,
            fontSize: 40,
            color: BRAND.white,
          }}>
            145 confirmed on-chain proofs
          </div>
        </div>
        <div style={{
          fontFamily: "'IBM Plex Mono', monospace",
          fontSize: 16,
          color: 'rgba(255,255,255,0.55)',
          textAlign: 'right',
        }}>
          0x554cCa8...A9B83<br />
          chain 71 · eSpace Testnet
        </div>
      </div>

      {/* STRIP 2 — V2 Proof-to-Gasless */}
      <div style={{
        position: 'absolute',
        bottom: 0, left: 0, right: 0,
        background: 'rgba(0,0,0,0.82)',
        borderTop: `2px solid ${BRAND.green}`,
        padding: '28px 80px',
        opacity: strip2Opacity,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div>
          <div style={{
            fontFamily: "'IBM Plex Mono', monospace",
            fontSize: 13,
            color: BRAND.green,
            letterSpacing: '0.18em',
            marginBottom: 6,
          }}>
            DOFProofRegistryV2 · Proof-to-Gasless · TX Confirmed
          </div>
          <div style={{
            fontFamily: "'IBM Plex Mono', monospace",
            fontWeight: 700,
            fontSize: 36,
            color: BRAND.white,
          }}>
            gaslessGranted = <span style={{ color: BRAND.green }}>true</span>
          </div>
        </div>
        <div style={{
          fontFamily: "'IBM Plex Mono', monospace",
          fontSize: 15,
          color: 'rgba(255,255,255,0.55)',
          textAlign: 'right',
          lineHeight: 1.6,
        }}>
          0xd9cfdc...bfd2d<br />
          TRACER: 0.712 · Constitution: 0.95<br />
          Z3: 4/4 PROVEN
        </div>
      </div>

      {/* Tagline — center, appears after both images */}
      {frame > 560 && (
        <div style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          opacity: taglineOpacity,
          textAlign: 'center',
          background: 'rgba(0,0,0,0.88)',
          padding: '40px 80px',
          borderRadius: 4,
          border: `1px solid ${BRAND.green}44`,
        }}>
          <div style={{
            fontFamily: "'IBM Plex Mono', monospace",
            fontWeight: 700,
            fontSize: 42,
            color: BRAND.green,
          }}>
            Math earns economic privilege.
          </div>
          <div style={{
            fontFamily: "'IBM Plex Mono', monospace",
            fontSize: 22,
            color: 'rgba(255,255,255,0.60)',
            marginTop: 12,
          }}>
            That's new.
          </div>
        </div>
      )}
    </AbsoluteFill>
  );
};
