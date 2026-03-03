"use client"

import { useState } from "react"
import { RefreshCw, ChevronRight, BarChart3, FileText, Smartphone, BookOpen, Building2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import type { Source, SourceType } from "@/lib/mock-data"
import type { PublishMetadata } from "@/lib/vector/types"

interface SourcesPanelProps {
  sources: Source[]
  onRefreshSource: (id: string) => void
  publishMetadata?: PublishMetadata | null
}

function StatusDot({ status }: { status: Source["status"] }) {
  const color =
    status === "synced"
      ? "bg-emerald-500"
      : status === "syncing"
        ? "bg-amber-400 animate-pulse"
        : status === "stale"
          ? "bg-amber-400"
          : "bg-red-400"
  return <span className={`inline-block h-2 w-2 rounded-full ${color}`} />
}

function SourceIcon({ type }: { type: SourceType }) {
  const cls = "h-5 w-5 text-muted-foreground"
  if (type === "amplitude") return <BarChart3 className={cls} />
  if (type === "typeform") return <FileText className={cls} />
  if (type === "ios_release") return <Smartphone className={cls} />
  if (type === "product_context") return <BookOpen className={cls} />
  if (type === "company_context") return <Building2 className={cls} />
  return <FileText className={cls} />
}

function SourceStat({ source }: { source: Source }) {
  if (source.type === "amplitude" && source.charts) {
    return (
      <span className="text-sm text-muted-foreground">
        {source.charts.length} charts
      </span>
    )
  }
  if (source.type === "typeform") {
    return (
      <span className="text-sm text-muted-foreground">
        {source.responseCount ?? source.recordCount} responses
      </span>
    )
  }
  if (source.type === "ios_release" && source.latestReleaseDate) {
    return (
      <span className="text-sm text-muted-foreground">
        {source.latestRelease} &middot; {source.latestReleaseDate}
      </span>
    )
  }
  if (source.type === "product_context") {
    return (
      <span className="text-sm text-muted-foreground">
        UX flows &amp; surfaces
      </span>
    )
  }
  if (source.type === "company_context") {
    return (
      <span className="text-sm text-muted-foreground">
        Goals &amp; strategy
      </span>
    )
  }
  return null
}

export function SourcesPanel({
  sources,
  onRefreshSource,
  publishMetadata = null,
}: SourcesPanelProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const publishLabel = publishMetadata
    ? publishMetadata.status === "success"
      ? `Published to ${publishMetadata.destinationLabel}`
      : `Publish failed (${publishMetadata.destinationLabel})`
    : "Not published yet"
  const publishTimestamp = publishMetadata
    ? new Date(publishMetadata.attemptedAt).toLocaleString()
    : null

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto px-1.5 py-2">
        <div className="mb-2 rounded-md border border-border bg-background px-3 py-2.5">
          <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
            Slack Delivery
          </p>
          <p
            className={`mt-1 text-sm ${
              publishMetadata?.status === "failed" ? "text-red-500" : "text-foreground/85"
            }`}
          >
            {publishLabel}
          </p>
          {publishTimestamp && (
            <p className="mt-0.5 text-xs text-muted-foreground">{publishTimestamp}</p>
          )}
        </div>
        {sources.map((source) => {
          const isExpanded = expandedId === source.id
          const hasExpandable = source.type === "amplitude" && source.charts && source.charts.length > 0
          const isStaticDoc = source.type === "product_context" || source.type === "company_context"

          return (
            <div key={source.id}>
            <div
              className="group flex items-center justify-between rounded-md px-3 py-3 hover:bg-accent/50 transition-colors cursor-pointer"
              onClick={() => {
                if (hasExpandable) {
                  setExpandedId(isExpanded ? null : source.id)
                }
              }}
            >
              <div className="flex items-center gap-3 min-w-0 flex-1">
                {hasExpandable && (
                  <ChevronRight
                    className={`h-4 w-4 text-muted-foreground shrink-0 transition-transform ${isExpanded ? "rotate-90" : ""}`}
                  />
                )}
                {!hasExpandable && <span className="w-4 shrink-0" />}
                <SourceIcon type={source.type} />
                <StatusDot status={source.status} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-base text-foreground truncate">
                      {source.name}
                    </span>
                  </div>
                  <SourceStat source={source} />
                </div>
              </div>
              {!isStaticDoc && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-foreground shrink-0"
                  onClick={(e) => {
                    e.stopPropagation()
                    onRefreshSource(source.id)
                  }}
                  disabled={source.status === "syncing"}
                >
                  <RefreshCw
                    className={`h-4 w-4 ${source.status === "syncing" ? "animate-spin" : ""}`}
                  />
                  <span className="sr-only">Refresh {source.name}</span>
                </Button>
              )}
            </div>

              {/* Expanded chart list for Amplitude */}
              {isExpanded && source.charts && (
                <div className="ml-[42px] mr-3 mb-1 space-y-1">
                  {source.charts.map((chart) => (
                    <div
                      key={chart.id}
                      className="flex items-center gap-3 rounded px-3 py-2 text-sm hover:bg-accent/30 transition-colors"
                    >
                      <span className="inline-block h-1.5 w-1.5 rounded-full bg-muted-foreground/50 shrink-0" />
                      <span className="text-foreground/80 truncate flex-1">
                        {chart.name}
                      </span>
                      <span className="text-xs font-mono text-muted-foreground shrink-0">
                        {chart.chartType}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {/* Stale warning */}
              {source.error && (
                <div className="ml-[42px] mr-3 mb-1 px-3">
                  <span className="text-xs text-amber-500">
                    {source.error}
                  </span>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
