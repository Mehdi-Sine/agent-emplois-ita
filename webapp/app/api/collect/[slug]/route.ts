import { NextResponse } from "next/server";

import { dispatchCollectWorkflow } from "@/lib/github-dispatch";

type Params = {
  params: Promise<{ slug: string }>;
};

export async function POST(_: Request, context: Params) {
  try {
    const { slug } = await context.params;

    if (!slug) {
      return NextResponse.json({ ok: false, error: "Missing slug." }, { status: 400 });
    }

    const result = await dispatchCollectWorkflow({ source: slug });

    return NextResponse.json(
      {
        ok: true,
        message: `Targeted run dispatched for ${slug}.`,
        result,
      },
      { status: 202 },
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json({ ok: false, error: message }, { status: 500 });
  }
}
