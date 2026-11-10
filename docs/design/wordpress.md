# WordPress in QUILL and QUILL Lite

The accepted product scope is now the [WordPress Workbench PRD](../Product%20Requirement%20Documents%20and%20Specifications/wordpress-workbench-prd.md).
This document preserves the earlier publishing plan and implementation log;
the current code status, plugin scope, and remaining work are recorded in the
[Workbench implementation status](../planning/workbench-implementation-status.md).

Payment integration remains governed by the current
[implementation notes](forms-payments-design.html) and
[QAF plugin contract](forms-payments-plugin-contract.html): provider
credentials and checkout stay plugin-owned.

## 1. What this is

Write, open, edit and publish WordPress pages and posts, and manage the site's
Media Library, from inside QUILL and QUILL Lite, with every editor tool still
in reach: Find, Replace, spelling, dictation, Read Aloud, bookmarks, the
Markdown and HTML tools, Choose Your AI.

This is not a site builder and does not touch the theme. The site keeps its
look; we work on the content inside it.

Three rules shape every decision in this document:

1. **Simple first.** A person who only wants to post a weekly news item should
   need three things: connect once, write, publish. Everything else is there
   when wanted and invisible when not. No command needs AI.
2. **Many sites.** Multiple sites are a requirement, not an extra. Every
   document knows which site it belongs to, and every confirmation names it.
3. **Both kinds of WordPress.** Self-hosted sites and WordPress.com sites work
   the same way from the user's side. Only the Connect step differs.

Nothing reaches a public site without a deliberate Publish or Update, and
nothing is ever deleted for good without a local copy first.

## 2. What already exists (2026-11-03)

QUILL has a publishing framework, built and tested, but mostly switched off:

- `quill/core/publishing.py`, `publishing_clients.py`,
  `publishing_providers.py`: saved connections (several, with one marked
  current), the application password in Windows Credential Manager, an
  HTTPS-only endpoint policy (`_validate_endpoint_security`), and these
  operations: verify, browse pages and posts by status, load, compare, create,
  update, publish and schedule. The client speaks `/wp-json/wp/v2`.
- `quill/core/publishing_linkage.py` remembers which local file came from
  which remote item.
- `quill/ui/publishing_tools.py` and `main_frame_publishing.py`: the
  Connections, Edit Connection, Browse and Schedule dialogs, plus a Publish
  submenu in `main_frame_menu.py`.
- **Gates:** `future.publishing_read` (connect, browse, open) is on only in
  the Full Quill profile. `future.publishing` (anything that sends) is
  `locked_off=True`.
- **QUILL Lite** has no publishing. `quill/apps/lite.py` says so on purpose,
  and this PRD changes that (section 11).

**Missing:**

- categories and tags;
- slug, excerpt and featured image;
- the Media Library;
- Trash;
- a conflict check: `modified_gmt` is fetched and never compared;
- local drafts and previous versions;
- Open by Web Address;
- WordPress.com;
- any of it in QUILL Lite.

## 3. Who it is for

- **The weekly poster:** a business or community group posting news. Needs
  New Post, a category and Publish.
- **The page fixer:** someone sent a link and one sentence is wrong. Needs
  Open by Web Address, Find and Update.
- **The site keeper:** looks after two or five sites, for work and for
  volunteering. Needs the site switcher, drafts that stay with their site,
  and the Media Library.
- **The writer:** long posts, many images. Needs alt text help, a check
  before publishing, and previous versions.

## 4. Connecting a site

### 4.1 One dialog, three fields

Connect a WordPress Site asks for:

- the site address;
- the username;
- the application password.

There is also a name field for the site, which defaults to the site's own
title once the connection is verified. Connect verifies before it saves, and
says exactly what was wrong if it fails:

- wrong password;
- not HTTPS;
- the REST API is blocked by a security plugin;
- the account lacks the role.

### 4.2 No copying passwords where WordPress allows it

WordPress 5.6 and later has an Authorize Application screen
(`/wp-admin/authorize-application.php`). It can hand the new application
password straight back to the app, with no copy and paste.

- QUILL opens that page in the default browser and listens on a one-time
  local loopback address for the reply.
- **What WordPress accepts (researched 2026-11-03):**
  - Core changeset r62096 (24 March 2026, ticket #57809) allows a plain
    `http://` `success_url` on the loopback addresses `127.0.0.1` and
    `[::1]`, on any site. Before it, plain http was accepted only on sites
    marked as a local environment (WordPress 6.2), so most live sites
    refused it.
  - `localhost` is still refused on purpose: RFC 8252 section 8.3 warns
    about it.
  - **Not yet confirmed:** which release ships r62096. Check the WordPress
    7.0 field guide before building.
- **Decision:** the flow works in three tiers, all automatic. The user only
  ever presses Connect.
  1. QUILL asks the site its version, from the REST index the client already
     reads. On a version that has r62096, it uses
     `http://127.0.0.1:<random port>/wordpress-done` with a one-time `state`.
     The password arrives by itself. QUILL saves it, verifies the
     connection, and says "Connected to Site Name".
  2. On an older site it uses no `success_url` at all. WordPress then shows
     the new password on its own page with a Copy button. QUILL's dialog
     waits on a single Paste field: "Copy the password WordPress is showing
     you, then come back and paste it here." The clipboard is checked when
     the dialog gets focus back, and a password-shaped value (24 characters
     in groups of four) is offered: "Use the password you just copied?"
  3. If the authorize screen is turned off (a security plugin, or
     `wp_is_application_passwords_available` false), Connect says so in
     plain words. It offers the manual route through the profile page.
  - Never `https://` to a page of ours that relays the password. A relay we
    run would be a place a password passes through, and nothing needs it.

A "Get an application password" button opens the profile page's Application
Passwords section, for sites where the authorize flow is turned off.

### 4.3 WordPress.com

- WordPress.com sites use OAuth through
  `public-api.wordpress.com/oauth2-1/authorize`. Content is served by
  `https://public-api.wordpress.com/wp/v2/sites/<site>/...`, which is the
  same `wp/v2` shape the client already speaks, under a different base URL
  with a bearer token.
- The user chooses "WordPress.com" in Connect, presses Sign In, approves in
  the browser, and picks the site or sites to add. One sign-in can add every
  site that account manages, each as its own connection.
- WordPress.com sites on plans that allow plugins also accept an application
  password on their own domain. If the user types such an address, the
  self-hosted path works and we don't argue.
- **What WordPress.com accepts (researched 2026-11-03):**
  - Its OpenID configuration
    (`public-api.wordpress.com/.well-known/openid-configuration`) advertises
    an OAuth 2.1 endpoint pair: `/oauth2-1/authorize` and `/oauth2-1/token`.
  - It supports `response_types_supported: ["code"]`,
    `code_challenge_methods_supported: ["S256"]` and
    `token_endpoint_auth_methods_supported` including `"none"`, plus
    `refresh_token` grants.
  - Scopes include `sites`, `posts`, `media`, `taxonomy`, `comments` and
    `global`.
  - The older `/oauth2/` docs describe the implicit grant
    (`response_type=token`) as deprecated, with tokens lasting from 18 hours
    to two weeks.
- **For everyone (Jeff, 2026-11-04).** WordPress.com sign-in has to work for
  every person on every WordPress.com plan, the free one included, without
  plugins and without anyone registering anything. That is why it runs through
  QUILL's own registered WordPress.com app: Jeff registers it once, the client
  id ships in every build, and each person signs in with their own
  WordPress.com account. The application-password route on a site's own
  address stays available for plugin plans, but it is never the only way in.
- **Decision:** use the authorization code flow with PKCE (S256) as a public
  client, with token auth `none`.
  - No client secret ships in the installer, and none is needed.
  - Do not use the implicit grant.
  - Ask for `sites posts media taxonomy comments`, not `global`: the
    narrowest scopes that cover everything in this PRD, and what the consent
    screen shows the user.
  - Keep the refresh token in Credential Manager. Renew silently, so the
    user signs in once, not every two weeks.
  - If a refresh fails, say "Sign in to WordPress.com again" and offer Sign
    In. Never fail silently on a publish.
- **Redirect:** register `http://127.0.0.1/wordpress-done` (loopback, any
  port, per RFC 8252) when creating the app.
  - **Not yet confirmed:** whether WordPress.com's Applications Manager
    accepts a loopback redirect, and whether it matches any port or needs
    exact ports. Test with the real app registration before building.
  - **If loopback is refused:** register one `https://` page on the QUILL
    site, `docs/site/wordpress-done.html`. A static page, it shows the
    one-time code with a Copy button and "Paste this into QUILL". The code
    alone is useless without the PKCE verifier, which never leaves the
    computer, so the page handles nothing secret. Static hosting on GitHub
    Pages means no server of ours.
- **Still to verify against a live site:** that the `wp/v2/sites/<site>/media`
  and `/block-types` routes behave as they do on a self-hosted site. Every
  endpoint the client uses gets a recorded fixture from a WordPress.com test
  site.
- **Our side (Jeff):**
  - Register a WordPress.com app under Community Access, at
    `developer.wordpress.com/apps`. It needs a name, a description, the
    redirect above, and the "public client" or native type if offered.
  - Give Claude the client id. It is not a secret and goes in settings.
  - Keep a free WordPress.com test site for the fixtures.

### 4.4 Many sites

- **The Sites list** is the existing Connections dialog, simplified. It
  offers:
  - Add;
  - Rename;
  - Verify;
  - Remove (the connection only, never the site's content);
  - Make Default.
- **Switch Site** is one key. It opens a short list and the choice is spoken.
- **The default site** is where New Page and New Post go, and what Open
  browses. Every dialog that touches a site has a Site combo box at the top,
  defaulting to the default site, so nobody has to switch first.
- **An open document belongs to its site for life.** Switching the default
  never moves it. The status bar and Document Properties say "WordPress: Site
  Name, Draft".
- **Confirmations name the site and the item:** "Publish 'Spring Workshop' to
  Community Radio?". This matters most when the same title exists on two
  sites.

## 5. Pages and posts

### 5.1 New Page, New Post

A small dialog asks for:

- the site;
- the title;
- Markdown or HTML (default from the last choice, Markdown first time);
- the slug (the last part of the page's address), filled in from the title
  as it is typed. Leave it alone to keep the suggestion.

For a post it also asks for categories and tags. The excerpt and everything
else live in Properties and are not asked up front. Creating it sends
nothing.

**The format is fixed once the document is created.** A Markdown document
never later gets read as HTML, or the other way round, so nothing on the
page is quietly reinterpreted. Markdown is turned into HTML only when it is
sent. Preview in Browser shows the result at any time.

The title is kept apart from the body, because the theme prints it. The body
starts with the first paragraph, not a Heading 1.

### 5.2 Open

**Open Page or Post** has these controls:

- site;
- type;
- status (Published, Drafts, Pending, Scheduled, Private, Trash);
- a search field.

The list reads "title, status, last changed". Enter opens the item. Paging is
automatic as the list is walked; there is no More button.

**Open by Web Address** works like this:

- Paste any link to a page or post, or press it with a link already on the
  clipboard.
- QUILL finds which saved site it belongs to and opens the item. That might
  not be the default site.
- If no saved site matches, it offers to connect that site.
- If the item is already open, it switches to that tab instead of opening a
  second copy.

**Existing items** open as HTML, with WordPress's block comments
(`<!-- wp:paragraph -->`) kept intact, so the block editor still sees blocks
afterwards. This is the safe default.

- Open as Markdown is a choice in the dialog, with a plain warning that block
  layout is not kept.
- A Markdown document QUILL created stays Markdown. QUILL keeps the Markdown
  source locally, keyed by site and id, so reopening it gives back Markdown,
  not converted HTML.

### 5.3 Saving, three separate actions

| Action | Key | What happens |
| --- | --- | --- |
| Save | Ctrl+S | A local working copy only. Never sends. |
| Save Draft to Site | (assigned) | An unpublished draft on the site. |
| Publish or Update | (assigned) | Asks once, naming site and title, then publishes. |

- Closing a WordPress document never publishes it.
- Local drafts are kept automatically. Open Local Draft lists them by site.
- A Private or Scheduled item keeps that status on Update.

After Publish, the page address is spoken and placed on the clipboard. Open on
Site opens it in the browser at any time.

### 5.4 Conflict protection

Before every Update, QUILL re-reads the item's `modified_gmt`. If someone else
changed the site copy since it was opened, nothing is sent. The user is told
who changed it and when, and offered three choices:

- Compare (the existing compare, both ways);
- Open the Site Copy;
- Send Mine Anyway, which asks a second time.

### 5.5 Properties

One dialog (Alt+Enter on a WordPress document) holds:

- title, slug, status and excerpt;
- categories and tags (the post only);
- the featured image (section 6.4);
- whether comments are open;
- the read-only facts: the site, the address, the author and when it last
  changed.

Each field has its own F1 help.

**Categories and tags:**

- one checkable list each, with a search field above it;
- each item says "checked" or "not checked";
- "New Category" and "New Tag" create one on the site when the account is
  allowed to;
- a summary line reads "2 categories, 3 tags".

### 5.6 Trash and versions

**Move to Trash:**

- Works from the open document or from the Open list.
- It is WordPress's Trash, never permanent deletion.
- A local copy is kept, and Trash is a status in Open, so it comes back.

**Previous Versions:**

- Lists newest first. Each row has the date, the title and the reason, such
  as:
  - "Opened from site";
  - "Saved";
  - "Site copy before update";
  - "Before AI change";
  - "Before restore".
- Before restoring, View opens a version's full text and its properties (the
  title, slug, status, categories and tags) in a read-only window. From there
  you can copy one paragraph instead of restoring all of it.
- Restore puts the version in the editor. It never publishes.
- Where the account can read them, the site's own revisions
  (`/wp/v2/<type>/<id>/revisions`) appear in the same list, marked "On the
  site". That makes this a true history, not just what QUILL happened to
  keep.

### 5.7 The whole editor, and finding commands

A WordPress document is an ordinary QUILL document. Nothing about the editor
is reduced for it. All of these work exactly as they do anywhere else:

- Find, and Find and Replace;
- heading and structure navigation;
- select, cut, copy and paste, and Change Case;
- the spelling and grammar checker;
- dictation;
- AutoCorrect and abbreviations;
- bookmarks and document notes;
- the Markdown and HTML insert tools: headings, links, email links, lists,
  tables and images;
- several documents open at once, from one site or several, and Compare;
- Read Aloud.

**Finding commands:**

- File > WordPress lists them all.
- The Command Palette, in QUILL and QUILL Lite alike, finds any of them by
  typing "WordPress" or part of a command's name. Every WordPress command is
  in it, with its key beside its name.

### 5.8 Scheduling

Schedule Publish already exists in the publishing core. It goes into File >
WordPress beside Publish or Update. It asks for the date, time and time zone,
confirms with the site and the title, and the item then shows as Scheduled in
Open. Change Schedule and Publish Now work on a scheduled item.

### 5.9 After publishing

- **Draft addresses need a sign-in:** a draft's address only works for
  someone signed in to WordPress. QUILL says so when it copies one:
  "Draft address copied. It needs a WordPress sign-in to open."
- **Adding a new page to a menu:** publishing a new page does not add it to
  the site's menus. After a new page is published, QUILL offers, once, "Add
  it to a menu?". That opens the Menus window (9.9) at the right place. The
  question can be turned off.

### 5.10 When things go wrong

Every failure is spoken with its reason and the next step. The common ones:

| What happened | What QUILL says and offers |
| --- | --- |
| The password was refused | It names the account and site. It offers to check that the application password belongs to that account, and Reconnect. |
| Connected, but an action was refused | It names the role and what that role cannot do (9.2). |
| A page cannot be found | It suggests checking the site, the type, the status and the search. Open always loads every page of results, so "more results" is never the cause. |
| A save was not confirmed | The local draft stays. QUILL re-reads the site before it offers Try Again, so nothing is created twice. |
| An upload was not confirmed | QUILL checks the Media Library for the file before it offers to upload again (6.2). |
| The site copy changed | Conflict protection (5.4). |
| Visual Review missed a change | It says the page may be a cached copy and suggests checking that the update finished (6.11). |
| A security plugin blocks the API | It says so plainly, and says what to ask the site's administrator for. |

**Page builders:** content made with a page builder is protected. That
includes Elementor, Divi and WPBakery, and shortcodes. It opens as islands
(8.1), editable as text where the builder stores text and otherwise kept
byte for byte. QUILL names the builder, and says that layout changes belong
in the builder.

## 6. Media Library

This is a first-class window, not a file picker.

### 6.1 Browse

The **Media Library** window:

- **opens with:** one key from any WordPress document or from the menu.
- **site:** chosen by a Site combo at the top.
- **controls:**
  - a search field;
  - a type filter (Images, Audio, Video, Documents, All);
  - an "Only unattached" check box.
- **each row reads:** title, type, size in pixels for images, file size,
  alt text or "no alt text", upload date.
- **paging:** automatic.
- **the details pane** shows, read-only:
  - the address;
  - the caption;
  - the description;
  - what it is attached to;
  - **Used In:** the pages and posts whose content links to this file,
    found by searching for its address. The search is slow, so it runs on
    request with a progress announcement.

### 6.1a Listen and watch (Jeff, 2026-11-04)

An audio or video file in the Media Library can be played without leaving
QUILL, so you can check what a file is before you insert it, remove it, or
write its transcript.

- **Play:** on an audio or video row, Play (or **Enter** on the row) opens a
  small player window. It uses the shared transport panel that QUILL and
  Quill Media Player already use, so the keys are the familiar ones:
  - play and pause;
  - stop;
  - back and forward;
  - Go to Position;
  - speed;
  - volume;
  - the position and length, on request.
- **Video:** plays its sound and shows the picture. If the site has a
  captions track for it, Captions reads the current caption on request.
- **Streamed, not saved:** the file streams from its address on the site,
  over HTTPS. Nothing is downloaded unless you choose Download.
- **Other ways to play it:**
  - Open in Quill Media Player, for chapters, bookmarks and resume;
  - Open in Browser.
- **In a document:** Play Media Here plays the audio or video block at the
  caret.
- **The same in both editors**, through the shared module.

### 6.2 Upload

- **Ways to upload:**
  - one or many files from the computer;
  - an image on the clipboard;
  - a file from a web address.
- **Before upload:** each file gets its title, alt text, caption and a
  Decorative check box. The alt text field is the focus first for an image.
- **During upload:** progress is spoken per file. A failed file says why, and
  the rest carry on.
- **No duplicates:** if the same file (same name and size) is already in the
  library, QUILL asks "Use the one already there?" before uploading a second.

### 6.3 Edit and remove

- **Edit Details:** changes title, alt text, caption and description on the
  site.
- **Remove from Library:**
  - **Confirm first:** names the file and the site, and says how many pages
    use it, if Used In has run.
  - **Back up first:** WordPress media has no Trash, so removal is
    permanent. QUILL downloads a copy to a local "Removed from Site Name"
    folder first, and the confirmation says so.
  - **Many at once:** several files can be chosen and removed together, with
    one confirmation that gives the count.
- **Download:** saves a copy locally.
- **Copy Address:** puts the file's address on the clipboard.

### 6.4 Attach and insert

- **Insert Picture from This Computer:** one command, from any WordPress
  document.
  - **Choose the file:** a standard Open dialog.
  - **Then the image dialog opens (6.7), with everything:**
    - alt text, with Suggest;
    - Decorative;
    - caption;
    - display width;
    - Use as Featured Image;
    - Link to;
    - Describe Image.
  - **Insert:** uploads the file with its title, alt text and caption, then
    places it at the caret. Upload progress is spoken, and so is the
    outcome: "Picture inserted: Volunteers at the spring fair".
  - **No duplicates:** if the same file is already in the library, QUILL
    offers to reuse it instead of uploading again (6.2).
  - **Offline, or before the document is on the site:** the picture is
    inserted from the local file straight away, with all its settings. It
    is marked "not uploaded yet" in the document, in Where Am I and in Check
    Before Publishing. On Save Draft to Site or Publish, QUILL uploads every
    local picture first, swaps each local path for its library address, and
    keeps each one's alt text, caption, width and featured-image choice. A
    page never reaches the site pointing at a file on the writer's computer.
  - Pictures dropped or pasted in (below) go through the same path.
- **Insert into Document:**
  - places the image at the caret, as Markdown or HTML to match the document;
  - a figure with alt text and caption;
  - an optional display width;
  - for audio and video, the matching block markup.
- **Alt text is per placement:** changing it in the document changes that
  occurrence only, never the library item everywhere.
- **Attach to This Page or Post:** sets the media item's parent. This is
  WordPress's own sense of "attached", which galleries and some themes use.
  It is separate from inserting.
- **Set as Featured Image:** works from the library, from the document's
  Properties, or from an inserted image. "Remove Featured Image" sits beside
  it.
- **Pasting an image** into a WordPress document offers to upload it and
  insert it, alt text first.

### 6.5 Image size, and file size

These are two different things, kept as two separate commands:

- **Image Size:** the width the image is shown at. Proportions are kept,
  nothing is cropped, and it changes only the markup.
- **Make a Smaller Copy:**
  - Pillow is already in the runtime, so this happens on the computer.
  - Choose a maximum width and a format.
  - Before and after, it reports pixels and file size.
  - Upload and Use replaces only this occurrence. The original stays in the
    library.

### 6.6 Every image capability, in one place

This is the full list of what working with images must do. Every row is
required. Sections 6.7 to 6.11 hold the detail.

| Capability | Where |
| --- | --- |
| Upload a file and insert it at the caret | 6.2, 6.4 |
| Reuse an image already in the library, with no duplicate upload | 6.2, 6.4 |
| The insert dialog has alt text, caption, Decorative and Use as Featured Image | 6.7 |
| Library rows give title, dimensions, alt, caption and address | 6.1 |
| Alt text is per placement, not per library item | 6.4 |
| Suggest Alt Text, editable, never saved by itself | 6.8 |
| Describe Image, a longer appraisal for the user | 6.8 |
| Make a new picture from a description, in three shapes and three backgrounds | 6.9 |
| Suggest a picture from the page content | 6.9 |
| Image Size, with a preview and a way back to the earlier size | 6.5, 6.7 |
| A smaller copy, with a before-and-after report and a description of the result | 6.5 |
| The site logo resized, previewed first, reversible and conflict-safe | 6.10 |
| Visual Review of the public page on desktop and phone, image by image | 6.11 |
| Preview and Review of a proposed size before it is applied | 6.11 |
| A check of the library before re-uploading after an unconfirmed upload | 6.2 |

### 6.7 The image dialog

Inserting an image, by upload or from the library, opens one dialog. In tab
order:

1. **Alternative text**, an edit field, with Suggest beside it (6.8).
2. **Decorative**, a check box. Checked, it empties and disables the alt text
   field and writes `alt=""`. Its help says what decorative means: the image
   adds nothing a visitor needs.
3. **Caption**, an edit field. Visible text for credits, names and context.
4. **Display width**, a combo box offering:
   - Full width;
   - the theme's content width;
   - Half;
   - a number of pixels.

   It always keeps the proportions. The image's real size is said beside it:
   "Image is 2400 by 1600".
5. **Use as Featured Image**, a check box.
6. **Link to**, a combo box: nothing, the file, or an address. Choosing an
   address turns the alt text label into "Alternative text (say where the
   link goes)", because a linked image's alt text is the link's name.
7. Describe Image, Insert and Cancel.

**Image Size** on an inserted image opens the same dialog at that image,
showing:

- the current width;
- the proposed width, with "Preview on the Page" (6.11);
- "Back to Earlier Size". QUILL keeps each placement's earlier widths in the
  document's local history, so this works after a save, not only within one
  session.

### 6.8 Alt text and descriptions

There are three image reports, kept apart because they answer three different
questions. Each one's help says which question it answers.

| Report | Who it is for | Question |
| --- | --- | --- |
| Suggest Alt Text | visitors using a screen reader | What does this picture contribute here? |
| Describe Image | the person writing | What is actually in this picture, and is it any good? |
| Visual Review | the person writing | How does this picture sit on the real page? |

**Suggest Alt Text:**

- **What it sends:** the image, the heading above it, the paragraphs either
  side, the caption, and the link target if there is one.
- **The instruction it gives the AI asks for:**
  - one or two sentences on the image's purpose, not its pixels;
  - visible text read out exactly;
  - no "image of";
  - no invented names. If a person is shown and the page does not name them,
    the suggestion says "a person" and the field's help says to add the name
    if it matters.
- **Charts and diagrams:** for a chart or a diagram it proposes short alt text
  and offers "Add a Fuller Description After the Image", a paragraph inserted
  below for the user to edit.
- **Decorative images:** when the image looks decorative (a divider, a
  texture), it says so and suggests the Decorative check box rather than
  inventing words.
- **The result is only a proposal:** it lands in the field, selected, ready
  to be replaced or corrected. It is never saved on its own.

**Describe Image** works on any library item, any inserted image, any
generated picture and any smaller copy. It gives a longer report, which opens
in a read-only text window with Copy and Save:

- the subject;
- the arrangement;
- the colours and lighting;
- any visible text, quoted;
- the mood;
- problems: awkward cropping, distorted hands or faces, garbled lettering, a
  crowded composition, low resolution for its size.

It always looks at the actual file, never at the description it was made
from. That is the existing Studio rule: "a separate look by the vision
model".

**Beyond:** an **Alt Text Review** for the whole document. It lists every
image with its current alt text, marks the empty, the filename-like
("IMG_2041.jpg") and the suspiciously long, and offers Suggest on each, one
at a time.

### 6.9 Making a picture

The Picture Maker that Audio Studio already has (`quill/core/ai/image_generation.py`,
`quill/ui/studio_picture_maker.py`) moves to the shared `quill/ui/` layer. It
follows the same pattern as the hosted AI, so QUILL, QUILL Lite and Studio all
reach one implementation.

- **The description:** one edit field, with the help suggesting what to
  include: the subject, the style, the colours, the arrangement, the
  background and anything to avoid.
- **Shape:** Square, Landscape or Portrait. These are the existing
  `IMAGE_SIZES`.
- **Background:**
  - **Normal.**
  - **Solid colour,** with a colour name chosen from the site's theme palette
    (8.4).
  - **Transparent.** Offered only when the provider can make one: OpenAI
    image models can and Imagen cannot. When it cannot, the option is
    missing rather than failing later, and its help says why.
- **Make the Picture:**
  - It asks first, naming the provider and model, as Studio does today.
  - It saves the file on the computer only. It never uploads and never
    changes the page.
  - A Describe Image report on the result opens at once.
- **The versions list:** every version is kept, each with its description.
  "Change Description" goes back to the description with the conversation so
  far, and Make the Picture again adds a version.
- **On a chosen version:**
  - Describe Image;
  - Open in Image Viewer;
  - Save As;
  - Make a Smaller Copy (6.5);
  - Insert into Document, which opens the image dialog (6.7) with the
    upload done on Insert.
- **Suggest from Page Content:**
  - The AI reads the page, or the selection, and proposes three things: a
    description, a shape and a background, with one sentence on why the
    picture would suit the content.
  - All three land in the Picture Maker's fields, editable, and nothing is
    made until Make the Picture.
- **An honest rule:** a generated picture is an illustration, never a
  screenshot. If the description asks for an application's screen, menu or
  dialog, the Picture Maker says once, plainly, that a real screenshot is the
  right thing for a reader who needs to see real controls, and goes ahead if
  asked again.

### 6.10 The site logo

The site logo is the theme's logo on every page, not an image in one post,
so changes to it are previewed first and always reversible.

- **Find it:** Site Logo reads the standard `site_logo` setting
  (`/wp/v2/settings`) and the media item behind it, and says:
  - the file;
  - its real size;
  - the width the theme shows it at, measured on the public page (6.11).
- **Another kind of logo:** if the theme uses a header image or a page
  builder's own logo instead, Site Logo says so and stops. That one belongs to
  the theme's own controls.
- **Propose a width,** then Preview on the Page:
  - QUILL renders the public home page at desktop and phone widths, with the
    logo at the proposed width.
  - The rendering is done by injecting a style into the captured page, so
    nothing on the site changes.
  - A Visual Review report on the two views opens.
- **Apply to Site:**
  - It is available only after a preview has succeeded.
  - It confirms, naming the site, the old width and the new width.
  - Then it makes a resized copy (with Pillow), uploads it, and sets it as
    `site_logo`.
  - The original media item is never touched or removed.
- **Restore Earlier Logo:** lists the logos QUILL has set, newest first, each
  with its size and date.
- **Conflict-safe:** before Apply and before Restore, QUILL re-reads
  `site_logo`. If someone changed it since the preview, nothing is sent, and
  the user is told.
- **It needs the right permission:** the `manage_options` capability. Without
  it, the command says so and nothing more.

### 6.11 Visual Review

Visual Review tells a blind site owner what a sighted visitor sees, image by
image. It moves here from section 10, because most of what it reports is
about images.

- **Capture:**
  - The installed Microsoft Edge, or Chrome when Edge is missing, captures
    the public page at a desktop width (1366) and a phone width (390). It
    runs in headless mode with the DevTools protocol.
  - There is no browser window to manage, and the default browser is not
    changed.
  - Progress is spoken: "Capturing the phone view".
  - **What is measured, from the live page:**
    - every image's displayed width and height;
    - whether it overflows the content area;
    - whether it loaded, partly loaded or failed;
    - its position relative to the nearest heading;
    - its existing alt text.

    These are facts, gathered by the browser, not guessed by the AI.
- **Report:**
  - The AI gets both screenshots, the page text and the measurements.
  - It writes:
    - an overall impression;
    - the desktop layout;
    - the phone layout;
    - spacing and balance;
    - what works well;
    - then one entry per image: where it is ("below Individual Training"),
      the measured size on each view, the existing alt text, a fresh
      description of what is shown, and whether it suits the text around it.
  - Each finding is labelled as one of three kinds:
    - **"likely a problem"**;
    - **"a design choice you may want"**;
    - **"worth checking"**.
  - The report opens in a read-only text window, with Copy and Save as Text.
- **From report to fix:**
  - Each image entry with a size suggestion has "Try This Width". That opens
    Image Size (6.7) at that image, with the width filled in.
  - After the user Updates the page, "Review Again" reruns the review on the
    same views.
- **Preview and Review:**
  - This version reviews a proposed change without publishing it. It
    captures the current public page with a proposed image width or logo
    width injected as a style, and reports on that.
  - It is how Image Size and Site Logo preview.
  - What it cannot preview is unpublished text, and it says so.
- **Honest about what it saw:**
  - It reviews the public page only. If the document has unpublished
    changes, it says "This reviews the page as published. Your unpublished
    changes are not in it."
  - It separates "the image failed to load", "the image had not finished
    loading" and "this part of the page was not captured", rather than
    calling an image broken.
  - If the captured page is older than the last Update, it says the site may
    be serving a cached copy.
- **What it sends:** the screenshots, the page text and the measurements, to
  the AI chosen in Choose Your AI, after the usual consent. Capturing itself
  sends nothing anywhere except a normal visit to the public page.

### 6.12 What each image action sends

| Action | Sends | To |
| --- | --- | --- |
| Upload, Edit Details, Remove, Site Logo apply | the file or the fields | the site |
| Image Size, Make a Smaller Copy | nothing | (on the computer) |
| Suggest Alt Text | the image and nearby text | the chosen AI |
| Describe Image | the image | the chosen AI |
| Make the Picture | the description | the chosen image provider |
| Suggest from Page Content | the page or selection text | the chosen AI |
| Visual Review, Preview and Review | screenshots, page text, measurements | the chosen AI |

Reducing a file is always local. Asking for a description of the smaller copy
is a separate choice.

## 7. Check Before Publishing

Publish runs a short check and speaks the result in one line, for example
"Ready to publish: no problems found" or "2 things to look at". The list then
opens, and each item jumps to its place in the document.

The checks:

- an image with no alt text that is not marked decorative;
- a link with no text, or a link to a page on this site that does not exist;
- a heading that skips a level, or a Heading 1 in the body (the theme already
  shows the title);
- an empty title;
- the document belongs to a different site than the default, with the site
  named;
- the site copy changed since opening (section 5.4).

None of these blocks publishing. "Publish Anyway" is always there. The check
is fast and runs locally, except the link check, which only reads the site.

## 8. Blocks, made plain

The block editor is where most WordPress sites now keep their layout: buttons,
columns, galleries, call-outs, accordions, embeds, and patterns the site owner
designed. In a browser it is a drag-and-drop canvas full of floating
toolbars, and it is one of the hardest parts of WordPress to use with a
screen reader.

QUILL does it differently. A block is just a piece of the document with a
name, and every action on it is a command, a list or a form. Nothing is
dragged and nothing floats.

### 8.1 What a block looks like in QUILL

The idea is that **ordinary writing is ordinary writing**. A paragraph is a
paragraph, a heading is a heading, and a list is a list.

- **Ordinary blocks need no markup.** The core blocks that map onto something
  QUILL already has are written the way they always are, as Markdown or HTML:
  paragraph, heading, list, quote, image, table, separator, code and
  preformatted. QUILL adds and removes the block comments
  (`<!-- wp:heading {"level":2} -->`) itself, on open and on send. The user
  never sees or types one.
- **Other blocks are fences, in Markdown.** Anything else is written as a
  readable fence. That is the same `:::` syntax QUILL already uses for page
  breaks and divs, so there is one idea to learn, not two:

  ```
  ::: button "Book a session" https://example.org/book

  ::: columns
  ::: column
  Morning sessions run from nine.
  ::: column
  Evening sessions run from six.
  ::: end columns

  ::: details "What does it cost?"
  The first session is free.
  ::: end details
  ```

- **HTML documents** keep the real block markup, but QUILL folds each block
  comment into one spoken line: "Button block: Book a session". Arrowing
  never makes the user read JSON.
- **A block QUILL does not know is an island.** A plugin's block, a complex
  gallery or a form shows as one protected line, for example "Contact form
  block (from a plugin), press Enter for its settings". It is sent back byte
  for byte unless the user changes it on purpose, so nothing on the site is
  ever broken by being opened in QUILL.

### 8.2 Inserting a block

**Insert Block** (one key) opens a search field over a list:

- **What the list holds:**
  - every block the site allows, from `/wp/v2/block-types`;
  - the site's own patterns, from `/wp/v2/block-patterns/patterns`;
  - the site's synced patterns (`/wp/v2/blocks`).
- **What each row reads:** the block's name and a one-line description, in
  the site's language.
- **Searching:** typing "but" finds Button and Buttons.
- **Order:** the most-used blocks come first, and then the rest from A to Z.

Choosing one opens a short form with only the fields that block needs:

- Button: text, link, open in new tab;
- Columns: how many;
- Details: the summary line;
- Embed: the address;
- Gallery: a check list of images from the Media Library;
- Cover: an image and its text.

**The form is generated, not hand-built.** It comes from the block type's
attribute schema, so a plugin's block gets a usable form too. The fields
QUILL has a better control for (images, links, colours) get that control.

**Patterns are the simplest thing of all.** A site owner, or their designer,
builds "Event announcement" or "Staff profile" once in the block editor. From
then on, anyone can insert it by name and fill in the words.

### 8.3 Moving through blocks

- **Next Block and Previous Block:** a quick-navigation pair. Each move says
  the block type, its position and its first words, for example "Image block,
  4 of 12: Volunteers at the spring fair".
- **Where Am I:** says the block and its nesting, for example "Paragraph,
  inside Column 2 of Columns".
- **The Blocks window:** a tree view of the whole document, one row per
  block, with nested blocks as children. From the tree:
  - Move Up and Move Down (Alt+Shift+Up and Down, the keys the block editor
    itself uses);
  - Duplicate;
  - Remove;
  - Change To, for example paragraph to heading, list to paragraphs, or
    image to cover;
  - Group and Ungroup.

  Enter goes to the block in the document.
- **Undo:** every one of these is a single undo step.

### 8.4 Block settings

**Block Settings** on the current block opens a form, never a sidebar:

- alignment;
- width (wide or full, where the theme allows);
- colours;
- font size;
- spacing;
- any other attribute the block has.

**Colours and sizes come from the theme by name.** QUILL reads the theme's
palette and font-size presets, from `theme.json` through the global styles
endpoint. So the choice reads "Accent (dark green)" and "Large", never
`#2f5d50` or `1.375rem`.

The theme decides what is offered. A user cannot pick a colour the site's
design does not have. That is also how the block editor itself behaves when a
theme locks its palette.

### 8.5 Never breaking a block

The block editor marks a block as "invalid" when its saved HTML is not exactly
what that block would have written. A tool that writes blocks carelessly
leaves the site owner a page full of warnings. So:

- **Core blocks match WordPress exactly.** For every core block QUILL writes,
  the serializer produces the markup WordPress's own save code produces. The
  tests run against WordPress's published block fixtures (the
  `full-content` fixtures in the Gutenberg repository).
