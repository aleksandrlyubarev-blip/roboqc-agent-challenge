/**
 * Pure presentational condition report — usable from both the client flow
 * (app/page.tsx) and the server-rendered shareable page (app/r/[id]/page.tsx).
 */
import type { InspectionMeta } from "@/lib/inspection/client";
import type { Finding, InspectionReport } from "@/lib/inspection/schema";

const PHASE_LABEL: Record<string, string> = {
  move_in: "Move-in",
  move_out: "Move-out",
};

function groupByArea(findings: Finding[]): Record<string, Finding[]> {
  return findings.reduce<Record<string, Finding[]>>((acc, f) => {
    (acc[f.area] ??= []).push(f);
    return acc;
  }, {});
}

export function Report({
  report,
  meta,
  propertyLabel,
  phase,
  generatedAt,
}: {
  report: InspectionReport;
  meta?: InspectionMeta;
  propertyLabel?: string;
  phase?: string;
  generatedAt?: string;
}) {
  const groups = groupByArea(report.findings);
  return (
    <div className="card">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <div>
          {propertyLabel && <div style={{ fontWeight: 600 }}>{propertyLabel}</div>}
          {phase && (
            <div className="muted" style={{ fontSize: 13 }}>
              {PHASE_LABEL[phase] ?? phase} inspection
              {generatedAt && ` · ${new Date(generatedAt).toLocaleDateString()}`}
            </div>
          )}
        </div>
        <span className={`overall ${report.overall_condition}`}>{report.overall_condition}</span>
      </div>

      <p style={{ marginTop: 14 }}>{report.summary}</p>

      <h2>Findings {report.findings.length > 0 ? `(${report.findings.length})` : ""}</h2>
      {report.findings.length === 0 ? (
        <p className="muted">No condition issues found in the photos provided.</p>
      ) : (
        Object.entries(groups).map(([area, items]) => (
          <div className="area-group" key={area}>
            <div className="area-head">{area.replace(/_/g, " ")}</div>
            {items.map((f, i) => (
              <div className="finding" key={i}>
                <div className="top">
                  <strong>
                    {f.element.replace(/_/g, " ")} · {f.type.replace(/_/g, " ")}
                  </strong>
                  <span style={{ display: "flex", gap: 6 }}>
                    <span className={`tag sev ${f.severity}`}>{f.severity}</span>
                    <span className={`tag wear ${f.wear_classification}`}>
                      {f.wear_classification.replace(/_/g, " ")}
                    </span>
                  </span>
                </div>
                <div className="muted" style={{ fontSize: 14, marginTop: 4 }}>
                  {f.description}
                  {f.location_hint && ` — ${f.location_hint}`}
                </div>
                <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>
                  Draft responsibility: <strong>{f.draft_responsibility}</strong> —{" "}
                  {f.responsibility_rationale}
                </div>
              </div>
            ))}
          </div>
        ))
      )}

      <p className="muted" style={{ fontSize: 13, marginTop: 16 }}>
        {report.confidence_note}
      </p>
      <p className="disclaimer" style={{ margin: "12px 0 0" }}>
        This is a draft condition report that organizes visual evidence. It is not a legal
        determination and makes no promise about deposit outcomes. Responsibility hints depend on
        the lease, the move-in baseline, and local law.
      </p>

      {meta && (
        <p className="meta">
          Drafted by {meta.modelId} · {meta.latencyMs} ms ·{" "}
          {meta.inputTokens + meta.outputTokens} tokens · ~${meta.estimatedCostUsd.toFixed(4)}
        </p>
      )}
    </div>
  );
}
