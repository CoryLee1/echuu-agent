import { getToken } from "../hooks/useAuth";

const API_BASE = "http://localhost:8000";

const headers = () => ({
  "Content-Type": "application/json",
  Authorization: `Bearer ${getToken() ?? ""}`,
});

export type EvalFixture = {
  id: string;
  split: "train" | "dev" | "test" | "unspecified";
  topic: string;
  character_name: string;
  persona: string;
  tone_intent: string;
  depth_budget: string;
  entertainment_mechanism: string;
  transcript_chars: number;
};

export type EvalStatus = {
  fixtures: number;
  run_groups: number;
  pairs_total: number;
  pairs_judged: number;
  pairs_pending: number;
  generation: {
    running: boolean;
    completed: number;
    total: number;
    current: string;
    error: string | null;
  };
};

export type EvalVariant = {
  variant: "human" | "with_dossier" | "no_dossier";
  text: string;
  audio_url: string;
};

export type EvalPair =
  | { done: true }
  | { done: false; fixture_id: string; a: EvalVariant; b: EvalVariant };

export type EvalReportRow = {
  variant_a: string;
  variant_b: string;
  n: number;
  wins_a: number;
  ties: number;
  rate: number;
  low: number;
  high: number;
};

export type EvalRun = {
  run_id: string;
  variants: Array<{
    variant: "human" | "with_dossier" | "no_dossier";
    generated_at_utc: string | null;
    stage_count: number;
  }>;
};

export type PipelineStage = {
  id: string;
  label: string;
  status: "completed" | "skipped" | "degraded" | "failed";
  duration_ms: number;
  input?: unknown;
  output?: unknown;
  metrics?: Record<string, unknown>;
  ai?: {
    uses_ai: boolean;
    provider?: string;
    model?: string;
    call_count: number;
    duration_ms?: number;
    prompt_chars?: number;
    avg_prompt_chars?: number;
    max_prompt_chars?: number;
    response_chars?: number;
    failed_calls?: number;
    calls?: Array<Record<string, unknown>>;
  };
};

export type PipelineTrace = {
  version: number;
  pipeline: string;
  evaluation_context?: {
    source_fixture_id: string;
    split: string;
    retrieval_seed: number;
    retrieval_allowed_pool_size: number | null;
    retrieval_exclude_ids: string[];
    tuning_guidance_ids?: string[];
  };
  stages: PipelineStage[];
};

export type TuningNote = {
  id: string;
  created_at: string;
  author: string;
  run_id: string;
  variant: "human" | "with_dossier" | "no_dossier";
  stage_id: string;
  observation: string;
  target_excerpt?: string;
  positive_feedback?: string;
  issue_feedback?: string;
  adjustment: string;
  expected_effect: string;
  feedback_type?: "positive" | "issue" | "mixed";
  category?: "strength" | "world_knowledge" | "fabricated_detail" | "focus_drift" | "persona" | "logic" | "style" | "repetition" | "safety" | "other";
  severity?: "low" | "medium" | "high";
  status: "planned" | "applied" | "validated" | "reverted";
};

const request = async <T>(path: string, init?: RequestInit): Promise<T> => {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { ...headers(), ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || "评测请求失败");
  }
  return response.json();
};

export const fetchEvalFixtures = () =>
  request<EvalFixture[]>("/api/eval/fixtures");

export const fetchEvalStatus = () =>
  request<EvalStatus>("/api/eval/status");

export const fetchEvalNext = () =>
  request<EvalPair>("/api/eval/next");

export const fetchEvalReport = () =>
  request<EvalReportRow[]>("/api/eval/report");

export const fetchEvalRuns = () =>
  request<EvalRun[]>("/api/eval/runs");

export const fetchEvalTrace = (runId: string, variant: string) =>
  request<PipelineTrace>(
    `/api/eval/trace/${encodeURIComponent(runId)}/${encodeURIComponent(variant)}`,
  );

export const fetchTuningNotes = () =>
  request<TuningNote[]>("/api/eval/tuning-notes");

export const createTuningNote = (payload: {
  run_id: string;
  variant: string;
  stage_id: string;
  observation: string;
  target_excerpt?: string;
  positive_feedback?: string;
  issue_feedback?: string;
  adjustment: string;
  expected_effect: string;
  feedback_type?: TuningNote["feedback_type"];
  category?: TuningNote["category"];
  severity?: TuningNote["severity"];
  status: TuningNote["status"];
}) =>
  request<TuningNote>("/api/eval/tuning-notes", {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const startEvalGeneration = (fixtureIds: string[], repeats: number) =>
  request<{ ok: boolean; total: number }>("/api/eval/generate", {
    method: "POST",
    body: JSON.stringify({ fixture_ids: fixtureIds, repeats }),
  });

export const submitEvalJudgment = (
  pair: Extract<EvalPair, { done: false }>,
  winner: "a" | "b" | "tie",
) =>
  request<{ ok: boolean }>("/api/eval/judge", {
    method: "POST",
    body: JSON.stringify({
      fixture_id: pair.fixture_id,
      variant_a: pair.a.variant,
      variant_b: pair.b.variant,
      winner,
    }),
  });

export const evalAudioUrl = (path: string) => `${API_BASE}${path}`;
