import { NextResponse } from "next/server"
import { getLatestTrace } from "@/lib/vector/workflows"

export async function GET() {
  const trace = await getLatestTrace()
  return NextResponse.json({ trace })
}
