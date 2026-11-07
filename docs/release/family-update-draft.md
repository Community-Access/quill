# QUILL family update: draft announcement

**Draft for review, not a release announcement.** The changes below are in the
working tree or are plans; product packages and release dates must be verified
before this text is published.

## QUILL and QUILL Lite: payment form authoring

Both editors share Stripe/PayPal payment setup, insertion and site readiness
checks. New forms start in test mode; paid-form publication checks mode and
provider/webhook readiness. Responses display, refresh and export payment
metadata. Actual checkout requires QAF payment contract version 1 on WordPress.
Provider credentials and money movement stay there. No plugin deployment,
live payment acceptance or published package is implied by this draft.

## QUILL and Quill Radio

The shared Radio code retires its built-in SomaFM source in response to
SomaFM's published terms for third-party clients. Known catalogue entries and
direct playback and recording paths are filtered or blocked. Review of
indirect paths, existing user data and previously published packages is still
open. The change is not a new public release.

QUILL no longer downloads or distributes a legacy voice engine while its
redistribution terms are unclear. Separately installed copies still work;
complete removal, previous packages and other distribution paths need review.
New Studio portable builds copy only the supported speech engine folders.

## QUILL Lite and the shared Windows runtime

The shared Windows OCR and Media projections move to PyWinRT 4.0.3 and the
Windows SDK 10.0.28000.2705 projection line. This includes the Windows OCR
path used by QUILL and QUILL Lite, and Windows Media paths used by Radio and
Studio. Device references and player event handlers are released at shutdown
to address a Windows Media exit crash. This is a runtime change, not a promise
of new functionality or publication of any product update.

## QUILL and QUILL Lite: Choose Your AI

Both editors get one window for where their AI comes from, **Choose Your AI**
(Ctrl+4): QUILL's free AI, a ChatGPT plan, GitHub Copilot, Codex, or your own
key, which now covers OpenAI, Google Gemini, Anthropic Claude, OpenRouter,
Ollama Cloud, a custom OpenAI-compatible service and Ollama on your own
computer. **Which AI Am I Using** (Ctrl+8) says which one is answering. Signing
out of the one in use leaves no AI in use until you choose; nothing switches
by itself. On Copilot or Codex, **Do a Document Task** (Ctrl+3) carries out a
job with several steps and asks before every change. Saved prompts become one
list shared by the family. GitHub Copilot sign-in shows "not available yet"
until the builds carry each app's GitHub registration, and Codex needs the
engine in the shared runtime; both must be confirmed in the staged packages
before this paragraph is published.

## QUILL Studio and Quill Converter

Studio already offers shared audio conversion and offline caption generation
for supported audio and video. Its consolidated production plan proposes
accessible project-to-Converter round trips, capability checks, batch review
and richer local or explicitly consented cloud transcription and AI assistance.
These proposed workflows are not a claim that the features have shipped.
Converter support depends on the available codecs and valid media; no
guarantee is made for every format or protected file.

## Release and legal checks

Installed editions of QUILL, QUILL Lite, Radio, Cast, Studio, Weather, Inkwell,
Converter, Transcribe, Beacon and Social use the shared QuillVille Runtime.
The current runtime carries PyMuPDF 1.28.2 under AGPL-3.0. Only QUILL exposes
the GLOW feature that brings it in; the other apps carry it in the runtime.
Media Player uses its host's runtime. Standalone portable packages leave GLOW,
and with it PyMuPDF, out.

The exact source of PyMuPDF, and of every other GPL, LGPL or AGPL part, is
published with each release beside LICENSE.txt and THIRD-PARTY-NOTICES.txt.
Before publishing this draft, update the product-specific release notes and
check the actual staged packages.
