import { MOCK_SOURCES } from "@/lib/mock-data"
import { sourceIdFromKey } from "@/lib/vector/constants"
import { isoNow, startOfDayIso } from "@/lib/vector/time"
import type { NormalizedSourceSnapshot } from "@/lib/vector/types"
import type { AdapterResult } from "@/lib/vector/adapters/amplitude"

interface TypeformTheme {
  label: string
  count: number
}

interface TypeformResponseSample {
  id: string
  submittedAt: string
  textPreview: string
}

interface TypeformResponseItem {
  token?: string
  submitted_at?: string
  answers?: Array<{ type?: string; text?: string }>
}

export interface FetchTypeformOptions {
  runId: string
  since?: string
  until?: string
  fetchImpl?: typeof fetch
  forceError?: boolean
}

function buildSeededThemes(): TypeformTheme[] {
  return [
    { label: "onboarding confusion", count: 14 },
    { label: "bulk action requests", count: 7 },
    { label: "performance concerns", count: 4 },
  ]
}

function summarizeThemesFromItems(items: TypeformResponseItem[]): TypeformTheme[] {
  const buckets: Record<string, number> = {
    "onboarding confusion": 0,
    "bulk action requests": 0,
    "performance concerns": 0,
    other: 0,
  }

  for (const item of items) {
    const combined = (item.answers ?? [])
      .map((answer) => answer.text ?? "")
      .join(" ")
      .toLowerCase()

    if (combined.includes("onboarding") || combined.includes("signup")) {
      buckets["onboarding confusion"] += 1
    } else if (combined.includes("bulk") || combined.includes("multi-select")) {
      buckets["bulk action requests"] += 1
    } else if (combined.includes("slow") || combined.includes("performance")) {
      buckets["performance concerns"] += 1
    } else {
      buckets.other += 1
    }
  }

  return Object.entries(buckets)
    .filter(([, count]) => count > 0)
    .map(([label, count]) => ({ label, count }))
    .sort((a, b) => b.count - a.count)
}

async function fetchTypeformItems(
  formId: string,
  apiKey: string,
  since: string,
  until: string,
  fetchImpl: typeof fetch
): Promise<TypeformResponseItem[]> {
  const allItems: TypeformResponseItem[] = []
  let after: string | null = null

  for (let page = 0; page < 10; page += 1) {
    const url = new URL(`https://api.typeform.com/forms/${formId}/responses`)
    url.searchParams.set("completed", "true")
    url.searchParams.set("since", since)
    url.searchParams.set("until", until)
    url.searchParams.set("page_size", "100")

    if (after) {
      url.searchParams.set("after", after)
    }

    const response = await fetchImpl(url.toString(), {
      headers: {
        Authorization: `Bearer ${apiKey}`,
        Accept: "application/json",
      },
      cache: "no-store",
    })

    if (!response.ok) {
      const body = await response.text()
      throw new Error(`Typeform fetch failed (${response.status}): ${body || "unknown"}`)
    }

    const payload = (await response.json()) as {
      items?: TypeformResponseItem[]
      total_items?: number
    }

    const pageItems = payload.items ?? []
    allItems.push(...pageItems)

    if (pageItems.length === 0) {
      break
    }

    const nextCursor = pageItems[pageItems.length - 1]?.token
    if (!nextCursor || pageItems.length < 100) {
      break
    }

    after = nextCursor

    if (payload.total_items && allItems.length >= payload.total_items) {
      break
    }
  }

  return allItems
}

function createSamples(items: TypeformResponseItem[]): TypeformResponseSample[] {
  return items.slice(0, 5).map((item, index) => ({
    id: item.token ?? `response-${index + 1}`,
    submittedAt: item.submitted_at ?? isoNow(),
    textPreview:
      (item.answers ?? [])
        .map((answer) => answer.text ?? "")
        .join(" ")
        .slice(0, 180) || "No text response provided.",
  }))
}

/**
 * fetch_typeform adapter
 *
 * Pagination handling:
 * - Uses Typeform cursor pagination through the `after` token.
 * - Requests `completed=true` and bounded `since`/`until` range for deterministic windows.
 *
 * Delayed-response awareness:
 * - When the requested window includes very recent time, Typeform responses can lag.
 * - The adapter emits a caveat string surfaced directly in the Sources UI.
 */
export async function fetchTypeform(
  options: FetchTypeformOptions
): Promise<
  AdapterResult<{
    responseCount: number
    themes: TypeformTheme[]
    samples: TypeformResponseSample[]
    window: { since: string; until: string }
  }>
> {
  const {
    runId,
    since = startOfDayIso(7),
    until = isoNow(),
    fetchImpl = fetch,
    forceError = false,
  } = options

  if (forceError) {
    throw new Error("Forced typeform adapter failure")
  }

  const apiKey = process.env.TYPEFORM_API_KEY
  const formId = process.env.TYPEFORM_FORM_ID

  let responseCount = 0
  let themes: TypeformTheme[] = []
  let samples: TypeformResponseSample[] = []
  let caveat: string | null = null

  if (!apiKey || !formId) {
    const fallbackSource = MOCK_SOURCES.find((source) => source.type === "typeform")
    responseCount = fallbackSource?.responseCount ?? fallbackSource?.recordCount ?? 0
    themes = buildSeededThemes()
    samples = [
      {
        id: "seeded-response-1",
        submittedAt: isoNow(),
        textPreview: "Seeded Typeform data in use. Configure TYPEFORM_API_KEY and TYPEFORM_FORM_ID for live responses.",
      },
    ]
    caveat = "Using seeded Typeform responses. Configure TYPEFORM_API_KEY and TYPEFORM_FORM_ID for live ingest."
  } else {
    const items = await fetchTypeformItems(formId, apiKey, since, until, fetchImpl)
    responseCount = items.length
    themes = summarizeThemesFromItems(items)
    samples = createSamples(items)
  }

  const minutesSinceUntil = (Date.now() - Date.parse(until)) / 60000
  if (minutesSinceUntil <= 120) {
    caveat = "Typeform may delay very recent completed responses; newest submissions can appear with a short lag."
  }

  const snapshot: NormalizedSourceSnapshot<{
    responseCount: number
    themes: TypeformTheme[]
    samples: TypeformResponseSample[]
    window: { since: string; until: string }
  }> = {
    id: `${sourceIdFromKey("typeform")}-${runId}`,
    sourceKey: "typeform",
    sourceId: sourceIdFromKey("typeform"),
    runId,
    capturedAt: isoNow(),
    summary: `${responseCount} completed responses normalized from Typeform`,
    recordCount: responseCount,
    data: {
      responseCount,
      themes,
      samples,
      window: { since, until },
    },
  }

  return { snapshot, caveat }
}
