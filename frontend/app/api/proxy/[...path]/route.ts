import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";
const API_KEY = process.env.API_KEY ?? "";

type RouteParams = { params: Promise<{ path: string[] }> };

async function proxy(req: NextRequest, { params }: RouteParams): Promise<NextResponse> {
  const { path } = await params;
  const search = req.nextUrl.search;
  const backendUrl = `${BACKEND_URL}/api/${path.join("/")}${search}`;

  const hasBody = !["GET", "HEAD", "DELETE"].includes(req.method);
  const body = hasBody ? await req.text() : undefined;

  let res: Response;
  try {
    res = await fetch(backendUrl, {
      method: req.method,
      headers: {
        "Content-Type": "application/json",
        "x-api-key": API_KEY,
      },
      body,
      cache: "no-store",
    });
  } catch {
    return NextResponse.json({ detail: "Backend inaccessible" }, { status: 503 });
  }

  const text = await res.text();
  return new NextResponse(text, {
    status: res.status,
    headers: { "Content-Type": "application/json" },
  });
}

export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
