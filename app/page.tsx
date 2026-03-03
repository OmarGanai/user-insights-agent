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
  MOCK_SOURCES,
  MOCK_PIPELINE_STEPS,
  MOCK_PROMPT_SNAPSHOT,
  type Source,
} from "@/lib/mock-data"
import type { ReportArtifact, SlackPayload } from "@/lib/vector/types"

export default function Home() {
  const [debuggerOpen, setDebuggerOpen] = useState(false)
  const [sourcesOpen, setSourcesOpen] = useState(true)
  const [previewOpen, setPreviewOpen] = useState(true)
  const [showingSlackPreview, setShowingSlackPreview] = useState(false)
  const [publishingToSlack, setPublishingToSlack] = useState(false)
  const [sources, setSources] = useState<Source[]>(MOCK_SOURCES)
  const [reportArtifact, setReportArtifact] = useState<ReportArtifact | null>(null)
  const [previewPayload, setPreviewPayload] = useState<SlackPayload | null>(null)
  const [publishError, setPublishError] = useState<string | null>(null)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [isLoadingArtifact, setIsLoadingArtifact] = useState(true)

  const sections = reportArtifact?.sections ?? []
  const hypotheses = reportArtifact?.hypotheses ?? []
  const recommendations = reportArtifact?.recommendations ?? []

  const loadArtifact = useCallback(async () => {
    const response = await fetch("/api/report-artifact", { cache: "no-store" })
    if (!response.ok) throw new Error("Failed to load artifact")
    const data = (await response.json()) as { artifact: ReportArtifact }
    setReportArtifact(data.artifact)
  }, [])

  const loadPreviewPayload = useCallback(async () => {
    const response = await fetch("/api/report-artifact/preview", { cache: "no-store" })
    if (!response.ok) throw new Error("Failed to load preview payload")
    const data = (await response.json()) as {
      payload: SlackPayload
      publishMetadata: ReportArtifact["publishMetadata"]
    }
    setPreviewPayload(data.payload)
    setReportArtifact((current) =>
      current
        ? {
            ...current,
            publishMetadata: data.publishMetadata ?? current.publishMetadata,
          }
        : current
    )
  }, [])

  useEffect(() => {
    let active = true
    ;(async () => {
      try {
        await Promise.all([loadArtifact(), loadPreviewPayload()])
      } catch (_error) {
        // Leave UI with best-effort local defaults if API bootstrap fails.
      } finally {
        if (active) setIsLoadingArtifact(false)
      }
    })()

    return () => {
      active = false
    }
  }, [loadArtifact, loadPreviewPayload])

  const handlePublish = useCallback(async () => {
    setPublishError(null)
    setPublishingToSlack(true)
    try {
      const response = await fetch("/api/report-artifact/publish", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dryRun: false }),
      })
      const data = (await response.json()) as {
        payload?: SlackPayload
        publishMetadata?: ReportArtifact["publishMetadata"]
      }

      if (data.payload) {
        setPreviewPayload(data.payload)
      }

      if (data.publishMetadata) {
        setReportArtifact((current) =>
          current
            ? {
                ...current,
                publishMetadata: data.publishMetadata ?? null,
              }
            : current
        )
      }

      if (!response.ok) {
        setPublishError(
          data.publishMetadata?.error || "Slack publish failed. Check webhook config."
        )
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Slack publish failed."
      setPublishError(message)
    } finally {
      setPublishingToSlack(false)
    }
  }, [])

  const handleRefreshSource = useCallback((id: string) => {
    setSources((prev) =>
      prev.map((s) =>
        s.id === id ? { ...s, status: "syncing" as const } : s
      )
    )
    setTimeout(() => {
      setSources((prev) =>
        prev.map((s) =>
          s.id === id
            ? { ...s, status: "synced" as const, lastSync: "Just now", error: undefined }
            : s
        )
      )
    }, 1500)
  }, [])

  const handleRefreshDraft = useCallback(async () => {
    setIsRefreshing(true)
    try {
      await Promise.all([loadArtifact(), loadPreviewPayload()])
    } finally {
      setIsRefreshing(false)
    }
  }, [loadArtifact, loadPreviewPayload])

  const handleSectionUpdate = useCallback(
    (id: string, content: string) => {
      if (!reportArtifact) return

      setReportArtifact((current) => {
        if (!current) return current
        return {
          ...current,
          sections: current.sections.map((section) =>
            section.id === id ? { ...section, content } : section
          ),
        }
      })

      void (async () => {
        try {
          const response = await fetch(`/api/report-artifact/sections/${id}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ content }),
          })
          if (!response.ok) {
            throw new Error("Failed to persist section update")
          }
          const data = (await response.json()) as { artifact: ReportArtifact }
          setReportArtifact(data.artifact)
          await loadPreviewPayload()
        } catch (_error) {
          await Promise.all([loadArtifact(), loadPreviewPayload()])
        }
      })()
    },
    [reportArtifact, loadArtifact, loadPreviewPayload]
  )

  const handleEvidenceClick = useCallback((_evidenceId: string) => {
    setDebuggerOpen(true)
  }, [])

  // Helper: get icon for source type
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

  // Helper: get tooltip text for source
  function getSourceLabel(source: Source) {
    if (source.type === "amplitude") return `${source.name} (${source.charts?.length ?? 0} charts)`
    if (source.type === "typeform") return `${source.name} (${source.responseCount ?? 0} responses)`
    if (source.type === "ios_release") return `${source.name} (${source.latestRelease})`
    return source.name
  }

  return (
    <div className="flex h-screen flex-col overflow-hidden font-sans bg-background">
      {/* Minimal header */}
      <header className="flex h-11 shrink-0 items-center border-b border-border px-4">
        <span className="text-sm font-semibold tracking-tight text-foreground">
          Vector
        </span>
        <span className="ml-2.5 text-[11px] text-muted-foreground font-mono">W48</span>
      </header>

      {/* 3-column body */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: Sources */}
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
              <SourcesPanel
                sources={sources}
                onRefreshSource={handleRefreshSource}
                publishMetadata={reportArtifact?.publishMetadata ?? null}
              />
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

        {/* Center: Draft Workbench */}
        <div className="flex-1 overflow-hidden">
          <DraftWorkbench
            sections={sections}
            hypotheses={hypotheses}
            recommendations={recommendations}
            onSectionUpdate={handleSectionUpdate}
            onEvidenceClick={handleEvidenceClick}
            onRefreshDraft={handleRefreshDraft}
            isRefreshing={isRefreshing}
            isLoading={isLoadingArtifact}
            publishMetadata={reportArtifact?.publishMetadata ?? null}
            periodLabel={reportArtifact?.periodLabel ?? "Feb 24 - Mar 2, 2026"}
          />
        </div>

        {/* Right: Block Kit Preview */}
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
                payload={previewPayload}
                showingPreview={showingSlackPreview}
                onShowPreview={() => {
                  setShowingSlackPreview(true)
                  void loadPreviewPayload()
                }}
                onHidePreview={() => setShowingSlackPreview(false)}
                onPublish={handlePublish}
                publishingToSlack={publishingToSlack}
                publishMetadata={reportArtifact?.publishMetadata ?? null}
                publishError={publishError}
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

      {/* Debug toggle bar - anchored to bottom */}
      <div className="flex h-8 shrink-0 items-center border-t border-border px-3">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setDebuggerOpen(!debuggerOpen)}
          className={`h-6 gap-1.5 px-2 text-[11px] font-mono ${
            debuggerOpen
              ? "bg-accent text-foreground"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <Terminal className="h-3 w-3" />
          Debug
        </Button>
      </div>

      {/* Debugger Drawer */}
      <DebuggerDrawer
        open={debuggerOpen}
        onClose={() => setDebuggerOpen(false)}
        pipelineSteps={MOCK_PIPELINE_STEPS}
        promptSnapshot={MOCK_PROMPT_SNAPSHOT}
      />
    </div>
  )
}
