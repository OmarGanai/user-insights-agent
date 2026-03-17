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

function fail(message) {
  throw new Error(message)
}

function amplitudeStatusFromSources(payload) {
  const status = payload?.statusIndex?.amplitude
  if (!status || typeof status !== "object") {
    fail("Missing amplitude status in /api/sources response")
  }
  return status
}

function assertNoStaleSeededCaveat(status) {
  if (
    status.status === "error" &&
    typeof status.caveat === "string" &&
    status.caveat.includes("Using seeded Amplitude data")
  ) {
    fail("Amplitude error status still has stale seeded caveat")
  }
}

async function run() {
  const before = await requestJson("/api/sources", { method: "GET" })
  if (!before.response.ok) {
    fail(`GET /api/sources failed (${before.response.status})`)
  }

  const beforeAmplitude = amplitudeStatusFromSources(before.body)
  const beforeRunId = beforeAmplitude.latestRunId ?? null
  const beforeAttemptAt = beforeAmplitude.lastAttemptAt ?? null

  const refresh = await requestJson("/api/sources/refresh", {
    method: "POST",
    body: JSON.stringify({ sourceKey: "amplitude" }),
  })
  if (!refresh.response.ok) {
    fail(`POST /api/sources/refresh failed (${refresh.response.status})`)
  }

  const refreshAmplitude = amplitudeStatusFromSources(refresh.body)

  const after = await requestJson("/api/sources", { method: "GET" })
  if (!after.response.ok) {
    fail(`GET /api/sources (after refresh) failed (${after.response.status})`)
  }
  const afterAmplitude = amplitudeStatusFromSources(after.body)

  const refreshed =
    afterAmplitude.latestRunId !== beforeRunId || afterAmplitude.lastAttemptAt !== beforeAttemptAt

  if (!refreshed) {
    fail("Amplitude refresh did not update lastAttemptAt/latestRunId")
  }

  assertNoStaleSeededCaveat(refreshAmplitude)
  assertNoStaleSeededCaveat(afterAmplitude)

  if (!["synced", "error"].includes(afterAmplitude.status)) {
    fail(`Unexpected amplitude status after refresh: ${afterAmplitude.status}`)
  }

  if (afterAmplitude.status === "synced" && !afterAmplitude.snapshotId) {
    fail("Amplitude synced without snapshotId")
  }

  if (afterAmplitude.status === "error" && !afterAmplitude.error) {
    fail("Amplitude error status missing error details")
  }

  console.log("PASS: amplitude refresh endpoint updated status")
  console.log(
    JSON.stringify(
      {
        status: afterAmplitude.status,
        latestRunId: afterAmplitude.latestRunId,
        lastAttemptAt: afterAmplitude.lastAttemptAt,
        snapshotId: afterAmplitude.snapshotId,
        caveat: afterAmplitude.caveat ?? null,
        error: afterAmplitude.error ?? null,
      },
      null,
      2
    )
  )
}

run().catch((error) => {
  const message = error instanceof Error ? error.message : String(error)
  console.error(`FAIL: ${message}`)
  process.exitCode = 1
})
