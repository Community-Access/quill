# QUILL family update: draft announcement

**Draft for review, not a release announcement.** The changes below are in the
working tree or are plans; product packages and release dates must be verified
before this text is published.

## Starting minimized and WinGet

QUILL, Radio, Cast, Weather, Inkwell and Transcribe gain a separate choice to
start minimized when Windows starts. It is available alongside each app's
existing Start with Windows control and does not change an ordinary launch.
The app stays available from its tray icon. Portable copies do not create
startup entries. QUILL Transcribe still presents required first-run setup and
does not begin dictation at login.

WinGet manifests are prepared locally for the currently published Stable
installers of QUILL Lite 1.1.2 and Quill Radio 3.0.4. No package has been
submitted or accepted. The package IDs are proposals; public install
instructions and availability claims must wait until IDs are approved and the
catalog pull requests merge. See the [deployment guide](../planning/winget.md),
the [family user guide](../user%20guide/quill-family-startup-and-winget-guide.md), and
the [release-note draft](./family-startup-winget-release-draft.md).

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

## QUILL and QUILL Lite: WordPress, and forms

Both editors now write and publish WordPress posts and pages. You connect a
site with your browser, write in the editor you already use, and choose when
anything goes to the site: Ctrl+S stays on your computer, Save Draft to Site
sends a draft, and Publish or Update checks the page first and names the page
and the site before it asks. Save Draft on a post that is already published
now asks first. Pictures ask for their alternative text, posts can be
scheduled, earlier versions come back, and nothing someone else changed is
overwritten.

Around the writing, the comments, categories and tags, people, menus and Media
Library are all in the WordPress Workbench. Menus gain Add Menu Item, Add New
Pages Automatically and Arrange Items, and a Media Library row has Replace
File, which keeps the address where the site allows it and otherwise points
every use at the new file. The Workbench itself does most of what you would go
to wp-admin for, and says plainly where it cannot. From the page you are
writing, This Post in the Workbench opens your post's list with it selected,
and Insert > Picture from the Media Library lets you pick a picture there with
Enter. Every change shows a preview first, Ctrl+Z takes it back, and fields
that hold a secret are masked. Each site gains Site Health information and
security checks, a check for updates on WordPress.org, a content audit,
privacy request pointers and an Administration Areas list, and wp-admin for
This Place reaches the plugins' own screens. A site's AI abilities can be
offered to Ask the Site one at a time.

For moving content, Tools > WXR Files exports a site as WXR and imports one as
drafts. Across sites you can rename or merge a value everywhere, check every
link, make sites the same, copy to another site, put a site back from a
snapshot, and run a plain-language batch you check item by item. Where
WordPress's REST API cannot update or switch something, the row says so and
Open in Dashboard takes you to wp-admin. The Practice Site runs only on your
own computer and has three tutorials in QUILL.

The plugins come next. Gravity Forms gets feeds, results, entry notes,
resending notifications and test entries; Paid Memberships Pro gets discount
codes, access checks and membership changes with a preview of what stops;
redirects and the 404 log come from Redirection.

Forms are written as plain text in the QAF language, checked, filled in by
you with your screen reader, and then published to a site running QUILL
Accessible Forms or saved as a web page, large print or braille. Last, payment
forms: both editors share Stripe and PayPal payment setup, insertion and site
readiness checks. New forms start in test mode, and paid-form publication
checks mode and provider and webhook readiness. Responses display, refresh and
export payment metadata. Actual checkout requires QAF payment contract version
1 on WordPress, and provider credentials and money movement stay there. No
plugin deployment, live payment acceptance or published package is implied by
this draft.

None of the Workbench has been run against a live site or with a screen reader
yet; both come before this is published.

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
