"use client";

import { useEffect, useState } from "react";

import { Report } from "@/components/Report";
import type { InspectionMeta } from "@/lib/inspection/client";
import type { InspectionReport } from "@/lib/inspection/schema";

type Phase = "move_in" | "move_out";
type Status = "idle" | "creating" | "uploading" | "inspecting";

interface ReportData {
  sessionId: string;
  report: InspectionReport;
  meta: InspectionMeta;
}

function userId(): string {
  if (typeof window === "undefined") return "anonymous";
  let id = window.localStorage.getItem("depositshield_uid");
  if (!id) {
    id = crypto.randomUUID();
    window.localStorage.setItem("depositshield_uid", id);
  }
  return id;
}

export default function Home() {
  const [propertyLabel, setPropertyLabel] = useState("");
  const [phase, setPhase] = useState<Phase>("move_out");
  const [context, setContext] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [previews, setPreviews] = useState<string[]>([]);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<ReportData | null>(null);

  useEffect(() => () => previews.forEach((u) => URL.revokeObjectURL(u)), [previews]);

  function onSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const picked = Array.from(e.target.files ?? []).slice(0, 12);
    setFiles(picked);
    setPreviews(picked.map((f) => URL.createObjectURL(f)));
    setData(null);
    setError(null);
  }

  async function uploadOne(file: File, sessionId: string): Promise<string> {
    const res = await fetch("/api/upload-url", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ contentType: file.type, sessionId }),
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

  async function run() {
    if (files.length === 0) return;
    setError(null);
    setData(null);
    try {
      setStatus("creating");
      const sRes = await fetch("/api/sessions", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ propertyLabel, phase, userId: userId() }),
      });
      const sJson = await sRes.json();
      if (!sRes.ok) throw new Error(sJson.error ?? "could not create session");
      const sessionId: string = sJson.sessionId;

      setStatus("uploading");
      const photoKeys = await Promise.all(files.map((f) => uploadOne(f, sessionId)));

      setStatus("inspecting");
      const rRes = await fetch(`/api/sessions/${sessionId}/report`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ photoKeys, context }),
      });
      const rJson = await rRes.json();
      if (!rRes.ok) throw new Error(rJson.error ?? "inspection failed");
      setData({ sessionId, report: rJson.report, meta: rJson.meta });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setStatus("idle");
    }
  }

  const busy = status !== "idle";
  const label =
    status === "creating"
      ? "Creating session…"
      : status === "uploading"
        ? "Uploading photos…"
        : status === "inspecting"
          ? "Inspecting…"
          : "Inspect & draft report";

  return (
    <main>
      <div className="brand">
        <h1>
          Deposit<span className="mark">Shield</span>
        </h1>
      </div>
      <p className="tagline">
        Photograph a rental at move-in or move-out — get a structured condition report.
      </p>
      <p className="disclaimer">
        DepositShield organizes visual evidence and drafts a condition report. It is not legal
        advice and makes no promise about deposit recovery.
      </p>

      <div className="card">
        <label className="field" htmlFor="label">
          Property
        </label>
        <input
          id="label"
          type="text"
          placeholder="e.g. 12 Herzl St, Apt 4"
          value={propertyLabel}
          onChange={(e) => setPropertyLabel(e.target.value)}
        />

        <label className="field" htmlFor="phase">
          Inspection phase
        </label>
        <select id="phase" value={phase} onChange={(e) => setPhase(e.target.value as Phase)}>
          <option value="move_in">Move-in</option>
          <option value="move_out">Move-out</option>
        </select>

        <label className="field" htmlFor="photos">
          Photos (room by room — up to 12)
        </label>
        <input id="photos" type="file" accept="image/*" multiple onChange={onSelect} />
        {previews.length > 0 && (
          <div className="thumbs">
            {previews.map((src) => (
              // eslint-disable-next-line @next/next/no-img-element
              <img key={src} className="thumb" src={src} alt="property" />
            ))}
          </div>
        )}

        <label className="field" htmlFor="context">
          Optional context (known issues, currency, lease notes)
        </label>
        <input
          id="context"
          type="text"
          placeholder="e.g. wall scuff was present at move-in"
          value={context}
          onChange={(e) => setContext(e.target.value)}
        />

        <div style={{ marginTop: 16 }}>
          <button className="primary" onClick={run} disabled={busy || files.length === 0}>
            {label}
          </button>
        </div>
        {error && <p className="error">⚠ {error}</p>}
      </div>

      {data && (
        <>
          <Report report={data.report} meta={data.meta} propertyLabel={propertyLabel} phase={phase} />
          <div className="card">
            <div className="sharebar">
              <strong>Shareable evidence report:</strong>
              <a href={`/r/${data.sessionId}`} target="_blank" rel="noreferrer">
                /r/{data.sessionId}
              </a>
            </div>
          </div>
        </>
      )}
    </main>
  );
}
