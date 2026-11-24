const BACKEND_URL = process.env.AUTH_BACKEND_URL || 'http://127.0.0.1:8000';

function resultPage(message: string, success: boolean, status: number) {
  const color = success ? '#047857' : '#b91c1c';
  const html = `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Email verification</title>
  </head>
  <body style="margin:0;min-height:100vh;display:grid;place-items:center;background:#fff;font-family:Arial,sans-serif;padding:24px;box-sizing:border-box">
    <p role="status" style="margin:0;text-align:center;color:${color};font-size:18px;font-weight:600">${message}</p>
  </body>
</html>`;

  return new Response(html, {
    status,
    headers: { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store' },
  });
}

export async function GET(request: Request) {
  const token = new URL(request.url).searchParams.get('token')?.trim();
  if (!token) {
    return resultPage('Verification link is missing or invalid.', false, 400);
  }

  try {
    const response = await fetch(`${BACKEND_URL}/api/auth/verify-email`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token }),
      cache: 'no-store',
    });

    if (!response.ok) {
      return resultPage('Verification link is invalid or expired. Request a new link.', false, response.status);
    }

    return resultPage('You are successfully verified.', true, 200);
  } catch {
    return resultPage('Could not verify right now. Make sure the app is running on your PC and try again.', false, 503);
  }
}
