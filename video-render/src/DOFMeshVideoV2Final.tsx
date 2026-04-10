import React from 'react';
import { AbsoluteFill, Audio, staticFile, Video } from 'remotion';
import { TransitionSeries, springTiming } from '@remotion/transitions';
import { fade } from '@remotion/transitions/fade';

import { SubtitlesV2 }        from './components/SubtitlesV2';
import { SceneHookV2 }        from './scenes/SceneHookV2';
import { SceneProblemV2 }     from './scenes/SceneProblemV2';
import { SceneSolutionV2 }    from './scenes/SceneSolutionV2';
import { SceneWhyNowV2 }      from './scenes/SceneWhyNowV2';
import { Scene4Demo }         from './scenes/Scene4Demo';      // terminal demo existente
import { SceneConfluxProofV2 } from './scenes/SceneConfluxProofV2';
import { Scene5bGasless }     from './scenes/Scene5bGasless';  // Conflux advantage
import { SceneBusinessV2 }    from './scenes/SceneBusinessV2'; // BizModel + Market
import { SceneTractionV2 }    from './scenes/SceneTractionV2';
import { SceneTeamCTAV2 }     from './scenes/SceneTeamCTAV2';

// ─── TIMING (30 fps) — ajustado al audio 311s / 9339f ────────────────────────
// S1  Hook           24s =  720f
// S2  Problem        40s = 1200f
// S3  Solution       35s = 1050f
// S4  Why Now        22s =  660f
// S5  Demo           50s = 1500f  (terminal mp4)
// S6  Conflux Proof  33s =  990f
// S7  Conflux Adv    22s =  660f
// S8  Business+Mkt   46s = 1380f
// S9  Traction       24s =  720f
// S10 Team + CTA     20s =  600f
// ─────────────────────────────────────────────────────────────────────────────
// Subtotal scenes:          9480f
// 9 transitions × 15f:     -135f
// TOTAL:                    9345f ≈ 311.5s ≈ 5:11 (matches audio)

const TR = () => (
  <TransitionSeries.Transition
    presentation={fade()}
    timing={springTiming({ durationInFrames: 15 })}
  />
);

export const DOFMeshVideoV2Final: React.FC = () => (
  <AbsoluteFill style={{ background: '#000' }}>

    {/* Voiceover — genera con generate_voice_v2_hackathon.py */}
    {/* Fallback a voiceover.mp3 si v2 no existe aún */}
    <Audio
      src={staticFile('voiceover_v2.mp3')}
      volume={1}
      startFrom={0}
    />

    <TransitionSeries>

      {/* S1: HOOK — 24s */}
      <TransitionSeries.Sequence durationInFrames={720}>
        <SceneHookV2 />
      </TransitionSeries.Sequence>
      <TR />

      {/* S2: PROBLEM — 40s */}
      <TransitionSeries.Sequence durationInFrames={1200}>
        <SceneProblemV2 />
      </TransitionSeries.Sequence>
      <TR />

      {/* S3: SOLUTION — 35s */}
      <TransitionSeries.Sequence durationInFrames={1050}>
        <SceneSolutionV2 />
      </TransitionSeries.Sequence>
      <TR />

      {/* S4: WHY NOW — 22s */}
      <TransitionSeries.Sequence durationInFrames={660}>
        <SceneWhyNowV2 />
      </TransitionSeries.Sequence>
      <TR />

      {/* S5: LIVE DEMO — 50s (terminal recording) */}
      <TransitionSeries.Sequence durationInFrames={1500}>
        <Scene4Demo />
      </TransitionSeries.Sequence>
      <TR />

      {/* S6: CONFLUX PROOF ON-CHAIN — 33s */}
      <TransitionSeries.Sequence durationInFrames={990}>
        <SceneConfluxProofV2 />
      </TransitionSeries.Sequence>
      <TR />

      {/* S7: CONFLUX ADVANTAGE — 22s */}
      <TransitionSeries.Sequence durationInFrames={660}>
        <Scene5bGasless />
      </TransitionSeries.Sequence>
      <TR />

      {/* S8: BUSINESS MODEL + MARKET SIZE — 46s */}
      <TransitionSeries.Sequence durationInFrames={1380}>
        <SceneBusinessV2 />
      </TransitionSeries.Sequence>
      <TR />

      {/* S9: TRACTION — 24s */}
      <TransitionSeries.Sequence durationInFrames={720}>
        <SceneTractionV2 />
      </TransitionSeries.Sequence>
      <TR />

      {/* S10: TEAM + CTA + PUNCH LINE — 20s */}
      <TransitionSeries.Sequence durationInFrames={600}>
        <SceneTeamCTAV2 />
      </TransitionSeries.Sequence>

    </TransitionSeries>

    {/* Subtitles — sincronizados con Andrew Neural */}
    <AbsoluteFill style={{ pointerEvents: 'none' }}>
      <SubtitlesV2 />
    </AbsoluteFill>

  </AbsoluteFill>
);
