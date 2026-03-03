"use client"

import { useState } from "react"
import { X, Check, Loader2, AlertTriangle, FileText, ChevronDown, ChevronRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import type { PipelineStep } from "@/lib/mock-data"
import type { EvidenceResolution } from "@/lib/vector/types"

interface DebuggerDrawerProps {
  open: boolean
  onClose: () => void
  pipelineSteps: PipelineStep[]
  promptSnapshot: string
  evidenceDetail?: EvidenceResolution | null
  evidenceLoading?: boolean
}

function StepIcon({ status }: { status: PipelineStep["status"] }) {
  if (status === "complete")
    return <Check className="h-3 w-3 text-emerald-500 dark:text-emerald-400" />
  if (status === "running")
    return <Loader2 className="h-3 w-3 text-amber-500 dark:text-amber-400 animate-spin" />
  if (status === "error")
    return <AlertTriangle className="h-3 w-3 text-red-500 dark:text-red-400" />
  return <span className="inline-block h-3 w-3 rounded-full border border-border" />
}

function PipelineStepRow({ step }: { step: PipelineStep }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div>
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-3 rounded px-2 py-1.5 font-mono text-xs hover:bg-accent/30 transition-colors"
      >
        <StepIcon status={step.status} />
        {expanded ? (
          <ChevronDown className="h-2.5 w-2.5 text-muted-foreground shrink-0" />
        ) : (
          <ChevronRight className="h-2.5 w-2.5 text-muted-foreground shrink-0" />
        )}
        <span className="text-foreground/90 flex-1 text-left">{step.name}</span>
        {step.duration && (
          <span className="text-muted-foreground shrink-0">{step.duration}</span>
        )}
      </button>
      {expanded && (
        <div className="ml-[38px] mr-2 mb-1 rounded border border-border bg-background p-2 text-[11px] space-y-1.5">
          {step.detail && (
            <p className="text-foreground/80 leading-relaxed">{step.detail}</p>
          )}
          {step.outputFile && (
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <FileText className="h-3 w-3 shrink-0" />
              <span className="font-mono text-[10px]">{step.outputFile}</span>
            </div>
          )}
          {step.outputPreview && (
            <div className="rounded bg-accent/50 px-2 py-1.5 font-mono text-[10px] text-foreground/70 leading-relaxed">
              {step.outputPreview}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export function DebuggerDrawer({
  open,
  onClose,
  pipelineSteps,
  promptSnapshot,
  evidenceDetail,
  evidenceLoading = false,
}: DebuggerDrawerProps) {
  const [tab, setTab] = useState<"pipeline" | "prompt" | "evidence">("pipeline")

  if (!open) return null

  return (
    <div className="shrink-0 border-t border-border bg-card">
      {/* Header */}
      <div className="flex h-8 items-center justify-between px-4 border-b border-border">
        <div className="flex items-center gap-3">
          <span className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
            Debugger
          </span>
          <div className="flex items-center gap-0.5">
            <button
              onClick={() => setTab("pipeline")}
              className={`rounded px-2 py-0.5 text-[11px] font-medium transition-colors ${
                tab === "pipeline"
                  ? "bg-accent text-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Pipeline
            </button>
            <button
              onClick={() => setTab("evidence")}
              className={`rounded px-2 py-0.5 text-[11px] font-medium transition-colors ${
                tab === "evidence"
                  ? "bg-accent text-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Evidence
            </button>
            <button
              onClick={() => setTab("prompt")}
              className={`rounded px-2 py-0.5 text-[11px] font-medium transition-colors ${
                tab === "prompt"
                  ? "bg-accent text-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Prompt
            </button>
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="h-5 w-5 p-0 text-muted-foreground hover:text-foreground"
          onClick={onClose}
        >
          <X className="h-3 w-3" />
          <span className="sr-only">Close debugger</span>
        </Button>
      </div>

      {/* Content */}
      <div className="h-52 overflow-y-auto p-4">
        {tab === "pipeline" ? (
          <div className="space-y-0.5">
            {pipelineSteps.map((step) => (
              <PipelineStepRow key={step.id} step={step} />
            ))}
          </div>
        ) : tab === "evidence" ? (
          evidenceLoading ? (
            <div className="flex items-center gap-2 text-xs text-muted-foreground font-mono">
              <Loader2 className="h-3 w-3 animate-spin" />
              Loading evidence...
            </div>
          ) : evidenceDetail ? (
            <div className="space-y-2 text-xs font-mono text-foreground/80">
              <p className="text-foreground font-semibold">{evidenceDetail.sourceName}</p>
              <p className="leading-relaxed">{evidenceDetail.snippet}</p>
              <p className="text-muted-foreground">
                confidence={evidenceDetail.confidence} run={evidenceDetail.runId ?? "none"}
              </p>
              <p className="text-muted-foreground">
                snapshot={evidenceDetail.snapshotId ?? "none"} step={evidenceDetail.traceStepId ?? "none"}
              </p>
            </div>
          ) : (
            <p className="text-xs text-muted-foreground font-mono">
              Click an evidence chip in the draft to inspect provenance.
            </p>
          )
        ) : (
          <pre className="whitespace-pre-wrap text-xs font-mono text-foreground/80 leading-relaxed">
            {promptSnapshot}
          </pre>
        )}
      </div>
    </div>
  )
}