- **Dynamic blocks** (latest posts, query loop, navigation) are a comment
  with attributes and no saved HTML, so there is nothing to mismatch.
- **Untouched blocks** go back byte for byte (section 8.1).
- **A preview from the site itself.** Preview Blocks renders the document
  through the site's block renderer (`/wp/v2/block-renderer`) and shows the
  result in the existing browser preview. The user hears what the real site
  makes of the blocks before publishing.
- **Check Before Publishing** (section 7) gains one more check: a fence QUILL
  could not turn into a block, named with its line.

### 8.6 What this is not

- **Not a new canvas.** There is no visual layout surface. The theme draws
  the page; QUILL edits what goes in it.
- **Not full-site editing.** Templates, template parts, the site header and
  the navigation menu stay in WordPress (section 1).
- **Not a second block editor to maintain.** The core-block list is the
  thirty or so blocks people actually write with. Everything else comes from
  the site's own block types, with generated forms, or stays a protected
  island.

## 9. Accessibility, the whole way through

Sections 4 to 8 make WordPress usable by a blind writer. This section goes
further, in two directions:

- **For the writer:** every part of running a site that is hard in a browser
  becomes a list, a form or a spoken answer.
- **For the site's visitors:** QUILL helps the writer publish pages that are
  accessible to everyone who reads them, and helps them prove it.

Each feature names the REST API routes it uses, so nothing here depends on a
plugin. Routes marked "6.x" need that WordPress version. On an older site,
the feature says plainly that the site is too old for it, and why.

### 9.1 What the API offers, and what we use it for

The core REST API was surveyed on 2026-11-03 (developer.wordpress.org REST
API reference, plus the newer routes).

| Routes | Used for |
| --- | --- |
| posts, pages, revisions, autosaves | writing, versions, crash-safe drafts (5, 9.3) |
| media | the Media Library, captions and transcripts (6, 9.6) |
| categories, tags, taxonomies | Properties, the site map (5.5, 9.9) |
| comments | the Comments window (9.8) |
| users, users/me | roles, what this account may do (9.2) |
| settings | the site title, tagline, language and logo (6.10, 9.10) |
| search | Open, Used In, site-wide find (5.2, 9.5) |
| block-types, blocks, block-renderer, block-patterns | blocks (8), the page audit (9.4) |
| global-styles, themes | theme colours and contrast (9.7) |
| menus, menu-items, menu-locations, navigation (5.9+) | the Menus window (9.9) |
| sidebars, widgets, widget-types (5.8+) | the Widgets window (9.9) |
| templates, template-parts (5.9+) | read-only page structure (9.4) |
| plugins (5.5+) | knowing which accessibility plugins exist (9.4) |
| site health (`wp-site-health/v1`) | the Site Check (9.10) |
| batch (`batch/v1`, 5.6+) | many changes as one request, with one confirmation (9.5) |
| oembed | embeds named and described before insert (9.6) |
| application-passwords | signing a site out from QUILL, revoking others (9.10, 9.13) |
| users (create, edit, delete) | the Users window (9.13) |
| types, statuses, taxonomies | custom post types and taxonomies (9.13) |
| block-directory (5.5+) | installing a missing block (9.13) |
| font-families, font-collections (6.5+) | the Fonts window (9.13) |

Any route a site turns off, or an account cannot use, has its feature dimmed
with the reason as its label: "Menus: your account cannot edit menus on
Community Radio." A dimmed row is never silent.

### 9.2 Know what you can do before you try

On connect, and again daily, QUILL reads `users/me?context=edit`, which gives
the account's roles and capabilities. Every command then knows ahead of time
whether it will work.

- **A Contributor:** cannot publish. So Publish becomes Submit for Review
  (status `pending`), and the help says why.
- **An Author:** cannot publish pages. So Publish Page is dimmed, with the
  reason as its label.
- **The Sites list** says the role for each site: "Community Radio, Editor".
- **No guessing:** WordPress errors such as `rest_cannot_publish` are never
  where the user finds out. Each one is mapped to a plain sentence in case it
  happens anyway.

### 9.3 Never lose a word

- **Autosaves:** while a WordPress document is open, QUILL writes the
  account's autosave (`/<type>/<id>/autosaves`) every two minutes, as well as
  the local working copy. This is what the block editor itself does. If the
  computer dies, the words are on the site too, and WordPress's own "there is
  an autosave newer than this version" notice works for anyone who opens the
  item in a browser.
- **Reading autosaves:** Open notices an autosave newer than the published
  copy, whether from a browser session or a crashed QUILL, and offers it:
  "There is an unsaved version from yesterday, 4:12 PM. Open that instead?"
- **Previous Versions:** autosaves appear in the list (5.6), marked "Autosave
  on the site".

### 9.4 Check This Page, the visitor's way

Check Before Publishing (7) looks at the writer's text. **Check This Page**
looks at what a visitor actually gets: the theme, the header, the menus, the
footer and the content together.

- **Render:** headless Edge or Chrome loads the public page (or, before
  publishing, the block renderer's output inside the theme's preview, 8.5).
- **Check:** QUILL runs **axe-core** on the rendered page.
  - axe-core is bundled with the app, so nothing is downloaded at run time.
  - It is the same engine the accessibility rules already ask CI to use.
  - The check reads the page; it sends it nowhere. No AI is involved.
- **Report:**
  - One line first: "Community Radio home page: 3 problems, 2 to check".
  - Then a list with one row per finding, in plain words: what is wrong,
    who it affects, and where it is ("in the site footer").
  - Each row has Explain, which gives the WCAG criterion by number and
    name, and one paragraph on why it matters.
- **Content or theme:** each finding says whose it is.
  - **In the content:** "Go to It" opens the document at the block, and,
    where the fix is mechanical (empty alt text, an empty link, a skipped
    heading), offers "Fix It", which shows the change before applying it.
  - **In the theme or a plugin:** QUILL says so, names the theme or plugin
    (from `themes` and `plugins`), and offers "Write a Note for the Theme
    Author". That is a plain-text report of the finding, the page and the
    WCAG criterion, ready to paste into a support forum or email.
- **The page's shape:** the report ends with the page as a screen reader
  meets it. It reads it from the browser's accessibility tree (the DevTools
  `Accessibility.getFullAXTree`):
  - landmarks;
  - the heading outline, including the theme's own headings;
  - link and button counts;
  - the reading order.

  This is how a writer finds out that their theme puts the site title in a
  Heading 1 and their page title in another.

### 9.5 Check the Whole Site, and fix it in bulk

**Check the Whole Site** runs Check This Page across every published page and
post. It works through the list in the background, with progress spoken
every ten pages, and can be cancelled and resumed.

- **The report has three views:**
  - by page;
  - by problem ("Images with no alt text: 41, on 17 pages");
  - by owner (content, theme, plugin).
- **Fix in Bulk:** for content problems that repeat, it offers to fix them in
  bulk.
  - **Missing alt text:** steps through each image in turn: Suggest (6.8),
    edit, Next. A count is kept.
  - **The same image missing alt text in many places:** fills each in with
    the library's alt text, after a list showing every place it will change.
  - **"Click here" and "read more" links:** each one is shown with its
    sentence, for the writer to rename.
- **One confirmation:** fixes are made in local copies first. Then, after one
  confirmation that names the site and gives the number of pages, they go in
  one request (`batch/v1`). A version of every page is kept first, so Undo
  Site Fix can put them all back.
- **History:** each run is kept with its date, so the writer can say "41
  problems in March, 6 now". The history is per site and stays on the
  computer.
- **Site-wide Find and Replace:** the same machinery, for words rather than
  problems. For example: a phone number that changed, a person who left, a
  renamed programme.
  - It searches all content (`search`), lists every match with its sentence,
    and lets each be included or skipped.
  - Then it replaces in one batch, after the same confirmation, and keeps a
    version of each page.
  - Undo puts them all back.

### 9.6 Captions, transcripts and listening versions

- **Captions for video:** a video in the library, or one being uploaded, can
  have captions made on the computer by the transcription QUILL already has.
  - QUILL makes the captions file (WebVTT), opens it for review in a plain
    text window where each cue is a line with its time, and then uploads it.
  - It attaches the captions to the video block as a `track`, so the
    player's CC button works.
  - Speaker names and sound descriptions ("[applause]") are suggested, and
    each one is editable.
- **Transcripts for audio:** an audio file gets the same transcription.
  QUILL offers to insert it below the player as a Details block, "Read the
  transcript", so it does not swamp the page.
- **A listening version of a post:** Make a Listening Version.
  - It reads the post with the user's chosen Read Aloud voice into an MP3,
    on the computer.
  - It uploads the MP3 and inserts an audio block at the top of the post:
    "Listen to this post (6 minutes)".
  - When the post is updated, it says the recording is out of date and
    offers to remake it.
- **Embeds, named before they go in:** pasting a YouTube, Vimeo or podcast
  link asks the site's oEmbed proxy (`oembed/1.0/proxy`) what it is. QUILL
  then says the title and author before inserting, and gives the embed a
  title attribute, so it is never an unnamed frame for visitors.
- **Documents:** uploading a PDF or Word file offers "Also Publish as a Page".
  - It converts the file with the existing converter, opens the result as a
    new WordPress page for review, and links the two.
  - Many visitors with disabilities find a page easier than a PDF, and the
    page can be checked (9.4).
  - Nothing is published without the usual Publish.

### 9.7 Colours that pass, and say so

- **Contrast ratios as part of the name:** QUILL reads the theme's palette
  and its text and background colours from `global-styles`. Every colour
  choice in Block Settings (8.4) then says its contrast against the
  background it will sit on:
  - "Accent (dark green), 7.2 to 1, passes";
  - "Pale yellow, 1.4 to 1, too faint for text".
- **Warn, don't block:** a combination below WCAG AA (4.5 to 1 for body
  text, 3 to 1 for large text) is allowed but warned about, with the reason.
- **Palette Report:** every pairing in the theme, pass or fail. It is useful
  for a writer whose designer chose the palette, and it can be pasted into
  "Write a Note for the Theme Author" (9.4).
- **Colour never alone:** a block that relies only on colour to mean
  something, such as red text for "cancelled", is flagged by Check Before
  Publishing. The flag suggests also saying it in words.

### 9.8 The Comments window

Comments are moderated in the same window shape as the Media Library: a
Site combo, a status filter (Waiting, Approved, Spam, Trash) and a list.

- **Each row reads:** the author, the post, the date and the first words.
- **On a comment:**
  - Approve, Unapprove, Spam, Trash;
  - Reply, which opens a small editor with spelling and dictation;
  - Edit;
  - Open on Site.
- **Comment threads:** shown as a tree, so replies sit under their parent.
- **Many at once:** several comments can be acted on together, with one
  confirmation that gives the count.
- **Waiting comments:** on opening a site, QUILL says how many are waiting,
  once: "Community Radio: 3 comments waiting". This can be turned off per
  site in Sites.

### 9.9 Menus, widgets and the site map

The parts of a site that are drag-and-drop in the browser are lists here.

- **Menus** (`menus`, `menu-items`, `menu-locations`, 5.9+): a tree of each
  menu. Each row reads "Sessions, page, level 1, 3 of 7".
  - Add Page, Add Post, Add Category and Add Link;
  - Rename;
  - Move Up, Move Down, In and Out (Alt+Shift+arrows, the block editor's own
    keys);
  - Remove;
  - Which Location, for example the header or the footer.
  - **Checking the menu:** every item must have a name. An item that points
    to a page that is now a draft or in the Trash is flagged as a dead link
    for visitors.
- **Navigation blocks** (block themes): the same tree, reading and writing
  the `wp_navigation` post instead.
- **Widgets** (`sidebars`, `widgets`, `widget-types`, 5.8+), for classic
  themes: each widget area is a list, and each widget has a settings form,
  generated from its schema as blocks are (8.2).
- **The site map:** Site Map is a tree of every page by parent, with each
  post under its categories. Enter opens an item. Its point is to answer
  "where does this page live?" without the visual admin.
- **Templates and template parts** (5.9+, block themes): read-only. Template
  Outline lists the header, the footer and the template a page uses, with
  the blocks in each. That tells a writer why something they cannot find in
  their page appears on it. Editing templates stays out of scope (8.6).

### 9.10 The Site Check and the site's own settings

- **Site Check** reads `wp-site-health/v1`. It gives the WordPress version,
  the PHP version, HTTPS, available updates, and whether the REST API and
  loopback requests work. Each answer is a plain line, and "critical" items
  come first. It is how a site keeper hears that their site is behind,
  without the admin dashboard.
- **Site Settings** (`settings`, `manage_options` only):
  - the site title;
  - the tagline;
  - the site language;
  - the time zone;
  - the date format;
  - the front page and posts page.

  These are in one form, and each change is confirmed by name. **The site
  language matters for accessibility:** it is the page's `lang` attribute,
  so it decides which voice a screen reader uses for every visitor.
- **Sign Out This Site:** revokes QUILL's application password on the site
  itself (`users/me/application-passwords/<uuid>`), as well as forgetting it
  locally. Remove in Sites asks whether to do both.

### 9.11 Writing accessibly, as you go

These are in the editor, for any WordPress document, and none needs AI.

- **Language of a passage:** Mark Language puts a `lang` attribute on the
  selection, for example a French quotation in an English post. A visitor's
  screen reader then switches voice there. QUILL's own Read Aloud honours it
  too, using the multilingual voices.
- **Tables:** Insert Table always asks for a header row and a caption. A
  table without a header row is flagged by Check Before Publishing.
- **Link text:**
  - A link whose text is the address, "click here", "here" or "read more"
    is flagged, with its sentence.
  - A link that opens a new tab gets "(opens in a new tab)" added to its
    visible text, as WordPress itself does.
- **Emoji and symbols in headings and links:** these are flagged. A screen
  reader says the whole name ("sparkles"), and in a heading or link that is
  heard on every visit.
- **Motion:** an animated GIF or an autoplaying video is flagged.
  - An autoplaying video gets an offer to turn off autoplay.
  - A GIF gets an offer to make a still first frame with Pillow, with the
    animation as a link.
- **Images of text:** Describe Image (6.8) says when an image is mostly text.
  Check Before Publishing then suggests putting the words in the page, where
  everyone can read and search them.
- **Reading level:** an optional readability line in Properties, worked out
  locally ("Reading level: about 9th grade, 14 words per sentence"). It
  notes the longest sentences, with Go to It on each.
- **In Short:** an optional AI summary of the post in two or three plain
  sentences, inserted at the top as an "In short" block for the writer to
  edit. It is a help for readers with cognitive disabilities, and for
  everyone in a hurry.

### 9.12 An accessibility statement

**Write an Accessibility Statement** opens a new page draft from a plain
template. It includes:

- the standard aimed at (WCAG 2.2 AA);
- the date of the last Check the Whole Site, with its result;
- known problems that belong to the theme or plugins, from the report;
- a contact line, with the site's admin email offered;
- the date.

It is the writer's page to edit, and nothing is published without Publish.
Running Check the Whole Site later offers to update the statement's date and
known-problems list.

### 9.13 Administration

Everything the REST API lets an account manage gets a list window or a form.
Each one opens from File > WordPress > Manage, and shows only what the
account's role allows (9.2). Every change is confirmed by name and site.
Every removal says what happens to whatever depended on the item.

**Categories and Tags** (`categories`, `tags`): one window, two tabs.

- **Each row reads:** the name, the slug, the number of posts, and the
  parent (categories only, shown as a tree).
- **Add, Edit and Delete:**
  - Add and Edit set the name, slug, description and parent.
  - Delete says how many posts use the item. A deleted category's posts fall
    back to the site's default category, and QUILL names it.
- **Merge Into:** moves every post from one category or tag to another,
  then deletes the empty one. The API has no merge, so QUILL does it as one
  batch (`batch/v1`) after one confirmation that gives the post count. A
  record is kept, so Undo Merge can put the posts back.
- **Convert:** turns a tag into a category, or a category into a tag, the
  same way.
- **Find Unused:** lists items with no posts, for tidying, with several
  removable at once.
- **Default Category:** the one posts get when none is chosen (the
  `default_category` setting).
- **Other taxonomies:** any custom taxonomy the site exposes (`taxonomies`
  with `show_in_rest`), such as a plugin's "Event type", gets the same window,
  named by its own label.

**Users** (`users`, `list_users` and up):

- **Each row reads:** the name, the username, the role, the email and the
  number of posts.
- **Add User:** username, email, name, role and a generated password. WordPress
  sends the new user their sign-in details, and QUILL never shows or stores
  the password.
- **Edit:** the name, display name, email, role and biography.
- **Change Role:** for several users at once.
- **Delete:** WordPress requires the user's content to go to someone else, so
  QUILL asks who that should be first and names how many posts will move.
  Deleting yourself is refused, with the reason.
- **My Profile:** your own name, display name, biography and website. This is
  what visitors see on your author page.
- **Application Passwords:** lists each user's application passwords with
  their names and when each was last used. Revoke works on any one of them,
  with QUILL's own marked. It is how a site keeper shuts off an old app or a
  lost laptop without the dashboard.

**Plugins** (`plugins`, `activate_plugins`; WordPress 5.5+):

- **Each row reads:** the name, the version, active or inactive, the author,
  and whether an update is available (from Site Check, 9.10).
- **Activate and Deactivate:** each confirmed by name. Deactivating a plugin
  that the site's pages use warns first. QUILL knows this from the blocks and
  shortcodes it found in Check the Whole Site.
- **Add Plugin:** searches the WordPress.org plugin directory by name, reads
  its rating, its last update and its "tested up to" version, and installs it
  inactive. Activation is a separate, deliberate step.
- **Delete:** only for an inactive plugin, confirmed.
- **Accessibility plugins:** QUILL recognises the well-known ones and says
  what each does. When Check the Whole Site finds a problem a plugin would
  fix, it says so.
- **Block plugins** (`block-directory`): the block directory offers
  single-block plugins. Insert Block (8.2) searches it when the site has no
  matching block, and offers to install one, inactive, after confirmation.

**Themes** (`themes`):

- **Each row reads:** the name, the version, and active or inactive.
- **What the active theme supports:** read-only, from `theme_supports`. For
  example the logo, wide blocks, block styles, and editor colours. That
  explains why an option is or is not offered in Block Settings.
- **Activation:** the REST API cannot switch themes, so the window says so
  and offers Open in Dashboard at the right page.

**Pages and posts in bulk** (`posts`, `pages`, `batch/v1`):

- **Selecting in Open:** the Open list (5.2) allows many items to be selected.
- **Bulk Edit:** changes status, author, categories, tags, comment setting or
  page parent for all of them together.
  - It is one confirmation, naming the count and the site.
  - It is one batch.
  - A version of every item is kept first.
  - Undo Bulk Edit puts them back.
- **Page Order:** a tree of pages by parent, with Move Up, Move Down, In and
  Out. These set `parent` and `menu_order`.
- **More in Properties:** per item, Properties (5.5) also offers:
  - the page template, from the theme's templates;
  - the author;
  - the post format;
  - Sticky (keep at the top of the blog);
  - a password for a password-protected item;
  - pingbacks;
  - the publish date, which can be backdated.
- **Other post types:** any custom post type the site exposes (`types`
  with `show_in_rest`), such as "Events" or "Products", appears in Open and
  in New with its own label. Its fields come from its schema, the same way
  blocks' forms are generated (8.2).

**Synced patterns** (`blocks`, the `wp_block` type):

- **Each row reads:** the pattern's name, whether it is synced, and where it
  is used.
- **Edit:** a synced pattern is edited as a document. Saving it updates
  every page that uses it, and the confirmation says how many.
- **Rename, Delete and Unsync:** Unsync turns each use into ordinary blocks
  first, so nothing on the site goes missing.
- **New from Selection:** makes a pattern from the blocks selected in the
  editor.

**Site identity and reading** (`settings`, adding to 9.10):

- **The site icon:** the browser tab picture. It is chosen from the Media
  Library, and a square image is checked for.
- **Reading:** posts per page, and whether the front page is the latest
  posts or a chosen page.
- **Discussion defaults:** whether new posts take comments and pingbacks, and
  whether emoji are turned into pictures.
- **Writing:** the default post format.
- **Contact:** the site's admin email and the week's first day.

**Fonts** (`font-families`, `font-collections`; WordPress 6.5+, block
themes):

- lists the installed fonts and their faces;
- offers to install one from the site's font collections;
- shows each font's name together with a plain-words description: serif or
  sans serif, and whether it suits body text or headings.

Choosing which font the theme uses stays a design choice outside QUILL (8.6).

**What stays in WordPress:** some things the API cannot do. QUILL says so in
the one place someone would look for them, and offers Open in Dashboard:

- switching the theme;
- WordPress core updates;
- import and export;
- multisite network administration.

### 9.14 What these send

| Feature | Sends | To |
| --- | --- | --- |
| Check This Page, Check the Whole Site | nothing (reads public pages) | (on the computer) |
| Fix in Bulk, Site-wide Find and Replace | the changed pages, after one confirmation | the site |
| Captions, transcripts | the captions file or transcript, after review | the site |
| Make a Listening Version | the MP3 | the site |
| Embed naming | the link | the site's oEmbed proxy |
| In Short, Suggest Alt Text in Fix in Bulk | the text or image | the chosen AI |
| Site Check, Site Settings, Menus, Widgets, Comments | the requested change | the site |
| Administration (9.13) | the requested change, after confirmation | the site |
| Add Plugin | the search words | the WordPress.org plugin directory, through the site |

Every route gets its own `network_egress_audit` entry. axe-core and the
headless browser load only the site's public pages, and only when asked.

### 9.15 More from the API (2026-11-04 review)

A second pass over the REST API found more that is reasonable to use. Each item
below is checked against the site's own index first (routes, namespaces and
the account's capabilities), so a site without it never offers it, and a
dimmed command says why.

**Writing and reviewing:**

- **Notes on blocks** (WordPress 6.9+): editorial notes left on a block in the
  block editor are comments of type `note`, so QUILL can show them.
  - A Notes list beside the document, each reading "Sam on the second
    paragraph: tighten this".
  - Go to It, Reply, and Resolve.
  - Add Note on the block at the caret.
  - This is collaboration a screen-reader user has never been able to join in
    the block editor. Verify the route on the test site before building.
- **Custom fields:** any post meta a site registers for the REST API
  (`show_in_rest`) appears in Properties as a labelled field, generated from
  its schema as block forms are (8.2). That gives SEO titles and descriptions
  from plugins that register them, event dates, and the like.
- **Which application password is this:** Sites shows, for each site, which
  of the account's application passwords QUILL is using
  (`users/me/application-passwords/introspect`). Sign Out This Site revokes
  exactly that one.

**Pictures:**

- **Choose a size when inserting:** the library's own sizes
  (`media_details.sizes`: thumbnail, medium, large, full) are offered by name
  and width in the image dialog. Picking "medium, 300 wide" uses the site's
  smaller file rather than scaling the full one in the page. That saves
  visitors' data, and it is simpler than Make a Smaller Copy for most cases.
- **Edit a picture on the site** (`media/{id}/edit`, WordPress 5.5+): rotate,
  flip, and crop to a ratio (square, 4:3, 16:9). The original is kept, the
  edit makes a new library item, and Describe Image runs on the result so you
  hear what the crop kept.

**Look and layout:**

- **Style variations** (`global-styles/themes/{theme}/variations`, block
  themes): list the theme's ready-made looks by name, each with its Palette
  Report (9.7), so a person can choose the variation whose colours pass.
  Applying one asks first, names the site, and keeps the old one to go back
  to.
- **Site Styles, the safe subset:** the site's colour palette and font sizes
  can be edited by name (`global-styles/{id}`). Every colour shows its
  contrast against the background as you choose it. Anything else in
  `theme.json` stays in the Site Editor (8.6).
- **Pattern Directory** (`pattern-directory/patterns`): search WordPress.org's
  free patterns from Insert Block, beside the site's own. Each one is
  described in words, with its blocks listed, before it goes in.
- **Pattern categories** (`wp_pattern_category`): Synced Patterns (9.13) can
  be grouped and filtered by category.

**Plugins QUILL recognises:**

When a popular plugin's namespace is in the index, QUILL turns on a small,
plain extra for it, and says so in Site Check. Without the plugin, nothing
shows. These are sized as "useful in a sentence", never a full second admin:

- **BITS Accessible Forms** (`baf/v1`): forms (section 17a).
- **The Events Calendar** (`tribe/events/v1`):
  - events in Open, with start, end and venue in Properties;
  - New Event;
  - a plain "Coming up" list.

  Community organisations live on their calendars.
- **WooCommerce** (`wc/v3`), read and light edit only:
  - products in Open, with price and stock in Properties;
  - orders as a list QUILL reads aloud, never edits, and never exports
    without asking.
- **SEO plugins** that register meta (Yoast SEO, Rank Math): the title and
  description in Properties, with a length count spoken as you type.
- **Accessibility plugins:** recognised in Check the Whole Site, which says
  when one already fixes a finding (9.13).

**Running the site:**

