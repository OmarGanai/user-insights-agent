import { NextRequest, NextResponse } from "next/server"
import { refreshSources } from "@/lib/vector/ingest"
import { sourceKeyFromId } from "@/lib/vector/constants"
import type { VectorSourceKey } from "@/lib/vector/types"

interface RefreshRequestBody {
  sourceId?: string
  sourceKey?: VectorSourceKey
  forceErrorSourceId?: string
}

export async function POST(request: NextRequest) {
  const body = (await request.json().catch(() => ({}))) as RefreshRequestBody

  const parsedSourceKey = body.sourceKey ?? (body.sourceId ? sourceKeyFromId(body.sourceId) : null)
  const forceErrorSourceKey = body.forceErrorSourceId
    ? sourceKeyFromId(body.forceErrorSourceId)
    : undefined

  if (body.sourceId && !parsedSourceKey) {
    return NextResponse.json({ error: "Unknown sourceId" }, { status: 400 })
  }

  const result = await refreshSources({
    sourceKey: parsedSourceKey ?? undefined,
    forceErrorSourceKey: forceErrorSourceKey ?? undefined,
  })

  return NextResponse.json(result)
}
