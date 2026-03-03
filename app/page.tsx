"use client"

import { useState, useCallback, useEffect } from "react"
import {
  PanelLeftClose,
  PanelLeftOpen,
  PanelRightClose,
  PanelRightOpen,
  Terminal,
  BarChart3,
  FileText,
  Smartphone,
  BookOpen,
  Building2,
  Eye,
  Send,
} from "lucide-react"
import { SourcesPanel } from "@/components/vector/sources-panel"
import { DraftWorkbench } from "@/components/vector/draft-workbench"
import { ReportPreview } from "@/components/vector/report-preview"
import { DebuggerDrawer } from "@/components/vector/debugger-drawer"
import { Button } from "@/components/ui/button"
import {
  MOCK_HYPOTHESES,
  MOCK_PIPELINE_STEPS,
  MOCK_PROMPT_SNAPSHOT,
  MOCK_RECOMMENDATIONS,
  MOCK_REPORT_SECTIONS,
  MOCK_SOURCES,
  type Source,
} from "@/lib/mock-data"
import type {
  EvidenceResolution,
  PipelineTrace,
  ReportArtifact,
  SourceStatusResponse,
} from "@/lib/vector/types"

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.text()
    throw new Error(body || `Request failed (${response.status})`)
  }

  return (await response.json()) as T
}

