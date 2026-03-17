import { NextResponse } from "next/server"
import { ensureInitialIngest } from "@/lib/vector/ingest"

export const dynamic = "force-dynamic"

export async function GET() {
  const status = await ensureInitialIngest()
  return NextResponse.json(status)
}
