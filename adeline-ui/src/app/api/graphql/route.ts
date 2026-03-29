/**
 * /api/graphql — Hygraph CMS data gateway
 *
 * This route is the ONLY place in adeline-ui that calls Hygraph directly.
 * The browser never sees HYGRAPH_TOKEN or HYGRAPH_ENDPOINT.
 *
 * Supported operations (query only — no mutations from client):
 *   GetTrackPage(track)              → TrackPage with units + lesson stubs
 *   GetLessonStubs(track, gradeBand) → LessonStub[]
 *   GetDailyBread(date)              → DailyBread
 *   GetResourceLinks(track)          → ResourceLink[]
 *
 * All operations are cached at the Next.js ISR layer (60s revalidation).
 * POST-only. GET requests are rejected.
 */

import { NextRequest, NextResponse } from "next/server";
import {
  getTrackPage,
  getLessonStubsByTrack,
  getDailyBread,
  getResourceLinks,
  type Track,
} from "@/lib/hygraph/client";

// ── Allowed operation names (allowlist — never pass arbitrary queries to Hygraph)

type AllowedOperation =
  | "GetTrackPage"
  | "GetLessonStubs"
  | "GetDailyBread"
  | "GetResourceLinks";

const ALLOWED_OPERATIONS = new Set<AllowedOperation>([
  "GetTrackPage",
  "GetLessonStubs",
  "GetDailyBread",
  "GetResourceLinks",
]);

// ── Request body shape ────────────────────────────────────────────────────────

interface GraphQLGatewayRequest {
  operation: AllowedOperation;
  variables?: {
    track?: Track;
    gradeBand?: string;
    date?: string;
  };
}

// ── Route handler ─────────────────────────────────────────────────────────────

export async function POST(req: NextRequest): Promise<NextResponse> {
  let body: GraphQLGatewayRequest;

  try {
    body = await req.json() as GraphQLGatewayRequest;
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const { operation, variables = {} } = body;

  if (!ALLOWED_OPERATIONS.has(operation)) {
    return NextResponse.json(
      { error: `Unknown operation: ${operation}` },
      { status: 400 },
    );
  }

  try {
    switch (operation) {
      case "GetTrackPage": {
        if (!variables.track) {
          return NextResponse.json({ error: "track is required" }, { status: 422 });
        }
        const data = await getTrackPage(variables.track);
        return NextResponse.json({ data });
      }

      case "GetLessonStubs": {
        if (!variables.track) {
          return NextResponse.json({ error: "track is required" }, { status: 422 });
        }
        const data = await getLessonStubsByTrack(variables.track, variables.gradeBand);
        return NextResponse.json({ data });
      }

      case "GetDailyBread": {
        const date = variables.date ?? new Date().toISOString().split("T")[0];
        const data = await getDailyBread(date);
        return NextResponse.json({ data });
      }

      case "GetResourceLinks": {
        if (!variables.track) {
          return NextResponse.json({ error: "track is required" }, { status: 422 });
        }
        const data = await getResourceLinks(variables.track);
        return NextResponse.json({ data });
      }
    }
  } catch (e) {
    const message = e instanceof Error ? e.message : "Unknown CMS error";
    console.error(`[/api/graphql] ${operation} failed:`, e);
    return NextResponse.json({ error: message }, { status: 502 });
  }
}

// Reject GET — this is not a public GraphQL endpoint
export function GET(): NextResponse {
  return NextResponse.json(
    { error: "This endpoint accepts POST only. See /api/graphql." },
    { status: 405 },
  );
}
