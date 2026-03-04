import type { PublishMetadata, PublishMode, SlackPayload } from "@/lib/vector/types"

export interface PublishSlackOptions {
  payload: SlackPayload
  destinationLabel: string
  dryRun?: boolean
}

function buildFailureMetadata(
  destinationLabel: string,
  mode: PublishMode,
  message: string,
  httpStatus?: number
): PublishMetadata {
  return {
    attemptedAt: new Date().toISOString(),
    destinationLabel,
    status: "failed",
    mode,
    error: message,
    httpStatus,
  }
}

export async function postSlackMessage({
  payload,
  destinationLabel,
  dryRun = false,
}: PublishSlackOptions): Promise<PublishMetadata> {
  if (dryRun) {
    return {
      attemptedAt: new Date().toISOString(),
      destinationLabel,
      status: "success",
      mode: "dry_run",
    }
  }

  const webhookUrl = process.env.SLACK_WEBHOOK_URL

  if (!webhookUrl) {
    return buildFailureMetadata(
      destinationLabel,
      "webhook",
      "Missing SLACK_WEBHOOK_URL. Add it to your .env file."
    )
  }

  const abortController = new AbortController()
  const timeout = setTimeout(() => abortController.abort(), 10000)

  try {
    const response = await fetch(webhookUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: abortController.signal,
      cache: "no-store",
    })

    if (!response.ok) {
      const body = await response.text()
      return buildFailureMetadata(
        destinationLabel,
        "webhook",
        `Slack webhook rejected payload: ${body || "unknown error"}`,
        response.status
      )
    }

    return {
      attemptedAt: new Date().toISOString(),
      destinationLabel,
      status: "success",
      mode: "webhook",
      httpStatus: response.status,
    }
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      return buildFailureMetadata(
        destinationLabel,
        "webhook",
        "Slack publish timed out after 10 seconds."
      )
    }

    const message = error instanceof Error ? error.message : "Unknown publish error"
    return buildFailureMetadata(destinationLabel, "webhook", `Slack publish failed: ${message}`)
  } finally {
    clearTimeout(timeout)
  }
}
