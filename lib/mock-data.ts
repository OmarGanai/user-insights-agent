export type SourceStatus = "synced" | "stale" | "error" | "syncing"
export type SourceType = "amplitude" | "typeform" | "ios_release" | "product_context" | "company_context"

export interface AmplitudeChart {
  id: string
  name: string
  chartType: "funnel" | "segmentation" | "retention" | "lifecycle"
  lastUpdated: string
  url: string
}

export interface Source {
  id: string
  name: string
  type: SourceType
  status: SourceStatus
  lastSync: string
  recordCount: number
  error?: string
  notice?: string
  // Amplitude-specific
  charts?: AmplitudeChart[]
  // Typeform-specific
  responseCount?: number
  // iOS-specific
  latestRelease?: string
  latestReleaseDate?: string
}

export interface ReportSection {
  id: string
  title: string
  content: string
  evidence: Evidence[]
}

export interface Evidence {
  id: string
  source: string
  sourceName?: string
  snippet: string
  confidence: "high" | "medium" | "low"
  chartRef?: string // ID of the Amplitude chart referenced
  chartName?: string
}

export interface DataSource {
  label: string
  detail: string
  file?: string
}

export interface Recommendation {
  id: string
  rank: number
  title: string
  owner: string
  nextStep: string
  eta: string
  evidence: Evidence[]
  confidence: "high" | "medium" | "low"
}

export interface Hypothesis {
  id: string
  claim: string
  confidence: "high" | "medium" | "low"
  supportingEvidence: Evidence[]
  dataSources: DataSource[] // what data was used to form this
}

export interface PipelineStep {
  id: string
  name: string
  status: "complete" | "running" | "pending" | "error"
  duration?: string
  detail?: string
  outputFile?: string // link to the source markdown/snapshot file
  outputPreview?: string // first few lines of the output
}

export const AMPLITUDE_CHARTS: AmplitudeChart[] = [
  {
    id: "chart-onboarding-funnel",
    name: "Onboarding Funnel (7d)",
    chartType: "funnel",
    lastUpdated: "2 min ago",
    url: "https://analytics.amplitude.com/demo/chart/onboarding-funnel",
  },
  {
    id: "chart-dau-trend",
    name: "DAU Trend",
    chartType: "segmentation",
    lastUpdated: "2 min ago",
    url: "https://analytics.amplitude.com/demo/chart/dau-trend",
  },
  {
    id: "chart-retention",
    name: "7-Day Retention Curve",
    chartType: "retention",
    lastUpdated: "2 min ago",
    url: "https://analytics.amplitude.com/demo/chart/7d-retention",
  },
  {
    id: "chart-power-user-lifecycle",
    name: "Power User Lifecycle",
    chartType: "lifecycle",
    lastUpdated: "2 min ago",
    url: "https://analytics.amplitude.com/demo/chart/power-user-lifecycle",
  },
  {
    id: "chart-crash-free",
    name: "Crash-Free Sessions",
    chartType: "segmentation",
    lastUpdated: "15 min ago",
    url: "https://analytics.amplitude.com/demo/chart/crash-free",
  },
]

export const MOCK_SOURCES: Source[] = [
  {
    id: "src-amplitude",
    name: "Amplitude",
    type: "amplitude",
    status: "synced",
    lastSync: "2 min ago",
    recordCount: 1247,
    charts: AMPLITUDE_CHARTS,
  },
  {
    id: "src-typeform",
    name: "Typeform",
    type: "typeform",
    status: "synced",
    lastSync: "3 hours ago",
    recordCount: 89,
    responseCount: 89,
  },
  {
    id: "src-ios",
    name: "iOS Releases",
    type: "ios_release",
    status: "synced",
    lastSync: "15 min ago",
    recordCount: 3,
    latestRelease: "v3.1.0",
    latestReleaseDate: "Feb 27, 2026",
  },
  {
    id: "src-product-context",
    name: "Product Context",
    type: "product_context",
    status: "synced",
    lastSync: "1 day ago",
    recordCount: 1,
    error: undefined,
  },
  {
    id: "src-company-context",
    name: "Company Context",
    type: "company_context",
    status: "synced",
    lastSync: "1 day ago",
    recordCount: 1,
    error: undefined,
  },
]

