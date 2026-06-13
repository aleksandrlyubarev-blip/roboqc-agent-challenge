/**
 * GradeLens device-grading schema.
 *
 * Two representations are kept deliberately adjacent and MUST stay in sync:
 *   1. `GRADING_JSON_SCHEMA` — the wire schema sent to Claude via
 *      `output_config.format`. It contains NO numeric/length constraints and sets
 *      `additionalProperties: false` on every object (the structured-output API
 *      rejects `minimum`/`maximum`/`minLength`/… and requires the flag).
 *   2. `GradingResultSchema` (zod) — re-validates the model's JSON client-side and
 *      gives us a typed object. Numeric bounds that can't live in the wire schema
 *      are enforced here instead.
 *
 * This mirrors `src/neuron_vision/fable5/schemas.py` (the Python NeuroVision
 * reference) — same taxonomy, ported to the device domain.
 */
import { z } from "zod";

export const DEVICE_CATEGORIES = [
  "smartphone",
  "laptop",
  "tablet",
  "smartwatch",
  "headphones",
  "other",
] as const;

export const DEFECT_REGIONS = [
  "screen",
  "back",
  "frame",
  "camera",
  "ports",
  "buttons",
  "hinge",
  "other",
] as const;

export const DEFECT_TYPES = [
  "scratch",
  "crack",
  "dent",
  "chip",
  "dead_pixel",
  "discoloration",
  "mura",
  "burn_in",
  "missing_part",
  "wear",
  "other",
] as const;

export const SEVERITIES = ["minor", "moderate", "severe"] as const;
export const CONFIDENCE = ["low", "medium", "high"] as const;
export const GRADES = ["A", "B", "C", "D"] as const;

// ── Zod: post-validation + types ────────────────────────────────────────────
export const DefectSchema = z.object({
  region: z.enum(DEFECT_REGIONS),
  type: z.enum(DEFECT_TYPES),
  severity: z.enum(SEVERITIES),
  description: z.string().min(1),
  location_hint: z.string(),
});

export const GradingResultSchema = z.object({
  device: z.object({
    detected_category: z.enum(DEVICE_CATEGORIES),
    detected_brand_model: z.string(),
    identification_confidence: z.enum(CONFIDENCE),
  }),
  defects: z.array(DefectSchema),
  functional_observations: z.array(z.string()),
  cosmetic_grade: z.enum(GRADES),
  grade_rationale: z.string().min(1),
  resale: z.object({
    sellable: z.boolean(),
    recommended_actions: z.array(z.string()),
  }),
  price_band: z.object({
    currency: z.string().min(1),
    low: z.number().nonnegative(),
    high: z.number().nonnegative(),
    basis: z.string(),
  }),
  confidence_note: z.string(),
});

export type Defect = z.infer<typeof DefectSchema>;
export type GradingResult = z.infer<typeof GradingResultSchema>;

// ── Wire schema for output_config.format (no numeric/length constraints) ─────
export const GRADING_JSON_SCHEMA = {
  type: "object",
  additionalProperties: false,
  properties: {
    device: {
      type: "object",
      additionalProperties: false,
      properties: {
        detected_category: { type: "string", enum: [...DEVICE_CATEGORIES] },
        detected_brand_model: {
          type: "string",
          description: "Best guess of brand + model, or 'unknown'.",
        },
        identification_confidence: { type: "string", enum: [...CONFIDENCE] },
      },
      required: ["detected_category", "detected_brand_model", "identification_confidence"],
    },
    defects: {
      type: "array",
      description: "Every visible cosmetic/physical defect. Empty array if none.",
      items: {
        type: "object",
        additionalProperties: false,
        properties: {
          region: { type: "string", enum: [...DEFECT_REGIONS] },
          type: { type: "string", enum: [...DEFECT_TYPES] },
          severity: { type: "string", enum: [...SEVERITIES] },
          description: { type: "string" },
          location_hint: {
            type: "string",
            description: "Where on the device, e.g. 'top-left of screen'.",
          },
        },
        required: ["region", "type", "severity", "description", "location_hint"],
      },
    },
    functional_observations: {
      type: "array",
      description:
        "Observable functional signals only (e.g. 'screen powers on', 'visible burn-in'). Do not assert what cannot be seen.",
      items: { type: "string" },
    },
    cosmetic_grade: {
      type: "string",
      enum: [...GRADES],
      description: "A=like new, B=light wear, C=visible wear/minor damage, D=heavy damage.",
    },
    grade_rationale: {
      type: "string",
      description: "Why this grade, tied to the listed defects.",
    },
    resale: {
      type: "object",
      additionalProperties: false,
      properties: {
        sellable: { type: "boolean" },
        recommended_actions: {
          type: "array",
          items: { type: "string" },
          description: "Concrete steps to improve resale value (e.g. 'replace screen').",
        },
      },
      required: ["sellable", "recommended_actions"],
    },
    price_band: {
      type: "object",
      additionalProperties: false,
      properties: {
        currency: { type: "string", description: "ISO currency, e.g. 'ILS' or 'USD'." },
        low: { type: "number" },
        high: { type: "number" },
        basis: { type: "string", description: "How the estimate was reasoned, with caveats." },
      },
      required: ["currency", "low", "high", "basis"],
    },
    confidence_note: {
      type: "string",
      description:
        "Limitations of a photo-only grade (battery health, internals, water damage cannot be verified).",
    },
  },
  required: [
    "device",
    "defects",
    "functional_observations",
    "cosmetic_grade",
    "grade_rationale",
    "resale",
    "price_band",
    "confidence_note",
  ],
} as const;

/**
 * Defense-in-depth: strip constraint keys the structured-output API rejects and
 * force `additionalProperties: false` on every object. The hand-written schema
 * above is already clean; this guards against future edits introducing bounds.
 */
const UNSUPPORTED_KEYS = new Set([
  "minimum",
  "maximum",
  "exclusiveMinimum",
  "exclusiveMaximum",
  "multipleOf",
  "minLength",
  "maxLength",
  "pattern",
  "minItems",
  "maxItems",
  "uniqueItems",
]);

export function sanitizeJsonSchema(node: unknown): unknown {
  if (Array.isArray(node)) return node.map(sanitizeJsonSchema);
  if (node && typeof node === "object") {
    const out: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(node as Record<string, unknown>)) {
      if (UNSUPPORTED_KEYS.has(key)) continue;
      out[key] = sanitizeJsonSchema(value);
    }
    if (out.type === "object") out.additionalProperties = false;
    return out;
  }
  return node;
}
