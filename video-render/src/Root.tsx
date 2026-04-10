import React from 'react';
import { Composition } from 'remotion';
import { DOFMeshVideoV8 } from './DOFMeshVideoV8';
import { DOFMeshVideoV2Final } from './DOFMeshVideoV2Final';
import { waitForFonts } from './fonts';

waitForFonts();

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/* V2 — Hackathon pitch completo (4 min, business model, market, traction) */}
      <Composition
        id="DOFMeshV2Final"
        component={DOFMeshVideoV2Final}
        durationInFrames={9345}
        fps={30}
        width={1920}
        height={1080}
      />
      {/* V8 — versión anterior (3 min, técnico) */}
      <Composition
        id="DOFMeshV8"
        component={DOFMeshVideoV8}
        durationInFrames={5460}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
