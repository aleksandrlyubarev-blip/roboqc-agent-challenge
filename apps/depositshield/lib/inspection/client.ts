/**
 * DepositShield reasoning client — Claude Opus 4.8 vision + structured output.
 *
 * Adaptive thinking; structured output via output_config.format (schema
 * sanitized + zod re-validated); byte-stable cached system prompt. Logs
 * metadata only — never prompts, images, or output.
 */
import Anthropic from "@anthropic-ai/sdk";

import { INSPECTION_SYSTEM_PROMPT } from "./prompt";
import {
  INSPECTION_JSON_SCHEMA,
  InspectionReport,
  InspectionReportSchema,
  sanitizeJsonSchema,
} from "./schema";

const MODEL = "claude-opus-4-8";
const MAX_TOKENS = 16_000;
// USD per million tokens for claude-opus-4-8.
const INPUT_RATE = 5;
const OUTPUT_RATE = 25;

export interface ImageInput {
  mediaType: string;
  base64: string;
}

export interface InspectionMeta {
  modelId: string;
  latencyMs: number;
  inputTokens: number;
  outputTokens: number;
  estimatedCostUsd: number;
}

export interface InspectionResponse {
  report: InspectionReport;
  meta: InspectionMeta;
}

export class InspectionError extends Error {}

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
    if (!apiKey) throw new InspectionError("ANTHROPIC_API_KEY is not set");
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

function buildUserContent(images: ImageInput[], phase: string, context?: string): unknown[] {
  const blocks: unknown[] = images.map((img) => ({
    type: "image",
    source: { type: "base64", media_type: img.mediaType, data: img.base64 },
  }));
  const ctx = context?.trim() ? `Additional context: ${context.trim()}\n\n` : "";
  blocks.push({
    type: "text",
    text:
      `${ctx}This is a ${phase} inspection of a rental property. Inspect every ` +
      `visible area in these photos, draft a room-by-room condition report, and ` +
      `for each issue classify normal wear vs. damage beyond normal wear with a ` +
      `draft responsibility hint. Remember this is not a legal determination.`,
  });
  return blocks;
}

/**
 * Inspect a set of property photos and draft a condition report.
 * Throws InspectionError on refusal or bad output.
 */
export async function inspectCondition(
  images: ImageInput[],
  phase: "move_in" | "move_out",
  context?: string,
): Promise<InspectionResponse> {
  if (images.length === 0) throw new InspectionError("at least one photo is required");

  const effort = process.env.DEPOSITSHIELD_EFFORT ?? "high";
  const client = getClient();

  const params = {
    model: MODEL,
    max_tokens: MAX_TOKENS,
    thinking: { type: "adaptive" },
    output_config: {
      effort,
      format: { type: "json_schema", schema: sanitizeJsonSchema(INSPECTION_JSON_SCHEMA) },
    },
    system: [
      { type: "text", text: INSPECTION_SYSTEM_PROMPT, cache_control: { type: "ephemeral" } },
    ],
    messages: [{ role: "user", content: buildUserContent(images, phase, context) }],
  };

  const started = Date.now();
  // Cast: output_config typing can lag the installed SDK.
  const create = client.messages.create as unknown as (p: unknown) => Promise<MessageResponse>;

  let response: MessageResponse;
  try {
    response = await create(params);
  } catch (err) {
    throw new InspectionError(`Anthropic request failed: ${(err as Error).message}`);
  }
  const latencyMs = Date.now() - started;

  if (response.stop_reason === "refusal") {
    const category = response.stop_details?.category ?? "unknown";
    throw new InspectionError(`request was declined (${category})`);
  }

  const text = response.content.find((b) => b.type === "text")?.text;
  if (!text) throw new InspectionError("model returned no text content");

  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch {
    throw new InspectionError("model output was not valid JSON");
  }

  const validated = InspectionReportSchema.safeParse(parsed);
  if (!validated.success) {
    throw new InspectionError(`model output failed schema validation: ${validated.error.message}`);
  }

  const usage = response.usage ?? {};
  const meta: InspectionMeta = {
    modelId: response.model,
    latencyMs,
    inputTokens: usage.input_tokens ?? 0,
    outputTokens: usage.output_tokens ?? 0,
    estimatedCostUsd: estimateCostUsd(usage),
  };

  return { report: validated.data, meta };
}
