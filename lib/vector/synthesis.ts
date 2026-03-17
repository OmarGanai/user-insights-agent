import { SOURCE_DEFINITIONS } from "@/lib/vector/constants"
import type { Evidence, Hypothesis, PipelineStep, Recommendation, ReportSection } from "@/lib/mock-data"
import { isoNow } from "@/lib/vector/time"
import type {
  CompletionSignal,
  EvidenceResolution,
  RuntimeContextPayload,
  VectorSourceKey,
  VectorState,
} from "@/lib/vector/types"

const REQUIRED_KEYS: VectorSourceKey[] = ["amplitude", "typeform", "ios_release"]

function asPipelineStatus(status: string): PipelineStep["status"] {
  if (status === "synced") return "complete"
  if (status === "syncing") return "running"
  if (status === "error") return "error"
  return "pending"
}

function buildPeriodLabel(): string {
  const formatter = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric" })
  const end = new Date()
  const start = new Date(Date.now() - 6 * 24 * 60 * 60 * 1000)
  return `${formatter.format(start)} - ${formatter.format(end)}, ${end.getUTCFullYear()}`
}

function completionSignalFromState(state: VectorState): CompletionSignal {
  const availableCount = REQUIRED_KEYS.filter((key) => Boolean(state.snapshots[key])).length
  const errorCount = REQUIRED_KEYS.filter((key) => state.statusIndex[key].status === "error").length

  if (availableCount === 0) {
    return {
      status: "blocked",
      summary: "No required source snapshots are available; run ingest before synthesis.",
      completedAt: isoNow(),
    }
  }

  if (errorCount > 0 || availableCount < REQUIRED_KEYS.length) {
    return {
      status: "partial",
      summary: `Draft generated with partial source coverage (${availableCount}/${REQUIRED_KEYS.length} required sources synced).`,
      completedAt: isoNow(),
    }
  }

  return {
    status: "success",
    summary: "Draft generated with complete source coverage.",
    completedAt: isoNow(),
  }
}

function buildEvidence(
  evidenceId: string,
  sourceKey: VectorSourceKey,
  sourceName: string,
  snippet: string,
  confidence: Evidence["confidence"],
  runId: string | null,
  snapshotId: string | null,
  traceStepId: string
): {
  evidence: Evidence
  resolution: EvidenceResolution
} {
  const evidence: Evidence = {
    id: evidenceId,
    source: sourceName,
    snippet,
    confidence,
  }

  const resolution: EvidenceResolution = {
    evidenceId,
    sourceKey,
    sourceName,
    snippet,
    confidence,
    runId,
    snapshotId,
    traceStepId,
  }

  return { evidence, resolution }
}

