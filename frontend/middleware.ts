import { NextRequest, NextResponse } from "next/server";

const DISABLED_ROUTES = ["/chat", "/accessibility"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (DISABLED_ROUTES.some((route) => pathname === route || pathname.startsWith(route + "/"))) {
    return NextResponse.redirect(new URL("/", request.url));
  }

  const token = request.cookies.get("token")?.value;
  const isLoginPage = pathname === "/login";

  if (isLoginPage && token) {
    return NextResponse.redirect(new URL("/", request.url));
  }

  if (!isLoginPage && !token) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)"],
};
