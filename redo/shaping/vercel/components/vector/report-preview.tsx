"use client"

import { useState } from "react"
import { Hash, Send, CheckCircle2, Eye, EyeOff } from "lucide-react"
import { Button } from "@/components/ui/button"
import type { ReportSection, Hypothesis, Recommendation } from "@/lib/mock-data"

interface ReportPreviewProps {
  sections: ReportSection[]
  hypotheses: Hypothesis[]
  recommendations: Recommendation[]
  showingPreview?: boolean
  onShowPreview?: () => void
  onHidePreview?: () => void
  onPublish?: () => void
  publishingToSlack?: boolean
}

// Block Kit default attachment bar color (no custom color set)
const ATTACHMENT_BAR = "#e8e8e8"

function ConfidencePill({ level }: { level: string }) {
  const styles: Record<string, string> = {
    high: "bg-[#e8f5e9] text-[#2e7d32] border border-[#a5d6a7]",
    medium: "bg-[#fff8e1] text-[#f57f17] border border-[#ffe082]",
    low: "bg-[#fce4ec] text-[#c62828] border border-[#ef9a9a]",
  }
  const labels: Record<string, string> = { high: "High", medium: "Med", low: "Low" }
  return (
    <span className={`inline-flex shrink-0 items-center rounded px-2 py-1 text-xs font-semibold leading-none ${styles[level] ?? "bg-gray-100 text-gray-600"}`}>
      {labels[level] ?? level}
    </span>
  )
}

// A single Block Kit section attachment (left bar + content)
function SlackAttachment({
  title,
  children,
  color,
  isMetrics = false,
}: {
  title: string
  children: React.ReactNode
  color: string
  isMetrics?: boolean
}) {
  return (
    <div className="flex gap-0 mb-2">
      <div className="w-1 shrink-0 rounded-sm mr-4" style={{ backgroundColor: color }} />
      <div className="flex-1 min-w-0 py-1">
        <p className="text-base font-bold text-[#1d1c1d] leading-snug mb-2">{title}</p>
        <div className={`text-sm text-[#616061] leading-relaxed ${isMetrics ? "font-mono" : ""}`}>
          {children}
        </div>
      </div>
    </div>
  )
}

