#!/usr/bin/env node

const baseUrl = process.env.VECTOR_BASE_URL || "http://127.0.0.1:3000"

async function requestJson(path, options = {}) {
  const response = await fetch(`${baseUrl}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  })

  const body = await response.json().catch(() => ({}))
  return { response, body }
}

function stableJson(value) {
  return JSON.stringify(value)
}

async function run() {
  const preview = await requestJson("/api/report-artifact/preview", { method: "GET" })
  if (!preview.response.ok) {
    throw new Error(`Preview request failed (${preview.response.status})`)
  }

  const publish = await requestJson("/api/report-artifact/publish", {
    method: "POST",
    body: JSON.stringify({ dryRun: true }),
  })

  if (!publish.response.ok) {
    throw new Error(`Dry-run publish failed (${publish.response.status})`)
  }

  const previewPayload = preview.body?.payload
  const publishPayload = publish.body?.payload

  if (!previewPayload || !publishPayload) {
    throw new Error("Missing payload in preview or publish response")
  }

  const equivalent = stableJson(previewPayload) === stableJson(publishPayload)
  if (!equivalent) {
    throw new Error("Preview and publish payloads differ")
  }

  console.log("PASS: preview and publish payloads are equivalent")
}

run().catch((error) => {
  const message = error instanceof Error ? error.message : String(error)
  console.error(`FAIL: ${message}`)
  process.exitCode = 1
})
