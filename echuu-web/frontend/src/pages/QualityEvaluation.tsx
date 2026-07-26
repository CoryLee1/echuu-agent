import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  BarChart3,
  Bot,
  BrainCircuit,
  CheckCircle2,
  ChevronRight,
  CircleDot,
  Clock3,
  FileInput,
  FlaskConical,
  Loader2,
  Mic2,
  Play,
  Quote,
  RefreshCw,
  Route,
  Save,
  ScrollText,
  Sparkles,
  ThumbsUp,
} from "lucide-react";
import {
  evalAudioUrl,
  createTuningNote,
  fetchEvalFixtures,
  fetchEvalNext,
  fetchEvalReport,
  fetchEvalRuns,
  fetchEvalStatus,
  fetchEvalTrace,
  fetchTuningNotes,
  startEvalGeneration,
  submitEvalJudgment,
  type EvalFixture,
  type EvalPair,
  type EvalReportRow,
  type EvalRun,
  type EvalStatus,
  type PipelineStage,
  type PipelineTrace,
  type TuningNote,
} from "../api/evaluationApi";
import { Button } from "../components/ui/button";
import { Card, CardContent } from "../components/ui/card";

const variantLabel: Record<string, string> = {
  human: "真人原稿",
  with_dossier: "Dossier 开启",
  no_dossier: "Dossier 关闭",
};

const tuningStatusLabel: Record<TuningNote["status"], string> = {
  planned: "计划中",
  applied: "已应用",
  validated: "已验证",
  reverted: "已回退",
};

const splitLabel: Record<EvalFixture["split"], string> = {
  train: "TRAIN · 调教",
  dev: "DEV · 验证",
  test: "TEST · 锁定测试",
  unspecified: "未分组",
};

const splitClass: Record<EvalFixture["split"], string> = {
  train: "bg-sky-50 text-sky-700",
  dev: "bg-amber-50 text-amber-700",
  test: "bg-rose-50 text-rose-700",
  unspecified: "bg-slate-100 text-slate-500",
};

const discourseModeLabel: Record<string, string> = {
  narrative: "故事叙述",
  commentary: "观点评论",
  advice: "问答建议",
  banter: "联动接梗",
  emotional: "情绪分享",
  explainer: "解释科普",
  reaction: "即时反应",
};

const toneModeLabel: Record<string, string> = {
  auto: "自动判断",
  conversational: "自然聊天",
  playful_teasing: "轻松调笑",
  light_banter: "轻量接梗",
  warm: "温暖",
  serious: "认真",
  reflective: "沉思",
  informative: "解释型",
  energetic: "高能量",
};

const depthBudgetLabel: Record<string, string> = {
  auto: "自动判断",
  light: "轻：不做理论化延伸",
  medium: "中：允许一个判断",
  deep: "深：可展开复杂论证",
};

type ReviewVariant = "with_dossier" | "no_dossier" | "human";

const comparisonColumns: Array<{
  variant: ReviewVariant;
  title: string;
  badge: string;
  tone: string;
}> = [
  {
    variant: "with_dossier",
    title: "AI 生成 A",
    badge: "Dossier 开启",
    tone: "border-violet-200 bg-violet-50 text-violet-800",
  },
  {
    variant: "no_dossier",
    title: "AI 生成 B",
    badge: "Dossier 关闭",
    tone: "border-sky-200 bg-sky-50 text-sky-800",
  },
  {
    variant: "human",
    title: "真人原始 Clip",
    badge: "参考原文",
    tone: "border-emerald-200 bg-emerald-50 text-emerald-800",
  },
];

const feedbackCategoryLabel: Record<NonNullable<TuningNote["category"]>, string> = {
  strength: "值得保留",
  world_knowledge: "常识 / 领域事实",
  fabricated_detail: "夸张 / 捏造细节",
  focus_drift: "核心发散 / 跑题",
  persona: "人设偏差",
  logic: "逻辑 / 结构",
  style: "语言 / 风格",
  repetition: "重复 / 冗余",
  safety: "边界 / 安全",
  other: "其他",
};

const severityLabel: Record<NonNullable<TuningNote["severity"]>, string> = {
  low: "轻微",
  medium: "中等",
  high: "严重",
};

const finalTextFromTrace = (candidate?: PipelineTrace) => {
  const output = candidate?.stages.find((stage) => stage.id === "runtime_output")?.output;
  if (!output || typeof output !== "object" || !("text" in output)) return "";
  return typeof output.text === "string" ? output.text : "";
};

const storyCoreFromTrace = (candidate?: PipelineTrace) => {
  const output = candidate?.stages.find((stage) => stage.id === "persona_analysis")?.output;
  if (!output || typeof output !== "object" || !("story_core" in output)) return null;
  const storyCore = output.story_core;
  if (!storyCore || typeof storyCore !== "object") return null;
  const value = storyCore as Record<string, unknown>;
  return {
    spine: typeof value.spine === "string" ? value.spine : "",
    discourseMode: typeof value.discourse_mode === "string" ? value.discourse_mode : "",
    toneMode: typeof value.tone_mode === "string" ? value.tone_mode : "",
    depthBudget: typeof value.depth_budget === "string" ? value.depth_budget : "",
    entertainmentMechanism: typeof value.entertainment_mechanism === "string"
      ? value.entertainment_mechanism
      : "",
    supportingPoints: Array.isArray(value.supporting_points)
      ? value.supporting_points.filter((item): item is string => typeof item === "string")
      : [],
    beats: Array.isArray(value.story_beats)
      ? value.story_beats.filter((item): item is string => typeof item === "string")
      : [],
  };
};

const tuningRulesFromTrace = (candidate?: PipelineTrace) => {
  const stage = candidate?.stages.find((item) => item.id === "tuning_guidance");
  const output = stage?.output;
  if (!output || typeof output !== "object" || !("rules" in output) || !Array.isArray(output.rules)) return [];
  return output.rules.flatMap((item) => {
    if (!item || typeof item !== "object") return [];
    const value = item as Record<string, unknown>;
    if (typeof value.rule !== "string") return [];
    return [{
      id: typeof value.id === "string" ? value.id : "",
      category: typeof value.category === "string" ? value.category : "other",
      rule: value.rule,
    }];
  });
};

const annotationTone = (note: TuningNote) => {
  if (note.feedback_type === "positive" || note.category === "strength") {
    return "bg-emerald-100 decoration-emerald-500";
  }
  if (note.severity === "high") return "bg-red-100 decoration-red-500";
  if (note.severity === "low") return "bg-sky-100 decoration-sky-500";
  return "bg-amber-100 decoration-amber-500";
};

const renderAnnotatedText = (text: string, notes: TuningNote[]) => {
  const occupied: Array<{ start: number; end: number; note: TuningNote }> = [];
  for (const note of notes) {
    const excerpt = note.target_excerpt?.trim();
    if (!excerpt) continue;
    const start = text.indexOf(excerpt);
    if (start < 0) continue;
    const end = start + excerpt.length;
    if (occupied.some((range) => start < range.end && end > range.start)) continue;
    occupied.push({ start, end, note });
  }
  occupied.sort((left, right) => left.start - right.start);

  const parts = [];
  let cursor = 0;
  for (const range of occupied) {
    if (range.start > cursor) parts.push(text.slice(cursor, range.start));
    parts.push(
      <mark
        key={range.note.id}
        className={`rounded px-0.5 text-inherit underline decoration-2 underline-offset-2 ${annotationTone(range.note)}`}
        title={range.note.issue_feedback || range.note.positive_feedback || range.note.observation}
      >
        {text.slice(range.start, range.end)}
      </mark>,
    );
    cursor = range.end;
  }
  if (cursor < text.length) parts.push(text.slice(cursor));
  return parts;
};

const emptyStatus: EvalStatus = {
  fixtures: 0,
  run_groups: 0,
  pairs_total: 0,
  pairs_judged: 0,
  pairs_pending: 0,
  generation: { running: false, completed: 0, total: 0, current: "", error: null },
};

const pipelineBlueprint = [
  {
    id: "input",
    label: "输入",
    detail: "角色名、人设、背景、主题与 Dossier 开关。",
    output: "本轮真正送进 Pipeline 的统一配置。",
    tuning: "角色、主题或实验条件不对时，先修样本和角色画像，不要急着改 Prompt。",
    icon: FileInput,
  },
  {
    id: "tuning_guidance",
    label: "批注规则",
    detail: "把 TRAIN 人工批注编译成可泛化规则，不把被批注原句直接喂回模型。",
    output: "本轮实际采用的批注 ID、问题分类、一般化规则与规则指纹。",
    tuning: "检查规则是否忠于批注意图且没有写成单样本特例；DEV/TEST 批注不会进入生成。",
    icon: FlaskConical,
  },
  {
    id: "dossier",
    label: "人物扩充",
    detail: "从静态人设推导身份张力、行为规则与长期记忆。",
    output: "扩展人设、冲突假设、触发器、禁区与行为规则。",
    tuning: "重点标注捏造事实、过度戏剧化和角色不一致；这些问题应修 Dossier 约束。",
    icon: Sparkles,
  },
  {
    id: "persona_analysis",
    label: "类型与内核",
    detail: "选择故事、观点、问答、联动等话语类型，并生成对应内容计划。",
    output: "话语类型、选择理由、丰富人设、内容内核与展开结构。",
    tuning: "先检查唯一主轴是不是一句明确结论，再看最多两个支撑点是否都为它服务；上游已经发散就修分析 Prompt。",
    icon: BrainCircuit,
  },
  {
    id: "unit_plan",
    label: "节目分段",
    detail: "把类型专属内容节点映射到 2–4 个时间与能量单元；非叙事默认最多 3 段。",
    output: "每段时间窗、语速/音高/音量、密度、主轴和支撑点。",
    tuning: "检查是否为了凑段数拆出支线，以及内容结构有没有被节奏切断。",
    icon: Route,
  },
  {
    id: "script_writer",
    label: "剧本生成",
    detail: "合并人物、内容计划、Dossier 与 few-shot 生成逐句台词。",
    output: "逐句脚本，以及每段的 purpose 与 spine_link（怎样推进唯一主轴）。",
    tuning: "逐段问“删掉后主结论是否有损失”；没有损失就标核心发散，并修改 Writer Prompt。",
    icon: ScrollText,
  },
  {
    id: "postprocess",
    label: "后处理",
    detail: "删除生硬升华，保留埋梗并整理最终脚本。",
    output: "规则清洗后的结构化台词。",
    tuning: "对比剧本生成：如果好句被删或坏句漏过，应改规则而不是重新训练写作风格。",
    icon: CircleDot,
  },
  {
    id: "runtime_output",
    label: "运行输出",
    detail: "按最大步数驱动引擎，汇总实际输出文本。",
    output: "用户最终看到的完整文本、步数与停止原因。",
    tuning: "若上游脚本正常而这里重复或截断，应排查引擎循环与停止条件。",
    icon: Play,
  },
  {
    id: "tts",
    label: "语音合成",
    detail: "将最终文本转换为可试听音频。",
    output: "音频路径、降级或失败状态。",
    tuning: "音色、韵律和内容质量分开评；TTS 问题不要反向污染文本 Prompt。",
    icon: Mic2,
  },
];

