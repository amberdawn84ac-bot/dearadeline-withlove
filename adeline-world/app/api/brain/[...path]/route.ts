import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const brainUrl = process.env.BRAIN_URL;
  if (!brainUrl) {
    return NextResponse.json({ error: "Brain connection is not configured." }, { status: 503 });
  }

  const { path } = await context.params;
  const target = new URL(path.join("/"), `${brainUrl.replace(/\/$/, "")}/`);
  target.search = request.nextUrl.search;

  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  const authorization = request.headers.get("authorization");
  if (contentType) headers.set("content-type", contentType);
  if (authorization) headers.set("authorization", authorization);

  try {
    const upstream = await fetch(target, {
      method: request.method,
      headers,
      body: request.method === "GET" || request.method === "HEAD" ? undefined : await request.text(),
      cache: "no-store",
      signal: AbortSignal.timeout(120_000),
    });
    const responseHeaders = new Headers();
    const upstreamType = upstream.headers.get("content-type");
    if (upstreamType) responseHeaders.set("content-type", upstreamType);
    const cacheControl = upstream.headers.get("cache-control");
    if (cacheControl) responseHeaders.set("cache-control", cacheControl);
    const buffering = upstream.headers.get("x-accel-buffering");
    if (buffering) responseHeaders.set("x-accel-buffering", buffering);

    return new NextResponse(upstream.body, {
      status: upstream.status,
      headers: responseHeaders,
    });
  } catch {
    return NextResponse.json({ error: "Adeline's Brain is temporarily unavailable." }, { status: 502 });
  }
}

export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
