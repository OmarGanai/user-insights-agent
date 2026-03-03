"use client"

import { useState, useRef, useEffect } from "react"
import { Pencil, Check, X, RefreshCw, ChevronDown, ChevronRight, BarChart3, FileText } from "lucide-react"
import { Button } from "@/components/ui/button"
import type { ReportSection, Hypothesis, Recommendation, Evidence } from "@/lib/mock-data"

interface DraftWorkbenchProps {
  sections: ReportSection[]
  hypotheses: Hypothesis[]
  recommendations: Recommendation[]
  onSectionUpdate: (id: string, content: string) => void
  onEvidenceClick: (evidenceId: string) => void
  onRefreshDraft: () => void
  isRefreshing: boolean
}

function ConfidenceBadge({ level }: { level: Hypothesis["confidence"] }) {
  const styles = {
    high: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400",
    medium: "bg-amber-500/15 text-amber-700 dark:text-amber-400",
    low: "bg-red-500/15 text-red-700 dark:text-red-400",
  }
  return (
    <span
      className={`inline-flex items-center rounded px-2.5 py-1 text-xs font-medium uppercase tracking-wider shrink-0 ${styles[level]}`}
    >
      {level}
    </span>
  )
}

function ChartRefChip({ chartName, onClick }: { chartName: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="inline-flex items-center gap-1.5 rounded bg-accent px-2.5 py-1 text-xs font-mono text-muted-foreground hover:text-foreground hover:bg-accent/80 transition-colors cursor-pointer"
    >
      <BarChart3 className="h-4 w-4" />
      {chartName}
    </button>
  )
}

function EvidenceChip({ ev, onClick }: { ev: Evidence; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="inline-flex items-center gap-1.5 rounded bg-accent px-2.5 py-1 text-xs font-mono text-muted-foreground hover:text-foreground hover:bg-accent/80 transition-colors cursor-pointer"
    >
      {ev.source === "Amplitude" ? (
        <BarChart3 className="h-4 w-4" />
      ) : (
        <FileText className="h-4 w-4" />
      )}
      {ev.chartName || ev.source}
    </button>
  )
}

