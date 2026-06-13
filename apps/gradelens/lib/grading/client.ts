/**
 * GradeLens reasoning client — Claude Opus 4.8 vision + structured output.
 *
 * Adaptive thinking; structured output via output_config.format (schema
 * sanitized + zod re-validated); byte-stable cached system prompt. Logs
 * metadata only — never prompts, images, or output.
 */
import Anthropic from "@anthropic-ai/sdk";

import { GRADING_SYSTEM_PROMPT } from "./prompt";
import {
  GRADING_JSON_SCHEMA,
  GradingResult,
  GradingResultSchema,
  sanitizeJsonSchema,
} from "./schema";

const MODEL = "claude-opus-4-8";
const MAX_TOKENS = 16_000;
// USD per million tokens for claude-opus-4-8.
const INPUT_RATE = 5;
const OUTPUT_RATE = 25;

export interface ImageInput {
  /** e.g. "image/jpeg" | "image/png" | "image/webp" */
  mediaType: string;
  /** base64-encoded image bytes (no data: prefix) */
  base64: string;
}

export interface GradeCallMeta {
  modelId: string;
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
interface MessageResponse {
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

function estimateCostUsd(usage: Usage): number {
  const cachedIn = usage.cache_read_input_tokens ?? 0;
  const writeIn = usage.cache_creation_input_tokens ?? 0;
  const freshIn = usage.input_tokens ?? 0;
  const out = usage.output_tokens ?? 0;
  const inputCost = (freshIn + writeIn * 1.25 + cachedIn * 0.1) * INPUT_RATE;
  return (inputCost + out * OUTPUT_RATE) / 1_000_000;
}

function buildUserContent(images: ImageInput[], deviceHint?: string): unknown[] {
  const blocks: unknown[] = images.map((img) => ({
    type: "image",
    source: { type: "base64", media_type: img.mediaType, data: img.base64 },
  }));
  const hint = deviceHint?.trim() ? `Seller-provided context: ${deviceHint.trim()}\n\n` : "";
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
 * Throws GradingError on refusal or unparseable output.
 */
export async function gradeDevice(
  images: ImageInput[],
  deviceHint?: string,
): Promise<GradeResponse> {
  if (images.length === 0) throw new GradingError("at least one photo is required");

  const effort = process.env.GRADELENS_EFFORT ?? "high";
  const client = getClient();

  const params = {
    model: MODEL,
    max_tokens: MAX_TOKENS,
    thinking: { type: "adaptive" },
    output_config: {
      effort,
      format: { type: "json_schema", schema: sanitizeJsonSchema(GRADING_JSON_SCHEMA) },
    },
    system: [
      { type: "text", text: GRADING_SYSTEM_PROMPT, cache_control: { type: "ephemeral" } },
    ],
    messages: [{ role: "user", content: buildUserContent(images, deviceHint) }],
  };

  const started = Date.now();
  // Cast: output_config typing can lag the installed SDK.
  const create = client.messages.create as unknown as (p: unknown) => Promise<MessageResponse>;

  let response: MessageResponse;
  try {
    response = await create(params);
  } catch (err) {
    throw new GradingError(`Anthropic request failed: ${(err as Error).message}`);
  }
  const latencyMs = Date.now() - started;

  if (response.stop_reason === "refusal") {
    const category = response.stop_details?.category ?? "unknown";
    throw new GradingError(`request was declined (${category})`);
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
    latencyMs,
    inputTokens: usage.input_tokens ?? 0,
    outputTokens: usage.output_tokens ?? 0,
    estimatedCostUsd: estimateCostUsd(usage),
  };

  return { result: validated.data, meta };
}
