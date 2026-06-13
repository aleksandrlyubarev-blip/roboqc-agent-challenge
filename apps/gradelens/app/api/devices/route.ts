import { NextResponse } from "next/server";

import { listGradingsByUser } from "@/lib/db/dynamo";

export const runtime = "nodejs";

export async function GET(req: Request): Promise<NextResponse> {
  const userId = new URL(req.url).searchParams.get("userId")?.trim() || "anonymous";
  try {
    const records = await listGradingsByUser(userId);
    return NextResponse.json({ records });
  } catch (err) {
    return NextResponse.json(
      { error: `failed to list gradings: ${(err as Error).message}` },
      { status: 500 },
    );
  }
}