function EditableSection({
  section,
  onUpdate,
  onEvidenceClick,
}: {
  section: ReportSection
  onUpdate: (content: string) => void
  onEvidenceClick: (id: string) => void
}) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(section.content)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (editing && textareaRef.current) {
      textareaRef.current.focus()
      textareaRef.current.style.height = "auto"
      textareaRef.current.style.height = textareaRef.current.scrollHeight + "px"
    }
  }, [editing])

  const handleSave = () => {
    onUpdate(draft)
    setEditing(false)
  }

  const handleCancel = () => {
    setDraft(section.content)
    setEditing(false)
  }

  // Split content into lines for rendering, preserving line breaks
  const contentLines = section.content.split("\n")

  return (
    <div className="group relative">
      {editing ? (
        <div className="space-y-2">
          <textarea
            ref={textareaRef}
            value={draft}
            onChange={(e) => {
              setDraft(e.target.value)
              e.target.style.height = "auto"
              e.target.style.height = e.target.scrollHeight + "px"
            }}
            className="w-full resize-none rounded-md border border-border bg-input p-4 text-base text-foreground leading-relaxed focus:outline-none focus:ring-1 focus:ring-ring font-sans"
          />
          <div className="flex items-center gap-2">
            <Button size="sm" className="h-8 px-3 text-sm" onClick={handleSave}>
              <Check className="mr-1.5 h-4 w-4" />
              Save
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="h-8 px-3 text-sm text-muted-foreground"
              onClick={handleCancel}
            >
              <X className="mr-1.5 h-4 w-4" />
              Cancel
            </Button>
          </div>
        </div>
      ) : (
        <div className="relative">
          <div className="text-base text-foreground/90 leading-relaxed pr-8 whitespace-pre-line">
            {contentLines.map((line, i) => (
              <span key={i}>
                {line}
                {i < contentLines.length - 1 && "\n"}
              </span>
            ))}
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="absolute -right-1 -top-1 h-8 w-8 p-0 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-foreground"
            onClick={() => setEditing(true)}
          >
            <Pencil className="h-4 w-4" />
            <span className="sr-only">Edit {section.title}</span>
          </Button>
          {/* Chart/evidence references */}
          {section.evidence && section.evidence.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {section.evidence.map((ev) => (
                <EvidenceChip
                  key={ev.id}
                  ev={ev}
                  onClick={() => onEvidenceClick(ev.id)}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function DataProvenanceBlock({ hypothesis, onEvidenceClick }: { hypothesis: Hypothesis; onEvidenceClick: (id: string) => void }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="mt-3">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        <span className="font-medium uppercase tracking-wider">Data used</span>
        <span className="font-mono">({hypothesis.dataSources.length} sources)</span>
      </button>
      {expanded && (
        <div className="mt-2 ml-4 space-y-2 border-l border-border pl-4">
          {hypothesis.dataSources.map((ds, i) => (
            <div key={i} className="text-sm">
              <div className="flex items-center gap-2">
                <span className="font-medium text-foreground/80">{ds.label}</span>
                {ds.file && (
                  <span className="font-mono text-xs text-muted-foreground">
                    {ds.file}
                  </span>
                )}
              </div>
              <p className="text-muted-foreground leading-relaxed mt-1">{ds.detail}</p>
            </div>
          ))}
          {hypothesis.supportingEvidence.length > 0 && (
            <div className="flex flex-wrap gap-1.5 pt-1">
              {hypothesis.supportingEvidence.map((ev) => (
                <EvidenceChip
                  key={ev.id}
                  ev={ev}
                  onClick={() => onEvidenceClick(ev.id)}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export function DraftWorkbench({
  sections,
  hypotheses,
  recommendations,
  onSectionUpdate,
  onEvidenceClick,
  onRefreshDraft,
  isRefreshing,
}: DraftWorkbenchProps) {
  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl px-10 py-10">
        {/* Title bar */}
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3">
              <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Draft Workbench
              </span>
            </div>
            <h1 className="mt-2 text-2xl font-semibold text-foreground text-balance">
              Weekly Product Brief
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Feb 24 - Mar 2, 2026
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="h-9 gap-2 px-3 text-sm text-muted-foreground hover:text-foreground"
            onClick={onRefreshDraft}
            disabled={isRefreshing}
          >
            <RefreshCw className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`} />
            {isRefreshing ? "Regenerating..." : "Refresh draft"}
          </Button>
        </div>

        {/* Sections */}
        <div className="mt-10 space-y-10">
          {sections
            .filter((s) => s.id !== "sec-hypotheses" && s.id !== "sec-recommendations")
            .map((section) => (
              <div key={section.id}>
                <h2 className="text-xs font-medium uppercase tracking-wider text-muted-foreground mb-4">
                  {section.title}
                </h2>
                <EditableSection
                  section={section}
                  onUpdate={(content) => onSectionUpdate(section.id, content)}
                  onEvidenceClick={onEvidenceClick}
                />
              </div>
            ))}

          {/* Hypotheses */}
          <div>
            <h2 className="text-xs font-medium uppercase tracking-wider text-muted-foreground mb-4">
              Hypotheses
            </h2>
            <div className="space-y-5">
              {hypotheses.map((h) => (
                <div key={h.id} className="rounded-md border border-border p-4">
                  <div className="flex items-start justify-between gap-4">
                    <p className="text-base text-foreground/90 leading-relaxed flex-1">
                      {h.claim}
                    </p>
                    <ConfidenceBadge level={h.confidence} />
                  </div>
                  <DataProvenanceBlock hypothesis={h} onEvidenceClick={onEvidenceClick} />
                </div>
              ))}
            </div>
          </div>

          {/* Recommendations */}
          <div>
            <h2 className="text-xs font-medium uppercase tracking-wider text-muted-foreground mb-4">
              Recommendations
            </h2>
            <div className="space-y-3">
              {recommendations.map((r, i) => (
                <div key={r.id} className="flex items-start gap-4">
                  <span className="mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded bg-accent text-xs font-mono text-muted-foreground">
                    {i + 1}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-base text-foreground/90">{r.title}</p>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {r.owner} &middot; {r.eta}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
