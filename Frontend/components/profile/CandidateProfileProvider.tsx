"use client";

import {
  createContext,
  useContext,
  useState,
  type ReactNode,
} from "react";
import {
  sampleMetrics,
  sampleProvenance,
  sampleReadinessCategories,
  sampleRoadmapCompletions,
  sampleRoadmapRecommendations,
  sampleSkills,
} from "@/app/data/sample-data";
import {
  completeRoadmapItem as completeRoadmapProfileItem,
  createInitialCandidateProfile,
  resetResumeMetadata as resetProfileResumeMetadata,
  updateResumeMetadata as updateProfileResumeMetadata,
  type CandidateProfile,
  type SelectedResumeMetadata,
} from "./candidate-profile-state";
import { useAuth } from "@/components/auth/AuthProvider";

export type {
  CandidateProfile,
  CandidateAnalysis,
  CandidateRoadmap,
  CandidateResumeMetadata,
  CandidateResumeStatus,
  DataProvenance,
} from "./candidate-profile-state";

type CandidateProfileContextValue = {
  profile: CandidateProfile;
  setResumeMetadata: (metadata: SelectedResumeMetadata) => void;
  resetResumeMetadata: () => void;
  completeRoadmapItem: (title: string) => void;
};

const CandidateProfileContext = createContext<CandidateProfileContextValue | null>(null);

function createInitialProfile() {
  return createInitialCandidateProfile({
    targetRole: "Frontend Developer",
    targetRoleProvenance: sampleProvenance,
    skills: sampleSkills,
    readiness: {
      overall: sampleMetrics.careerReadiness,
      interview: sampleMetrics.interviewReadiness,
      status: "sample",
      provenance: sampleProvenance,
      categories: sampleReadinessCategories,
    },
    roadmap: {
      recommendations: sampleRoadmapRecommendations,
      completions: sampleRoadmapCompletions,
      status: "sample",
      sourceFingerprint: null,
      provenance: sampleProvenance,
    },
    analysis: {
      status: "sample",
      sourceFingerprint: null,
      version: 1,
      provenance: sampleProvenance,
    },
  });
}

export function CandidateProfileProvider({ children }: { children: ReactNode }) {
  const { session } = useAuth();
  return <CandidateProfileStateProvider key={session?.profile.id ?? "signed-out"}>{children}</CandidateProfileStateProvider>;
}

function CandidateProfileStateProvider({ children }: { children: ReactNode }) {
  const [profile, setProfile] = useState(createInitialProfile);

  function setResumeMetadata(metadata: SelectedResumeMetadata) {
    setProfile((current) => updateProfileResumeMetadata(current, metadata));
  }

  function resetResumeMetadata() {
    setProfile(resetProfileResumeMetadata);
  }

  function completeRoadmapItem(title: string) {
    setProfile((current) => completeRoadmapProfileItem(current, title));
  }

  return (
    <CandidateProfileContext.Provider value={{ profile, setResumeMetadata, resetResumeMetadata, completeRoadmapItem }}>
      {children}
    </CandidateProfileContext.Provider>
  );
}

export function useCandidateProfile() {
  const context = useContext(CandidateProfileContext);
  if (!context) {
    throw new Error("useCandidateProfile must be used within CandidateProfileProvider");
  }
  return context;
}
