"use client"

import { AlertTriangle, CheckCircle2, Eye, EyeOff, Hash, Send } from "lucide-react"
import { Button } from "@/components/ui/button"
import type { PublishMetadata, SlackBlock, SlackPayload } from "@/lib/vector/types"

interface ReportPreviewProps {
  payload: SlackPayload | null
  showingPreview?: boolean
  onShowPreview?: () => void
  onHidePreview?: () => void
  onPublish?: () => void
  publishingToSlack?: boolean
  publishMetadata?: PublishMetadata | null
  publishError?: string | null
}

function cleanMrkdwn(text: string): string {
  return text
    .replace(/\*(.*?)\*/g, "$1")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/<([^|>]+)\|([^>]+)>/g, "$2 ($1)")
}

function renderBlock(block: SlackBlock, index: number) {
  if (block.type === "divider") {
    return <div key={`divider-${index}`} className="h-px bg-[#e0e0e0]" />
  }

  if (block.type === "header") {
    return (
      <h3 key={`header-${index}`} className="text-base font-bold text-[#1d1c1d]">
        {cleanMrkdwn(block.text.text)}
      </h3>
    )
  }

  if (block.type === "context") {
    return (
      <p key={`context-${index}`} className="text-xs text-[#616061]">
        {block.elements.map((element) => cleanMrkdwn(element.text)).join(" • ")}
      </p>
    )
  }

  return (
    <p
      key={`section-${index}`}
      className="whitespace-pre-line text-sm leading-relaxed text-[#1d1c1d]"
    >
      {cleanMrkdwn(block.text.text)}
    </p>
  )
}

function SlackPayloadMessage({ payload }: { payload: SlackPayload }) {
  return (
    <div
      className="overflow-hidden rounded-xl border border-[#e0e0e0] shadow-lg"
      style={{ fontFamily: "-apple-system, 'Lato', sans-serif" }}
    >
      <div className="flex items-center gap-2 bg-[#3f0e40] px-4 py-3 text-sm font-semibold text-white">
        <Hash className="h-4 w-4 text-white/80" />
        product-updates
      </div>
      <div className="space-y-3 bg-white px-5 py-4">{payload.blocks.map(renderBlock)}</div>
    </div>
  )
}

function publishSummary(metadata: PublishMetadata | null): string | null {
  if (!metadata) return null
  const when = new Date(metadata.attemptedAt).toLocaleString()

  if (metadata.status === "success") {
    return `Sent to ${metadata.destinationLabel} at ${when}`
  }

  return `Failed to publish at ${when}`
}

export function ReportPreview({
  payload,
  showingPreview = false,
  onShowPreview,
  onHidePreview,
  onPublish,
  publishingToSlack = false,
  publishMetadata = null,
  publishError = null,
}: ReportPreviewProps) {
  const currentChannel = publishMetadata?.destinationLabel || "#product-updates"
  const lastPublishSummary = publishSummary(publishMetadata)
  const hasPublishFailure = publishMetadata?.status === "failed"

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 border-b border-border px-4 py-3">
        <Hash className="h-5 w-5 text-muted-foreground" />
        <span className="flex-1 text-sm font-medium text-foreground/80">{currentChannel}</span>
      </div>

      <div className="flex-1 space-y-5 overflow-y-auto px-4 py-5">
        {!showingPreview && (
          <div className="space-y-4 rounded-md border border-border bg-background p-5">
            <div className="flex items-center gap-3">
              {hasPublishFailure ? (
                <AlertTriangle className="h-4 w-4 text-red-500" />
              ) : (
                <div className="h-3 w-3 rounded-full bg-emerald-500" />
              )}
              <span className="text-sm font-medium text-foreground">
                {hasPublishFailure ? "Publish failed" : "Ready to publish"}
              </span>
            </div>

            <p className="text-sm leading-relaxed text-muted-foreground">
              Preview uses the canonical Block Kit serializer, and publish sends the same payload to
              Slack.
            </p>

            {lastPublishSummary && (
              <p
                className={`text-xs ${
                  hasPublishFailure ? "text-red-500" : "text-muted-foreground"
                }`}
              >
                {lastPublishSummary}
              </p>
            )}
            {(publishMetadata?.error || publishError) && (
              <p className="text-xs text-red-500">{publishError || publishMetadata?.error}</p>
            )}

            <div className="flex items-center gap-3 pt-2">
              <Button
                size="sm"
                className="h-9 gap-2 px-4 text-sm"
                onClick={onPublish}
                disabled={publishingToSlack}
              >
                {publishingToSlack ? (
                  "Sending..."
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
                Preview payload
              </Button>
            </div>
          </div>
        )}

        {showingPreview && (
          <>
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Block Kit Preview (Canonical)
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

            {payload ? (
              <>
                <SlackPayloadMessage payload={payload} />
                <div className="rounded-md border border-border bg-card p-3">
                  <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                    Payload JSON
                  </p>
                  <pre className="mt-2 overflow-x-auto whitespace-pre-wrap break-all font-mono text-[11px] text-foreground/80">
                    {JSON.stringify(payload, null, 2)}
                  </pre>
                </div>
              </>
            ) : (
              <div className="rounded-md border border-border bg-background p-4 text-sm text-muted-foreground">
                Loading preview payload...
              </div>
            )}

            <Button
              size="sm"
              className="h-10 w-full gap-2 text-sm"
              onClick={onPublish}
              disabled={publishingToSlack}
            >
              {publishingToSlack ? (
                "Sending..."
              ) : publishMetadata?.status === "success" ? (
                <>
                  <CheckCircle2 className="h-4 w-4" />
                  Publish again
                </>
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
