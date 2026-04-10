import React from 'react';
import { interpolate, useCurrentFrame } from 'remotion';
import { BRAND } from '../brand';

// SubtitlesV2 — generado automáticamente por gen_subs_v2.py
// Voice: en-US-AndrewNeural  Rate: -10%
// 81 sentences · 9397 frames total @ 30fps
// MÉTRICAS CORRECTAS: 4,308 tests · 8 chains · 147 proofs · V2 0x8B6B...

interface Sub { start: number; end: number; text: string; }

export const SUBS_V2: Sub[] = [
  { start:     1, end:    53, text: "Two trillion dollars." },
  { start:    50, end:    90, text: "Zero proof." },
  { start:    87, end:   318, text: "AI agents are executing transactions, managing DAO treasuries, making financial decisions — right now." },
  { start:   315, end:   443, text: "And there is no mathematical proof any of them behaved correctly." },
  { start:   440, end:   555, text: "You would not trust a bridge that was probably structurally sound." },
  { start:   552, end:   652, text: "But every autonomous agent fleet runs on probably." },
  { start:   649, end:   780, text: "Rules encoded as prompts can be overridden at any moment." },
  { start:   777, end:   843, text: "Language models hallucinate." },
  { start:   840, end:   928, text: "A validator that lies cannot validate." },
  { start:   925, end:  1012, text: "Audit logs can be altered after the fact." },
  { start:  1009, end:  1185, text: "The entire AI agent stack is built on trust — and trust is not a proof." },
  { start:  1182, end:  1244, text: "DOF-MESH changes this." },
  { start:  1241, end:  1444, text: "We are the first framework that mathematically proves an AI agent behaved correctly — before it acts." },
  { start:  1441, end:  1531, text: "Three independent deterministic layers." },
  { start:  1528, end:  1620, text: "Layer one: Constitution enforcement." },
  { start:  1617, end:  1673, text: "Deterministic rules." },
  { start:  1670, end:  1762, text: "Zero language models in the decision path." },
  { start:  1759, end:  1897, text: "Layer two: Z3 SMT formal verification." },
  { start:  1894, end:  2072, text: "Four theorems proven for all possible inputs — by Microsoft Research's solver." },
  { start:  2069, end:  2145, text: "Layer three: TRACER score." },
  { start:  2142, end:  2231, text: "Five-dimensional behavioral quality scoring." },
  { start:  2228, end:  2480, text: "The result: a keccak256 proof hash, registered permanently on Conflux — tamper-proof forever." },
  { start:  2477, end:  2508, text: "Why now?" },
  { start:  2505, end:  2671, text: "Three hundred twenty-seven million AI agents will be deployed by 2027." },
  { start:  2668, end:  2830, text: "The AI governance market reaches forty-seven billion dollars by 2030." },
  { start:  2827, end:  2966, text: "And today — zero frameworks offer formal mathematical proof." },
  { start:  2963, end:  3038, text: "The infrastructure gap is open." },
  { start:  3035, end:  3084, text: "We built the solution." },
  { start:  3081, end:  3122, text: "Watch this live." },
  { start:  3119, end:  3302, text: "Agent 1687 requests a DeFi transaction on Conflux eSpace." },
  { start:  3299, end:  3401, text: "DOF-MESH intercepts it before execution." },
  { start:  3398, end:  3473, text: "Constitution check: passed." },
  { start:  3470, end:  3540, text: "Zero language models involved." },
  { start:  3537, end:  3733, text: "Z3 formal verification: four of four theorems proven in seven milliseconds." },
  { start:  3730, end:  3912, text: "TRACER behavioral score: zero point seven one two — well above threshold." },
  { start:  3909, end:  3964, text: "The agent qualifies." },
  { start:  3961, end:  4010, text: "Now it goes on-chain." },
  { start:  4007, end:  4050, text: "Here is the proof." },
  { start:  4047, end:  4078, text: "Permanent." },
  { start:  4075, end:  4248, text: "One hundred forty-five confirmed transactions on DOFProofRegistryV1." },
  { start:  4245, end:  4368, text: "And our latest innovation: V2 Proof-to-Gasless." },
  { start:  4365, end:  4746, text: "When an agent proves mathematical compliance — TRACER above zero point four, Constitution above ninety percent — it is automatically added to Conflux's SponsorWhitelistControl." },
  { start:  4743, end:  4842, text: "Its next transactions cost zero gas." },
  { start:  4839, end:  4917, text: "Math earns economic privilege." },
  { start:  4914, end:  4948, text: "That is new." },
  { start:  4945, end:  4989, text: "Why Conflux?" },
  { start:  4986, end:  5151, text: "Because Gas Sponsorship is architecturally necessary for agent infrastructure." },
  { start:  5148, end:  5243, text: "Agents should not hold gas — they should act." },
  { start:  5240, end:  5475, text: "Conflux's native SponsorWhitelistControl makes zero-friction compliance registration possible at any scale." },
  { start:  5472, end:  5568, text: "On Ethereum, every agent needs gas." },
  { start:  5565, end:  5653, text: "On Conflux, math replaces money." },
  { start:  5650, end:  5745, text: "No other EVM chain has this natively." },
  { start:  5742, end:  5797, text: "Three revenue streams." },
  { start:  5794, end:  5882, text: "First: the open-source SDK." },
  { start:  5879, end:  6069, text: "Developers run pip install dof-sdk — Conflux integration ships included." },
  { start:  6066, end:  6249, text: "Second: the compliance API at ninety-nine to nine hundred ninety-nine dollars per month." },
  { start:  6246, end:  6282, text: "Finance." },
  { start:  6279, end:  6311, text: "Healthcare." },
  { start:  6308, end:  6336, text: "Legal." },
  { start:  6333, end:  6434, text: "Any team that cannot afford an agent that lies." },
  { start:  6431, end:  6530, text: "Third: enterprise white-label licensing." },
  { start:  6527, end:  6638, text: "Fifty thousand to five hundred thousand dollars per year." },
  { start:  6635, end:  6770, text: "DAO treasuries, DeFi protocols, full agent fleets." },
  { start:  6767, end:  6956, text: "The total addressable market for AI governance reaches eighteen billion by 2028." },
  { start:  6953, end:  7140, text: "Our serviceable market — blockchain AI agent compliance — is three point two billion." },
  { start:  7137, end:  7409, text: "Our realistic capture in year three: one hundred sixty million, starting with DeFi protocols needing provably-correct agents." },
  { start:  7406, end:  7458, text: "This is not a prototype." },
  { start:  7455, end:  7590, text: "One hundred forty-seven on-chain attestations on Conflux alone." },
  { start:  7587, end:  7637, text: "Eight active chains." },
  { start:  7634, end:  7720, text: "Four thousand three hundred eight tests passing." },
  { start:  7717, end:  7833, text: "Two hundred thirty-eight autonomous agent cycles completed." },
  { start:  7830, end:  8058, text: "Six MCP tools fully operational — the first Model Context Protocol server for Conflux Network." },
  { start:  8055, end:  8308, text: "ERC-8004, the Autonomous Agent Identity Standard, submitted to Ethereum Magicians." },
  { start:  8305, end:  8459, text: "I am Juan Carlos Quiceno — solo builder from Medellín, Colombia." },
  { start:  8456, end:  8679, text: "I built every line of this: the framework, the contracts, the MCP server, the SDK." },
  { start:  8676, end:  9051, text: "My ask is simple: help us deploy to Conflux mainnet, connect us with regulated-industry partners, and recognize this as the missing infrastructure layer for AI on blockchain." },
  { start:  9048, end:  9100, text: "The math is proven." },
  { start:  9097, end:  9140, text: "The chain is ready." },
  { start:  9137, end:  9185, text: "The agents are waiting." },
  { start:  9186, end:  9261, text: "Most frameworks verify what happened." },
  { start:  9258, end:  9340, text: "DOF verifies what is about to happen." },
];

