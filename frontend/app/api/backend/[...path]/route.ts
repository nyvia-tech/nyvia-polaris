import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = (process.env.BACKEND_URL || 'http://localhost:8000').trim().replace(/\/$/, '');

async function proxy(req: NextRequest, params: { path: string[] }) {
  const path = params.path.join('/');
  const url = `${BACKEND_URL}/${path}/`;

  console.log(`[proxy] ${req.method} ${url}`);

  let body: string | undefined;
  if (req.method !== 'GET') {
    body = await req.text();
  }

  let response: Response;
  try {
    response = await fetch(url, {
      method: req.method,
      headers: { 'Content-Type': 'application/json' },
      body,
      signal: AbortSignal.timeout(60_000), // 60s para el cold start de Render
    });
  } catch (err) {
    console.error(`[proxy] fetch failed:`, err);
    return NextResponse.json(
      { detail: 'No se pudo conectar con el backend. Intenta en unos segundos.' },
      { status: 503 }
    );
  }

  let data: unknown;
  try {
    data = await response.json();
  } catch {
    const text = await response.text();
    console.error(`[proxy] response no es JSON:`, text);
    return NextResponse.json(
      { detail: 'El backend devolvió una respuesta inesperada.' },
      { status: 502 }
    );
  }

  return NextResponse.json(data, { status: response.status });
}

export async function GET(req: NextRequest, { params }: { params: { path: string[] } }) {
  return proxy(req, params);
}

export async function POST(req: NextRequest, { params }: { params: { path: string[] } }) {
  return proxy(req, params);
}