export default function Home() {
  const [debuggerOpen, setDebuggerOpen] = useState(false)
  const [sourcesOpen, setSourcesOpen] = useState(true)
  const [previewOpen, setPreviewOpen] = useState(true)
  const [showingSlackPreview, setShowingSlackPreview] = useState(false)
  const [publishingToSlack, setPublishingToSlack] = useState(false)
  const [sources, setSources] = useState<Source[]>(MOCK_SOURCES)
  const [reportArtifact, setReportArtifact] = useState<ReportArtifact | null>(null)
  const [trace, setTrace] = useState<PipelineTrace | null>(null)
  const [evidenceDetail, setEvidenceDetail] = useState<EvidenceResolution | null>(null)
  const [evidenceLoading, setEvidenceLoading] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [isBootstrapping, setIsBootstrapping] = useState(true)

  const sections = reportArtifact?.sections ?? MOCK_REPORT_SECTIONS
  const hypotheses = reportArtifact?.hypotheses ?? MOCK_HYPOTHESES
  const recommendations = reportArtifact?.recommendations ?? MOCK_RECOMMENDATIONS
  const pipelineSteps = trace?.steps ?? MOCK_PIPELINE_STEPS
  const promptSnapshot = trace?.promptSnapshot ?? MOCK_PROMPT_SNAPSHOT

  const loadSources = useCallback(async () => {
    const response = await fetch("/api/sources", { cache: "no-store" })
    const data = await parseJson<SourceStatusResponse>(response)
    setSources(data.sourceInventory)
  }, [])

  const loadArtifact = useCallback(async () => {
    const response = await fetch("/api/report-artifact", { cache: "no-store" })
    const data = await parseJson<{ artifact: ReportArtifact }>(response)
    setReportArtifact(data.artifact)
  }, [])

  const loadTrace = useCallback(async () => {
    const response = await fetch("/api/report-artifact/trace", { cache: "no-store" })
    const data = await parseJson<{ trace: PipelineTrace | null }>(response)
    setTrace(data.trace)
  }, [])

  useEffect(() => {
    let active = true

    ;(async () => {
      try {
        await Promise.all([loadSources(), loadArtifact(), loadTrace()])
      } catch {
        // Keep mock-backed fallback if live bootstrap fails.
      } finally {
        if (active) {
          setIsBootstrapping(false)
        }
      }
    })()

    return () => {
      active = false
    }
  }, [loadArtifact, loadSources, loadTrace])

  const handlePublish = useCallback(async () => {
    setPublishingToSlack(true)
    setTimeout(() => {
      setPublishingToSlack(false)
    }, 1200)
  }, [])

  const handleRefreshSource = useCallback(
    async (id: string) => {
      setSources((previous) =>
        previous.map((source) => (source.id === id ? { ...source, status: "syncing" } : source))
      )

      try {
        const response = await fetch("/api/sources/refresh", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ sourceId: id }),
        })
        const data = await parseJson<{ sourceInventory: Source[] }>(response)
        setSources(data.sourceInventory)
      } catch {
        await loadSources()
      }
    },
    [loadSources]
  )

  const handleRefreshDraft = useCallback(async () => {
    setIsRefreshing(true)
    try {
      const response = await fetch("/api/report-artifact/generate", {
        method: "POST",
        cache: "no-store",
      })
      const data = await parseJson<{ artifact: ReportArtifact; trace: PipelineTrace }>(response)
      setReportArtifact(data.artifact)
      setTrace(data.trace)
      await loadSources()
    } finally {
      setIsRefreshing(false)
    }
  }, [loadSources])

  const handleSectionUpdate = useCallback(async (id: string, content: string) => {
    setReportArtifact((current) => {
      if (!current) return current
      return {
        ...current,
        sections: current.sections.map((section) =>
          section.id === id ? { ...section, content } : section
        ),
      }
    })

    try {
      const response = await fetch(`/api/report-artifact/sections/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
      })
      const data = await parseJson<{ artifact: ReportArtifact }>(response)
      setReportArtifact(data.artifact)
    } catch {
      await loadArtifact()
    }
  }, [loadArtifact])

  const handleEvidenceClick = useCallback(async (evidenceId: string) => {
    setDebuggerOpen(true)
    setEvidenceLoading(true)

    try {
      const response = await fetch(`/api/report-artifact/evidence/${evidenceId}`, {
        cache: "no-store",
      })
      const data = await parseJson<{ evidence: EvidenceResolution }>(response)
      setEvidenceDetail(data.evidence)
    } catch {
      setEvidenceDetail(null)
    } finally {
      setEvidenceLoading(false)
    }
  }, [])

  function getSourceIcon(type: string) {
    switch (type) {
      case "amplitude":
        return <BarChart3 className="h-5 w-5" />
      case "typeform":
        return <FileText className="h-5 w-5" />
      case "ios_release":
        return <Smartphone className="h-5 w-5" />
      case "product_context":
        return <BookOpen className="h-5 w-5" />
      case "company_context":
        return <Building2 className="h-5 w-5" />
      default:
        return <FileText className="h-5 w-5" />
    }
  }

  function getSourceLabel(source: Source) {
    if (source.type === "amplitude") return `${source.name} (${source.charts?.length ?? 0} charts)`
    if (source.type === "typeform") return `${source.name} (${source.responseCount ?? 0} responses)`
    if (source.type === "ios_release") return `${source.name} (${source.latestRelease ?? "n/a"})`
    return source.name
  }

  const sourceFreshness = sources.map((source) => ({
    id: source.id,
    name: source.name,
    lastSync: source.lastSync,
    status: source.status,
  }))

  return (
    <div className="flex h-screen flex-col overflow-hidden font-sans bg-background">
      <header className="flex h-11 shrink-0 items-center border-b border-border px-4">
        <span className="text-sm font-semibold tracking-tight text-foreground">Vector</span>
        <span className="ml-2.5 text-[11px] text-muted-foreground font-mono">W48</span>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {sourcesOpen ? (
          <div className="flex w-64 shrink-0 flex-col border-r border-border">
            <div className="flex h-9 shrink-0 items-center justify-between px-3">
              <span className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                Sources
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSourcesOpen(false)}
                className="h-6 p-0 text-muted-foreground hover:text-foreground"
              >
                <PanelLeftClose className="h-3.5 w-3.5" />
                <span className="sr-only">Close sources</span>
              </Button>
            </div>
            <div className="flex-1 overflow-hidden">
              <SourcesPanel sources={sources} onRefreshSource={handleRefreshSource} />
            </div>
          </div>
        ) : (
          <div className="flex shrink-0 flex-col border-r border-border bg-secondary/30 pt-2 px-1 gap-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSourcesOpen(true)}
              className="h-10 w-10 p-0 text-muted-foreground hover:text-foreground hover:bg-accent/50 transition-colors"
              title="Open sources panel"
            >
              <PanelLeftOpen className="h-5 w-5" />
              <span className="sr-only">Open sources</span>
            </Button>
            <div className="h-px bg-border my-1" />
            {sources.map((source) => (
              <Button
                key={source.id}
                variant="ghost"
                size="sm"
                onClick={() => setSourcesOpen(true)}
                className="h-10 w-10 p-0 text-muted-foreground hover:text-foreground hover:bg-accent/50 transition-colors"
                title={getSourceLabel(source)}
              >
                {getSourceIcon(source.type)}
                <span className="sr-only">{getSourceLabel(source)}</span>
              </Button>
            ))}
          </div>
        )}

        <div className="flex-1 overflow-hidden">
          <DraftWorkbench
            sections={sections}
            hypotheses={hypotheses}
            recommendations={recommendations}
            sourceFreshness={sourceFreshness}
            onSectionUpdate={handleSectionUpdate}
            onEvidenceClick={handleEvidenceClick}
            onRefreshDraft={handleRefreshDraft}
            isRefreshing={isRefreshing || isBootstrapping}
          />
        </div>

        {previewOpen ? (
          <div className="flex w-[420px] shrink-0 flex-col border-l border-border">
            <div className="flex h-9 shrink-0 items-center justify-between px-3">
              <span className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                Publish
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setPreviewOpen(false)}
                className="h-6 p-0 text-muted-foreground hover:text-foreground"
              >
                <PanelRightClose className="h-3.5 w-3.5" />
                <span className="sr-only">Close publish</span>
              </Button>
            </div>
            <div className="flex-1 overflow-hidden">
              <ReportPreview
                sections={sections}
                hypotheses={hypotheses}
                recommendations={recommendations}
                showingPreview={showingSlackPreview}
                onShowPreview={() => setShowingSlackPreview(true)}
                onHidePreview={() => setShowingSlackPreview(false)}
                onPublish={handlePublish}
                publishingToSlack={publishingToSlack}
              />
            </div>
          </div>
        ) : (
          <div className="flex shrink-0 flex-col border-l border-border bg-secondary/30 pt-2 px-1 gap-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setPreviewOpen(true)}
              className="h-10 w-10 p-0 text-muted-foreground hover:text-foreground hover:bg-accent/50 transition-colors"
              title="Open publish panel"
            >
              <PanelRightOpen className="h-5 w-5" />
              <span className="sr-only">Open publish</span>
            </Button>
            <div className="h-px bg-border my-1" />
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setPreviewOpen(true)
                setShowingSlackPreview(true)
              }}
              className="h-10 w-10 p-0 text-muted-foreground hover:text-foreground hover:bg-accent/50 transition-colors"
              title="Show Slack preview"
            >
              <Eye className="h-5 w-5" />
              <span className="sr-only">Preview</span>
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={handlePublish}
              disabled={publishingToSlack}
              className="h-10 w-10 p-0 text-muted-foreground hover:text-foreground hover:bg-accent/50 transition-colors disabled:opacity-50"
              title="Publish to Slack"
            >
              <Send className="h-5 w-5" />
              <span className="sr-only">Publish</span>
            </Button>
          </div>
        )}
      </div>

      <div className="flex h-8 shrink-0 items-center justify-between border-t border-border px-3">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setDebuggerOpen(!debuggerOpen)}
          className={`h-6 gap-1.5 px-2 text-[11px] font-mono ${
            debuggerOpen ? "bg-accent text-foreground" : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <Terminal className="h-3 w-3" />
          Debug
        </Button>
        <span className="text-[11px] font-mono text-muted-foreground">
          completion: {reportArtifact?.runMetadata.completion.status ?? "pending"}
        </span>
      </div>

      <DebuggerDrawer
        open={debuggerOpen}
        onClose={() => setDebuggerOpen(false)}
        pipelineSteps={pipelineSteps}
        promptSnapshot={promptSnapshot}
        evidenceDetail={evidenceDetail}
        evidenceLoading={evidenceLoading}
      />
    </div>
  )
}