export function synthesizeReportDraft(state: VectorState, runtimeContext: RuntimeContextPayload): {
  periodLabel: string
  sections: ReportSection[]
  hypotheses: Hypothesis[]
  recommendations: Recommendation[]
  evidenceMap: Record<string, EvidenceResolution>
  completion: CompletionSignal
  traceSteps: PipelineStep[]
} {
  const amplitude = state.snapshots.amplitude?.data as
    | { charts?: Array<{ name?: string; dataPoints?: number }> }
    | undefined
  const typeform = state.snapshots.typeform?.data as
    | { responseCount?: number; themes?: Array<{ label?: string; count?: number }> }
    | undefined
  const ios = state.snapshots.ios_release?.data as
    | { latestVersion?: string; latestReleaseDate?: string }
    | undefined

  const latestRun = state.runs[state.runs.length - 1]
  const runId = latestRun?.id ?? null

  const chartCount = amplitude?.charts?.length ?? 0
  const responseCount = typeform?.responseCount ?? 0
  const topTheme = typeform?.themes?.[0]
  const latestVersion = ios?.latestVersion ?? "unknown"

  const evidenceMap: Record<string, EvidenceResolution> = {}

  const metricsEvidence = buildEvidence(
    "ev-v3-metrics",
    "amplitude",
    "Amplitude",
    `Amplitude normalized ${chartCount} chart snapshots for this run.`,
    "high",
    runId,
    state.statusIndex.amplitude.snapshotId,
    "step-ingest-amplitude"
  )
  evidenceMap[metricsEvidence.evidence.id] = metricsEvidence.resolution

  const feedbackEvidence = buildEvidence(
    "ev-v3-feedback",
    "typeform",
    "Typeform",
    `Typeform returned ${responseCount} completed responses in the current window.`,
    "high",
    runId,
    state.statusIndex.typeform.snapshotId,
    "step-ingest-typeform"
  )
  evidenceMap[feedbackEvidence.evidence.id] = feedbackEvidence.resolution

  const releaseEvidence = buildEvidence(
    "ev-v3-release",
    "ios_release",
    "iOS Releases",
    `Latest merged release is ${latestVersion}${ios?.latestReleaseDate ? ` (${ios.latestReleaseDate})` : ""}.`,
    "medium",
    runId,
    state.statusIndex.ios_release.snapshotId,
    "step-ingest-ios_release"
  )
  evidenceMap[releaseEvidence.evidence.id] = releaseEvidence.resolution

  const hypotheses: Hypothesis[] = [
    {
      id: "hyp-v3-1",
      claim:
        "Onboarding clarity remains the fastest lever because quantitative and qualitative signals both point to early journey friction.",
      confidence: "high",
      supportingEvidence: [metricsEvidence.evidence, feedbackEvidence.evidence],
      dataSources: [
        {
          label: "Amplitude charts",
          detail: `${chartCount} normalized charts contributed to this draft.`,
          file: state.statusIndex.amplitude.snapshotId ?? undefined,
        },
        {
          label: "Typeform responses",
          detail: `${responseCount} completed responses were available during synthesis.`,
          file: state.statusIndex.typeform.snapshotId ?? undefined,
        },
      ],
    },
    {
      id: "hyp-v3-2",
      claim:
        "Retention-oriented roadmap decisions should prioritize feedback themes that repeat across quantitative trend shifts.",
      confidence: "medium",
      supportingEvidence: [feedbackEvidence.evidence],
      dataSources: [
        {
          label: "Top Typeform theme",
          detail: `${topTheme?.label ?? "No dominant theme detected"} (${topTheme?.count ?? 0} mentions).`,
          file: state.statusIndex.typeform.snapshotId ?? undefined,
        },
      ],
    },
    {
      id: "hyp-v3-3",
      claim:
        "Release messaging should connect stability gains to user-perceived value so improvements are visible beyond crash metrics.",
      confidence: "low",
      supportingEvidence: [releaseEvidence.evidence],
      dataSources: [
        {
          label: "iOS release metadata",
          detail: `Latest release captured as ${latestVersion}.`,
          file: state.statusIndex.ios_release.snapshotId ?? undefined,
        },
      ],
    },
  ]

  const recommendations: Recommendation[] = [
    {
      id: "rec-v3-1",
      rank: 1,
      title: "Run an onboarding message variant test in the highest-dropoff step",
      owner: "Product",
      nextStep: "Ship two message variants and track completion deltas over one week.",
      eta: "1 week",
      confidence: "high",
      evidence: [metricsEvidence.evidence, feedbackEvidence.evidence],
    },
    {
      id: "rec-v3-2",
      rank: 2,
      title: "Prioritize backlog items that map directly to the top feedback theme",
      owner: "Product + Eng",
      nextStep: "Create an experiment card tied to the highest-frequency Typeform theme.",
      eta: "2 weeks",
      confidence: "medium",
      evidence: [feedbackEvidence.evidence],
    },
    {
      id: "rec-v3-3",
      rank: 3,
      title: "Update release communication to explicitly call out user-facing impact",
      owner: "Marketing",
      nextStep: "Add value-focused copy to release notes and in-app update messaging.",
      eta: "Next release",
      confidence: "low",
      evidence: [releaseEvidence.evidence],
    },
  ]

  const sections: ReportSection[] = [
    {
      id: "sec-summary",
      title: "Executive Summary",
      content:
        `This draft was synthesized from live snapshots across ${chartCount} Amplitude charts, ${responseCount} Typeform responses, and iOS release metadata (${latestVersion}). ` +
        "Signals remain strongest around onboarding clarity and retention-focused prioritization.",
      evidence: [metricsEvidence.evidence, feedbackEvidence.evidence],
    },
    {
      id: "sec-metrics",
      title: "Key Metrics & Top Movers",
      content:
        `- Normalized chart count: ${chartCount}\n` +
        `- Completed survey responses: ${responseCount}\n` +
        `- Latest iOS version observed: ${latestVersion}`,
      evidence: [metricsEvidence.evidence, releaseEvidence.evidence],
    },
    {
      id: "sec-feedback",
      title: "User Feedback Themes",
      content:
        topTheme
          ? `${topTheme.label} appeared in ${topTheme.count ?? 0} responses and should drive near-term decision framing.`
          : "No dominant feedback theme detected in the current response window.",
      evidence: [feedbackEvidence.evidence],
    },
    {
      id: "sec-releases",
      title: "Release Impact",
      content:
        `Current release baseline is ${latestVersion}${ios?.latestReleaseDate ? ` (${ios.latestReleaseDate})` : ""}. ` +
        "Treat this as directional until enough post-release behavioral data accumulates.",
      evidence: [releaseEvidence.evidence],
    },
    {
      id: "sec-hypotheses",
      title: "Hypotheses",
      content: "",
      evidence: [],
    },
    {
      id: "sec-recommendations",
      title: "Recommendations",
      content: "",
      evidence: [],
    },
  ]

  const traceSteps: PipelineStep[] = [
    ...SOURCE_DEFINITIONS.map((source) => ({
      id: `step-ingest-${source.key}`,
      name: `Ingest: ${source.name}`,
      status: asPipelineStatus(state.statusIndex[source.key].status),
      detail: state.statusIndex[source.key].error
        ? `Error: ${state.statusIndex[source.key].error}`
        : state.snapshots[source.key]?.summary ?? "No snapshot available",
      outputFile: state.statusIndex[source.key].snapshotId ?? undefined,
      outputPreview: state.snapshots[source.key]?.summary,
    })),
    {
      id: "step-normalize",
      name: "Normalize snapshots",
      status: "complete",
      detail: "Source snapshots normalized into synthesis-ready context.",
      outputPreview: `${Object.keys(state.snapshots).length} source snapshots available.`,
    },
    {
      id: "step-synthesize",
      name: "Synthesize draft",
      status: "complete",
      detail: "Generated sections, hypotheses, recommendations, and evidence map.",
      outputPreview: `${sections.length} sections, ${hypotheses.length} hypotheses, ${recommendations.length} recommendations.`,
    },
  ]

  const completion = completionSignalFromState(state)

  traceSteps.push({
    id: "step-complete-task",
    name: "complete_task",
    status:
      completion.status === "blocked"
        ? "error"
        : completion.status === "partial"
          ? "running"
          : "complete",
    detail: `complete_task status=${completion.status}`,
    outputPreview: completion.summary,
  })

  return {
    periodLabel: buildPeriodLabel(),
    sections,
    hypotheses,
    recommendations,
    evidenceMap,
    completion,
    traceSteps,
  }
}
