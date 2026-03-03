import { promises as fs } from "node:fs"
import path from "node:path"
import { MOCK_SOURCES } from "@/lib/mock-data"
import { IOS_RELEASE_NOTES_FILE, sourceIdFromKey } from "@/lib/vector/constants"
import { isoNow } from "@/lib/vector/time"
import type { NormalizedSourceSnapshot } from "@/lib/vector/types"
import type { AdapterResult } from "@/lib/vector/adapters/amplitude"

interface ITunesLookupResult {
  version?: string
  currentVersionReleaseDate?: string
  trackName?: string
}

interface ITunesLookupPayload {
  resultCount?: number
  results?: ITunesLookupResult[]
}

export interface FetchIosReleaseOptions {
  runId: string
  fetchImpl?: typeof fetch
  forceError?: boolean
}

async function readReleaseNotesFile(): Promise<string> {
  const absolutePath = path.join(process.cwd(), IOS_RELEASE_NOTES_FILE)
  return fs.readFile(absolutePath, "utf8")
}

async function fetchItunesLookupMetadata(
  appId: string,
  fetchImpl: typeof fetch
): Promise<ITunesLookupResult | null> {
  const response = await fetchImpl(`https://itunes.apple.com/lookup?id=${appId}`, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  })

  if (!response.ok) {
    const body = await response.text()
    throw new Error(`iTunes lookup failed (${response.status}): ${body || "unknown"}`)
  }

  const payload = (await response.json()) as ITunesLookupPayload
  if (!payload.resultCount || !payload.results || payload.results.length === 0) {
    return null
  }

  return payload.results[0] ?? null
}

/**
 * iOS release adapter
 *
 * Merge behavior:
 * - Reads curated markdown release notes via `readReleaseNotesFile`.
 * - Enriches with Apple Lookup metadata via `fetch_itunes_lookup_metadata` when `IOS_APP_ID` is set.
 * - Produces one normalized snapshot containing both local notes and lookup metadata.
 */
export async function fetchIosRelease(
  options: FetchIosReleaseOptions
): Promise<
  AdapterResult<{
    appName: string
    latestVersion: string
    latestReleaseDate: string
    releaseNotesMarkdown: string
  }>
> {
  const { runId, fetchImpl = fetch, forceError = false } = options

  if (forceError) {
    throw new Error("Forced iOS adapter failure")
  }

  const [releaseNotesMarkdown, fallbackSource] = await Promise.all([
    readReleaseNotesFile(),
    Promise.resolve(MOCK_SOURCES.find((source) => source.type === "ios_release")),
  ])

  const appId = process.env.IOS_APP_ID

  let appName = "Vector iOS"
  let latestVersion = fallbackSource?.latestRelease ?? "v3.1.0"
  let latestReleaseDate = fallbackSource?.latestReleaseDate ?? "2026-02-27"
  let caveat: string | null = null

  if (!appId) {
    caveat = "Using local iOS release notes only. Configure IOS_APP_ID to include live iTunes metadata."
  } else {
    const metadata = await fetchItunesLookupMetadata(appId, fetchImpl)
    if (metadata) {
      appName = metadata.trackName ?? appName
      latestVersion = metadata.version ?? latestVersion
      latestReleaseDate = metadata.currentVersionReleaseDate ?? latestReleaseDate
    }
  }

  const snapshot: NormalizedSourceSnapshot<{
    appName: string
    latestVersion: string
    latestReleaseDate: string
    releaseNotesMarkdown: string
  }> = {
    id: `${sourceIdFromKey("ios_release")}-${runId}`,
    sourceKey: "ios_release",
    sourceId: sourceIdFromKey("ios_release"),
    runId,
    capturedAt: isoNow(),
    summary: `Merged iOS lookup metadata with release markdown for ${latestVersion}`,
    recordCount: 1,
    data: {
      appName,
      latestVersion,
      latestReleaseDate,
      releaseNotesMarkdown,
    },
  }

  return { snapshot, caveat }
}
