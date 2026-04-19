export async function POST(request: Request) {
  const { messages } = await request.json();

  const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";

  const res = await fetch(`${backendUrl}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages }),
  });

  if (!res.ok) {
    return new Response(JSON.stringify({ error: "Backend request failed" }), {
      status: res.status,
      headers: { "Content-Type": "application/json" },
    });
  }

  return new Response(res.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
