import { NextResponse } from "next/server";

import { getSessionBundle } from "@/lib/db/dynamo";

export const runtime = "nodejs";

export async function GET(
  _req: Request,
  ctx: { params: Promise<{ id: string }> },
): Promise<NextResponse> {
  const { id } = await ctx.params;
  try {
    const bundle = await getSessionBundle(id);
    if (!bundle) return NextResponse.json({ error: "session not found" }, { status: 404 });
    return NextResponse.json(bundle);
  } catch (err) {
    return NextResponse.json(
      { error: `failed to load session: ${(err as Error).message}` },
      { status: 500 },
    );
  }
}
