import { randomUUID } from "node:crypto";

import { NextResponse } from "next/server";

import { GradingError, gradeDevice } from "@/lib/grading/client";
import { putGrading } from "@/lib/db/dynamo";
import { fetchImage } from "@/lib/storage/s3";

export const runtime = "nodejs";
// The grading call can take 10–30s at high effort; give the function room.
export const maxDuration = 60;

interface GradeBody {
  photoKeys?: string[];
  deviceHint?: string;
  userId?: string;
}

export async function POST(req: Request): Promise<NextResponse> {
  let body: GradeBody;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid JSON body" }, { status: 400 });
  }

  const photoKeys = body.photoKeys ?? [];
  if (photoKeys.length === 0) {
    return NextResponse.json({ error: "photoKeys must not be empty" }, { status: 400 });
  }
  if (photoKeys.length > 8) {
    return NextResponse.json({ error: "at most 8 photos per grading" }, { status: 400 });
  }

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
    const { result, meta } = await gradeDevice(images, body.deviceHint);
    const record = {
      id: randomUUID(),
      userId: body.userId?.trim() || "anonymous",
      createdAt: new Date().toISOString(),
      deviceHint: body.deviceHint?.trim() || null,
      photoKeys,
      result,
      meta,
    };
    await putGrading(record);
    return NextResponse.json({ id: record.id, result, meta });
  } catch (err) {
    if (err instanceof GradingError) {
      return NextResponse.json({ error: err.message }, { status: 503 });
    }
    return NextResponse.json(
      { error: `grading failed: ${(err as Error).message}` },
      { status: 500 },
    );
  }
}
