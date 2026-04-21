import { NextRequest, NextResponse } from "next/server";

const FASTAPI_BASE_URL = process.env.FASTAPI_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL;

export async function POST(request: NextRequest) {
  if (!FASTAPI_BASE_URL) {
    return NextResponse.json(
      { detail: "FASTAPI_BASE_URL is not configured." },
      { status: 500 }
    );
  }

  try {
    const body = await request.json();
    const upstream = await fetch(`${FASTAPI_BASE_URL}/send-report`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
    });

    const payload = await upstream.json();
    return NextResponse.json(payload, { status: upstream.status });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Failed to proxy send report request.";
    return NextResponse.json({ detail: message }, { status: 500 });
  }
}
