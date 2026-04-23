import { cookies } from "next/headers";

const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";

async function getAuthToken() {
  const cookieStore = await cookies();
  return cookieStore.get("auth_token")?.value;
}

function unauthorizedResponse() {
  return new Response(JSON.stringify({ error: "Unauthorized" }), {
    status: 401,
    headers: { "Content-Type": "application/json" },
  });
}

export async function GET() {
  const token = await getAuthToken();
  if (!token) return unauthorizedResponse();

  const res = await fetch(`${backendUrl}/api/conversations`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  return new Response(await res.text(), {
    status: res.status,
    headers: { "Content-Type": res.headers.get("Content-Type") || "application/json" },
  });
}

export async function POST() {
  const token = await getAuthToken();
  if (!token) return unauthorizedResponse();

  const res = await fetch(`${backendUrl}/api/conversations`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });

  return new Response(await res.text(), {
    status: res.status,
    headers: { "Content-Type": res.headers.get("Content-Type") || "application/json" },
  });
}
