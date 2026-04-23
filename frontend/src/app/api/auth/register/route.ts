export async function POST(request: Request) {
  const { username, password } = await request.json();

  const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";

  const res = await fetch(`${backendUrl}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  const data = await res.json();

  if (!res.ok) {
    return Response.json(
      { error: data.detail || "注册失败" },
      { status: res.status }
    );
  }

  const response = Response.json(data);
  response.headers.set(
    "Set-Cookie",
    `auth_token=${data.access_token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=${7 * 24 * 60 * 60}`
  );

  return response;
}