const preferredVariant = (run?: EvalRun) => {
  if (!run) return "";
  const available = new Set(run.variants.map((item) => item.variant));
  if (available.has("with_dossier")) return "with_dossier";
  if (available.has("no_dossier")) return "no_dossier";
  return available.has("human") ? "human" : "";
};

const Metric = ({ label, value, hint }: { label: string; value: string | number; hint: string }) => (
  <Card>
    <CardContent className="p-5">
      <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">{label}</div>
      <div className="mt-2 text-3xl font-bold text-slate-900">{value}</div>
      <div className="mt-1 text-xs text-slate-500">{hint}</div>
    </CardContent>
  </Card>
);

const QualityEvaluation = () => {
  const [fixtures, setFixtures] = useState<EvalFixture[]>([]);
  const [status, setStatus] = useState<EvalStatus>(emptyStatus);
  const [report, setReport] = useState<EvalReportRow[]>([]);
  const [runs, setRuns] = useState<EvalRun[]>([]);
  const [pair, setPair] = useState<EvalPair>({ done: true });
  const [selectedRun, setSelectedRun] = useState("");
  const [selectedVariant, setSelectedVariant] = useState("with_dossier");
  const [trace, setTrace] = useState<PipelineTrace | null>(null);
  const [comparisonTraces, setComparisonTraces] = useState<Partial<Record<ReviewVariant, PipelineTrace>>>({});
  const [comparisonLoading, setComparisonLoading] = useState(false);
  const [tuningNotes, setTuningNotes] = useState<TuningNote[]>([]);
  const [selectedStageId, setSelectedStageId] = useState("input");
  const [targetExcerpt, setTargetExcerpt] = useState("");
  const [positiveFeedback, setPositiveFeedback] = useState("");
  const [issueFeedback, setIssueFeedback] = useState("");
  const [adjustment, setAdjustment] = useState("");
  const [expectedEffect, setExpectedEffect] = useState("");
  const [tuningStatus, setTuningStatus] = useState<TuningNote["status"]>("planned");
  const [selectedFixture, setSelectedFixture] = useState("");
  const [repeats, setRepeats] = useState(3);
  const [showEvalAudio, setShowEvalAudio] = useState(false);
  const [showAllStages, setShowAllStages] = useState(false);
  const [reviewVariant, setReviewVariant] = useState<ReviewVariant>("with_dossier");
  const [reviewExcerpt, setReviewExcerpt] = useState("");
  const [reviewType, setReviewType] = useState<"positive" | "issue">("issue");
  const [reviewCategory, setReviewCategory] = useState<NonNullable<TuningNote["category"]>>("world_knowledge");
  const [reviewSeverity, setReviewSeverity] = useState<NonNullable<TuningNote["severity"]>>("medium");
  const [reviewComment, setReviewComment] = useState("");
  const [reviewAdjustment, setReviewAdjustment] = useState("");
  const [reviewExpected, setReviewExpected] = useState("");
  const [selectionToolbar, setSelectionToolbar] = useState<{ x: number; y: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const stageOutputRef = useRef<HTMLPreElement>(null);
  const variantSelectionIsManualRef = useRef(false);

  const refresh = useCallback(async () => {
    const [nextStatus, nextReport, nextPair, nextRuns] = await Promise.all([
      fetchEvalStatus(),
      fetchEvalReport(),
      fetchEvalNext(),
      fetchEvalRuns(),
    ]);
    setStatus(nextStatus);
    setReport(nextReport);
    setPair(nextPair);
    setRuns(nextRuns);
    setSelectedRun((current) => current || nextRuns[0]?.run_id || "");
  }, []);

  useEffect(() => {
    Promise.all([
      fetchEvalFixtures(),
      fetchEvalStatus(),
      fetchEvalReport(),
      fetchEvalNext(),
      fetchEvalRuns(),
      fetchTuningNotes(),
    ])
      .then(([nextFixtures, nextStatus, nextReport, nextPair, nextRuns, nextNotes]) => {
        setFixtures(nextFixtures);
        setSelectedFixture((current) => current || nextFixtures[0]?.id || "");
        setStatus(nextStatus);
        setReport(nextReport);
        setPair(nextPair);
        setRuns(nextRuns);
        setSelectedRun((current) => current || nextRuns[0]?.run_id || "");
        setTuningNotes(nextNotes);
      })
      .catch((reason) => setError(reason instanceof Error ? reason.message : "加载失败"))
      .finally(() => setLoading(false));
  }, []);

  const selectedRunRevision = useMemo(() => {
    const run = runs.find((item) => item.run_id === selectedRun);
    return run?.variants
      .map((item) => `${item.variant}:${item.generated_at_utc ?? ""}`)
      .sort()
      .join("|") ?? "";
  }, [runs, selectedRun]);

  useEffect(() => {
    if (!selectedRun || !selectedVariant) {
      setTrace(null);
      return;
    }
    fetchEvalTrace(selectedRun, selectedVariant)
      .then((nextTrace) => {
        setTrace(nextTrace);
        setSelectedStageId(nextTrace.stages[0]?.id ?? "input");
      })
      .catch(() => setTrace(null));
  }, [selectedRun, selectedRunRevision, selectedVariant]);

  useEffect(() => {
    if (!status.generation.running) return;
    const timer = window.setInterval(() => {
      refresh().catch((reason) => setError(reason instanceof Error ? reason.message : "刷新失败"));
    }, 2000);
    return () => window.clearInterval(timer);
  }, [refresh, status.generation.running]);

  const progress = useMemo(() => {
    if (!status.generation.total) return 0;
    return Math.round((status.generation.completed / status.generation.total) * 100);
  }, [status.generation.completed, status.generation.total]);

  const activeRun = useMemo(
    () => runs.find((run) => run.run_id === selectedRun),
    [runs, selectedRun],
  );
  const activeFixture = useMemo(
    () => fixtures.find((fixture) => fixture.id === selectedFixture) ?? null,
    [fixtures, selectedFixture],
  );
  const activeVariantKey = useMemo(
    () => activeRun?.variants.map((item) => item.variant).sort().join("|") ?? "",
    [activeRun],
  );
  const comparisonTexts = useMemo(
    () => ({
      with_dossier: finalTextFromTrace(comparisonTraces.with_dossier),
      no_dossier: finalTextFromTrace(comparisonTraces.no_dossier),
      human: finalTextFromTrace(comparisonTraces.human),
    }),
    [comparisonTraces],
  );
  const comparisonNotes = useMemo(
    () => ({
      with_dossier: tuningNotes.filter(
        (note) => note.run_id === selectedRun && note.variant === "with_dossier" && note.stage_id === "runtime_output",
      ),
      no_dossier: tuningNotes.filter(
        (note) => note.run_id === selectedRun && note.variant === "no_dossier" && note.stage_id === "runtime_output",
      ),
      human: tuningNotes.filter(
        (note) => note.run_id === selectedRun && note.variant === "human" && note.stage_id === "runtime_output",
      ),
    }),
    [selectedRun, tuningNotes],
  );
  const activeBlueprint = useMemo(
    () => pipelineBlueprint.find((item) => item.id === selectedStageId),
    [selectedStageId],
  );
  const selectedStage = useMemo(
    () => trace?.stages.find((stage) => stage.id === selectedStageId) ?? null,
    [trace, selectedStageId],
  );
  const traceDiscourseMode = useMemo(() => {
    const mode = trace?.stages.find((stage) => stage.id === "persona_analysis")
      ?.metrics?.discourse_mode;
    return typeof mode === "string" ? mode : "";
  }, [trace]);
  const traceStoryCore = useMemo(() => storyCoreFromTrace(trace ?? undefined), [trace]);
  const traceTuningRules = useMemo(() => tuningRulesFromTrace(trace ?? undefined), [trace]);
  const tracePromptAudit = useMemo(() => {
    const stages = trace?.stages ?? [];
    const leakedStages = stages.filter((stage) => stage.metrics?.prompt_leak_detected === true);
    const failedQualityStages = stages.filter(
      (stage) => stage.metrics?.quality_gate_passed === false,
    );
    const aiStages = stages.filter((stage) => stage.ai?.uses_ai);
    const longPromptStages = aiStages.filter(
      (stage) => Number(stage.ai?.max_prompt_chars ?? 0) > 6000,
    );
    return {
      leakedStages,
      failedQualityStages,
      longPromptStages,
      totalPromptChars: aiStages.reduce(
        (sum, stage) => sum + Number(stage.ai?.prompt_chars ?? 0),
        0,
      ),
      maxSinglePromptChars: aiStages.reduce(
        (max, stage) => Math.max(max, Number(stage.ai?.max_prompt_chars ?? 0)),
        0,
      ),
    };
  }, [trace]);
  const selectedTuningNotes = useMemo(
    () => tuningNotes.filter(
      (note) =>
        note.run_id === selectedRun &&
        note.variant === selectedVariant &&
        note.stage_id === selectedStageId,
    ),
    [selectedRun, selectedStageId, selectedVariant, tuningNotes],
  );

  useEffect(() => {
    let cancelled = false;
    if (!selectedRun || !activeVariantKey) {
      setComparisonTraces({});
      return () => {
        cancelled = true;
      };
    }
    const available = activeVariantKey.split("|") as ReviewVariant[];
    setComparisonLoading(true);
    Promise.all(
      available.map(async (variant) => [
        variant,
        await fetchEvalTrace(selectedRun, variant),
      ] as const),
    )
      .then((entries) => {
        if (!cancelled) setComparisonTraces(Object.fromEntries(entries));
      })
      .catch((reason) => {
        if (!cancelled) setError(reason instanceof Error ? reason.message : "三栏对照加载失败");
      })
      .finally(() => {
        if (!cancelled) setComparisonLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [activeVariantKey, selectedRun, selectedRunRevision]);

  useEffect(() => {
    setTargetExcerpt("");
    setPositiveFeedback("");
    setIssueFeedback("");
    setAdjustment("");
    setExpectedEffect("");
  }, [selectedRun, selectedStageId, selectedVariant]);

  useEffect(() => {
    setReviewVariant("with_dossier");
    setReviewExcerpt("");
    setReviewComment("");
    setReviewAdjustment("");
    setReviewExpected("");
    setSelectionToolbar(null);
  }, [selectedRun]);

  useEffect(() => {
    if (!activeRun) return;
    const available = activeRun.variants.map((item) => item.variant);
    const currentIsAvailable = available.includes(
      selectedVariant as "human" | "with_dossier" | "no_dossier",
    );
    if (!variantSelectionIsManualRef.current || !currentIsAvailable) {
      setSelectedVariant(preferredVariant(activeRun));
    }
  }, [activeRun, selectedVariant]);

  const handleRunChange = (runId: string) => {
    variantSelectionIsManualRef.current = false;
    setSelectedRun(runId);
    setSelectedVariant(preferredVariant(runs.find((run) => run.run_id === runId)));
  };

  const handleVariantChange = (variant: string) => {
    variantSelectionIsManualRef.current = true;
    setSelectedVariant(variant);
  };

  const handleGenerate = async () => {
    if (!selectedFixture) return;
    setBusy(true);
    setError("");
    try {
      await startEvalGeneration([selectedFixture], repeats);
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "启动生成失败");
    } finally {
      setBusy(false);
    }
  };

  const handleJudge = async (winner: "a" | "b" | "tie") => {
    if (pair.done) return;
    setBusy(true);
    setError("");
    try {
      await submitEvalJudgment(pair, winner);
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "提交评测失败");
    } finally {
      setBusy(false);
    }
  };

  const handleSaveTuning = async () => {
    const positive = positiveFeedback.trim();
    const issue = issueFeedback.trim();
    if (!selectedRun || !selectedVariant || !selectedStage || (!positive && !issue)) return;
    setBusy(true);
    setError("");
    try {
      const note = await createTuningNote({
        run_id: selectedRun,
        variant: selectedVariant,
        stage_id: selectedStage.id,
        observation: [
          positive ? `好在哪里：${positive}` : "",
          issue ? `不合理在哪里：${issue}` : "",
        ].filter(Boolean).join("\n"),
        target_excerpt: targetExcerpt.trim(),
        positive_feedback: positive,
        issue_feedback: issue,
        adjustment: adjustment.trim(),
        expected_effect: expectedEffect.trim(),
        status: tuningStatus,
      });
      setTuningNotes((current) => [note, ...current]);
      setTargetExcerpt("");
      setPositiveFeedback("");
      setIssueFeedback("");
      setAdjustment("");
      setExpectedEffect("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "保存调教记录失败");
    } finally {
      setBusy(false);
    }
  };

  const handleComparisonSelection = (
    variant: ReviewVariant,
    container: HTMLDivElement,
  ) => {
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0 || selection.isCollapsed) {
      setSelectionToolbar(null);
      return;
    }
    const range = selection.getRangeAt(0);
    if (!container.contains(range.commonAncestorContainer)) return;
    const excerpt = selection.toString().trim();
    if (!excerpt) return;
    const bounds = range.getBoundingClientRect();
    const panelWidth = 360;
    const panelHeight = 330;
    const x = Math.min(
      window.innerWidth - panelWidth - 16,
      Math.max(16, bounds.left + bounds.width / 2 - panelWidth / 2),
    );
    const preferredY = bounds.bottom + 10;
    const y = preferredY + panelHeight < window.innerHeight
      ? preferredY
      : Math.max(16, bounds.top - panelHeight - 10);
    setReviewVariant(variant);
    setReviewExcerpt(excerpt.slice(0, 4000));
    setReviewComment("");
    setReviewAdjustment("");
    setReviewExpected("");
    if (variant === "human") {
      setReviewType("positive");
      setReviewCategory("strength");
      setReviewSeverity("low");
    } else {
      setReviewType("issue");
      setReviewCategory("world_knowledge");
      setReviewSeverity("medium");
    }
    setSelectionToolbar({ x, y });
    setError("");
  };

  const applyReviewType = (type: "positive" | "issue") => {
    setReviewType(type);
    if (type === "positive") {
      setReviewCategory("strength");
      setReviewSeverity("low");
    } else if (reviewCategory === "strength") {
      setReviewCategory("world_knowledge");
      setReviewSeverity("medium");
    }
  };

  const handleSaveReview = async () => {
    const excerpt = reviewExcerpt.trim();
    const comment = reviewComment.trim();
    if (!selectedRun || !excerpt || !comment) return;
    setBusy(true);
    setError("");
    try {
      const note = await createTuningNote({
        run_id: selectedRun,
        variant: reviewVariant,
        stage_id: "runtime_output",
        observation: `${feedbackCategoryLabel[reviewCategory]}：${comment}`,
        target_excerpt: excerpt,
        positive_feedback: reviewType === "positive" ? comment : "",
        issue_feedback: reviewType === "issue" ? comment : "",
        adjustment: reviewAdjustment.trim(),
        expected_effect: reviewExpected.trim(),
        feedback_type: reviewType,
        category: reviewCategory,
        severity: reviewSeverity,
        status: "planned",
      });
      setTuningNotes((current) => [note, ...current]);
      setReviewExcerpt("");
      setReviewComment("");
      setReviewAdjustment("");
      setReviewExpected("");
      setSelectionToolbar(null);
      window.getSelection()?.removeAllRanges();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "保存文档批注失败");
    } finally {
      setBusy(false);
    }
  };

  const handleCaptureSelectedOutput = () => {
    const selection = window.getSelection();
    const output = stageOutputRef.current;
    if (!selection || !output || selection.rangeCount === 0 || selection.isCollapsed) {
      setError("请先在右侧“阶段输出”中拖选需要标注的原文。");
      return;
    }
    const range = selection.getRangeAt(0);
    if (!output.contains(range.commonAncestorContainer)) {
      setError("只能引用当前阶段输出中选中的内容。");
      return;
    }
    const excerpt = selection.toString().trim();
    if (!excerpt) {
      setError("没有读取到选中的输出内容。");
      return;
    }
    setTargetExcerpt(excerpt.slice(0, 4000));
    setError("");
  };

  const selectedStageUnavailableMessage = selectedVariant === "human"
    ? "真人原稿是评测基线，不经过这个 AI 阶段；请切换到 Dossier 开启查看完整输出。"
    : status.generation.running
      ? "当前变体仍在生成，这个阶段尚未写入 Trace。"
      : "当前 Trace 没有记录这个阶段。";

  if (loading) {
    return <div className="flex h-64 items-center justify-center text-slate-500"><Loader2 className="mr-2 animate-spin" />加载评测台...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-indigo-600">
            <FlaskConical size={18} />
            <span className="text-xs font-bold uppercase tracking-[0.2em]">Quality Lab</span>
          </div>
          <h1 className="mt-2 text-2xl font-bold text-slate-900">Echuu 生成质量评测</h1>
          <p className="mt-1 text-sm text-slate-500">多轮生成、真人基线与 Dossier 消融盲测。</p>
        </div>
        <Button variant="outline" className="gap-2" onClick={() => refresh()} disabled={busy}>
          <RefreshCw size={15} /> 刷新数据
        </Button>
      </div>

      {error && <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

      {selectionToolbar ? (
        <div
          role="dialog"
          aria-label="文档选区批注"
          className="fixed z-50 w-[360px] rounded-2xl border border-slate-200 bg-white p-4 shadow-2xl"
          style={{ left: selectionToolbar.x, top: selectionToolbar.y }}
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="text-xs font-bold text-slate-900">添加文档批注</div>
              <div className="mt-1 text-[11px] text-slate-400">
                {comparisonColumns.find((item) => item.variant === reviewVariant)?.title}
              </div>
            </div>
            <button
              type="button"
              aria-label="关闭文档批注"
              className="rounded-md px-2 py-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
              onClick={() => setSelectionToolbar(null)}
            >
              ×
            </button>
          </div>
          <blockquote className="mt-3 line-clamp-3 rounded-lg border-l-4 border-indigo-300 bg-slate-50 px-3 py-2 text-xs leading-5 text-slate-600">
            {reviewExcerpt}
          </blockquote>
          <div className="mt-3 grid grid-cols-2 gap-2">
            <button
              type="button"
              aria-pressed={reviewType === "positive"}
              className={`flex items-center justify-center gap-2 rounded-xl border px-3 py-2 text-sm font-semibold ${
                reviewType === "positive"
                  ? "border-emerald-400 bg-emerald-50 text-emerald-700"
                  : "border-slate-200 text-slate-500 hover:border-emerald-200"
              }`}
              onClick={() => applyReviewType("positive")}
            >
              <ThumbsUp size={14} /> 好
            </button>
            <button
              type="button"
              aria-pressed={reviewType === "issue"}
              className={`flex items-center justify-center gap-2 rounded-xl border px-3 py-2 text-sm font-semibold ${
                reviewType === "issue"
                  ? "border-red-400 bg-red-50 text-red-700"
                  : "border-slate-200 text-slate-500 hover:border-red-200"
              }`}
              onClick={() => applyReviewType("issue")}
            >
              <AlertTriangle size={14} /> 不好
            </button>
          </div>
          <div className="mt-3 grid grid-cols-[1fr_100px] gap-2">
            <select
              aria-label="浮层批注分类"
              className="min-w-0 rounded-lg border border-slate-200 bg-white px-2.5 py-2 text-xs"
              value={reviewCategory}
              onChange={(event) => setReviewCategory(event.target.value as NonNullable<TuningNote["category"]>)}
            >
              {Object.entries(feedbackCategoryLabel).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
            <select
              aria-label="浮层严重程度"
              className="rounded-lg border border-slate-200 bg-white px-2.5 py-2 text-xs"
              value={reviewSeverity}
              onChange={(event) => setReviewSeverity(event.target.value as NonNullable<TuningNote["severity"]>)}
              disabled={reviewType === "positive"}
            >
              {Object.entries(severityLabel).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>
          <textarea
            aria-label="浮层批注内容"
            className="mt-3 min-h-20 w-full rounded-xl border border-slate-200 p-3 text-sm outline-none focus:ring-2 focus:ring-indigo-500"
            placeholder="写下为什么好，或为什么不好…"
            value={reviewComment}
            onChange={(event) => setReviewComment(event.target.value)}
            maxLength={4000}
            autoFocus
          />
          <Button
            className="mt-3 w-full gap-2"
            onClick={handleSaveReview}
            disabled={!reviewComment.trim() || busy}
          >
            <Save size={14} /> 保存批注
          </Button>
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Metric label="Fixtures" value={status.fixtures} hint="真实直播片段样本" />
        <Metric label="Run groups" value={status.run_groups} hint="已生成的多轮样本" />
        <Metric label="Judged" value={`${status.pairs_judged}/${status.pairs_total}`} hint="已完成盲测对数" />
        <Metric label="Pending" value={status.pairs_pending} hint="待人工判断" />
      </div>

      <Card>
        <CardContent className="p-6">
          <div className="flex items-center gap-2">
            <Sparkles className="text-indigo-600" size={18} />
            <h2 className="font-bold text-slate-900">生成新评测组</h2>
          </div>
          <div className="mt-5 grid gap-4 lg:grid-cols-[1fr_140px_auto]">
            <label className="space-y-2">
              <span className="text-xs font-semibold text-slate-500">样本与角色画像</span>
              <select
                className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-indigo-500"
                value={selectedFixture}
                onChange={(event) => setSelectedFixture(event.target.value)}
              >
                {fixtures.map((fixture) => (
                  <option key={fixture.id} value={fixture.id}>
                    [{fixture.split.toUpperCase()}] {fixture.id} · {fixture.topic} · {fixture.character_name}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-2">
              <span className="text-xs font-semibold text-slate-500">重复轮数</span>
              <select
                className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-indigo-500"
                value={repeats}
                onChange={(event) => setRepeats(Number(event.target.value))}
              >
                {[1, 2, 3, 4, 5].map((value) => <option key={value} value={value}>{value} 轮</option>)}
              </select>
            </label>
            <div className="flex items-end">
              <Button className="w-full gap-2 lg:w-auto" onClick={handleGenerate} disabled={busy || status.generation.running}>
                {status.generation.running ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
                {status.generation.running ? "生成中" : "开始生成"}
              </Button>
            </div>
          </div>
          {activeFixture && (
            <div className="mt-4 space-y-3">
              <div className={`rounded-xl px-4 py-3 text-xs ${
                activeFixture.split === "test"
                  ? "border border-rose-200 bg-rose-50 text-rose-700"
                  : activeFixture.split === "dev"
                    ? "border border-amber-200 bg-amber-50 text-amber-700"
                    : "border border-sky-200 bg-sky-50 text-sky-700"
              }`}>
                <b>{splitLabel[activeFixture.split]}：</b>
                {activeFixture.split === "train"
                  ? "用于发现问题和修改 Prompt；few-shot 只从 TRAIN 池检索，并排除当前样本。"
                  : activeFixture.split === "dev"
                    ? "用于比较调教版本，不应针对单条结果继续加规则。"
                    : "用于阶段性最终检查；查看结果后该测试集就不再是严格未见集。"}
              </div>
              <div className="rounded-xl border border-violet-100 bg-violet-50/60 px-4 py-3">
                <div className="flex flex-wrap gap-2 text-[11px] font-semibold">
                  <span className="rounded-full bg-white px-2.5 py-1 text-violet-700">
                    目标语气：{toneModeLabel[activeFixture.tone_intent] ?? activeFixture.tone_intent}
                  </span>
                  <span className="rounded-full bg-white px-2.5 py-1 text-violet-700">
                    深度预算：{depthBudgetLabel[activeFixture.depth_budget] ?? activeFixture.depth_budget}
                  </span>
                </div>
                <p className="mt-2 text-xs leading-5 text-slate-600">
                  <b>这轮靠什么好看：</b>
                  {activeFixture.entertainment_mechanism || "未指定，由分析器判断"}
                </p>
              </div>
            </div>
          )}
          {status.generation.running && (
            <div className="mt-5">
              <div className="flex justify-between text-xs text-slate-500">
                <span>{status.generation.current || "准备模型..."}</span>
                <span>{status.generation.completed}/{status.generation.total} · {progress}%</span>
              </div>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100">
                <div className="h-full rounded-full bg-indigo-600 transition-all" style={{ width: `${progress}%` }} />
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <Quote className="text-indigo-600" size={19} />
                <h2 className="font-bold text-slate-900">三栏文档批注台</h2>
              </div>
              <p className="mt-1 text-xs text-slate-500">
                左边对照两个 AI 版本，右边查看真人原始 Clip；像批注文档一样框选文字并写评论。
              </p>
            </div>
            <label className="space-y-1">
              <span className="block text-[11px] font-semibold text-slate-400">评测运行</span>
              <select
                aria-label="三栏批注运行批次"
                className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                value={selectedRun}
                onChange={(event) => handleRunChange(event.target.value)}
                disabled={!runs.length}
              >
                {!runs.length && <option value="">尚无运行记录</option>}
                {runs.map((run) => <option key={run.run_id} value={run.run_id}>{run.run_id}</option>)}
              </select>
            </label>
          </div>

          <div className="mt-4 rounded-xl border border-indigo-100 bg-indigo-50 px-4 py-3 text-xs leading-5 text-indigo-800">
            <b>这是定性诊断区，不计入匿名胜率。</b>
            先用原文判断 AI 是否始终回答同一个核心，再检查常识、捏造和夸张；跑题处选“核心发散 / 跑题”，
            选中文字会自动进入统一批注表。
          </div>

          <div className="mt-5 overflow-x-auto pb-2">
            <div className="grid min-w-[1260px] grid-cols-3 gap-4">
              {comparisonColumns.map((column) => {
                const text = comparisonTexts[column.variant];
                const notes = comparisonNotes[column.variant];
                return (
                  <article key={column.variant} className="min-w-0 rounded-2xl border border-slate-200 bg-white">
                    <div className="flex items-center justify-between gap-3 border-b border-slate-100 px-4 py-3">
                      <div>
                        <h3 className="text-sm font-bold text-slate-900">{column.title}</h3>
                        <span className={`mt-1 inline-flex rounded-full border px-2.5 py-1 text-[10px] font-semibold ${column.tone}`}>
                          {column.badge}
                        </span>
                      </div>
                      <span className="text-[11px] text-slate-400">{text.length.toLocaleString()} 字</span>
                    </div>
                    <div className="grid h-[600px] grid-cols-[minmax(0,1fr)_150px]">
                      <div
                        className="select-text overflow-y-auto whitespace-pre-wrap px-4 py-4 text-sm leading-7 text-slate-700 selection:bg-indigo-200"
                        onMouseUp={(event) => handleComparisonSelection(column.variant, event.currentTarget)}
                      >
                        {comparisonLoading && !text
                          ? "正在加载该版本..."
                          : text
                            ? renderAnnotatedText(text, notes)
                            : "这个运行尚未生成该版本。"}
                      </div>
                      <aside className="overflow-y-auto border-l border-slate-100 bg-slate-50/80">
                        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-slate-200 bg-slate-50 px-3 py-2.5">
                          <span className="text-[11px] font-bold text-slate-600">批注栏</span>
                          <span className="text-[10px] text-slate-400">{notes.length} 条</span>
                        </div>
                        <div className="space-y-2 p-2">
                          {notes.map((note) => (
                            <div key={note.id} className="relative rounded-lg border border-slate-200 bg-white p-2.5 text-[11px] shadow-sm">
                              <span className="absolute -left-2 top-4 h-px w-2 bg-slate-300" />
                              <div className="flex flex-wrap gap-1">
                                <span className={`rounded-full px-1.5 py-0.5 font-semibold ${
                                  note.feedback_type === "positive"
                                    ? "bg-emerald-50 text-emerald-700"
                                    : "bg-red-50 text-red-700"
                                }`}>
                                  {note.feedback_type === "positive" ? "好" : "不好"}
                                </span>
                                <span className="rounded-full bg-slate-100 px-1.5 py-0.5 text-slate-600">
                                  {feedbackCategoryLabel[note.category ?? "other"]}
                                </span>
                              </div>
                              {note.target_excerpt ? (
                                <blockquote className="mt-2 line-clamp-3 border-l-2 border-indigo-300 pl-1.5 leading-4 text-slate-400">
                                  {note.target_excerpt}
                                </blockquote>
                              ) : null}
                              <div className="mt-2 leading-4 text-slate-700">
                                {note.issue_feedback || note.positive_feedback || note.observation}
                              </div>
                            </div>
                          ))}
                          {notes.length === 0 ? (
                            <div className="rounded-lg border border-dashed border-slate-200 px-2 py-5 text-center text-[11px] leading-4 text-slate-400">
                              框选文档后，评论会显示在这里
                            </div>
                          ) : null}
                        </div>
                      </aside>
                    </div>
                  </article>
                );
              })}
            </div>
          </div>

          <div className="mt-5 rounded-2xl border border-indigo-200 bg-indigo-50/40 p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="font-bold text-slate-900">统一批注任务</h3>
                <p className="mt-1 text-xs text-slate-500">
                  所有版本都在这里填写，保存后原文会高亮并在对应栏显示评论。
                </p>
              </div>
              <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-indigo-700">
                {comparisonColumns.find((item) => item.variant === reviewVariant)?.title}
              </span>
            </div>

            <div className="mt-4 space-y-4">
              <div className="grid gap-3 lg:grid-cols-[180px_1fr]">
                <label className="space-y-1">
                  <span className="text-[11px] font-semibold text-slate-500">批注对象</span>
                  <select
                    aria-label="文档批注对象"
                    className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm"
                    value={reviewVariant}
                    onChange={(event) => setReviewVariant(event.target.value as ReviewVariant)}
                  >
                    {comparisonColumns.map((column) => (
                      <option key={column.variant} value={column.variant}>{column.title}</option>
                    ))}
                  </select>
                </label>
                <label className="space-y-1">
                  <span className="text-[11px] font-semibold text-slate-500">
                    引用原文（框选上方文字会自动填入，也可以手动粘贴）
                  </span>
                  <textarea
                    aria-label="文档批注引用原文"
                    className="min-h-20 w-full rounded-xl border border-indigo-200 bg-white p-3 text-sm leading-6 outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="请先在三栏中框选文字，或把需要批注的原句粘贴到这里"
                    value={reviewExcerpt}
                    onChange={(event) => setReviewExcerpt(event.target.value)}
                    maxLength={4000}
                  />
                </label>
              </div>
                <div className="grid gap-3 lg:grid-cols-[180px_220px_140px_1fr]">
                  <div className="space-y-1">
                    <span className="text-[11px] font-semibold text-slate-500">好 / 不好</span>
                    <div className="grid grid-cols-2 gap-2">
                      <button
                        type="button"
                        aria-label="标为好"
                        aria-pressed={reviewType === "positive"}
                        className={`flex items-center justify-center gap-1.5 rounded-xl border px-2 py-2.5 text-sm font-semibold ${
                          reviewType === "positive"
                            ? "border-emerald-400 bg-emerald-50 text-emerald-700"
                            : "border-slate-200 bg-white text-slate-500"
                        }`}
                        onClick={() => applyReviewType("positive")}
                      >
                        <ThumbsUp size={14} /> 好
                      </button>
                      <button
                        type="button"
                        aria-label="标为不好"
                        aria-pressed={reviewType === "issue"}
                        className={`flex items-center justify-center gap-1.5 rounded-xl border px-2 py-2.5 text-sm font-semibold ${
                          reviewType === "issue"
                            ? "border-red-400 bg-red-50 text-red-700"
                            : "border-slate-200 bg-white text-slate-500"
                        }`}
                        onClick={() => applyReviewType("issue")}
                      >
                        <AlertTriangle size={14} /> 不好
                      </button>
                    </div>
                  </div>
                  <label className="space-y-1">
                    <span className="text-[11px] font-semibold text-slate-500">问题分类</span>
                    <select
                      aria-label="批注问题分类"
                      className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm"
                      value={reviewCategory}
                      onChange={(event) => setReviewCategory(event.target.value as NonNullable<TuningNote["category"]>)}
                    >
                      {Object.entries(feedbackCategoryLabel).map(([value, label]) => (
                        <option key={value} value={value}>{label}</option>
                      ))}
                    </select>
                  </label>
                  <label className="space-y-1">
                    <span className="text-[11px] font-semibold text-slate-500">严重程度</span>
                    <select
                      aria-label="批注严重程度"
                      className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm"
                      value={reviewSeverity}
                      onChange={(event) => setReviewSeverity(event.target.value as NonNullable<TuningNote["severity"]>)}
                      disabled={reviewType === "positive"}
                    >
                      {Object.entries(severityLabel).map(([value, label]) => (
                        <option key={value} value={value}>{label}</option>
                      ))}
                    </select>
                  </label>
                  <label className="space-y-1">
                    <span className="text-[11px] font-semibold text-slate-500">你的判断</span>
                    <textarea
                      aria-label="文档批注判断"
                      className="min-h-20 w-full rounded-xl border border-slate-200 bg-white p-3 text-sm outline-none focus:ring-2 focus:ring-indigo-500"
                      placeholder="说明它为什么好，或为什么不符合常识、角色与上下文"
                      value={reviewComment}
                      onChange={(event) => setReviewComment(event.target.value)}
                      maxLength={4000}
                    />
                  </label>
                </div>
                <div className="grid gap-3 lg:grid-cols-2">
                  <textarea
                    aria-label="文档批注矫正建议"
                    className="min-h-20 rounded-xl border border-slate-200 bg-white p-3 text-sm outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="建议怎么改：写成可执行的 Prompt、规则或数据修正"
                    value={reviewAdjustment}
                    onChange={(event) => setReviewAdjustment(event.target.value)}
                    maxLength={4000}
                  />
                  <textarea
                    aria-label="文档批注验证标准"
                    className="min-h-20 rounded-xl border border-slate-200 bg-white p-3 text-sm outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="怎么验证改好了：写出跨样本测试标准"
                    value={reviewExpected}
                    onChange={(event) => setReviewExpected(event.target.value)}
                    maxLength={4000}
                  />
                </div>
                <div className="flex justify-end">
                  <Button
                    className="gap-2"
                    onClick={handleSaveReview}
                    disabled={!reviewExcerpt.trim() || !reviewComment.trim() || busy}
                  >
                    <Save size={15} /> 保存并高亮批注
                  </Button>
                </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <BrainCircuit className="text-indigo-600" size={19} />
                <h2 className="font-bold text-slate-900">Pipeline 调试台</h2>
              </div>
              <p className="mt-1 text-xs text-slate-500">先选 AI 变体，再逐阶段定位质量从哪里开始偏移。</p>
            </div>
            <div className="flex flex-wrap gap-3">
              <label className="space-y-1">
                <span className="block text-[11px] font-semibold text-slate-400">1. 运行批次</span>
                <select
                  aria-label="Pipeline 运行批次"
                  className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                  value={selectedRun}
                  onChange={(event) => handleRunChange(event.target.value)}
                  disabled={!runs.length}
                >
                  {!runs.length && <option value="">尚无运行记录</option>}
                  {runs.map((run) => <option key={run.run_id} value={run.run_id}>{run.run_id}</option>)}
                </select>
              </label>
              <label className="space-y-1">
                <span className="block text-[11px] font-semibold text-slate-400">2. 查看变体</span>
                <select
                  aria-label="Pipeline 查看变体"
                  className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                  value={selectedVariant}
                  onChange={(event) => handleVariantChange(event.target.value)}
                  disabled={!activeRun}
                >
                  {(activeRun?.variants ?? []).map((item) => (
                    <option key={item.variant} value={item.variant}>
                      {item.variant === "with_dossier"
                        ? "Dossier 开启 · 完整 AI Pipeline"
                        : item.variant === "no_dossier"
                          ? "Dossier 关闭 · 消融 Pipeline"
                          : "真人原稿 · 只作基线"}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </div>
          <div className="mt-5 grid gap-3 md:grid-cols-3">
            {[
              ["① 选运行和变体", "调 Prompt 时用 TRAIN；要看完整链路请选择 Dossier 开启。"],
              ["② 点阶段找偏移", "从左到右检查；第一个明显错误的阶段，才是优先调教对象。"],
              ["③ 引用输出并记录", "框选具体原文，写清好/坏、矫正动作和可验证的预期。"],
            ].map(([title, detail]) => (
              <div key={title} className="rounded-xl border border-indigo-100 bg-indigo-50/50 px-4 py-3">
                <div className="text-xs font-bold text-indigo-800">{title}</div>
                <div className="mt-1 text-xs leading-5 text-indigo-700/80">{detail}</div>
              </div>
            ))}
          </div>
          {status.run_groups > 0 && runs.length === 0 && (
            <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
              现有生成结果来自 Trace 功能启用之前，只有最终文本，无法还原中间阶段。请重新生成一组以查看完整 Pipeline。
            </div>
          )}
          {selectedVariant === "human" ? (
            <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-800">
              <b>当前是“真人原稿”基线：</b>
              它只有输入、最终文本和 TTS，不经过人物扩充、类型分析、分段或剧本生成。
              要看每阶段输出，请在“查看变体”切换到 <b>Dossier 开启 · 完整 AI Pipeline</b>。
            </div>
          ) : (
            <div className="mt-5 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
              当前正在查看 <b>{variantLabel[selectedVariant]}</b> 的 AI Trace；绿色为完成、灰色为跳过、黄色为降级。
            </div>
          )}
          {selectedVariant !== "human" && trace ? (
            <>
              <div className={`mt-3 rounded-xl border px-4 py-3 text-sm ${
                tracePromptAudit.leakedStages.length
                  ? "border-red-200 bg-red-50 text-red-800"
                  : "border-emerald-200 bg-emerald-50 text-emerald-800"
              }`}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <b>
                    Prompt 内泄审计：
                    {tracePromptAudit.leakedStages.length
                      ? `发现 ${tracePromptAudit.leakedStages.length} 个风险阶段`
                      : "所有已记录阶段通过"}
                  </b>
                  <span className="text-xs">
                    累计 Prompt {tracePromptAudit.totalPromptChars.toLocaleString()} 字
                    {tracePromptAudit.maxSinglePromptChars
                      ? ` · 单次最大 ${tracePromptAudit.maxSinglePromptChars.toLocaleString()} 字`
                      : ""}
                  </span>
                </div>
                {tracePromptAudit.leakedStages.length ? (
                  <p className="mt-1 text-xs leading-5">
                    风险阶段：{tracePromptAudit.leakedStages.map((stage) => stage.label).join("、")}。
                    点击红点阶段查看 prompt_leak_markers；该轮不应进入盲测。
                  </p>
                ) : (
                  <p className="mt-1 text-xs leading-5">
                    这里只代表内部字段名、调教规则片段和质量守门文案没有进入可见输出，
                    不代表台词已经通过事实与内容质量检查。
                  </p>
                )}
              </div>
              {tracePromptAudit.failedQualityStages.length ? (
                <div className="mt-3 rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                  <b>
                    生成质量门失败：{tracePromptAudit.failedQualityStages
                      .map((stage) => stage.label)
                      .join("、")}
                  </b>
                  <p className="mt-1 text-xs leading-5">
                    当前输出已安全降级，不能拿占位文本做盲测。点击对应黄色阶段，
                    查看 quality_gate_first_issues、quality_gate_retry_issues 及其 details。
                  </p>
                </div>
              ) : null}
              {tracePromptAudit.longPromptStages.length ? (
                <div className="mt-3 rounded-xl border border-orange-200 bg-orange-50 px-4 py-3 text-xs leading-5 text-orange-800">
                  <b>长 Prompt 风险：</b>
                  {tracePromptAudit.longPromptStages.map((stage) => (
                    <span key={stage.id} className="ml-1">
                      {stage.label} {Number(stage.ai?.max_prompt_chars ?? 0).toLocaleString()} 字
                    </span>
                  ))}
                  。单次超过 6,000 字会提高规则互相干扰和复述内部措辞的风险，建议优先压缩该阶段。
                </div>
              ) : null}
            </>
          ) : null}
          {trace?.evaluation_context && (
            <div className="mt-5 flex flex-wrap gap-2 text-xs">
              <span className="rounded-full bg-slate-100 px-3 py-1.5 text-slate-600">
                Split: {trace.evaluation_context.split.toUpperCase()}
              </span>
              <span className="rounded-full bg-slate-100 px-3 py-1.5 text-slate-600">
                Retrieval seed: {trace.evaluation_context.retrieval_seed}
              </span>
              <span className="rounded-full bg-slate-100 px-3 py-1.5 text-slate-600">
                TRAIN pool: {trace.evaluation_context.retrieval_allowed_pool_size ?? "unbounded"}
              </span>
              <span className="rounded-full bg-rose-50 px-3 py-1.5 text-rose-700">
                Excluded: {trace.evaluation_context.retrieval_exclude_ids.join(", ") || "none"}
              </span>
              {traceDiscourseMode ? (
                <span className="rounded-full bg-violet-50 px-3 py-1.5 font-semibold text-violet-700">
                  话语类型: {discourseModeLabel[traceDiscourseMode] ?? traceDiscourseMode}
                </span>
              ) : null}
            </div>
          )}
          {selectedVariant !== "human" && traceTuningRules.length ? (
            <div className="mt-5 rounded-2xl border border-emerald-200 bg-emerald-50/60 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-xs font-bold uppercase tracking-wider text-emerald-700">本轮采用的人类批注</span>
                <span className="rounded-full bg-white px-2.5 py-1 text-[11px] font-semibold text-emerald-700">
                  TRAIN 规则 {traceTuningRules.length} 条
                </span>
              </div>
              <div className="mt-3 grid gap-2 md:grid-cols-2">
                {traceTuningRules.map((item, index) => (
                  <div key={item.id || `${item.category}-${index}`} className="rounded-xl border border-emerald-100 bg-white px-3 py-2.5">
                    <div className="text-[10px] font-bold uppercase tracking-wider text-emerald-600">
                      {feedbackCategoryLabel[item.category as NonNullable<TuningNote["category"]>] ?? item.category}
                    </div>
                    <p className="mt-1 text-xs leading-5 text-slate-600">{item.rule}</p>
                  </div>
                ))}
              </div>
              <p className="mt-3 text-xs text-emerald-800/70">
                这里只传一般规则，不传被批注原句；因此能利用你的反馈，同时降低记住单条样本的风险。
              </p>
            </div>
          ) : null}
          {selectedVariant !== "human" && traceStoryCore?.spine ? (
            <div className="mt-5 rounded-2xl border border-indigo-200 bg-gradient-to-r from-indigo-50 to-white p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-xs font-bold uppercase tracking-wider text-indigo-500">本轮内容骨架 · 先骨架后成稿</span>
                <span className="rounded-full bg-white px-2.5 py-1 text-[11px] font-semibold text-indigo-700">
                  删段测试：删后不影响结论 = 发散
                </span>
              </div>
              <div className="mt-3 rounded-xl border border-indigo-100 bg-white px-4 py-3">
                <div className="text-[10px] font-bold uppercase tracking-wider text-indigo-500">唯一主轴</div>
                <p className="mt-1 text-sm font-semibold leading-6 text-slate-900">{traceStoryCore.spine}</p>
              </div>
              <div className="mt-3 grid gap-2 md:grid-cols-3">
                <div className="rounded-xl border border-indigo-100 bg-white px-3 py-2.5">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">表达方式</div>
                  <p className="mt-1 text-xs font-semibold text-slate-700">
                    {(toneModeLabel[traceStoryCore.toneMode] ?? traceStoryCore.toneMode) || "旧 Trace 未记录"}
                  </p>
                </div>
                <div className="rounded-xl border border-indigo-100 bg-white px-3 py-2.5">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">深度预算</div>
                  <p className="mt-1 text-xs font-semibold text-slate-700">
                    {(depthBudgetLabel[traceStoryCore.depthBudget] ?? traceStoryCore.depthBudget) || "旧 Trace 未记录"}
                  </p>
                </div>
                <div className="rounded-xl border border-indigo-100 bg-white px-3 py-2.5">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">好看的机制</div>
                  <p className="mt-1 text-xs font-semibold leading-5 text-slate-700">
                    {traceStoryCore.entertainmentMechanism || "旧 Trace 未记录"}
                  </p>
                </div>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {traceStoryCore.supportingPoints.length ? traceStoryCore.supportingPoints.map((point, index) => (
                  <span key={`${index}-${point}`} className="rounded-lg border border-indigo-100 bg-white px-3 py-1.5 text-xs text-slate-600">
                    支撑 {index + 1}：{point}
                  </span>
                )) : (
                  <span className="text-xs text-amber-700">旧 Trace 没有独立记录支撑点；重新生成后可见。</span>
                )}
              </div>
              {traceStoryCore.beats.length ? (
                <div className="mt-4 grid gap-2 md:grid-cols-3">
                  {traceStoryCore.beats.map((beat, index) => (
                    <div key={`${index}-${beat}`} className="rounded-xl border border-violet-100 bg-violet-50/60 px-3 py-3">
                      <div className="text-[10px] font-bold uppercase tracking-wider text-violet-500">推进 {index + 1}</div>
                      <p className="mt-1 text-xs leading-5 text-slate-700">{beat}</p>
                    </div>
                  ))}
                </div>
              ) : null}
              <p className="mt-3 text-xs leading-5 text-slate-500">
                先检查这份骨架是否合理，再点“剧本生成”检查每个 Unit 的 purpose 和 spine_link；
                如果成稿偏离骨架，就在文档批注台框选并标为“核心发散 / 跑题”。
              </p>
            </div>
          ) : null}

          <div className="mt-6 overflow-x-auto pb-2">
            <div className="flex min-w-max items-center gap-2">
              {pipelineBlueprint.map((blueprint, index) => {
                const stage = trace?.stages.find((item) => item.id === blueprint.id);
                const isActive = selectedStageId === blueprint.id;
                const Icon = blueprint.icon;
                const missingLabel = selectedVariant === "human"
                  ? "基线不经过"
                  : status.generation.running
                    ? "尚未完成"
                    : "Trace 未记录";
                return (
                  <div key={blueprint.id} className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setSelectedStageId(blueprint.id)}
                      className={`w-36 rounded-2xl border px-3 py-3 text-left transition-colors ${
                        isActive
                          ? "border-indigo-500 bg-indigo-50 text-indigo-800"
                          : "border-slate-200 bg-white text-slate-600 hover:border-indigo-200"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <Icon size={16} />
                        <span className={`h-2 w-2 rounded-full ${
                          stage?.metrics?.prompt_leak_detected === true ? "bg-red-500" :
                          stage?.status === "completed" ? "bg-emerald-500" :
                          stage?.status === "degraded" ? "bg-amber-500" :
                          stage?.status === "failed" ? "bg-red-500" :
                          stage?.status === "skipped" ? "bg-slate-300" : "bg-slate-200"
                        }`} />
                      </div>
                      <div className="mt-2 text-sm font-bold">{blueprint.label}</div>
                      <div className="mt-1 text-[11px] text-slate-400">
                        {stage ? `${stage.duration_ms.toLocaleString()} ms` : missingLabel}
                      </div>
                      <div className={`mt-2 text-[10px] font-semibold ${
                        stage?.ai?.uses_ai ? "text-violet-600" : "text-slate-300"
                      }`}>
                        {!stage
                          ? selectedVariant === "human"
                            ? "真人基线跳过"
                            : status.generation.running
                              ? "等待当前变体"
                              : "无阶段数据"
                          : stage.ai?.uses_ai
                            ? `AI ×${stage.ai.call_count} · ${stage.ai.model ?? "unknown"}`
                            : stage.status === "skipped"
                              ? "按实验条件跳过"
                              : "规则处理 · No AI"}
                      </div>
                    </button>
                    {index < pipelineBlueprint.length - 1 && <ChevronRight size={16} className="text-slate-300" />}
                  </div>
                );
              })}
            </div>
          </div>

          <div className="mt-5 grid gap-4 xl:grid-cols-[280px_1fr_1fr]">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-400">阶段说明</div>
              <div className="mt-3 font-bold text-slate-800">
                {activeBlueprint?.label}
              </div>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                {activeBlueprint?.detail}
              </p>
              <div className="mt-4 rounded-xl border border-sky-100 bg-sky-50 p-3 text-xs leading-5 text-sky-800">
                <b>这一阶段输出：</b>{activeBlueprint?.output}
              </div>
              <div className="mt-3 rounded-xl border border-violet-100 bg-violet-50 p-3 text-xs leading-5 text-violet-800">
                <b>怎么调：</b>{activeBlueprint?.tuning}
              </div>
              {selectedStage && (
                <div className="mt-4 rounded-xl border border-slate-200 bg-white p-3">
                  <div className="flex items-center gap-2 text-xs font-semibold text-slate-600">
                    <Clock3 size={14} className="text-indigo-500" />
                    阶段总耗时 {selectedStage.duration_ms.toLocaleString()} ms
                  </div>
                  <div className="mt-2 flex items-start gap-2 text-xs">
                    <Bot size={14} className={selectedStage.ai?.uses_ai ? "text-violet-500" : "text-slate-300"} />
                    {selectedStage.ai?.uses_ai ? (
                      <div>
                        <div className="font-semibold text-violet-700">
                          {selectedStage.ai.provider} / {selectedStage.ai.model}
                        </div>
                        <div className="mt-1 text-slate-500">
                          {selectedStage.ai.call_count} 次 · AI {selectedStage.ai.duration_ms ?? 0} ms
                          {selectedStage.ai.failed_calls ? ` · 失败 ${selectedStage.ai.failed_calls}` : ""}
                        </div>
                        <div className="mt-1 text-slate-400">
                          Prompt {selectedStage.ai.prompt_chars ?? 0} 字 · Response {selectedStage.ai.response_chars ?? 0} 字
                        </div>
                        {selectedStage.ai.max_prompt_chars ? (
                          <div className="mt-1 text-slate-400">
                            单次平均 {selectedStage.ai.avg_prompt_chars ?? 0} 字 · 最大 {selectedStage.ai.max_prompt_chars} 字
                          </div>
                        ) : null}
                      </div>
                    ) : (
                      <span className="text-slate-400">本阶段不调用生成模型</span>
                    )}
                  </div>
                  {selectedStage.metrics?.quality_gate_passed === false ? (
                    <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-2 text-xs leading-5 text-amber-800">
                      <b>质量门未通过</b>
                      <div>
                        首稿：
                        {Array.isArray(selectedStage.metrics?.quality_gate_first_issues)
                          ? selectedStage.metrics.quality_gate_first_issues.join("、")
                          : "未知"}
                      </div>
                      <div>
                        重试：
                        {Array.isArray(selectedStage.metrics?.quality_gate_retry_issues)
                          ? selectedStage.metrics.quality_gate_retry_issues.join("、")
                          : "未知"}
                      </div>
                      {Array.isArray(selectedStage.metrics?.quality_gate_retry_issue_details)
                        && selectedStage.metrics.quality_gate_retry_issue_details.length ? (
                          <div className="mt-1 break-all text-amber-700">
                            命中细节：{selectedStage.metrics.quality_gate_retry_issue_details.join("；")}
                          </div>
                        ) : null}
                    </div>
                  ) : null}
                </div>
              )}
              {selectedStage?.metrics && (
                <div className="mt-4 space-y-2 border-t border-slate-200 pt-4">
                  {Object.entries(selectedStage.metrics).map(([key, value]) => (
                    <div key={key} className="flex justify-between gap-3 text-xs">
                      <span className="text-slate-400">{key}</span>
                      <span className="text-right font-mono text-slate-700">{String(value)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div className="min-w-0 rounded-2xl border border-slate-200">
              <div className="border-b border-slate-100 px-4 py-3 text-xs font-bold uppercase tracking-wider text-slate-400">阶段输入</div>
              <pre className="max-h-96 overflow-auto whitespace-pre-wrap break-words p-4 text-xs leading-5 text-slate-700">
                {selectedStage ? JSON.stringify(selectedStage.input ?? null, null, 2) : selectedStageUnavailableMessage}
              </pre>
            </div>
            <div className="min-w-0 rounded-2xl border border-slate-200">
              <div className="flex items-center justify-between gap-3 border-b border-slate-100 px-4 py-3">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-400">阶段输出</span>
                <button
                  type="button"
                  className="flex items-center gap-1.5 rounded-lg bg-indigo-50 px-2.5 py-1.5 text-[11px] font-semibold text-indigo-700 hover:bg-indigo-100 disabled:cursor-not-allowed disabled:opacity-40"
                  onMouseDown={(event) => {
                    event.preventDefault();
                    handleCaptureSelectedOutput();
                  }}
                  disabled={!selectedStage}
                >
                  <Quote size={12} /> 引用选中输出
                </button>
              </div>
              <pre ref={stageOutputRef} className="max-h-96 overflow-auto whitespace-pre-wrap break-words p-4 text-xs leading-5 text-slate-700 selection:bg-indigo-200">
                {selectedStage ? JSON.stringify(selectedStage.output ?? null, null, 2) : selectedStageUnavailableMessage}
              </pre>
            </div>
          </div>

          <div className="mt-5 rounded-2xl border border-slate-200">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4">
              <div>
                <h3 className="font-bold text-slate-900">全链路输出总览</h3>
                <p className="mt-1 text-xs text-slate-500">
                  一次展开当前 Trace 的全部阶段，适合从上游到下游寻找第一个质量偏移点。
                </p>
              </div>
              <Button
                variant="outline"
                onClick={() => setShowAllStages((current) => !current)}
                disabled={!trace}
              >
                {showAllStages ? "收起全部阶段" : `展开全部 ${trace?.stages.length ?? 0} 个阶段`}
              </Button>
            </div>
            {showAllStages && trace ? (
              <div className="space-y-4 p-5">
                {trace.stages.map((stage, index) => {
                  const blueprint = pipelineBlueprint.find((item) => item.id === stage.id);
                  return (
                    <article
                      key={stage.id}
                      className="rounded-2xl border border-slate-200 bg-slate-50 p-4 [content-visibility:auto]"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div className="flex items-center gap-3">
                          <span className="flex h-7 w-7 items-center justify-center rounded-full bg-indigo-600 text-xs font-bold text-white">
                            {index + 1}
                          </span>
                          <div>
                            <div className="font-bold text-slate-900">{blueprint?.label ?? stage.label}</div>
                            <div className="mt-0.5 text-xs text-slate-500">{blueprint?.output}</div>
                          </div>
                        </div>
                        <div className="flex flex-wrap gap-2 text-[11px]">
                          <span className="rounded-full bg-white px-2.5 py-1 text-slate-600">
                            {stage.status}
                          </span>
                          <span className="rounded-full bg-white px-2.5 py-1 text-slate-600">
                            {stage.duration_ms.toLocaleString()} ms
                          </span>
                          <span className="rounded-full bg-violet-50 px-2.5 py-1 text-violet-700">
                            {stage.ai?.uses_ai
                              ? `AI ×${stage.ai.call_count} · ${stage.ai.model ?? "unknown"}`
                              : "No AI"}
                          </span>
                        </div>
                      </div>
                      <div className="mt-4 grid gap-3 lg:grid-cols-2">
                        <details className="rounded-xl border border-slate-200 bg-white">
                          <summary className="cursor-pointer px-4 py-3 text-xs font-bold text-slate-600">查看阶段输入</summary>
                          <pre className="max-h-80 overflow-auto border-t border-slate-100 p-4 text-xs leading-5 text-slate-700">
                            {JSON.stringify(stage.input ?? null, null, 2)}
                          </pre>
                        </details>
                        <details className="rounded-xl border border-indigo-100 bg-white" open>
                          <summary className="cursor-pointer px-4 py-3 text-xs font-bold text-indigo-700">查看阶段输出</summary>
                          <pre className="max-h-80 overflow-auto whitespace-pre-wrap break-words border-t border-indigo-50 p-4 text-xs leading-5 text-slate-700">
                            {JSON.stringify(stage.output ?? null, null, 2)}
                          </pre>
                        </details>
                      </div>
                    </article>
                  );
                })}
              </div>
            ) : (
              <div className="px-5 py-6 text-sm text-slate-400">
                {trace
                  ? "点击“展开全部阶段”查看完整链路。"
                  : "请选择一个已完成的 AI 变体。"}
              </div>
            )}
          </div>

          <div className="mt-5 grid gap-4 xl:grid-cols-[1fr_1.2fr]">
            <div className="rounded-2xl border border-slate-200 p-5">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-slate-900">记录本阶段调教</h3>
                  <p className="mt-1 text-xs text-slate-500">定位具体原文，分别说明优点和问题，形成可执行的矫正依据。</p>
                </div>
                <span className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-500">
                  {selectedStage ? selectedStage.label : "等待 Trace"}
                </span>
              </div>
              <div className="mt-4 space-y-3">
                <textarea
                  className="min-h-20 w-full rounded-xl border border-indigo-100 bg-indigo-50/40 p-3 text-sm outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="定位片段：可在右侧阶段输出中拖选原文，再点“引用选中输出”；也可手动填写字段路径"
                  value={targetExcerpt}
                  onChange={(event) => setTargetExcerpt(event.target.value)}
                  maxLength={4000}
                  disabled={!selectedStage}
                />
                <div className="grid gap-3 md:grid-cols-2">
                  <label className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-3">
                    <span className="flex items-center gap-2 text-xs font-bold text-emerald-700">
                      <ThumbsUp size={14} /> 好在哪里
                    </span>
                    <textarea
                      className="mt-2 min-h-24 w-full resize-y bg-transparent text-sm outline-none"
                      placeholder="例如：开场用了具体动作，角色辨识度很高"
                      value={positiveFeedback}
                      onChange={(event) => setPositiveFeedback(event.target.value)}
                      maxLength={1800}
                      disabled={!selectedStage}
                    />
                  </label>
                  <label className="rounded-xl border border-red-200 bg-red-50/50 p-3">
                    <span className="flex items-center gap-2 text-xs font-bold text-red-700">
                      <AlertTriangle size={14} /> 不合理在哪里
                    </span>
                    <textarea
                      className="mt-2 min-h-24 w-full resize-y bg-transparent text-sm outline-none"
                      placeholder="例如：情绪转折没有铺垫，结论与前文冲突"
                      value={issueFeedback}
                      onChange={(event) => setIssueFeedback(event.target.value)}
                      maxLength={1800}
                      disabled={!selectedStage}
                    />
                  </label>
                </div>
                <textarea
                  className="min-h-20 w-full rounded-xl border border-slate-200 p-3 text-sm outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="建议怎么矫正：例如要求转折前必须出现一个可观察的触发事件"
                  value={adjustment}
                  onChange={(event) => setAdjustment(event.target.value)}
                  maxLength={4000}
                  disabled={!selectedStage}
                />
                <textarea
                  className="min-h-16 w-full rounded-xl border border-slate-200 p-3 text-sm outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="预期效果与验证标准"
                  value={expectedEffect}
                  onChange={(event) => setExpectedEffect(event.target.value)}
                  maxLength={4000}
                  disabled={!selectedStage}
                />
                <div className="flex gap-3">
                  <select
                    className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                    value={tuningStatus}
                    onChange={(event) => setTuningStatus(event.target.value as TuningNote["status"])}
                    disabled={!selectedStage}
                  >
                    {Object.entries(tuningStatusLabel).map(([value, label]) => (
                      <option key={value} value={value}>{label}</option>
                    ))}
                  </select>
                  <Button
                    className="gap-2"
                    onClick={handleSaveTuning}
                    disabled={!selectedStage || (!positiveFeedback.trim() && !issueFeedback.trim()) || busy}
                  >
                    <Save size={15} /> 保存记录
                  </Button>
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 p-5">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-slate-900">阶段调教历史</h3>
                  <p className="mt-1 text-xs text-slate-500">当前运行、变体和阶段的历史记录。</p>
                </div>
                <span className="text-xs text-slate-400">{selectedTuningNotes.length} 条</span>
              </div>
              <div className="mt-4 max-h-[430px] space-y-3 overflow-y-auto">
                {selectedTuningNotes.map((note) => (
                  <article key={note.id} className="rounded-xl border border-slate-100 bg-slate-50 p-4">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="rounded-full bg-indigo-50 px-2.5 py-1 text-[11px] font-semibold text-indigo-700">
                        {tuningStatusLabel[note.status]}
                      </span>
                      <span className="text-[11px] text-slate-400">
                        {note.author} · {new Date(note.created_at).toLocaleString()}
                      </span>
                    </div>
                    {note.target_excerpt && (
                      <blockquote className="mt-3 rounded-lg border-l-4 border-indigo-300 bg-white px-3 py-2 text-xs leading-5 text-slate-600">
                        <Quote size={12} className="mb-1 text-indigo-400" />
                        {note.target_excerpt}
                      </blockquote>
                    )}
                    {note.positive_feedback && (
                      <div className="mt-3 rounded-lg bg-emerald-50 px-3 py-2 text-xs leading-5 text-emerald-800">
                        <b>好在哪里：</b>{note.positive_feedback}
                      </div>
                    )}
                    {note.issue_feedback && (
                      <div className="mt-2 rounded-lg bg-red-50 px-3 py-2 text-xs leading-5 text-red-800">
                        <b>不合理在哪里：</b>{note.issue_feedback}
                      </div>
                    )}
                    {!note.positive_feedback && !note.issue_feedback && (
                      <div className="mt-3 text-sm font-medium text-slate-800">{note.observation}</div>
                    )}
                    {note.adjustment && <div className="mt-2 text-xs leading-5 text-slate-600"><b>矫正：</b>{note.adjustment}</div>}
                    {note.expected_effect && <div className="mt-1 text-xs leading-5 text-slate-500"><b>预期：</b>{note.expected_effect}</div>}
                  </article>
                ))}
                {selectedTuningNotes.length === 0 && (
                  <div className="rounded-xl border border-dashed border-slate-200 py-12 text-center text-sm text-slate-400">
                    该阶段暂无调教记录
                  </div>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[1.5fr_1fr]">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-bold text-slate-900">定量匿名 A/B（定版时使用）</h2>
                <p className="mt-1 text-xs text-slate-500">这里不显示原文和来源，只用于无偏胜率；日常调教请使用上方三栏批注台。</p>
              </div>
              <div className="flex items-center gap-3">
                <label className="flex items-center gap-2 text-xs text-slate-500">
                  <input
                    type="checkbox"
                    checked={showEvalAudio}
                    onChange={(event) => setShowEvalAudio(event.target.checked)}
                  />
                  单独试听 TTS
                </label>
                {!pair.done && <span className="rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-700">{pair.fixture_id}</span>}
              </div>
            </div>
            {pair.done ? (
              <div className="mt-8 flex flex-col items-center rounded-2xl border border-dashed border-slate-200 py-12 text-center">
                <CheckCircle2 className="text-emerald-500" size={30} />
                <div className="mt-3 font-semibold text-slate-700">当前没有待评测内容</div>
                <div className="mt-1 text-sm text-slate-400">先在上方生成一个评测组。</div>
              </div>
            ) : (
              <>
                <div className="mt-5 grid gap-4 md:grid-cols-2">
                  {(["a", "b"] as const).map((side) => {
                    const variant = pair[side];
                    return (
                      <div key={side} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                        <div className="flex items-center justify-between">
                          <span className="text-lg font-black text-slate-800">{side.toUpperCase()}</span>
                          <span className="text-xs text-slate-400">来源已隐藏</span>
                        </div>
                        {showEvalAudio ? (
                          <audio className="mt-3 w-full" controls src={evalAudioUrl(variant.audio_url)} />
                        ) : (
                          <div className="mt-3 rounded-lg bg-white px-3 py-2 text-xs text-slate-400">
                            文本盲测模式：TTS 已隐藏，避免音色影响内容判断。
                          </div>
                        )}
                        <div className="mt-4 max-h-80 overflow-y-auto whitespace-pre-wrap text-sm leading-6 text-slate-700">{variant.text}</div>
                      </div>
                    );
                  })}
                </div>
                <div className="mt-5 grid grid-cols-3 gap-3">
                  <Button variant="outline" onClick={() => handleJudge("a")} disabled={busy}>A 更好</Button>
                  <Button variant="outline" onClick={() => handleJudge("tie")} disabled={busy}>难分</Button>
                  <Button variant="outline" onClick={() => handleJudge("b")} disabled={busy}>B 更好</Button>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-2">
              <BarChart3 className="text-indigo-600" size={18} />
              <h2 className="font-bold text-slate-900">胜率报告</h2>
            </div>
            <div className="mt-5 space-y-4">
              {report.map((row) => (
                <div key={`${row.variant_a}-${row.variant_b}`} className="rounded-xl border border-slate-100 p-4">
                  <div className="text-sm font-semibold text-slate-800">
                    {variantLabel[row.variant_a]} <span className="text-slate-300">vs</span> {variantLabel[row.variant_b]}
                  </div>
                  <div className="mt-3 flex items-end justify-between">
                    <span className="text-2xl font-black text-indigo-600">{Math.round(row.rate * 100)}%</span>
                    <span className="text-xs text-slate-400">
                      n={row.n} · tie={row.ties} · 95% CI {Math.round(row.low * 100)}–{Math.round(row.high * 100)}%
                    </span>
                  </div>
                  <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100">
                    <div className="h-full rounded-full bg-indigo-500" style={{ width: `${row.rate * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardContent className="p-6">
          <h2 className="font-bold text-slate-900">评测样本库</h2>
          <div className="mt-4 grid gap-3 lg:grid-cols-2">
            {fixtures.map((fixture) => (
              <div key={fixture.id} className="rounded-xl border border-slate-100 p-4">
                <div className="flex items-center justify-between gap-3">
                  <span className="font-semibold text-slate-800">{fixture.topic}</span>
                  <div className="flex items-center gap-2">
                    <span className={`rounded-full px-2 py-1 text-[10px] font-bold ${splitClass[fixture.split]}`}>
                      {fixture.split.toUpperCase()}
                    </span>
                    <span className="text-xs text-slate-400">{fixture.transcript_chars} 字</span>
                  </div>
                </div>
                <div className="mt-1 text-xs font-medium text-indigo-600">{fixture.character_name}</div>
                <p className="mt-2 text-sm leading-5 text-slate-500">{fixture.persona}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default QualityEvaluation;