export const SubtitlesV2: React.FC = () => {
  const frame = useCurrentFrame();
  const active = SUBS_V2.find(s => frame >= s.start && frame <= s.end);
  if (!active) return null;

  const opacity = interpolate(
    frame,
    [active.start, active.start + 5, active.end - 5, active.end],
    [0, 1, 1, 0],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
  );

  return (
    <div style={{
      position:   'absolute',
      bottom:     56,
      left:       '50%',
      transform:  'translateX(-50%)',
      opacity,
      maxWidth:   '80%',
      textAlign:  'center',
    }}>
      {/* Dark pill — legible sobre cualquier fondo */}
      <div style={{
        display:        'inline-block',
        background:     'rgba(0,0,0,0.82)',
        backdropFilter: 'blur(8px)',
        border:         '1px solid rgba(255,255,255,0.12)',
        borderRadius:   4,
        padding:        '12px 32px',
      }}>
        <div style={{
          fontFamily:    "'IBM Plex Mono', monospace",
          fontWeight:    600,
          fontSize:      26,
          color:         '#FFFFFF',   // blanco puro — nunca gris
          letterSpacing: '0.01em',
          lineHeight:    1.3,
          whiteSpace:    'nowrap',
        }}>
          {active.text}
        </div>
      </div>
    </div>
  );
};
