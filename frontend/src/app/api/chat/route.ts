import { cookies } from "next/headers";

export async function POST(request: Request) {
  const { conversation_id, messages } = await request.json();

  const cookieStore = await cookies();
  const token = cookieStore.get("auth_token")?.value;

  if (!token) {
    const response = new Response(JSON.stringify({ error: "Unauthorized" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
    response.headers.set("Set-Cookie", "auth_token=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0");
    return response;
  }

  const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";

  const res = await fetch(`${backendUrl}/api/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ conversation_id, messages }),
  });

  if (!res.ok) {
    const response = new Response(JSON.stringify({ error: "Backend request failed" }), {
      status: res.status,
      headers: { "Content-Type": "application/json" },
    });
    if (res.status === 401) {
      response.headers.set("Set-Cookie", "auth_token=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0");
    }
    return response;
  }

  return new Response(res.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
