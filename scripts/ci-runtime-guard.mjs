import { readFileSync } from "node:fs"

function assertIncludesAll(haystack, needles, context) {
  const missing = needles.filter((needle) => !haystack.includes(needle))
  if (missing.length > 0) {
    throw new Error(`${context} is missing required entries: ${missing.join(", ")}`)
  }
}

function main() {
  const envExample = readFileSync(".env.example", "utf8")
  const readme = readFileSync("README.md", "utf8")
  const v3Plan = readFileSync("redo/shaping/V3-plan.md", "utf8")
  const slices = readFileSync("redo/shaping/vector-slices-final.md", "utf8")

  const requiredRuntimeKeys = ["ADK_RUNTIME_URL", "GEMINI_API_KEY", "GEMINI_MODEL"]
  assertIncludesAll(envExample, requiredRuntimeKeys, ".env.example")
  assertIncludesAll(readme, requiredRuntimeKeys, "README.md")

  assertIncludesAll(
    v3Plan,
    ["Runtime identity gate", "Completion semantics gate", "Config parity gate"],
    "redo/shaping/V3-plan.md"
  )

  assertIncludesAll(
    slices,
    ["backend=adk_gemini", "No deterministic synthesis fallback"],
    "redo/shaping/vector-slices-final.md"
  )

  console.log("runtime guard checks passed")
}

try {
  main()
} catch (error) {
  const message = error instanceof Error ? error.message : String(error)
  console.error(`runtime guard failed: ${message}`)
  process.exit(1)
}