export const MOCK_HYPOTHESES: Hypothesis[] = [
  {
    id: "hyp-1",
    claim: "Onboarding drop-off at step 3 is driven by unclear value proposition messaging, not technical friction.",
    confidence: "high",
    dataSources: [
      {
        label: "Onboarding Funnel (7d)",
        detail: "Step 3 completion rate dropped 18% after copy change in v2.4.1. Avg time-on-step: 12s to 34s.",
        file: "snapshots/amplitude/onboarding-funnel.md",
      },
      {
        label: "Typeform responses",
        detail: "12 of 89 respondents mentioned confusion at signup about value proposition.",
        file: "snapshots/typeform/responses.md",
      },
    ],
    supportingEvidence: [
      {
        id: "ev-1a",
        source: "Amplitude",
        chartRef: "chart-onboarding-funnel",
        chartName: "Onboarding Funnel (7d)",
        snippet: "Step 3 completion rate dropped 18% after copy change in v2.4.1. Avg time-on-step increased from 12s to 34s.",
        confidence: "high",
      },
      {
        id: "ev-1b",
        source: "Typeform",
        snippet: "\"I didn't understand what the app would do for me\" - 12 of 89 respondents mentioned confusion at signup.",
        confidence: "high",
      },
    ],
  },
  {
    id: "hyp-2",
    claim: "Power users are churning due to missing bulk-action capabilities in the dashboard.",
    confidence: "medium",
    dataSources: [
      {
        label: "Power User Lifecycle",
        detail: "Users with >100 items show 2.3x higher churn rate. Session duration declining WoW.",
        file: "snapshots/amplitude/power-user-lifecycle.md",
      },
      {
        label: "Typeform responses",
        detail: "7 respondents explicitly requested bulk actions for managing items.",
        file: "snapshots/typeform/responses.md",
      },
    ],
    supportingEvidence: [
      {
        id: "ev-2a",
        source: "Typeform",
        snippet: "\"I need to update 50+ items at once, clicking through each one is painful\" - recurring theme in 7 responses.",
        confidence: "medium",
      },
      {
        id: "ev-2b",
        source: "Amplitude",
        chartRef: "chart-power-user-lifecycle",
        chartName: "Power User Lifecycle",
        snippet: "Users with >100 items show 2.3x higher churn rate vs. average. Session duration declining week-over-week.",
        confidence: "medium",
      },
    ],
  },
  {
    id: "hyp-3",
    claim: "The v3.1.0 release improved crash-free rate but user sentiment around performance has not improved.",
    confidence: "low",
    dataSources: [
      {
        label: "Crash-Free Sessions",
        detail: "Crash-free rate moved from 98.2% to 99.1% post-v3.1.0.",
        file: "snapshots/amplitude/crash-free.md",
      },
      {
        label: "iOS release notes",
        detail: "v3.1.0 (build 4521) shipped Feb 27 - stability release. Release impact applied (>2 weeks ago).",
        file: "snapshots/ios/release-notes.md",
      },
      {
        label: "Typeform responses",
        detail: "4 respondents report app feels slow post-update. Small sample, may not be representative.",
        file: "snapshots/typeform/responses.md",
      },
    ],
    supportingEvidence: [
      {
        id: "ev-3a",
        source: "iOS Releases",
        snippet: "v3.1.0 release notes cite \"stability improvements\". Crash-free rate moved from 98.2% to 99.1%.",
        confidence: "high",
      },
      {
        id: "ev-3b",
        source: "Amplitude",
        chartRef: "chart-crash-free",
        chartName: "Crash-Free Sessions",
        snippet: "Crash-free sessions improved from 98.2% to 99.1% since Feb 27 release.",
        confidence: "high",
      },
      {
        id: "ev-3c",
        source: "Typeform",
        snippet: "\"App still feels slow\" mentioned by 4 respondents post-v3.1.0. Sample is small and may not be representative.",
        confidence: "low",
      },
    ],
  },
]

