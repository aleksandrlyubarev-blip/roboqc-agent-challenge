/**
 * DepositShield condition-inspection schema.
 *
 * The heart of the product is `wear_classification` (normal wear-and-tear vs
 * damage beyond normal wear) and a *draft* responsibility hint — this is where
 * Fable 5 reasoning visibly beats pixel-only detection. Framing is deliberately
 * cautious: this drafts a condition report, it is not a legal determination.
 *
 * Two representations kept in sync (same pattern as the NeuroVision pipeline):
 *   - INSPECTION_JSON_SCHEMA: wire schema for output_config.format (no numeric/
 *     length constraints, additionalProperties:false on every object).
 *   - InspectionReportSchema (zod): re-validates the model's JSON, gives types.
 */
import { z } from "zod";

export const AREAS = [
  "kitchen",
  "bathroom",
  "living_room",
  "bedroom",
  "hallway",
  "balcony",
  "laundry",
  "exterior",
  "other",
] as const;

export const ELEMENTS = [
  "wall",
  "ceiling",
  "floor",
  "flooring",
  "door",
  "window",
  "countertop",
  "cabinet",
  "appliance",
  "fixture",
  "plumbing",
  "other",
] as const;

export const DEFECT_TYPES = [
  "stain",
  "scratch",
  "crack",
  "hole",
  "dent",
  "mould",
  "water_damage",
  "chip",
  "missing",
  "broken",
  "dirty",
  "paint_damage",
  "other",
] as const;

export const SEVERITIES = ["minor", "moderate", "severe"] as const;
export const CONDITIONS = ["good", "light_wear", "damage"] as const;
export const WEAR_CLASS = ["normal_wear", "beyond_normal_wear", "unclear"] as const;
export const RESPONSIBILITY = ["tenant", "landlord", "shared", "unclear"] as const;
export const OVERALL = ["excellent", "good", "fair", "poor"] as const;

// ── zod: post-validation + types ────────────────────────────────────────────
export const FindingSchema = z.object({
  area: z.enum(AREAS),
  element: z.enum(ELEMENTS),
  type: z.enum(DEFECT_TYPES),
  severity: z.enum(SEVERITIES),
  condition: z.enum(CONDITIONS),
  description: z.string().min(1),
  location_hint: z.string(),
  wear_classification: z.enum(WEAR_CLASS),
  draft_responsibility: z.enum(RESPONSIBILITY),
  responsibility_rationale: z.string(),
});

export const InspectionReportSchema = z.object({
  overall_condition: z.enum(OVERALL),
  summary: z.string().min(1),
  areas_inspected: z.array(z.enum(AREAS)),
  findings: z.array(FindingSchema),
  confidence_note: z.string(),
});

export type Finding = z.infer<typeof FindingSchema>;
export type InspectionReport = z.infer<typeof InspectionReportSchema>;

// ── wire schema (no numeric/length constraints) ─────────────────────────────
export const INSPECTION_JSON_SCHEMA = {
  type: "object",
  additionalProperties: false,
  properties: {
    overall_condition: {
      type: "string",
      enum: [...OVERALL],
      description: "Overall condition of the property across inspected areas.",
    },
    summary: { type: "string", description: "Plain-language summary of the property's condition." },
    areas_inspected: {
      type: "array",
      items: { type: "string", enum: [...AREAS] },
      description: "Distinct areas visible across the photos.",
    },
    findings: {
      type: "array",
      description: "Every visible condition issue. Empty array if the property is in clean condition.",
      items: {
        type: "object",
        additionalProperties: false,
        properties: {
          area: { type: "string", enum: [...AREAS] },
          element: { type: "string", enum: [...ELEMENTS] },
          type: { type: "string", enum: [...DEFECT_TYPES] },
          severity: { type: "string", enum: [...SEVERITIES] },
          condition: { type: "string", enum: [...CONDITIONS] },
          description: { type: "string" },
          location_hint: { type: "string", description: "Where in the photo / area." },
          wear_classification: {
            type: "string",
            enum: [...WEAR_CLASS],
            description:
              "normal_wear = expected aging from ordinary living; beyond_normal_wear = damage exceeding normal use; unclear if not determinable from a photo.",
          },
          draft_responsibility: {
            type: "string",
            enum: [...RESPONSIBILITY],
            description: "DRAFT hint only, not a legal determination.",
          },
          responsibility_rationale: {
            type: "string",
            description: "Why this draft classification, with caveats.",
          },
        },
        required: [
          "area",
          "element",
          "type",
          "severity",
          "condition",
          "description",
          "location_hint",
          "wear_classification",
          "draft_responsibility",
          "responsibility_rationale",
        ],
      },
    },
    confidence_note: {
      type: "string",
      description:
        "Limitations of a photo-only inspection (no before/after comparison, hidden damage, measurements cannot be verified).",
    },
  },
  required: ["overall_condition", "summary", "areas_inspected", "findings", "confidence_note"],
} as const;

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
