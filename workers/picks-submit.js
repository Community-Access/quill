/*
 * picks-submit: the receiver that lets anybody suggest a station with no
 * GitHub account, from quillforall.org.
 *
 * GitHub Pages is static. It serves files and cannot accept a submission, so
 * something has to receive the POST and hold a credential that can write to
 * the repo -- and that credential can never live in the public page, because
 * the page is readable by everyone. This is that something: about eighty lines
 * on Cloudflare Workers' free tier.
 *
 * DEPLOY
 * ------
 *   npx wrangler deploy workers/picks-submit.js --name picks-submit
 *   npx wrangler secret put GITHUB_TOKEN     # fine-grained PAT, Issues: write
 *   npx wrangler secret put TURNSTILE_SECRET # optional, see below
 *
 * Then set SUBMIT_URL in docs/site/picks/suggest/suggest.js to the deployed
 * URL. Nothing else changes: the form, its validation and the issue body are
 * already shared with the in-app dialog.
 *
 * ON SPAM CONTROL
 * ---------------
 * If you add a challenge, use Cloudflare Turnstile and NOT reCAPTCHA.
 * Turnstile is usually invisible and needs no puzzle; reCAPTCHA's image grids
 * are exactly the barrier this whole project exists to remove. A spam control
 * that locks out blind users to keep out bots has failed at the only job that
 * matters here. Turnstile is optional below -- without the secret, the rate
 * limit alone applies.
 */

const REPO = "Community-Access/quill";
const LABEL = "pick:suggestion";
const MAX_BODY = 8000;
const MAX_TITLE = 200;

// One suggestion per IP per minute, and twenty a day. A bad afternoon then
// costs a handful of closed issues rather than a repo full of them.
const PER_MINUTE = 1;
const PER_DAY = 20;

export default {
  async fetch(request, env) {
    const cors = {
      "Access-Control-Allow-Origin": "https://quillforall.org",
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    };
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: cors });
    }
    if (request.method !== "POST") {
      return json({ error: "POST only" }, 405, cors);
    }

    let payload;
    try {
      payload = await request.json();
    } catch {
      return json({ error: "that was not JSON" }, 400, cors);
    }

    const title = String(payload.title || "").trim().slice(0, MAX_TITLE);
    const body = String(payload.body || "").trim().slice(0, MAX_BODY);
    if (!title || !body) {
      return json({ error: "a title and a body are required" }, 400, cors);
    }
    // The body must carry the machine-readable block, or approving it later
    // would publish nothing. Refusing here keeps the review queue honest.
    if (!body.includes("```json pick")) {
      return json({ error: "that submission is not in the expected shape" }, 400, cors);
    }

    if (env.TURNSTILE_SECRET && !(await turnstileOk(payload.turnstile, env, request))) {
      return json({ error: "could not verify that you are a person" }, 400, cors);
    }

    const ip = request.headers.get("CF-Connecting-IP") || "unknown";
    if (env.PICKS_RATE && !(await withinRate(env.PICKS_RATE, ip))) {
      return json({ error: "too many suggestions just now; try again shortly" }, 429, cors);
    }

    const response = await fetch(`https://api.github.com/repos/${REPO}/issues`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.GITHUB_TOKEN}`,
        Accept: "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "picks-submit (quillforall.org)",
      },
      body: JSON.stringify({ title, body, labels: [LABEL] }),
    });
    if (!response.ok) {
      return json({ error: "GitHub would not accept it just now" }, 502, cors);
    }
    const issue = await response.json();
    return json({ ok: true, number: issue.number }, 200, cors);
  },
};

function json(value, status, headers) {
  return new Response(JSON.stringify(value), {
    status,
    headers: { ...headers, "Content-Type": "application/json" },
  });
}

async function turnstileOk(token, env, request) {
  if (!token) {
    return false;
  }
  const form = new FormData();
  form.append("secret", env.TURNSTILE_SECRET);
  form.append("response", token);
  form.append("remoteip", request.headers.get("CF-Connecting-IP") || "");
  const verify = await fetch(
    "https://challenges.cloudflare.com/turnstile/v0/siteverify",
    { method: "POST", body: form }
  );
  const outcome = await verify.json().catch(() => ({}));
  return Boolean(outcome.success);
}

async function withinRate(store, ip) {
  // PICKS_RATE is an optional KV namespace. Without it the Worker still works;
  // it simply does not rate-limit, which is fine while volumes are small.
  const minuteKey = `m:${ip}:${Math.floor(Date.now() / 60000)}`;
  const dayKey = `d:${ip}:${new Date().toISOString().slice(0, 10)}`;
  const [minute, day] = await Promise.all([store.get(minuteKey), store.get(dayKey)]);
  if (Number(minute || 0) >= PER_MINUTE || Number(day || 0) >= PER_DAY) {
    return false;
  }
  await Promise.all([
    store.put(minuteKey, String(Number(minute || 0) + 1), { expirationTtl: 120 }),
    store.put(dayKey, String(Number(day || 0) + 1), { expirationTtl: 86400 }),
  ]);
  return true;
}