- **Abilities** (`wp-abilities/v1`, WordPress 6.9+): sites can describe actions
  they offer to AI agents. Where Choose Your AI is on and the site lists
  abilities, Ask can use them. Every ability is listed by name, off until
  checked, approved per use, and shown in the answer. This follows the vendor
  tools rule in code.md decision 4. Verify the route on the test site.
- **Site Check, every test:** the separate Site Health tests (HTTPS, loopback,
  background updates, the authorization header, page cache) each read as one
  line. The authorization-header test explains, when it fails, why
  application passwords would not work.
- **Bulk moderation:** select many comments and approve, spam or trash them
  in one batch, with one confirmation that gives the count.
- **Library-wide alternative text:** the Alt Text Review (6.8) extended to the
  whole Media Library. It steps through every picture with no alternative
  text, offers Suggest, and saves in batches.

**Left out on purpose:**

- editing templates and template parts, beyond reading them (8.6);
- WordPress core updates and theme switching, which the API cannot do;
- import and export;
- multisite network administration;
- anything that would make QUILL a second dashboard rather than a writing
  tool.

### 9.16 Every route, and the value still to add (2026-11-04)

The live test site (WordPress 7.1.4) exposes 135 REST routes in five
namespaces: `wp/v2`, `wp-site-health/v1`, `wp-block-editor/v1`,
`wp-abilities/v1` and `oembed/1.0`, plus `batch/v1`. This table maps every
group to where QUILL uses it, so nothing is left out by accident. A route a
site does not have is never offered, and its command is dimmed with the
reason.

| Routes | Used for | Section |
|---|---|---|
| `posts`, `pages`, their `revisions` and `autosaves` | writing, opening, saving, versions, crash-safe drafts | 5, 9.3 |
| `types`, `statuses` | custom post types in Open and New; custom statuses in Properties | 9.13 |
| `categories`, `tags`, `taxonomies` | Properties, Categories and Tags, custom taxonomies | 5.5, 9.13 |
| `media`, `media/{id}/edit` | the Media Library, uploads, edit a picture on the site | 6, 9.15 |
| `media/{id}/sideload`, `finalize`, `post-process` | reliable big uploads, and regenerating sizes after an edit (below) | 9.16 |
| `comments` (and `type=note`) | Comments, bulk moderation, Notes on blocks | 9.8, 9.15 |
| `users`, `users/me`, `application-passwords`, `introspect` | roles, Users, My Profile, which password, Sign Out | 9.2, 9.13, 9.15 |
| `settings` | Site Settings, logo, icon, reading, discussion | 9.10, 9.13 |
| `search` | Open by Web Address, Link to a Page on This Site, Site-wide Find | 5.2, 9.5, 12 |
| `block-types`, `block-renderer`, `blocks`, `block-patterns/patterns`, `block-patterns/categories`, `pattern-directory/patterns`, `wp_pattern_category`, `block-directory/search` | blocks, patterns, synced patterns, previews, installing a missing block | 8, 9.13, 9.15 |
| `global-styles/{id}`, its `revisions`, `themes/{theme}/variations` | colours that pass, style variations, safe Site Styles, and going back to an earlier look | 9.7, 9.15 |
| `themes` | what the theme supports | 9.13 |
| `font-collections`, `font-families`, `font-faces` | the Fonts window | 9.13 |
| `menus`, `menu-items`, `menu-locations`, `navigation` (and their revisions and autosaves), `wp-block-editor/v1/navigation-fallback` | the Menus window, and undoing a menu change | 9.9 |
| `sidebars`, `widgets`, `widget-types` (with `encode` and `render`) | the Widgets window | 9.9 |
| `templates`, `template-parts` (with `lookup` and revisions) | Template Outline, read-only | 9.9 |
| `plugins` | the Plugins window | 9.13 |
| `icons`, `icon-collections` | Insert Icon (below) | 9.16 |
| `wp-block-editor/v1/url-details` | hearing a page's title before you link to it (below) | 9.16 |
| `wp-block-editor/v1/export` | downloading a copy of the site's design (below) | 9.16 |
| `wp-site-health/v1/tests/*`, `directory-sizes` | Site Check, and how much space the site uses | 9.10, 9.16 |
| `wp-abilities/v1` (`abilities`, `categories`, `run`) | Abilities, opt-in, for Ask | 9.15 |
| `oembed/1.0/proxy` | naming embeds before they go in | 9.6 |
| `batch/v1` | Fix in Bulk, merges, bulk edit, bulk moderation | 9.5, 9.13 |
| `view-config` | not used: editor display preferences, no value to a writer | |

**New value, from routes not yet used:**

- **Hear where a link goes before you add it** (`url-details`):
  - **Inserting a link:** Insert Link reads the target page's title and
    description aloud, so a typo in an address is caught at once.
  - **Fixing vague link text:** for a "click here" or "read more" link that
    Check Before Publishing found, Fix It offers the target page's own title
    as the link text. This one route turns the most common accessibility
    problem on the web into a one-key fix.
  - **Checking links:** Check This Page uses it to report links whose pages
    are gone.
- **Insert Icon** (`icons`, `icon-collections`, WordPress 7.x): a searchable
  list of the site's icons by name. Each one is either decorative, so screen
  readers skip it, or given a label that says what it means. An icon is never
  left unnamed.
- **Big uploads that do not fail** (`sideload`, `finalize`): long videos and
  big audio files upload in pieces, with progress spoken. After Edit a Picture
  on the Site, Regenerate Sizes (`post-process`) remakes the thumbnail and
  medium copies so the theme shows the edit everywhere.
- **Going back to an earlier site look** (`global-styles` revisions): Site
  Styles has Previous Looks, like Previous Versions for a page. Each one is
  dated, with its Palette Report.
- **Undo a menu change** (`navigation` and `menu-items` revisions and
  autosaves): the Menus window keeps a history, so a removed menu item can
  come back.
- **How much space the site uses** (`directory-sizes`): Site Check says the
  size of uploads, themes, plugins and the database, in words ("Uploads:
  1.2 GB"). It warns before a big upload on a host that is nearly full.
- **Download a copy of the site's design** (`wp-block-editor/v1/export`,
  block themes, administrators): a zip of the theme with the person's
  changes, saved to their computer before they try a style variation.

**New value that uses routes already in the plan:**

- **Send This Document to WordPress:** any document open in QUILL can become
  a new draft on a chosen site, whether a Word file, Markdown, a text file or
  a dictated note. Its pictures go to the Media Library, its headings become
  heading blocks, and its first heading becomes the title. This is the most
  natural way in for a writer who already works in QUILL.
- **Publish to Another Site:** copy a post to another connected site, as a
  draft there. Pictures are uploaded again, and categories and tags are
  matched by name (or created, after asking). One newsletter on three sites
  is a common need for people who keep several sites.
- **Duplicate:** make a new draft from any page or post, on the same site
  or another, with everything but the date and status.
- **Download My Writing:** every page and post on a site saved to a folder of
  Markdown or Word files, with pictures and a contents page. It is an
  offline archive, a backup the person can read, and a way to move house.
  The export runs in the background and can be resumed.
- **Send a Folder as Drafts:** a folder of Markdown or Word files becomes
  drafts on a site in one go. One confirmation gives the count, and each
  file is checked first with Check Before Publishing.
- **Coming Up:** a list of everything scheduled on every connected site, by
  date. It answers "what goes out next week?" in one place.
- **What Changed on My Sites:** since you last looked, new comments, posts
  others published, plugin updates waiting and site health warnings, across
  every site. One list, read on request; never a pop-up.

### 9.17 Route coverage audit: what the code really calls (2026-11-04)


Worktree: `S:\wt\quill-docs` at `0a8ba0c1e`. This audit is read-only. Source table: `docs/design/wordpress.md` section 9.16, lines 1559-1643.

##### How it was checked

- **Core:** an AST scan of every `api.get/post/delete/request/iter_collection/upload/batch` call in `quill/core/wordpress`, `quill/ui/wordpress_*.py` and the Lite adapters. A route that appears only in `routes.FEATURES`, `site_health.RECOGNISED` or a constant (for example `link_targets.URL_DETAILS`) counted only when a function actually sends it.
- **UI:** both editors build their menus from the one table, `quill/core/wordpress/menu.py` (`PLACES`).
  - QUILL fills it in `main_frame_wordpress.py` `_fill_wordpress_menu`, called from `main_frame_menu.py:285` and `:3330`.
  - Lite gets its rows from `quill/core/lite/commands.py:145` and `:1022` through `lite_rows()` and `lite_placed_rows()`.
  - All 99 rows have a shared handler on `WordPressCommands`, and every one of the 99 `cmd_wp_*` methods in `quill/apps/lite_window_wordpress.py` hands off to the matching shared handler. A script verified this, with no mismatches.
  - Keys come from `menu.LAYER_KEYS`, used by `keymap.py` (through `wordpress.keys.default_bindings`) and by Lite's `_wordpress_key_bindings`. The prefix is `Ctrl+Alt+Shift+Grave`, and only 22 rows have a key.
- **Lite column:** every row is the same command at the same path with the same key, as `cmd_wp_<id>`. Lite's only difference is that its Tools > WordPress submenu has no access letter (`menu.py` docstring). `tests/unit/apps/test_lite_wordpress.py` checks that all 99 `cmd_wp_*` hand off, but checks delegation only.
- **Docs:**
  - The two user-guide chapters (`docs/user guide/quill-guide/quill-guide-16-wordpress.md` and `standalone/quilllite/docs/guide/lite-guide-14-wordpress.md`) are the same 62-line page. Each has a menu table and nine keys, and sends readers to the shared manual (`docs/user guide/wordpress-and-forms/wordpress-forms-0N-*.md`).
  - Tutorials (`quill/core/tutorials/wordpress_lessons*.py`) have 7 lessons: connect, write and publish, open by address, pictures and alt text, Check Before Publishing, previous version, and answer comments.
  - In the Docs column, "Guide" means that chapter, "Manual NN" is the manual chapter, and "Tut" is a tutorial.

##### Coverage table

| Routes | Core | QUILL | Lite | Options | Tests | Docs | Status |
|---|---|---|---|---|---|---|---|
| `posts`, `pages`, their `revisions` and `autosaves` | `site.py`: `list_items`, `load_item`, `create_item`, `update_item`, `trash_item`, `restore_from_trash`, `list_revisions` (revisions+autosaves), `save_autosave`; `schedule.py`: `send_scheduled`, `latest_autosave`, `find_landed` | File > WordPress: New Page (`wordpress.new_page`, G), New Post (N), Open Page or Post (O), Save Draft to Site (D), Publish or Update (P), Schedule Publish (E), Previous Versions (V), Compare with Site (C), Move to Trash (T). Registered from `PLACES` | same ids as `cmd_wp_*`, same keys | New: Site choice, Title, Slug, format radio, category/tag check groups. Open: Find box, Open, Move to Trash..., Restore from Trash. Versions: View..., Restore. Schedule dialog. "Unsaved Version" choice | `test_wp_commands_write_send.py::test_save_draft_creates_the_page_as_a_draft`; `test_wp_api.py::test_revisions_and_autosaves_newest_first_and_forbidden_is_skipped`. No UI behaviour test for `cmd_versions`, `cmd_trash`, `cmd_compare` or `cmd_new_post` (Lite delegation only) | Guide (menu table, keys); Manual 02; Tut (write and publish, previous version) | **full** (tests thin on Versions, Trash and Compare) |
| `types`, `statuses` | `site.list_content_types` (`types`). `statuses`: **none** | Open Page or Post asks for the kind (`_choose_kind`) when the site has custom types | same | Kind choice in Open. Properties "Status" is a **fixed** list (`PropertiesDialog.status` `wx.Choice`) | `test_wp_link_and_placement.py::test_open_offers_the_sites_own_types_and_lists_them` | Manual 02 (Open); custom types not described | **partial**: `statuses` never called, so custom statuses never shown |
| `categories`, `tags`, `taxonomies` | `site.list_terms`, `create_term`, `update_term`, `delete_term`, `merge_terms`; `site_library.convert_term`, `delete_terms` (batch), `default_category`. `taxonomies`: **none** | Tools > WordPress > Categories and Tags (`wordpress.manage_terms`); Properties check groups | same | Choose Categories or Tags, then Add..., Rename..., Merge Into..., Find Unused..., Delete..., Make Default... | `test_wp_admin_comments_terms.py::test_terms_list_shows_slug_count_parent_and_default`; `test_wp_api.py::test_merge_moves_posts_then_deletes_the_source` | Manual 02, 05 | **partial**: `taxonomies` never called; only `category` and `post_tag` are offered, with no custom taxonomies |
| `media`, `media/{id}/edit` | `site_media.list_media`, `upload_media`, `update_media`, `delete_media`; `media_edit.edit_on_site`, `save_alt_texts` (batch); `media_tools.load_image_sizes` | Tools > WordPress > Media Library (M), Alt Text Review (X), Alt Text for the Whole Library, More Media > Upload Files (U), Upload from Web Address, Paste Image, Make a Smaller Copy, Edit a Picture on the Site; Insert > Picture from the Media Library, Picture from This Computer; Format > WordPress > Image Size | same | Library: Find, Insert..., Play..., Used In, Attach, Set as Featured Image, Suggest Alternative Text..., Describe Image..., Edit Alternative Text..., Copy Address, Remove from Library.... Image dialog: Alternative text, Suggest, Decorative, Caption, File size, Use as featured image, Link to, Describe Image | `test_wp_media_library.py::test_media_library_lists_and_finds_used_in_for_a_small_library`; `test_wp_api_writing_pictures.py::test_a_site_without_the_edit_route_says_so` | Guide; Manual 04; Tut (pictures) | **full** |
| `media/{id}/sideload`, `finalize`, `post-process` | `media_pieces.PieceUpload.send_next` (sideload), `.finish` (finalize), `regenerate_sizes` (post-process) | More Media > Upload a Large File (`wordpress.upload_large_file`), Regenerate Sizes (`wordpress.regenerate_sizes`) | same | Large file: a file picker only. Regenerate: a picture list. Progress is spoken at each quarter | `test_wp_routes_media.py::test_a_big_file_goes_in_pieces_with_progress`, `::test_regenerate_sizes` | Manual 04 | **partial**: Regenerate is not offered after Edit a Picture on the Site (the plan says it should be); a large file gets no title, alt or caption step, and an interrupted upload cannot resume |
| `comments` (and `type=note`) | `comments.list_comments`, `set_status`, `set_many`, `edit_comment`, `reply`, `count_waiting`; `block_notes.list_notes`, `add_note`, `reply`, `set_resolved`. (`site_media.list_comments/set_comment_status/reply_to_comment/count_waiting_comments` are dead duplicates with no callers) | Tools > WordPress > Comments (`wordpress.comments`); Insert > Note on This Block; View > Block Notes | same | Show... (Waiting, Approved, Spam, Trash), a moderation button for each status, Approve All..., Reply..., Edit..., Open on Site, Waiting Count on First Use, Mark, Mark Everything, Do with Marked.... Notes: Go to It, Reply..., Resolve or Reopen, Add Note... | `test_wp_admin_comments_terms.py::test_waiting_comments_are_threaded_with_replies_under_their_parent`; `test_wp_api_writing_notes.py` | Guide; Manual 05, 03; Tut (answer comments) | **full** (spot-checked) |
| `users`, `users/me`, `application-passwords`, `introspect` | `site.load_account`; `site_admin.list_users`, `add_user`, `update_user`, `delete_user`, `post_count`, `list_app_passwords`, `revoke_app_password`, `current_password_uuid`; `site_features.which_password` | Manage > Users, Application Passwords, Sign Out This Site | same | Users: My Profile..., Add User..., Edit..., Change Role..., Delete..., Application Passwords.... App passwords: Revoke..., Which Password. Sign Out: a choice | `test_wp_admin_people.py::test_users_list_and_role_aware_buttons`, `::test_sign_out_revokes_forgets_and_removes` | Manual 01, 07 | **full** |
| `settings` | `site_admin.load_settings`, `save_setting`; `site_library.default_category`/`set_default_category`; logo in `wordpress_picture_commands.replace_logo`/`read_logos` | Tools > WordPress > Site Settings; More Media > Site Logo | same | 17 fields: title, tagline, language, time zone, date and time formats, week start, email, front page shows, front page, posts page, posts per page, comment and ping defaults, emoticons, default format, site icon. One Change... button. Logo: From the Library..., From a File..., From the Picture Maker..., Preview a Width..., Restore Earlier... | `test_wp_admin_manage.py::test_settings_list_reads_values_in_words`; `test_wp_pictures_logo.py::test_shows_the_logo_and_the_icon` | Manual 07, 04 | **full** |
| `search` | **none** | (Open by Web Address uses a slug lookup on the kind route; Link to a Page lists published pages and posts; Site-wide Find walks the collections in `site_fixes.fetch_items`) | none | n/a | none | n/a | **missing**: the route is never called. The three features it was meant for work through other routes |
| `block-types`, `block-renderer`, `blocks`, `block-patterns/patterns`, `block-patterns/categories`, `pattern-directory/patterns`, `wp_pattern_category`, `block-directory/search` | `block_catalog.fetch_choices` (block-types, block-patterns/patterns, blocks); `block_preview._api_render` (renderer); `site_library` synced-pattern functions (blocks); `pattern_directory.search`, `load_categories` (wp_pattern_category). `block-patterns/categories` and `block-directory/search`: **none** | Insert > WordPress Block; View > Preview Blocks; Manage > Synced Patterns; Format > WordPress > Block Settings | same | Insert Block: Find, Insert, WordPress.org Patterns.... Synced Patterns: Edit..., Rename..., Unsync..., Delete..., New from Selection..., by category | `test_wp_api_site_look.py::test_insert_block_offers_the_directory_only_where_the_site_has_it`; `test_wp_block_settings.py::test_preview_renders_dynamic_blocks_and_reads_the_rest`; `test_wp_admin_manage.py::test_patterns_list_where_each_is_used` | Guide; Manual 03 | **partial**: no "install a missing block" (`block-directory/search`); pattern categories come only from `wp_pattern_category` |
| `global-styles/{id}`, its `revisions`, `themes/{theme}/variations` | `site_styles.load_user_styles`, `save_user_styles`, `theme_styles`, `list_variations`; `looks_history.list_looks`, `restore_look` | Tools > WordPress > Design > Style Variations, Site Styles; Manage > Previous Looks; Palette Report | same | Variations: Apply.... Styles: Change..., Put Back the Previous Look.... Previous Looks: Palette Report..., Go Back to This Look... | `test_wp_api_site_look.py::test_applying_a_variation_keeps_the_old_look_and_put_back_restores_it`; `test_wp_routes_media.py::test_previous_looks_go_back` | Manual 06, 07 | **full** (spot-checked) |
| `themes` | `site_admin.list_themes`; `site_styles.active_theme`; `looks_history.styles_id` | Manage > Themes | same | Read-only list, Open in Dashboard | `test_wp_admin_manage.py::test_themes_list_supports_and_dashboard` | Manual 07 | **full** (read-only by design) |
| `font-collections`, `font-families`, `font-faces` | `site_library.list_fonts`, `list_font_choices`, `install_font` (family plus each face), `delete_font` | Manage > Fonts | same | Install... (a collection choice, then confirm), Delete... | `test_wp_admin_manage.py::test_fonts_list_install_and_delete` | Manual 07 | **full** (spot-checked) |
| `menus`, `menu-items`, `menu-locations`, `navigation` (and their revisions and autosaves), `navigation-fallback` | `navigation.load_menus`, `classic_nodes`, `load_locations`, `save_menu`, `add_item`, `rename_item`, `remove_item`, `set_locations`, `target_statuses`; `looks_history.navigation_versions`, `restore_navigation`. Navigation autosaves, menu-items revisions and autosaves, and `navigation-fallback`: **none** | Tools > WordPress > Menus, Menu History | same | Menus: Add Page..., Add Post..., Add Category..., Add Link..., Rename..., Move Up, Move Down, Move In, Move Out, Remove..., Check Menu, Other Menu..., Locations.... History: Bring Back Removed Items..., Restore This Version... (Navigation only) | `test_wp_admin_menus_widgets.py::test_menus_window_reads_the_tree`; `test_wp_routes_media.py::test_menu_history_restores_a_navigation_revision` | Manual 05 | **partial**: classic-menu history is local snapshots, so only changes made after the Menus window has read a menu can be undone. Navigation autosaves and the fallback are unused. Core may not register menu-items revisions at all; check the live index |
| `sidebars`, `widgets`, `widget-types` (with `encode` and `render`) | `site_structure.list_sidebars`, `list_widgets`, `add_block_widget`, `edit_block_widget`, `move_widget`, `remove_widget`. `widget-types`: **none** | Manage > Widgets | same | Add Text..., Edit..., Move to Area..., Remove..., Open in Dashboard | `test_wp_admin_menus_widgets.py::test_add_edit_move_and_remove_widgets` | Manual 07 | **partial**: `widget-types`, `encode` and `render` are never called, so only Text block widgets can be added and legacy widgets cannot be edited or previewed |
| `templates`, `template-parts` (with `lookup` and revisions) | `site_structure.list_templates`. `lookup` and revisions: **none** | Manage > Template Outline | same | A report only, with no controls | `test_wp_admin_structure.py::test_template_outline_puts_the_documents_template_first` | Manual 07 | **partial**: `lookup` and revisions are unused (read-only by design) |
| `plugins` | `site_admin.list_plugins`, `set_plugin_active`, `install_plugin`, `delete_plugin` | Manage > Plugins | same | Activate or Deactivate..., Add Plugin..., Delete..., Open in Dashboard | `test_wp_admin_manage.py::test_plugins_list_explains_accessibility_plugins` | Manual 07 | **full** |
| `icons`, `icon-collections` | `icons.list_icons` | Insert > WordPress Icon (`wordpress.insert_icon`) | same | Find, Insert with a Label... (Icon Label text), Insert as Decorative | `test_wp_routes_links.py::test_insert_icon_with_a_label` | Manual 03 | **full** |
| `wp-block-editor/v1/url-details` | `link_targets.read_target`, `dead_links` | Edit > WordPress > Hear Where a Link Goes, Fix Link Text; dead links in Tools > WordPress > Check This Page | same | Hear: Address box, then Insert Link confirm. Fix: Use the Page's Title, Use All Titles. Check This Page: Dead Links... | `test_wp_routes_links.py::test_fix_link_text_with_no_vague_links_says_so` and the `hear_link` tests | Manual 03, 06 | **partial**: not wired into Link to a Page on This Site, or into Check Before Publishing's fix, as the plan places it |
| `wp-block-editor/v1/export` | `site_space.export_design` (through `fetch_bytes`) | Manage > Download a Copy of the Site's Design | same | A Save As box | `test_wp_routes_media.py::test_download_design_saves_the_zip` | Manual 07 | **full** (Style Variations does not offer it first) |
| `wp-site-health/v1/tests/*`, `directory-sizes` | `site_health.health_lines` (tests, from the index); `across_sites._health`; `site_space.read_space` | Tools > WordPress > Site Check; Manage > Space Used | same | Report only | `test_wp_admin_manage.py::test_site_check_puts_critical_first`; `test_wp_routes_media.py::test_space_used_in_words` | Manual 07 | **partial**: sizes are a separate command, not part of Site Check, and there is no warning before a big upload on a nearly full host |
| `wp-abilities/v1` (`abilities`, `categories`, `run`) | `abilities.list_abilities`, `run_ability`. `categories`: **none** | Manage > AI Abilities, Ask the Site | same | Turn On or Off (with confirm); Ask the Site: question text, then a Run Ability confirm | `test_wp_api_site_abilities.py::test_ask_the_site_needs_an_ability_turned_on` | Manual 01, 07 | **partial**: `categories` is unused |
| `oembed/1.0/proxy` | `listening.oembed` | More Media > Name Embeds | same | Report only | `test_wp_listening.py::test_oembed_asks_the_sites_proxy`; `test_wp_listening_pages.py::test_no_embeds_is_said` | Manual 04 | **full** |
| `batch/v1` | `api.batch` from `site_structure.save_page_order`, `site_library.bulk_edit`/`undo_bulk_edit`/`delete_terms`/`unsync`, `site.merge_terms`, `media_edit.save_alt_texts`, `wordpress_site_check_commands` (Fix in Bulk, undo) | Check the Whole Site > Fix in Bulk..., Undo Site Fix, Bulk Edit, Page Order, Merge Into, Alt Text for the Whole Library | same | Bulk Edit: Select, Select All, Change..., Undo Bulk Edit.... Page Order: Move Up, Move Down, Move In, Move Out, Open | `test_wp_admin_structure.py::test_page_order_moves_and_saves_in_one_batch`, `::test_bulk_edit_changes_selected_posts_then_undoes` | Manual 06, 07 | **full** |
| `view-config` | none | none | none | n/a | none | n/a | **n/a**: not used, by design |
| Send This Document to WordPress (existing routes) | `site.create_item`, `site_media.upload_media` (`cross_site.move_pictures`) | File > WordPress > Send and Copy > Send This Document to WordPress | same | A site choice | `test_wp_routes_copies.py::test_send_document_makes_a_draft_from_an_ordinary_file` | Manual 02 | **full** |
| Publish to Another Site | same, plus `create_term` | Send and Copy > Publish to Another Site | same | A site choice; Categories and Tags confirm | `test_wp_routes_copies.py::test_publish_elsewhere_with_only_one_site` | Manual 02 | **full** |
| Duplicate | `load_item`, `create_item` | Send and Copy > Duplicate | same | Item choice, then a same-site or other-site choice | `test_wp_routes_copies.py::test_duplicate_on_the_same_site_opens_the_copy` | Manual 02, 03 | **full** |
| Download My Writing | `writing_archive.download_writing` | Send and Copy > Download My Writing | same | A folder picker (resumes from its manifest) | `test_wp_routes_copies.py::test_download_my_writing_then_resume` | Manual 02 | **partial**: Markdown only; the plan says Markdown **or Word** |
| Send a Folder as Drafts | `writing_archive.send_folder` | Send and Copy > Send a Folder as Drafts | same | A folder picker, then a count confirm | `test_wp_routes_copies.py::test_send_folder_confirms_the_count_then_sends` | Manual 02 | **partial**: accepts `.md/.markdown/.txt/.html`, but not `.docx` |
| Coming Up | `across_sites.coming_up` (`scheduled_on`) | Tools > WordPress > Your Sites > Coming Up | same | List, Open | `test_wp_routes_copies.py::test_coming_up_lists_every_scheduled_item` | Manual 02, 07 | **full** |
| What Changed on My Sites | `across_sites.what_changed` (posts, comments, health tests) | Your Sites > What Changed on My Sites | same | List, Open in Browser | `test_wp_routes_copies.py::test_what_changed_then_nothing_new` | Manual 02, 07; Tut mention | **partial**: no plugin updates waiting (the REST API cannot say; `across_sites.py:11`) |

##### Spot checks of three full rows

- **Comments** (`wordpress_admin_commands._show_comments`): every Action is a closure that runs `site_job` or `background` against `comments.set_status`, `reply`, `edit_comment` or `set_many`, and updates the live rows. Show... reloads with a new status, and Waiting Count on First Use writes the site profile. All handlers are wired.
- **Previous Looks and Menu History** (`wordpress_route_history.py`): Go Back confirms, then calls `restore_look` (a POST to `global-styles/{id}`). Restore This Version calls `restore_navigation`, and Bring Back calls `bring_back`. Every handler is gated by `with_route` and its `routes.FEATURES` entry. All wired.
- **Fonts** (`wordpress_design_commands._show_fonts`): Install reads `font-collections`, asks for a choice, confirms, then POSTs the family and each face. Delete confirms, then sends a forced DELETE. All wired.

##### Routes the code calls

Core WordPress routes called: **75 of 135**.

- **`wp/v2`, 61 routes:**
  - `posts`, `posts/{id}`, `posts/{id}/revisions`, `posts/{id}/autosaves`, and the same four for `pages`;
  - `types`;
  - `categories`, `categories/{id}`, `tags`, `tags/{id}`;
  - `media`, `media/{id}`, `media/{id}/edit`, `/sideload`, `/finalize`, `/post-process`;
  - `comments`, `comments/{id}`;
  - `users`, `users/{id}`, `users/me`, `users/{id}/application-passwords`, `.../{uuid}`, `.../introspect`;
  - `settings`;
  - `block-types`, `block-renderer/{name}`, `blocks`, `blocks/{id}`, `block-patterns/patterns`, `pattern-directory/patterns`, `wp_pattern_category`;
  - `global-styles/{id}`, `global-styles/{id}/revisions`, `global-styles/themes/{s}`, `global-styles/themes/{s}/variations`;
  - `themes`;
  - `font-collections`, `font-families`, `font-families/{id}`, `font-families/{id}/font-faces`;
  - `menus`, `menus/{id}`, `menu-items`, `menu-items/{id}`, `menu-locations`, `navigation`, `navigation/{id}`, `navigation/{id}/revisions`;
  - `sidebars`, `widgets`, `widgets/{id}`;
  - `templates`, `template-parts`;
  - `plugins`, `plugins/{plugin}`;
  - `icons`, `icon-collections`.
- **The REST index `/`.**
- **`wp-block-editor/v1`:** `url-details`, `export`.
- **`wp-site-health/v1`:** `tests/{test}` (driven by the index: 6 on WordPress 7.1, 5 in the fallback list) and `directory-sizes`.
- **`wp-abilities/v1`:** `abilities`, `abilities/{name}/run`.
- **`oembed/1.0/proxy`.**
- **`batch/v1`.**

Never called, though the table names them: `search`, `statuses`, `taxonomies`, `block-patterns/categories`, `block-directory/search`, `widget-types` (with `encode` and `render`), template `lookup` and revisions, navigation autosaves, menu-items revisions and autosaves, `navigation-fallback`, `wp-abilities/v1/categories`, and `view-config` (by design).

##### Called, but not named in the table

- The REST index `/`, read by `site_features.read_index`, `site.load_site_info`, `schedule.site_time_zone` and `site_admin.site_check`.
- `global-styles/themes/{stylesheet}`, the theme's base styles. It is read by Site Styles, Palette Report, Block Settings presets and Check This Page.
- `users/{id}/application-passwords/{uuid}`, the DELETE behind Revoke and Sign Out.
- `menus/{id}`, for Locations.
- Custom post-type and custom-taxonomy routes at `wp/v2/{rest_base}`, with their revisions and autosaves, through `kind_route` and `taxonomy_route`.
- Plugin namespaces that are not among the 135:
  - `tribe/events/v1`: `events`, `events/{id}`, `venues`;
  - `wc/v3`: `products/{id}`, `orders`;
  - `baf/v1`: `forms`, `forms/{id}`, `entries`, `entries/{id}` (Forms);
  - Yoast and Rank Math fields go through post meta on the kind route.

##### Gaps to build, by user value

