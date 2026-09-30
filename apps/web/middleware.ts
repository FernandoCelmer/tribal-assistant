import { NextResponse, type NextRequest } from "next/server";

const MUTATING = new Set(["POST", "PUT", "PATCH", "DELETE"]);
const PROXIED = ["/api/v1/", "/docs", "/openapi.json"];

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;

  if (pathname === "/health") return NextResponse.rewrite(new URL(`${apiBase()}/health`));

  if (pathname.startsWith("/api/v1/") && MUTATING.has(request.method)) {
    const source = request.headers.get("origin") ?? request.headers.get("referer");
    const host = request.headers.get("x-forwarded-host") ?? request.headers.get("host");
    if (source && host && !sameHost(source, host)) return NextResponse.json({ detail: "requisição de outra origem recusada" }, { status: 403 });
  }

  if (PROXIED.some((prefix) => pathname.startsWith(prefix))) {
    const headers = new Headers(request.headers);
    headers.delete("authorization");
    return NextResponse.rewrite(new URL(`${apiBase()}${pathname}${search}`), { request: { headers } });
  }

  return NextResponse.next();
}

export const config = { runtime: "nodejs", matcher: ["/((?!_next/static|_next/image|favicon.ico|icon.svg).*)"] };

function sameHost(source: string, host: string): boolean {
  try {
    return new URL(source).host === host;
  } catch {
    return false;
  }
}

function apiBase(): string {
  return (process.env.TRIBAL_API ?? "http://127.0.0.1:8000").replace(/\/$/, "");
}
