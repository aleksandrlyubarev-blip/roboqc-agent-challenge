import { NextResponse } from "next/server";

import { createUploadUrl, isAllowedImageType } from "@/lib/storage/s3";

export const runtime = "nodejs";

export async function POST(req: Request): Promise<NextResponse> {
  let body: { contentType?: string; sessionId?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid JSON body" }, { status: 400 });
  }

  if (!isAllowedImageType(body.contentType ?? "")) {
    return NextResponse.json(
      { error: "contentType must be image/jpeg, image/png or image/webp" },
      { status: 400 },
    );
  }
  if (!body.sessionId) {
    return NextResponse.json({ error: "sessionId is required" }, { status: 400 });
  }

  try {
    const { key, url } = await createUploadUrl(body.contentType!, body.sessionId);
    return NextResponse.json({ key, url });
  } catch (err) {
    return NextResponse.json(
      { error: `failed to create upload URL: ${(err as Error).message}` },
      { status: 500 },
    );
  }
}
