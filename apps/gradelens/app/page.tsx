"use client";

import { useEffect, useState } from "react";

import type { GradeCallMeta } from "@/lib/grading/client";
import type { GradingResult } from "@/lib/grading/schema";

interface GradeResponse {
  id: string;
  result: GradingResult;
  meta: GradeCallMeta;
}

type Status = "idle" | "uploading" | "grading";

function userId(): string {
  if (typeof window === "undefined") return "anonymous";
  let id = window.localStorage.getItem("gradelens_uid");
  if (!id) {
    id = crypto.randomUUID();
    window.localStorage.setItem("gradelens_uid", id);
  }
  return id;
}

export default function Home() {
  const [files, setFiles] = useState<File[]>([]);
  const [previews, setPreviews] = useState<string[]>([]);
  const [hint, setHint] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<GradeResponse | null>(null);

  useEffect(() => {
    return () => previews.forEach((url) => URL.revokeObjectURL(url));
  }, [previews]);

  function onSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const picked = Array.from(e.target.files ?? []).slice(0, 8);
    setFiles(picked);
    setPreviews(picked.map((f) => URL.createObjectURL(f)));
    setData(null);
    setError(null);
  }

  async function uploadOne(file: File): Promise<string> {
    const res = await fetch("/api/upload-url", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ contentType: file.type }),
    });
    if (!res.ok) throw new Error((await res.json()).error ?? "upload URL failed");
    const { key, url } = await res.json();
    const put = await fetch(url, {
      method: "PUT",
      headers: { "content-type": file.type },
      body: file,
    });
    if (!put.ok) throw new Error("photo upload to storage failed");
    return key;
  }

  async function grade() {
    if (files.length === 0) return;
    setError(null);
    setData(null);
    try {
      setStatus("uploading");
      const photoKeys = await Promise.all(files.map(uploadOne));
      setStatus("grading");
      const res = await fetch("/api/grade", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ photoKeys, deviceHint: hint, userId: userId() }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error ?? "grading failed");
      setData(json as GradeResponse);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setStatus("idle");
    }
  }

  const busy = status !== "idle";

  return (
    <main>
      <div className="brand">
        <h1>
          GradeLens<span className="dot">.</span>
        </h1>
      </div>
      <p className="tagline">
        Photograph a used device — get an instant, dispute-ready condition report.
      </p>

      <div className="card">
        <label className="field" htmlFor="photos">
          Device photos (front, back, corners — up to 8)
        </label>
        <input id="photos" type="file" accept="image/*" multiple onChange={onSelect} />
        {previews.length > 0 && (
          <div className="thumbs">
            {previews.map((src) => (
              // eslint-disable-next-line @next/next/no-img-element
              <img key={src} className="thumb" src={src} alt="device" />
            ))}
          </div>
        )}

        <label className="field" htmlFor="hint" style={{ marginTop: 8 }}>
          Optional context (model, currency, known issues)
        </label>
        <input
          id="hint"
          type="text"
          placeholder="e.g. iPhone 13, price in ILS, screen replaced once"
          value={hint}
          onChange={(e) => setHint(e.target.value)}
        />

        <div style={{ marginTop: 16 }}>
          <button className="primary" onClick={grade} disabled={busy || files.length === 0}>
            {status === "uploading"
              ? "Uploading photos…"
              : status === "grading"
                ? "Grading…"
                : "Grade device"}
          </button>
        </div>
        {error && <p className="error">⚠ {error}</p>}
      </div>

      {data && <Report data={data} />}
    </main>
  );
}

function Report({ data }: { data: GradeResponse }) {
  const { result, meta } = data;
  const p = result.price_band;
  return (
    <div className="card">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <div className="row">
          <div className={`grade-badge grade-${result.cosmetic_grade}`}>
            {result.cosmetic_grade}
          </div>
          <div>
            <div style={{ fontWeight: 600 }}>
              {result.device.detected_brand_model || "Unidentified device"}
            </div>
            <div className="muted" style={{ fontSize: 13 }}>
              {result.device.detected_category} · ID confidence{" "}
              {result.device.identification_confidence}
            </div>
          </div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div className="muted" style={{ fontSize: 12 }}>
            Est. resale
          </div>
          <div className="price">
            {p.low.toLocaleString()}–{p.high.toLocaleString()} {p.currency}
          </div>
        </div>
      </div>

      <p style={{ marginTop: 14 }}>{result.grade_rationale}</p>

      <h2 style={{ marginTop: 18 }}>
        Defects {result.defects.length > 0 ? `(${result.defects.length})` : ""}
      </h2>
      {result.defects.length === 0 ? (
        <p className="muted">No visible defects found.</p>
      ) : (
        result.defects.map((d, i) => (
          <div className="defect" key={i}>
            <div className="row" style={{ justifyContent: "space-between" }}>
              <strong>
                {d.region} · {d.type.replace(/_/g, " ")}
              </strong>
              <span className={`sev ${d.severity}`}>{d.severity}</span>
            </div>
            <div className="muted" style={{ fontSize: 14 }}>
              {d.description} {d.location_hint && `— ${d.location_hint}`}
            </div>
          </div>
        ))
      )}

      {result.resale.recommended_actions.length > 0 && (
        <>
          <h2 style={{ marginTop: 18 }}>To improve resale</h2>
          <ul className="muted" style={{ marginTop: 0 }}>
            {result.resale.recommended_actions.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        </>
      )}

      <p className="muted" style={{ fontSize: 13, marginTop: 16 }}>
        {result.confidence_note}
      </p>

      <p className="meta">
        Graded by {meta.modelId} · {meta.latencyMs} ms ·{" "}
        {meta.inputTokens + meta.outputTokens} tokens · ~$
        {meta.estimatedCostUsd.toFixed(4)}
      </p>
    </div>
  );
}