1. **Install a missing block** (`block-directory/search`): Insert Block cannot offer a block the site lacks, though the table promises it.
2. **Custom taxonomies and custom statuses** (`taxonomies`, `statuses`): Properties and Categories and Tags know only category and tag, and the status list is fixed. Sites with custom post types usually have both.
3. **Space Used inside Site Check, and a warning before a big upload** (`directory-sizes`): the route is called today only by a separate Manage command.
4. **Offer Regenerate Sizes after Edit a Picture on the Site** (`post-process`): it is a separate command today, so an edited picture keeps stale thumbnails.
5. **Use url-details where the plan puts it:** speak the target in Link to a Page on This Site, and offer the fix for a vague link from Check Before Publishing.
6. **Word in and out:** Download My Writing writes only Markdown, and Send a Folder as Drafts skips `.docx`.
7. **Upload a Large File needs a details step and resume:** there is no title, alt or caption, and it cannot carry on after a failure. It also reads the whole file into memory.
8. **Widgets beyond Text** (`widget-types` with `encode` and `render`): legacy widgets cannot be edited or previewed.
9. **Site-wide `search`**: Open by Web Address and Link to a Page would then find custom post types, and Site-wide Find would no longer have to walk every collection.
10. **Menu undo for classic menus and Navigation autosaves:** history exists only for changes made after the Menus window first read the menu. Fix the 9.16 row too, since core probably registers no menu-items revisions or autosaves.
11. **Behaviour tests** for `cmd_versions`, `cmd_trash`, `cmd_compare`, `cmd_new_post`, `cmd_open_by_address`, `cmd_open_local_draft`, `cmd_open_on_site`, `cmd_switch_site`, `cmd_sites`, `cmd_connect` and `cmd_check`. Today they have only Lite's delegation test.
12. **Docs:** the user-guide chapters name only the menus and nine keys, and the 7 tutorials skip menus, users, Site Check, fonts and every 9.16 command. Everything else is only in the shared manual.
13. **Smaller items:**
    - template `lookup` and revisions;
    - `wp-abilities/v1/categories`;
    - `block-patterns/categories`;
    - `navigation-fallback`;
    - delete the dead comment functions in `site_media.py`.

### 9.18 Everything wp-admin does: the parity checklist (2026-11-04)

Jeff, 2026-11-04: "we should have all of this." Everything a site owner can do in wp-admin, QUILL and QUILL Lite do too, accessibly; what the REST API cannot reach opens the right wp-admin screen instead, said plainly.


Read-only audit, 2026-11-04. Code: `S:\wt\quill-docs`. Live site: https://lp.csedesigns.com/wordpress (WordPress 7.1.4), public REST index fetched without sign-in (802 routes, 27 namespaces).

##### How to read this

- Both editors build their WordPress menus from `quill/core/wordpress/menu.py` (`PLACES`), so every row here is the same in QUILL and QUILL Lite. There is no separate Lite column.
- Status words:
  - **full**: QUILL does everything that screen does.
  - **partial**: QUILL does some of it; what is missing is named.
  - **missing**: a REST route exists, and QUILL does not use it.
  - **in progress**: one of the fifteen items already being built. Not counted as a gap.
  - **not possible**: no REST route on the live site. The honest alternative is listed in the last section.
- Command paths are given as menus, for example Tools > WordPress > Comments. "Open in Dashboard" means QUILL's existing button that opens the matching wp-admin screen in the browser (Themes, Plugins and Widgets have one today).
- Roles are WordPress's default roles. Shop Manager is WooCommerce's.
- Each screen ends with a "Gaps" list giving the route, the role and an accessibility note for each missing or partial row.

##### Dashboard

| Capability | Status | QUILL today |
|---|---|---|
| At a Glance (counts of posts, pages, comments; version; theme) | partial | Site Check reports the version; no counts anywhere |
| Activity (recently published, publishing soon, recent comments) | partial | Your Sites > Coming Up (scheduled) and What Changed on My Sites (new posts and comments), across sites; no single-site view |
| Site Health status widget | full | Tools > WordPress > Site Check (tests from `wp-site-health/v1`) |
| Quick Draft | full | File > WordPress > New Post, then Save Draft to Site |
| WordPress Events and News | not possible | Comes from api.wordpress.org, not the site |
| Plugin dashboard widgets (WooCommerce status, Yoast overview) | missing | None |

Gaps:
- **At a Glance.** Routes: `wp/v2/posts`, `pages`, `comments` with `per_page=1`, reading the `X-WP-Total` header for each status; `wp/v2/themes?status=active`; the index for the version. Role: any signed-in author sees their own; Editor sees all. Accessibility: a short report dialog, one sentence a line ("12 posts published, 3 drafts, 4 comments waiting"), with a Refresh button. Counts are the information, so never only a coloured bubble.
- **Activity for one site.** Routes: `wp/v2/posts?status=future`, `posts?orderby=date&per_page=5`, `comments?per_page=5`. Role: Author or higher. Accessibility: one ListWindow with three headed groups read as rows ("Publishing soon: ..."), Enter opens the item.
- **Plugin widgets.** Routes: `wc-analytics/reports/performance-indicators` (WooCommerce), `yoast/v1/seo_scores` and `yoast/v1/readability_scores` (Yoast). Role: Shop Manager; Editor for Yoast. Accessibility: fold into the At a Glance report as extra sentences when the namespace is present.

##### Posts and Pages: the list screens

| Capability | Status | QUILL today |
|---|---|---|
| List all items, newest first | full | File > WordPress > Open Page or Post (OpenDialog list) |
| Search by title | full | Open: "Find by title or status" box (also sends `search`) |
| Filter by status (All, Published, Drafts, Pending, Scheduled, Private) | partial | Find box matches status words locally; no status choice, counts per status not shown |
| Filter by date (month) | missing | None |
| Filter by category, tag, author, format | missing | None |
| Custom post types (Products, Events, Venues) | full | Open asks for the kind when the site has custom types |
| Custom statuses | in progress | (statuses work package) |
| Bulk actions: Edit (status, author, categories, tags, comments, parent) | full | Tools > WordPress > Manage > Bulk Edit, with Undo |
| Bulk actions: Move to Trash | missing | Bulk Edit has no Trash field; trash is one at a time |
| Quick Edit (title, slug, date, author, password, private, categories, tags, status, sticky, comments) | partial | Properties covers it for the open document; no Quick Edit from the list without opening the item; author and date are not editable there |
| Sticky | full | Properties: "Keep at the top of the blog" |
| Author column and change author | partial | Shown in Properties About box; changeable only in Bulk Edit |
| Password protected | full | Properties: "Password to read it" |
| Private | full | Properties: Status = Private |
| Move to Trash | full | File > WordPress > Move to Trash; Open > Move to Trash |
| Restore from Trash | full | Open > Restore from Trash |
| Delete Permanently, Empty Trash | missing | None (QUILL never force-deletes posts) |
| View Trash as a list | partial | Restore from Trash lists trashed items; no browse-only view |
| Duplicate (not core, common) | full | Send and Copy > Duplicate |
| Page hierarchy and order | full | Manage > Page Order; Site Map |
| Screen Options (columns, items per page) | not possible | Browser-only UI setting; QUILL lists use their own fixed columns |

Gaps:
- **Status filter with counts.** Route: `wp/v2/{kind}?status=X` and `X-WP-Total`. Role: Contributor+. Accessibility: a "Show" choice above the list ("Drafts (3)"), like the Comments window's Show button, so the count is spoken with the label.
- **Date, category, tag, author and format filters.** Routes: `wp/v2/posts` args `after`, `before`, `categories`, `tags`, `author`, `format` (all on the live index). Role: Contributor+. Accessibility: a "Filter..." button that opens one dialog with labelled choices; the list title then says the filter ("Posts in Recipes, March 2026: 14"), and a Clear Filter button returns focus to the list.
- **Bulk Trash.** Route: `batch/v1` of `DELETE wp/v2/{kind}/{id}` (no `force`). Role: Editor for others' items. Accessibility: add "Move to Trash" to Bulk Edit's field choice with a count confirmation ("Move 6 posts to the Trash?") and Undo Bulk Edit restoring them.
- **Quick Edit from the list.** Route: `POST wp/v2/{kind}/{id}`. Role: Author for own, Editor for others. Accessibility: a "Properties..." button in Open that runs the same Properties dialog against the selected row without loading the body; focus returns to the same row after saving.
- **Delete Permanently and Empty Trash.** Route: `DELETE wp/v2/{kind}/{id}?force=true`. Role: Editor (delete_others_posts) or Author for own. Accessibility: only in the Trash view, with a confirm that names the item and says it cannot be undone; default button is Cancel.

##### Posts and Pages: the editor

| Capability | Status | QUILL today |
|---|---|---|
| Title, content, blocks | full | The document; Insert > WordPress Block; View > WordPress Blocks |
| Featured image | full | Media Library > Set as Featured Image; Image dialog "Use as featured image" |
| Remove featured image | missing | No way to clear `featured_media` |
| Excerpt | full | Properties: Excerpt |
| Slug | full | Properties: Slug |
| Author | partial | Bulk Edit only; not in Properties |
| Post format | partial | New Post offers a format radio; cannot change it later |
| Parent page | partial | Page Order (Move In/Out) and Bulk Edit; not in Properties |
| Template (page and post template) | missing | Carried through save, never chosen |
| Order (menu_order) | full | Page Order |
| Discussion: allow comments | full | Properties: Allow comments |
| Discussion: allow pingbacks and trackbacks | missing | `ping_status` carried, not shown |
| Categories and tags | full | Properties check groups (posts) |
| Custom taxonomies (event categories, product categories) | in progress | (taxonomies work package) |
| Custom fields (registered meta) | full | File > WordPress > Custom Fields |
| Scheduling | full | File > WordPress > Schedule Publish |
| Change the publish date (back-date) | partial | Schedule sets a future date only |
| Revisions: list, compare, restore | full | Previous Versions; Compare with Site |
| Autosaves and conflict protection | full | Unsaved Version choice; conflict check on save |
| Preview a draft on the theme | partial | View > Preview Blocks renders locally; Preview and Review needs a published page; Open on Site opens the public link only |
| Synced patterns: insert, edit, unsync, create | full | Manage > Synced Patterns; Insert > WordPress Block |
| Footnotes | full | Handled as the `footnotes` meta with the blocks (`blocks.py`) |
| Block notes (7.0 notes) | full | Insert > Note on This Block; View > Block Notes |
| Comments on this post | partial | Comments window lists all comments site-wide; no "only this post" view |
| Post lock (someone else is editing) | not possible | No REST route exposes the edit lock |

Gaps:
- **Author, format, parent, template, pingbacks and publish date in Properties.** Routes: `POST wp/v2/{kind}/{id}` with `author`, `format`, `parent`, `template`, `ping_status`, `date` (all listed as POST args on the live index); choices from `wp/v2/users?who=authors`, `wp/v2/templates?post_type=X` and `wp/v2/types/{type}` (for supported formats). Role: author change needs Editor (edit_others_posts); the rest Author. Accessibility: plain `wx.Choice` rows with labels ("Author:", "Template:"), each with `SetHelpText`; date as the same typed-date field Schedule uses, read back in words. Keep the dialog in one column so Tab order follows reading order.
- **Remove featured image.** Route: `featured_media: 0`. Role: Author. Accessibility: a "Remove Featured Image" button in Properties, shown only when there is one, with the image's alt text named in the About box.
- **Preview a draft.** No REST route returns a signed preview link. Honest alternative: open `{site}/?p={id}&preview=true` in the browser where the person is signed in to wp-admin, and say so first ("Opens in your browser; you must be signed in there"). Role: Author.
- **Comments on this post.** Route: `wp/v2/comments?post={id}`. Role: Editor to moderate. Accessibility: open the existing Comments window pre-filtered, with the title saying the post's name.

##### Media

| Capability | Status | QUILL today |
|---|---|---|
| Browse the library (grid and list) | full | Tools > WordPress > Media Library (one accessible list; grid is visual only) |
| Search | full | Media Library: Find |
| Filter by type (images, audio, video, documents, unattached) | missing | None |
| Filter by month | missing | None |
| Upload | full | More Media > Upload Files, Upload from Web Address, Paste Image, Insert > Picture from This Computer |
| Big uploads with details and resume | in progress | (big-upload metadata and resume) |
| Edit alt text | full | Media Library: Edit Alternative Text, Suggest, Describe; Alt Text for the Whole Library |
| Edit title, caption, description | partial | Core function allows it (`update_media`); the Library has no button for it |
| Crop (free crop) | partial | Edit a Picture on the Site: crop to fixed ratios only, centred |
| Rotate and flip | full | Edit a Picture on the Site |
| Scale (resize the original) | partial | Make a Smaller Copy (local resize, new upload); REST edit has no scale |
| Attach to a post | full | Media Library: Attach to This Page or Post |
| Detach | missing | None |
| Used in (where a file appears) | full | Media Library: Used In (QUILL addition) |
| Delete permanently | full | Media Library: Remove from Library (downloads a copy first) |
| Regenerate sizes | in progress | (Regenerate Sizes) |
| Copy file URL | full | Media Library: Copy Address |
| Download file | partial | Remove from Library saves a copy; no plain Download button |

Gaps:
- **Type, unattached and month filters.** Route: `wp/v2/media` args `media_type`, `mime_type`, `parent=0` (unattached), `after`, `before`. Role: Author sees own, Editor all. Accessibility: a "Show" choice ("All files, Pictures, Audio, Video, Documents, Not attached") and a month choice, both before the list in Tab order; the list label speaks the filter and count.
- **Edit details.** Route: `POST wp/v2/media/{id}` with `title`, `caption`, `description`. Role: Author for own. Accessibility: an "Edit Details..." button opening one dialog of labelled multi-line fields; caption and description help text say where each shows.
- **Free crop.** Route: `POST wp/v2/media/{id}/edit` with `x`, `y`, `width`, `height` (percent). Role: Author. Accessibility: numeric fields in percent plus the existing presets; read back "keeps the middle 80 percent of the width". Never drag-only.
- **Detach.** Route: `POST wp/v2/media/{id}` with `post: 0`. Role: Author. Accessibility: a Detach button that names the page it leaves.
- **Download.** Route: the item's `source_url`. Role: Author. Accessibility: a Download... button with a Save As box.

##### Comments

| Capability | Status | QUILL today |
|---|---|---|
| Lists by status: Pending, Approved, Spam, Trash | full | Tools > WordPress > Comments: Show... |
| All (every status together) | missing | One status at a time |
| Approve, Unapprove | full | Comments |
| Spam, Not Spam | full | Comments |
| Trash, Restore | full | Comments |
| Delete Permanently, Empty Spam, Empty Trash | missing | None |
| Reply | full | Comments: Reply... |
| Edit (content) | partial | Edit... changes text only; author name, email, URL and date are not editable |
| Bulk actions | full | Mark, Mark Everything, Do with Marked..., Approve All... |
| Threading | full | Replies listed under their parent |
| Search comments | missing | None |
| Filter by post or by type (comments, pingbacks, reviews) | missing | None |
| Waiting count | full | Waiting Count on First Use |
| Per-post discussion settings | partial | Properties: Allow comments; pingbacks missing (see Editor) |
| Site Discussion settings | partial | Site Settings has the two defaults; the rest are not in REST (see Settings) |

Gaps:
- **Delete Permanently and Empty Spam/Trash.** Route: `DELETE wp/v2/comments/{id}?force=true` (batch for Empty). Role: Editor (moderate_comments). Accessibility: only in the Spam and Trash views; confirm with the count ("Permanently delete 37 spam comments?"); announce the result count.
- **All, search, by post, by type.** Route: `wp/v2/comments` args `status=all`, `search`, `post`, `type`. Role: Editor. Accessibility: add "All" to Show; a Find box above the list like the Media Library; the window title says the filter.
- **Edit author fields.** Route: `POST wp/v2/comments/{id}` with `author_name`, `author_email`, `author_url`, `date`. Role: Editor. Accessibility: one dialog with labelled fields; email field help says it is private.

##### Appearance, part 1: Themes, Site Editor, Customize, Widgets

| Capability | Status | QUILL today |
|---|---|---|
| Themes: list, details, what it supports | full | Manage > Themes |
| Themes: activate, live preview | not possible | `wp/v2/themes` is GET only |
| Themes: install, update, delete | not possible | No REST route |
| Site Editor: Styles (colours, type, variations, history) | full | Design > Site Styles, Style Variations; Manage > Previous Looks; Palette Report |
| Site Editor: Additional CSS | missing | Not read or written |
| Site Editor: Fonts | full | Manage > Fonts |
| Site Editor: Navigation | partial | Tools > WordPress > Menus, Menu History; autosaves and fallback in progress |
| Site Editor: Pages | full | Open, Page Order, Site Map |
| Site Editor: Templates (list) | full | Manage > Template Outline (report) |
| Site Editor: Templates (open, edit, create, reset to theme) | missing | Report only |
| Site Editor: template lookup and revisions | in progress | (template lookup and revisions) |
| Site Editor: Template Parts (header, footer: open, edit, create) | missing | Report only |
| Site Editor: Patterns (synced, theme, directory) | full | Synced Patterns; Insert Block > WordPress.org Patterns |
| Site Editor: pattern categories | in progress | (pattern and ability categories) |
| Site Editor: export the theme | full | Manage > Download a Copy of the Site's Design |
| Customize (classic themes: site identity, colours, homepage) | partial | Logo, icon, title, tagline, homepage in Site Settings and Site Logo; theme mods are not in REST |
| Widgets: list areas, add Text, edit, move, remove | full | Manage > Widgets |
| Widgets: every widget type | in progress | (every widget type) |

Gaps:
- **Additional CSS.** Route: `POST wp/v2/global-styles/{id}` with `styles.css`. Role: Administrator (edit_css; `unfiltered_html` on single site). Accessibility: open the CSS as a plain-text document in QUILL with Save to Site; warn first that CSS changes the whole site, and keep the previous version in Previous Looks.
- **Edit templates and parts.** Routes: `GET/POST wp/v2/templates/{id}` and `wp/v2/template-parts/{id}` (content is block markup, same as a page), `POST wp/v2/templates` to create, `DELETE` to reset a customised one to the theme. Role: Administrator (edit_theme_options). Accessibility: open as a WordPress document through the same block tools, with the document title "Template: Single Post" so the reader always knows it is not a page; Reset asks with the template name.

##### Appearance, part 2: Menus, Background, Header, theme file editor

| Capability | Status | QUILL today |
|---|---|---|
| Menus: add pages, posts, categories, links; reorder; nest; remove | full | Tools > WordPress > Menus |
| Menus: locations | full | Menus: Locations... |
| Menus: create, rename, delete a menu; Edit Item dialog | in progress | (full menu editing) |
| Menus: auto-add new pages | missing | `auto_add` not offered |
| Background (classic) | not possible | Theme mod, no REST |
| Header image (classic) | not possible | Theme mod, no REST |
| Theme File Editor | not possible | No REST route; also disabled on many hosts |

Gaps:
- **Auto-add new pages.** Route: `POST wp/v2/menus/{id}` with `auto_add`. Role: Administrator (edit_theme_options). Accessibility: a check box in the menu-editing dialog being built; fold it into that work package rather than a separate one.

##### Plugins

| Capability | Status | QUILL today |
|---|---|---|
| List with status and description | full | Manage > Plugins |
| Activate, deactivate | full | Plugins: Activate or Deactivate... |
| Install from WordPress.org by slug | full | Plugins: Add Plugin... |
| Search the plugin directory | not possible | Site REST has no directory search (only `block-directory/search`, for block plugins, in progress) |
| Delete | full | Plugins: Delete... |
| Update | not possible | `wp/v2/plugins` accepts `status` only |
| Enable or disable auto-updates | not possible | No `auto_update` argument on this site's route |
| Network activate | not possible | Single site; see Multisite |

##### Users

| Capability | Status | QUILL today |
|---|---|---|
| List users with role | full | Manage > Users |
| Filter by role, search | missing | None |
| Add user (username, email, name, role; password emailed) | full | Users: Add User... |
| Add user: first and last name, website, send notification choice | partial | Name only; WordPress sends no notification over REST |
| Edit user (name, email) | full | Users: Edit... |
| Edit user: first name, last name, nickname, bio, website, language | partial | Bio and website only on My Profile; others not offered |
| Change role | full | Users: Change Role... |
| Delete with reassign | full | Users: Delete... ("Give their posts and pages to") |
| Your profile: display name, bio, website | full | Users: My Profile... |
| Your profile: first/last name, nickname, email, language, new password | partial | Not offered |
| Your profile: admin colour scheme, toolbar, keyboard shortcuts | not possible | Browser-only preferences |
| Application passwords: list, revoke, which is QUILL's | full | Manage > Application Passwords |
| Application passwords: create one by name | missing | Only made through Connect a Site |
| Sessions: log out everywhere | not possible | No REST route for sessions |

Gaps:
- **Role filter and search.** Route: `wp/v2/users` args `roles`, `search`. Role: Administrator (list_users). Accessibility: a Find box and a Role choice before the list, the list label carrying the count.
- **The rest of the profile fields.** Route: `POST wp/v2/users/{id}` or `users/me` with `first_name`, `last_name`, `nickname`, `email`, `locale`, `password`. Role: self for `me`; Administrator for others. Accessibility: one Profile dialog in a single column; New Password uses the existing password field style, a Show check box, and never echoes the value in speech or logs. Email change says WordPress may ask for confirmation.
- **Create an application password.** Route: `POST wp/v2/users/{id}/application-passwords` with `name`. Role: self, or Administrator for others. Accessibility: show the new password once in a read-only field with Copy, say "shown only now", and never write it to settings or logs.

##### Tools

| Capability | Status | QUILL today |
|---|---|---|
| Import (WXR, Blogger, RSS) | not possible | No REST; Send a Folder as Drafts is the partial alternative |
| Export (WXR) | not possible | No REST; Download My Writing (Markdown; Word and HTML in progress) |
| Site Health: Status tab | full | Site Check |
| Site Health: Info tab (server, PHP, database, constants) | not possible | No core REST; WooCommerce's `wc/v3/system_status` covers much of it on shop sites |
| Site Health: directory sizes | in progress | (Space Used in Site Check) |
| Export Personal Data | not possible | No REST route |
| Erase Personal Data | not possible | No REST route |
| Scheduled Actions (WooCommerce Action Scheduler) | not possible | No REST route on the live index |
| Theme and plugin file editors | not possible | No REST route |
| Category to tag converter | full | Categories and Tags (convert_term) |

##### Settings

| Capability | Status | QUILL today |
|---|---|---|
| General: title, tagline, admin email, language, time zone, date and time formats, week start, site icon | full | Tools > WordPress > Site Settings |
| General: WordPress Address and Site Address | partial | Not offered; REST exposes `url` only. Deliberately left out is reasonable |
| General: membership, new user default role | not possible | Not in REST settings |
| Writing: default category, default post format | full | Site Settings; Categories and Tags > Make Default |
| Writing: post via email, update services | not possible | Not in REST settings |
| Reading: front page displays, front page, posts page, posts per page | full | Site Settings |
| Reading: feed items and full text or excerpt, search engine visibility | not possible | Not in REST settings |
| Discussion: default comment and ping status | full | Site Settings |
| Discussion: moderation, approval, avatars, threading, pagination, notifications | not possible | Not in REST settings |
| Media: thumbnail, medium and large sizes; uploads folder | not possible | Not in REST settings |
| Permalinks | not possible | Not in REST settings |
| Privacy: privacy policy page | not possible | Not in REST settings |
| Emoticons | full | Site Settings |

##### Updates

| Capability | Status | QUILL today |
|---|---|---|
| WordPress core update | not possible | No REST route |
| Plugin updates | not possible | No REST route |
| Theme updates | not possible | No REST route |
| Translation updates | not possible | No REST route |
| Know that updates are waiting | not possible | No REST route; `wp-site-health/v1/tests/background-updates` only says whether automatic updates can run (already in Site Check) |

##### WooCommerce (wc/v3)

Today: product price, sale price and stock in Properties and Plugin Fields (`plugin_shop_seo.py`), products open as the `product` post type, and Plugin Extras > Shop Orders (read-only list, Copy Order). Everything else is missing. All rows need Shop Manager or Administrator (manage_woocommerce), except where noted.

| Capability | Status | Routes on the live index |
|---|---|---|
| Products: list, search, filter (category, type, stock) | partial | `wc/v3/products` (Open lists them as posts, no shop filters) |
| Products: create and edit every field (type, SKU, prices, sale dates, stock, shipping class, dimensions, downloads, images, upsells) | partial | `wc/v3/products`, `products/{id}`; QUILL edits price, sale price and stock only |
| Products: duplicate | missing | `products/{id}/duplicate` |
| Products: bulk edit | missing | `products/batch` |
| Variations: list, edit, generate | missing | `products/{id}/variations`, `/batch`, `/generate` |
| Attributes and their terms | missing | `products/attributes`, `/{id}/terms` |
| Categories, tags, brands | missing | `products/categories`, `products/tags`, `products/brands` (also `wp/v2/product_cat`; custom taxonomies are in progress) |
| Shipping classes | missing | `products/shipping_classes` |
| Reviews: list, approve, reply, spam, delete | missing | `products/reviews`, `/batch` |
| Orders: list, read | full | Shop Orders |
| Orders: filter and search | missing | `wc/v3/orders` args `status`, `search`, `after`, `customer` |
| Orders: change status | missing | `POST orders/{id}` with `status`; `orders/statuses` |
| Orders: create or edit line items, addresses | missing | `POST orders`, `orders/{id}` |
| Orders: notes (private and to customer) | missing | `orders/{id}/notes` |
| Orders: refunds | missing | `orders/{id}/refunds`, `/refunds/preview` |
| Orders: resend emails, receipt | missing | `orders/{id}/actions/send_email`, `send_order_details`, `receipt` |
| Coupons | missing | `coupons`, `/batch` |
| Customers: list, edit, downloads | missing | `customers`, `customers/{id}/downloads` |
| Reports: sales, top sellers, totals | missing | `reports/sales`, `top_sellers`, `orders/totals` and the rest |
| Analytics (revenue, orders, products, stock, taxes) | missing | `wc-analytics/reports/*` |
| Settings (general, products, tax, accounts, emails, advanced) | missing | `settings`, `settings/{group}`, `/batch` |
| Shipping zones, locations, methods | missing | `shipping/zones`, `/{id}/locations`, `/{zone}/methods` |
| Tax rates and classes | missing | `taxes`, `taxes/classes` |
| Payment gateways: enable, settings | missing | `payment_gateways`, `/{id}` |
| Webhooks | missing | `webhooks` |
| System status and tools | missing | `system_status`, `system_status/tools/{id}` |
| WooCommerce marketplace and subscriptions | not possible | Routes exist but are for Woo.com account linking; not a site-owner editing task. Open in Dashboard |

Accessibility notes for the whole shop:
- One "Shop" window per area (Products, Orders, Customers, Coupons, Reports, Store Settings), each the standard ListWindow so it reads like Comments and Media Library.
- Money always spoken with the currency name from `data/currencies/current` ("12 dollars 50"), never a bare symbol.
- Order status changes, refunds and customer-notes send email to a customer: confirm each one with the order number, amount and what the customer will receive. Refunds through a gateway move money; QUILL should present the refund the shop owner chose, require an explicit confirm, and say whether the gateway or only the record is refunded (`api_refund`).
- Customer names and addresses stay in memory, as Shop Orders does now; no export without a confirm.
- Reports: sentences and a small table, never a chart only.
- Webhooks: a secret field uses the password style and is never spoken back.
- Payment gateway settings may hold API keys: show them as password fields and never log them.

##### The Events Calendar

Today: Plugin Extras > Events Coming Up (list), New Event (title, start, end, venue), start, end and venue in Properties, and events open as the `tribe_events` type.

| Capability | Status | Routes / gap |
|---|---|---|
| Events: list upcoming | full | Events Coming Up |
| Events: list past, search, filter by category or venue | missing | `tribe/events/v1/events` args `start_date`, `end_date`, `search`, `categories`, `venue` |
| Events: create with title, start, end, venue | full | New Event |
| Events: all-day, time zone, cost, website, organizer, categories, tags, featured, sticky, hide from listings, show map | missing | `POST tribe/events/v1/events/{id}` (all are args on the live index) |
| Events: edit date and venue after creation | partial | Properties shows them; Plugin Fields changes start and end; venue and the rest not |
| Events: description and excerpt | full | The document body and Properties excerpt |
| Events: recurring events | not possible | Events Calendar Pro only; not on this site |
| Venues: list | partial | Read for New Event's choice only |
| Venues: create, edit, delete (address, city, state, zip, country, phone, website, map) | missing | `tribe/events/v1/venues`, `/{id}` |
| Organizers: list, create, edit, delete (name, email, phone, website) | missing | `tribe/events/v1/organizers`, `/{id}` |
| Event categories and tags | missing | `tribe/events/v1/categories`, `tags` (and `wp/v2/tribe_events_cat`; custom taxonomies in progress) |
| Calendar settings | not possible | No REST route for TEC settings |
| Importers (Event Aggregator) | not possible | Routes exist only for an import already running; setup is browser-only |

Role: Author can add own events; Editor for others'; venues and organizers follow the same caps.
Accessibility: event dates spoken with day names, as `plugin_events.spoken_span` already does; the Event dialog groups When, Where, Who and Cost with labelled sections; venue and organizer choosers have "New Venue..." beside them so the person never leaves the dialog; an all-day check box disables the time fields and says so.

##### Yoast SEO

Today: SEO title and meta description, with their lengths, in Properties and Plugin Fields (registered meta `_yoast_wpseo_title`, `_yoast_wpseo_metadesc`).

| Capability | Status | Routes / gap |
|---|---|---|
| SEO title, meta description | full | Plugin Fields |
| Focus keyphrase | missing | Registered meta `_yoast_wpseo_focuskw` (on the live index) |
| Search appearance preview (what Google shows) | missing | `yoast/v1/get_head?url=`; `yoast_head_json` on each item |
| SEO and readability scores, per post and site-wide | missing | `yoast/v1/seo_scores`, `readability_scores` |
| Bulk editor (titles and descriptions for many posts) | missing | `yoast/v1/bulk_editor/posts`, `update_search`, `update_social` |
| Social title, description, image | missing | `bulk_editor/update_social` (no registered meta for these) |
| Related keyphrases (Semrush), rank tracking (Wincher) | not possible | Routes exist but need the person's third-party account; Open in Dashboard |
| Yoast settings, site representation, social profiles | partial | Only the first-time configuration routes exist (`configuration/*`); the full settings pages are browser-only |
| Indexing (SEO data optimisation) | missing | `yoast/v1/indexing/*` |
| Redirects, schema, breadcrumbs settings | not possible | Premium or browser-only |
| Yoast AI features | not possible | Need a Yoast account; QUILL's own AI covers the writing side |

Role: Author for own posts' fields; Editor for the bulk editor and scores; Administrator for indexing and configuration.
Accessibility: the preview is spoken as three lines (title, address, description) with "cut off after N characters" when Google would truncate; scores as words ("SEO: good, Readability: needs improvement"), never only coloured dots; the bulk editor is a ListWindow with an Edit... button per row and Undo.

