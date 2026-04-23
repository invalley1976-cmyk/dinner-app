// Cloudflare Pages Function: /api/state
// GET  -> returns saved state JSON
// POST -> replaces saved state (body = JSON)

const KEY = "main";
const EMPTY_STATE = {
  users: [],
  schedule: {},
  parentMemo: {},
  urgentCancels: []
};

export async function onRequestGet({ env }) {
  const row = await env.DB
    .prepare("SELECT v, updated_at FROM kv WHERE k = ?")
    .bind(KEY)
    .first();
  const data = row ? JSON.parse(row.v) : EMPTY_STATE;
  return new Response(JSON.stringify({ value: JSON.stringify(data), updatedAt: row?.updated_at ?? 0 }), {
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" }
  });
}

export async function onRequestPost({ env, request }) {
  const body = await request.text();
  try { JSON.parse(body); } catch { return new Response("invalid json", { status: 400 }); }
  const now = Date.now();
  await env.DB
    .prepare(
      "INSERT INTO kv (k, v, updated_at) VALUES (?, ?, ?) " +
      "ON CONFLICT(k) DO UPDATE SET v = excluded.v, updated_at = excluded.updated_at"
    )
    .bind(KEY, body, now)
    .run();
  return new Response(JSON.stringify({ ok: true, updatedAt: now }), {
    headers: { "content-type": "application/json; charset=utf-8" }
  });
}