export const MOCK_RECOMMENDATIONS: Recommendation[] = [
  {
    id: "rec-1",
    rank: 1,
    title: "Rewrite onboarding step 3 with outcome-first messaging",
    owner: "Sarah (Product)",
    nextStep: "Draft new copy variants and set up A/B test",
    eta: "Mar 10",
    confidence: "high",
    evidence: [
      {
        id: "ev-r1a",
        source: "Amplitude",
        chartRef: "chart-onboarding-funnel",
        chartName: "Onboarding Funnel (7d)",
        snippet: "Step 3 completion rate dropped 18% after copy change in v2.4.1.",
        confidence: "high",
      },
      {
        id: "ev-r1b",
        source: "Typeform",
        snippet: "12 of 89 respondents mentioned confusion at signup about value proposition.",
        confidence: "high",
      },
    ],
  },
  {
    id: "rec-2",
    rank: 2,
    title: "Ship bulk-action MVP for power users",
    owner: "Marcus (Eng)",
    nextStep: "Scope multi-select + batch update API endpoint",
    eta: "Mar 17",
    confidence: "medium",
    evidence: [
      {
        id: "ev-r2a",
        source: "Typeform",
        snippet: "7 respondents explicitly requested bulk actions for managing items.",
        confidence: "medium",
      },
    ],
  },
  {
    id: "rec-3",
    rank: 3,
    title: "Investigate perceived performance issues post-v3.1.0",
    owner: "Dev (Eng)",
    nextStep: "Add client-side performance instrumentation to identify bottleneck",
    eta: "Mar 14",
    confidence: "low",
    evidence: [
      {
        id: "ev-r3a",
        source: "Typeform",
        snippet: "4 respondents report app feeling slow, but crash rate improved. Needs deeper investigation.",
        confidence: "low",
      },
    ],
  },
]

