# Cast Premium Auth

**Bundled QUILL Quillin** — `com.quill.castpremiumauth`

The reference implementation of the `feed_auth_providers` contribution model
(the `podcast.feed.auth` capability) introduced for cross-app Quillins. It runs
only in **Quill Cast** (`targets: ["cast"]`).

## What it does

Some podcast networks put premium/subscriber shows behind an authenticated
feed. This Quillin supplies the `Authorization` header for feeds hosted on
`premium.example.com` (and its subdomains), so those shows can refresh and
download in Quill Cast just like any other subscription.

It is **declarative and host-mediated**: the Quillin declares the hosts it can
authenticate (`match_hosts`) and a handler that returns a header string. The
QUILL host attaches that header to the feed request — the Quillin makes no
network call of its own and needs no `net` capability (least privilege).

## How it works

- `contributes.feed_auth_providers` declares the provider `id`, its
  `match_hosts`, and the `handler` name.
- The handler (`feed_auth_header`) reads a token from the Quillin's own storage
  (`api_token`, falling back to a demo token) and writes the resulting
  `Bearer <token>` header back to storage under the result key the host reads.
- `quill.core.podcasts.feed_auth.auth_header_for_url` consults the registered
  providers first, then falls back to the built-in per-show HTTP Basic path.

## Capabilities

- `podcast.feed.auth` — contribute a feed authentication provider.
- `storage` — read the API token and return the computed header.

## License

MIT. See `LICENSE`.
