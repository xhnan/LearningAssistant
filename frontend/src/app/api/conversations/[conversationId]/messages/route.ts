import { cookies } from "next/headers";

const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";

async function getAuthToken() {
  const cookieStore = await cookies();
  return cookieStore.get("auth_token")?.value;
}

function unauthorizedResponse() {
  const response = new Response(JSON.stringify({ error: "Unauthorized" }), {
    status: 401,
    headers: { "Content-Type": "application/json" },
  });
  response.headers.set("Set-Cookie", "auth_token=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0");
  return response;
}

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ conversationId: string }> }
) {
  const token = await getAuthToken();
  if (!token) return unauthorizedResponse();

  const { conversationId } = await params;
  const res = await fetch(`${backendUrl}/api/conversations/${conversationId}/messages`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  const body = res.status === 204 || res.status === 304 ? null : await res.text();
  const response = new Response(body, {
    status: res.status,
    headers: { "Content-Type": res.headers.get("Content-Type") || "application/json" },
  });
  if (res.status === 401) {
    response.headers.set("Set-Cookie", "auth_token=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0");
  }
  return response;
}
