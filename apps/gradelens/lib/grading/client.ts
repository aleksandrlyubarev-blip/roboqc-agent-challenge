/**
 * GradeLens reasoning client — Claude Fable 5 vision + structured output.
 *
 * TypeScript port of `src/neuron_vision/fable5/client.py`. Same design:
 *   - adaptive thinking only (no temperature / budget_tokens);
 *   - structured output via `output_config.format` (json_schema), schema
 *     sanitized of numeric/length constraints, re-validated with zod;
 *   - byte-stable system prompt with an ephemeral cache breakpoint;
 *   - server-side refusal fallback to claude-opus-4-8 (beta
 *     `server-side-fallback-2026-06-01`);
 *   - cost/latency/token telemetry returned with every call.
 *
 * Secrets: reads ANTHROPIC_API_KEY from the environment (Vercel encrypted env).
 * Never logs prompts, images, or responses — metadata only.
 */
import Anthropic from "@anthropic-ai/sdk";

import { GRADING_SYSTEM_PROMPT } from "./prompt";
import {
  GRADING_JSON_SCHEMA,
  GradingResult,
  GradingResultSchema,
  sanitizeJsonSchema,
} from "./schema";

const PRIMARY_MODEL = "claude-fable-5";
const FALLBACK_MODEL = "claude-opus-4-8";
const MAX_TOKENS = 16_000;
const SERVER_SIDE_FALLBACK_BETA = "server-side-fallback-2026-06-01";

// USD per million tokens: [input, output].
const PRICING: Record<string, [number, number]> = {
  "claude-fable-5": [10, 50],
  "claude-opus-4-8": [5, 25],
};

export interface ImageInput {
  /** e.g. "image/jpeg" | "image/png" | "image/webp" */
  mediaType: string;
  /** base64-encoded image bytes (no data: prefix) */
  base64: string;
}

export interface GradeCallMeta {
  modelId: string;
  fallbackUsed: boolean;
  latencyMs: number;
  inputTokens: number;
  outputTokens: number;
  estimatedCostUsd: number;
}

export interface GradeResponse {
  result: GradingResult;
  meta: GradeCallMeta;
}

export class GradingError extends Error {}

// Minimal response shape we read — decouples us from beta param typing churn.
interface ContentBlock {
  type: string;
  text?: string;
}
interface Usage {
  input_tokens?: number;
  output_tokens?: number;
  cache_read_input_tokens?: number;
  cache_creation_input_tokens?: number;
}
interface BetaMessageResponse {
  model: string;
  stop_reason: string | null;
  stop_details?: { category?: string | null } | null;
  content: ContentBlock[];
  usage?: Usage;
}

let cachedClient: Anthropic | null = null;
function getClient(): Anthropic {
  if (!cachedClient) {
    const apiKey = process.env.ANTHROPIC_API_KEY;
    if (!apiKey) throw new GradingError("ANTHROPIC_API_KEY is not set");
    cachedClient = new Anthropic({ apiKey, maxRetries: 3 });
  }
  return cachedClient;
}

function estimateCostUsd(model: string, usage: Usage): number {
  const [inRate, outRate] = PRICING[model] ?? PRICING[FALLBACK_MODEL];
  const cachedIn = usage.cache_read_input_tokens ?? 0;
  const writeIn = usage.cache_creation_input_tokens ?? 0;
  const freshIn = usage.input_tokens ?? 0;
  const out = usage.output_tokens ?? 0;
  // cache reads ~0.1x, cache writes ~1.25x, fresh input 1x.
  const inputCost = (freshIn + writeIn * 1.25 + cachedIn * 0.1) * inRate;
  return (inputCost + out * outRate) / 1_000_000;
}

function buildUserContent(images: ImageInput[], deviceHint?: string): unknown[] {
  const blocks: unknown[] = images.map((img) => ({
    type: "image",
    source: { type: "base64", media_type: img.mediaType, data: img.base64 },
  }));
  const hint = deviceHint?.trim()
    ? `Seller-provided context: ${deviceHint.trim()}\n\n`
    : "";
  blocks.push({
    type: "text",
    text:
      `${hint}Grade the device shown in these photos. Inspect every visible ` +
      `surface, list all defects, assign an A–D cosmetic grade, and estimate a ` +
      `resale price band. If a currency is implied by the context use it, ` +
      `otherwise default to USD.`,
  });
  return blocks;
}

/**
 * Grade a single device from one or more photos.
 * Throws GradingError on refusal (both models declined) or unparseable output.
 */
export async function gradeDevice(
  images: ImageInput[],
  deviceHint?: string,
): Promise<GradeResponse> {
  if (images.length === 0) throw new GradingError("at least one photo is required");

  const effort = process.env.GRADELENS_EFFORT ?? "high";
  const client = getClient();

  const params = {
    model: PRIMARY_MODEL,
    max_tokens: MAX_TOKENS,
    betas: [SERVER_SIDE_FALLBACK_BETA],
    fallbacks: [{ model: FALLBACK_MODEL }],
    thinking: { type: "adaptive" },
    output_config: {
      effort,
      format: { type: "json_schema", schema: sanitizeJsonSchema(GRADING_JSON_SCHEMA) },
    },
    system: [
      {
        type: "text",
        text: GRADING_SYSTEM_PROMPT,
        cache_control: { type: "ephemeral" },
      },
    ],
    messages: [{ role: "user", content: buildUserContent(images, deviceHint) }],
  };

  const started = Date.now();
  // Cast the method: beta params (`fallbacks`, `output_config`) may lag the
  // installed SDK's static types. Requires @anthropic-ai/sdk with Fable 5 support.
  const create = client.beta.messages.create as unknown as (
    p: unknown,
  ) => Promise<BetaMessageResponse>;

  let response: BetaMessageResponse;
  try {
    response = await create(params);
  } catch (err) {
    throw new GradingError(`Anthropic request failed: ${(err as Error).message}`);
  }
  const latencyMs = Date.now() - started;

  if (response.stop_reason === "refusal") {
    const category = response.stop_details?.category ?? "unknown";
    throw new GradingError(`request was declined by safety classifiers (${category})`);
  }

  const text = response.content.find((b) => b.type === "text")?.text;
  if (!text) throw new GradingError("model returned no text content");

  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch {
    throw new GradingError("model output was not valid JSON");
  }

  const validated = GradingResultSchema.safeParse(parsed);
  if (!validated.success) {
    throw new GradingError(`model output failed schema validation: ${validated.error.message}`);
  }

  const usage = response.usage ?? {};
  const meta: GradeCallMeta = {
    modelId: response.model,
    fallbackUsed: !response.model.startsWith("claude-fable-5"),
    latencyMs,
    inputTokens: usage.input_tokens ?? 0,
    outputTokens: usage.output_tokens ?? 0,
    estimatedCostUsd: estimateCostUsd(response.model, usage),
  };

  return { result: validated.data, meta };
}