##### QUILL Accessible Forms (baf/v1)

Today: Forms publish a form (create and update), find pages that show it, and a Responses window (Read, View, Find, Mark, Export to CSV and Word, Open as Table, Summarise, Delete).

| Capability | Status | Routes / gap |
|---|---|---|
| Forms: list | full | Forms on site lists them |
| Forms: create, update | full | Publish Form |
| Forms: draft or published status | partial | Publish sends a status; no way to switch an existing form back to draft |
| Forms: delete or trash | missing | `DELETE baf/v1/forms/{id}` |
| Forms: settings (notifications, confirmation, limits) | missing | `settings` on `POST baf/v1/forms/{id}`; QUILL keeps the site's `config` but never edits `settings` |
| Forms: import from other plugins | in progress | (form importers) |
| Entries: list, read, export, delete | full | Responses |
| Entries: star, mark read, change status | missing | `POST baf/v1/entries/{id}`; `GET entries` takes `starred`, `status` |
| Entries: search on the site | partial | Responses Find is local; `search` arg unused |
| Views (saved entry views) | missing | `baf/v1/views` |
| Conditional cascade data | full | Used by the model (`cascade/{id}`) |

Role: Administrator (BAF's own capabilities; check BAF for an Editor-level cap).
Accessibility: form settings as one labelled dialog grouped by Notifications, Confirmation and Limits; notification email fields validated with errors next to the field; starring announced ("starred, 3 starred").

##### Multisite network admin

- **Applicable?** Not to the live site: the index has no network namespace and no `wp/v2/sites` route, so it is a single site.
- **What REST allows on a network:** core registers no network-admin routes at all. Sites, network users, network plugins and network themes are wp-admin only. On a subsite, the ordinary routes work per site, and QUILL already treats each subsite as its own connection.
- **Honest alternative:** a "Network Admin" button that opens `{site}/wp-admin/network/` in the browser when the index reports multisite. Super Admin role.

##### Totals

| Status | Rows |
|---|---|
| full | 81 |
| partial | 32 |
| missing | 59 |
| in progress | 10 |
| not possible | 40 |

##### Gaps to build

Each package touches its own files. Every package also adds one or two rows to `quill/core/wordpress/menu.py` and to `keymap.py`'s documentation fixtures; those are one-line merges, so agree an order for menu.py and nothing else collides. Every new command needs a Lite `cmd_wp_*` hand-off (generated from the table), F1 help strings, a GATE-LITE-COVER classification, and a behavioural test.

1. **Lists and filters for posts, pages and media (medium).** Status, date, category, tag, author and format filters in Open; Media type, unattached and month filters; Bulk Trash; Delete Permanently and Empty Trash; Quick Edit from Open.
   - Files: `quill/core/wordpress/site.py` (`list_items` params), `quill/core/wordpress/site_library.py` (`BULK_FIELDS`), `quill/ui/wordpress_open_commands.py`, `quill/ui/wordpress_media_library.py` (filters only), `quill/core/wordpress/site_media.py` (`list_media` params).
2. **Properties, the rest of the editor sidebar (medium).** Author, format, parent, template, pingbacks, publish date, remove featured image; comments for this post.
   - Files: `quill/ui/wordpress_item_dialogs.py` (`PropertiesDialog`), `quill/ui/wordpress_more_commands.py` (`cmd_properties`), `quill/core/wordpress/site.py` (template and author choices). Coordinate with the in-progress custom statuses and taxonomies work, which touches the same dialog: build this after it lands, or in the same branch.
3. **Media details (small).** Edit title, caption and description; detach; download; free crop by numbers.
   - Files: `quill/core/wordpress/media_edit.py`, `quill/ui/wordpress_picture_edit_commands.py`, a new `quill/ui/wordpress_media_details.py` hooked from the library's action list.
4. **Comments, complete (small).** All, search, by post and type, Delete Permanently, Empty Spam and Trash, edit author fields.
   - Files: `quill/core/wordpress/comments.py`, `quill/ui/wordpress_admin_commands.py` (`_show_comments` and `_ACTIONS`).
5. **People, complete (small).** Role filter and search, full profile fields and password change, create an application password.
   - Files: `quill/core/wordpress/site_admin.py` (user functions), `quill/ui/wordpress_people_commands.py`.
6. **Dashboard (small).** At a Glance with counts, single-site Activity, plugin summary sentences.
   - Files: new `quill/core/wordpress/dashboard.py`, new `quill/ui/wordpress_dashboard_commands.py`, one row in `menu.py`.
7. **Site Editor writing (medium).** Open, edit, create and reset templates and template parts as documents; Additional CSS as a document.
   - Files: `quill/core/wordpress/site_structure.py`, `quill/ui/wordpress_structure_commands.py`, `quill/core/wordpress/site_styles.py`, `quill/ui/wordpress_look_commands.py`. Coordinate with the in-progress template lookup and revisions work.
8. **WooCommerce catalog (large).** Products with every field, duplicate, bulk edit, variations, attributes, categories, tags, brands, shipping classes, reviews.
   - Files: new `quill/core/wordpress/shop_catalog.py`, new `quill/ui/wordpress_shop_catalog_commands.py`; leave `plugin_shop_seo.py` untouched except to import from the new module.
9. **WooCommerce orders and customers (large).** Order filters, status, notes, refunds, emails, create orders; coupons; customers; reports and analytics.
   - Files: new `quill/core/wordpress/shop_orders.py`, `quill/ui/wordpress_shop_commands.py` (extend Shop Orders), new `quill/ui/wordpress_shop_reports_commands.py`.
10. **WooCommerce store settings (medium).** Settings groups, shipping zones and methods, taxes, payment gateways, webhooks, system status and tools.
    - Files: new `quill/core/wordpress/shop_settings.py`, new `quill/ui/wordpress_shop_settings_commands.py`.
11. **The Events Calendar, complete (medium).** Full event fields, past and filtered lists, venues and organizers with create, edit and delete, event categories and tags.
    - Files: `quill/core/wordpress/plugin_events.py`, new `quill/ui/wordpress_events_commands.py` (move the events parts out of `wordpress_plugin_commands.py`).
12. **Yoast SEO, complete (medium).** Focus keyphrase, search preview, scores, bulk editor, social fields, indexing.
    - Files: new `quill/core/wordpress/plugin_seo.py` (split from `plugin_shop_seo.py`), new `quill/ui/wordpress_seo_commands.py`. Add `yoast/v1` read routes to `network_egress_audit` notes if the audit lists namespaces.
13. **Forms on the site, complete (small).** Delete or trash a form, switch status, edit form settings, star and status for entries, server search, views.
    - Files: `quill/core/forms/baf_site.py`, `quill/ui/forms_publish_commands.py`, `quill/ui/forms_responses_commands.py`.
14. **Open in Dashboard for every screen REST cannot reach (small).** One submenu, Tools > WordPress > Manage > Open in Dashboard, listing Updates, Import, Export, Export and Erase Personal Data, Site Health Info, Permalinks, Discussion, Media and Privacy settings, Themes (activate, install), Customize, Theme File Editor, Scheduled Actions, Network Admin (multisite only).
    - Files: new `quill/core/wordpress/admin_screens.py` (screen -> wp-admin path, role needed), new `quill/ui/wordpress_dashboard_links.py`, one submenu in `menu.py`.

##### Not possible over REST

| What | Honest alternative |
|---|---|
| WordPress Events and News widget | Open https://wordpress.org/news/ in the browser; not site-specific |
| Screen Options | Not needed; QUILL's lists choose their own columns |
| Post edit lock | Conflict protection on save (already built) |
| Theme activate, live preview, install, update, delete | Open in Dashboard: Appearance > Themes (`themes.php`) |
| Customize: Background, Header, theme mods | Open in Dashboard: Customizer (`customize.php`) |
| Theme and plugin file editors | Open in Dashboard (`theme-editor.php`, `plugin-editor.php`); warn that many hosts disable them |
| Plugin directory search | Open `plugin-install.php?s=` in the browser; or, with consent and a new `network_egress_audit` entry, read api.wordpress.org's plugins info API, then install by slug as today |
| Plugin and theme updates, auto-update toggles | Open in Dashboard: `update-core.php` and `plugins.php` |
| WordPress core and translation updates | Open in Dashboard: `update-core.php` |
| Knowing updates are waiting | Open in Dashboard; Site Check keeps saying whether automatic updates can run |
| Profile preferences (colour scheme, toolbar, shortcuts) | Open in Dashboard: `profile.php` |
| Log out other sessions | Open in Dashboard: `profile.php` (Sessions section); or revoke application passwords in QUILL |
| Import (WXR, Blogger, RSS) | Send a Folder as Drafts; or Open in Dashboard: `import.php` |
| Export (WXR) | Download My Writing; or Open in Dashboard: `export.php` |
| Site Health Info tab | WooCommerce sites: `wc/v3/system_status` gives the environment; otherwise Open in Dashboard: `site-health.php?tab=debug` |
| Export and Erase Personal Data | Open in Dashboard: `export-personal-data.php`, `erase-personal-data.php` |
| WooCommerce Scheduled Actions | Open in Dashboard: `admin.php?page=wc-status&tab=action-scheduler` |
| General: membership and default role | Open in Dashboard: `options-general.php` |
| Writing: post by email, update services | Open in Dashboard: `options-writing.php` |
| Reading: feeds, search engine visibility | Open in Dashboard: `options-reading.php` |
| Discussion: moderation, avatars, threading, notifications | Open in Dashboard: `options-discussion.php` |
| Media sizes and upload folders | Open in Dashboard: `options-media.php` |
| Permalinks | Open in Dashboard: `options-permalink.php` |
| Privacy policy page | Open in Dashboard: `options-privacy.php` |
| WooCommerce marketplace and subscriptions | Open in Dashboard: WooCommerce > Extensions |
| Events Calendar settings | Open in Dashboard: Events > Settings |
| Event Aggregator importers | Open in Dashboard: Events > Import |
| Recurring events | Needs Events Calendar Pro; not installed |
| Yoast: Semrush and Wincher | Open in Dashboard; needs the person's own third-party account |
| Yoast: full settings, redirects, schema, breadcrumbs | Open in Dashboard: Yoast SEO > Settings |
| Yoast AI features | QUILL's own AI for writing help; Yoast AI needs a Yoast account |
| Multisite network admin | Open `wp-admin/network/` in the browser when the site is multisite; Super Admin only |
| WordPress Address and Site Address | Deliberately not offered: a typo locks the owner out. Open in Dashboard: `options-general.php` |

## 10. Optional AI

These reuse what the family already has. Choose Your AI decides which AI, and
nothing new is invented here.

- **Ask About This Document:** this already exists, and works unchanged on a
  WordPress document.
  - It asks about the selection, or the whole page when nothing is
    selected.
  - The answer opens in a read-only window and is never inserted.
- **Change Text with AI:**
  - the user says what to change;
  - the AI returns a proposal, which has three views:
    - an explanation of the passages affected and the new wording;
    - the whole proposed document;
    - its Markdown or HTML source;
  - the user reads it and then chooses Apply or Change Instructions;
  - Apply is one undo step, so Ctrl+Z takes it back;
  - a version is kept;
  - nothing is sent to the site.
- **The existing AI text tools** work on WordPress documents unchanged, on
  the selection or the whole page. These include:
  - spelling and grammar;
  - summarise;
  - plain language;
  - friendlier;
  - step by step.
- **Suggest Alt Text:**
  - the existing Propose Alt Text, fed the image and the paragraph around it;
  - its answer goes into the alt text field to be edited, never saved by
    itself;
  - it is reachable from Upload, Edit Details and inserted images.
- **Describe Image:**
  - the existing Ask About an Image, for any library item;
  - it gives a longer description for the user, not for visitors.
- **Visual Review, the Picture Maker and the site logo:** section 6, from
  6.9 on.
- **In Short:** section 9.11.

Every AI action says what it will send before it sends it. That uses the
existing privacy agreement, not a new prompt.

## 11. QUILL Lite

The same commands, on the same keys, from the same shared code. That follows
the hosted AI pattern:

- the shared modules are `quill/core/wordpress/` and `quill/ui/wordpress_*`;
- QUILL reaches them through a small adapter mixin;
- QUILL Lite reaches them through its command table;
- a test asserts that neither side has a second implementation.

**This reverses a written decision.** `quill/apps/lite.py` says Lite has "no
publishing". The reason to reverse it is that WordPress is writing, and the
person who wants a light editor is very often the person who keeps a small
site. The docstring, the About text in `lite_window_commands.py` and the
Lite PRD change in the same pull request.

QUILL gets it first or at the same time, never after. That follows the rule
that QUILL Lite may never be ahead of QUILL.

## 12. Menus and keys

**Where each command lives (Jeff, 2026-11-04).** Commands go where Word users
already look for them, not all in one WordPress submenu. File > WordPress keeps
only what is about a whole document or a site. Everything you do *inside* a
page joins the ordinary menus.

**When they show:**

- **The rows exist** whenever the WordPress feature is on (the profile and
  Customize Features decide that, as for every feature).
- **They are enabled** only when the document in front of you is a WordPress
  document.
- **Elsewhere they are dimmed,** and choosing one, or pressing its key, says
  why: "Insert Block works in a WordPress page or post. Open one with File,
  WordPress." A command is never silent.
- **The Command Palette** lists them the same way.

| Menu | WordPress commands there |
|---|---|
| **File > WordPress** | New Page, New Post, Open Page or Post, Open by Web Address, Open Local Draft; Save Draft to Site, Publish or Update, Schedule Publish; Open on Site, Copy Address; Properties, Previous Versions, Compare with Site, Move to Trash; Switch Site, Sites, Connect a Site |
| **Insert** | Block... (with the site's patterns); Picture from the Media Library...; Picture from This Computer... (the existing Insert Picture, uploading on send); Link to a Page on This Site...; Make a Picture... |
| **Format** | Block Settings...; Image Size...; Mark Language... |
| **View** | Blocks (the tree window); Preview Blocks |
| **Edit** (or wherever each editor keeps structure navigation) | Next Block, Previous Block; Where Am I (block) |
| **Tools > WordPress** | Check Before Publishing; Check This Page; Check the Whole Site; Site-wide Find and Replace; Alt Text Review; Visual Review; Media Library; Comments; Categories and Tags; Menus; Site Check and Settings; Manage (users, plugins, themes, fonts, synced patterns) |

**The same placement in both editors.** QUILL Lite has the same Insert, Format,
View, Edit and Tools menus, so a command is in the same place in both. The
rows come from the one shared table (`quill/core/wordpress/menu.py`), which
now names each row's menu.

**The menu, in order:** the File > WordPress submenu keeps its groups, minus
what moved:

1. New Page, New Post, Open Page or Post, Open by Web Address, Open Local
   Draft.
2. Save Draft to Site, Publish or Update, Schedule Publish, Open on Site,
   Copy Address.
3. Properties, Previous Versions, Compare with Site, Move to Trash.
4. Switch Site, Sites, Connect a Site.

**Keys:**

- **Every command gets a key or a written reason** (rule 8).
- **The everyday five** get short keys: Open, Save Draft to Site, Publish or
  Update, Media Library and Switch Site. They are chosen by the family rules
  when this is built. QUILL Lite reaches them plainly, so they are not put on
  QUILL's leader (rule 6). Any divergence between the two editors is a
  `keymap.py` comment and a parity row (rule 11).
- **The once-in-a-while commands** (Sites, Move to Trash) get a key, not a
  short one (rule 9).

**Help:**

- every dialog and control answers F1 (GATE-<APP>-HELP);
- each window's purpose is authored inline;
- the docs teach the chords, so GATE-DOCKEY and the documentation-chords gate
  cover them.

## 13. Speaking

- **Speak only what the screen reader does not already say:**
  - the outcome of a background request ("Draft saved to Community Radio");
  - progress on long work ("Uploading 2 of 5");
  - failures, which are always spoken with the reason.
- **Never speak:** dialog titles or focus.
- **No command is silent.** Publish with no connection says "Connect a
  WordPress site first", and offers Connect.
- **Braille shows what is spoken**, through the announcement service
  (GATE-BRAILLE).

## 14. Safety and privacy

- **HTTPS only.** This is the existing `_validate_endpoint_security`.
  Loopback is allowed for local test sites.
- **Secrets:** application passwords and WordPress.com tokens are kept in
  Credential Manager, never in settings JSON and never in logs. The
  redaction filter learns both shapes.
- **Network egress:** every new endpoint gets a `network_egress_audit` entry:
  - media;
  - categories;
  - tags;
  - revisions;
  - search;
  - users/me;
  - WordPress.com OAuth;
  - the public API.
- **Destructive actions:**
  - Trash is recoverable;
  - removing media is the one permanent action, and it is preceded by a
    local copy and a named confirmation.
- **Unconfirmed sends:** if a send is not confirmed (time-out, lost
  connection), the local draft stands. QUILL re-reads the site before
  offering to try again, so it never creates a duplicate post.
- **Safe Mode** turns all of this off, like the other network features.

## 15. One release

There are no phases. Everything in this document ships together, in QUILL and
QUILL Lite at once, as one feature called "WordPress":

- **One feature flag:** "WordPress" replaces `future.publishing` and
  `future.publishing_read`, and is on by default in every writer profile.
  Decided by Jeff, 2026-11-03.
- **Settings move with it:** existing saved connections and linkage carry
  over unchanged.

The work is built in this order inside the one branch, because each step
needs the one before it. Nothing is released until all of it is done.

1. **Foundation:**
   - the shared `quill/core/wordpress/` and `quill/ui/wordpress_*` layer;
   - the flag;
   - roles and capabilities (9.2);
   - every REST route and its egress entry;
   - recorded fixtures for a self-hosted and a WordPress.com site.
2. **Connect:**
   - self-hosted (4.1, 4.2);
   - WordPress.com (4.3);
   - many sites (4.4);
   - Sign Out This Site (9.10).
3. **Pages and posts:**
   - New, Open, Open by Web Address, local drafts, autosaves (9.3), the three
     saves, conflict protection;
   - Properties;
   - Trash;
   - Previous Versions.
4. **Blocks:** the whole of section 8.
5. **Media:**
   - the Media Library and the image dialog (6.1 to 6.7);
   - alt text and descriptions (6.8);
   - the Picture Maker (6.9);
   - the site logo (6.10);
   - captions, transcripts, listening versions, embeds and documents (9.6).
6. **Checks:**
   - Check Before Publishing (7);
   - writing accessibly (9.11);
   - colours (9.7);
   - Visual Review (6.11);
   - Check This Page and Check the Whole Site, with Fix in Bulk and
     Site-wide Find and Replace (9.4, 9.5);
   - the accessibility statement (9.12).
7. **Running the site:**
   - Comments (9.8);
   - Menus, Widgets, Site Map and Template Outline (9.9);
   - Site Check and Site Settings (9.10);
   - administration: categories and tags, users, plugins, themes, bulk edit,
     page order, synced patterns, fonts (9.13).
8. **AI:** Change Text with AI and In Short (10).
9. **Across the family:**
   - **QUILL Cast and Audio Studio:** Post This Episode uploads the audio,
     with its transcript (9.6), and opens a post with the player, show notes
     and chapters filled in.
   - **Quill Converter:** gains Upload to WordPress as a destination.
   - **Working offline:** drafts waiting to send are queued, and announced
     when the connection returns.
10. **Docs, gates and the QUILL Lite parity test** (17).

## 16. Open questions

None.

Settled on 2026-11-03:

- **One "WordPress" feature**, on by default, replaces the two publishing
  flags (section 15).
- **Used In** (6.1) runs by itself in the background the first time a site's
  Media Library is opened, when the site has 500 pages and posts or fewer,
  and keeps its answers up to date from then on. On a larger site it runs
  on request, per file. Either way, the answers are cached per site.
- **The WordPress submenu goes under File**, in both editors (section 12).
- **WordPress.com sign-in** is the authorization code flow with PKCE as a
  public client, so no secret ships. Jeff registers the app and passes on the
  client id (section 4.3).
- **The application-password handback** returns automatically by loopback on
  sites with r62096, and falls back to paste on older ones (section 4.2).

## 17. Done means

- **The core tasks work in both editors, on more than one site:** a person
  can connect a self-hosted site and a WordPress.com site, write a post with
  an image from the Media Library, publish it, fix a sentence on a page from
  its web address, and get yesterday's wording back.
- **They work with a screen reader alone.**
- **The visitor side works:** Check the Whole Site runs on a real site,
  finds its problems, fixes the content ones in one batch with Undo, and
  writes the accessibility statement. Every image capability in 6.6 works.
- **Every command has a key, F1 help and a spoken outcome.**
- **Everything is tested:** each core function has a unit test against a
  recorded REST fixture, and each command has a behavioural test (the
  GATE-LITE-COVER shape), with no live network.
- **Every gate passes:** `platform_report` and the menu, key, docs and egress
  gates.
- **Documented:** the user guides of both editors have a WordPress chapter in
  a human voice, and the changelogs are updated.

## 17a. Forms (merged from forms.md, 2026-11-04)

Forms are written in BITS Accessible Forms' language (BFL) and published to
sites running BAF, so they belong with the rest of WordPress. They also work
with no site at all, as web pages, Word documents and braille-ready copies.

### 17a.1 What this is

Write, check, try out and publish accessible forms from QUILL and QUILL Lite:
contact forms, event registrations, membership renewals, surveys and feedback
forms. You write the form as a short, readable text document, in the editor
you already use, and QUILL turns it into:

- a form on a WordPress site;
- a standalone web page;
- a printable or large-print document;
- a braille-ready copy.

You can fill it in yourself, with your screen reader, before anyone else
sees it, and read the responses afterwards in a list.

**Why.** Building a form today almost always means a drag-and-drop canvas,
which is one of the hardest things on the web for a screen-reader user. But a
form is really structured text: a title, pages, sections, questions, choices
and rules. QUILL is good at text.

**QUILL Accessible Forms (QAF)**, first called BITS Accessible Forms (BAF)
(`S:\code\qaf`, which was `S:\code\baf` until 2026-11-08), is the WordPress side. It is a
WCAG 2.2 AA form plugin with a plain form language, BFL (Barrier-Free
Language), a REST API, 30+ field types, choice libraries, conditional logic
and entry views. QUILL does not build a second form engine for the web. It
becomes the accessible way to write, check and manage BAF forms, and it brings
over everything from BAF that makes sense on a computer rather than a server
(17a.3).

**Four rules shape the plan:**

1. **Simple first.** A contact form is New Form, three questions, Publish.
2. **Both editors.** QUILL and QUILL Lite get the same forms, from one shared
   module. Lite is never behind and never ahead (CLAUDE.md).
3. **One language.** Forms are written in BFL, exactly as BAF reads it. No
   third syntax beside Markdown and QUILL's `:::` fences.
4. **People's answers are private.** Responses stay on the site. QUILL reads
   them only when asked, says what it is downloading, and never writes them to
   a log.

### 17a.2 What already exists

**In QAF (`S:\code\qaf`):**

- **BFL:** the form language, with:
  - four block styles (indentation, braces, square brackets, begin/end);
  - labels and `#ids`;
  - modifiers (`@required`, `@placeholder`...), in four syntaxes;
  - choices (`value|label`, `label:price`), choice libraries;
  - pages, sections, and `if` blocks with operators.
- **The reference:** the BFL language guide,
  `docs/user-guide/bfl-language-guide.md`.
- **REST API (`baf/v1`):**
  - `/forms` and `/forms/{id}`;
  - `/entries` and `/entries/{id}`;
  - `/submit/{form_id}`;
  - `/bfl/parse` and `/bfl/validate`;
  - cascades.
- **Field types:**
  - **Basic:** text, email, number, textarea, select, radio, checkbox,
    date/time, phone, URL, password, colour, range.
  - **Advanced:** file upload, signature, rating, Likert, NPS, ranking,
    repeater, address, name, hidden, HTML, section, page break.
  - **Payment:** Stripe, PayPal, calculation.
- **Choice libraries:** about 60, covering countries and regions, states and
  provinces, time zones, days, months and years, time slots, currencies,
  languages, phone codes and contact preferences.
- **Behaviour:**
  - conditional logic;
  - multi-page forms;
  - input masks;
  - smart defaults (`geo`, `today+N`, `user:*`);
  - unique validation;
  - calculations;
  - cascading choices.
- **Entry views:** table, cards, list, map and calendar.
- **Integrations:** email notifications, webhooks, Google Sheets, PDF, Stripe,
  PayPal.
- **Security:** CSRF, honeypot, rate limiting, CAPTCHA, sanitising, file
  validation.

**In QUILL:**

- the WordPress connection, sites, REST client and Check Before Publishing
  machinery (`wordpress.md`);
- Table and CSV Studio for tabular data;
- Word, HTML and EPUB export;
- braille output;
- the shared-module pattern for QUILL and Lite;
- Choose Your AI.

### 17a.3 What comes over from BAF, and what stays there

| From BAF | In QUILL | Why |
|---|---|---|
| BFL, all four block styles, modifiers, choices, pages, sections, `if` blocks | **Yes:** a Python BFL reader and writer in the shared core, byte-faithful to BAF's | The form *is* the document |
| BFL validation | **Yes:** locally, with BAF's error messages, and through `/bfl/validate` when connected | Errors while you type, not at publish |
| All field types except payment | **Yes:** in Insert Field, the preview and every export | |
| Choice libraries (about 60) | **Yes:** ported as data, the same names, so `@choices countries` works offline | Search a library by name in Insert Field |
| Conditional logic, calculations, cascades, smart defaults, input masks, unique validation | **Yes:** a shared evaluator, so the preview behaves like the site | Fill It In Yourself must be honest |
| Multi-page forms and sections | **Yes** | |
| Entry views: table, list | **Yes:** the Responses window, and export to Table and CSV Studio | |
| Entry views: cards, calendar, map | **As accessible equivalents:** grouped by date (calendar), grouped by place (map), one response per page (cards) | The information, without the picture |
| PDF from entries | **Yes:** through QUILL's own export of one response, or all of them | |
| Email notifications, confirmations, redirects, submission limits, scheduling | **Yes, as form settings** in a Form Properties window, written to BAF | They are form settings, not code |
| Webhooks, Google Sheets | **Settings only,** shown and edited by name; the secrets stay in WordPress | |
| Stripe, PayPal, payment fields | **The form's side only** (2026-11-06/07): the payment field and the form's payment settings, test mode first, under payment contract version 1. Keys, checkout and webhooks stay in WordPress (`forms-payments-design.md`) | Never handle payment secrets |
| CAPTCHA, honeypot, rate limiting, CSRF | **No; server-side.** QUILL shows whether each is on, read-only | |
| Google Places address autocomplete | **No; server-side** | It needs the site's key |
| Drag-and-drop builder | **No.** The text document is the builder | |
| Accessibility runtime (ARIA, live regions, focus) | **Stays in BAF.** QUILL's standalone HTML export uses the same patterns | |

### 17a.4 Writing a form

#### 17a.4.1 New Form

- **Where:** File > New > Form..., in both editors.
- **It asks for:**
  - the title;
  - a template: blank, contact, event registration, membership renewal,
    survey, accessibility feedback, or volunteer sign-up;
  - where it will live: a WordPress site with BAF, or "just this computer"
    for HTML and print.
- **The result:** a BFL document (`.bfl`), with syntax colouring where the
  editor has it, and headings for pages and sections in heading navigation.

#### 17a.4.1a What a form looks like in the document

A form is plain BFL text, one question per few lines, so it reads naturally
line by line and every editor tool works on it:

```bfl
form "Spring fair sign-up"
@submit_label "Sign me up"

section "About you"

text "Your name" #name
@required
@autocomplete name

email "Email address" #email
@required
@help "We only use this to confirm your place."

radio "How did you hear about us?" #heard
  "A friend"
  "Our newsletter"
  "Somewhere else"

if heard is "Somewhere else"
  text "Where?" #heard_other

page

select "Which session?" #session
@choices time_slots_hourly
```

- **Headings:** a `section` line and a `page` line are headings for heading
  navigation, so you can jump between parts of a long form.
- **Labels:** a question's label is in quotes, followed by its `#id`.
- **Settings:** the lines starting `@` underneath set what it does.
- **Indented lines** are its choices, or the questions a rule shows.
- **Rules:** an `if` line reads as the sentence it is.
- **No hidden markup.** There is nothing but this text.

#### 17a.4.2 Insert Field

- **Where:** Insert > Form Field..., with a key.
- **The list:** every field type, searchable, with a one-line description.
- **On choosing one:** a short form asks only what that field needs, for
  example label, id, required, help text, choices, or a choice library
  (searchable). Insert writes BFL at the caret, in the block style the
  document already uses.
- **Insert Section** and **Insert Page Break** sit beside it.

#### 17a.4.3 The form outline

- **Where:** View > Form Outline.
- **What it shows:** a tree of pages, sections and fields. Each row reads
  "Email address, email field, required, page 1".
- **What you can do:**
  - Enter goes to the field;
  - Move Up and Down, and In and Out, with Alt+Shift and the arrows;
  - Duplicate, Remove;
  - Change Type.
- **Undo:** each is one undo step.
- **The same shape as the WordPress Blocks window,** so it is learned once.

#### 17a.4.4 Rules in sentences

**Rules** (Format > Form Rules...) lists every condition as a sentence:

- "Show Company name when Type is Business."
- "Total is Quantity times Price."
- "Show State when Country is United States."

Add Rule builds one from three choices: when what, is what, then what. QUILL
writes the BFL `if` block, and reads the sentence back. Nobody has to edit
rule syntax unless they want to.

#### 17a.4.5 Form Properties

Form Properties... holds everything that is not a question:

- submit label, success message, redirect;
- notifications and autoresponders;
- submission limits and scheduling;
- whether CAPTCHA and the honeypot are on (read-only);
- the BAF form id and site, once published.

### 17a.5 Checking a form

**Check This Form** runs locally while you write, as Check Before Publishing
does for pages (section 7). Every finding says what to fix, with Go to
It. It looks for:

- a field with no visible label, or a label that is only a placeholder;
- a group of choices (radio, checkbox, Likert) without a group question;
- required fields marked only by an asterisk or colour;
- a field with a format rule (mask, pattern, minimum) and no help saying what
  is expected;
- name, email, phone and address fields without autofill hints (the
  `autocomplete` tokens BAF writes);
- a rule that points at an id that does not exist, or hides a required field
  forever;
- a page with no questions, or a form over 30 questions on one page;
- duplicate ids;
- a choice list over 15 items that would be easier as a library or a search.

BFL errors (an unclosed block, an unknown modifier) appear in the same list,
with BAF's own wording, and so do the site's `/bfl/validate` results when
connected.

### 17a.6 Fill It In Yourself

**Fill It In Yourself** builds the form as a real, native window in QUILL,
from the same BFL, with the shared rules evaluator. You tab through it exactly
as a visitor would:

- labels, groups, help text, errors and required states are announced;
- pages have Next and Back;
- conditions show and hide fields as you answer;
- calculations update.

Submit does not send anything. It shows what would be sent, as a list of
question and answer pairs, and checks every rule. Test on Site sends one
marked test entry through `/submit/{id}` when connected, so the whole path
can be proved. It is deleted afterwards if the account can.

This is the feature only QUILL can offer: a screen-reader user hears their own
form before anyone else does.

### 17a.7 Publishing and exporting

- **Publish Form (to a site with BAF):**
  - it creates or updates the form through `/forms`, after a confirmation
    naming the site;
  - conflict protection and previous versions work as for pages
    (5.4, 5.6);
  - Insert Form Into Page puts the form's block or shortcode into a
    WordPress page.
- **Save As Web Page:** a standalone, accessible HTML form, using BAF's
  markup patterns. It submits to an address you give, or nowhere when it is
  for printing.
- **Save As Word Document:** a printable form, with lines to write on, and
  check boxes as boxes. A large-print version uses 18 point and up.
- **Save As Braille-Ready Text:** one question per block, with choices
  listed, through QUILL's braille output.
- **One source, every format,** so a paper form and its web form can never
  disagree.

### 17a.8 Responses

- **Responses...** lists a form's responses newest first: "Response 41,
  3 November, 2:10 PM, Jane Smith, Event registration".
- **Views:**
  - **list;**
  - **one at a time:** question and answer pairs, read line by line;
  - **grouped by date:** the calendar view;
  - **grouped by place:** the map view.
- **Find:** across every answer.
- **Export:**
  - to Table and CSV Studio, as an accessible grid;
  - to CSV;
  - to a Word document for one response, or all of them.
- **Delete:** a response, or several, after a confirmation that gives the
  count.
- **Waiting count:** "4 new responses to Event registration", when you open a
  site, like waiting comments in WordPress. You can turn this off.
- **Privacy:** responses are downloaded only when Responses is open, kept in
  memory, and never written to a log. Exports go where you choose.

### 17a.9 AI, optional

Through Choose Your AI, as everywhere else in QUILL:

- **Draft a Form:** describe it in a sentence, get BFL to read and edit. It
  is a proposal, applied as one undo step.
- **Plain Language:** rewrite the questions and help text more simply,
  proposed for review.
- **Suggest Autofill Hints and Help Text:** for the fields Check This Form
  flagged.
- **Summarise Responses:** a written summary of a survey's answers. It sends
  the answers to the AI, so it asks first, every time, and says how many
  responses it would send.

### 17a.10 QUILL Lite

Forms come to QUILL Lite in the same change as QUILL, from the same shared
modules:

- the core in `quill/core/forms/`, wx-free;
- the windows in `quill/ui/forms_*`;
- QUILL reaches them through a small mixin, Lite through its command table;
- a test asserts there is no second implementation.

**A new Lite area, Forms:**

- on in Recommended and Everything;
- off in WordPad and Notepad, which never made forms.

With WordPress and Coding, Lite has 24 areas, and the counts in the profile
descriptions and the guide are recounted at merge.

**Placement is the same in both editors:**

- New Form in File > New;
- Form Field in Insert;
- Form Outline in View;
- Form Rules in Format;
- Check This Form, Fill It In Yourself and Responses in Tools > Forms.

The keys follow the family rules (`keymap.py` comments and parity rows).

### 17a.11 Safety

- **Never handles payment keys or settings,** CAPTCHA keys, or the address
  lookup key. They stay in WordPress.
- **The network:** every new BAF route gets a `network_egress_audit` entry.
  Nothing is sent without a deliberate Publish, Test on Site or Delete.
- **Personal data:** responses are personal data (17a.8). Summarise
  Responses asks every time.
- **Safe Mode** turns off publishing, responses and the AI. Writing,
  checking, Fill It In Yourself and exporting still work, because they are
  local.

### 17a.12 One release

As with WordPress, there are no phases. Everything here ships together. It is
built in this order, because each piece needs the one before:

1. **The core, in `quill/core/forms/`:**
   - the BFL reader and writer, with conformance tests against BAF's own
     `tests/` fixtures and the language guide's examples;
   - the form model;
   - the choice libraries;
   - the rules evaluator.
2. **Writing:** New Form, templates, Insert Field, the outline, Rules, Form
   Properties. In both editors.
3. **Check This Form,** and Fill It In Yourself.
4. **Exports:** web page, Word, large print, braille-ready.
5. **The BAF connection:**
   - Publish Form, Insert Form Into Page, Test on Site;
   - Responses, with its views and exports;
   - the waiting count.
6. **AI.**
7. **Docs and gates:**
   - a Forms chapter in both user guides;
   - tutorials;
   - the PRDs, changelogs and release notes;
   - F1 help, the keyboard reference;
   - the regression plan, with BAF installed on the test site
     (lp.csedesigns.com/wordpress);
   - every gate.

### 17a.13 Open questions for Jeff

1. File extension for a form document: `.bfl`, or `.form.md` so other editors
   show it as text?
2. Should BAF's PHP BFL parser and QUILL's Python one share a conformance
   suite in the BAF repository, so the two can never disagree?
3. May the test site install QAF from `S:\code\qaf` for the regression plan?

### 17a.14 Is BFL complete? Not yet (checked against BAF's code, 2026-11-04)

BAF has 67 field classes (`includes/fields/`). Its BFL parser recognises fewer.

**Field types BFL cannot write or read today** (absent from the parser's
type list, the compiler, and the language guide):

- **Input:** appointment, colour, currency, range and slider, toggle, OTP
  (one-time code), rich text, typed signature.
- **Choice:** image choice, matrix (grid questions), NPS (net promoter
  score), quiz (questions with scoring).
- **Other:** map, payment, progress, social, summary, table.
- **Validator gaps:** the validator also rejects the WordPress fields BAF
  supports for posting content and registering users: post title, content,
  excerpt, image, category, tags and custom field; user email, login and
  password.

`columns` and `page` work, as layout keywords rather than field types.

**What this means:** a form built in BAF's visual builder with any of those
fields cannot be exported to BFL and back without losing them. So today BFL is
a subset of BAF, not its whole language.

**Combinations BFL cannot express yet:**

- **Conditions are single tests.** The operators are is, contains, starts,
  ends, greater, less, empty and filled. There is no "and" or "or" in one
  condition, no "is not", no "is one of", and no "else". Nesting `if` blocks
  gives "and", but "or" needs the questions repeated.
- **No page-level or section-level conditions,** to skip a whole page.
- **No date comparisons** (before, after, within N days), and no comparing
  two fields with each other.
- **Calculations:** check the formula language against the calculation,
  total, price, quantity and coupon fields. Those fields exist, but are only
  partly reachable from BFL.
- **Repeaters with nested sections or conditions inside them:** untested.
- **Quiz scoring and outcomes** (score to message), and **save and resume**
  (the `save` field): not in BFL.

**The plan:** make BFL complete in BAF itself. That is the language's home, and
QUILL must match it byte for byte. Work in `S:\code\qaf`:

1. One written BFL specification, beside the guide, listing every field type
   with its modifiers, every block style, and the condition and calculation
   grammar.
2. Add the missing field types to the lexer, parser, validator, compiler,
   exporter and formatter, with an example of each in the guide.
3. Extend conditions:
   - `and`, `or`, `not`;
   - `is one of`;
   - `else`;
   - date operators;
   - field-to-field comparison;
   - conditions on `page` and `section`.

   Every condition still reads as a sentence.
4. Quiz scoring, outcome messages, and save and resume.
5. **A round-trip conformance suite:** every field type and every
   combination is built in the visual builder, exported to BFL, imported
   again, and compared. The same fixtures run against QUILL's Python reader
   (17a.13, question 2).
6. Only then does QUILL's Insert Field offer the new types, and Check This
   Form learns their accessibility rules. For example:
   - a matrix needs row and column headers;
   - a colour picker needs a typed alternative;
   - a map needs a written location field;
   - an OTP field needs its digits announced one at a time.

Until BFL is complete, QUILL keeps any field it cannot express as an island
(the same idea as unknown blocks, 8.1). It is shown as one protected line, and
sent back unchanged, so opening a form in QUILL never loses a field.

### 17a.15 The foundation: a JSON form model, with BFL as its readable face (Jeff, 2026-11-04)

This replaces 17a.14's plan of extending BFL on its own. BFL stays what
people write, but it is no longer the definition.

1. **The form model.** A documented JSON model, with a published JSON Schema,
   is the single definition of a form:
   - fields and their types;
   - pages and sections;
   - choices and choice libraries;
   - rules, calculations and scoring;
   - smart defaults and masks;
   - translations;
   - settings and confirmations;
   - a `version`.

   BAF stores this model. BAF's visual builder, BFL, and QUILL's windows are
   all views of it. Every feature exists in the model first, so no view can
   fall behind.
2. **One expression language** for conditions, calculations, quiz scoring and
   smart defaults. It is small and fully specified:
   - `and`, `or` and `not`;
   - comparisons, and `is one of`;
   - dates (before, after, within N days);
   - field references and arithmetic.

   The model stores the expression. BFL and QUILL show it as a sentence
   ("Show Company name when Type is Business or Type is Charity").
3. **BFL becomes a readable notation of the model, and nothing more:**
   - every model feature has a BFL spelling;
   - BFL to model, and model to BFL, round-trip exactly;
   - BAF's PHP and QUILL's Python both check against the same schema,
     instead of two parsers trying to agree.

   The missing field types and conditions (17a.14) are added to the model
   first, then given their BFL spelling.
4. **Import and export,** each a mapping to and from the model:
   - SurveyJS JSON;
   - XLSForm (the spreadsheet form standard in community and humanitarian
     work);
   - Google Forms, through its API;
   - plain HTML forms;
   - the WordPress form plugins: Gravity Forms, WPForms, Contact Form 7 and
     Ninja Forms.

   Anything a source has that the model cannot hold is listed in an import
   report, never silently dropped.
5. **Translations built in:** one form, several languages, with each
   language's labels, help and messages side by side. Fill It In Yourself can
   be run in each language.
6. **Versioning:**
   - **The form:** each form carries the model version it was written for.
   - **Old forms:** older forms are upgraded by a documented migration, and
     never broken.
   - **BFL:** a form written in BFL carries its version on its first line.
7. **A shared conformance suite, in the BAF repository:**
   - the schema;
   - an example of every field type and every rule shape;
   - the round trips BFL to model to BFL, and builder to model to builder;
   - every import and export.

   QUILL runs the same fixtures against its Python reader in CI.

**Where the work happens:**

- `S:\code\qaf`: the model, the schema, the expression language, BFL's
  mapping, the builder's mapping, the conformance suite, and the imports and
  exports that run on the site.
- `quill/core/forms/`: the same model and its expression evaluator in Python,
  BFL in and out, schema checking, and the imports and exports that run on the
  computer (XLSForm, SurveyJS, HTML). QUILL and QUILL Lite share it.

### 17a.16 BAF is the forms plugin (Jeff, 2026-11-05)

Forms on a site use BITS Accessible Forms (BAF). Nothing else on the site
needs a plugin: every other WordPress feature uses only WordPress's own REST
API and application passwords.

The reason a plugin is needed at all: WordPress has no forms. Something on the
site has to show the form to visitors, check and store their answers, send the
emails, and keep spam out. QUILL runs on the writer's computer, so it cannot
do that for visitors.

**Without BAF:** a site without BAF can still use a form saved as a standalone
web page (Save As Web Page). That page submits to an address the writer
chooses, and has no Responses window.

**Not now:** other form plugins (Gravity Forms, WPForms, Contact Form 7, Ninja
Forms) are supported for import only. Publishing to them is not planned unless
people ask for it.

### 17a.17 The name: QUILL Accessible Forms, and `.qaf` files (Jeff, 2026-11-05)

- **The plugin's new name:** BITS Accessible Forms (BAF) is renamed **QUILL
  Accessible Forms (QAF)**, in its plugin header, slug, text domain, readme,
  docs and admin screens.
- **The code:** the plugin is not released yet, so its code prefixes move as
  well:
  - the PHP class prefix `BAF_` becomes `QAF_`;
  - the REST namespace `baf/v1` becomes `qaf/v1`;
  - options, tables, hooks and shortcodes become `qaf_`.

  `baf/v1` stays as a read-only alias for one release, so a test site already
  running it keeps working.
- **Form files are `.qaf`.** That answers 17a.13 question 1: a form saved from
  QUILL or QUILL Lite is `name.qaf`, opened by File > Open, recognised by its
  first line (`bfl 1`, the form language's version), and associated with
  QUILL by the installer.
- **The language** inside a `.qaf` file keeps its readable form. It is called
  the QAF form language in user-facing text, rather than BFL.
- **QUILL's side:** menus, help, docs, tutorials, the regression plan, and the
  `.bfl` constant that becomes `.qaf`.

## 18. Progress log

**The rule (Jeff, 2026-11-04):** every fix and every feature is recorded in
three places when it is done:

1. here, in the progress log, saying what was done and how it was checked;
2. in the changelogs, QUILL's `CHANGELOG.md` and QUILL Lite's, in plain words;
3. by removing it from the Remaining tasks list at the bottom of this file.

Work is not finished until all three are done.

The work happens in the `S:\wt\quill-wordpress` worktree (moved from
`S:\QUILL-palette` on 2026-11-04), on the branch `feat/wordpress`, which is
cut from `origin/main`. Nothing is committed, by
request. Each entry says what is done and how it was checked.

### 2026-11-04: Command Palette, every command in both editors

- **QUILL:** every menu item is now in the palette. When the palette opens,
  any menu item that no registered command owns is added under its menu path,
  and runs by posting its own menu event. That covers recent files, open
  documents, the braille tools and the other dynamic rows. A dimmed item
  says it is not available instead of doing nothing.
  - New: `quill/ui/palette_menu_reach.py`.
  - The methods live in `main_frame_palette_labels.py`, to stay within
    GATE-11.
  - New: `CommandRegistry.unregister_prefix`.
- **QUILL Lite:**
  - The palette stays in every profile, including WordPad (now 6 of 21 areas)
    and Notepad (now 3 of 21).
  - It also lists the open windows and recent files from the window's own
    menu bar, without doubling table commands.
  - The "no command palette" line in `lite.py` is corrected.
- **Docs:** the QUILL user guide (palette section), the Lite user guide
  (profiles), the Lite PRD, and both changelogs.
- **Checked:**
  - New tests: `tests/unit/ui/test_palette_menu_reach.py` and
    `tests/unit/apps/test_lite_palette_menu_rows.py`, plus a real-frame
    check added to `test_quill_menu_accelerators.py` that no menu item is
    missing from the palette.
  - `tests/unit/core/lite`, `tests/unit/apps` (Lite and palette),
    `tests/unit/docs`: all pass.
  - ruff, mypy (`quill/core/commands.py`) and GATE-11 pass.
- **Not yet:** the rendered HTML and EPUB copies of the changed docs are
  regenerated at the end of the run.

### 2026-11-04: the palette is in Tools in both editors

- QUILL Lite's Command Palette moved from View to Tools, first in the menu,
  which is where QUILL keeps it. Ctrl+Shift+P is unchanged.
- Updated to match: the Lite user guide (Finding a command, and the key
  tables) and the Lite changelog.

### 2026-11-04: WordPress core, the shared wx-free layer (`quill/core/wordpress/`)

- **`api.py`:** the one door to a site.
  - Self-hosted and WordPress.com routes (`wp/v2/sites/<site>/...`).
  - Application-password Basic or Bearer signing, with the secret never in
    a repr.
  - HTTPS-only, except loopback and `.test` hosts.
  - Automatic paging by `X-WP-TotalPages`, raw-body uploads, and
    `batch/v1` in chunks of 25.
  - Every refusal turned into a plain sentence that names the site: 33
    WordPress error codes, plus every status. A PHP notice printed before
    the JSON is tolerated.
- **`site.py`:** one function per action.
  - Pages, posts and custom types: list, load (raw content, so block
    comments survive), create, update, Trash, restore, the conflict stamp,
    autosaves, and revisions with autosaves.
  - The account's roles and capabilities, so Publish becomes Submit for
    Review for a Contributor.
  - The REST index: name, version, namespaces and authorize URL.
  - Categories, tags and taxonomies: list, create, update, delete, merge
    (one batch).
  - Media: list, filter, upload with fields, update, delete, and finding a
    duplicate.
  - Comments: list, count waiting, moderate, reply.
  - Helpers: slug, sizes, friendly dates, plain text.
- **`sites.py`:** many sites with one default.
  - Open by Web Address matches by host and the longest path.
  - Secrets live in Credential Manager under the site id.
  - Old publishing connections are imported once, keeping their ids so
    their saved passwords still work.
- **`local.py`:** working copies keyed by site, kind and id.
  - Each keeps its fixed format, properties, the base `modified_gmt` and
    pictures not uploaded yet.
  - Previous Versions with reasons, newest first, capped at 50. Restore
    keeps what it replaces.
  - Conflict detection, with its spoken sentence.
- **`signin.py`** (built by a helper agent):
  - the Authorize Application handback: index URL, state, loopback
    support by version, redirect parsing, and password-shape detection;
  - a real `127.0.0.1` one-shot listener with an accessible reply page;
  - WordPress.com OAuth 2.1 PKCE: authorize URL, code, token and refresh
    requests, redacted token reprs, and an injected opener.
- **`checks.py`, `contrast.py`, `readability.py`** (built by a helper agent):
  - 24 kinds of Check Before Publishing findings, with a one-line summary;
  - WCAG contrast with colour names ("Accent (dark green), 7.4 to 1,
    passes") and a palette report;
  - a local reading level.
- **Checked:** 500+ tests in `tests/unit/core/wordpress/` pass with no
  network. ruff and mypy are clean on these modules.
- **In progress:** `blocks.py` and `fences.py`, the block grammar and
  Markdown fences, are being built by a helper agent.

### 2026-11-04: the windows and commands, in both editors

- **Core additions:**
  - `blocks.py` and `fences.py` are done, by a helper agent, and split into
    `fences.py`, `fences_write.py` and `fences_markup.py` for GATE-11.
    - The block grammar round-trips byte for byte.
    - Markdown fences: plain Markdown for ordinary blocks; `:::` lines for
      buttons, columns, groups, details, embeds and spacers; islands for
      anything else.
    - A block whose Markdown would not round-trip exactly stays an island,
      so nothing on a site is ever changed by being opened.
    - 174 tests, plus fuzzing of 3000 posts and 20000 inputs.
  - `signin.py` is split into `signin_base.py` and `signin_loopback.py`.
  - Media and comments moved to `site_media.py`.
  - `menu.py` is the one File > WordPress table both editors build from.
  - `api.py` gained unsigned requests for the REST index. `local.py` gained
    the document file: a WordPress document is an ordinary file under the
    data folder, so Ctrl+S is the local save.
- **Shared windows** (`quill/ui/wordpress_dialogs.py`,
  `wordpress_item_dialogs.py`):
  - Connect a Site, and Paste the Password;
  - a choose-one list;
  - one list-window shape for every "manage" window (a list, details, action
    buttons and Find);
  - New Page or Post, with the slug filled in from the title and Markdown or
    HTML;
  - Properties;
  - the image dialog;
  - a read-only report;
  - a text question;
  - named confirmations.

  Every control has inline F1 help, and OK, Cancel and Close carry no
  access key.
- **Shared commands** (`wordpress_commands.py` plus the `_open_`, `_more_`
  and `_site_` mixins, and `wordpress_connect.py`). There are 21 commands:
  - New Page, New Post;
  - Open Page or Post (site, kind, list, find, Open, Move to Trash), Open by
    Web Address (`?p=`, `?page_id=` or the slug), Open Local Draft;
  - Save Draft to Site, Publish or Update, Open on Site, Copy Address;
  - Properties, Previous Versions, Compare with Site, Check Before
    Publishing, Move to Trash;
  - Media Library (find, insert with the image dialog, edit alternative
    text, copy the address, remove after a local backup), Insert Picture
    from This Computer (uploaded on the next send, with addresses swapped
    in);
  - Comments (approve, reply, spam, trash), Categories and Tags (add,
    rename, merge, delete);
  - Switch Site, Sites, Connect a Site.

  How sending works:
  - The send checks for conflicts first. It offers Compare, Open the Site's
    Copy, or Send Mine Anyway.
  - It keeps the site's copy as a version before updating.
  - A Contributor's Publish becomes Submit for Review.
  - Private and Scheduled items keep their status.
  - The address goes on the clipboard after publishing.

  Connect verifies before saving. The browser route uses the loopback
  handback on new sites, and paste with a clipboard offer on older ones.
  WordPress.com says plainly that it waits on QUILL's app registration.
- **QUILL:**
  - `main_frame_wordpress.py` is an adapter only: the host, plus a
    File > WordPress submenu built from the table, with each row
    registered for the palette.
  - The older Publish submenu is replaced.
  - New feature `core.wordpress` is on in every profile except Essential.
- **QUILL Lite:**
  - `lite_window_wordpress.py` is an adapter only, with the same 21 rows in
    the command table under File > WordPress (no access key: every letter of
    the name is taken in File).
  - New area WordPress: on in Recommended and Everything, off in WordPad
    and Notepad.
  - The area count is now 22. The guide, PRD, changelog and tests are
    updated.
- **Keys: still an open question.** Of every Ctrl, Alt and Shift chord with
  a letter, digit or F-key, only Ctrl+Alt+Shift+Q and Ctrl+Alt+Shift+R are
  free in both editors. Until keys are chosen, the commands are reached by
  File > WordPress (the Alt path) and the Command Palette.
- **Checked so far:**
  - `tests/unit/apps/test_lite_wordpress.py`: 26 pass. It checks that every
    Lite row runs the shared command, that the two tables match, and that
    neither adapter has a second implementation.
  - The Lite command coverage snapshot is regenerated: 307 covered, 0
    shape-only.
  - Feature tests and the QUILL menu gates pass.
  - The full QUILL and Lite runs are in progress.
- **Not done yet:**
  - the WordPress chapters in both user guides;
  - the help and reachability snapshots;
  - the network egress entries;
  - Visual Review, the Site Check, page audits, captions, administration
    beyond terms, and the Picture Maker move.

### 2026-11-04: WordPress.com must work for everyone

- **Recorded in 4.3:** sign-in works on every WordPress.com plan, free
  included, through QUILL's own registered app, with no plugins needed and
  nothing for the person to register.
- **What is built:** the PKCE code (`signin.py`), the loopback listener and
  the `wp/v2/sites/<site>` routes.
- **What is missing:** the client id. `WPCOM_CLIENT_ID` in
  `quill/ui/wordpress_connect.py` is empty until Jeff registers the app at
  developer.wordpress.com/apps (redirect `http://127.0.0.1/wordpress-done`).
  Until then, choosing WordPress.com says so plainly.
- **Network egress:** `network_egress_audit` reports nothing unreviewed. The
  WordPress client sends through an injected opener, which the scan cannot
  see. Explicit audit entries for the WordPress routes are still to be added
  by hand.

### 2026-11-04: user guide chapters, changelogs, and worktrees under S:\wt

- **User guides:** a WordPress chapter in both guides. It is Chapter 16 in
  QUILL and Chapter 14 in QUILL Lite. It covers connecting, many sites,
  writing, opening, the three saves, conflicts, Properties, versions, Trash,
  pictures, comments, categories and tags, and keys.
- **Changelogs:** WordPress entries in both (marked in progress).
- **Worktrees:** this work moved to `S:\wt\quill-wordpress`.
- **Checked:** the docs gates ran, and a few trip on the new chapter. They
  are listed under Remaining tasks.
- **Stopped:** work paused at Jeff's request after this entry.

### 2026-11-04 (evening): a test harness, a lost-document fix, and the grouped menu

- **A harness for the commands.** `tests/unit/ui/wordpress/conftest.py` runs
  every shared WordPress command against a fake editor, a fake site that
  records each request, and scripted dialogs that answer Cancel unless told
  otherwise. Until now the commands had no behavioural tests at all; section
  17 asks for one per command.
- **Fixed: a new page lost track of itself on its first send.** Save Draft
  to Site or Publish on a page started in QUILL moved its folder to the
  site's id, out from under the open file, so the next command said "This is
  not a WordPress document". A working copy now keeps its folder for life,
  and `find` looks a sent draft up by its site id. Found by the first
  harness test; `test_wp_local_and_sites.py` now asserts the open file still
  maps to the copy.
- **The menu is grouped** (`quill/core/wordpress/menu.py`). The everyday
  rows stay in File > WordPress; the rest sit in four submenus: Blocks, Media
  and Files, Checking, and Running the Site. Every command the plan names has
  a row and a handler name, so the whole menu exists as one contract.
  - QUILL builds the nesting from the table; QUILL Lite's command table is
    now generated from it (`lite_rows()`), so the two cannot drift.
  - Lite: Alt+F, W now opens WordPress (Print Preview moved to T), and the
    Command Palette row lost its access letter, which Look Up Word also
    claimed. Lite's area filter now prunes nested empty submenus.
  - Every WordPress row in Lite carries a written reason for having no key
    (rule 8) until keys are chosen.
- **The rest of section 19 is being built** by helpers working in parallel,
  one per area: pages, blocks, media, pictures, checking, running the site,
  media for listening and the family apps, and retiring the old Publishing
  feature. Each is logged here as it lands.
- **Checked:** `tests/unit/ui/wordpress` (8 pass), `tests/unit/core/wordpress`
  (508 pass), `tests/unit/apps/test_lite_wordpress.py` and
  `tests/unit/core/lite` pass apart from the handlers still being built and
  the guide naming the new commands.

### 2026-11-04 (night): Blocks, Checking, and the Picture Maker landed

- **Blocks (section 8),** File > WordPress > Blocks. Core in
  `block_spans.py`, `block_edit.py`, `block_catalog.py`, `block_settings.py`
  and `block_preview.py`; the form in `quill/ui/wordpress_block_dialogs.py`.
  - Insert Block with the site's patterns and synced patterns; Next and
    Previous Block and Where Am I; the Blocks window (Go To, Move Up and Down,
    Duplicate, Remove, Change To, Group); Block Settings with the theme
    palette and contrast (9.7); Preview Blocks through `block-renderer`.
  - Every edit copies each byte outside the block it touches, in Markdown and
    HTML documents, as one undo step.
  - Checked: 16 hand-written block fixtures round-trip byte for byte; 259
    tests pass. The official Gutenberg fixture corpus is not vendored.
  - Left out: Gallery in Insert Block, image-to-cover in Change To, static
    plugin blocks, spacing settings, and the user's own global-styles edits.
- **Checking (9.4, 9.5, 9.7, 9.11, 9.12),** File > WordPress > Checking.
  Core in `cdp.py` (Edge or Chrome, hidden, from their standard install
  folders only), `page_audit.py`, `site_fixes.py`, `site_report.py`.
  - Check This Page, Check the Whole Site with Fix in Bulk, Undo Site Fix,
    Site-wide Find and Replace, Write an Accessibility Statement, Palette
    Report, Mark Language and In Short.
  - Properties now shows the reading level ("about 9th grade, 14 words per
    sentence"), worked out on this computer.
  - Checked: 149 tests pass.
  - **Waits on vendoring axe-core** (MPL-2.0) at `quill/data/axe/axe.min.js`
    with its licence. Until then Check This Page says plainly it cannot run,
    and Check the Whole Site checks content only.
- **Pictures (6.9 to 6.11),** File > WordPress > Media and Files.
  - The Picture Maker moved to shared code (`quill/core/ai/picture_maker.py`);
    QUILL Studio now makes pictures through it. WordPress adds Suggest from
    Page Content and Insert into Document, uploading on Insert.
  - Site Logo, Visual Review (desktop and phone, published pages only), and
    Preview and Review. Nothing goes to an AI before a confirmation naming the
    provider and model.
  - Checked: 149 tests pass, and Studio's Picture Maker tests still pass.

### 2026-11-04 (night): the Media Library (6.1 to 6.8, 6.12)

- Core in `media_tools.py` and `media_alt.py`; commands in
  `wordpress_media_library.py`, `wordpress_media_upload.py`,
  `wordpress_image_commands.py` and `wordpress_media_ai.py`.
- Insert from Media Library, Paste Image, Upload Files, Upload from Web
  Address (HTTPS only, 64 MB cap, content type checked, no redirect to plain
  HTTP), Image Size with Back to Earlier Size, Make a Smaller Copy, the Alt
  Text Review, and in the library window Used In, Attach, Set as Featured
  Image, Suggest Alt Text and Describe Image (through Ask About an Image, its
  gates and its agreement).
- Fixed on the way: the library window's `&Files` and `&Find` shared F
  (GATE-14); the list is now `Fi&les`.
- Checked: 151 tests pass.
- Left out: removing many files at once, a Download button, and per-byte
  progress within one file.

### 2026-11-04: a real WordPress site for regression testing

- **The site:** https://lp.csedesigns.com/wordpress/ (WordPress 7.1.4,
  self-hosted, HTTPS). It runs in its own Docker containers on
  lp.csedesigns.com, served by the existing Caddy through a route pinned
  above the letitglow.app redirect. Nothing else on that server changed.
- **Accounts:** one per role (administrator, editor, author, contributor,
  subscriber), each with an application password. The passwords are kept on
  the server only.
- **Seeded content:** every status, a page hierarchy, an Every Block page, a
  post with one problem of each kind for Check Before Publishing, media with
  and without alternative text, the site logo and icon, terms, comments in
  each state, revisions and a synced pattern.
- **Scripts:** `reset.sh` puts the content back to its starting state;
  `verify.sh` checks each role over the REST API, as QUILL does.
- **Test plan:** `docs/qa/wordpress-regression-testing.md`, 30 numbered tests
  run in both editors. The scripts are in `docs/qa/wordpress-test-site/`.
- **A bug the site found:** WordPress lists `/batch/v1` as a route, not a
  namespace, so QUILL's batch check must read `routes`. The WordPress session
  has been told.

### 2026-11-04: two bugs found on the live test site, fixed

- **Batch was reported as missing.** WordPress 7.1 lists `/batch/v1` in the
  REST index's `routes`, never in `namespaces`, so `SiteInfo.supports`
  said a batch-capable site could not batch. It now checks both.
- **The version was missing.** WordPress 7.1's REST index has no
  `generator`, so QUILL could not tell that the site takes the automatic
  password handback, and would always have fallen back to paste.
  `load_site_info` now reads the version from the site's feed
  (`feed_version`), using the same signed opener.
- **Checked:**
  - against the live site: version 7.1.4, loopback handback supported,
    batch supported;
  - a new unit test for routes;
  - all 788 tests in `tests/unit/core/wordpress` pass;
  - ruff and mypy are clean;
  - both changelogs say so.

### 2026-11-04 (night): pages, running the site, and the old Publishing retired

- **Pages (5.8 to 5.10, 9.3, offline).** Core in `schedule.py` and
  `offline.py`; commands in `wordpress_page_commands.py`,
  `wordpress_offline_commands.py` and `wordpress_schedule_dialog.py`.
  - Schedule Publish, Change Schedule and Publish Now; autosaves every two
    minutes on a host timer (`start_repeating`, owned by the window); the
    newer-autosave offer on Open; Restore from Trash in the Open list; the
    once-only "Add it to a menu?" after a new page goes public; Try Again
    that re-reads the site first; and the offline queue.
  - A schedule that cannot reach the site is spoken, not queued, because
    sending it late could land after the chosen time.
- **Running the site (9.8 to 9.10, 9.13).** Core in `comments.py`,
  `navigation.py`, `site_admin.py`, `site_structure.py`, `site_library.py`;
  commands in the `wordpress_admin_*`-family mixins.
  - Comments with every status, threads, Edit and Approve All; the waiting
    count, spoken once per site per session (hooked in `api()`, silent on
    failure, off per site); Menus and Navigation; Widgets; Site Map; Template
    Outline; Site Check; Site Settings with the site icon; Users and
    Application Passwords; Sign Out This Site; Plugins, Themes, Fonts, Synced
    Patterns; Bulk Edit with Undo; Page Order; Convert, Find Unused and
    Default Category.
  - Left out: Undo Merge, custom taxonomies in the terms window, many users'
    roles at once, a synced pattern as a whole document, and plugin search
    (core REST has none, and WordPress.org would be a new outside host).
- **The old Publishing is retired.** The Publish submenu, its eleven
  commands, `main_frame_publishing.py`, `publishing_tools.py`, the flags
  `future.publishing` and `future.publishing_read`, and the experimental
  setting `publishing_experimental_enabled` are gone, with their tests, help
  topics and budget entries. Kept: the wx-free publishing core that File >
  WordPress still uses for saved secrets and the one-time import of old
  connections. Vault's Publish Note now follows the WordPress feature.
- **Egress:** every WordPress call site is reviewed in
  `quill/tools/network_egress_entries_wordpress.py`: the site door
  (`send_to_site`, including Upload from Web Address), WordPress.com tokens,
  and the browser's loopback socket (`cdp.py`). The audit reports nothing
  unreviewed.
- **Checked:** each area's own tests pass (pages, admin 103, retirement's
  touched suites).

### 2026-11-05: the commands moved to Word's menus (section 12)

- **One table names each row's menu** (`quill/core/wordpress/menu.py`,
  `PLACES`). File > WordPress keeps the document and site commands in its
  four groups. Insert has WordPress Block, Picture from the Media Library,
  Picture from This Computer, Link to a Page on This Site and Make a Picture.
  Format > WordPress has Block Settings, Image Size and Mark Language. View
  has WordPress Blocks and Preview Blocks. Edit > WordPress has Next Block,
  Previous Block and Where Am I. Tools > WordPress has the checks, the Media
  Library, Alt Text Review and Visual Review, the site's upkeep, and two
  submenus, More Media and Manage.
  - Format and Edit take a WordPress submenu rather than loose rows: in QUILL
    Lite both menus have no free access letter for "Block Settings" or "Next
    Block", and a keyless Lite row with no letter has no route at all.
  - Tools > WordPress has no access letter in QUILL Lite's Tools (Say Word
    Summary holds the W, and no other letter of the word is free).
- **Dimmed outside a WordPress document,** in both editors: the page
  commands (`DOCUMENT_ONLY`). QUILL refreshes them with its other contextual
  rows; QUILL Lite with its markup rows. Reached from the Command Palette, a
  page command says where it works: "Link to a Page on This Site works in a
  WordPress page or post. Open one with File, WordPress."
- **New: Insert > Link to a Page on This Site** (`wordpress_link_commands.py`),
  the one row section 12 names that did not exist. It lists what the site has
  published, and inserts a Markdown or HTML link named by the selection or
  the page's title.
- **Also on 2026-11-05:** the Category and Tag pickers in New Page or Post and
  Properties are separate check boxes now. The check list box they used reads
  each name without saying whether it is checked (A11Y-SR-1), and the
  pre-commit gate caught it.
- **Committed and pushed:** `c9fe1545c` on `feat/wordpress`, all the code to
  that point. Docs follow in their own commit.
- **Checked:** `tests/unit/ui/wordpress`, `tests/unit/core/wordpress` and
  `tests/unit/apps` (4310 pass; one Cast window test fails only under
  parallel load and passes alone), the QUILL and Lite menu accelerator gates,
  and the Lite command coverage snapshot (355 covered, 0 shape-only).

### 2026-11-05: axe-core vendored, and media for listening (9.6) landed

- **axe-core 4.14.0** (npm, released 2026-10-05, a month old) is in
  `quill/data/axe/`, with Jeff's go-ahead: `axe.min.js` unchanged, its
  MPL-2.0 `LICENSE.txt` and `LICENSE-3RD-PARTY.txt` beside it, and
  `SOURCE.json` recording the tarball address, npm's sha512 integrity and the
  file's SHA-256 (`20c09fe1...e878`). The download's integrity matched npm's
  before anything was copied. It is in the third-party catalogue
  (`components.json`, QUILL and QUILL Lite), the notices are re-rendered, and
  `pyproject.toml` force-includes the folder. Check This Page now runs.
  - Checked: `test_wp_axe_vendored.py` fails on any change to the file, its
    size, its version or a missing licence; Check This Page tests pass (17).
- **Media for listening (9.6),** Tools > WordPress > More Media. Core in
  `listening.py`, `episode.py`, `listen_engines.py`.
  - Captions for Video (WebVTT from QUILL's transcription, reviewed, uploaded
    and attached as a track), Transcript for Audio, Make a Listening Version
    (Read Aloud's export, uploaded, an audio block at the top), Name Embeds
    (oEmbed titles), and Publish a Document as a Page (PDF or Word through
    the import converter).
  - `quill/core/speech/transcribe.py` gained `output_timestamps`, off by
    default, so its other callers are unchanged.
- **Across the family:** QUILL Cast (Episode > Post This Episode to
  WordPress, Ctrl+Alt+P), Audio Studio (WordPress > Post an Episode to
  WordPress, Ctrl+Shift+W) and Quill Converter (File > Upload to WordPress,
  Ctrl+Alt+W). None of them can open an editor window, so each writes an
  ordinary local WordPress draft and starts QUILL with it; when QUILL cannot
  start, it says the draft waits in File > WordPress > Open Local Draft. A
  test asserts the three adapters hold no WordPress code of their own.
  - Checked: 589 tests in the area and the family gates pass, apart from
    snapshot drift that is regenerated with the rest.
  - Left for later: offering Also Publish as a Page straight after a PDF
    upload, warning on Publish that the listening version is out of date,
    and naming an embed the moment it is pasted.

### 2026-11-05: listen and watch (6.1a), and Enter in the list windows

- **Play from the Media Library.** Play (or Enter on a sound or video row)
  opens a small player built on the shared transport panel, `PlayerPanel`,
  so the keys are QUILL's and Quill Media Player's. It streams the file's
  HTTPS address and saves nothing. Video shows its picture where the engine
  can; Captions reads a WebVTT track on request (only from the site's own
  host); Go to Position, Open in Quill Media Player and Open in Browser are
  beside it. Closing stops and releases playback on every route.
  - Code: `quill/core/wordpress/media_play.py`,
    `quill/ui/wordpress_player_commands.py` and its window, a base of
    `WordPressMediaCommands`.
- **View > Play Media Here** plays the audio or video block at the caret,
  nested blocks and Markdown islands included. Dimmed outside a WordPress
  document.
- **Enter now runs a list window's main action.** The Open list always said
  "Enter opens the selected one" and Enter did nothing; it opens now, and a
  double-click does the same. In the Media Library, Enter plays a sound or
  video file and inserts anything else. (`ListWindow(on_enter=...)`.)
- **The test site** (`docs/qa/wordpress-test-site/setup.sh`) seeds a
  three-second tone, a five-second silent video with English captions, and a
  "Listen and Watch" page; the regression plan has tests 31 to 37 for them.
  The script is syntax-checked, not run.
- **Checked:** 126 player and Media Library tests, the Lite parity tests and
  key gates pass.
- **Not yet:** the video picture is untried live; with the modern Windows
  Media engine there is no picture, and the window says so once and points
  to Open in Browser. Quill Media Player does not yet open a web address it
  is given (it reads its arguments as file paths and drops them on a second
  launch); its fix waits because `quill/apps/player.py` is at its size
  budget. The shared panel's audiobook words ("0 chapters", "End of book")
  read oddly for one file.

### 2026-11-05: the docs, the snapshots, and the second commit

- **Docs, in a human voice:** QUILL Chapter 16 and QUILL Lite Chapter 14
  rewritten to the new menus and everything built; both PRDs gained a
  WordPress section (one shared layer, one adapter each, one menu table);
  WordPress entries in QUILL's 1.0.0 release notes, QUILL Lite's 2.0 release
  notes and What's New; short sections in the QUILL Cast, Audio Studio and
  Quill Converter guides; the regression plan follows the new paths. Keys:
  the chapters say there are none yet, Alt+F, W opens File > WordPress, and
  the Command Palette finds every row.
- **Fixed on the way:** QUILL's main window could not build its WordPress
  rows. The menu ids were made with `wx.NewIdRef()` and only the numbers
  kept, so wx released them and refused them ("id should first be
  reserved"). The refs are kept now; the documented-menus gate found it.
  Both changelogs also still named the old submenus, and are corrected.
- **Regenerated:** the dialog inventory, surface reachability, QUILL Lite
  command coverage (356 covered, 0 shape-only), the F1 help inventories for
  QUILL Lite, Audio Studio, QUILL Cast, Converter and Player (no control
  without help), accessible names, the F1 help reference, the control
  reference, the third-party notices, and every changed doc's HTML and EPUB.
- **Committed and pushed:** `7ec8a049b`.
- **Checked:** ruff clean; `mypy quill\core quill\io` reports nothing in
  those packages (its 791 errors are all in followed imports under
  `quill/ui` and `quill/apps`, as on main); the egress audit has nothing
  unreviewed; the docs artifact check passes. The full suite is running.

### 2026-11-05: the full suite and platform_report

- **Full suite** (`pytest -q -n 4`): 9614 passed, 41 failed. Run again on
  their own, the rich-format, build-script and Cast window failures all
  pass; they failed only in the parallel run, which the machine ran with
  about 170 MB of memory free. One was real and is fixed:
  - the WordPress.com token request opened its URL without QUILL's TLS check
    (`test_tls_one_check.py`); it passes `verified_ssl_context()` now.
- **platform_report:** 51 of 53 gates passed. Both failures were real:
  - **GATE-CTLLABEL, a screen-reader bug.** The shared row helper built each
    field before its label, so Windows could read a label as the *next*
    field's name. It is `labelled_row` now: it moves the label in front of
    the field in z-order and names the field with `set_spoken_name`. A real
    dialog shows the label first; the scan (`control_label_scan.py`) knows
    the helper, and the gate reports no unnamed control.
  - **GATE-CAPS.** The Picture Maker's Suggest from Page Content asked the AI
    without saying it needs text; it passes `requires=("text",)` now.
- **Checked:** the control-label and Picture Maker tests (41) and the
  WordPress UI tests pass.

### 2026-11-05: the site's own kinds in Open, and the live site

- **Open lists the site's own kinds** beside Posts and Pages: events,
  recipes, anything a plugin or theme registers with a REST base
  (`site.list_content_types`, from `wp/v2/types`). Patterns, templates,
  navigation, fonts and media are left out, because they are not pages a
  person writes. A site or role that will not list its types still gets
  Posts and Pages, silently.
  - Checked: `test_wp_link_and_placement.py` (Events offered and listed;
    the fallback when the types are refused).
- **The test site gets an Events type** (`setup.sh`: a must-use plugin with
  `show_in_rest`, and one published event, Open Day). Regression tests 38
  and 39 cover it.
- **Live site, run from this computer without a password:** QUILL's core
  read the REST index of https://lp.csedesigns.com/wordpress/ as "QUILL
  WordPress Test Site", WordPress 7.1.4, with the batch route and the
  Authorize Application address present.
- **Not run yet: the signed-in live tests.** Copying QUILL's core to the test
  host to run them there, with the test accounts that live on it, was refused
  by this session's permission guard (a write on a remote machine), and the
  application passwords are not to leave that host. Jeff can run them with
  the regression plan, or allow the remote copy, or run `setup.sh` there
  himself to seed the tone, the clip and Events first.

### 2026-11-05: guided WordPress tutorials, and the Player plays web addresses

- **Seven guided WordPress lessons** in Help > Tutorials, in both editors,
  from one shared module (`quill/core/tutorials/wordpress_lessons.py` and
  `wordpress_lessons_more.py`): connect your site; write a post and publish
  it; open by web address and fix a sentence; pictures with alternative
  text; Check Before Publishing; previous versions; comments. They use the
  test site's real content and teach the key layer from `LAYER_KEYS`, so
  the table cannot drift. No password appears in any lesson, and a test
  checks for anything shaped like one. QUILL has 37 lessons now, QUILL Lite
  23. Both tutorial books are regenerated and rendered.
  - Checked: the tutorial catalogue and QUILL Lite tutorial tests (52 pass,
    drift included), GATE-11 and ruff.
- **Quill Media Player plays an https address** given on the command line or
  handed over from a second launch (which before did nothing at all), so the
  WordPress player's Open in Quill Media Player works. Plain http is
  refused with the reason. To fit GATE-11, the bookmark handlers moved to
  `player_bookmarks.py` (player.py 926 to 843 lines, its budget lowered to
  match). The shared panel says "End of file" for a file with no chapters,
  and Go to Position works on a stream.
  - Checked: 93 Player and WordPress player tests, 70 Audio Studio and gate
    tests (one timer-ownership read error from another helper's edit passed
    on its own), the Player help audit.
- **Docs:** both guides now teach View > Play Media Here, which QUILL Lite's
  guide gate found missing.

### 2026-11-05: more from the API, writing and pictures (9.15, first half)

- **Block Notes** (View > Block Notes, Insert > Note on This Block): the
  block editor's notes (comments of type `note`, WordPress 6.9+), each read
  as "Sam on the second paragraph: tighten this", with Go to It, Reply and
  Resolve. Offered only where the site lists the route. **Built on the
  documented shape, not yet tried on the live site**; if resolving works
  differently there, only `block_notes.set_resolved` changes. In a Markdown
  document a noted block becomes a protected line, and Add Note asks first.
- **Custom fields:** registered post meta in Properties, generated from its
  schema, and File > WordPress > Custom Fields; the next send carries them.
- **Which password:** Sites names the application password QUILL is using
  (`users/me/application-passwords/introspect`), and Sign Out This Site
  revokes exactly that one, by name.
- **Picture sizes and editing:** the image dialog offers the library's own
  sizes ("Medium, 300 wide"); Tools > WordPress > More Media > Edit a Picture
  on the Site rotates, crops (square, 4:3, 16:9) and flips where the site
  offers it, into a new library item, described when AI is on.
- **Bulk moderation** (Comments: Mark, Mark Everything, Do with Marked) and
  **Alt Text for the Whole Library** (Tools > WordPress), saving in batches.
- Code: `wordpress_api_writing_commands.py` with its Notes and picture-edit
  mixins, four core modules; menu rows added to the shared table and QUILL
  Lite's handlers generated from it.
- **Checked:** 65 new tests and 203 for the areas touched; the Lite parity,
  key and QUILL menu-accelerator gates (113).

### 2026-11-05: every route, and more value (9.16)

- One feature table (`quill/core/wordpress/routes.py`): each command reads the
  site's routes and the account first, once a session per site, and says why
  in one sentence when the site or role cannot.
- Edit > WordPress: Hear Where a Link Goes (`url-details`) and Fix Link Text
  ("click here" gets the target page's title); Check This Page now finds dead
  links. Insert > WordPress Icon, always labelled or marked decorative.
  Tools > WordPress > More Media: Upload a Large File (in pieces, with spoken
  progress) and Regenerate Sizes. Tools > WordPress: Menu History; Manage:
  Previous Looks, Space Used, Download a Copy of the Site's Design; Your
  Sites: Coming Up and What Changed on My Sites, across every site.
- File > WordPress > Send and Copy: Send This Document to WordPress
  (any open document becomes a draft), Publish to Another Site, Duplicate,
  Download My Writing (Markdown, incremental), Send a Folder as Drafts.
- Regression tests 40 to 55 added.
- **Built from the route names, not yet answered by the live site:** the
  icons list, upload in pieces and Regenerate Sizes (tests 43 to 45; they
  need the signed-in run).
- Left out: plugin updates in What Changed (REST does not report them), Word
  files in the archive tools (Markdown only), and a "nearly full" warning
  (the site reports sizes but no limit).
- **Checked:** 184 tests; the Lite parity and menu-accelerator gates.

### 2026-11-05: the WordPress keys, the rest of 9.15, and the Forms core

- **The WordPress key layer** (option 1, as Jeff approved), in both editors:
  Ctrl+Alt+Shift+Grave, then one letter from `LAYER_KEYS`. O Open, P Publish
  or Update, M Media Library, S Switch Site, W Open by Web Address, D Save
  Draft to Site; G New Page, N New Post, L Open Local Draft, E Schedule, I
  Open on Site, Y Copy Address, R Properties, V Previous Versions, C Compare,
  T Move to Trash, Shift+S Sites, A Connect a Site; B Blocks, K Check Before
  Publishing, U Upload Files, X Alt Text Review. Starting it says "WordPress
  keys"; Escape says "Left WordPress keys"; an unknown letter says "No
  WordPress command on X." and types nothing; it times out after 4 seconds.
  - The chord was checked free in both editors and outside every family
    hotkey first, and a test pins that. The shared layer is
    `quill/core/wordpress/keys.py` (no wx); both editors read the letters
    from their live keymap, so a key moved in the Keyboard Manager moves
    its letter. Menus show the key in brackets, e.g. "(Ctrl+Alt+Shift+Grave,
    O)". Key Describer titles, the keyboard reference and QUILL Lite's key
    table are regenerated; the docs teach it; the parity table proves the
    letters match.
  - Checked: 63 key-layer tests, 466 Lite, parity and docs-gate tests.
- **9.15, second half** (Tools > WordPress > Design, Plugin Extras, Manage;
  File > WordPress > Plugin Fields): Style Variations with their Palette
  Reports and Put Back the Previous Look; Site Styles (palette and font
  sizes only, contrast spoken before saving); the Pattern Directory from
  Insert Block; pattern categories in Synced Patterns; The Events Calendar
  (Events Coming Up, New Event, start, end and venue in Properties);
  WooCommerce (price and stock; Shop Orders read-only, copying asks first);
  Yoast and Rank Math SEO fields with lengths; AI Abilities, off until turned
  on per site, and Ask the Site, which runs one only after a yes each time;
  and Site Check running every Site Health test the site lists.
  - Abilities are reached through Ask the Site rather than the editor's own
    Ask, which would mean changing the shared AI conversation code.
  - None of these plugins or abilities are on the test site, so they are
    built from the documented routes; regression tests to follow.
  - Checked: 231 tests.
- **9.16 wired:** its 16 rows are in the shared table, including File >
  WordPress > Send and Copy (renamed from "Send, Copy and Download", whose
  comma the documented-menus gate read as a path break). Check This Page
  keeps working when a site has no link-details route; dead links are an
  extra, never a gate.
- **The Forms core** (`quill/core/forms/`, 24 modules), built in 17a.15's
  order: the JSON form model with versions and migrations; its JSON Schema
  (`quill/core/forms/schema/form.schema.json`, `urn:baf:form-model:1`); one
  expression language (and, or, not, is one of, dates, field references,
  arithmetic) with an evaluator and a sentence for every rule; BFL in and out
  with islands for anything unknown; translations; imports and exports for
  SurveyJS, XLSForm and HTML; BAF's 124 choice libraries offline; spoken
  field summaries. Nothing is on the menus yet.
  - Conformance: byte for byte against BAF's PHP parser and formatter on 20
    vendored fixtures, all 111 guide and test examples, and 300 random
    variations; every model fits the schema.
  - **Found:** BAF's parser does not do what its own guide teaches in 29 of
    111 examples, and its formatter changes the meaning of 58 (indented
    choices and `if` blocks, `if` with extra words becoming unconditional,
    values compared where the guide uses labels). QUILL reads the documented
    language, and `baf_compare.divergences()` explains in a sentence where
    the site would differ, for Check This Form.
  - **For Jeff:** the choice libraries and fixtures come from BAF
    (GPL-2.0-or-later) into MIT-licensed QUILL; and the new BFL spellings
    (`@when`, `@calculate`, `@score`, `@choice_score`, `@translate`,
    `outcome`, `// bfl-version 1`) need BAF-side agreement.
  - Checked: 249 tests; ruff and scoped mypy clean.

### 2026-11-05: BAF gets the JSON form model (in S:\code\baf)

- **Branch `feat/json-form-model`** in `S:\code\baf`, cut from main
  461375e, six local commits; **not pushed** (this session's permission
  guard refused publishing a new branch) and no PR. Jeff can push it with
  `git -C S:\code\baf push -u origin feat/json-form-model`.
- Built: the documented model (`docs/form-model.md`, with the migration
  note) and its schema (`schema/form.schema.json`) for all 64 field types,
  rules, scoring, outcomes, translations, settings and notifications; one
  expression language (`docs/expression-language.md`) with a PHP evaluator
  and sentence renderer; BFL as a notation of the model, round-tripping
  exactly, first line `bfl 1`, the old parser untouched; storage of the
  model beside the builder's fields, so the builder keeps working and keeps
  what it cannot show; the shared conformance suite
  (`tests/conformance/manifest.json`); and imports from Gravity Forms,
  WPForms, Contact Form 7, Ninja Forms and Google Forms, each with a report.
- Checked: 51 new tests pass under a stand-in runner (PHP 8.1 is here,
  PHPUnit is not, and nothing was installed); BAF's whole suite gives the
  same 111 old failures on main and on the branch, so nothing regressed.
- **Left on the BAF side:** a JavaScript copy of the evaluator so published
  forms honour or-conditions, dates, page conditions, outcomes and
  translations; builder screens for rules, outcomes, translations and
  choice libraries; Structure mode and the REST API moving to the new
  reader; an imports screen and exports to the five builders.
- **Next on the QUILL side:** QUILL's reader agrees with BAF's suite, which
  differs in places from what QUILL's helper chose alone (BAF's first line is
  `bfl 1`, QUILL wrote `// bfl-version 1`; the two schemas must become one).

### 2026-11-05: one form definition for QUILL and BAF

- QUILL's Forms core now follows BAF's `feat/json-form-model` everywhere the
  two differed. The schema is BAF's, byte for byte, and a live test fails if
  they ever drift. The model is BAF's JSON, held as plain data rather than a
  typed copy, which would be a second definition. The expression language
  and BFL (first line `bfl 1`) are ports of BAF's. QUILL's own spellings are
  dropped in favour of BAF's.
- Kept, QUILL only: a document that is not edited writes back byte for byte
  (line endings, byte order mark and comments included), an edit rewrites
  only what it touched, and lines BAF skips stay in the document as islands
  (stored under `extensions.quill.islands`, which BAF passes back unchanged).
- Conformance: every suite in BAF's manifest that QUILL runs passes, read
  live from the branch; a vendored subset runs in CI.
- **Disagreements left open**, where QUILL follows BAF's code over BAF's
  docs: priced choices are written long-hand, not as `+ Small:10`; a library
  keyword after a select's label (`select "Country" countries`, as the guide
  teaches) is skipped by BAF's new reader; and some edges (an empty list for
  an object, rounding of very long numbers, lone surrogates, integers past
  2^63). These go to the BAF side.
