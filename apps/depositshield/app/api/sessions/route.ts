import { randomUUID } from "node:crypto";

import { NextResponse } from "next/server";

import { createSession, listSessionsByUser, type Phase } from "@/lib/db/dynamo";

export const runtime = "nodejs";

export async function POST(req: Request): Promise<NextResponse> {
  let body: { propertyLabel?: string; phase?: Phase; userId?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid JSON body" }, { status: 400 });
  }

  const phase: Phase = body.phase === "move_out" ? "move_out" : "move_in";
  const session = {
    id: randomUUID(),
    userId: body.userId?.trim() || "anonymous",
    propertyLabel: body.propertyLabel?.trim() || "Untitled property",
    phase,
    status: "created" as const,
    createdAt: new Date().toISOString(),
  };

  try {
    await createSession(session);
    return NextResponse.json({ sessionId: session.id, session });
  } catch (err) {
    return NextResponse.json(
      { error: `failed to create session: ${(err as Error).message}` },
      { status: 500 },
    );
  }
}

export async function GET(req: Request): Promise<NextResponse> {
  const userId = new URL(req.url).searchParams.get("userId")?.trim() || "anonymous";
  try {
    const sessions = await listSessionsByUser(userId);
    return NextResponse.json({ sessions });
  } catch (err) {
    return NextResponse.json(
      { error: `failed to list sessions: ${(err as Error).message}` },
      { status: 500 },
    );
  }
}
