import { NextResponse } from "next/server";

import { dispatchCollectWorkflow } from "@/lib/github-dispatch";

export async function POST() {
  try {
    const result = await dispatchCollectWorkflow();
    return NextResponse.json(
      {
        ok: true,
        message: "Global run dispatched.",
        result,
      },
      { status: 202 },
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json({ ok: false, error: message }, { status: 500 });
  }
}