- Checked: 175 core tests; with the Forms commands' tests, 246.

### 2026-11-05: the Forms commands, in both editors (17a.4 to 17a.6, 17a.10)

- One placement table, `quill/core/forms/menu.py`, the same shape as
  WordPress's: File > New Form; Insert > Form Field; View > Form Outline;
  Format > Form Rules; Tools > Forms with Check This Form, Fill It In
  Yourself, Form Properties and Responses (Responses says it waits on the
  BAF connection, being built now). Dimmed outside a form document, and
  each says why from the Command Palette. A form document is `.bfl`, set
  once as `FORM_EXTENSION` until Jeff answers 17a.13.
- Shared code in `quill/ui/forms_*`; QUILL's `main_frame_forms.py` and
  Lite's `lite_window_forms.py` hand off only, and a test asserts it. QUILL
  feature `core.forms` (off only in Essential); a QUILL Lite area Forms (on
  in Recommended and Everything, off in WordPad and Notepad; 23 areas).
- New Form with templates; Insert Field from every field type the core
  knows (Section and Page break first in its list); the outline (go to,
  move, rename); Rules as sentences, added and edited in the expression
  language; Form Properties; Check This Form with Go to It and where the
  site's older reader would differ; Fill It In Yourself, following the
  rules, in each of the form's languages.
