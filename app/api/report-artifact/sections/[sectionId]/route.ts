import { NextRequest, NextResponse } from "next/server"
import { updateReportSection } from "@/lib/vector/artifact-store"

interface RequestBody {
  content?: unknown
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ sectionId: string }> }
) {
  const body = (await request.json()) as RequestBody
  const sectionId = (await params).sectionId

  if (typeof body.content !== "string") {
    return NextResponse.json(
      { error: "content must be a string" },
      { status: 400 }
    )
  }

  try {
    const artifact = updateReportSection(sectionId, body.content)
    return NextResponse.json({ artifact })
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown update error"
    return NextResponse.json({ error: message }, { status: 404 })
  }
}