export const MOCK_REPORT_SECTIONS: ReportSection[] = [
  {
    id: "sec-summary",
    title: "Executive Summary",
    content: "This week's signals show a clear pattern: onboarding friction is the highest-leverage problem to solve. Amplitude data confirms an 18% drop in step-3 completion since v2.4.1, corroborated by qualitative feedback from Typeform. Power-user churn is an emerging risk worth addressing in the next sprint. The v3.1.0 release improved stability metrics but user perception of performance lags behind.",
    evidence: [],
  },
  {
    id: "sec-metrics",
    title: "Key Metrics & Top Movers",
    content: "- DAU: 12,400 (down 3% WoW)\n- Onboarding completion: 54% (down 18% since v2.4.1)\n- 7-day retention: 38% (flat)\n- Crash-free rate: 99.1% (up from 98.2%)\n- NPS: 32 (down 4 points)",
    evidence: [
      {
        id: "ev-m1",
        source: "Amplitude",
        chartRef: "chart-dau-trend",
        chartName: "DAU Trend",
        snippet: "DAU trend pulled from weekly dashboard snapshot.",
        confidence: "high",
      },
      {
        id: "ev-m2",
        source: "Amplitude",
        chartRef: "chart-onboarding-funnel",
        chartName: "Onboarding Funnel (7d)",
        snippet: "Onboarding completion from funnel chart, period Feb 24 - Mar 2.",
        confidence: "high",
      },
      {
        id: "ev-m3",
        source: "Amplitude",
        chartRef: "chart-retention",
        chartName: "7-Day Retention Curve",
        snippet: "Retention data from cohort analysis.",
        confidence: "high",
      },
      {
        id: "ev-m4",
        source: "Amplitude",
        chartRef: "chart-crash-free",
        chartName: "Crash-Free Sessions",
        snippet: "Crash-free metric from sessions chart.",
        confidence: "high",
      },
    ],
  },
  {
    id: "sec-feedback",
    title: "User Feedback Themes",
    content: "Three dominant themes emerged from 89 completed Typeform responses this week:\n\n1. Onboarding confusion (14 mentions) - Users don't understand the value proposition at step 3\n2. Bulk action requests (7 mentions) - Power users need multi-select capabilities\n3. Performance perception (4 mentions) - Despite improved crash rates, some users feel the app is slow",
    evidence: [
      {
        id: "ev-f1",
        source: "Typeform",
        snippet: "89 completed responses analyzed. Response_type=completed filter applied, date range Feb 24-Mar 2.",
        confidence: "high",
      },
    ],
  },
  {
    id: "sec-releases",
    title: "Release Impact",
    content: "v3.1.0 shipped on Feb 27 with stability improvements. Crash-free sessions improved from 98.2% to 99.1%. However, no measurable impact on retention or engagement metrics yet. Release notes positioned this as a maintenance release, which may have dampened user perception of progress.\n\nNote: Release impact analysis only considers charts with data from at least 2 weeks post-release to allow for meaningful adoption measurement.",
    evidence: [
      {
        id: "ev-rel1",
        source: "iOS Releases",
        snippet: "v3.1.0 (build 4521) live on App Store since Feb 27. Lookup API confirms current version.",
        confidence: "high",
      },
      {
        id: "ev-rel2",
        source: "Amplitude",
        chartRef: "chart-crash-free",
        chartName: "Crash-Free Sessions",
        snippet: "Crash-free metric improvement measured over 2+ weeks post-release window.",
        confidence: "high",
      },
    ],
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

export const MOCK_PIPELINE_STEPS: PipelineStep[] = [
  {
    id: "step-1",
    name: "Ingest: Amplitude",
    status: "complete",
    duration: "1.2s",
    detail: "Fetched 5 charts via Dashboard REST API. 1,247 data points across all charts.",
    outputFile: "snapshots/amplitude/",
    outputPreview: "Charts: onboarding-funnel.md, dau-trend.md, 7d-retention.md, power-user-lifecycle.md, crash-free.md",
  },
  {
    id: "step-2",
    name: "Ingest: Typeform",
    status: "complete",
    duration: "2.8s",
    detail: "Fetched 89 responses (response_type=completed). Paginated with since/until.",
    outputFile: "snapshots/typeform/responses.md",
    outputPreview: "89 responses, 3 dominant themes extracted. Top: onboarding confusion (14), bulk actions (7), perf (4).",
  },
  {
    id: "step-3",
    name: "Ingest: iOS Release",
    status: "complete",
    duration: "0.4s",
    detail: "Apple Lookup API returned v3.1.0 metadata. Merged with curated release-notes.md.",
    outputFile: "snapshots/ios/release-notes.md",
    outputPreview: "v3.1.0 (build 4521), Feb 27. \"Stability improvements and bug fixes.\"",
  },
  {
    id: "step-4",
    name: "Normalize snapshots",
    status: "complete",
    duration: "0.3s",
    detail: "All sources normalized to run-scoped snapshot format.",
    outputFile: "snapshots/normalized/",
    outputPreview: "3 sources -> 7 snapshot files. Total context: 14.2 KB.",
  },
  {
    id: "step-5",
    name: "Load product context",
    status: "complete",
    duration: "0.1s",
    detail: "product-context.md loaded (2.1 KB). Contains product goals, user segments, and vocabulary.",
    outputFile: "config/product-context.md",
    outputPreview: "Goals: improve activation, reduce churn. Segments: new users, power users.",
  },
  {
    id: "step-6",
    name: "Synthesize draft",
    status: "complete",
    duration: "4.7s",
    detail: "Gemini 3 Flash generated 6-section decision brief with 3 hypotheses and 3 ranked recommendations.",
    outputFile: "runs/2026-03-02/draft.md",
    outputPreview: "6 sections, 3 hypotheses (1 high, 1 med, 1 low), 3 recommendations.",
  },
  {
    id: "step-7",
    name: "Render Block Kit",
    status: "complete",
    duration: "0.2s",
    detail: "Converted report artifact to Slack Block Kit payload. 18 blocks total (under 50-block limit).",
    outputFile: "runs/2026-03-02/blockkit.json",
    outputPreview: "18 blocks: 1 header, 4 sections, 3 hypotheses, 3 recs, dividers.",
  },
]

export const MOCK_PROMPT_SNAPSHOT = `System: You are Vector, a product intelligence synthesis agent.

Context injected:
- Source inventory: [amplitude (5 charts, 1247 data points), typeform (89 responses), ios_release (v3.1.0)]
- Product context: config/product-context.md (goals, segments, vocabulary)
- Snapshot files:
  - snapshots/amplitude/onboarding-funnel.md
  - snapshots/amplitude/dau-trend.md
  - snapshots/amplitude/7d-retention.md
  - snapshots/amplitude/power-user-lifecycle.md
  - snapshots/amplitude/crash-free.md
  - snapshots/typeform/responses.md
  - snapshots/ios/release-notes.md
- Capability map: fetch_amplitude, fetch_typeform, read_release_notes_file, fetch_itunes_lookup_metadata, write_report_draft, update_report_section, render_blockkit_preview, post_slack_message
- Release impact policy: Only consider charts with data >= 2 weeks post-release
- Recent run state: Last run 2026-03-01T10:00:00Z, status=published

Task: Generate a 6-section decision brief from normalized source snapshots.
Sections: Executive Summary, Key Metrics & Top Movers, User Feedback Themes, Release Impact, Hypotheses, Recommendations.
Each hypothesis must include confidence level and cite specific data sources used.
Each recommendation must include owner, next step, and ETA.
Link every claim to evidence snippets from source data.`