- **Keys:** none of the eight rows has one, each with a written reason; no
  sensible chord is free in both editors and outside the family hotkeys. A
  letter on the WordPress layer (Ctrl+Alt+Shift+Grave, F) is free, but would
  widen that layer beyond WordPress; left for Jeff.
- QUILL Lite gave up two access letters (Close Window (MDI) and Switch
  Document Mode lost their M, keeping Ctrl+F4 and Alt+Shift+F) so New Form
  and Form Rules have one.
- Chapter 17: Forms in QUILL's guide, Chapter 15 in QUILL Lite's.
- Found: inserting a question first on a page was dropped by the core's
  byte-exact writer; the UI checks every write and falls back to a whole
  rewrite, and the core fix is under way.
- **Checked:** 92 new tests; 827 with the gates; dialog and docs gates (62).
- Committed: `5774c1207`.

### 2026-11-05: Forms core fixes, and the UI on the core's helpers

- A question inserted first on a page (or first in a section, or in an empty
  form) was dropped by the byte-exact writer; it is written now, and the
  writer reads its own result back and writes the whole form tidily
  (`last_write = "canonical"`) if a splice would ever lose an edit.
- Fill It In Yourself showed no choices for questions drawing on a choice
  library (a broad `except` hid the error); fixed in the core, and the UI
  now asks `libraries.choices_for(item, model)`, which also finds a
  library the form defines.
- The outline and translations come from the core
  (`summary.outline_rows`, `translate.localize`), so both editors and Check
  This Form read a question the same way; the UI's own copies are removed.
- Checked: 270 core and UI tests, then 92 UI tests after the switch.

### 2026-11-05: Forms on the site, on paper and with AI (17a.7 to 17a.9)

- Tools > Forms, in both editors: Publish Form (live or draft, confirmed by
  site, warning if the site's copy changed since you last published, the
  site's previous copy kept, ten per form), Insert Form Into Page (BAF's
  block, or a shortcode in a Markdown page), Test on Site, and Responses
  (list, one at a time, by date and by place, Find, CSV, Open as Table and
  Word exports saved only where you choose, Mark and Delete after a count).
  Only on sites whose index lists `baf/v1`, and off in Safe Mode. The count
  of new responses is said once per site per session (BAF has no unread
  flag, so "new" means since you last opened Responses in QUILL).
- Exports, all local and working in Safe Mode: Save As Web Page, Word
  Document, Large Print (18 point and up) and Braille-Ready Text (40 cells,
  UEB contracted through QUILL's own braille translator with the braille
  pack).
- AI, through the same Choose Your AI path WordPress uses: Draft a Form,
  Plain Language, Suggest Autofill Hints, and Summarise Responses (which
  asks every time, with the count). Each says what it sends first; each is
  a proposal applied on a yes, as one undo step.
- **Fixed in BAF** (`feat/json-form-model`, local commit `045c682`): BAF's
  REST create and update stored the model but not the fields its renderer
  reads, so a form published from QUILL showed no fields. They now call
  `set_model()` when a model is sent, keeping the site's other settings.
- **Persistence:** every WordPress and Forms store is classified
  (`quill/tools/persistence_entries_wordpress.py`); the site list is
  `needs-versioning`, the rest content, cache or markers.
- **Checked:** 74 new tests; 847 WordPress and Forms tests; the menu, docs
  and coverage gates.

### 2026-11-05: Forms tutorials, and rules that match however you type

- **Seven guided Forms lessons** in both editors, a Forms track after
  WordPress, from shared modules (`quill/core/tutorials/forms_lessons.py`
  and `forms_lessons_more.py`): start from a template, add questions, add a
  rule and hear it as a sentence, Check This Form, Fill It In Yourself, large
  print and braille-ready copies, and publishing to a site with BITS
  Accessible Forms and reading its responses. Every quoted sentence was
  checked against the real commands. QUILL has 44 lessons, QUILL Lite 30.
- **Fixed, found while writing lesson 3:** Add Rule compared the answer as
  typed, but a choice is stored as its value ("phone"), so typing "Phone"
  made a rule that never matched, silently. The answer is now matched to
  the question's choices by value or label in any capitals
  (`forms_outline_commands.choice_value`).
- Regression tests 56 to 68 (Forms); 63 to 68 need BAF on the test site.
- A garbled-text gate hit in `quill/core/forms/expr.py` (a literal
  replacement character) is written as `chr(0xFFFD)` now.
- **Checked:** 93 tutorial tests, 17 Lite docs tests, the docs gates, and 74
  Forms UI tests after the fix.

### 2026-11-05: main merged in, and BAF's next steps

- **origin/main merged** (agentic coding, #1760) as `2e6c69949`. QUILL Lite
  now has 24 areas: main's Coding plus WordPress and Forms (Recommended 19,
  Everything 23, Developer 20, WordPad 6, Notepad 3), recounted in the
  profiles, guide, PRD and tests. The old Publishing flags stay retired in
  every profile, Developer included. Four access letters the merge made
  collide were moved: Print Preview has none now, Edit > WordPress has none,
  Pre&view Blocks, Pict&ure from the Media Library.
- **BAF, seven more local commits on `feat/json-form-model`** (not pushed):
  a JavaScript copy of the expression evaluator, exactly matching PHP (476
  conformance checks pass in Node), and published forms now run their model
  (conditions, all eight rule actions, calculations, defaults, page skips,
  with the live region saying when questions appear or go); Structure mode
  and the REST API on the new reader and writer (`bfl/parse` now returns
  `{valid, model, config, errors, warnings}`, plus `bfl/validate` and
  `bfl/format`); the open disagreements settled (`+ Small:10`, and the
  library keyword after a label); exports to Gravity Forms, WPForms,
  Contact Form 7, Ninja Forms and Google Forms; and an accessible Import and
  Export screen. 74 model tests, 147 unit tests pass (the same 111 older
  failures as before). Not yet tried in WordPress or a browser.
- **Left on the BAF side:** builder screens for rules, outcomes,
  translations and choice libraries (planned in `docs/builder-model-screens.md`),
  and a check of the live wiring and new screens with NVDA and JAWS.
