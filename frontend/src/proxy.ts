import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Optimistic auth check: without a session cookie, go to /login.
// The real check happens in Django on every /api request (401 -> client redirects).
export function proxy(request: NextRequest) {
  if (!request.cookies.has("sessionid")) {
    const url = new URL("/login", request.url);
    const next = request.nextUrl.pathname + request.nextUrl.search;
    if (next !== "/") url.searchParams.set("next", next);
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  // Pages only: never API calls (large PDF uploads must not be buffered), assets or the login page.
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|login).*)"],
};