// Light-themed Slack UI matching the screenshot
function SlackMessage({
  sections,
  hypotheses,
  recommendations,
}: {
  sections: ReportSection[]
  hypotheses: Hypothesis[]
  recommendations: Recommendation[]
}) {
  const [hovered, setHovered] = useState(false)
  const visibleSections = sections.filter(
    (s) => s.id !== "sec-hypotheses" && s.id !== "sec-recommendations"
  )

  return (
    // Mac window chrome
    <div className="rounded-xl overflow-hidden shadow-lg border border-[#e0e0e0]" style={{ fontFamily: "-apple-system, 'Lato', sans-serif" }}>

      {/* Mac titlebar */}
      <div className="flex items-center gap-0 bg-[#3f0e40] px-4 py-3">
        {/* Traffic lights */}
        <div className="flex items-center gap-2 mr-5">
          <div className="h-3.5 w-3.5 rounded-full bg-[#ff5f57]" />
          <div className="h-3.5 w-3.5 rounded-full bg-[#febc2e]" />
          <div className="h-3.5 w-3.5 rounded-full bg-[#28c840]" />
        </div>
        {/* Channel pill */}
        <div className="flex items-center gap-2 rounded-md bg-white/20 px-3.5 py-1.5">
          <Hash className="h-4 w-4 text-white/80" />
          <span className="text-sm font-semibold text-white">product-updates</span>
        </div>
      </div>

      {/* Slack message area — white */}
      <div
        className={`bg-white px-5 py-4 transition-colors ${hovered ? "bg-[#f8f8f8]" : ""}`}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      >
        {/* Sender row */}
        <div className="flex items-start gap-4 mb-3">
          {/* App avatar - Slack purple rounded square */}
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-[#4a154b] text-white font-bold text-xl select-none">
            V
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-base font-bold text-[#1d1c1d] hover:underline cursor-pointer">
                Vector
              </span>
              <span className="rounded border border-[#d1d2d3] px-1.5 py-0.5 text-xs font-bold uppercase tracking-wide text-[#616061]">
                APP
              </span>
              <span className="text-sm text-[#616061]">Today at 10:42 AM</span>
            </div>

            {/* Brief title as plain message text above attachments */}
            <p className="mt-1.5 text-base font-bold text-[#1d1c1d] leading-snug">
              Weekly Product Brief —<br />Feb 24 – Mar 2
            </p>
          </div>
        </div>

        {/* Block Kit attachments - one per section */}
        <div className="space-y-px ml-1">
          {visibleSections.map((section) => (
            <SlackAttachment
              key={section.id}
              title={section.title}
              color={ATTACHMENT_BAR}
              isMetrics={section.id === "sec-metrics"}
            >
              <p className="whitespace-pre-line">
                {section.content.length > 260
                  ? section.content.slice(0, 260) + "…"
                  : section.content}
              </p>
              {section.evidence.filter(e => e.chartName).length > 0 && (
                <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1">
                  {section.evidence.filter(e => e.chartName).map((ev) => (
                    <span key={ev.id} className="text-sm text-[#1264a3] hover:underline cursor-pointer">
                      {ev.chartName}
                    </span>
                  ))}
                </div>
              )}
            </SlackAttachment>
          ))}

          {/* Hypotheses attachment */}
          <SlackAttachment
            title="Hypotheses"
            color={ATTACHMENT_BAR}
          >
            <div className="space-y-2">
              {hypotheses.map((h) => (
                <div key={h.id} className="flex items-start gap-2.5">
                  <ConfidencePill level={h.confidence} />
                  <span className="leading-relaxed">
                    {h.claim.length > 100 ? h.claim.slice(0, 100) + "…" : h.claim}
                  </span>
                </div>
              ))}
            </div>
          </SlackAttachment>

          {/* Recommendations attachment */}
          <SlackAttachment
            title="Recommendations"
            color={ATTACHMENT_BAR}
          >
            <div className="space-y-1.5">
              {recommendations.map((r, i) => (
                <div key={r.id} className="flex items-start gap-2">
                  <span className="shrink-0 text-[#1d1c1d] font-medium">{i + 1}.</span>
                  <span className="text-sm">
                    {r.title}
                    <span className="text-[#9e9ea6] ml-2 text-xs">{r.owner} · {r.eta}</span>
                  </span>
                </div>
              ))}
            </div>
          </SlackAttachment>
        </div>

        {/* Footer */}
        <p className="mt-3 ml-1 text-xs text-[#9e9ea6]">
          Generated by Vector · 3 sources · 7 snapshots
        </p>
      </div>
    </div>
  )
}

export function ReportPreview({
  sections,
  hypotheses,
  recommendations,
  showingPreview = false,
  onShowPreview,
  onHidePreview,
  onPublish,
  publishingToSlack = false,
}: ReportPreviewProps) {
  const [published, setPublished] = useState(false)

  const handlePublish = () => {
    onPublish?.()
    setTimeout(() => {
      setPublished(true)
      setTimeout(() => setPublished(false), 3000)
    }, 1200)
  }

  return (
    <div className="flex h-full flex-col">
      {/* Channel row */}
      <div className="flex items-center gap-2 border-b border-border px-4 py-3">
        <Hash className="h-5 w-5 text-muted-foreground" />
        <span className="text-sm text-foreground/80 font-medium flex-1">product-updates</span>
      </div>

      {/* Scrollable body */}
      <div className="flex-1 overflow-y-auto px-4 py-5 space-y-5">
        {/* Ready-to-publish status */}
        {!showingPreview && (
          <div className="rounded-md border border-border bg-background p-5 space-y-4">
            <div className="flex items-center gap-3">
              <div className="h-3 w-3 rounded-full bg-emerald-500" />
              <span className="text-sm font-medium text-foreground">Ready to publish</span>
            </div>
            <p className="text-sm text-muted-foreground leading-relaxed">
              The draft has been reviewed and is ready to post to{" "}
              <span className="font-medium text-foreground">#product-updates</span>.
              Review the Block Kit preview before sending.
            </p>
            <div className="flex items-center gap-3 pt-2">
              <Button
                size="sm"
                className="h-9 gap-2 px-4 text-sm"
                onClick={handlePublish}
                disabled={publishingToSlack || published}
              >
                {published ? (
                  <>
                    <CheckCircle2 className="h-4 w-4" />
                    Sent to Slack
                  </>
                ) : publishingToSlack ? (
                  "Sending…"
                ) : (
                  <>
                    <Send className="h-4 w-4" />
                    Publish to Slack
                  </>
                )}
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="h-9 gap-2 px-4 text-sm"
                onClick={onShowPreview}
              >
                <Eye className="h-4 w-4" />
                Preview
              </Button>
            </div>
          </div>
        )}

        {/* Block Kit preview */}
        {showingPreview && (
          <>
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Block Kit Preview
              </span>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 gap-1.5 px-2 text-xs text-muted-foreground hover:text-foreground"
                onClick={onHidePreview}
              >
                <EyeOff className="h-4 w-4" />
                Hide
              </Button>
            </div>
            <SlackMessage
              sections={sections}
              hypotheses={hypotheses}
              recommendations={recommendations}
            />
            {/* Publish button below preview */}
            <Button
              size="sm"
              className="w-full h-10 gap-2 text-sm"
              onClick={handlePublish}
              disabled={publishingToSlack || published}
            >
              {published ? (
                <>
                  <CheckCircle2 className="h-4 w-4" />
                  Sent to Slack
                </>
              ) : publishingToSlack ? (
                "Sending…"
              ) : (
                <>
                  <Send className="h-4 w-4" />
                  Publish to Slack
                </>
              )}
            </Button>
          </>
        )}
      </div>
    </div>
  )
}