- **Next on the QUILL side:** the new conformance cases (exponent-free
  numbers, the short priced spelling, the library keyword, 144 expression
  edge cases).

### 2026-11-05: QUILL's Forms core passes BAF's newest suite

- Every suite QUILL runs from BAF's manifest (`feat/json-form-model`,
  44f04f1) passes, read live: numbers in canonical text are plain digits,
  never an exponent; PHP's own float text is kept where BAF still uses it;
  rounding copies PHP's `round()` exactly (fuzzed against BAF's PHP, 3,000
  cases each); answers held as objects are handled as BAF handles them;
  expression errors give their offset in UTF-8 bytes; the writer uses the
  short priced spelling (`+ Small:10`), and the reader accepts the library
  keyword after a label. The vendored subset is refreshed.
- `baf_site.form_from_payload` reads the `model` BAF now returns beside
  `config`.
- Fixed: Fill It In Yourself's language chooser was laid out through the
  shared row helper by attribute, which the label gate cannot see; it calls
  `labelled_row` directly now (platform_report: control-labels clean).
- **Checked:** 280 Forms core and UI tests; platform_report 52 of 53 before
  this fix, the 53rd (control labels) clean after it.

### 2026-11-05: BAF's builder screens for the model

- Five more local commits on BAF's `feat/json-form-model` (not pushed):
  Rules, Quiz outcomes, Translations and Choice libraries screens, editing
  the stored model through BAF's AJAX actions. Each save reads the stored
  model again and puts back only its own part. Every control is labelled,
  fieldsets and headings on every screen, tables with captions and row
  headers, row buttons named for their row, a status region per screen,
  modal dialogs that trap Tab and return focus, errors joined to fields
  with a summary that takes focus, each rule read as its sentence, nothing
  that needs drag and drop.
- Fixed on the way: the builder's mode tabs had no script at all (the
  enqueued `baf-admin.js` did not exist); they now work with the arrow keys,
  Home and End, as one tab stop.
- Checked: 85 model tests (74 before), 20 editor tests and 476 conformance
  checks in Node, every flow driven in a browser against a faked server.
- Not built: the per-question Scoring section in the Visual mode's field
  panel (the plan's step 4), which is drawn on the server per field type.
- Not yet: a run in WordPress, and a check with NVDA and JAWS.

### 2026-11-05: BAF's per-question Scoring section

- Local commit `f3639d8` on BAF's `feat/json-form-model`: each card for a
  question that can be scored has its own Scoring button (named for its
  question) opening a section drawn on the server from the saved model:
  points, the correct answer or answers in a fieldset, partial credit,
  accepted text answers, each choice's points in a table with row headers,
  feedback and the explanation. Focus moves to its heading and back; errors
  are joined to fields; a status region says what was saved. Saving puts
  back only that question's scoring.
- **Found:** the Visual mode's existing Edit panel has never worked (the
  script and the server disagree on what is sent, `baf_save_field_settings`
  has no handler, and the card buttons' classes match no click handler).
  Scoring does not depend on it.
- Checked: 88 model tests, 25 editor tests in Node, 476 conformance
  checks, and a browser run against a faked server. Not yet in WordPress.

### 2026-11-05: BAF's Visual mode works

- Local commit `34f110a` on BAF's `feat/json-form-model`: no card action in
  BAF's Visual mode had ever worked (the script looked for elements that do
  not exist, its buttons matched no handler, and add, duplicate, delete,
  reorder and save had no server handlers). Each now changes the saved
  model through the normal validated save (`BAF_Builder_Field_Ops`, five
  AJAX handlers), touching only its own question or the order; a refused
  change says why and leaves the page matching the model.
- The Edit panel is drawn on the server (Label, Help, Placeholder,
  Required), labelled, with an error summary, a status region and focus
  managed; a question added from the palette gets its card, and its Scoring
  button, at once. Delete asks in the shared alertdialog; reduced motion
  skips the move animation; every message is translatable.
- Checked: 100 model tests, 27 editor tests in Node, 476 conformance
  checks, every card action in a browser against the real PHP classes.

### 2026-11-05: forms on a site use BAF (17a.16)

- Jeff's decision recorded in 17a.16 is reflected in both guides: forms are
  published only to BITS Accessible Forms; without it, Save As Web Page
  gives a standalone accessible page; forms from other plugins come in by
  import only. QUILL's code already publishes only to `baf/v1`, and none of
  its text implied another plugin could host a form.

### 2026-11-05: BAF is MIT, and so are the parts of it in QUILL

- Jeff relicensed BITS Accessible Forms to MIT (BAF branch
  `chore/mit-license`, a8e58b4, which Jeff pushes). The BAF-derived files
  in QUILL now say so: the choice libraries' source note
  (`quill/core/forms/libraries/baf_libraries.json`) and the fixtures'
  `SOURCE.txt`. The schema carried no licence text. The GPL caveat is gone
  from section 19.
- To do once Jeff has pushed `chore/mit-license`: merge it into
  `feat/json-form-model`, so both BAF branches agree.

### 2026-11-05: the plugin's Visual mode, finished, and the rename begun

- Local commit `47c98a7` on BAF's `feat/json-form-model`: a new form is
  created on its first add (no save and reload); Add Field is a modal "Add
  a question" dialog with a filtered list of types and F only inside the
  canvas (never a page-wide single key, WCAG 2.1.4); Convert Type lists
  what would change, then changes the model, and says how many conditions
  read the question; Save Draft and Publish save the model; nested
  questions in sections and columns have cards; drag and drop goes through
  the same order check. 108 model tests, 28 editor tests, a browser run.
- Left for the plugin's own next pass: the Preview button has no script;
  the Accessibility Coach and the old `baf_save_form` are unreviewed;
  sections and columns have no canvas actions; a repeater's own questions
  have no cards; Convert does not rewrite the conditions it counts.
- **The rename to QUILL Accessible Forms (17a.17)** is under way: QUILL's
  side on #1762 (`.qaf` files, `qaf/v1` first, the installer association,
  user-facing text), the plugin's on a new local branch `chore/rename-qaf`
  from `chore/mit-license` 1196703 with the model work merged in.

### 2026-11-05: the plugin is QUILL Accessible Forms (17a.17)

- New local branch `chore/rename-qaf` in the plugin repository (worktree
  `S:\wt\baf-qaf`), cut from `chore/mit-license` 1196703 with the model
  work and the activation fix merged in; not pushed. The header names QUILL
  Accessible Forms by Jeff Bishop, MIT, "Copyright (c) 2024-2026 Jeff
  Bishop"; the main file is `quill-accessible-forms.php`; every `BAF_`,
  `baf_` and `baf-` name is QAF; the REST namespace is `qaf/v1`, with
  `baf/v1` answering GET only, for one release; saved forms are `.qaf`, and
  `.bfl` still opens; on-screen text says "the QAF form language".
- Old data is migrated once, on activation: tables renamed, options copied
  (the old ones kept for a release), meta and capabilities moved; the old
  shortcodes keep working. Written up in the README.
- Left as they are: the `bfl 1` version line and internal names
  (`qaf/v1/bfl/...` routes, `bfl` keys); URLs whose new address is unknown
  (`bitsolutions.org`, the schema's `$id`).
- Checked: 118 model tests (10 new, for the migration and the alias); 191
  unit tests and the same 111 older failures; 476 conformance checks in
  Node. Not tried in a real WordPress.
- QUILL's side of the rename follows in a pull request after #1762.

### 2026-11-07: payments, both sides (contract version 1)

- **The plugin.** New local branch `feat/qaf-payments` in the plugin
  repository (worktree `S:\wt\baf-payments`), cut from `chore/rename-qaf`
  beb3e2c; not pushed. `includes/payments/` implements every clause of
  `forms-payments-plugin-contract.md`: the readiness route (verified, not
  merely typed, keys and webhooks, per mode), validation in
  `QAF_Form::set_model` and again at checkout, server-side amounts in
  integer minor units (fixed, donation with bounds, number fields, totals
  from products, linked quantities, coupons, shipping, tax and
  calculations), Stripe Payment Intents and PayPal Orders v2 with
  idempotency keys, verified webhooks recorded once and applied through a
  transition table with compare-and-set writes, `qaf_payment_paid` once per
  entry, the entries' `payment` object, and QAF Forms > Payments in
  wp-admin (write-only secrets, test and live mode, Check Connection, Create
  Webhook, a report with totals). Its admin guide is
  `docs/payments-admin-guide.md` there.
- **The desktop.** The rest of the payment plan that fits the boundary in
  `forms-payments-design.md`: Test on Site says the test card or sandbox
  account; Insert Payment Field lists the form's amount fields; the plugin's
  precision and statement-descriptor rules are checked before publishing;
  Responses say payments in words; redaction covers `rk_live_`,
  `rk_test_`, `whsec_` and PayPal tokens.
- **Docs.** "Taking payments with your forms", Chapter 18 of QUILL's guide
  and Chapter 16 of QUILL Lite's; the Forms chapters point to it.
- Checked: the plugin's 103 payment tests, run under a stand-in for PHPUnit
  because this machine has PHP 8.1 and no PHPUnit or Composer; the plugin's
  476 Node conformance checks. Not tried in a real WordPress, nor against
  Stripe's or PayPal's sandboxes.

### 2026-11-08: QAF main carries everything; the folder is S:\code\qaf

- The plugin's `main` was fast-forwarded to `feat/qaf-payments` (cbc7fef), at
  Jeff's word. Every other branch (`chore/mit-license`, `chore/rename-qaf`,
  `feat/json-form-model`) was already contained in it, so nothing was lost or
  merged by hand. All 215 PHP files pass `php -l`; PHPUnit was not run (no
  vendor folder on this machine).
- The worktree `S:\wt\baf-payments` was removed and the repository folder
  renamed from `S:\code\baf` to `S:\code\qaf`. The plugin's name is QUILL
  Accessible Forms (QAF).
- Published at Jeff's word: https://github.com/Community-Access/quill-accessible-forms
  (public, `main` pushed). History was scanned first: every key-shaped string
  is a test placeholder. `main` is protected: a pull request with one approval,
  resolved conversations, no force pushes, no deletion; admins can still merge.
  The feature branches stay local, since `main` contains them.

### 2026-11-09: what the site says about itself, lists and groups, and the one query

The groundwork from the WordPress Workbench PRD that does not wait for the
shared Workbench engine (WP-R-030 to WP-R-034). Not yet tried against the
live site.

- **Taxonomies and statuses come from the site (WP-R-031).**
  `quill/core/wordpress/site_taxonomies.py` reads `wp/v2/taxonomies` and
  `wp/v2/statuses` with `context=edit` (and the public answer for an account
  that may not ask for it), and keeps each connection's answer for ten
  minutes. `taxonomy_route()` now uses a taxonomy's own `rest_base` and
  `rest_namespace` instead of guessing `wp/v2/{slug}`; categories and tags
  never cost a request of their own, and a site that will not say keeps the
  old guess. A hierarchical custom term keeps its parent on update, and Merge
  moves posts by the taxonomy's field (`genres`, not `genre`).
- **Writing types, by status (WP-R-032, core).** `site_types.py` returns each
  type with its names, namespace and taxonomies, and can list one type's
  items in one status (the plugins' statuses included), count each status
  from `X-WP-Total`, offer the core six statuses then the site's own, and make
  a new item of any type with its terms. A type outside `wp/v2` has its whole
  route as its kind. The browsing and New commands are left for the
  Workbench, where the PRD puts them (a node per type, File > New per type);
  Open is unchanged.
- **Lists and groups in Custom Fields (WP-R-033).** Registered meta of type
  `array` (with `items`) and `object` (with `properties`) is now edited, not
  counted: `custom_field_shapes.py` says each one in a sentence, types what
  was typed into the schema's types, and keeps every key a group came with.
  In both editors, Custom Fields (and Properties after it) opens **Lists and
  Groups** after the plain fields; a group is one form, and a list opens with
  Add, Edit, Remove, Move Up, Move Down and Keep Changes. Changes are kept
  with the working copy and sent with the next Save Draft to Site or Publish.
  Only a list with no `items` schema, or a list of lists, is still left
  alone. Meta on terms, users and comments is read and written by the same
  functions (`object_route`, `meta_schema_for`, `site_values_for`,
  `send_meta`); no window offers it yet.
- **One query builder (WP-R-030 groundwork).** `query.py` is the attribute
  table the Filter Builder will read, every `wp/v2` collection argument with
  a label, a kind and its operators, plus taxonomies by rule and each route's
  own enums. `build()` sends what QUILL never did: `tax_relation`, every
  `_exclude`, `modified_after` and `modified_before`, `search_columns`,
  `search_semantics`, `ignore_sticky`, and terms "all of".
- **The combination test (WP-R-030).** `quill/tools/wordpress_combination_audit.py`
  (rostered in `platform_report` as `wordpress-combinations`) checks the 150
  `wp/v2` routes of the recorded index
  (`tests/unit/core/wordpress/fixtures/rest_index_test_site.json`): every
  collection argument known, every enum value offered and said in words,
  every writable property a field kind, every method an action. Seven plugin
  orderings without a spoken label are its planned gaps; the list may only
  shrink.
- **Advanced Custom Fields, read (WP-R-034).** `field_plugins.read_acf()`
  reads ACF's `acf` field where the schema shows it, into the same form.
- Tests: `test_wp_discovery.py`, `test_wp_custom_field_shapes.py`,
  `test_wp_query.py`, `test_wp_field_plugins.py`,
  `test_wordpress_combination_audit.py`, and five more in
  `test_wp_api_writing_fields.py`. The live regression
  (`docs/qa/wordpress-live-run.py`) has not been run on this branch.

### 2026-11-09: the WordPress Workbench, W1 to W4, behind a developer flag

The WordPress provider for the shared Workbench window (Workbench PRD Part
G: W1, W2, W3, W3a on the Workbench side, W3b for Gravity Forms, W4). It
answers only with `QUILL_WORDPRESS_WORKBENCH_WINDOW=1`
(`quill/core/wordpress/workbench_flag.py`); then the Tools > WordPress doors
(Comments, Media Library, Categories and Tags, Menus, Site Check, Site
Settings, Site Map, and Manage's Users, Application Passwords, Plugins,
Themes, Fonts, Synced Patterns, Widgets and AI Abilities) open it at their
node, through one call (`WordPressCommands.workbench_door`) both editors
share. Not yet tried against the live site or with a screen reader.

- **The tree (W1, PRD 5).** `workbench_tree.py`: Start Here; Needs My
  Attention (Inbox, Comments Waiting, Pending Review, Scheduled, Drafts, Site
  Health, Held as Spam, Form Responses, and Updates, Accessibility, Broken
  Links, Orders and Watches shown with where each lives today); Sites, with
  every connected site's Overview, Posts and Pages by status (pages as a tree
  by parent), More Content Types and More Taxonomies with a node per
  discovered type and taxonomy (the shared engine's new `NodeSpec.dynamic`),
  Media by kind, Unattached and Without Alt Text, Comments by status,
  Categories, Tags, Menus and Navigation, Appearance (Themes, Templates,
  Template Parts, Patterns, Fonts, Widgets and Sidebars), Forms (Responses,
  Held as Spam), People (Users, Application Passwords), Plugins, Settings,
  Site Health, Abilities and More from This Site; Help and Learning (How
  WordPress Thinks, Words, Keys). Lists come from `workbench_load.py` through
  each site's own client, Needs My Attention from `workbench_attention.py`
  (one row for a site that does not answer). Enter on a post or page is the
  editor's own `open_item`. The status bar has Site, Your Role, Items,
  Filter, Loading, Waiting and Workbench Access.
- **Properties (W2, PRD 8, Appendix A).** `workbench_sheets.py` has a sheet
  for items (General, Organize with a field per taxonomy, Featured Image,
  Excerpt, Discussion, Template and Parent, Meta from the registered meta),
  media, comments, terms, users, plugins, themes, application passwords,
  settings and the site (with a read-only Spam page); anything else gets a
  sheet built from its route's schema (`OPTIONS`), or from the object
  itself. Terms and authors read "News (12)" and save by id or name. The
  sheet is the shared engine's new editable sheet
  (`quill/ui/workbench_sheet_editor.py`, OK, Cancel, Apply, Mixed values, a
  locked field's reason as its F1 help).
- **Editing and batch (W3, PRD 9 and 10).** `workbench_edit.py`: only the
  changed fields go back, under WordPress's names; the conflict check reads
  the object again and compares `modified_gmt`; the verify after names any
  field the site did not keep; the undo body goes to the shared Change
  History, and Ctrl+Z runs it. Several rows at once get the batch sheet
  (status, author, comments, pingbacks, sticky, template, parent, categories
  and tags added and removed; media titles, alt text, captions and
  descriptions), a preview, `batch/v1` with a result per item, one at a time
  where the site will not batch, and Try Again for failures. Delete is
  Trash for posts, pages, custom items and comments; Shift+Delete is Delete
  Permanently, confirmed by name. Filters (`workbench_filter.py`) turn the
  shared query string into `query.build()` parameters, with term slugs and
  names looked up, and filter loaded rows here for lists the API cannot
  filter; the Filter Builder, Show Only Like This, Hide Like This and Only
  Mine write the same string.
- **Spam (W3a, Workbench side, PRD 13a.5).** Held as Spam gathers comments
  in `spam` and form entries held as spam; Not Spam (Ctrl+Shift+A) puts a
  comment back in the queue and a QAF entry back to `active`, Spam
  (Ctrl+Shift+S) the other way, one or many, each undoable. The Spam page on
  the Site sheet is read only; the PRD's provider states, thresholds and
  question bank need QAF's spam work first.
- **Gravity Forms (W3b, PRD 13b).** `workbench_forms.py` finds form plugins
  by namespace only: QAF on `qaf/v1` (or `baf/v1`) and Gravity Forms on
  `gf/v2`, whose forms and entries list with their status, and whose Spam
  and Not Spam send the whole entry back (`PUT`), as its API replaces
  entries. A new egress sentence covers `gf/v2`.
- **Permissions (W4, PRD 11).** `workbench_permissions.py`: every action
  names its capability and tier; a refused one is greyed in the context
  menu and, reached by key, says why ("Publishing pages needs the Editor
  role or higher. You are an Author on Community Radio."), and Shift+F1
  lists all of them. Workbench Access per site (Read Only, Organize, Full,
  kept in `workbench_access.json` beside the site list); Safe Mode and View
  As Role are Read Only. `workbench_people.py`: Change Role and Remove with
  reassignment (the preview counts the posts), refused for your own
  Administrator role and for the last Administrator; New Here makes an
  application password and shows its secret once; Delete revokes one. A
  warning comes before deactivating QAF or the Application Passwords plugin.
- **Keys (Part C).** The bar is `workbench_actions.WINDOW_MENU`, checked by
  `menus.problems`. Delete, Shift+Delete and Ctrl+Z act only in the list:
  the shared frame's new `workbench_frame_keys.py` keeps them away from the
  filter box, where they edit the text.
- **Shared engine, additive only.** `NodeSpec.dynamic`; the frame's optional
  provider hooks (`dynamic_children`, `current_instance`, `filter_help`,
  `no_instance_text`, `list_keys`), no tree event while the frame is being
  destroyed; the editable sheet as a new module beside the read-only one.
- Tests: `tests/unit/core/wordpress/test_wp_workbench_core.py` (25) and
  `tests/unit/ui/wordpress/test_wp_workbench_window.py` (20, a real frame on
  a fake site). The live regression has not been run on this branch.

### 2026-11-10: the WordPress Workbench, W5 to W8, and the default way in

The rest of the Workbench PRD's phases, one commit each, on the same branch
as W1 to W4. None of it has met the live site or a screen reader yet.

- **W1 to W4 leftovers.** File > WordPress > Properties is now built from the
  Workbench's item sheet (`workbench_copy_sheet.py`, PRD 8): the editor's
  sheet keeps the fields a working copy sends, and the Workbench's new fields
  reach it. View > Load More and Load All (`workbench_listing.py`, a page
  limit the loaders read, up to ten thousand rows), Columns, and Group By as
  a Group node of child values under Posts, Pages, Media, Comments and
  Plugins. New Here for every creatable kind, Merge Into and Convert to
  Category or Tag (`workbench_create.py`), Send Password Reset as a wp-admin
  pointer, Roles and What They May Do, Empty Spam (tier 3) and Not Spam, and
  Allow This Sender. F1 on the tree and the list answers from
  `workbench_node_help.py`, which a test holds to every node and row type.
- **W5 coverage.** `workbench_coverage.py` classifies every route by rule
  (covered, schema_built, planned, wp_admin_only, out_of_scope, each with its
  home), and `quill/tools/wordpress_coverage_audit.py` is the gate over the
  recorded index with `route_coverage.json` as the snapshot, in
  platform_report as wordpress-coverage: 802 routes, 143 covered, 33 built
  from their schema, 386 planned, 158 in wp-admin only, 82 out of scope.
  More from This Site lists namespaces with the routes reached, and a node per
  namespace lists its routes (`workbench_discovered.py`); the Content Model
  lists post types and taxonomies with who registered them, read only
  (QUILL Site Types detected by namespace); Abilities run with their input
  schema as a sheet and a preview.
- **W6, complete.** The Tools > WordPress doors always open the Workbench.
  The classic-window preference and environment override are removed.
  Open WordPress Workbench remains the first row in both editors, on the
  layer's H, with a command catalogue row.
- **W7.** `workbench_bold.py`: Copy to Site (plan as preview, terms by
  name, links rewritten, pictures read from the source host and uploaded),
  Compare Sites, Take a Snapshot, the Calendar with a node per day, Read Site
  as Document (opened in the editor for its exports). The editorial queue on
  items (Approve and Schedule, Send Back with a Note, Assign a Reviewer,
  through block notes). `workbench_io.py`: Export List as CSV or Excel,
  Import Posts from a Spreadsheet, and the REST Console's completion,
  capability, parameters and answer tree (`quill/ui/wordpress_rest_console.py`).
  Watches (`workbench_watches.py`) run on the editor's existing two-minute
  WordPress timer through `wordpress_watch_commands.py`, at most every
  fifteen minutes, first round silent. The Practice Site
  (`workbench_practice.py`) starts WordPress Playground through the bundled
  Node with a blueprint that leaves QUILL an application password, and
  connects it; `scripts/fetch_build_deps.py --only wp-playground-cli` stages
  `@wp-playground/cli` 1.0.28 (GPL-2.0-or-later) from
  `scripts/wp_playground/package.json`. That entry has never been run: no
  download was made, there is no lockfile yet, and the pin is to verify.
- **W8.** `workbench_across.py`: By Name under each site (terms, field
  values, authors, media usage, patterns, links, blocks and shortcodes,
  forms, from one scan kept five minutes), Across Sites (Ctrl+0) for terms,
  plugins, themes, people and settings with Variants and Missing From, Site
  Sets and the scope, Make Them the Same with a site-by-site preview (terms,
  plugin status, settings), Promote to Network where a site reports
  network-only plugins, and the Fleet view.
- **15.11, core first.** `workbench_sweep.py`: Content Audit, Media >
  Housekeeping, Privacy Requests (wp-admin pointers, as core has no route),
  and the redirect offered after a slug change only where `redirection/v1`
  is in the index (its body is from the plugin's documentation, to verify).
- Tests: `test_wp_workbench_leftovers.py`, `test_wp_workbench_bold_core.py`,
  `test_wp_workbench_across_core.py`, `test_wordpress_coverage_audit.py`, and
  in the real frame `test_wp_workbench_lists.py`, `test_wp_workbench_default.py`,
  `test_wp_workbench_bold.py` and `test_wp_workbench_across.py`.

## 19. Remaining tasks

**wp-admin parity (9.18), Jeff 2026-11-04, "we should have all of this":**

- [ ] Route gaps 1-15 (9.17 and menus): feat/wordpress-followup.
- [ ] Package 1: lists and filters for posts, pages and media; bulk trash, permanent delete, Quick Edit.
- [ ] Package 2: Properties, the rest of the sidebar (author, format, parent, template, pingbacks, date, featured image).
- [ ] Package 3: media details (title, caption, description, detach, download, crop by numbers).
- [ ] Package 4: comments, complete.
- [ ] Package 5: people, complete.
- [ ] Package 6: Dashboard (At a Glance, activity, plugin summaries).
- [ ] Package 7: Site Editor writing (templates, parts, Additional CSS).
- [ ] Package 8: WooCommerce catalog.
- [ ] Package 9: WooCommerce orders, customers, coupons, reports.
- [ ] Package 10: WooCommerce store settings.
- [ ] Package 11: The Events Calendar, complete.
- [ ] Package 12: Yoast SEO, complete.
- [ ] Package 13: forms on the site, complete.
- [ ] Package 14: Open in Dashboard for every screen REST cannot reach.
- [ ] Manual: every new window and control in docs/user guide/wordpress-and-forms/.

This list is kept current. A task is removed when it is done and checked, and
the progress log above says what was done. Everything not listed here is
built.

### WordPress Workbench (Workbench PRD, after W1 to W8)
- Run `docs/qa/wordpress-live-run.py` and a screen-reader pass (NVDA and
  JAWS) on the Workbench: nothing from W1 to W8 has met a live site, and
  Delete and Ctrl+Z being kept from the filter box rests on wx's key hook
  running before menu accelerators. The Workbench is now the default, so this
  comes before the next release.
- The Practice Site: run `python scripts/fetch_build_deps.py --only
  wp-playground-cli` once (it has never run), commit the lockfile it writes,
  confirm the `@wp-playground/cli` pin and its entry point
  (`wp-playground.js`), add it to the shared runtime's build and to
  `quill/data/third_party/components.json`, and check on a live run that the
  blueprint leaves the application password and that Playground accepts it
  over plain HTTP on 127.0.0.1. Playground fetches WordPress itself on first
  start unless that is staged too; decide before shipping (15.1 says
  bundled).
- The WordPress Workbench's own APP_KEYMAPS entry (Part C): its keys are the
  window's menu table today, so they are not rebindable.
- Users: Sessions and others' application passwords; the PRD's Users, the
  rest (invite from a spreadsheet, sign out everywhere).
- Spam: the provider states, thresholds, blocklist and question bank on the
  Spam page (needs QAF's spam work, 13a.3 and 13a.6); the weekly Watch.
- QAF and Gravity Forms are the supported form integrations. Paid Memberships
  Pro is the supported membership integration through the site's documented
  Abilities API. Other plugin-specific integrations are outside the current
  implementation scope; see the [current scope record](../planning/workbench-implementation-status.md).
- Updates, Accessibility, Broken Links, Orders, Shop, Podcast and Search
  nodes; Global Styles as a node.
- 15.12 operations beyond listing: rename, split and reassign a value
  everywhere from By Name; Make Them the Same for themes, people and menus;
  install a plugin on the sites missing it; compare global styles.
- 15.11 plugin rows (Redirection beyond the slug offer, backups, security,
  caching, multilingual, memberships, courses, stats and the rest): each
  behind its namespace, after its API is checked against a live install.
  The redirect body is from the plugin's documentation and is unverified.
- This Post in the Workbench (File > WordPress) and the Media Library's
  picking mode for Insert Picture (PRD 14).
- QUILL Site Types (12b, decision 12): the plugin, then making types and
  fields from the Content Model.
- **Completed:** remove the classic WordPress management-window choice and
  route all management doors to the Workbench.
- The Workbench in the WordPress and Forms manual
  (`docs/user guide/wordpress-and-forms/`); the editors' user guides have
  their section.

### Workbench groundwork (Workbench PRD WP-R-030 to WP-R-034)
- Run `docs/qa/wordpress-live-run.py` on the branch before it merges:
  taxonomy discovery, Custom Fields lists and groups, and a custom type's
  terms have only met recorded responses.
- Custom types: New per type (the Workbench has a node, batch and filters
  for each; its statuses as child nodes are left too).
- Custom fields on terms, users and comments: a window or sheet page (the
  core is in `custom_fields.py`).
- Advanced Custom Fields: send changes back as `{"acf": ...}` and show the
  fields in Custom Fields; Meta Box, Pods and CMB2.
- Spoken labels for the seven plugin orderings the combination test lists
  as planned (the Workbench's Filter Builder now writes `query.py` queries).

### Every route, and more value (9.16)
- **Waiting on Jeff:** the icons list, upload in pieces and Regenerate Sizes,
  tried signed in on the live site (regression tests 43 to 45; the
  signed-in run needs a write on the test host, which the guard refuses).

### More from the API (9.15)
- **Waiting on Jeff:** Notes on blocks, tried on the live site (built from
  the documented shape; needs the signed-in run).
- **Waiting on Jeff:** The Events Calendar, WooCommerce, SEO plugins and
  Abilities, tried on a site that has them (installing them on the test
  site is a write on the test host).

### Forms (17a)
- **Waiting on Jeff:** a key for the Forms commands (the only free option is
  a letter on the WordPress key layer).
- Run the Forms regression tests 63 to 68 with BAF on the test site
  (**waiting on Jeff**, 17a.13 question 3).
- The plugin's own next pass (Preview, the Accessibility Coach, canvas
  actions for sections and columns, repeater cards, Convert rewriting
  conditions); the QAF rename on both sides *(in progress)*.
  **Waiting on Jeff:** the BAF changes tried in a real
  WordPress with NVDA and JAWS (this machine has no WordPress).
- **Payments, waiting on Jeff:** the plugin's `feat/qaf-payments` run with
  real PHPUnit and the WordPress test suite; installed on a test site with
  Stripe test keys and a PayPal sandbox app; and the live checks in
  `docs/qa/forms-payments-acceptance.md`, including a screen-reader pass
  through Stripe's Payment Element and PayPal's buttons. Pushing the
  branch is his call.

- **Waiting on Jeff:** the three questions in 17a.13 (the file extension,
  answered in 17a.17: `.qaf`; the shared conformance
  suite, built in BAF's repository so either answer works; installing BAF on
  the test site), and pushing `feat/json-form-model` in `S:\code\baf` (the
  guard refuses publishing a branch here), and pushing BAF's
  `chore/mit-license`, after which it is merged into `feat/json-form-model`.

### Docs and gates
- CI green on the pull request, Community-Access/quill#1762 (opened as a
  draft on 2026-11-05; CI's sharded suite is the gate, the local full suite
  outruns an hour on this machine). platform_report was 53 of 53 locally.

### Connecting
- **Waiting on Jeff:** WordPress.com sign-in, once the client id exists (he
  registers the app at developer.wordpress.com/apps).
- **Waiting on Jeff:** a Contributor's role and the Events type, tried signed
  in against the live site (regression tests 15, 38 and 39). Copying QUILL's
  core to lp.csedesigns.com, or running setup.sh there, is a write on a
  remote machine, which this session's permission guard refuses.


### Media for listening (9.6)
- **Waiting on Jeff:** run `setup.sh` on the test site to seed the tone, the
  video, the Listen and Watch page and the Events type, then try playback
  live with a screen reader (writing on the test host is outside this
  session's permissions).

