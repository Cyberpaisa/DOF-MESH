import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, spring, useVideoConfig, Img, staticFile } from 'remotion';

// ==============================================================================
// ENTERPRISE MASTER SCENE: "Governance-as-a-Service" (Conflux x DOF-MESH)
// Features: Z3 Integration, Second Brain RAG, Defi Bounds, and SponsorWhitelist
// ALL TEXT AND VARIABLES IN ENGLISH AS REQUESTED.
// ==============================================================================

const BRAND = {
  black: '#0A0A0A',
  green: '#00CC55',
  glass: 'rgba(255, 255, 255, 0.04)',
  border: 'rgba(255, 255, 255, 0.1)',
  sans: '"Inter", sans-serif',
  mono: '"IBM Plex Mono", monospace',
};

const ENTERPRISE_FEATURES = [
  { step: '01', title: 'RAG SECOND BRAIN', desc: 'Secure Local Folders (Raw/Wiki) powering AI Context' },
  { step: '02', title: 'Z3 FIREWALL', desc: 'Mathematical Theorem Prover ensuring 100% Determinism' },
  { step: '03', title: 'USDT0 COMPLIANCE', desc: 'DeFi Liquidity bounds strictly validated On-Chain' },
  { step: '04', title: 'SPONSOR WHITELIST', desc: 'Zero-Gas Execution powered exclusively by Conflux' },
];

export const SceneEnterpriseMaster: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Master fade-in interpolation
  const masterOpacity = interpolate(frame, [0, 20], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Spring animation for the central architecture box
  const boxScale = interpolate(
    spring({ frame: Math.max(0, frame - 30), fps, config: { damping: 200 } }),
    [0, 1], [0.95, 1]
  );

  return (
    <div style={{
      backgroundColor: BRAND.black,
      width: '100%', height: '100%',
      position: 'relative', overflow: 'hidden',
      opacity: masterOpacity,
      display: 'flex', flexDirection: 'column',
      justifyContent: 'center', alignItems: 'center'
    }}>
      
      {/* BACKGROUND GRAPHIC: Subtle math/grid pattern representing the RAG Brain */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
        backgroundImage: 'radial-gradient(circle at 50% 50%, rgba(0, 204, 85, 0.05) 0%, transparent 60%)',
        zIndex: 0
      }} />

      {/* HEADER SECTION: Emphasizing the SaaS Value Proposition */}
      <div style={{ zIndex: 10, textAlign: 'center', marginBottom: 60 }}>
        <h1 style={{ fontFamily: BRAND.sans, fontSize: 64, color: 'white', fontWeight: 600, margin: 0 }}>
          Governance-as-a-Service
        </h1>
        <p style={{ fontFamily: BRAND.mono, fontSize: 24, color: BRAND.green, margin: '16px 0 0 0', textTransform: 'uppercase' }}>
          Monetizing Mathematics. Fueling AI with Conflux.
        </p>
      </div>

      {/* CORE INFRASTRUCTURE MATRIX */}
      <div style={{
        zIndex: 10,
        display: 'flex',
        gap: 24,
        transform: `scale(${boxScale})`,
        width: '80%', flexWrap: 'nowrap'
      }}>
        {ENTERPRISE_FEATURES.map((feat, i) => {
          // Staggered entry for each feature card
          const childOp = interpolate(frame, [60 + i * 15, 80 + i * 15], [0, 1], { extrapolateRight: 'clamp' });
          const slideUp = interpolate(frame, [60 + i * 15, 80 + i * 15], [20, 0], { extrapolateRight: 'clamp' });

          return (
            <div key={i} style={{
              flex: 1,
              background: BRAND.glass,
              border: `1px solid ${BRAND.border}`,
              borderTop: `4px solid ${BRAND.green}`,
              borderRadius: 8,
              padding: 32,
              opacity: childOp,
              transform: `translateY(${slideUp}px)`,
              boxShadow: '0 20px 40px rgba(0,0,0,0.5)'
            }}>
              <span style={{ fontFamily: BRAND.mono, fontSize: 16, color: 'gray' }}>{feat.step}</span>
              <h2 style={{ fontFamily: BRAND.sans, fontSize: 28, color: 'white', margin: '12px 0' }}>{feat.title}</h2>
              <p style={{ fontFamily: BRAND.sans, fontSize: 18, color: 'rgba(255,255,255,0.7)', lineHeight: 1.5 }}>
                {feat.desc}
              </p>
            </div>
          );
        })}
      </div>

      {/* EVIDENCE OVERLAYS (The Proofs) */}
      <AbsoluteFill style={{ zIndex: 5, pointerEvents: 'none', justifyContent: 'flex-end', padding: 60 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', opacity: interpolate(frame, [150, 180], [0, 1]) }}>
           {/* Replace string with your loaded empirical shots. Ensure you copy the PNGs to Remotion's public folder */}
           <div style={{ background: 'black', padding: 10, border: `1px solid ${BRAND.border}` }}>
              <p style={{ fontFamily: BRAND.mono, color: 'white', fontSize: 14 }}>> 146_TXs_ConfluxScan_Verified</p>
           </div>
           <div style={{ background: 'black', padding: 10, border: `1px solid ${BRAND.green}` }}>
              <p style={{ fontFamily: BRAND.mono, color: BRAND.green, fontSize: 14 }}>> GAS SPONSORED: ZERO</p>
           </div>
        </div>
      </AbsoluteFill>

    </div>
  );
};
