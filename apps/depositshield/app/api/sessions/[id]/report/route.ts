import { NextResponse } from "next/server";

import { addPhotoEvents, getSessionMeta, putReport } from "@/lib/db/dynamo";
import { InspectionError, inspectCondition } from "@/lib/inspection/client";
import { fetchImage } from "@/lib/storage/s3";

export const runtime = "nodejs";
// Fable 5 inspection can take 10–30s at high effort.
export const maxDuration = 60;

export async function POST(
  req: Request,
  ctx: { params: Promise<{ id: string }> },
): Promise<NextResponse> {
  const { id } = await ctx.params;

  let body: { photoKeys?: string[]; context?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid JSON body" }, { status: 400 });
  }

  const photoKeys = body.photoKeys ?? [];
  if (photoKeys.length === 0) {
    return NextResponse.json({ error: "photoKeys must not be empty" }, { status: 400 });
  }
  if (photoKeys.length > 12) {
    return NextResponse.json({ error: "at most 12 photos per session" }, { status: 400 });
  }

  const session = await getSessionMeta(id);
  if (!session) return NextResponse.json({ error: "session not found" }, { status: 404 });

  let images;
  try {
    images = await Promise.all(photoKeys.map(fetchImage));
  } catch (err) {
    return NextResponse.json(
      { error: `could not load photos: ${(err as Error).message}` },
      { status: 400 },
    );
  }

  try {
    await addPhotoEvents(id, photoKeys);
    const { report, meta } = await inspectCondition(images, session.phase, body.context);
    const stored = await putReport(id, report, meta);
    return NextResponse.json({ sessionId: id, ...stored });
  } catch (err) {
    if (err instanceof InspectionError) {
      return NextResponse.json({ error: err.message }, { status: 503 });
    }
    return NextResponse.json(
      { error: `inspection failed: ${(err as Error).message}` },
      { status: 500 },
    );
  }
}
