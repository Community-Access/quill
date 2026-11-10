# WordPress Workbench: product requirements

| | |
|---|---|
| Product | The WordPress Workbench, in QUILL and QUILL Lite |
| Owner | Jeff Bishop, Community Access |
| Status | Accepted by Jeff, 2026-11-09, with every decision taken as recommended. This is the accepted scope; current implementation status and later scope decisions are in the [Workbench implementation status](../planning/workbench-implementation-status.md) |
| Version | 1.0 of this PRD, 2026-11-09 |
| Sister PRD | [GitHub Workbench PRD](./github-workbench-prd.md). This PRD reuses its engine, its keys and its rules, and cites its sections as "GitHub PRD 15.2" |
| Plan of record it extends | `docs/design/wordpress.md` (WordPress and Forms in both editors), cited as "wordpress.md 9.18" |
| Checked against | `S:\QUILL` main, 2026-11-09: 63 modules in `quill/core/wordpress`, about 70 `quill/ui/wordpress_*` modules, 66 dialog rows in `quill/core/wordpress/menu.py`; the test site's REST index (802 routes in 27 namespaces, WordPress 7.1.4, wordpress.md 9.18) |

## Later implementation scope decision (2026-11-10)

For the current implementation, plugin-specific support is limited to **QUILL
Accessible Forms (QAF), Gravity Forms, and Paid Memberships Pro**. The other
plugin candidates named in section 13b.2 remain part of this original accepted
specification's history; they are removed from the current delivery scope.
WordPress's general route and Abilities discovery remain available as core
Workbench features, but discovery alone does not promise a first-class
integration for another plugin. The current delivery record is in the
[Workbench implementation status](../planning/workbench-implementation-status.md).

This accepted PRD is the canonical product scope for the WordPress Workbench.
The earlier [WordPress design and implementation log](../design/wordpress.md)
is retained as history and links back here for current requirements.

## Additional user requirement: change an existing form field's control

An existing QAF field can change to another supported control type after it
has been added. QUILL preserves the label, help, rules, compatible choices and
other shared properties; converts single and multiple defaults where needed;
and previews settings that will be adjusted or dropped. A conversion that
needs required setup first is refused with the missing properties named.

For Gravity Forms, QUILL offers conversion for common text, paragraph, email,
number, drop-down, radio and checkbox controls. It reads and retains the full
form object, shows the selected field and conversion preview, checks for
concurrent edits, then updates through REST v2 only after confirmation and the
site's `gravityforms_create_form` capability check. Other field families stay
untouched until their API behavior is supported.

## How this document is organized

- **Part A, the product:** what it is, who it is for, and what a great day
  sounds like.
- **Part B, the design:** the shared engine, the window, the tree,
  Properties, editing, filtering, permissions, coverage, and a bold sweep of
  what only this Workbench could do.
- **Part C, keys; Part D, help; Part E, requirements; Part F, quality;
  Part G, rollout.**
- **Appendices:** every object and its Properties sheet (A); every shipped
  WordPress window and its new home (B); the REST families and what they feed
  (C); and every route on the test site with every argument and value (D),
  generated from its REST index, with a note on GraphQL.

## Part A: the product

### A1. In one paragraph

Writing a page stays where it belongs, in the editor, where QUILL already
makes blocks plain and checks a page before it goes out. Everything else
about running a WordPress site (comments, media, menus, people, plugins,
themes, settings, forms, the shop, the podcast, the site's health, and every
site you look after) moves into one WordPress Workbench: a tree of where you
are, a list of what is there, details about the one you picked, and
Alt+Enter for the Properties of anything. It is built on the same engine as
the GitHub Workbench, so the two windows look, sound and answer the keyboard
the same way, and learning one is learning both.

### A2. The short version

- **Writing stays in the editor; running the site moves to the Workbench.**
  Enter on a post or page opens it in the editor. Everything that is not
  writing a document gets one home.
- **One engine, two Workbenches.** The tree, list, details, Properties
  sheets, filters, action table, tiers, Change History, help catalogue and
  coverage gate are built once, in shared modules, and GitHub and WordPress
  are two providers of the same window shape (section 3).
- **Needs My Attention, across every site:** comments waiting, drafts
  waiting for review, scheduled posts, updates available, Site Check and
  accessibility problems, new form responses, new orders, broken links,
  pictures with no alt text.
- **Alt+Enter is Properties, on everything:** posts, pages, media, comments,
  categories, tags, menus, users, plugins, themes, templates, patterns, fonts,
  widgets, settings, forms, responses, products, orders, and any custom
  post type a plugin adds.
- **Any plugin's content, automatically.** WordPress describes every route
  with a schema, so the Workbench builds a list and a Properties sheet for
  custom post types, taxonomies and plugin routes it has never seen
  (section 12).
- **Edit everything the site lets you edit,** in batch through WordPress's
  batch endpoint, verified afterwards, undoable through revisions and Change
  History.
- **Filter on every attribute** the REST API can query, and on the rest
  locally, honestly.
- **Permissions from the account's own capabilities,** known before
  offering, explained when missing, and managed where WordPress lets them be
  (roles, application passwords, registration, discussion), with View As
  Role.
- **Bold extras:** a practice site that runs on this computer through
  WordPress Playground, site to site copying (staging to live), a content
  calendar, an editorial queue, the whole site read as a book, Watches,
  plain-language batches, a REST Console, and the WordPress Abilities API as
  commands.
- **The same keys as the GitHub Workbench.** Ctrl+number to go places,
  Alt+number to hear where you are, Delete to move to Trash (which WordPress
  can undo), Alt+Enter for everything else, and typing always moves through
  the list.
- **Help that teaches WordPress,** for people who have never opened wp-admin.

### A3. The problem

wordpress.md built a great deal, and put each command where a Word user
looks (wordpress.md 12): File > WordPress for the document and the site,
Insert, Format, View and Edit for what happens inside a page, and Tools >
WordPress for everything else. Writing works well that way. Running a site
does not:

- **Tools > WordPress is a row of separate windows:** Media Library,
  Comments, Categories and Tags, Menus, Site Check and Settings, Manage (users,
  plugins, themes, fonts, synced patterns), Site-wide Find and Replace, Alt
  Text Review, Visual Review, Check the Whole Site. Each has its own layout,
  list and buttons. Moving from a comment to the post it is on, to that
  post's author, to their role, is four windows.
- **No place says what needs you.** Pending comments, posts waiting for
  review, updates and Site Check problems are each found by opening the right
  window.
- **Several sites multiply it.** Switch Site changes one current site, so a
  person who looks after five sites checks each in turn.
- **What a plugin adds is invisible.** A custom post type (events, recipes,
  courses, products) has no window unless QUILL wrote one for that plugin.
- **wp-admin is still the fallback** for whatever has no window, and wp-admin
  is the reason this exists.

### A4. Goals

1. **Parity with wp-admin** wherever the REST API reaches, measured by the
   route audit (wordpress.md 9.17 and 9.18) turned into a gate (section 12).
2. **Better than wp-admin by ear:** moderation, media, menus, people,
   settings and site health become lists you can move through and sheets you
   can read.
3. **One window shape across the family.** A person who knows the GitHub
   Workbench knows this one.
4. **Every site at once** where that helps: one Inbox, one search, one
   calendar.
5. **Safe:** previews, Trash first, revisions, verify after save, no
   self-lockout.
6. **Help everywhere,** in plain words.
7. **QUILL Lite is never ahead,** and never behind: the same window in both.

### A5. Not goals

- Replacing the editor for writing. The Workbench never edits a page's
  blocks; it opens the page in the editor.
- Hosting or installing WordPress on a server.
- Editing role capabilities, which WordPress's REST API does not offer; the
  sheet shows them read-only and says so (section 11).
- A visual site builder. Design changes go through global styles, templates
  and patterns as data, with Visual Review (wordpress.md 6.11) for checking.

### A6. People it is for

| Person | Comes to | Delight |
|---|---|---|
| A blind blogger with one site | write, moderate comments, keep it healthy | "3 comments waiting" in Inbox, approve with Enter, the site's health in one sentence |
| A community radio station's volunteer | publish shows, the podcast, the schedule | Post This Episode, the content calendar, Watches for new responses |
| A small business owner | the shop, orders, forms with payments | new orders in Inbox, an order read as a receipt |
| A web person with ten client sites | updates, health, access, copying between sites | one Inbox across sites, batch updates, site to site copy |
| An editor in a newsroom | the review queue, scheduling, authors | Pending Review in Inbox, the calendar, change an author in batch |
| A teacher or club organizer | pages, events, sign-up forms | forms responses as a list, export to a spreadsheet |
| A first-time site owner | learn WordPress at all | the practice site on their own computer, the glossary |

### A7. Journeys

1. **Morning across five sites.** Ctrl+1: "Inbox (9)". "Community Radio, 3
   comments waiting." Enter on one reads it with its post; Ctrl+Shift+A
   approves; Delete moves spam to Trash. "Client Bakery, 2 plugin updates."
   Alt+Enter shows what each update changes; Update... runs both with a
   preview. "Inbox is empty."
2. **A new event type.** A site uses an events plugin QUILL has never heard
   of. The tree shows "Events (12)" under the site, discovered from the REST
   index. Alt+Enter on an event opens a sheet built from the plugin's own
   schema: date, venue, price, each a labelled control.
3. **A volunteer gets access.** Ctrl+N on Users, a name, an email, the role
   Author. The preview: "Add Sam as an Author on Community Radio. Sam will be
   able to write and publish their own posts, upload pictures, and not touch
   pages, comments or settings." View As Role first shows the Workbench as an
   Author sees it.
4. **Staging to live.** Select the eight pages changed on the staging site,
   Copy to Site..., choose the live site. The preview names every page,
   picture and menu item that will be created or replaced there, and the
   pictures' alt text goes with them.
5. **Learning.** A new site owner chooses Help > Practice Site. A real
   WordPress starts on their own computer in seconds through WordPress
   Playground; they publish, break and delete things; nothing reaches the
   internet.

### A8. Delight, on purpose

The GitHub PRD's A8 applies as written: one specific sentence per outcome,
sounds through the shared feedback channels, counts where you look and never
announced, celebrations that fit ("Every picture on Community Radio has alt
text now."), no dead ends, it remembers you, and no hunting for keys.

### A9. Success measures

| Measure | Target before the Workbench replaces the Tools > WordPress windows |
|---|---|
| Route coverage (section 12) | Every route on the test site classified; `missing` zero |
| Help coverage | 100 percent of nodes, row types, fields and commands |
| Tasks with five people (section 17) | All completed; at most one wrong turn each; faster than wp-admin by screen reader |
| Screen readers | NVDA, JAWS and Narrator recorded per phase |
| wp-admin fallbacks | Only where no REST route exists, each listed |

## Part B: the design

### 1. What exists today (verified)

- **Writing:** New Page, New Post, Open, Save Draft to Site, Publish or
  Update, Schedule, Properties (wordpress.md 5.5), Previous Versions, Compare
  with Site, Trash; blocks made plain with a Blocks tree window; Check Before
  Publishing. These stay in the editor.
- **Windows under Tools > WordPress:** Media Library (with Listen and Watch,
  the player, upload, alt text, Make a Picture, Visual Review), Comments (a
  thread tree), Categories and Tags, Menus (a tree), Site Map, Site Check and
  Settings, Manage (users, plugins, themes, fonts, synced patterns),
  Site-wide Find and Replace, Alt Text Review, Check the Whole Site, Forms and
  their responses and payments, the shop, Post This Episode.
- **Knowledge:** capabilities from `users/me?context=edit` drive dimming with
  reasons (wordpress.md 9.2); a route coverage audit exists as a document
  (wordpress.md 9.17); a wp-admin parity checklist (wordpress.md 9.18).
- **Both editors** build their WordPress rows from `quill/core/wordpress/menu.py`.

### 1a. What today's implementation is missing (audited 2026-11-09)

Checked against `S:\QUILL` main and the test site's REST index (Appendix D).
Some of this exists in part, which makes the gaps more striking:

| Area | What exists | What is missing |
|---|---|---|
| Custom post types | `site_types.writing_types()` reads `wp/v2/types` and Open Page or Post can open an item of a custom type | No node or list per type, no browsing by status, no New for a custom type, no batch, no filters, and no type-specific taxonomies. On the test site that leaves Events, Venues, Organizers, Products and calendar embeds (The Events Calendar, WooCommerce) unreachable except by opening one you already know |
| Custom fields (post meta) | `custom_fields.py` reads each type's schema with `OPTIONS` and shows scalar meta (text, numbers, true or false, choices) in Properties | Lists and objects are "left alone" and only counted, so repeaters, galleries, relationships and grouped fields cannot be seen or edited. Meta on terms, users and comments is not read at all |
| Field plugins | none | Advanced Custom Fields (its `acf` REST field and field groups), Meta Box, Pods and CMB2 each expose fields their own way; none is read |
| Custom taxonomies | categories and tags, and other taxonomies by guessing their route | `taxonomy_route()` guesses `wp/v2/{taxonomy}` instead of reading each taxonomy's `rest_base` from `wp/v2/taxonomies`, so any taxonomy whose route differs from its name breaks. Nothing discovers which taxonomies exist, which types they belong to, or whether they are hierarchical. On the test site: product categories, tags and brands, event categories |
| Statuses | core statuses | `wp/v2/statuses` is not read, so plugin statuses (WooCommerce's order statuses, privacy request statuses) are unknown to filters and the Status choice |
| Query combinations | status, search, author, parent, order, sticky, menu order, format in places | Never used: `tax_relation` (AND or OR across taxonomies), `categories_exclude`, `tags_exclude`, `modified_after`, `modified_before`, `search_columns` (title, content, excerpt), `search_semantics`, `ignore_sticky`; `before` and `after` barely. Every one is a filter a person cannot ask for today |
| Site-wide search | per type | `wp/v2/search` (one search across every type, term and format) is not used |
| Plugins and blocks | plugins listed and managed | the block directory (`wp/v2/block-directory`: find and install block plugins) and `widget-types` are not used |
| Multisite | nothing | networks, their sites, network plugins and themes, super admins |
| Plugin namespaces on the test site | WooCommerce `wc/v3`, Yoast `yoast/v1`, The Events Calendar `tribe/events/v1` in part | WooCommerce analytics and reports (`wc-analytics`, `wc-admin`, 186 routes), the rest of The Events Calendar (`tec/v1`, Event Aggregator), Jetpack (`jetpack/v4`), and an unidentified `baf/v1` |
| QAF on the test site | QAF is the family's own forms plugin | the test site does not run it (no QAF namespace in its index), so the live regression run cannot cover QAF's REST API or its spam handling; install it there |
| Revisions and autosaves | Previous Versions | revisions for custom types and templates |

Every row becomes covered through section 12 (discovery and schema-built
sheets) and section 12a (every combination), and each is a `missing` row the
coverage gate shows until it is.

### 2. Principles

1. **Writing is a document; a site is a place.** Documents open in the
   editor. Places open in the Workbench. Enter on a post is "write"; Alt+Enter
   is "about".
2. **One engine.** Nothing here is built twice: if the GitHub Workbench has
   it, WordPress uses it, and anything WordPress needs that GitHub would too
   goes in the shared engine.
3. **Where, what, about** (GitHub PRD 2.1); **one home per feature, chosen by
   what kind of thing it is** (GitHub PRD 2.2).
4. **Trash first.** Anything WordPress can put in Trash goes there, and
   Delete means Trash. Permanent deletion is a separate, tier 3 command.
5. **The site's own words.** Statuses, roles and settings use WordPress's
   names, explained in the glossary, never renamed.
6. **Discover, don't hard-code.** Post types, taxonomies, statuses, settings,
   routes and abilities come from the site, so a plugin's additions appear
   without a QUILL release.
7. **The existing windows are not thrown away;** their loaders, savers and
   checks become the Workbench's providers.

### 3. The shared Workbench engine

The GitHub PRD designs the engine for GitHub (GitHub PRD 10, 15 to 18).
This PRD asks that it be built provider-neutral from the first PR:

| Shared module (wx-free unless marked) | What it holds | GitHub provides | WordPress provides |
|---|---|---|---|
| `quill/core/workbench/tree.py` | `NodeSpec`: key, label, parent, scope, needs, loader, row type | GitHub's tree | each site's tree, discovered |
| `quill/core/workbench/actions.py` | the action table: rows per row type, tier, requirement, help, default | GitHub actions | WordPress actions |
| `quill/core/workbench/properties.py` | sheet models: pages, fields, requirement, loader, saver, conflict check, verify | GitHub sheets | WordPress sheets, and schema-built sheets (section 12) |
| `quill/core/workbench/filters.py` | the one query, the builder's attributes and operators, local filtering | GitHub search syntax | REST query parameters |
| `quill/core/workbench/history.py` | Change History and Undo | GitHub changes | WordPress changes, with revisions |
| `quill/core/workbench/help.py` | node, row, field and glossary help | GitHub words | WordPress words |
| `quill/core/workbench/coverage.py` | the coverage table and gate | GitHub's API description | each site's REST index |
| `quill/ui/workbench_frame.py` (wx) | the frame, panes, menus, sheets, previews, results | | |

`quill/core/github/workbench_*` and `quill/core/wordpress/workbench_*` then
hold only what is particular to each. The GitHub PRD's Phase 1 spike builds
the frame; this PRD's Phase W0 is the refactor that makes it shared before
either provider grows (Part G).

### 4. The window

"WordPress Workbench - Community Radio". Everything in GitHub PRD 3.1 and
3.2 holds: a top-level frame with its own menu bar, status bar and taskbar
button, one per app, never blocking the editor; F6 between tree, filter
box, list, details and the status bar; it remembers where you were, per site.

**The status bar is one you can move through and act on,** the GitHub
PRD's 3.2.1 contract from the shared engine: F6 reaches it (no Tab stops),
Left and Right move cell to cell, Home and End jump to the ends, Enter does
the obvious thing, the Applications key or Shift+F10 opens the cell's
actions, Escape goes back, every menu ends with Copy and Help for This Cell,
and the same facts are mirrored to the real status bar and to Alt+1 to Alt+9.

| Cell | Reads | Enter | Context menu |
|---|---|---|---|
| Site | "Site, Community Radio" | Select it in the tree | Site Properties (Alt+Enter); Open the Site; Open wp-admin; Switch Site...; Copy Address |
| Your role | "Editor on Community Radio" | What Can I Do Here? | What Can I Do Here?; View As Role...; Application Passwords |
| Items | "48 posts, 2 selected" | Select All | Select All; Clear Selection; Export List...; Columns...; Load All |
| Filter | "Filter, category:events" or "No filter" | Filter Builder... | Edit; Clear; Save as Search...; Pin to Needs My Attention |
| Loading | "Up to date, 14:05" | Refresh (F5) | Refresh; Cancel Loading; Load All |
| Health | "Health, Should be improved, 2 problems" | Go to Site Health | Go to Site Health; Run the Checks Again; Explain |
| Waiting | "3 comments waiting, 1 held as spam" (only when there are any) | Go to Comments Waiting | Comments Waiting; Held as Spam; Approve All Waiting... (with the preview) |
| Updates | "2 updates" (only when there are any) | Go to Updates | Go to Updates; Update All... (with the preview); What Changed |
| Workbench access | "Full" or "Read Only" | Change... | Read Only; Organize; Full; Dry Run on or off |

### 5. The tree

```
Start Here
Needs My Attention                 every site you have, together
    Inbox                          everything below, newest first
    Comments Waiting (n)
    Pending Review (n)             posts and pages submitted for review
    Scheduled (n)                  with their dates
    Drafts (n)                     your own
    Updates (n)                    WordPress, plugins, themes, translations
    Site Health (n)                Site Check problems
    Accessibility (n)              Check the Whole Site findings, pictures without alt text
    Broken Links (n)
    Held as Spam (n)               comments and form entries the site doubted (13a.5)
    Form Responses (n new)
    Orders (n new)                 sites with a shop
    Watches
Sites
    <site>                         one per connected site, with your role
        Overview                   the site in sentences: name, address, WordPress version, health, counts
        Posts                      by status as children: Published, Drafts, Pending, Scheduled, Private, Trash
        Pages                      as a tree by parent, then the same statuses
        <each custom post type>    discovered: Events, Courses, Products...
        Media                      by type: Pictures, Audio, Video, Documents; Unattached; Without Alt Text
        Comments                   Waiting, Approved, Spam, Trash
        Categories                 as a tree by parent
        Tags
        <each custom taxonomy>     discovered
        Menus and Navigation       each menu, its locations, navigation blocks
        Appearance
            Themes
            Global Styles
            Templates
            Template Parts
            Patterns               synced and site patterns
            Fonts
            Widgets and Sidebars
        Forms                      each form, its responses, payments
        Shop                       products, orders, customers, coupons, reports
        Podcast                    episodes, the feed
        People
            Users                  by role
            Application Passwords  yours, and others' where you may
        Plugins                    active, inactive, updates
        Settings                   General, Writing, Reading, Discussion, Media, Permalinks, Privacy
        Site Health                tests and their results, the site's information
        Abilities                  what the site's Abilities API offers (WordPress 6.9 and later)
        More from this site        every other REST route family, by namespace
    Network                        multisite: its sites, network plugins and themes, super admins
Calendar                           every site's scheduled and published content, by day
Search                             across every site: posts, pages, media, comments, users
Practice Site                      the WordPress Playground site (section 15.1)
```

Rules from GitHub PRD 3.3 and 9 hold: native tree, four levels at most,
lazy loading, counts last and never announced, nodes needing a capability
always shown with the reason.

### 6. Menus

Built from the action table, every row with its key or reason, greyed rows
with their reason (GitHub PRD 4):

- **File:** New (Post, Page, each custom type, Media Upload, User, Category,
  Tag, Menu, Form, Product, Site Connection), Open in Editor, Open on Site,
  Open in wp-admin, Connect a Site, Close Workbench.
- **Edit:** Copy, Copy Link, Copy as Text, Filter, Filter Builder, Select
  All, Undo WordPress Change, Find and Replace Across Sites...
- **View:** Status, Sort, Columns, Group By, Refresh, Load More, Back,
  Forward, Calendar View.
- **Go:** the tree's places, and Next Waiting Comment, Next Draft, Next
  Problem.
- **Item:** everything for the selected rows: Open in Editor, Properties,
  Publish, Schedule, Submit for Review, Make Private, Move to Trash,
  Restore, Delete Permanently, Duplicate, Copy to Site, Approve, Unapprove,
  Spam, Reply, Activate, Deactivate, Update, Set as Featured Image, and the
  rest by row type.
- **Site:** Switch Site, Site Properties, Check the Whole Site, Site Health,
  Updates, Export, Copy Site Content to Another Site, Application Passwords,
  Abilities, REST Console.
- **Tools:** Workbench Options, Practice Site, Watches.
- **Window:** Switch to Editor, and the editor's documents.
- **Help:** Part D.

The editor keeps File > WordPress for writing (unchanged), and Tools >
WordPress becomes a short list of doors into the Workbench at the right
node, as the GitHub PRD does for the GitHub menu (GitHub PRD 6). Every
existing command id stays registered and opens its new home.

### 7. Context menus

GitHub PRD 5's rules: the default first, only rows for the selected row
type, about eight then More, Properties last.

| Row | Context menu |
|---|---|
| Post, page, custom item | Open in Editor; Publish or Update; Schedule...; Preview on Site; Duplicate; Copy to Site...; Move to Trash; More; Properties |
| Media item | Listen or Watch, or View; Edit Alt Text; Insert in the Current Document; Set as Featured Image...; Replace File...; Copy Link; Move to Trash or Delete; More; Properties |
| Comment | Read with Its Post; Approve or Unapprove; Reply...; Spam; Move to Trash; Open the Post in the Editor; More; Properties |
| Category, tag, term | Show Its Posts; New Child...; Merge Into...; Delete...; Properties |
| Menu, menu item | Open the Menu; Add Item...; Move Up, Move Down, In, Out; Remove; Properties |
| User | Show Their Posts; Change Role...; Send Password Reset; Application Passwords; Remove... (with reassignment); Properties |
| Plugin, theme | Activate or Deactivate; Update; What Changed; Open Its Settings; Delete...; Properties |
| Form response | Open; Mark Read; Export...; Delete...; Properties |
| Order | Open as a Receipt; Change Status...; Refund... (tier 3); Add Note...; Properties |
| Update | What Changed; Update; Skip This Version; Properties |
| Problem (health, accessibility, link) | Explain; Fix...; Open the Page in the Editor; Ignore; Properties |

### 8. Properties: Alt+Enter on anything

GitHub PRD 15 applies whole: three routes to one command, every fact a
focusable labelled control, editable exactly when the capability allows,
read-only with the reason otherwise, OK, Cancel and Apply, Copy as Text,
several objects at once with Mixed values, the conflict check (here on
`modified_gmt`, which wordpress.md 2 found fetched and never compared),
verify after save, one sentence for what changed, and Undo. Appendix A lists
every object's pages.

The editor's File > WordPress > Properties (wordpress.md 5.5) and the
Workbench's sheet for the same post are the same sheet, so a field added once
appears in both.

### 9. Edit everything the site lets you edit

- **Every writable field** of every object, from its sheet; the menu rows
  open the sheet at the right page. No per-field keys (the GitHub PRD's rule,
  16.3): Alt+Enter, and the page.
- **Batch, the way wp-admin's Bulk Edit should have been:** select any rows,
  Alt+Enter, change status, author, categories added and removed, tags added
  and removed, comments on or off, pings, sticky, template, parent, format;
  the preview lists every item; sent through WordPress's batch endpoint
  (`/batch/v1`, 25 requests a call), with a result per item and retry.
- **Media in batch:** alt text, captions, descriptions, titles, attachments,
  across a selection, with AI suggestions offered (wordpress.md 6.8), never
  written without review.
- **Terms:** rename, change slug, parent and description, merge two terms
  (reassign every post, then delete the old one), convert a tag to a category
  and back.
- **Undo:** Undo WordPress Change reverses a change from Change History;
  for content, Previous Versions restores any revision; Trash restores
  anything trashed.

### 10. Filtering on every attribute

The four ways in of GitHub PRD 17.1 (filter box, Filter Builder, Filter menu,
Show Only and Hide on cells), writing one query. Here the query is the REST
API's own parameters, so every filter reaches the whole site, not just the
loaded rows:

- **Posts, pages and custom types:** search, status, author (and not
  author), categories and tags (any of, all of, none of), every custom
  taxonomy, before and after (published), modified before and after, sticky,
  parent, menu order, slug, format, and ordering by date, modified, title,
  author, relevance, menu order.
- **Media:** type, file type, attached or not, parent, author, date, has alt
  text (locally), size (locally).
- **Comments:** status, post, author, author email, parent, type, date
  ranges, search.
- **Users:** role, capability, has published posts, search, registered date.
- **Plugins and themes:** status, has update, auto-updates on.
- **Form responses and orders:** every field of the form; order status,
  customer, total, date, product.
- **Local filtering** for anything the API cannot query, said honestly in the
  status bar, with Load All (GitHub PRD 17.3).
- **Across sites:** the same filter can run on every connected site at once
  from Search and Needs My Attention.

### 11. Permissions

- **Know before offering:** roles and capabilities from
  `users/me?context=edit` (wordpress.md 9.2), on connect and daily, per site.
  Every action and field declares the capability it needs (`edit_posts`,
  `publish_pages`, `moderate_comments`, `manage_categories`, `upload_files`,
  `edit_theme_options`, `activate_plugins`, `update_plugins`, `list_users`,
  `promote_users`, `manage_options`, and the rest), and the action table
  greys with the reason: "Publishing pages needs the Editor role or higher.
  You are an Author on Community Radio."
- **Managing people:** add users (with role and a welcome email choice),
  change roles, send a password reset, remove a user with their content
  reassigned to someone else (the preview names how many posts move), and on
  a network, add a site's users and super admins.
- **Roles, read-only and explained:** each role's capabilities are listed
  in plain words on the Users node's Properties. WordPress's REST API cannot
  change a role's capabilities, so the sheet says so, and points to the
  site's role plugin if one is installed and offers routes (section 12).
- **Application passwords:** your own on each site (create with a name,
  revoke, see last used and from where), and other users' where you may.
- **Content access:** visibility (public, private, password protected, with
  the password write-only), comments and pings per post, registration
  (anyone can register, default role), discussion settings (moderation,
  approval rules, blocklists).
- **Workbench access per site:** Read Only, Organize, Full, and Safe Mode as
  Read Only (GitHub PRD 18.4).
- **Tiers and guards:** GitHub PRD 18.4's four tiers, with Trash as tier 1
  (undoable) and Delete Permanently as tier 3; no removing your own
  Administrator role or the last Administrator; deactivating the plugin that
  provides QUILL's own connection (for example a forms or REST plugin) warns
  first.
- **View As Role:** the Workbench greys and explains everything as an
  Author, Editor, Contributor, Subscriber or any custom role would meet it.

### 12. Coverage: every route, discovered

wordpress.md 9.17 audits routes by hand. Here that becomes live and gated:

- **Each site describes itself.** The REST index (`/wp-json/`) lists every
  namespace and route the site offers, and each route's methods and argument
  schema; `OPTIONS` on a route returns its full schema.
- **Known routes** map to the tree, sheets and actions built for them.
- **Unknown routes become usable anyway.** For a custom post type or
  taxonomy registered with REST support, the Workbench builds its node,
  list columns, filters (from its query arguments) and Properties sheet (from
  its schema: strings as text boxes, enums as lists, booleans as check boxes,
  dates as date boxes, integers as numbers, references as pickers). For any
  other route family, "More from this site" lists it by namespace with a
  sheet for each readable item.
- **The coverage gate** (shared `coverage.py`) runs against the test site's
  recorded index: every route is `covered`, `schema_built`, `planned`,
  `wp_admin_only` (with the screen it opens) or `out_of_scope`, and a new route
  is `missing` until classified.
- **The Abilities API** (WordPress 6.9 and later): the site's registered
  abilities appear under Abilities as commands, each with its input schema as
  a sheet, its permission check, and a preview; plugins that register
  abilities get commands here with no QUILL release.

### 12a. Every combination: how a route becomes filters, fields and actions

Jeff, 2026-11-09: embed the API and "match everything to all combinations".
Appendix D lists every route on the test site with every argument and its
allowed values. The Workbench turns them into the interface by rule, so
nothing a route accepts is left unreachable:

| In the route | Becomes |
|---|---|
| A GET collection route | a node and its list |
| Each GET argument | a Filter Builder attribute, with an operator chosen by its type: text (contains), integer and id lists (is any of, is none of), dates (before, after, between, in the last n days), booleans (is, is not) |
| An argument's `enum` | the attribute's values, every one offered: for posts, all twenty-odd statuses including the plugins' own, every `orderby`, every `format`, both `tax_relation` choices, every `search_columns` choice |
| A pair like `categories` and `categories_exclude` | one attribute with "any of" and "none of" |
| `tax_relation` | the Filter Builder's "all of these" or "any of these" across taxonomy rows |
| `orderby` and `order` | the Sort choice, every value |
| The item schema's properties | the Properties sheet's fields, by type: strings as text boxes, `enum` as lists, booleans as check boxes, dates as date boxes, integers and numbers as number boxes, ids of other objects as pickers, `readonly` as read-only fields |
| Nested `object` and `array` properties | a sub-page or a list with Insert, Delete and Alt+Up and Alt+Down for order (the gap in today's custom fields) |
| `meta` in the schema | the Custom Fields page, every registered key, including lists and objects |
| POST on a collection | New, here (Ctrl+N), with the create schema as the sheet |
| POST, PUT or PATCH on an item | the sheet's OK and Apply |
| DELETE | Delete (Trash where the type has Trash) and Delete Permanently (`force=true`, tier 3) |
| Custom action routes (for example `/autosaves`, `/revisions/{id}`, a plugin's `/sync`) | an Item menu row, its arguments as a small sheet, with a preview |
| The capability WordPress checks | the action table's requirement, and the reason a row is greyed |

**The combination test.** For each route in the recorded index, a generated
test asserts that every GET argument has a Filter Builder attribute, every
enum value is offered, every writable schema property has a sheet field, and
every method has an action. A route that fails is `missing` in the coverage
gate. So when WordPress or a plugin adds an argument, the gate names it.

**Writing combinations.** Batch edits (section 9) combine with filters: any
filter's result can be selected and changed together, and the preview says
how many items each change touches. Changes that conflict (setting a status
some selected items cannot have, such as `future` without a date) are named
in the preview rather than failing halfway.

### 12b. Making your own post types, taxonomies and fields

**Why it needs something on the site.** WordPress has no REST route that
creates a post type, a taxonomy or a custom field. Each is registered by
PHP code that runs on every page load (`register_post_type`,
`register_taxonomy`, `register_meta`), so a desktop app cannot create one
on its own. Something on the site has to keep the definition and register
it. There are two ways, and the Workbench supports both.

**Way 1: a plugin the site already has.**
- **Advanced Custom Fields** (free since 6.1) creates post types, taxonomies
  and field groups in wp-admin, and can show fields in REST. The Workbench
  reads and edits the fields it shows (WP-R-034). Whether ACF lets field
  groups themselves be created over REST is to verify; if not, Create Field
  Group opens the right wp-admin screen.
- **Pods, Meta Box and Custom Post Type UI** the same way, each to the level
  its API reaches (Pods has REST routes of its own, to verify).

**Way 2: QUILL Site Types, a small plugin of our own** (or a module of
QAF, decision 12):
- **REST routes to define things:** post types (name, labels, slug,
  hierarchical, supports, archive, menu position, icon, which taxonomies),
  taxonomies (name, labels, hierarchical, which types), and field groups
  (which types, terms, users or comments they attach to, and their fields).
  Each definition is stored as data and registered on `init` with
  `show_in_rest`, so it appears in the REST index and the Workbench
  discovers it like anything else (section 12).
- **Field types, ours:** a field has a JSON schema type (string, number,
  integer, boolean, array, object), which is all WordPress stores, plus a
  field kind that says how to edit and check it. The kinds: text, long
  text, rich text, number, money, date, time, date and time, true or false,
  choice, several choices, email, address, phone, link, colour (named, with
  its contrast), picture (with required alt text), file, gallery, related
  item (any type), related term, related user, repeater (a list of groups),
  group, location, and accessible-by-default kinds no field plugin has: a
  transcript for audio, captions for video, a long description for a
  picture, and a language-marked text. Each kind has its accessible control
  in the Properties sheet and its check (an email must be one; a picture
  must have alt text).
- **Your own kinds:** a site can add a kind by giving its schema, its label
  and its check rules, and the Workbench builds its control from the schema
  (section 12a), so a new kind needs no QUILL release.
- **Nothing locked in:** Export as Code writes the definitions as a PHP file
  (the `register_*` calls) or as `theme.json`-style JSON for a theme, so a
  site can stop using the plugin and keep its types and fields.
- **Permissions:** defining types and fields needs `manage_options`; filling
  them in follows each type's own capabilities (section 11).
- **In the Workbench:** Sites > site > Content Model lists the site's post
  types, taxonomies and field groups, whoever registered them (core, a
  theme, a plugin, or QUILL Site Types). Ctrl+N makes a new one, Alt+Enter
  opens its sheet: General, Labels, Supports, Taxonomies, Fields (a list with
  Insert, Delete, and Alt+Up and Alt+Down for order, each field's own sheet
  for its kind, label, help, required, default and choices), Permissions,
  and Export. The ones a plugin or theme registered are read-only, and say
  which plugin owns them.
- **Templates with them:** a new type can come with a starter page shape and
  a QAF form for collecting entries of that type (an event submission form
  that creates an Event), tying types, fields and forms together.

### 13. Templates and patterns

- **Patterns:** the site's synced and unsynced patterns as a list; New
  Pattern from the current selection in the editor; Properties for title,
  categories, sync status, and where it is used.
- **Starter pages:** a saved page shape (blocks, template, categories) that
  New Page can start from, kept per site or shared across sites.
- **Templates and template parts** (block themes): listed, opened in the
  editor as blocks, reset to the theme's original.
- **Form templates:** the Forms engine's (QAF) templates and starters, as for
  GitHub issue forms (GitHub PRD 21).

### 13a. Spam: on the site, and in the Workbench

Spam is caught on the site, by the site, because QUILL runs on the writer's
computer and is not there when a visitor presses Submit. The Workbench is
where a person sees what was caught, why, and puts right what was caught by
mistake. Two kinds: comments (WordPress core) and form entries (QAF and the
other form plugins of 13b).

#### 13a.1 What QAF does on the front end today

Verified in `S:\code\qaf` at `cbc7fef` (2026-11-07):

- **Honeypot,** on by default (`includes/security/class-qaf-honeypot.php`).
- **Rate limiting,** per address and per form, on by default
  (`class-qaf-rate-limiter.php`).
- **CAPTCHA,** off by default, with five providers: reCAPTCHA v2, reCAPTCHA
  v3, hCaptcha, Cloudflare Turnstile, and a maths question
  (`class-qaf-captcha.php`).
- **An entry status of `spam`** in its table (`active`, `trash`, `spam`,
  `pending`, `approved`, `rejected`), readable and settable through its REST
  API (`/entries`, `/entries/{id}` with `status`).

What it does not do yet: check what was written (links, known spam phrases,
known spam senders), keep a reason or score with a spam entry, or work with
the spam services and security plugins a site already has.

#### 13a.2 The rule that matters most: never punish people for how they use a computer

Many bot detectors watch mouse movement, typing rhythm and how long a page
was open. Keyboard users, screen-reader users, switch users and people
dictating all look "unusual" to those signals, and they are exactly who QUILL
is for. So, for QAF:

1. **Prefer checks that look at what was sent, not how it was typed:** the
   honeypot, a minimum time to fill (generous: never under three seconds),
   rate limits, link counts, the site's own WordPress blocklist
   (`disallowed_keys`), and a content check by a spam service (13a.3).
2. **Prefer challenges a person never sees:** Turnstile in its managed or
   invisible mode, reCAPTCHA v3, or proof-of-work (ALTCHA, open source, solved
   by the browser in the background). A visible puzzle is the last resort, and
   always offers an accessible alternative.
3. **Hold, never drop.** Anything a check doubts is kept with status `spam`
   and the reason, not thrown away, and the visitor sees the same polite
   confirmation either way, so a real person caught by mistake loses nothing:
   someone reviews it (13a.5) and it comes back.
4. **Say why.** Every held entry or comment keeps which check flagged it and
   its score: "Held: 6 links (the limit is 3)", "Held: OOPSpam score 5 of 6",
   "Held: filled in 1.2 seconds".

#### 13a.3 Working with the spam tools a site already has

QAF gains one spam-check interface with providers, each optional, each shown
in QAF's settings and in the Workbench's Spam page (13a.5):

| Provider | What it checks | How QAF uses it | Status |
|---|---|---|---|
| Honeypot, time to fill, rate limit, link count | how the form was sent | built in | honeypot and rate limit exist; time and links to add |
| WordPress's own blocklist (`disallowed_keys`) and moderation keys | words, addresses and emails the site already blocks | read the site's Discussion settings, so one list protects comments and forms | to add |
| Akismet | content, sender and address, against Automattic's network | if Akismet is active with a key, QAF sends the entry through Akismet's comment-check as a contact form, and reports Spam and Not Spam back (submit-spam, submit-ham) so it learns | to add |
| OOPSpam | content, sender, address, country and language, with a score from 0 to 6 | if the OOPSpam plugin is active, QAF uses its saved API key and threshold; otherwise a key in QAF's settings. Spam and Not Spam reported back | to add; verify the plugin's integration hooks and report endpoint during the phase |
| Shield Security | bot signals (its silentCAPTCHA), and the site's blocked addresses | if Shield is active, QAF asks it whether the visitor is a bot before saving, and respects its IP blocks; because silentCAPTCHA is behaviour-based, its answer holds an entry for review rather than rejecting it (rule 3) | to add; verify which public functions or filters Shield offers to third-party forms, and ask Shield's developers to list QAF among its supported forms |
| CleanTalk | content and sender, through its cloud service | as Akismet, if active | to verify |
| Turnstile, reCAPTCHA v2 and v3, hCaptcha, maths | challenges | exist today | exist |
| ALTCHA | proof of work, no tracking, no puzzle | built in, self-hosted | to add |

Two more things QAF offers, so any security plugin can join in without QAF
knowing about it: a `qaf_spam_check` filter that providers add to, and a
`qaf_entry_marked` action fired on Spam and Not Spam, so a plugin can learn
from the person's decision.

Privacy, which matters for a forms plugin: any provider that sends content
off the site (Akismet, OOPSpam, CleanTalk) is off until the site owner turns
it on, says what it sends, and is listed in QAF's privacy text for the
site's privacy policy.

#### 13a.4 Comments

WordPress core already gives comments the statuses Waiting, Approved, Spam
and Trash, and Akismet or Shield or OOPSpam decide on the site. The
Workbench (wordpress.md 9.8, and Appendix A here) reads the status and,
where the plugin stores it, the reason (Akismet's history, for example), and
Spam and Not Spam go back through the REST API so the plugin learns.

#### 13a.5 Spam in the Workbench

- **Needs My Attention > Held as Spam (n),** across every site: comments and
  form entries the site doubted, newest first, each row reading "Contact
  form, Community Radio, held: 6 links, 2 hours ago".
- **Enter reads it in full;** Alt+Enter shows its Properties, including the
  check, the score and the sender's details the site keeps.
- **Not Spam** (Ctrl+Shift+A, the same key that approves a comment) restores it to the
  form's entries or the comment queue, tells the provider, and offers to
  allow that sender from now on. **Spam** confirms it and tells the provider.
  **Delete** moves it to Trash; Empty Spam deletes them all permanently
  (tier 3).
- **Batch:** select many, then Not Spam or Spam, with the preview.
- **The Spam page** of each site's Properties and of each form: which checks
  are on, each provider's state ("OOPSpam: on, threshold 3, 1,204 checks
  left this month"), the honeypot, time and link limits, and the blocklist,
  editable with `manage_options` (for site-wide) or the form's editing
  capability (for one form).
- **A weekly sentence,** if wanted, as a Watch: "This week on Community Radio:
  212 spam held, 3 released by you, nothing missed."

#### 13a.6 Text challenges: accessible, and as strong as a text challenge can be

A text challenge (a question in words, answered in words) is the one kind of
CAPTCHA that works the same by ear, by braille, by switch and by voice. QAF's
maths question is the start. The honest limit first: any text a screen reader
can read, an AI model can read and answer, so no text challenge stops a
determined bot. What it does well is stop the large majority of form spam,
which comes from cheap scripts, and cost the rest time and money. So it is
built as one layer that appears only when it is needed, never as the gate.

**When it appears: risk first, question second.**
- The quiet checks run first (13a.2): honeypot, time to fill, rate limit,
  proof of work, the content check. Most people never see a question.
- A question is asked only when those checks are unsure. When they are sure
  it is spam, the entry is held without asking anything.
- A site can choose Always Ask for a form under attack, and Never Ask.

**What the questions are like.** Answerable by anyone who can use the form,
in any language the site offers, without trivia, arithmetic or knowledge of
the site:
- **Everyday sense:** "Which is colder, snow or soup?"
- **Following an instruction about the question itself:** "Type the second
  word of this sentence."
- **Choosing from a short list,** read in full: "Which of these is an animal:
  chair, horse, window?" (also as radio buttons, for switch and voice users).
- **Ordering:** "Put these in order, smallest first: town, city, house."
- Maths only as an option, because numbers are a barrier for people with
  dyscalculia.

**What makes it hard to beat cheaply:**
- **Made fresh each time** from templates and word lists on the server
  (thousands of combinations per language), never one fixed question a bot
  can learn.
- **The answer never reaches the page.** The server keeps it with a one-time
  challenge id that expires in 15 minutes and works once.
- **Bound to the visit:** the challenge is tied to the form, the session and
  the proof-of-work token, so answers cannot be farmed and replayed.
- **Each failure costs the bot more:** more proof of work for the next try,
  and a tighter rate limit, while a person sees the same gentle question.
- **The site's own words:** a site can add questions in its own voice, and the
  bank grows with them.
- **No tricks that harm people:** no hidden "if you are a bot, type X" text,
  because screen readers read hidden text too and would trip real users.

**Generous to people:**
- Answers are matched loosely: capitals, spaces, punctuation, numbers as
  digits or words, common misspellings, and any of several right answers.
- **No lockout.** A wrong answer gets a new question with the same patience,
  and after three tries the form offers Send Anyway: "A person will read it
  before it is published or answered." The entry is held (13a.5), never lost.
- **It is a form field like any other:** a label, the question as its
  description, the error next to the field and announced, no time limit, and
  F1 help in QUILL's fill window.
- This follows the intent of WCAG 2.2's Accessible Authentication criterion
  (3.3.8), which counts puzzles as cognitive tests that need an alternative,
  and the W3C's note on the inaccessibility of CAPTCHA.

**In the Workbench:** the Spam page (13a.5) shows how often the question was
asked, passed, failed and sent anyway, and lets a site edit its own question
bank, choose the kinds, and preview questions in each language. A sentence
sums it up: "Asked 40 times this week; 31 passed, 2 sent anyway, 7 gave up."

### 13b. Form plugins: QAF first, and the ones sites already use

QAF (QUILL Accessible Forms, `S:\code\qaf`) is the family's own forms plugin
and is first-class everywhere (wordpress.md 17a). But most sites already run
another one, with years of entries. The Workbench meets them where they are.

#### 13b.1 What every form plugin gets

For each plugin the site has, found by its REST namespace (section 12):

- **A node:** Sites > site > Forms > by plugin, each form a child node with
  its entries.
- **Entries as a list** with their fields as columns, filterable on every
  field, exportable, with an entry's Properties showing every answer, its
  date, its status (including spam), and notes.
- **Spam and Not Spam** where the plugin has the status.
- **Bring it into QAF** (Forms > Import from...): the form's fields converted
  into a QAF form with a preview of anything that does not map, and,
  optionally, its entries copied across, so a site can move to an accessible
  form without losing history.

#### 13b.2 What each plugin offers

The level each can reach depends on what the plugin exposes. Each row's REST
claims are verified against the plugin's current documentation and a live
install on the test site before its phase starts.

| Plugin | Forms | Entries | Spam status | Notes |
|---|---|---|---|---|
| QAF | read, write, build (BFL), check, publish | read, status, export | yes | first-class, both editors (wordpress.md 17a) |
| Gravity Forms | read, and write through its REST API v2 (`gf/v2`) | read, edit, status | yes | the fullest third-party API |
| Formidable Forms | read, through its REST API add-on | read | yes | needs the add-on |
| Fluent Forms | read | read | yes | REST coverage to verify |
| WPForms | read where its API allows | Pro stores entries; REST access to verify | Pro | may need wp-admin for some actions |
| Contact Form 7 | read its forms (`contact-form-7/v1`) | none of its own; Flamingo stores them, with no REST access | Flamingo | entries "open in wp-admin" until Flamingo exposes them |
| Ninja Forms | to verify | to verify | yes | |
| Jetpack Forms | the forms in blocks | responses as its feedback post type, where shown in REST | yes | |
| Forminator | to verify | to verify | yes | |
| Anything else | schema-built (section 12) | schema-built | if exposed | |

#### 13b.3 Moving to QAF, the accessible way

- **Import** from Gravity Forms (its form JSON), Contact Form 7 (its form
  tags), WPForms and Formidable (their exports), and any plugin's form as
  read through the API, into QAF's model, joining the existing SurveyJS and
  XLSForm imports (`quill/core/forms/interop_*`).
- **Check** the imported form with the Forms accessibility checks before it
  replaces anything: labels, required fields, error messages, groups.
- **Swap in place:** replace the old form's block or shortcode on every page
  that uses it with the QAF form, with the preview listing each page.
- **Keep the history:** copy old entries into QAF's entries, marked with
  their source, or leave them where they are and keep reading them through
  13b.1.

### 14. The editor side

- File > WordPress keeps writing (wordpress.md 12) unchanged.
- Tools > WordPress becomes doors: Open WordPress Workbench, Needs My
  Attention, Comments Waiting, Media Library, This Site's Settings, and the
  existing command ids open their nodes.
- **This Post in the Workbench** (from File > WordPress) selects the open
  document's post in the tree.
- The Media Library's Insert stays one step from the editor: Insert Picture
  from the Media Library opens the Workbench on Media in a picking mode, and
  Enter inserts.

### 15. Thinking boldly

#### 15.1 A practice site on your own computer

WordPress Playground runs a complete WordPress in WebAssembly, with no
server. QUILL already ships Node in the shared runtime (for the language
servers), so Help > Practice Site starts a Playground site locally (through
its command-line tool, version-pinned and bundled, as every other component
is), signs in, connects it as "Practice Site", and offers starter content,
so anyone can learn publishing, moderation, plugins and settings with
nothing at stake and nothing on the internet. Reset Practice Site puts it
back. It is also the test bed for Part F's integration tests.

#### 15.2 Site to site

- **Copy to Site...** on any posts, pages, media, menus, categories, forms or
  patterns: to another connected site, with pictures uploaded, links
  rewritten to the target's addresses, terms matched by name or created,
  authors mapped, and the preview listing every create and replace.
- **Compare Sites:** what differs between staging and live, by object, read
  as a list.
- **A local snapshot:** Site > Take a Snapshot saves every post, page, term,
  menu and setting (not media files, unless asked) to this computer, so a
  bad batch can be put back even after revisions are trimmed.

#### 15.3 The content calendar

Calendar in the tree lists each day as a node ("Tuesday 12 November: 2
scheduled, 1 published"), across every site, filterable by site, author and
type. Moving a post to another day is changing its date on the sheet; the
preview says the new time in the site's own time zone and yours.

#### 15.4 The editorial queue

Pending Review is a real workflow: assign a reviewer (a note and a
Watch), leave notes on a draft (wordpress.md's notes), approve and schedule
in one step, send back with a note. A Contributor sees what is theirs and
where it is in the queue.

#### 15.5 Read the site like a book

Read Site as Document builds the whole site (or a category, or a menu's
pages) as one document in the editor: headings per page, in menu order,
with each page's address, then exports to Word, EPUB or DAISY. Useful for
proofreading a whole site by ear, for an accessibility review, and for an
offline archive.

#### 15.6 Health and accessibility as places

Site Health, Accessibility and Broken Links are nodes with one row per
problem, each with Explain, Fix... (where QUILL can: alt text, empty links,
heading order, colour contrast in global styles, a missing page title) and
Open the Page in the Editor. Fixing in bulk (wordpress.md 9.5) is a batch
with its preview. A weekly Watch can run Check the Whole Site and say only
what changed.

#### 15.7 Watches

GitHub PRD 22.5, for sites: a new comment on this post, a form response, an
order, an update available, a scheduled post going live, the site not
answering (checked gently, at most every 15 minutes, with consent), a Site
Health status change.

#### 15.8 Plain language in, a previewed batch out

"Move every draft older than a year to Trash." "Give every post in Events
the tag 2026." "Which pictures have no alt text on the home page?" Through
the Command Key work, shown in the batch preview, nothing sent before Enter.

#### 15.9 The REST Console

Tools > REST Console: any route on the current site, with completion from the
site's own index and schema, the capability it needs, a preview for writes,
and Change History; the answer as a tree. Saved requests can become menu rows
with keys. It is the guarantee behind "anything WordPress can do".

#### 15.10 Lists in and out

Export any list (posts, comments, users, responses, orders) as CSV, Excel,
Markdown or a QUILL table; import posts or pages from a spreadsheet with a
preview; import a folder of Markdown or Word documents as drafts.

#### 15.11 The third sweep: what running a real site also involves

Jeff, 2026-11-09: "anything else missing?" Each row gets a node or a sheet
page, and, where a plugin provides it, is reached through that plugin's REST
namespace when the site has one (section 12). Every plugin's API is marked
**to verify** until it has been checked against its documentation and a live
install on the test site; where no API exists, the row says what wp-admin
screen it opens, so nothing is a dead end.

| Area | What people need | Home | Through |
|---|---|---|---|
| Redirects | a redirect made automatically when a slug or address changes; a list of redirects to add, edit and test; the 404 log, so broken incoming links are found | Sites > site > Redirects; post Properties > Address | Redirection (`redirection/v1`), Yoast Premium, Rank Math; to verify |
| Backups | when the last backup ran, whether it worked, Back Up Now, restore points | Needs My Attention > Site Health; Sites > site > Backups | Jetpack Backup (`jetpack/v4`), UpdraftPlus and host tools; to verify; restore opens the plugin's screen |
| Security | failed sign-ins, blocked addresses, file changes, two-factor status of each user, plugin vulnerability alerts | Needs My Attention > Security; Users > each user's sheet > Security | Shield Security, Wordfence, Solid Security, Patchstack; to verify; vulnerability data for installed plugin versions from a public database only with consent |
| Abandoned plugins | a plugin not updated in two years, or closed on WordPress.org | Plugins, with a "Last updated" column and a Watch | the WordPress.org plugin directory API, with consent (an egress row) |
| Installing plugins | search WordPress.org and install, with ratings, active installs, last update and the accessibility of its admin screens where known | Plugins > Add New | core `wp/v2/plugins` installs by slug; search through the WordPress.org API with consent |
| Caching and speed | purge the cache after an update, per page or whole site; image optimization status; page speed as numbers, in words | Item > Clear Cache; Sites > site > Performance | WP Rocket, LiteSpeed Cache, W3 Total Cache, Jetpack Boost; to verify |
| Multilingual sites | each post's translations linked side by side, missing translations as a list, the language of each page, the language switcher | post Properties > Translations; Needs My Attention > Missing Translations | Polylang, WPML, TranslatePress; to verify; Mark Language (wordpress.md 12) already marks passages |
| Privacy requests | personal data export and erase requests, their status, Confirm and Complete | Needs My Attention > Privacy Requests | core keeps these as requests (their statuses are in the index); if no REST route exists on the site, they open wp-admin's Privacy screens |
| Consent and cookies | which consent tool runs, its categories and texts, checked for accessibility | Settings > Privacy | consent plugins; to verify |
| Email delivery | whether the site's email works, the mail log, Send Test Email | Site Health; Settings > Email | WP Mail SMTP, FluentSMTP, Post SMTP; to verify |
| Newsletters and subscribers | subscriber lists, new subscribers, send a post as a newsletter, open counts | Sites > site > Subscribers | Jetpack Newsletter, MailPoet, The Newsletter Plugin; to verify |
| Memberships | members, levels, expiry, payments, renewals due | Sites > site > Members; Needs My Attention > Renewals | Paid Memberships Pro (BITS runs it), MemberPress, Restrict Content Pro; to verify |
| Courses | courses, lessons, students, progress, quizzes | Sites > site > Courses | LearnDash, LifterLMS, Tutor LMS, Sensei; to verify |
| Event tickets and RSVPs | attendees, check-in as a list, capacity, refunds | Events > each event > Attendees | Event Tickets (The Events Calendar's family), WooCommerce Bookings; to verify |
| Shop, the rest | low stock as a Watch, subscriptions and their renewals, bookings, product reviews (wordpress.md 9.18 lists reviews as missing) | Shop | `wc/v3`; extensions to verify |
| Stats | views and visitors by page and day, top referrers, search terms, as tables and sentences | Sites > site > Stats | Jetpack Stats, Site Kit by Google, Independent Analytics; to verify |
| Search and sitemaps | the sitemap's contents, which pages ask not to be indexed, Search Engine Visibility in plain words | Settings > Reading; Sites > site > SEO | core `wp-sitemap.xml`, Yoast `yoast/v1` (in the index) |
| Social sharing | share a post when it publishes, to which accounts, with what text and alt text | post Properties > Sharing | Jetpack Social; to verify |
| Scheduled tasks | what WordPress plans to run and when, and anything overdue | Site Health > Scheduled Tasks | Site Health's information; WP Crontrol if installed; to verify |
| Someone else is editing | know before opening that another person has a post open, and take over only on purpose | the post's row and Properties | WordPress's post lock is held through its heartbeat, not REST; the Workbench checks `modified` and the lock where exposed, and says what it knows |
| Content audit | pages nobody links to, pages not updated in a year, duplicate titles, very long or very short pages, reading level, headings that skip a level | Needs My Attention > Content Audit; a report as a QUILL table | built from the content QUILL already reads, with Document Statistics' measures |
| Media housekeeping | unused media, duplicate files, very large files, video without captions, audio without transcripts | Media > Housekeeping | built from Media and its Usage page (Appendix A) |
| Moving in | importing from Blogger, Medium, Substack, Squarespace and WordPress export files | File > Import into Site... | the export file read on this computer, sent as posts and media over REST, with a preview |
| Moving out and archiving | a complete export (posts, pages, media list, terms, menus, settings) as files, and a static copy of the site for an archive | Site > Export... | REST reads; the standard export file is made on this computer |
| SSL and the address | the certificate's expiry date, the site answering on HTTPS, the address WordPress thinks it has | Site Health; Site Properties > Connection | read from the connection itself; a Watch at 30 days before expiry |
| Users, the rest | invite in bulk from a spreadsheet, sign a user out everywhere, see who has never signed in | People > Users | core `wp/v2/users`; sessions where exposed; to verify |
| Roles, edited | change what a role may do, and make new roles | People > Roles | only through a role plugin's routes (Members, User Role Editor); to verify; core REST cannot (section 11) |
| Collaboration | notes on drafts, assigning a draft to someone, and, on WordPress versions that add live collaboration, who is in a post now | Pending Review; post Properties > Notes | core notes (`block_notes.py` exists); live collaboration routes when WordPress ships them |
| Asking about the site | "Which pages mention our old address?", "Summarize this week's comments" | Item > Ask; Site > Ask About This Site | the family's Ask AI, over content QUILL already reads, never sending a site's private content without saying so |

#### 15.12 Across sites, and across the whole site: every kind of thing, by name

Jeff, 2026-11-09, on the GitHub PRD's section 22.11 ("handle all tags and
labels in their own places and not tied to a specific thing"): "this is also
true of WordPress where applicable." It is, in two directions.

**Within one site: things in their own places, not inside a post.** A tag or
category is edited today from a post's Properties or from Categories and
Tags. Each kind below gets its own node with every value it has, and its
sheet works on the value itself, wherever it is used:

| Kind | A row reads | What you can do |
|---|---|---|
| Tags, categories, every custom taxonomy's terms | "accessibility: 48 posts, 3 pages, 2 events" | rename and change slug (with a redirect for the archive address, 15.11); merge into another term; split (move some items to a new term); convert between taxonomies (a tag into a category); change parent; set term meta; delete with the items reassigned; list every item that uses it, of every type |
| Custom field values | "Venue: Main Hall, on 31 events" | find every item with a value; change it everywhere; find items missing a required field |
| Authors | "Sam: 120 posts, 4 drafts" | reassign many items to another author; find items by a former user |
| Pictures and files | "logo.png: used on 14 pages, in 2 menus, the site icon" | replace everywhere it is used; find where it is used before deleting (Media > Usage) |
| Patterns and template parts | "Footer: used by 3 templates" | where it is used; update all; detach copies |
| Links | "https://old.example.org: linked from 22 pages" | change every link at once (Site-wide Find and Replace, focused on links); find broken ones (15.11) |
| Shortcodes and blocks | "[gallery]: on 9 pages", "Columns block: on 40 pages" | find every use; convert a shortcode to its block; find blocks from a plugin about to be removed |
| Forms | "Contact: on 5 pages" | where it is used; replace with another form everywhere (13b.3) |

**Across sites: the same name on many sites.** A new top-level branch,
**Across Sites** (Ctrl+0, as in the GitHub Workbench), over every connected
site or a **Site Set** ("Client sites", "Family sites"):

| Kind | A row reads | What you can do everywhere at once |
|---|---|---|
| Tags, categories, custom terms | "Events: on 4 sites, 2 slugs" | align names, slugs and descriptions; create on the sites missing it; merge everywhere |
| Plugins | "Yoast SEO: on 9 sites, 3 versions, 2 inactive" | update everywhere; activate or deactivate; turn auto-updates on; remove everywhere; install on the sites missing it |
| Themes | "Twenty Twenty-Five: active on 3 sites" | update everywhere; compare global styles |
| Users | "Sam: Editor on 2 sites, Author on 1" | the access matrix from the person's side; change a role everywhere; remove everywhere with reassignment on each site |
| Settings | "Discussion: comment approval differs on 2 of 6 sites" | make any setting the same (time zone, permalinks, discussion rules, search visibility, privacy page); see where they drift |
| Menus and navigation | "Footer menu: on 5 sites, 3 versions" | compare and copy one to the others (section 15.2) |
| Patterns, starter pages, forms, content types | by name | copy one to every site; see where versions differ |
| Pages with a role | "Privacy policy: 6 sites, last updated from 2 to 30 months ago" | find the stale ones; update from one |
| Redirects, application passwords, spam senders | by address or name | block a spam sender on every site at once; revoke one application password everywhere |
| Health, backups, security, updates | by site | the Fleet view: every site in one list, read row by row ("Community Radio: health good, backed up today, 2 updates") |

**The same shape as GitHub's:** every row says where the copies differ, a
Variants page lists each variant and the sites that have it, a Missing From
page lists the sites without it, and "make them the same" is a choice of
which variant wins, previewed site by site. On a multisite network, where
WordPress has a network-wide form (network plugins and themes, super
admins), the sheet offers Promote to Network.

**Kind by scope by operation:** every kind, over every scope (one site, a
Site Set, every site, a network), with every operation the kind allows, is a
row in the shared action table, so the combination test (section 12a) and
the coverage gate cover it.

### 16. QUILL Lite

The same window, the same commands, from the same tables, as wordpress.md
11 already requires. Nothing here is QUILL only.

### 17. Checking it with people

Before the Tools > WordPress windows retire, the same tasks with about five
people, screen-reader users and sighted, new to WordPress and experienced:
moderate a morning's comments; find every picture without alt text and fix
three; give a volunteer the Author role; schedule a week of posts; update
plugins on two sites; copy a page from staging to live. Count wrong turns
and time, against wp-admin.

## Part C: keys

The GitHub PRD's Part C applies, with the same families, so the two
Workbenches answer the keyboard the same way: Ctrl+1 to Ctrl+9 for the
top-level places (Needs My Attention, Sites on the current site, Calendar,
Search, Watches, Practice Site, Start Here), Ctrl+Shift+1 to Ctrl+Shift+9
for the parts of the current site (Posts, Pages, Media, Comments, Users,
Plugins, Appearance, Settings, Site Health), Alt+1 to Alt+9 to hear where you
are, F6 between panes, F5 refresh, Alt+Up to the parent, Enter for the
default, Alt+Enter for Properties, Shift+Enter to open on the site, Ctrl+N
new here, and typing always moves through the list. No key sets a single
property. Particular to WordPress:

| Key | Does |
|---|---|
| Enter on a post or page | Open in the editor |
| Ctrl+Enter on a post or page | Preview on the site, in your browser |
| Delete | Move to Trash (undoable); on a comment, Trash; on a user, Remove... with reassignment |
| Shift+Delete | Delete Permanently... (tier 3) |
| Ctrl+Shift+A | Approve the selected comments; on held spam (comments or form entries), Not Spam |
| Ctrl+Shift+U | Unapprove |
| Ctrl+Shift+S | Mark as spam (comments and form entries), and tell the spam provider |
| Ctrl+Shift+M | Reply to the selected comment |
| Ctrl+Shift+P | Publish or Update the selected posts (with the preview for more than one) |
| Ctrl+Z | Undo WordPress Change |

Each passes the GitHub PRD's C1 checks before adoption and lives in the
WordPress Workbench's `APP_KEYMAPS` entry.

## Part D: help, a huge part of this

Jeff, 2026-11-09: help "must be a huge huge part of both WordPress and GitHub
workbenches, it must be rich and delightful." Help is built once, in the
shared engine's help module, so everything in the GitHub PRD's Part D is
here too, word for word in behaviour:

- **The keys:** F1 in layers, Shift+F1 What Can I Do Here?, Alt+F1 What Is
  This?, Ctrl+F1 the guide chapter, Ctrl+Shift+F1 Search Help, F9 the last
  result again, Shift+F9 Explain That.
- **Help and Learning** in the tree: Start Here, Do Something, The Guide,
  Words, Keys, Tutorials, What Changed, Tips, Ask a Person (GitHub PRD D11).
- **Take Me There, Walk Me Through It and Do It** on every topic (D12).
- **Explain That and Why?** on every result and every automatic behaviour
  (D13).
- **Help that knows the situation,** key cards in print and braille, the guide
  as a book and a spoken tour, QUILLBert and QUILLBee, tips at the right
  moment, Ask a Person, the optional Ask How, one source, and the quality
  measures (D14 to D20).

What WordPress adds, because most people who run a WordPress site have never
been taught it:

### D1. WordPress explained, for people who were never shown

- **The glossary, generous:** post, page, slug, permalink, excerpt, featured
  image, block, pattern, synced pattern, template, template part, theme,
  block theme, classic theme, child theme, plugin, widget, sidebar, menu
  location, navigation block, taxonomy, category, tag, term, custom post type,
  custom field, sticky, revision, autosave, Trash, pending review, scheduled,
  draft, private, password protected, role, capability, application
  password, multisite, network, Site Health, REST API, ability, shortcode,
  oEmbed, cron, cache, redirect, 404, sitemap, every default role's name, and
  every term this PRD's sections introduce (Site Set, Content Model, Held as
  Spam). Each entry has an example from the person's own site when it can.
- **How WordPress thinks,** a short chapter at the top of the guide: a site is
  posts and pages made of blocks, dressed by a theme, extended by plugins,
  run by people with roles. Every later chapter points back to it.
- **Analogies from what people know:** a category is like a folder, a tag
  like a label in Outlook, a pattern like a Word building block, a template
  like a Word template, Trash like the Recycle Bin, a revision like a saved
  version in Word.

### D2. Every setting, explained as wp-admin never does

Each field on every Settings page has a help topic that says what it really
does, with this site's own example and the consequence of changing it:

- what "Discourage search engines from indexing this site" really does, and
  does not do;
- each Permalinks choice, showing what this site's newest post's address would
  become, and that a redirect is offered (15.11);
- each Discussion rule, with how many of this site's recent comments it would
  have held;
- Reading's "Your homepage displays", with this site's pages named;
- every plugin setting the Workbench can reach, with the plugin's own
  documentation linked.

### D3. Help where the stakes are

- **Before an update:** What Changed reads the plugin's or theme's changelog
  for the versions you skip, and says plainly whether it mentions security,
  breaking changes or database updates.
- **Before deleting or deactivating:** what depends on it (pages using a
  plugin's blocks or shortcodes, menus using a page, posts using a term), and
  how to undo it.
- **When something breaks:** a Site Health problem's help says what it means
  for visitors, what usually causes it, and the steps, with Take Me There to
  each.
- **Accessibility findings:** each one says who it affects and how ("A screen
  reader user hears 'image' and nothing else"), the WCAG success criterion,
  and Fix....
- **Spam and challenges:** why an entry was held, what the visitor saw, and
  what Not Spam will tell the spam service (13a).

### D4. Learning WordPress safely

- **Tutorials on the practice site** (15.1): your first post; moderating
  comments; the Media Library and alt text; menus; adding a user and choosing
  a role; updating plugins safely; building an accessible form; spam and
  challenges; custom types and fields; copying from staging to live; across
  sites with a Site Set.
- **Break It on Purpose:** a few practice-site lessons start broken (a
  missing alt text, a broken link, a plugin conflict, a wrong permalink) and
  teach the Workbench's way of finding and fixing each.
- **A first-week path** in Start Here for a new site owner: one short lesson
  a day, each finishing with something real on their own site.

### D5. Help for the people a site serves

- **Help text for your visitors:** QAF's forms, text challenges and Held as
  Spam confirmation (13a) come with plain, accessible visitor-facing words,
  editable per site, translated.
- **An accessibility statement** (wordpress.md 9.12) drafted from what the
  Workbench knows about the site, kept current by a Watch.

### D6. wp-admin pointers

Where something truly needs wp-admin, the help says which screen and why,
Open in wp-admin goes there, and the topic says what the screen will ask, so
nobody lands somewhere unfamiliar unprepared.

## Part E: requirements

- WP-R-001 Must: the Workbench is the shared engine's frame with a WordPress
  provider; nothing in the engine is GitHub-only or WordPress-only (3).
- WP-R-002 Must: writing stays in the editor; Enter on a post or page opens
  it there (2, 14).
- WP-R-002a Must: the status bar contract of the GitHub PRD's 3.2.1, with the
  WordPress cells of section 4 (4).
- WP-R-003 Must: Needs My Attention gathers every connected site (5).
- WP-R-004 Must: every shipped Tools > WordPress window's capability has a
  node, sheet or action (Appendix B), and its command id opens it (14).
- WP-R-005 Must: Alt+Enter Properties on every object in Appendix A,
  including discovered custom types (8, 12).
- WP-R-006 Must: conflict check on `modified_gmt` and verify after every
  save (8).
- WP-R-007 Must: batch edits through `/batch/v1` with a preview and a result
  per item (9).
- WP-R-008 Must: Delete means Trash where WordPress has Trash; permanent
  deletion is tier 3 (2, 11).
- WP-R-009 Must: filters use the REST API's parameters, with honest local
  filtering for the rest (10).
- WP-R-010 Must: every action and field declares its capability; greying
  carries the reason (11).
- WP-R-011 Must: user management with roles, reassignment on removal, and no
  self-lockout (11).
- WP-R-012 Must: application passwords listed, created and revoked (11).
- WP-R-013 Must: the route coverage gate against the test site's recorded
  index (12).
- WP-R-014 Must: schema-built nodes and sheets for custom post types and
  taxonomies (12).
- WP-R-015 Should: the Abilities API as commands (12).
- WP-R-016 Should: Copy to Site, Compare Sites, snapshots (15.2).
- WP-R-017 Should: the practice site on WordPress Playground (15.1).
- WP-R-018 Should: Calendar and the editorial queue (15.3, 15.4).
- WP-R-019 Should: Read Site as Document (15.5).
- WP-R-020 Should: Watches, the REST Console, lists in and out (15.7 to 15.10).
- WP-R-021 May: plain-language batches (15.8).
- WP-R-022 Must: the keys of Part C, passing the C1 checks.
- WP-R-023 Must: help per Part D, with GATE-WORDPRESS-HELP at zero.
- WP-R-046 Must: every help feature of the GitHub PRD's Part D (D1 to D20),
  from the shared help module, with nothing GitHub-only (Part D).
- WP-R-047 Must: the WordPress glossary, How WordPress Thinks, and every
  Settings field explained with the site's own example (D1, D2).
- WP-R-048 Must: help before updates, deletions and deactivations, and for
  every Site Health and accessibility finding (D3).
- WP-R-049 Should: practice-site tutorials, Break It on Purpose and the
  first-week path (D4).
- WP-R-050 Should: visitor-facing help text for forms and challenges (D5).
- WP-R-024 Must: QUILL Lite has the same window and commands (16).
- WP-R-025 Must: Held as Spam across sites, with the reason and score, Spam
  and Not Spam reported back to the provider, and batch (13a.5).
- WP-R-026 Must (QAF): spam is held with its reason, never dropped, and the
  visitor's confirmation is the same either way (13a.2).
- WP-R-027 Must (QAF): no check that judges a visitor by how they type or
  move the mouse may reject an entry; it may only hold it (13a.2).
- WP-R-028 Should (QAF): the spam-check interface with Akismet, OOPSpam,
  Shield Security, CleanTalk, the site's blocklist, time to fill, link count
  and ALTCHA as providers, plus the `qaf_spam_check` filter and
  `qaf_entry_marked` action (13a.3).
- WP-R-030 Must: the combination test of 12a over the recorded index: every
  GET argument a filter, every enum value offered, every writable property a
  field, every method an action.
- WP-R-031 Must: taxonomies and statuses discovered from `wp/v2/taxonomies`
  and `wp/v2/statuses`; `taxonomy_route()` reads `rest_base` instead of
  guessing (1a).
- WP-R-032 Must: custom post types get nodes, lists, New, batch and filters,
  not only Open (1a).
- WP-R-033 Must: custom fields of every type, including lists and objects,
  on posts, pages, custom types, terms, users and comments (1a, 12a).
- WP-R-034 Should: Advanced Custom Fields, Meta Box, Pods and CMB2 fields
  through their REST exposure (1a).
- WP-R-035 Must: QAF installed on the test site so the live run covers it
  (1a).
- WP-R-036 Must: Content Model lists every post type, taxonomy and field
  group on a site, with who registered each (12b).
- WP-R-037 Should: QUILL Site Types defines post types, taxonomies and field
  groups over REST, with the field kinds of 12b, site-defined kinds, and
  Export as Code (12b).
- WP-R-038 Should: ACF, Pods, Meta Box and Custom Post Type UI definitions
  read, and edited where their APIs allow (12b).
- WP-R-039 Should (QAF): text challenges asked only when the quiet checks are
  unsure, generated per visit with the answer kept on the server, loosely
  matched, never locking anyone out, with Send Anyway after three tries
  (13a.6).
- WP-R-040 Should: every row of 15.11 has a home, reached through its
  plugin's REST namespace where one exists and verified before its phase, or
  opening the named wp-admin screen where none does (15.11).
- WP-R-041 Must: a redirect is offered whenever a published item's address
  changes, on sites with a redirect plugin (15.11).
- WP-R-042 Should: the content audit and media housekeeping reports
  (15.11).
- WP-R-043 Must: terms, field values, authors, media, patterns, links,
  shortcodes and forms each have their own place, with the value itself as
  the object (15.12).
- WP-R-044 Must: Across Sites with Site Sets, variants, Missing From and
  every operation over every scope (15.12).
- WP-R-045 Should: the Fleet view across sites, and Promote to Network on
  multisite (15.12).
- WP-R-029 Should: entries, spam status and export for every form plugin in
  13b.2 at the level its API allows, and import into QAF (13b).

## Part F: quality

The GitHub PRD's Part F applies (accessibility, performance budgets,
reliability, security, privacy, testing), with these particulars:

- **Credentials:** application passwords stay in Windows Credential Manager
  (wordpress.md 4); HTTPS only (`_validate_endpoint_security`); post
  passwords and webhook secrets are write-only.
- **Network:** only the connected sites, WordPress.com's API for WordPress.com
  sites, and the practice site on this computer; each in the network egress
  audit. The site-answering Watch asks consent.
- **Performance:** `_fields` and `_embed` keep requests small; ETags where
  the site sends them; lists paged and lazy; the batch endpoint for writes.
- **Testing:** recorded responses for every provider call; the live run
  (`docs/qa/wordpress-live-run.py`) against the test site before a branch
  merges, as now; the practice site for local integration tests once
  Playground ships.
- **Bundling:** the Playground command-line tool is bundled and pinned, never
  downloaded at run time (the family's bundle-everything rule); its licence
  goes in the third-party notices.

### Dependencies (checked 2026-11-09)

**In the QUILL family's installers:**

- **Nothing new for the core Workbench.** It uses the shared engine and the
  WordPress modules already shipped (requests, the REST client, Credential
  Manager), and the GitHub PRD's F6 list covers the shared pieces (PyYAML,
  ruamel.yaml and jsonschema are not needed for WordPress itself; jsonschema
  helps check schema-built sheets if it is declared for GitHub).
- **WordPress Playground's command-line tool** (`@wp-playground/cli`), for
  the practice site (15.1). GPL-2.0-or-later, runs on the Node the shared
  runtime already bundles. It is the largest addition (its PHP-in-WebAssembly
  build is tens of megabytes per PHP version); ship one PHP version, pinned,
  in the shared runtime, started only when asked.
- **openpyxl** (already shipped) for spreadsheet import and export.
- **markitdown and Pandoc** (already shipped) for importing documents and for
  Read Site as Document's exports.

**On the WordPress site, not in QUILL's installers:**

- **QAF** (`S:\code\qaf`): the spam providers (Akismet, OOPSpam, Shield
  Security, CleanTalk) need no libraries, only their plugins or keys on the
  site; ALTCHA needs its PHP library (`altcha-org/altcha-lib-php`, MIT),
  bundled inside QAF.
- **QUILL Site Types** (decision 12): a new plugin with no dependencies.

**Services, not dependencies,** each with consent and an egress row:
WordPress.org's plugin directory API, one vulnerability database (decision 15;
its licence must allow this use), and the site-answering Watch.

## Part G: rollout

| Phase | What ships |
|---|---|
| W0 | The shared engine: make the GitHub Workbench's tree, actions, properties, filters, history, help and coverage modules provider-neutral (after GitHub Phase 1, before GitHub Phase 2 grows) |
| W1 | The WordPress Workbench, read-only: the tree, lists and details, from today's loaders; Needs My Attention |
| W2 | Properties on every object; the editor's Properties shares the sheet |
| W3 | Editing and batch; Trash and Undo; filters |
| W4 | Permissions: capabilities, users, roles, application passwords, View As Role |
| W5 | Coverage: the recorded index, the gate, schema-built types, Abilities |
| W6 | Tools > WordPress becomes doors; its windows parked one release, then retired |
| W3a | Spam: Held as Spam in the Workbench (comments first, then QAF entries); in QAF, the hold-never-drop rule, reasons, and the provider interface with Akismet and OOPSpam |
| W3b | Other form plugins: Gravity Forms, then the rest of 13b.2; import into QAF |
| W7 | Bold: practice site, site to site, calendar, editorial queue, Read Site as Document, Watches, REST Console, lists in and out |
| W8 | Things in their own places within a site, then Across Sites, Site Sets and the Fleet view (15.12) |

Help and docs ship with each phase, never after.

### Risks

| Risk | What reduces it |
|---|---|
| Two Workbenches drift apart | one engine (WP-R-001); a test that both providers use only shared frame code |
| Plugin routes with poor schemas | schema-built sheets fall back to read-only details with the raw fields named |
| Big sites and slow hosts | `_fields`, paging, caching, batch endpoint, honest loading states |
| A batch damages a site | previews, Trash first, revisions, snapshots, Read Only per site |
| Playground's size and pace | bundled once in the shared runtime; started only when asked |
| Users who love the current windows | they stay one release as a fallback |

### Decisions for Jeff

**All decided, 2026-11-09.** Jeff: "I agree with all of this." Every
recommendation below is accepted as written, decisions 1 to 16.

1. Build the shared engine first (Phase W0), before GitHub's Workbench grows
   past its spike? Recommendation: yes.
2. Writing stays in the editor, and Enter on a post opens it there?
   Recommendation: yes.
3. Needs My Attention across every site by default, with a per-site choice?
   Recommendation: yes.
4. Delete means Trash, and Shift+Delete is Delete Permanently with
   confirmation? Recommendation: yes.
5. Bundle WordPress Playground's command-line tool for the practice site?
   Recommendation: yes, in the shared runtime, pinned.
6. The site-answering Watch, at most every 15 minutes, off by default?
   Recommendation: yes.
7. Retire the Tools > WordPress windows one release after W6?
   Recommendation: yes.
8. QAF holds doubtful entries as spam and never rejects on behaviour signals
   (13a.2)? Recommendation: yes; it is the rule that protects QUILL's own
   users.
9. Which spam providers first? Recommendation: Akismet (most sites already
   have it) and OOPSpam, then Shield Security once its integration points are
   confirmed with its developers, then CleanTalk and ALTCHA.
10. Content-sending providers off until the owner turns them on, each
    described in QAF's privacy text? Recommendation: yes.
11. Which other form plugins first? Recommendation: Gravity Forms (fullest
    API), then Jetpack Forms, Formidable and Fluent Forms; Contact Form 7 and
    WPForms as far as their APIs reach.
12. Making post types and fields: QUILL Site Types as its own small plugin,
    or a module inside QAF? Recommendation: its own plugin, in its own repo
    beside `S:\code\qaf`, because a site may want types without forms; QAF
    uses it when both are present.
13. Field kinds: start with the core list of 12b including the accessibility
    kinds (transcript, captions, long description, language-marked text)?
    Recommendation: yes; they are what no field plugin offers.
14. Text challenges: maths off by default in favour of everyday questions,
    and Send Anyway after three tries? Recommendation: yes to both.
15. Calls to WordPress.org (plugin search, last-updated dates) and to a
    vulnerability database, each with consent and an egress row?
    Recommendation: yes, off until the person turns them on.
16. Which 15.11 areas first? Recommendation: redirects, backups status,
    security alerts and privacy requests (they protect the site and its
    visitors), then memberships (BITS runs Paid Memberships Pro), then the
    rest by demand.
17. Across Sites on Ctrl+0 and terms in their own places, as in the GitHub
    Workbench (15.12)? Recommendation: yes; terms within a site first, then
    plugins and users across sites. (Added after the 16 accepted decisions;
    open until Jeff confirms.)

The QAF items (13a.1 to 13a.3, WP-R-026 to WP-R-028) are built in
`S:\code\qaf` and belong in its own PRD (`docs/PRD.md` there) as well; the
Workbench side is built here.

## Appendix A: every object and its Properties sheet

| Object | Pages | Notes |
|---|---|---|
| Post, page, custom item | General (title, slug, status, visibility, password, author, dates), Organize (categories, tags, custom taxonomies, format, sticky), Featured Image, Excerpt, Discussion (comments, pings), Template and Parent (pages), Revisions, Meta (registered fields), SEO (when a plugin exposes it), You (your edits, your notes) | The same sheet as File > WordPress > Properties |
| Media item | General (title, file, type, size, dimensions, uploaded, by), Alt Text and Caption, Description, Attached To, Sizes, Listen or Watch (audio and video: length, transcript, captions), Usage (where it appears) | Alt text required for pictures before insert, as now |
| Comment | General (author, email, address, date, status, type), Text, Post, Thread, Moderation history | Email shown only with `moderate_comments` |
| Category, tag, custom term | General (name, slug, description, parent), Posts, Count | Merge Into... on the sheet |
| Menu, menu item, location | Items as a tree, Locations, each item's label, target, link, classes, description | Navigation blocks the same way |
| User | General (name, username, email, display name, website, bio), Role, Posts, Application Passwords, Sessions (where exposed) | Remove with reassignment |
| Plugin | General (name, version, author, description, status, auto-updates), Update (what changed, from its changelog), Network | Activate, Deactivate, Update, Delete |
| Theme | General, Update, Customizations (global styles), Templates | Activate, Update |
| Template, template part | General (title, slug, theme, source: theme or customized), Area (parts), Usage | Reset to Theme |
| Pattern | General (title, categories, synced), Usage | |
| Font family and face | General, Faces, Usage | Install from the font collection, remove |
| Widget, sidebar | Widget type, settings from its schema, sidebar | Legacy widgets read-only where the API is |
| Settings group | Every field of General, Writing, Reading, Discussion, Media, Permalinks, Privacy, with this site's examples | Read-only where `manage_options` is missing |
| Form, response, payment | the Forms engine's sheets (wordpress.md 17a) | |
| Product, order, customer, coupon | the shop's fields; an order read as a receipt | |
| Podcast episode | the episode's fields, enclosure, feed status | |
| Application password | Name, created, last used, last address, Revoke | |
| Site | General (name, tagline, address, language, time zone), Health, Your Role, Connection (how QUILL signs in), Counts, REST Namespaces, Abilities | Alt+Enter on the site node |
| Anything discovered | built from its route's schema (section 12) | |

## Appendix B: every shipped window and its new home

| Today (Tools > WordPress) | New home |
|---|---|
| Media Library | Sites > site > Media; picking mode for Insert |
| Comments | Sites > site > Comments; Needs My Attention > Comments Waiting |
| Categories and Tags | Sites > site > Categories, Tags |
| Menus | Sites > site > Menus and Navigation |
| Site Map | Sites > site > Pages (the parent tree) |
| Site Check and Settings | Sites > site > Settings; Site Health |
| Manage: users | Sites > site > People > Users |
| Manage: plugins | Sites > site > Plugins |
| Manage: themes, fonts, synced patterns | Sites > site > Appearance |
| Check the Whole Site, Alt Text Review | Needs My Attention > Accessibility; Media > Without Alt Text |
| Visual Review | Item > Visual Review on a page; stays a dialog |
| Site-wide Find and Replace | Edit > Find and Replace Across Sites... |
| Forms, responses, payments | Sites > site > Forms |
| Shop | Sites > site > Shop |
| Post This Episode | Sites > site > Podcast; File > New > Episode |
| Switch Site, Sites, Connect a Site | the Sites branch; File > Connect a Site |
| Blocks window, Check Before Publishing | Stay in the editor: they are about the document |

## Appendix C: REST families and what they feed

| Route family | Feeds |
|---|---|
| `wp/v2/posts`, `pages`, each type's route, `revisions`, `autosaves` | Posts, Pages, custom types; sheets; Revisions |
| `wp/v2/types`, `taxonomies`, `statuses` | discovery of the tree (section 12) |
| `wp/v2/media` | Media |
| `wp/v2/comments` | Comments |
| `wp/v2/categories`, `tags`, each taxonomy's route | terms |
| `wp/v2/menus`, `menu-items`, `menu-locations`, `navigation` | Menus and Navigation |
| `wp/v2/themes`, `global-styles`, `templates`, `template-parts`, `blocks`, `block-patterns`, `font-families`, `font-collections` | Appearance |
| `wp/v2/widgets`, `sidebars`, `widget-types` | Widgets and Sidebars |
| `wp/v2/users`, `users/{id}/application-passwords` | People |
| `wp/v2/plugins`, `block-directory/search` | Plugins |
| `wp/v2/settings` | Settings |
| `wp-site-health/v1` | Site Health |
| `wp/v2/search` | Search |
| `batch/v1` | every batch (section 9) |
| `wp-abilities/v1` | Abilities (section 12) |
| `wc/v3` (WooCommerce), the forms plugin's namespace, podcast plugins | Shop, Forms, Podcast |
| every other namespace | More from this site, schema-built |

## Appendix D: the WordPress REST API, every route on the test site

Generated from the public REST index of the QUILL WordPress Test Site (https://lp.csedesigns.com/wordpress, read 2026-11-09 without signing in): **802 routes in 27 namespaces**. Signed in, a site can show more (routes that need a capability to be listed), and every site differs by its plugins, which is why section 12 discovers routes per site rather than trusting this list. This appendix is the recorded index the coverage gate runs against.

How to read each table:

- **Route** and **Methods**: GET reads; POST creates or changes; PUT and PATCH change; DELETE removes (with `force` it skips Trash).
- **Arguments** are every parameter the route accepts, with its allowed values in brackets. These are the combinations: on a GET they are the Filter Builder's attributes and values (section 10); on a POST, PUT or PATCH they are the Properties sheet's fields (section 8). Every one must be reachable. Common ones (`context`, `_fields`, `_embed`, `page`, `per_page`, `offset`) are plumbing and left out of the lists.
- **QUILL today** says whether QUILL's WordPress code names this route family now (an approximate text match; wordpress.md 9.17 is the exact audit).

### D.0 GraphQL

WordPress itself has no GraphQL API. The WPGraphQL plugin adds one at `/graphql`, with an introspectable schema. The test site does not run it. When a connected site does, the Workbench lists it under More from this site, reads its schema the way it reads REST schemas, and the REST Console (section 15.9) gains a GraphQL mode; REST stays the primary route because every site has it.

### D.1 Namespaces

| Namespace | Routes | Workbench home | QUILL today |
|---|---|---|---|
| `wp/v2` | 150 | Core content and site (by family below) | yes |
| `wc/v3` | 112 | Sites > site > Shop (products, orders, customers, coupons, reports, settings, taxes, shipping, payment gateways, webhooks) | yes |
| `wc-admin` | 97 | Shop > Reports and Analytics (read-only tables); shop onboarding and notes | no |
| `wc-analytics` | 89 | Shop > Reports and Analytics (read-only tables) | no |
| `wc/v2` | 72 | Shop: older version of wc/v3; use wc/v3 | no |
| `yoast/v1` | 61 | Post and page Properties > SEO; Sites > site > SEO (Yoast settings, redirects where the plan offers them) | yes |
| `wc/v1` | 49 | Shop: older version of wc/v3; use wc/v3 | no |
| `wc/store` | 31 | Out of scope: the shop's public checkout API for visitors | no |
| `wc/store/v1` | 31 | Out of scope: the shop's public checkout API for visitors | no |
| `jetpack/v4` | 18 | Sites > site > Jetpack (modules on and off, connection, stats where exposed) | no |
| `tribe/events/v1` | 15 | Sites > site > Events (The Events Calendar): events, venues, organizers, categories, tags | yes |
| `baf/v1` | 12 | To identify: a plugin namespace on the test site; schema-built until known | yes |
| `tec/v1` | 8 | Events: settings and tickets where offered | no |
| `wccom-site/v3` | 8 | Out of scope: WooCommerce.com connection internals | no |
| `wp-site-health/v1` | 8 | Sites > site > Site Health; Needs My Attention > Site Health | yes |
| `tec/migrations/v1` | 6 | Out of scope: data migrations | no |
| `wp-abilities/v1` | 6 | Sites > site > Abilities (section 12) | yes |
| `wc-admin-email` | 5 | Shop > Settings > Emails | no |
| `wp-block-editor/v1` | 4 | Editor plumbing: block editor settings, URL details, navigation fallback | yes |
| `oembed/1.0` | 3 | Editor plumbing: embeds (Name Embeds) | yes |
| `tribe/event-aggregator/v1` | 3 | Events > Imports (Event Aggregator) | no |
| `(index)` | 2 | Discovery: the index itself | no |
| `wc/pos/v1/catalog` | 2 | Out of scope: point of sale catalog | no |
| `tribe/views/v2` | 2 | Out of scope: the calendar's front-end views | no |
| `tec/v2/onboarding` | 2 | Out of scope: setup wizard | no |
| `wc/private` | 2 | Out of scope: private to WooCommerce | no |
| `wc-push-notifications` | 2 | Out of scope: WooCommerce mobile app notifications | no |
| `wc-telemetry` | 2 | Out of scope: WooCommerce telemetry | no |

### D: `wp/v2` (150 routes)

Home: Core content and site (by family below).

| Route | Methods | Arguments | Home | QUILL today |
|---|---|---|---|---|
| `/wp/v2` | GET | namespace | Discovery | no |
| `/wp/v2/block-directory/search` | GET | term | Plugins > Add Block Plugin (block directory) | no |
| `/wp/v2/block-patterns/categories` | GET | - | Appearance > Patterns; Insert Block | yes |
| `/wp/v2/block-patterns/patterns` | GET | - | Appearance > Patterns; Insert Block | yes |
| `/wp/v2/block-renderer/(?P<name>[a-z0-9-]+/[a-z0-9-]+)` | GET, POST | name; attributes; post_id | Editor plumbing: block preview | yes |
| `/wp/v2/block-types` | GET | namespace | Insert Block (editor) | yes |
| `/wp/v2/block-types/(?P<namespace>[a-zA-Z0-9_-]+)` | GET | namespace | Insert Block (editor) | yes |
| `/wp/v2/block-types/(?P<namespace>[a-zA-Z0-9_-]+)/(?P<name>[a-zA-Z0-9_-]+)` | GET | name; namespace | Insert Block (editor) | yes |
| `/wp/v2/blocks` | GET, POST | search; after; modified_after; before; modified_before; exclude; include; search_semantics (exact); order (asc / desc); orderby (author / date / id / include / modified / parent / relevance / slug / include_slugs / title); search_columns (post_title / post_content / post_excerpt); slug; status (publish / future / draft / pending / private / trash / auto-draft / inherit / request-pending / request-confirmed / request-failed / request-completed / wc-pending / wc-processing and 13 more); tax_relation (AND / OR); wp_pattern_category; wp_pattern_category_exclude; date; date_gmt; status (publish / future / draft / pending / private / wc-pending / wc-processing / wc-on-hold / wc-completed / wc-cancelled / wc-refunded / wc-failed / wc-checkout-draft / tribe-ea-success and 5 more); password; title; content; excerpt; meta; template | Appearance > Patterns (synced) | yes |
| `/wp/v2/blocks/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; excerpt_length; password; date; date_gmt; slug; status (publish / future / draft / pending / private / wc-pending / wc-processing / wc-on-hold / wc-completed / wc-cancelled / wc-refunded / wc-failed / wc-checkout-draft / tribe-ea-success and 5 more); title; content; excerpt; meta; template; wp_pattern_category; force | Appearance > Patterns (synced) | yes |
| `/wp/v2/blocks/(?P<id>[\d]+)/autosaves` | GET, POST | parent; date; date_gmt; slug; status (publish / future / draft / pending / private / wc-pending / wc-processing / wc-on-hold / wc-completed / wc-cancelled / wc-refunded / wc-failed / wc-checkout-draft / tribe-ea-success and 5 more); password; title; content; excerpt; meta; template; wp_pattern_category | Appearance > Patterns (synced) | yes |
| `/wp/v2/blocks/(?P<parent>[\d]+)/autosaves/(?P<id>[\d]+)` | GET | parent; id | Appearance > Patterns (synced) | yes |
| `/wp/v2/blocks/(?P<parent>[\d]+)/revisions` | GET | parent; search; exclude; include; order (asc / desc); orderby (date / id / include / relevance / slug / include_slugs / title) | Appearance > Patterns (synced) | yes |
| `/wp/v2/blocks/(?P<parent>[\d]+)/revisions/(?P<id>[\d]+)` | GET, DELETE | parent; id; force | Appearance > Patterns (synced) | yes |
| `/wp/v2/categories` | GET, POST | search; exclude; include; order (asc / desc); orderby (id / include / name / slug / include_slugs / term_group / description / count); hide_empty; parent; post; slug; description; name; meta | Categories | yes |
| `/wp/v2/categories/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; description; name; slug; parent; meta; force | Categories | yes |
| `/wp/v2/comments` | GET, POST | search; after; author; author_exclude; author_email; before; exclude; include; order (asc / desc); orderby (date / date_gmt / id / include / post / parent / type); parent; parent_exclude; post; status; type; password; author_ip; author_name; author_url; author_user_agent; content; date; date_gmt; meta | Comments; Held as Spam; comment Properties | yes |
| `/wp/v2/comments/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; password; author; author_email; author_ip; author_name; author_url; author_user_agent; content; date; date_gmt; parent; post; status; meta; force | Comments; Held as Spam; comment Properties | yes |
| `/wp/v2/events` | GET, POST | search; after; modified_after; author; author_exclude; before; modified_before; exclude; include; search_semantics (exact); order (asc / desc); orderby (author / date / id / include / modified / parent / relevance / slug / include_slugs / title); search_columns (post_title / post_content / post_excerpt); slug; status (publish / future / draft / pending / private / trash / auto-draft / inherit / request-pending / request-confirmed / request-failed / request-completed / wc-pending / wc-processing and 13 more); date; date_gmt; status (publish / future / draft / pending / private / wc-pending / wc-processing / wc-on-hold / wc-completed / wc-cancelled / wc-refunded / wc-failed / wc-checkout-draft / tribe-ea-success and 5 more); password; title; content; template | Discovered type or taxonomy `events`: schema-built (section 12) | no |
| `/wp/v2/events/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; password; date; date_gmt; slug; status (publish / future / draft / pending / private / wc-pending / wc-processing / wc-on-hold / wc-completed / wc-cancelled / wc-refunded / wc-failed / wc-checkout-draft / tribe-ea-success and 5 more); title; content; author; template; force | Discovered type or taxonomy `events`: schema-built (section 12) | no |
| `/wp/v2/events/(?P<id>[\d]+)/autosaves` | GET, POST | parent; date; date_gmt; slug; status (publish / future / draft / pending / private / wc-pending / wc-processing / wc-on-hold / wc-completed / wc-cancelled / wc-refunded / wc-failed / wc-checkout-draft / tribe-ea-success and 5 more); password; title; content; author; template | Discovered type or taxonomy `events`: schema-built (section 12) | no |
| `/wp/v2/events/(?P<parent>[\d]+)/autosaves/(?P<id>[\d]+)` | GET | parent; id | Discovered type or taxonomy `events`: schema-built (section 12) | no |
| `/wp/v2/events/(?P<parent>[\d]+)/revisions` | GET | parent; search; exclude; include; order (asc / desc); orderby (date / id / include / relevance / slug / include_slugs / title) | Discovered type or taxonomy `events`: schema-built (section 12) | no |
| `/wp/v2/events/(?P<parent>[\d]+)/revisions/(?P<id>[\d]+)` | GET, DELETE | parent; id; force | Discovered type or taxonomy `events`: schema-built (section 12) | no |
| `/wp/v2/font-collections` | GET | - | Appearance > Fonts (install) | yes |
| `/wp/v2/font-collections/(?P<slug>[\/\w-]+)` | GET | - | Appearance > Fonts (install) | yes |
| `/wp/v2/font-families` | GET, POST | exclude; include; search_semantics (exact); order (asc / desc); orderby (id / include); slug; theme_json_version; font_family_settings | Appearance > Fonts | yes |
| `/wp/v2/font-families/(?P<font_family_id>[\d]+)/font-faces` | GET, POST | font_family_id; exclude; include; search_semantics (exact); order (asc / desc); orderby (id / include); theme_json_version; font_face_settings | Appearance > Fonts | yes |
| `/wp/v2/font-families/(?P<font_family_id>[\d]+)/font-faces/(?P<id>[\d]+)` | GET, DELETE | font_family_id; id; force | Appearance > Fonts | yes |
| `/wp/v2/font-families/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; theme_json_version; font_family_settings; force | Appearance > Fonts | yes |
| `/wp/v2/global-styles/(?P<id>[\/\d+]+)` | GET, POST, PUT, PATCH | id; styles; settings; title | Appearance > Global Styles | yes |
| `/wp/v2/global-styles/(?P<parent>[\d]+)/revisions` | GET | parent | Appearance > Global Styles | yes |
| `/wp/v2/global-styles/(?P<parent>[\d]+)/revisions/(?P<id>[\d]+)` | GET | parent; id | Appearance > Global Styles | yes |
| `/wp/v2/global-styles/themes/(?P<stylesheet>[\/\s%\w\.\(\)\[\]\@_\-]+)/variations` | GET | stylesheet | Appearance > Global Styles | yes |
| `/wp/v2/global-styles/themes/(?P<stylesheet>[^\/:<>\*\?"\\|]+(?:\/[^\/:<>\*\?"\\|]+)?)` | GET | stylesheet | Appearance > Global Styles | yes |
| `/wp/v2/icon-collections` | GET | search | Discovered type or taxonomy `icon-collections`: schema-built (section 12) | yes |
| `/wp/v2/icon-collections/(?P<slug>[a-z0-9](?:[a-z0-9_-]*[a-z0-9])?)` | GET | slug | Discovered type or taxonomy `icon-collections`: schema-built (section 12) | yes |
| `/wp/v2/icons` | GET | search; collection | Discovered type or taxonomy `icons`: schema-built (section 12) | yes |
| `/wp/v2/icons/(?P<collection>[a-z0-9](?:[a-z0-9_-]*[a-z0-9])?)` | GET | collection; search | Discovered type or taxonomy `icons`: schema-built (section 12) | yes |
| `/wp/v2/icons/(?P<name>[a-z0-9](?:[a-z0-9_-]*[a-z0-9])?/[a-z0-9](?:[a-z0-9_-]*[a-z0-9])?)` | GET | name | Discovered type or taxonomy `icons`: schema-built (section 12) | yes |
| `/wp/v2/media` | GET, POST | search; after; modified_after; author; author_exclude; before; modified_before; exclude; include; search_semantics (exact); order (asc / desc); orderby (author / date / id / include / modified / parent / relevance / slug / include_slugs / title); parent; parent_exclude; search_columns (post_title / post_content / post_excerpt); slug; status (inherit / private / trash); media_type (image / video / text / application / audio); mime_type; date; date_gmt; status (publish / future / draft / pending / private / wc-pending / wc-processing / wc-on-hold / wc-completed / wc-cancelled / wc-refunded / wc-failed / wc-checkout-draft / tribe-ea-success and 5 more); title; featured_media; comment_status (open / closed); ping_status (open / closed); meta; template; alt_text; caption; description; post; generate_sub_sizes; convert_format; url | Media; media Properties | yes |
| `/wp/v2/media/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; date; date_gmt; slug; status (publish / future / draft / pending / private / wc-pending / wc-processing / wc-on-hold / wc-completed / wc-cancelled / wc-refunded / wc-failed / wc-checkout-draft / tribe-ea-success and 5 more); title; author; featured_media; comment_status (open / closed); ping_status (open / closed); meta; template; alt_text; caption; description; post; force | Media; media Properties | yes |
| `/wp/v2/media/(?P<id>[\d]+)/edit` | POST | src; modifiers; rotation; x; y; width; height; caption; description; title; post; alt_text | Media; media Properties | yes |
| `/wp/v2/media/(?P<id>[\d]+)/finalize` | POST | id; sub_sizes | Media; media Properties | yes |
| `/wp/v2/media/(?P<id>[\d]+)/post-process` | POST | id; action (create-image-subsizes) | Media; media Properties | yes |
| `/wp/v2/media/(?P<id>[\d]+)/sideload` | POST | id; image_size; convert_format | Media; media Properties | yes |
| `/wp/v2/menu-items` | GET, POST | search; after; modified_after; before; modified_before; exclude; include; search_semantics (exact); order (asc / desc); orderby (author / date / id / include / modified / parent / relevance / slug / include_slugs / title / menu_order); search_columns (post_title / post_content / post_excerpt); slug; status (publish / future / draft / pending / private / trash / auto-draft / inherit / request-pending / request-confirmed / request-failed / request-completed / wc-pending / wc-processing and 13 more); tax_relation (AND / OR); menus; menus_exclude; menu_order; title; type (taxonomy / post_type / post_type_archive / custom); status (publish / future / draft / pending / private / wc-pending / wc-processing / wc-on-hold / wc-completed / wc-cancelled / wc-refunded / wc-failed / wc-checkout-draft / tribe-ea-success and 5 more); parent; attr_title; classes; description; object; object_id; target (_blank / ); url; xfn; meta | Menus and Navigation | yes |
| `/wp/v2/menu-items/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; title; type (taxonomy / post_type / post_type_archive / custom); status (publish / future / draft / pending / private / wc-pending / wc-processing / wc-on-hold / wc-completed / wc-cancelled / wc-refunded / wc-failed / wc-checkout-draft / tribe-ea-success and 5 more); parent; attr_title; classes; description; menu_order; object; object_id; target (_blank / ); url; xfn; menus; meta; force | Menus and Navigation | yes |
| `/wp/v2/menu-items/(?P<id>[\d]+)/autosaves` | GET, POST | parent; title; type (taxonomy / post_type / post_type_archive / custom); status (publish / future / draft / pending / private / wc-pending / wc-processing / wc-on-hold / wc-completed / wc-cancelled / wc-refunded / wc-failed / wc-checkout-draft / tribe-ea-success and 5 more); attr_title; classes; description; menu_order; object; object_id; target (_blank / ); url; xfn; menus; meta | Menus and Navigation | yes |
| `/wp/v2/menu-items/(?P<parent>[\d]+)/autosaves/(?P<id>[\d]+)` | GET | parent; id | Menus and Navigation | yes |
| `/wp/v2/menu-locations` | GET | - | Menus and Navigation | yes |
| `/wp/v2/menu-locations/(?P<location>[\w-]+)` | GET | location | Menus and Navigation | yes |
| `/wp/v2/menus` | GET, POST | search; exclude; include; order (asc / desc); orderby (id / include / name / slug / include_slugs / term_group / description / count); hide_empty; post; slug; description; name; meta; locations; auto_add | Menus and Navigation | yes |
| `/wp/v2/menus/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; description; name; slug; meta; locations; auto_add; force | Menus and Navigation | yes |
| `/wp/v2/navigation` | GET, POST | search; after; modified_after; before; modified_before; exclude; include; search_semantics (exact); order (asc / desc); orderby (author / date / id / include / modified / parent / relevance / slug / include_slugs / title); search_columns (post_title / post_content / post_excerpt); slug; status (publish / future / draft / pending / private / trash / auto-draft / inherit / request-pending / request-confirmed / request-failed / request-completed / wc-pending / wc-processing and 13 more); date; date_gmt; status (publish / future / draft / pending / private / wc-pending / wc-processing / wc-on-hold / wc-completed / wc-cancelled / wc-refunded / wc-failed / wc-checkout-draft / tribe-ea-success and 5 more); password; title; content; template | Menus and Navigation (navigation blocks) | yes |
| `/wp/v2/navigation/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; password; date; date_gmt; slug; status (publish / future / draft / pending / private / wc-pending / wc-processing / wc-on-hold / wc-completed / wc-cancelled / wc-refunded / wc-failed / wc-checkout-draft / tribe-ea-success and 5 more); title; content; template; force | Menus and Navigation (navigation blocks) | yes |
| `/wp/v2/navigation/(?P<id>[\d]+)/autosaves` | GET, POST | parent; date; date_gmt; slug; status (publish / future / draft / pending / private / wc-pending / wc-processing / wc-on-hold / wc-completed / wc-cancelled / wc-refunded / wc-failed / wc-checkout-draft / tribe-ea-success and 5 more); password; title; content; template | Menus and Navigation (navigation blocks) | yes |
| `/wp/v2/navigation/(?P<parent>[\d]+)/autosaves/(?P<id>[\d]+)` | GET | parent; id | Menus and Navigation (navigation blocks) | yes |
| `/wp/v2/navigation/(?P<parent>[\d]+)/revisions` | GET | parent; search; exclude; include; order (asc / desc); orderby (date / id / include / relevance / slug / include_slugs / title) | Menus and Navigation (navigation blocks) | yes |
| `/wp/v2/navigation/(?P<parent>[\d]+)/revisions/(?P<id>[\d]+)` | GET, DELETE | parent; id; force | Menus and Navigation (navigation blocks) | yes |
| `/wp/v2/pages` | GET, POST | search; after; modified_after; author; author_exclude; before; modified_before; exclude; include; menu_order; search_semantics (exact); order (asc / desc); orderby (author / date / id / include / modified / parent / relevance / slug / include_slugs / title / menu_order); parent; parent_exclude; search_columns (post_title / post_content / post_excerpt); slug; status (publish / future / draft / pending / private / trash / auto-draft / inherit / request-pending / request-confirmed / request-failed / request-completed / wc-pending / wc-processing and 13 more); date; date_gmt; status (publish / future / draft / pending / private / wc-pending / wc-processing / wc-on-hold / wc-completed / wc-cancelled / wc-refunded / wc-failed / wc-checkout-draft / tribe-ea-success and 5 more); password; title; content; excerpt; featured_media; comment_status (open / closed); ping_status (open / closed); meta; template | Pages; page Properties | yes |
| `/wp/v2/pages/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; excerpt_length; password; date; date_gmt; slug; status (publish / future / draft / pending / private / wc-pending / wc-processing / wc-on-hold / wc-completed / wc-cancelled / wc-refunded / wc-failed / wc-checkout-draft / tribe-ea-success and 5 more); parent; title; content; author; excerpt; featured_media; comment_status (open / closed); ping_status (open / closed); menu_order; meta; template; force | Pages; page Properties | yes |
| `/wp/v2/pages/(?P<id>[\d]+)/autosaves` | GET, POST | parent; date; date_gmt; slug; status (publish / future / draft / pending / private / wc-pending / wc-processing / wc-on-hold / wc-completed / wc-cancelled / wc-refunded / wc-failed / wc-checkout-draft / tribe-ea-success and 5 more); password; title; content; author; excerpt; featured_media; comment_status (open / closed); ping_status (open / closed); menu_order; meta; template | Pages; page Properties | yes |
| `/wp/v2/pages/(?P<parent>[\d]+)/autosaves/(?P<id>[\d]+)` | GET | parent; id | Pages; page Properties | yes |
| `/wp/v2/pages/(?P<parent>[\d]+)/revisions` | GET | parent; search; exclude; include; order (asc / desc); orderby (date / id / include / relevance / slug / include_slugs / title) | Pages; page Properties | yes |
| `/wp/v2/pages/(?P<parent>[\d]+)/revisions/(?P<id>[\d]+)` | GET, DELETE | parent; id; force | Pages; page Properties | yes |
| `/wp/v2/pattern-directory/patterns` | GET | search; category; keyword; slug; order (asc / desc); orderby (author / date / id / include / modified / parent / relevance / slug / include_slugs / title / favorite_count) | Appearance > Patterns > From the Pattern Directory | yes |
| `/wp/v2/plugins` | GET, POST | search; status (inactive / active); slug | Plugins | yes |
| `/wp/v2/plugins/(?P<plugin>[^.\/]+(?:\/[^.\/]+)?)` | GET, POST, PUT, PATCH, DELETE | plugin; status (inactive / active) | Plugins | yes |
| `/wp/v2/posts` | GET, POST | search; after; modified_after; author; author_exclude; before; modified_before; exclude; include; search_semantics (exact); order (asc / desc); orderby (author / date / id / include / modified / parent / relevance / slug / include_slugs / title); search_columns (post_title / post_content / post_excerpt); slug; status (publish / future / draft / pending / private / trash / auto-draft / inherit / request-pending / request-confirmed / request-failed / request-completed / wc-pending / wc-processing and 13 more); tax_relation (AND / OR); categories; categories_exclude; tags; tags_exclude; sticky; ignore_sticky; format (standard / aside / chat / gallery / link / image / quote / status / video / audio); date; date_gmt; status (publish / future / draft / pending / private / wc-pending / wc-processing / wc-on-hold / wc-completed / wc-cancelled / wc-refunded / wc-failed / wc-checkout-draft / tribe-ea-success and 5 more); password; title; content; excerpt; featured_media; comment_status (open / closed); ping_status (open / closed); meta; template | Posts; post Properties | yes |
| `/wp/v2/posts/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; excerpt_length; password; date; date_gmt; slug; status (publish / future / draft / pending / private / wc-pending / wc-processing / wc-on-hold / wc-completed / wc-cancelled / wc-refunded / wc-failed / wc-checkout-draft / tribe-ea-success and 5 more); title; content; author; excerpt; featured_media; comment_status (open / closed); ping_status (open / closed); format (standard / aside / chat / gallery / link / image / quote / status / video / audio); meta; sticky; template; categories; tags; force | Posts; post Properties | yes |
| `/wp/v2/posts/(?P<id>[\d]+)/autosaves` | GET, POST | parent; date; date_gmt; slug; status (publish / future / draft / pending / private / wc-pending / wc-processing / wc-on-hold / wc-completed / wc-cancelled / wc-refunded / wc-failed / wc-checkout-draft / tribe-ea-success and 5 more); password; title; content; author; excerpt; featured_media; comment_status (open / closed); ping_status (open / closed); format (standard / aside / chat / gallery / link / image / quote / status / video / audio); meta; sticky; template; categories; tags | Posts; post Properties | yes |
| `/wp/v2/posts/(?P<parent>[\d]+)/autosaves/(?P<id>[\d]+)` | GET | parent; id | Posts; post Properties | yes |
| `/wp/v2/posts/(?P<parent>[\d]+)/revisions` | GET | parent; search; exclude; include; order (asc / desc); orderby (date / id / include / relevance / slug / include_slugs / title) | Posts; post Properties | yes |
| `/wp/v2/posts/(?P<parent>[\d]+)/revisions/(?P<id>[\d]+)` | GET, DELETE | parent; id; force | Posts; post Properties | yes |
| `/wp/v2/product` | GET, POST | search; after; modified_after; before; modified_before; exclude; include; search_semantics (exact); order (asc / desc); orderby (author / date / id / include / modified / parent / relevance / slug / include_slugs / title / popularity / rating / post__in / price and 5 more); search_columns (post_title / post_content / post_excerpt); slug; status (publish / future / draft / pending / private / trash / auto-draft / inherit / request-pending / request-confirmed / request-failed / request-completed / wc-pending / wc-processing and 13 more); tax_relation (AND / OR); product_brand; product_brand_exclude; product_cat; product_cat_exclude; product_tag; product_tag_exclude; brand; date; date_gmt; status (publish / future / draft / pending / private / wc-pending / wc-processing / wc-on-hold / wc-completed / wc-cancelled / wc-refunded / wc-failed / wc-checkout-draft / tribe-ea-success and 5 more); password; title; content; excerpt; featured_media; comment_status (open / closed); ping_status (open / closed); meta; template | Discovered type or taxonomy `product`: schema-built (section 12) | no |
| `/wp/v2/product/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; excerpt_length; password; date; date_gmt; slug; status (publish / future / draft / pending / private / wc-pending / wc-processing / wc-on-hold / wc-completed / wc-cancelled / wc-refunded / wc-failed / wc-checkout-draft / tribe-ea-success and 5 more); title; content; excerpt; featured_media; comment_status (open / closed); ping_status (open / closed); meta; template; product_brand; product_cat; product_tag; force | Discovered type or taxonomy `product`: schema-built (section 12) | no |
| `/wp/v2/product/(?P<id>[\d]+)/autosaves` | GET, POST | parent; date; date_gmt; slug; status (publish / future / draft / pending / private / wc-pending / wc-processing / wc-on-hold / wc-completed / wc-cancelled / wc-refunded / wc-failed / wc-checkout-draft / tribe-ea-success and 5 more); password; title; content; excerpt; featured_media; comment_status (open / closed); ping_status (open / closed); meta; template; product_brand; product_cat; product_tag | Discovered type or taxonomy `product`: schema-built (section 12) | no |
| `/wp/v2/product/(?P<parent>[\d]+)/autosaves/(?P<id>[\d]+)` | GET | parent; id | Discovered type or taxonomy `product`: schema-built (section 12) | no |
| `/wp/v2/product_brand` | GET, POST | search; exclude; include; order (asc / desc); orderby (id / include / name / slug / include_slugs / term_group / description / count); hide_empty; parent; post; slug; description; name; meta | Discovered type or taxonomy `product_brand`: schema-built (section 12) | no |
| `/wp/v2/product_brand/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; description; name; slug; parent; meta; force | Discovered type or taxonomy `product_brand`: schema-built (section 12) | no |
| `/wp/v2/product_cat` | GET, POST | search; exclude; include; order (asc / desc); orderby (id / include / name / slug / include_slugs / term_group / description / count); hide_empty; parent; post; slug; description; name; meta | Discovered type or taxonomy `product_cat`: schema-built (section 12) | no |
| `/wp/v2/product_cat/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; description; name; slug; parent; meta; force | Discovered type or taxonomy `product_cat`: schema-built (section 12) | no |
| `/wp/v2/product_tag` | GET, POST | search; exclude; include; order (asc / desc); orderby (id / include / name / slug / include_slugs / term_group / description / count); hide_empty; post; slug; description; name; meta | Discovered type or taxonomy `product_tag`: schema-built (section 12) | no |
| `/wp/v2/product_tag/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; description; name; slug; meta; force | Discovered type or taxonomy `product_tag`: schema-built (section 12) | no |
| `/wp/v2/search` | GET | search; type (post / term / post-format); subtype (post / page / product / event / tribe_events / category / post_tag / product_brand / product_cat / product_tag / tribe_events_cat / any); exclude; include | Search (across types) | no |
| `/wp/v2/settings` | GET, POST, PUT, PATCH | title; description; url; email; timezone; date_format; time_format; start_of_week; language; use_smilies; default_category; default_post_format; posts_per_page; show_on_front; page_on_front; page_for_posts; default_ping_status (open / closed); default_comment_status (open / closed); site_logo; site_icon; pickup_location_settings; pickup_locations; woocommerce_default_catalog_orderby (menu_order / popularity / rating / date / price / price-desc); woocommerce_checkout_phone_field (optional / required / hidden); woocommerce_checkout_company_field (optional / required / hidden); woocommerce_checkout_address_2_field (optional / required / hidden) | Settings (every group) | yes |
| `/wp/v2/sidebars` | GET | - | Appearance > Widgets and Sidebars | yes |
| `/wp/v2/sidebars/(?P<id>[\w-]+)` | GET, POST, PUT, PATCH | id; widgets | Appearance > Widgets and Sidebars | yes |
| `/wp/v2/statuses` | GET | - | Discovery of every status, for filters and the Status choice | no |
| `/wp/v2/statuses/(?P<status>[\w-]+)` | GET | status | Discovery of every status, for filters and the Status choice | no |
| `/wp/v2/tags` | GET, POST | search; exclude; include; order (asc / desc); orderby (id / include / name / slug / include_slugs / term_group / description / count); hide_empty; post; slug; description; name; meta | Tags | yes |
| `/wp/v2/tags/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; description; name; slug; meta; force | Tags | yes |
| `/wp/v2/taxonomies` | GET | type | Discovery of every taxonomy (section 12) | no |
| `/wp/v2/taxonomies/(?P<taxonomy>[\w-]+)` | GET | taxonomy | Discovery of every taxonomy (section 12) | no |
| `/wp/v2/tec_calendar_embed` | GET, POST | search; after; modified_after; before; modified_before; exclude; include; search_semantics (exact); order (asc / desc); orderby (author / date / id / include / modified / parent / relevance / slug / include_slugs / title); search_columns (post_title / post_content / post_excerpt); slug; status (publish / future / draft / pending / private / trash / auto-draft / inherit / request-pending / request-confirmed / request-failed / request-completed / wc-pending / wc-processing and 13 more); tax_relation (AND / OR); tags; tags_exclude; tribe_events_cat; tribe_events_cat_exclude; date; date_gmt; status (publish / future / draft / pending / private / wc-pending / wc-processing / wc-on-hold / wc-completed / wc-cancelled / wc-refunded / wc-failed / wc-checkout-draft / tribe-ea-success and 5 more); password; title; template | Discovered type or taxonomy `tec_calendar_embed`: schema-built (section 12) | no |
| `/wp/v2/tec_calendar_embed/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; password; date; date_gmt; slug; status (publish / future / draft / pending / private / wc-pending / wc-processing / wc-on-hold / wc-completed / wc-cancelled / wc-refunded / wc-failed / wc-checkout-draft / tribe-ea-success and 5 more); title; template; tags; tribe_events_cat; force | Discovered type or taxonomy `tec_calendar_embed`: schema-built (section 12) | no |
| `/wp/v2/template-parts` | GET, POST | wp_id; area; post_type; slug; theme; type; content; title; description; status (publish / future / draft / pending / private / wc-pending / wc-processing / wc-on-hold / wc-completed / wc-cancelled / wc-refunded / wc-failed / wc-checkout-draft / tribe-ea-success and 5 more); author | Appearance > Template Parts | yes |
| `/wp/v2/template-parts/(?P<id>([^\/:<>\*\?"\\|]+(?:\/[^\/:<>\*\?"\\|]+)?)[\/\w%-]+)` | GET, POST, PUT, PATCH, DELETE | id; slug; theme; type; content; title; description; status (publish / future / draft / pending / private / wc-pending / wc-processing / wc-on-hold / wc-completed / wc-cancelled / wc-refunded / wc-failed / wc-checkout-draft / tribe-ea-success and 5 more); author; area; force | Appearance > Template Parts | yes |
| `/wp/v2/template-parts/(?P<id>([^\/:<>\*\?"\\|]+(?:\/[^\/:<>\*\?"\\|]+)?)[\/\w%-]+)/autosaves` | GET, POST | id; slug; theme; type; content; title; description; status (publish / future / draft / pending / private / wc-pending / wc-processing / wc-on-hold / wc-completed / wc-cancelled / wc-refunded / wc-failed / wc-checkout-draft / tribe-ea-success and 5 more); author; area | Appearance > Template Parts | yes |
| `/wp/v2/template-parts/(?P<parent>([^\/:<>\*\?"\\|]+(?:\/[^\/:<>\*\?"\\|]+)?)[\/\w%-]+)/autosaves/(?P<id>[\d]+)` | GET | parent; id | Appearance > Template Parts | yes |
| `/wp/v2/template-parts/(?P<parent>([^\/:<>\*\?"\\|]+(?:\/[^\/:<>\*\?"\\|]+)?)[\/\w%-]+)/revisions` | GET | parent; search; exclude; include; order (asc / desc); orderby (date / id / include / relevance / slug / include_slugs / title) | Appearance > Template Parts | yes |
| `/wp/v2/template-parts/(?P<parent>([^\/:<>\*\?"\\|]+(?:\/[^\/:<>\*\?"\\|]+)?)[\/\w%-]+)/revisions/(?P<id>[\d]+)` | GET, DELETE | parent; id; force | Appearance > Template Parts | yes |
| `/wp/v2/template-parts/lookup` | GET | slug; is_custom; template_prefix | Appearance > Template Parts | yes |
| `/wp/v2/templates` | GET, POST | wp_id; area; post_type; slug; theme; type; content; title; description; status (publish / future / draft / pending / private / wc-pending / wc-processing / wc-on-hold / wc-completed / wc-cancelled / wc-refunded / wc-failed / wc-checkout-draft / tribe-ea-success and 5 more); author | Appearance > Templates | yes |
| `/wp/v2/templates/(?P<id>([^\/:<>\*\?"\\|]+(?:\/[^\/:<>\*\?"\\|]+)?)[\/\w%-]+)` | GET, POST, PUT, PATCH, DELETE | id; slug; theme; type; content; title; description; status (publish / future / draft / pending / private / wc-pending / wc-processing / wc-on-hold / wc-completed / wc-cancelled / wc-refunded / wc-failed / wc-checkout-draft / tribe-ea-success and 5 more); author; force | Appearance > Templates | yes |
| `/wp/v2/templates/(?P<id>([^\/:<>\*\?"\\|]+(?:\/[^\/:<>\*\?"\\|]+)?)[\/\w%-]+)/autosaves` | GET, POST | id; slug; theme; type; content; title; description; status (publish / future / draft / pending / private / wc-pending / wc-processing / wc-on-hold / wc-completed / wc-cancelled / wc-refunded / wc-failed / wc-checkout-draft / tribe-ea-success and 5 more); author | Appearance > Templates | yes |
| `/wp/v2/templates/(?P<parent>([^\/:<>\*\?"\\|]+(?:\/[^\/:<>\*\?"\\|]+)?)[\/\w%-]+)/autosaves/(?P<id>[\d]+)` | GET | parent; id | Appearance > Templates | yes |
| `/wp/v2/templates/(?P<parent>([^\/:<>\*\?"\\|]+(?:\/[^\/:<>\*\?"\\|]+)?)[\/\w%-]+)/revisions` | GET | parent; search; exclude; include; order (asc / desc); orderby (date / id / include / relevance / slug / include_slugs / title) | Appearance > Templates | yes |
| `/wp/v2/templates/(?P<parent>([^\/:<>\*\?"\\|]+(?:\/[^\/:<>\*\?"\\|]+)?)[\/\w%-]+)/revisions/(?P<id>[\d]+)` | GET, DELETE | parent; id; force | Appearance > Templates | yes |
| `/wp/v2/templates/lookup` | GET | slug; is_custom; template_prefix | Appearance > Templates | yes |
| `/wp/v2/themes` | GET | status (active / inactive) | Appearance > Themes | yes |
| `/wp/v2/themes/(?P<stylesheet>[^\/:<>\*\?"\\|]+(?:\/[^\/:<>\*\?"\\|]+)?)` | GET | stylesheet | Appearance > Themes | yes |
| `/wp/v2/tribe_events` | GET, POST | search; after; modified_after; author; author_exclude; before; modified_before; exclude; include; search_semantics (exact); order (asc / desc); orderby (author / date / id / include / modified / parent / relevance / slug / include_slugs / title); search_columns (post_title / post_content / post_excerpt); slug; status (publish / future / draft / pending / private / trash / auto-draft / inherit / request-pending / request-confirmed / request-failed / request-completed / wc-pending / wc-processing and 13 more); tax_relation (AND / OR); tags; tags_exclude; tribe_events_cat; tribe_events_cat_exclude; date; date_gmt; status (publish / future / draft / pending / private / wc-pending / wc-processing / wc-on-hold / wc-completed / wc-cancelled / wc-refunded / wc-failed / wc-checkout-draft / tribe-ea-success and 5 more); password; title; content; excerpt; featured_media; meta; template | Discovered type or taxonomy `tribe_events`: schema-built (section 12) | no |
| `/wp/v2/tribe_events/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; excerpt_length; password; date; date_gmt; slug; status (publish / future / draft / pending / private / wc-pending / wc-processing / wc-on-hold / wc-completed / wc-cancelled / wc-refunded / wc-failed / wc-checkout-draft / tribe-ea-success and 5 more); title; content; author; excerpt; featured_media; meta; template; tags; tribe_events_cat; force | Discovered type or taxonomy `tribe_events`: schema-built (section 12) | no |
| `/wp/v2/tribe_events/(?P<id>[\d]+)/autosaves` | GET, POST | parent; date; date_gmt; slug; status (publish / future / draft / pending / private / wc-pending / wc-processing / wc-on-hold / wc-completed / wc-cancelled / wc-refunded / wc-failed / wc-checkout-draft / tribe-ea-success and 5 more); password; title; content; author; excerpt; featured_media; meta; template; tags; tribe_events_cat | Discovered type or taxonomy `tribe_events`: schema-built (section 12) | no |
| `/wp/v2/tribe_events/(?P<parent>[\d]+)/autosaves/(?P<id>[\d]+)` | GET | parent; id | Discovered type or taxonomy `tribe_events`: schema-built (section 12) | no |
| `/wp/v2/tribe_events/(?P<parent>[\d]+)/revisions` | GET | parent; search; exclude; include; order (asc / desc); orderby (date / id / include / relevance / slug / include_slugs / title) | Discovered type or taxonomy `tribe_events`: schema-built (section 12) | no |
| `/wp/v2/tribe_events/(?P<parent>[\d]+)/revisions/(?P<id>[\d]+)` | GET, DELETE | parent; id; force | Discovered type or taxonomy `tribe_events`: schema-built (section 12) | no |
| `/wp/v2/tribe_events_cat` | GET, POST | search; exclude; include; order (asc / desc); orderby (id / include / name / slug / include_slugs / term_group / description / count); hide_empty; parent; post; slug; description; name; meta | Discovered type or taxonomy `tribe_events_cat`: schema-built (section 12) | no |
| `/wp/v2/tribe_events_cat/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; description; name; slug; parent; meta; force | Discovered type or taxonomy `tribe_events_cat`: schema-built (section 12) | no |
| `/wp/v2/tribe_organizer` | GET, POST | search; after; modified_after; author; author_exclude; before; modified_before; exclude; include; search_semantics (exact); order (asc / desc); orderby (author / date / id / include / modified / parent / relevance / slug / include_slugs / title); search_columns (post_title / post_content / post_excerpt); slug; status (publish / future / draft / pending / private / trash / auto-draft / inherit / request-pending / request-confirmed / request-failed / request-completed / wc-pending / wc-processing and 13 more); date; date_gmt; status (publish / future / draft / pending / private / wc-pending / wc-processing / wc-on-hold / wc-completed / wc-cancelled / wc-refunded / wc-failed / wc-checkout-draft / tribe-ea-success and 5 more); password; title; content; excerpt; featured_media; meta; template | Discovered type or taxonomy `tribe_organizer`: schema-built (section 12) | no |
| `/wp/v2/tribe_organizer/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; excerpt_length; password; date; date_gmt; slug; status (publish / future / draft / pending / private / wc-pending / wc-processing / wc-on-hold / wc-completed / wc-cancelled / wc-refunded / wc-failed / wc-checkout-draft / tribe-ea-success and 5 more); title; content; author; excerpt; featured_media; meta; template; force | Discovered type or taxonomy `tribe_organizer`: schema-built (section 12) | no |
| `/wp/v2/tribe_organizer/(?P<id>[\d]+)/autosaves` | GET, POST | parent; date; date_gmt; slug; status (publish / future / draft / pending / private / wc-pending / wc-processing / wc-on-hold / wc-completed / wc-cancelled / wc-refunded / wc-failed / wc-checkout-draft / tribe-ea-success and 5 more); password; title; content; author; excerpt; featured_media; meta; template | Discovered type or taxonomy `tribe_organizer`: schema-built (section 12) | no |
| `/wp/v2/tribe_organizer/(?P<parent>[\d]+)/autosaves/(?P<id>[\d]+)` | GET | parent; id | Discovered type or taxonomy `tribe_organizer`: schema-built (section 12) | no |
| `/wp/v2/tribe_organizer/(?P<parent>[\d]+)/revisions` | GET | parent; search; exclude; include; order (asc / desc); orderby (date / id / include / relevance / slug / include_slugs / title) | Discovered type or taxonomy `tribe_organizer`: schema-built (section 12) | no |
| `/wp/v2/tribe_organizer/(?P<parent>[\d]+)/revisions/(?P<id>[\d]+)` | GET, DELETE | parent; id; force | Discovered type or taxonomy `tribe_organizer`: schema-built (section 12) | no |
| `/wp/v2/tribe_venue` | GET, POST | search; after; modified_after; author; author_exclude; before; modified_before; exclude; include; search_semantics (exact); order (asc / desc); orderby (author / date / id / include / modified / parent / relevance / slug / include_slugs / title); search_columns (post_title / post_content / post_excerpt); slug; status (publish / future / draft / pending / private / trash / auto-draft / inherit / request-pending / request-confirmed / request-failed / request-completed / wc-pending / wc-processing and 13 more); date; date_gmt; status (publish / future / draft / pending / private / wc-pending / wc-processing / wc-on-hold / wc-completed / wc-cancelled / wc-refunded / wc-failed / wc-checkout-draft / tribe-ea-success and 5 more); password; title; content; excerpt; featured_media; meta; template | Discovered type or taxonomy `tribe_venue`: schema-built (section 12) | no |
| `/wp/v2/tribe_venue/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; excerpt_length; password; date; date_gmt; slug; status (publish / future / draft / pending / private / wc-pending / wc-processing / wc-on-hold / wc-completed / wc-cancelled / wc-refunded / wc-failed / wc-checkout-draft / tribe-ea-success and 5 more); title; content; author; excerpt; featured_media; meta; template; force | Discovered type or taxonomy `tribe_venue`: schema-built (section 12) | no |
| `/wp/v2/tribe_venue/(?P<id>[\d]+)/autosaves` | GET, POST | parent; date; date_gmt; slug; status (publish / future / draft / pending / private / wc-pending / wc-processing / wc-on-hold / wc-completed / wc-cancelled / wc-refunded / wc-failed / wc-checkout-draft / tribe-ea-success and 5 more); password; title; content; author; excerpt; featured_media; meta; template | Discovered type or taxonomy `tribe_venue`: schema-built (section 12) | no |
| `/wp/v2/tribe_venue/(?P<parent>[\d]+)/autosaves/(?P<id>[\d]+)` | GET | parent; id | Discovered type or taxonomy `tribe_venue`: schema-built (section 12) | no |
| `/wp/v2/tribe_venue/(?P<parent>[\d]+)/revisions` | GET | parent; search; exclude; include; order (asc / desc); orderby (date / id / include / relevance / slug / include_slugs / title) | Discovered type or taxonomy `tribe_venue`: schema-built (section 12) | no |
| `/wp/v2/tribe_venue/(?P<parent>[\d]+)/revisions/(?P<id>[\d]+)` | GET, DELETE | parent; id; force | Discovered type or taxonomy `tribe_venue`: schema-built (section 12) | no |
| `/wp/v2/types` | GET | - | Discovery of every post type (section 12) | yes |
| `/wp/v2/types/(?P<type>[\w-]+)` | GET | type | Discovery of every post type (section 12) | yes |
| `/wp/v2/users` | GET, POST | search; exclude; include; order (asc / desc); orderby (id / include / name / registered_date / slug / include_slugs / email / url); slug; roles; capabilities; who (authors); has_published_posts; search_columns (email / name / id / username / slug); username; name; first_name; last_name; email; url; description; locale ( / en_US); nickname; password; meta; woocommerce_meta | People > Users; Account; application passwords | yes |
| `/wp/v2/users/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; username; name; first_name; last_name; email; url; description; locale ( / en_US); nickname; slug; roles; password; meta; woocommerce_meta; force; reassign | People > Users; Account; application passwords | yes |
| `/wp/v2/users/(?P<user_id>(?:[\d]+\|me))/application-passwords` | GET, POST, DELETE | app_id; name | People > Users; Account; application passwords | yes |
| `/wp/v2/users/(?P<user_id>(?:[\d]+\|me))/application-passwords/(?P<uuid>[\w\-]+)` | GET, POST, PUT, PATCH, DELETE | app_id; name | People > Users; Account; application passwords | yes |
| `/wp/v2/users/(?P<user_id>(?:[\d]+\|me))/application-passwords/introspect` | GET | - | People > Users; Account; application passwords | yes |
| `/wp/v2/users/me` | GET, POST, PUT, PATCH, DELETE | username; name; first_name; last_name; email; url; description; locale ( / en_US); nickname; slug; roles; password; meta; woocommerce_meta; force; reassign | People > Users; Account; application passwords | yes |
| `/wp/v2/view-config` | GET | kind; name | Discovered type or taxonomy `view-config`: schema-built (section 12) | no |
| `/wp/v2/widget-types` | GET | - | Appearance > Widgets and Sidebars | no |
| `/wp/v2/widget-types/(?P<id>[a-zA-Z0-9_-]+)` | GET | id | Appearance > Widgets and Sidebars | no |
| `/wp/v2/widget-types/(?P<id>[a-zA-Z0-9_-]+)/encode` | POST | id; instance; form_data | Appearance > Widgets and Sidebars | no |
| `/wp/v2/widget-types/(?P<id>[a-zA-Z0-9_-]+)/render` | POST | id; instance | Appearance > Widgets and Sidebars | no |
| `/wp/v2/widgets` | GET, POST | sidebar; id; id_base; instance; form_data | Appearance > Widgets and Sidebars | yes |
| `/wp/v2/widgets/(?P<id>[\w\-]+)` | GET, POST, PUT, PATCH, DELETE | id; id_base; sidebar; instance; form_data; force | Appearance > Widgets and Sidebars | yes |
| `/wp/v2/wp_pattern_category` | GET, POST | search; exclude; include; order (asc / desc); orderby (id / include / name / slug / include_slugs / term_group / description / count); hide_empty; post; slug; description; name; meta | Appearance > Patterns (categories) | yes |
| `/wp/v2/wp_pattern_category/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; description; name; slug; meta; force | Appearance > Patterns (categories) | yes |

### D: `(index)` (2 routes)

Home: Discovery: the index itself.

| Route | Methods | Arguments | Home | QUILL today |
|---|---|---|---|---|
| `/` | GET | - | - | no |
| `/batch/v1` | POST | validation (require-all-validate / normal); requests | - | no |

### D: `baf/v1` (12 routes)

Home: To identify: a plugin namespace on the test site; schema-built until known.

| Route | Methods | Arguments | Home | QUILL today |
|---|---|---|---|---|
| `/baf/v1` | GET | namespace | - | yes |
| `/baf/v1/bfl/compile` | POST | - | - | yes |
| `/baf/v1/bfl/format` | POST | - | - | yes |
| `/baf/v1/bfl/parse` | POST | - | - | yes |
| `/baf/v1/bfl/validate` | POST | - | - | yes |
| `/baf/v1/cascade/(?P<cascade_id>[a-zA-Z0-9_-]+)` | GET | cascade_id; parent_value | - | yes |
| `/baf/v1/entries` | GET, POST | search; status (draft / active / inactive); orderby; order (ASC / DESC); form_id; starred | - | yes |
| `/baf/v1/entries/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | - | - | yes |
| `/baf/v1/forms` | GET, POST | search; status (draft / active / inactive); orderby; order (ASC / DESC); title; description; config; bfl_source; settings | - | yes |
| `/baf/v1/forms/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; title; description; config; bfl_source; status (draft / active / inactive); settings | - | yes |
| `/baf/v1/submit/(?P<form_id>[\d]+)` | POST | - | - | yes |
| `/baf/v1/views` | GET | - | - | yes |

### D: `jetpack/v4` (18 routes)

Home: Sites > site > Jetpack (modules on and off, connection, stats where exposed).

| Route | Methods | Arguments | Home | QUILL today |
|---|---|---|---|---|
| `/jetpack/v4` | GET | namespace | - | no |
| `/jetpack/v4/connection` | GET, POST, PUT, PATCH | isActive | - | no |
| `/jetpack/v4/connection/authorize_url` | GET | redirect_uri | - | no |
| `/jetpack/v4/connection/check` | GET | - | - | no |
| `/jetpack/v4/connection/data` | GET | - | - | no |
| `/jetpack/v4/connection/owner` | POST, PUT, PATCH | owner | - | no |
| `/jetpack/v4/connection/plugins` | GET | - | - | no |
| `/jetpack/v4/connection/reconnect` | POST, PUT, PATCH | - | - | no |
| `/jetpack/v4/connection/register` | POST, PUT, PATCH | from; redirect_uri; plugin_slug | - | no |
| `/jetpack/v4/connection/user` | POST, PUT, PATCH | - | - | no |
| `/jetpack/v4/heartbeat/data` | GET | prefix | - | no |
| `/jetpack/v4/remote_authorize` | POST, PUT, PATCH | - | - | no |
| `/jetpack/v4/remote_connect` | POST, PUT, PATCH | - | - | no |
| `/jetpack/v4/remote_provision` | POST, PUT, PATCH | - | - | no |
| `/jetpack/v4/remote_register` | POST, PUT, PATCH | - | - | no |
| `/jetpack/v4/user-token` | POST, PUT, PATCH | user_token; is_connection_owner | - | no |
| `/jetpack/v4/verify_registration` | POST, PUT, PATCH | - | - | no |
| `/jetpack/v4/verify_xmlrpc_error` | POST | nonce | - | no |

### D: `oembed/1.0` (3 routes)

Home: Editor plumbing: embeds (Name Embeds).

| Route | Methods | Arguments | Home | QUILL today |
|---|---|---|---|---|
| `/oembed/1.0` | GET | namespace | - | yes |
| `/oembed/1.0/embed` | GET | url; format; maxwidth | - | yes |
| `/oembed/1.0/proxy` | GET | url; format (json / xml); maxwidth; maxheight; discover | - | yes |

### D: `tec/migrations/v1` (6 routes)

Home: Out of scope: data migrations.

| Route | Methods | Arguments | Home | QUILL today |
|---|---|---|---|---|
| `/tec/migrations/v1` | GET | namespace | - | no |
| `/tec/migrations/v1/executions/(?P<execution_id>\d+)/logs` | GET | execution_id; type; not-type; search; limit; order (ASC / DESC); order-by (id / type / created_at) | - | no |
| `/tec/migrations/v1/migrations` | GET | tags | - | no |
| `/tec/migrations/v1/migrations/(?P<migration_id>[a-zA-Z0-9_-]+)/executions` | GET | migration_id | - | no |
| `/tec/migrations/v1/migrations/(?P<migration_id>[a-zA-Z0-9_-]+)/rollback` | POST | migration_id; from-batch; to-batch; batch-size | - | no |
| `/tec/migrations/v1/migrations/(?P<migration_id>[a-zA-Z0-9_-]+)/run` | POST | migration_id; from-batch; to-batch; batch-size | - | no |

### D: `tec/v1` (8 routes)

Home: Events: settings and tickets where offered.

| Route | Methods | Arguments | Home | QUILL today |
|---|---|---|---|---|
| `/tec/v1` | GET | namespace | - | no |
| `/tec/v1/docs` | GET | - | - | no |
| `/tec/v1/events` | GET, POST | start_date; end_date; search; categories; tags; venue; organizer; featured; status (publish / pending / draft / future / private); post_parent; starts_before; starts_after; ends_before; ends_after; ticketed; orderby (date / event_date / title / menu_order / modified); order (ASC / DESC); date; date_gmt; slug; title; content; excerpt; author; featured_media; comment_status (open / closed); ping_status (open / closed); format (standard / aside / chat / gallery / link / image / quote / status / video / audio); sticky; template; tribe_events_cat; start_date_utc; end_date_utc; timezone; duration; all_day; cost; organizers; venues | - | no |
| `/tec/v1/events/(?P<id>\d+)` | GET, PUT, PATCH, DELETE | date; date_gmt; slug; status (publish / pending / draft / future / private); title; content; excerpt; author; featured_media; comment_status (open / closed); ping_status (open / closed); format (standard / aside / chat / gallery / link / image / quote / status / video / audio); sticky; template; tags; tribe_events_cat; start_date; start_date_utc; end_date; end_date_utc; timezone; duration; all_day; featured; cost; organizers; venues; force | - | no |
| `/tec/v1/organizers` | GET, POST | search; event; has_events; only_with_upcoming; status (publish / pending / draft / future / private); date; date_gmt; slug; title; content; excerpt; author; featured_media; comment_status (open / closed); ping_status (open / closed); format (standard / aside / chat / gallery / link / image / quote / status / video / audio); sticky; template; tags; phone; website; email | - | no |
| `/tec/v1/organizers/(?P<id>\d+)` | GET, PUT, PATCH, DELETE | date; date_gmt; slug; status (publish / pending / draft / future / private); title; content; excerpt; author; featured_media; comment_status (open / closed); ping_status (open / closed); format (standard / aside / chat / gallery / link / image / quote / status / video / audio); sticky; template; tags; phone; website; email; force | - | no |
| `/tec/v1/venues` | GET, POST | search; event; has_events; only_with_upcoming; status (publish / pending / draft / future / private); date; date_gmt; slug; title; content; excerpt; author; featured_media; comment_status (open / closed); ping_status (open / closed); format (standard / aside / chat / gallery / link / image / quote / status / video / audio); sticky; template; tags; address; country; city; state_province; state; province; zip; phone; website | - | no |
| `/tec/v1/venues/(?P<id>\d+)` | GET, PUT, PATCH, DELETE | date; date_gmt; slug; status (publish / pending / draft / future / private); title; content; excerpt; author; featured_media; comment_status (open / closed); ping_status (open / closed); format (standard / aside / chat / gallery / link / image / quote / status / video / audio); sticky; template; tags; address; country; city; state_province; state; province; zip; phone; website; force | - | no |

### D: `tec/v2/onboarding` (2 routes)

Home: Out of scope: setup wizard.

| Route | Methods | Arguments | Home | QUILL today |
|---|---|---|---|---|
| `/tec/v2/onboarding` | GET | namespace | - | no |
| `/tec/v2/onboarding/wizard` | POST | action_nonce | - | no |

### D: `tribe/event-aggregator/v1` (3 routes)

Home: Events > Imports (Event Aggregator).

| Route | Methods | Arguments | Home | QUILL today |
|---|---|---|---|---|
| `/tribe/event-aggregator/v1` | GET | namespace | - | no |
| `/tribe/event-aggregator/v1/import/(?P<import_id>\w+)/batch` | POST | import_id; batch_hash; status; percentage_complete; interval | - | no |
| `/tribe/event-aggregator/v1/import/(?P<import_id>\w+)/state` | POST | import_id; batch_hash; status (success / failed / pending); message; message_slug; percentage_complete | - | no |

### D: `tribe/events/v1` (15 routes)

Home: Sites > site > Events (The Events Calendar): events, venues, organizers, categories, tags.

| Route | Methods | Arguments | Home | QUILL today |
|---|---|---|---|---|
| `/tribe/events/v1` | GET | namespace | - | yes |
| `/tribe/events/v1/categories` | GET, POST | search; exclude; include; order; orderby; hide_empty; parent; post; event; slug; name; description | - | yes |
| `/tribe/events/v1/categories/(?P<id>\d+)` | GET, POST, PUT, PATCH, DELETE | id; name; description; slug; parent | - | yes |
| `/tribe/events/v1/doc` | GET | - | - | yes |
| `/tribe/events/v1/events` | GET, POST | start_date; end_date; starts_before; starts_after; ends_before; ends_after; strict_dates; search; categories; tags; venue; organizer; featured; status; geoloc; geoloc_lat; geoloc_lng; include; post_parent; ticketed; author; date; date_utc; title; description; slug; excerpt; timezone; all_day; image; cost; website; show_map; show_map_link; hide_from_listings; sticky | - | yes |
| `/tribe/events/v1/events/(?P<id>\d+)` | GET, DELETE, POST, PUT, PATCH | id; password; author; date; date_utc; title; description; slug; excerpt; status; timezone; all_day; start_date; end_date; image; cost; website; show_map; show_map_link; hide_from_listings; sticky; featured; categories; tags; venue; organizer | - | yes |
| `/tribe/events/v1/events/by-slug/(?P<slug>[^/]+)` | GET, DELETE, POST, PUT, PATCH | slug; author; date; date_utc; title; description; excerpt; status; timezone; all_day; start_date; end_date; image; cost; website; show_map; show_map_link; hide_from_listings; sticky; featured; categories; tags; venue; organizer | - | yes |
| `/tribe/events/v1/organizers` | GET, POST | search; event; has_events; only_with_upcoming; status; author; date; date_utc; organizer; description; phone; website; email; image | - | yes |
| `/tribe/events/v1/organizers/(?P<id>\d+)` | GET, DELETE, POST, PUT, PATCH | id; author; date; date_utc; organizer; description; status; phone; website; email; image | - | yes |
| `/tribe/events/v1/organizers/by-slug/(?P<slug>[^/]+)` | GET, DELETE, POST, PUT, PATCH | slug; author; date; date_utc; organizer; description; status; phone; website; email; image | - | yes |
| `/tribe/events/v1/tags` | GET, POST | search; exclude; include; order; orderby; hide_empty; post; event; slug; name; description | - | yes |
| `/tribe/events/v1/tags/(?P<id>\d+)` | GET, POST, PUT, PATCH, DELETE | id; name; description; slug | - | yes |
| `/tribe/events/v1/venues` | GET, POST | search; event; has_events; only_with_upcoming; status; author; date; date_utc; venue; description; show_map; show_map_link; address; city; country; province; state; zip; phone; stateprovince; website; image | - | yes |
| `/tribe/events/v1/venues/(?P<id>\d+)` | GET, DELETE, POST, PUT, PATCH | id; author; date; date_utc; venue; description; status; show_map; show_map_link; address; city; country; province; state; zip; phone; stateprovince; website; image | - | yes |
| `/tribe/events/v1/venues/by-slug/(?P<slug>[^/]+)` | GET, DELETE, POST, PUT, PATCH | slug; author; date; date_utc; venue; description; status; show_map; show_map_link; address; city; country; province; state; zip; phone; stateprovince; website; image | - | yes |

### D: `tribe/views/v2` (2 routes)

Home: Out of scope: the calendar's front-end views.

| Route | Methods | Arguments | Home | QUILL today |
|---|---|---|---|---|
| `/tribe/views/v2` | GET | namespace | - | no |
| `/tribe/views/v2/html` | GET, POST | u; view; tvn1; tvn2; view_data; action | - | no |

### D: `wc-admin` (97 routes)

Home: Shop > Reports and Analytics (read-only tables); shop onboarding and notes.

| Route | Methods | Arguments | Home | QUILL today |
|---|---|---|---|---|
| `/wc-admin` | GET | namespace | - | no |
| `/wc-admin/blueprint/export` | POST | steps | - | no |
| `/wc-admin/blueprint/import-allowed` | GET | - | - | no |
| `/wc-admin/blueprint/import-step` | POST | step_definition | - | no |
| `/wc-admin/experiments/assignment` | GET | - | - | no |
| `/wc-admin/features` | GET | - | - | no |
| `/wc-admin/launch-your-store/initialize-coming-soon` | POST | - | - | no |
| `/wc-admin/launch-your-store/survey-completed` | GET | - | - | no |
| `/wc-admin/launch-your-store/update-survey-status` | POST | status (yes / no) | - | no |
| `/wc-admin/launch-your-store/woopayments/test-orders` | DELETE | - | - | no |
| `/wc-admin/launch-your-store/woopayments/test-orders/count` | GET | - | - | no |
| `/wc-admin/marketing/campaign-types` | GET | - | - | no |
| `/wc-admin/marketing/campaigns` | GET | - | - | no |
| `/wc-admin/marketing/channels` | GET | - | - | no |
| `/wc-admin/marketing/knowledge-base` | GET | category | - | no |
| `/wc-admin/marketing/misc-recommendations` | GET | - | - | no |
| `/wc-admin/marketing/overview/activate-plugin` | POST, PUT, PATCH | plugin | - | no |
| `/wc-admin/marketing/overview/installed-plugins` | GET | - | - | no |
| `/wc-admin/marketing/recommendations` | GET | category (channels / extensions) | - | no |
| `/wc-admin/marketing/recommended` | GET | category | - | no |
| `/wc-admin/marketplace-promotions/dismiss` | POST | id | - | no |
| `/wc-admin/mobile-app` | GET | - | - | no |
| `/wc-admin/mobile-app/qr-login-approve` | POST | token; choice | - | no |
| `/wc-admin/mobile-app/qr-login-availability` | GET | - | - | no |
| `/wc-admin/mobile-app/qr-login-exchange` | POST | token; exchange_grant | - | no |
| `/wc-admin/mobile-app/qr-login-revoke` | DELETE | uuid | - | no |
| `/wc-admin/mobile-app/qr-login-scan` | POST | token; device; supports_number_matching | - | no |
| `/wc-admin/mobile-app/qr-login-session-status` | GET | session_id; token_hash | - | no |
| `/wc-admin/mobile-app/qr-login-status` | POST | token | - | no |
| `/wc-admin/mobile-app/qr-login-token` | POST | - | - | no |
| `/wc-admin/mobile-app/send-magic-link` | GET | - | - | no |
| `/wc-admin/notice/dismiss` | POST | - | - | no |
| `/wc-admin/onboarding/free-extensions` | GET | - | - | no |
| `/wc-admin/onboarding/plugins/install-and-activate` | POST | - | - | no |
| `/wc-admin/onboarding/plugins/install-and-activate-async` | POST | plugins; source | - | no |
| `/wc-admin/onboarding/plugins/jetpack-authorization-url` | GET | redirect_url; from | - | no |
| `/wc-admin/onboarding/plugins/scheduled-installs/(?P<job_id>\w+)` | GET | - | - | no |
| `/wc-admin/onboarding/product-types` | GET | - | - | no |
| `/wc-admin/onboarding/products` | POST | - | - | no |
| `/wc-admin/onboarding/profile` | GET, POST, PUT, PATCH | completed; skipped; industry; business_extensions; is_agree_marketing; store_email; is_store_country_set; is_plugins_page_skipped; business_choice; selling_online_answer; selling_platforms | - | no |
| `/wc-admin/onboarding/profile/experimental_get_email_prefill` | GET | - | - | no |
| `/wc-admin/onboarding/profile/progress` | GET | - | - | no |
| `/wc-admin/onboarding/profile/progress/core-profiler/complete` | POST, PUT, PATCH | step (intro-opt-in / skip-guided-setup / user-profile / business-info / plugins / intro-builder / skip-guided-setup) | - | no |
| `/wc-admin/onboarding/profile/update-store-currency-and-measurement-units` | POST | country_code | - | no |
| `/wc-admin/onboarding/tasks` | GET, POST | ids (setup / extended / secret_tasklist); extended_tasks | - | no |
| `/wc-admin/onboarding/tasks/(?P<id>[a-z0-9_-]+)/snooze` | POST | duration; task_list_id | - | no |
| `/wc-admin/onboarding/tasks/(?P<id>[a-z0-9_\-]+)/action` | POST, PUT, PATCH | - | - | no |
| `/wc-admin/onboarding/tasks/(?P<id>[a-z0-9_\-]+)/dismiss` | POST, PUT, PATCH | task_list_id | - | no |
| `/wc-admin/onboarding/tasks/(?P<id>[a-z0-9_\-]+)/hide` | POST, PUT, PATCH | - | - | no |
| `/wc-admin/onboarding/tasks/(?P<id>[a-z0-9_\-]+)/undo_dismiss` | POST, PUT, PATCH | task_list_id | - | no |
| `/wc-admin/onboarding/tasks/(?P<id>[a-z0-9_\-]+)/undo_snooze` | POST, PUT, PATCH | - | - | no |
| `/wc-admin/onboarding/tasks/(?P<id>[a-z0-9_\-]+)/unhide` | POST, PUT, PATCH | - | - | no |
| `/wc-admin/onboarding/tasks/create_homepage` | POST | - | - | no |
| `/wc-admin/onboarding/tasks/create_product_from_template` | POST | template_name | - | no |
| `/wc-admin/onboarding/tasks/import_sample_products` | POST | - | - | no |
| `/wc-admin/onboarding/themes/activate` | POST, PUT, PATCH | - | - | no |
| `/wc-admin/onboarding/themes/install` | POST, PUT, PATCH | - | - | no |
| `/wc-admin/options` | GET, POST, PUT, PATCH | - | - | no |
| `/wc-admin/payment-gateway-suggestions` | GET | force_default_suggestions | - | no |
| `/wc-admin/payment-gateway-suggestions/dismiss` | POST | - | - | no |
| `/wc-admin/plugins/activate` | POST, PUT, PATCH | - | - | no |
| `/wc-admin/plugins/activate/status` | GET | - | - | no |
| `/wc-admin/plugins/activate/status/(?P<job_id>[a-z0-9_\-]+)` | GET | - | - | no |
| `/wc-admin/plugins/active` | GET | - | - | no |
| `/wc-admin/plugins/connect-jetpack` | GET | - | - | no |
| `/wc-admin/plugins/connect-square` | POST, PUT, PATCH | - | - | no |
| `/wc-admin/plugins/connect-wcpay` | POST, PUT, PATCH | - | - | no |
| `/wc-admin/plugins/finish-wccom-connect` | POST | - | - | no |
| `/wc-admin/plugins/install` | POST, PUT, PATCH | - | - | no |
| `/wc-admin/plugins/install/status` | GET | - | - | no |
| `/wc-admin/plugins/install/status/(?P<job_id>[a-z0-9_\-]+)` | GET | - | - | no |
| `/wc-admin/plugins/installed` | GET | - | - | no |
| `/wc-admin/plugins/request-wccom-connect` | POST | - | - | no |
| `/wc-admin/settings/payments/country` | POST, PUT, PATCH | location | - | no |
| `/wc-admin/settings/payments/providers` | POST | location | - | no |
| `/wc-admin/settings/payments/providers/order` | POST, PUT, PATCH | order_map | - | no |
| `/wc-admin/settings/payments/suggestion/(?P<id>[\w\d\-]+)/attach` | POST, PUT, PATCH | - | - | no |
| `/wc-admin/settings/payments/suggestion/(?P<id>[\w\d\-]+)/hide` | POST, PUT, PATCH | - | - | no |
| `/wc-admin/settings/payments/suggestion/(?P<suggestion_id>[\w\d\-]+)/incentive/(?P<incentive_id>[\w\d\-]+)/dismiss` | POST, PUT, PATCH | do_not_track | - | no |
| `/wc-admin/settings/payments/woopayments/onboarding` | POST | location; source | - | no |
| `/wc-admin/settings/payments/woopayments/onboarding/preload` | POST | location | - | no |
| `/wc-admin/settings/payments/woopayments/onboarding/reset` | POST | location; from; source | - | no |
| `/wc-admin/settings/payments/woopayments/onboarding/step/(?P<step>[a-zA-Z0-9_-]+)/check` | POST | location | - | no |
| `/wc-admin/settings/payments/woopayments/onboarding/step/(?P<step>[a-zA-Z0-9_-]+)/clean` | POST | location | - | no |
| `/wc-admin/settings/payments/woopayments/onboarding/step/(?P<step>[a-zA-Z0-9_-]+)/finish` | POST | location; source | - | no |
| `/wc-admin/settings/payments/woopayments/onboarding/step/(?P<step>[a-zA-Z0-9_-]+)/save` | POST | location; source | - | no |
| `/wc-admin/settings/payments/woopayments/onboarding/step/(?P<step>[a-zA-Z0-9_-]+)/start` | POST | location; source | - | no |
| `/wc-admin/settings/payments/woopayments/onboarding/step/business_verification/kyc_session` | POST | location; source | - | no |
| `/wc-admin/settings/payments/woopayments/onboarding/step/business_verification/kyc_session/finish` | POST | location; source | - | no |
| `/wc-admin/settings/payments/woopayments/onboarding/step/business_verification/test_account/disable` | POST | location; from; source | - | no |
| `/wc-admin/settings/payments/woopayments/onboarding/step/test_account/init` | POST | location; source | - | no |
| `/wc-admin/settings/payments/woopayments/onboarding/step/test_account/reset` | POST | location; source | - | no |
| `/wc-admin/settings/payments/woopayments/onboarding/test_account/disable` | POST | location; from; source | - | no |
| `/wc-admin/settings/payments/woopayments/woopay-eligibility` | POST | - | - | no |
| `/wc-admin/shipping-partner-suggestions` | GET | force_default_suggestions | - | no |
| `/wc-admin/tax/recommendations/dismiss` | POST | - | - | no |
| `/wc-admin/themes` | POST, PUT, PATCH | pluginzip | - | no |

### D: `wc-admin-email` (5 routes)

Home: Shop > Settings > Emails.

| Route | Methods | Arguments | Home | QUILL today |
|---|---|---|---|---|
| `/wc-admin-email` | GET | namespace | - | no |
| `/wc-admin-email/settings/email/listing/recreate-email-post` | POST | email_id | - | no |
| `/wc-admin-email/settings/email/preview-subject` | GET | type | - | no |
| `/wc-admin-email/settings/email/save-transient` | POST | key; value | - | no |
| `/wc-admin-email/settings/email/send-preview` | POST | type; email | - | no |

### D: `wc-analytics` (89 routes)

Home: Shop > Reports and Analytics (read-only tables).

| Route | Methods | Arguments | Home | QUILL today |
|---|---|---|---|---|
| `/wc-analytics` | GET | namespace | - | no |
| `/wc-analytics/activity-panel/counts` | GET | order_statuses; review_status; product_status | - | no |
| `/wc-analytics/admin/notes` | GET | order (asc / desc); orderby (note_id / date / type / title / status); type (error / warning / update / info / marketing / survey); status (pending / actioned / unactioned / snoozed / sent); source | - | no |
| `/wc-analytics/admin/notes/(?P<id>[\d-]+)` | GET, POST, PUT, PATCH | id | - | no |
| `/wc-analytics/admin/notes/(?P<note_id>[\d-]+)/action/(?P<action_id>[\d-]+)` | POST, PUT, PATCH | note_id; action_id | - | no |
| `/wc-analytics/admin/notes/delete/(?P<id>[\d-]+)` | DELETE | - | - | no |
| `/wc-analytics/admin/notes/delete/all` | DELETE | status (pending / actioned / unactioned / snoozed / sent) | - | no |
| `/wc-analytics/admin/notes/experimental-activate-promo/(?P<promo_note_name>[\w-]+)` | POST, PUT, PATCH | - | - | no |
| `/wc-analytics/admin/notes/update` | POST, PUT, PATCH | - | - | no |
| `/wc-analytics/coupons` | GET, POST | search; after; before; modified_after; modified_before; dates_are_gmt; exclude; include; order (asc / desc); orderby (date / id / include / title / slug / modified); code; amount; status; discount_type (percent / fixed_cart / fixed_product); description; date_expires; date_expires_gmt; individual_use; product_ids; excluded_product_ids; usage_limit; usage_limit_per_user; limit_usage_to_x_items; free_shipping; product_categories; excluded_product_categories; exclude_sale_items; minimum_amount; maximum_amount; email_restrictions; meta_data | - | no |
| `/wc-analytics/coupons/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; code; amount; status; discount_type (percent / fixed_cart / fixed_product); description; date_expires; date_expires_gmt; individual_use; product_ids; excluded_product_ids; usage_limit; usage_limit_per_user; limit_usage_to_x_items; free_shipping; product_categories; excluded_product_categories; exclude_sale_items; minimum_amount; maximum_amount; email_restrictions; meta_data; force | - | no |
| `/wc-analytics/coupons/batch` | POST, PUT, PATCH | code; amount; status; discount_type (percent / fixed_cart / fixed_product); description; date_expires; date_expires_gmt; individual_use; product_ids; excluded_product_ids; usage_limit; usage_limit_per_user; limit_usage_to_x_items; free_shipping; product_categories; excluded_product_categories; exclude_sale_items; minimum_amount; maximum_amount; email_restrictions; meta_data | - | no |
| `/wc-analytics/customers` | GET | after; before; order (asc / desc); orderby (username / name / first_name / last_name / email / location / country / city / state / postcode / date_registered / date_last_active / orders_count / total_spend and 1 more); force_cache_refresh; registered_before; registered_after; match (all / any); search; searchby (name / username / email / all); name_includes; name_excludes; username_includes; username_excludes; email_includes; email_excludes; country_includes; country_excludes; last_active_before; last_active_after; last_active_between; registered_between; orders_count_min; orders_count_max; orders_count_between; total_spend_min; total_spend_max; total_spend_between; avg_order_value_min; avg_order_value_max; avg_order_value_between; last_order_before; last_order_after; customers_exclude; users; filter_empty (email / name / country / city / state / postcode); user_type (all / registered / guest); location_includes; location_excludes; include | - | no |
| `/wc-analytics/customers/(?P<id>[\d-]+)` | GET | id; after; before; order (asc / desc); orderby (username / name / first_name / last_name / email / location / country / city / state / postcode / date_registered / date_last_active / orders_count / total_spend and 1 more); force_cache_refresh; registered_before; registered_after; match (all / any); search; searchby (name / username / email / all); name_includes; name_excludes; username_includes; username_excludes; email_includes; email_excludes; country_includes; country_excludes; last_active_before; last_active_after; last_active_between; registered_between; orders_count_min; orders_count_max; orders_count_between; total_spend_min; total_spend_max; total_spend_between; avg_order_value_min; avg_order_value_max; avg_order_value_between; last_order_before; last_order_after; customers_exclude; users; filter_empty (email / name / country / city / state / postcode); user_type (all / registered / guest); location_includes; location_excludes; include | - | no |
| `/wc-analytics/data` | GET | - | - | no |
| `/wc-analytics/data/countries` | GET | - | - | no |
| `/wc-analytics/data/countries/(?P<location>[\w-]+)` | GET | location | - | no |
| `/wc-analytics/data/countries/locales` | GET | - | - | no |
| `/wc-analytics/data/download-ips` | GET | - | - | no |
| `/wc-analytics/imports/retry-failed` | POST | - | - | no |
| `/wc-analytics/imports/status` | GET | - | - | no |
| `/wc-analytics/imports/trigger` | POST | - | - | no |
| `/wc-analytics/leaderboards` | GET | after; before; persisted_query | - | no |
| `/wc-analytics/leaderboards/(?P<leaderboard>\w+)` | GET | leaderboard (customers / coupons / categories / products); after; before; persisted_query | - | no |
| `/wc-analytics/leaderboards/allowed` | GET | - | - | no |
| `/wc-analytics/orders` | GET, POST | search; after; before; modified_after; modified_before; dates_are_gmt; exclude; include; order (asc / desc); orderby (date / id / include / title / slug / modified); parent; parent_exclude; status (any / trash / pending / processing / on-hold / completed / cancelled / refunded / failed / checkout-draft); customer; product; dp; order_item_display_meta; include_meta; exclude_meta; created_via; number; parent_id; status (auto-draft / pending / processing / on-hold / completed / cancelled / refunded / failed / checkout-draft); currency (AED / AFN / ALL / AMD / ANG / AOA / ARS / AUD / AWG / AZN / BAM / BBD / BDT / BGN and 150 more); customer_id; customer_note; billing; shipping; payment_method; payment_method_title; transaction_id; meta_data; line_items; shipping_lines; fee_lines; coupon_lines; set_paid; manual_update | - | no |
| `/wc-analytics/orders/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; parent_id; created_via; status (auto-draft / pending / processing / on-hold / completed / cancelled / refunded / failed / checkout-draft); currency (AED / AFN / ALL / AMD / ANG / AOA / ARS / AUD / AWG / AZN / BAM / BBD / BDT / BGN and 150 more); customer_id; customer_note; billing; shipping; payment_method; payment_method_title; transaction_id; meta_data; line_items; shipping_lines; fee_lines; coupon_lines; set_paid; manual_update; force | - | no |
| `/wc-analytics/orders/batch` | POST, PUT, PATCH | parent_id; created_via; status (auto-draft / pending / processing / on-hold / completed / cancelled / refunded / failed / checkout-draft); currency (AED / AFN / ALL / AMD / ANG / AOA / ARS / AUD / AWG / AZN / BAM / BBD / BDT / BGN and 150 more); customer_id; customer_note; billing; shipping; payment_method; payment_method_title; transaction_id; meta_data; line_items; shipping_lines; fee_lines; coupon_lines; set_paid; manual_update | - | no |
| `/wc-analytics/products` | GET, POST | search; after; before; modified_after; modified_before; dates_are_gmt; exclude; include; order (asc / desc); orderby (date / id / include / title / slug / modified / popularity / rating / post__in / price / sales / menu_order / random / popularity and 5 more); parent; parent_exclude; brand; slug; status (any / future / trash / draft / pending / private / publish); type (simple / grouped / external / variable); sku; featured; category; tag; shipping_class; attribute; attribute_term; on_sale; min_price; max_price; include_meta; exclude_meta; image_size; stock_status (instock / outofstock / onbackorder); search_sku; search_name_or_sku; search_fields (name / global_unique_id / description / short_description / sku); include_status (any / future / trash / draft / pending / private / publish); exclude_status (future / trash / draft / pending / private / publish); include_types (simple / grouped / external / variable); exclude_types (simple / grouped / external / variable); downloadable; virtual; pos_products_only; low_in_stock; name; date_created; date_created_gmt; status (draft / pending / private / publish / future / auto-draft / trash); catalog_visibility (visible / catalog / search / hidden); description; short_description; global_unique_id; regular_price; sale_price; date_on_sale_from; date_on_sale_from_gmt; date_on_sale_to; date_on_sale_to_gmt; downloads; download_limit; download_expiry; external_url; button_text; tax_status (taxable / shipping / none); tax_class; manage_stock; stock_quantity; backorders (no / notify / yes); low_stock_amount; sold_individually; weight; dimensions; reviews_allowed; post_password; upsell_ids; cross_sell_ids; parent_id; purchase_note; categories; brands; tags; images; attributes; default_attributes; menu_order; meta_data | - | no |
| `/wc-analytics/products/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; image_size; name; slug; date_created; date_created_gmt; type (simple / grouped / external / variable); status (draft / pending / private / publish / future / auto-draft / trash); featured; catalog_visibility (visible / catalog / search / hidden); description; short_description; sku; global_unique_id; regular_price; sale_price; date_on_sale_from; date_on_sale_from_gmt; date_on_sale_to; date_on_sale_to_gmt; virtual; downloadable; downloads; download_limit; download_expiry; external_url; button_text; tax_status (taxable / shipping / none); tax_class; manage_stock; stock_quantity; stock_status (instock / outofstock / onbackorder); backorders (no / notify / yes); low_stock_amount; sold_individually; weight; dimensions; shipping_class; reviews_allowed; post_password; upsell_ids; cross_sell_ids; parent_id; purchase_note; categories; brands; tags; images; attributes; default_attributes; menu_order; meta_data; force | - | no |
| `/wc-analytics/products/(?P<id>[\d]+)/duplicate` | POST | id; name; slug; date_created; date_created_gmt; type (simple / grouped / external / variable); status (draft / pending / private / publish / future / auto-draft / trash); featured; catalog_visibility (visible / catalog / search / hidden); description; short_description; sku; global_unique_id; regular_price; sale_price; date_on_sale_from; date_on_sale_from_gmt; date_on_sale_to; date_on_sale_to_gmt; virtual; downloadable; downloads; download_limit; download_expiry; external_url; button_text; tax_status (taxable / shipping / none); tax_class; manage_stock; stock_quantity; stock_status (instock / outofstock / onbackorder); backorders (no / notify / yes); low_stock_amount; sold_individually; weight; dimensions; shipping_class; reviews_allowed; post_password; upsell_ids; cross_sell_ids; parent_id; purchase_note; categories; brands; tags; images; attributes; default_attributes; menu_order; meta_data | - | no |
| `/wc-analytics/products/(?P<id>[\d]+)/related` | GET | id | - | no |
| `/wc-analytics/products/(?P<product_id>[\d]+)/variations` | GET, POST | product_id; search; after; before; modified_after; modified_before; dates_are_gmt; exclude; include; order (asc / desc); orderby (date / id / include / title / slug / modified / menu_order); parent; parent_exclude; slug; status (any / future / trash / draft / pending / private / publish); sku; on_sale; min_price; max_price; include_meta; exclude_meta; image_size; stock_status (instock / outofstock / onbackorder); has_price; attributes; virtual; downloadable; include_status (any / future / trash / draft / pending / private / publish); exclude_status (future / trash / draft / pending / private / publish); pos_products_only; type (variation); description; global_unique_id; regular_price; sale_price; date_on_sale_from; date_on_sale_from_gmt; date_on_sale_to; date_on_sale_to_gmt; status (draft / pending / private / publish); downloads; download_limit; download_expiry; tax_status (taxable / shipping / none); tax_class; manage_stock; stock_quantity; backorders (no / notify / yes); low_stock_amount; weight; dimensions; shipping_class; image; gallery_image_ids; menu_order; meta_data; parent_id; name | - | no |
| `/wc-analytics/products/(?P<product_id>[\d]+)/variations/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | product_id; id; image_size; type (variation); description; sku; global_unique_id; regular_price; sale_price; date_on_sale_from; date_on_sale_from_gmt; date_on_sale_to; date_on_sale_to_gmt; status (draft / pending / private / publish); virtual; downloadable; downloads; download_limit; download_expiry; tax_status (taxable / shipping / none); tax_class; manage_stock; stock_quantity; stock_status (instock / outofstock / onbackorder); backorders (no / notify / yes); low_stock_amount; weight; dimensions; shipping_class; image; gallery_image_ids; attributes; menu_order; meta_data; parent_id; name; force | - | no |
| `/wc-analytics/products/(?P<product_id>[\d]+)/variations/batch` | POST, PUT, PATCH | product_id; type (variation); description; sku; global_unique_id; regular_price; sale_price; date_on_sale_from; date_on_sale_from_gmt; date_on_sale_to; date_on_sale_to_gmt; status (draft / pending / private / publish); virtual; downloadable; downloads; download_limit; download_expiry; tax_status (taxable / shipping / none); tax_class; manage_stock; stock_quantity; stock_status (instock / outofstock / onbackorder); backorders (no / notify / yes); low_stock_amount; weight; dimensions; shipping_class; image; gallery_image_ids; attributes; menu_order; meta_data; parent_id; name | - | no |
| `/wc-analytics/products/(?P<product_id>[\d]+)/variations/generate` | POST | product_id; delete; default_values; type (variation); description; sku; global_unique_id; regular_price; sale_price; date_on_sale_from; date_on_sale_from_gmt; date_on_sale_to; date_on_sale_to_gmt; status (draft / pending / private / publish); virtual; downloadable; downloads; download_limit; download_expiry; tax_status (taxable / shipping / none); tax_class; manage_stock; stock_quantity; stock_status (instock / outofstock / onbackorder); backorders (no / notify / yes); low_stock_amount; weight; dimensions; shipping_class; image; gallery_image_ids; attributes; menu_order; meta_data; parent_id; name | - | no |
| `/wc-analytics/products/attributes` | GET, POST | search; name; slug; type (select); order_by (menu_order / name / name_num / id); has_archives | - | no |
| `/wc-analytics/products/attributes/(?P<attribute_id>[\d]+)/terms` | GET, POST | attribute_id; search; exclude; include; order (asc / desc); orderby (id / include / name / slug / term_group / description / count); hide_empty; parent; product; slug; name; description; menu_order | - | no |
| `/wc-analytics/products/attributes/(?P<attribute_id>[\d]+)/terms/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; attribute_id; name; slug; description; menu_order; force | - | no |
| `/wc-analytics/products/attributes/(?P<attribute_id>[\d]+)/terms/batch` | POST, PUT, PATCH | attribute_id; name; slug; description; menu_order | - | no |
| `/wc-analytics/products/attributes/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; name; slug; type (select); order_by (menu_order / name / name_num / id); has_archives; force | - | no |
| `/wc-analytics/products/attributes/(?P<slug>[a-z0-9_\-]+)` | GET | slug | - | no |
| `/wc-analytics/products/attributes/(?P<slug>[a-z0-9_\-]+)/terms` | GET | slug; search; exclude; include; order (asc / desc); orderby (id / include / name / slug / term_group / description / count); hide_empty; parent; product | - | no |
| `/wc-analytics/products/attributes/batch` | POST, PUT, PATCH | name; slug; type (select); order_by (menu_order / name / name_num / id); has_archives | - | no |
| `/wc-analytics/products/batch` | POST, PUT, PATCH | name; slug; date_created; date_created_gmt; type (simple / grouped / external / variable); status (draft / pending / private / publish / future / auto-draft / trash); featured; catalog_visibility (visible / catalog / search / hidden); description; short_description; sku; global_unique_id; regular_price; sale_price; date_on_sale_from; date_on_sale_from_gmt; date_on_sale_to; date_on_sale_to_gmt; virtual; downloadable; downloads; download_limit; download_expiry; external_url; button_text; tax_status (taxable / shipping / none); tax_class; manage_stock; stock_quantity; stock_status (instock / outofstock / onbackorder); backorders (no / notify / yes); low_stock_amount; sold_individually; weight; dimensions; shipping_class; reviews_allowed; post_password; upsell_ids; cross_sell_ids; parent_id; purchase_note; categories; brands; tags; images; attributes; default_attributes; menu_order; meta_data | - | no |
| `/wc-analytics/products/categories` | GET, POST | search; exclude; include; order (asc / desc); orderby (id / include / name / slug / term_group / description / count); hide_empty; parent; product; slug; name; description; display (default / products / subcategories / both); image | - | no |
| `/wc-analytics/products/categories/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; name; slug; parent; description; display (default / products / subcategories / both); image; force | - | no |
| `/wc-analytics/products/categories/batch` | POST, PUT, PATCH | name; slug; parent; description; display (default / products / subcategories / both); image | - | no |
| `/wc-analytics/products/count-low-in-stock` | GET | status (draft / pending / private / publish / future) | - | no |
| `/wc-analytics/products/low-in-stock` | GET | status (draft / pending / private / publish / future) | - | no |
| `/wc-analytics/products/reviews` | GET, POST | search; after; before; exclude; include; order (asc / desc); orderby (date / date_gmt / id / include / product); reviewer; reviewer_exclude; reviewer_email; product; status (all / hold / approved / spam / trash); product_id; product_name; status (approved / hold / spam / unspam / trash / untrash); review; rating | - | no |
| `/wc-analytics/products/reviews/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; product_id; product_name; status (approved / hold / spam / unspam / trash / untrash); reviewer; reviewer_email; review; rating; force | - | no |
| `/wc-analytics/products/reviews/batch` | POST, PUT, PATCH | product_id; product_name; status (approved / hold / spam / unspam / trash / untrash); reviewer; reviewer_email; review; rating | - | no |
| `/wc-analytics/products/suggested-products` | GET | search; after; before; modified_after; modified_before; dates_are_gmt; exclude; include; order (asc / desc); orderby (date / id / include / title / slug / modified / popularity / rating / post__in / price / sales / menu_order / random / popularity and 2 more); parent; parent_exclude; brand; slug; status (any / future / trash / draft / pending / private / publish); type (simple / grouped / external / variable); sku; featured; category; tag; shipping_class; attribute; attribute_term; in_stock; on_sale; min_price; max_price; include_meta; exclude_meta; image_size; categories; tags; limit | - | no |
| `/wc-analytics/reports` | GET | - | - | no |
| `/wc-analytics/reports/(?P<type>[a-z]+)/export` | POST, PUT, PATCH | report_args; email | - | no |
| `/wc-analytics/reports/(?P<type>[a-z]+)/export/(?P<export_id>[a-z0-9]+)/status` | GET | - | - | no |
| `/wc-analytics/reports/categories` | GET | after; before; order (asc / desc); orderby (category_id / items_sold / net_revenue / orders_count / products_count / category); force_cache_refresh; interval (hour / day / week / month / quarter / year); status_is (any / trash / pending / processing / on-hold / completed / cancelled / refunded / failed / checkout-draft); status_is_not (any / trash / pending / processing / on-hold / completed / cancelled / refunded / failed / checkout-draft); categories; extended_info | - | no |
| `/wc-analytics/reports/coupons` | GET | after; before; order (asc / desc); orderby (coupon_id / code / amount / orders_count); force_cache_refresh; coupons; extended_info | - | no |
| `/wc-analytics/reports/coupons/stats` | GET | after; before; order (asc / desc); orderby (date / amount / coupons_count / orders_count); force_cache_refresh; fields; interval (hour / day / week / month / quarter / year); coupons; segmentby (product / variation / category / coupon) | - | no |
| `/wc-analytics/reports/customers` | GET | after; before; order (asc / desc); orderby (username / name / first_name / last_name / email / location / country / city / state / postcode / date_registered / date_last_active / orders_count / total_spend and 1 more); force_cache_refresh; registered_before; registered_after; match (all / any); search; searchby (name / username / email / all); name_includes; name_excludes; username_includes; username_excludes; email_includes; email_excludes; country_includes; country_excludes; last_active_before; last_active_after; last_active_between; registered_between; orders_count_min; orders_count_max; orders_count_between; total_spend_min; total_spend_max; total_spend_between; avg_order_value_min; avg_order_value_max; avg_order_value_between; last_order_before; last_order_after; customers; customers_exclude; users; filter_empty (email / name / country / city / state / postcode); user_type (all / registered / guest); location_includes; location_excludes | - | no |
| `/wc-analytics/reports/customers/stats` | GET | registered_before; registered_after; match (all / any); search; searchby (name / username / email / all); name_includes; name_excludes; username_includes; username_excludes; email_includes; email_excludes; country_includes; country_excludes; last_active_before; last_active_after; last_active_between; registered_between; orders_count_min; orders_count_max; orders_count_between; total_spend_min; total_spend_max; total_spend_between; avg_order_value_min; avg_order_value_max; avg_order_value_between; last_order_before; last_order_after; customers; customers_exclude; fields; force_cache_refresh | - | no |
| `/wc-analytics/reports/downloads` | GET | after; before; order (asc / desc); orderby (date / product); force_cache_refresh; match (all / any); product_includes; product_excludes; order_includes; order_excludes; customer_includes; customer_excludes; ip_address_includes; ip_address_excludes | - | no |
| `/wc-analytics/reports/downloads/stats` | GET | after; before; order (asc / desc); orderby (date / download_count); force_cache_refresh; fields; interval (hour / day / week / month / quarter / year); match (all / any); product_includes; product_excludes; order_includes; order_excludes; customer_includes; customer_excludes; ip_address_includes; ip_address_excludes | - | no |
| `/wc-analytics/reports/import` | POST, PUT, PATCH | days; skip_existing | - | no |
| `/wc-analytics/reports/import/cancel` | POST, PUT, PATCH | - | - | no |
| `/wc-analytics/reports/import/delete` | POST, PUT, PATCH | - | - | no |
| `/wc-analytics/reports/import/status` | GET | - | - | no |
| `/wc-analytics/reports/import/totals` | GET | days; skip_existing | - | no |
| `/wc-analytics/reports/orders` | GET | after; before; order (asc / desc); orderby (date / num_items_sold / net_total); force_cache_refresh; product_includes; product_excludes; variation_includes; variation_excludes; coupon_includes; coupon_excludes; tax_rate_includes; tax_rate_excludes; status_is (any / trash / pending / processing / on-hold / completed / cancelled / refunded / failed / checkout-draft); status_is_not (any / trash / pending / processing / on-hold / completed / cancelled / refunded / failed / checkout-draft); customer_type ( / returning / new); refunds ( / all / partial / full / none); extended_info; order_includes; order_excludes; attribute_is; attribute_is_not | - | no |
| `/wc-analytics/reports/orders/stats` | GET | after; before; order (asc / desc); orderby (date / net_revenue / orders_count / avg_order_value); force_cache_refresh; interval (hour / day / week / month / quarter / year); match (all / any); status_is (any / trash / pending / processing / on-hold / completed / cancelled / refunded / failed / checkout-draft); status_is_not (any / trash / pending / processing / on-hold / completed / cancelled / refunded / failed / checkout-draft); product_includes; product_excludes; variation_includes; variation_excludes; coupon_includes; coupon_excludes; tax_rate_includes; tax_rate_excludes; customer (new / returning); customer_type (new / returning); refunds ( / all / partial / full / none); attribute_is; attribute_is_not; segmentby (product / category / variation / coupon / customer_type) | - | no |
| `/wc-analytics/reports/performance-indicators` | GET | stats; after; before | - | no |
| `/wc-analytics/reports/performance-indicators/allowed` | GET | stats; after; before | - | no |
| `/wc-analytics/reports/products` | GET | after; before; order (asc / desc); orderby (date / net_revenue / orders_count / items_sold / product_name / variations / sku); force_cache_refresh; categories; match (all / any); products; search; extended_info | - | no |
| `/wc-analytics/reports/products/stats` | GET | after; before; order (asc / desc); orderby (date / net_revenue / coupons / refunds / shipping / taxes / net_revenue / orders_count / items_sold); force_cache_refresh; fields; interval (hour / day / week / month / quarter / year); categories; products; variations; search; segmentby (product / category / variation) | - | no |
| `/wc-analytics/reports/revenue/stats` | GET | after; before; order (asc / desc); orderby (date / total_sales / coupons / refunds / shipping / taxes / net_revenue / orders_count / items_sold / gross_sales); force_cache_refresh; interval (hour / day / week / month / quarter / year); segmentby (product / category / variation / coupon / customer_type); date_type (date_paid / date_created / date_completed) | - | no |
| `/wc-analytics/reports/stock` | GET | order (asc / desc); orderby (stock_status / stock_quantity / date / id / include / title / sku); exclude; include; parent; parent_exclude; type (all / lowstock / instock / outofstock / onbackorder) | - | no |
| `/wc-analytics/reports/stock/stats` | GET | - | - | no |
| `/wc-analytics/reports/taxes` | GET | after; before; order (asc / desc); orderby (name / tax_rate_id / tax_code / rate / order_tax / total_tax / shipping_tax / taxable_amount / orders_count); force_cache_refresh; taxes | - | no |
| `/wc-analytics/reports/taxes/stats` | GET | after; before; order (asc / desc); orderby (date / items_sold / total_sales / orders_count / products_count); force_cache_refresh; fields; interval (hour / day / week / month / quarter / year); taxes; segmentby (tax_rate_id) | - | no |
| `/wc-analytics/reports/variations` | GET | after; before; order (asc / desc); orderby (date / net_revenue / orders_count / items_sold / sku); force_cache_refresh; match (all / any); product_includes; product_excludes; variations; extended_info; attribute_is; attribute_is_not; category_includes; category_excludes; products | - | no |
| `/wc-analytics/reports/variations/stats` | GET | after; before; order (asc / desc); orderby (date / net_revenue / coupons / refunds / shipping / taxes / net_revenue / orders_count / items_sold); force_cache_refresh; fields; interval (hour / day / week / month / quarter / year); match (all / any); category_includes; category_excludes; product_includes; product_excludes; variations; segmentby (product / category / variation); attribute_is; attribute_is_not | - | no |
| `/wc-analytics/settings/(?P<group_id>[\w-]+)` | GET | group | - | no |
| `/wc-analytics/settings/(?P<group_id>[\w-]+)/(?P<id>[\w-]+)` | GET, POST, PUT, PATCH | group; id; value | - | no |
| `/wc-analytics/settings/(?P<group_id>[\w-]+)/batch` | POST, PUT, PATCH | group; value | - | no |
| `/wc-analytics/taxes` | GET, POST | order (asc / desc); orderby (id / order / priority); class (standard / reduced-rate / zero-rate); search; include; country; state; postcode; city; rate; name; priority; compound; shipping; order; postcodes; cities | - | no |
| `/wc-analytics/taxes/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; country; state; postcode; city; rate; name; priority; compound; shipping; order; class (standard / reduced-rate / zero-rate); postcodes; cities; force | - | no |
| `/wc-analytics/taxes/batch` | POST, PUT, PATCH | country; state; postcode; city; rate; name; priority; compound; shipping; order; class (standard / reduced-rate / zero-rate); postcodes; cities | - | no |
| `/wc-analytics/variations` | GET | search; after; before; modified_after; modified_before; dates_are_gmt; exclude; include; order (asc / desc); orderby (date / id / include / title / slug / modified / menu_order); parent; parent_exclude; slug; status (any / future / trash / draft / pending / private / publish); sku; on_sale; min_price; max_price; include_meta; exclude_meta; image_size; stock_status (instock / outofstock / onbackorder); has_price; attributes; virtual; downloadable; include_status (any / future / trash / draft / pending / private / publish); exclude_status (future / trash / draft / pending / private / publish); pos_products_only | - | no |

### D: `wc-push-notifications` (2 routes)

Home: Out of scope: WooCommerce mobile app notifications.

| Route | Methods | Arguments | Home | QUILL today |
|---|---|---|---|---|
| `/wc-push-notifications` | GET | namespace | - | no |
| `/wc-push-notifications/status` | GET | - | - | no |

### D: `wc-telemetry` (2 routes)

Home: Out of scope: WooCommerce telemetry.

| Route | Methods | Arguments | Home | QUILL today |
|---|---|---|---|---|
| `/wc-telemetry` | GET | namespace | - | no |
| `/wc-telemetry/tracker` | POST | platform; version; installation_date | - | no |

### D: `wc/pos/v1/catalog` (2 routes)

Home: Out of scope: point of sale catalog.

| Route | Methods | Arguments | Home | QUILL today |
|---|---|---|---|---|
| `/wc/pos/v1/catalog` | GET | namespace | - | no |
| `/wc/pos/v1/catalog/create` | POST | force; _product_fields; _variation_fields | - | no |

### D: `wc/private` (2 routes)

Home: Out of scope: private to WooCommerce.

| Route | Methods | Arguments | Home | QUILL today |
|---|---|---|---|---|
| `/wc/private` | GET | namespace | - | no |
| `/wc/private/patterns` | GET, POST | - | - | no |

### D: `wc/store` (31 routes)

Home: Out of scope: the shop's public checkout API for visitors.

| Route | Methods | Arguments | Home | QUILL today |
|---|---|---|---|---|
| `/wc/store` | GET | namespace | - | no |
| `/wc/store/batch` | POST | validation (require-all-validate / normal); requests | - | no |
| `/wc/store/cart` | GET | - | - | no |
| `/wc/store/cart/add-item` | POST | id; quantity; variation | - | no |
| `/wc/store/cart/apply-coupon` | POST | code | - | no |
| `/wc/store/cart/coupons` | GET, POST, DELETE | code; discount_type | - | no |
| `/wc/store/cart/coupons/(?P<code>[\w-]+)` | GET, DELETE | code | - | no |
| `/wc/store/cart/extensions` | POST | namespace; data | - | no |
| `/wc/store/cart/items` | GET, POST, DELETE | extensions | - | no |
| `/wc/store/cart/items/(?P<key>[\w-]{32})` | GET, POST, PUT, PATCH, DELETE | key; extensions; quantity | - | no |
| `/wc/store/cart/remove-coupon` | POST | code | - | no |
| `/wc/store/cart/remove-item` | POST | key | - | no |
| `/wc/store/cart/select-shipping-rate` | POST | package_id; rate_id | - | no |
| `/wc/store/cart/update-customer` | POST | billing_address; shipping_address | - | no |
| `/wc/store/cart/update-item` | POST | key; quantity | - | no |
| `/wc/store/checkout` | GET, POST, PUT, PATCH | payment_data; customer_password; expected_total; customer_note; billing_address; shipping_address; payment_method ( / bacs / cheque / cod); create_account; additional_fields; extensions; order_notes | - | no |
| `/wc/store/checkout/(?P<id>[\d]+)` | POST | payment_data; customer_note; billing_address; shipping_address; payment_method ( / bacs / cheque / cod); additional_fields; extensions | - | no |
| `/wc/store/order/(?P<id>[\d]+)` | GET | - | - | no |
| `/wc/store/products` | GET | search; slug; after; before; date_column (date / date_gmt / modified / modified_gmt); exclude; include; order (asc / desc); orderby (date / modified / id / include / title / slug / price / popularity / rating / menu_order / comment_count); parent; parent_exclude; type (simple / grouped / external / variable / variation); sku; featured; category; category_operator (in / not_in / and); brand; brand_operator (in / not_in / and); tag; tag_operator (in / not_in / and); on_sale; min_price; max_price; stock_status (instock / outofstock / onbackorder); attributes; attribute_relation (in / and); catalog_visibility (any / visible / catalog / search / hidden); rating (1 / 2 / 3 / 4 / 5); related | - | no |
| `/wc/store/products/(?P<id>[\d]+)` | GET | id | - | no |
| `/wc/store/products/(?P<slug>[\S]+)` | GET | slug | - | no |
| `/wc/store/products/attributes` | GET | - | - | no |
| `/wc/store/products/attributes/(?P<attribute_id>[\d]+)/terms` | GET | attribute_id; search; exclude; include; order (asc / desc); orderby (name / slug / count / menu_order / name_num / id); hide_empty; parent; __experimental_visual | - | no |
| `/wc/store/products/attributes/(?P<id>[\d]+)` | GET | id | - | no |
| `/wc/store/products/brands` | GET | search; exclude; include; order (asc / desc); orderby (name / slug / count); hide_empty; parent | - | no |
| `/wc/store/products/brands/(?P<identifier>[\w-]+)` | GET | identifier | - | no |
| `/wc/store/products/categories` | GET | search; exclude; include; order (asc / desc); orderby (name / slug / count); hide_empty; parent | - | no |
| `/wc/store/products/categories/(?P<id>[\d]+)` | GET | id | - | no |
| `/wc/store/products/collection-data` | GET | search; slug; after; before; date_column (date / date_gmt / modified / modified_gmt); exclude; include; order (asc / desc); orderby (date / modified / id / include / title / slug / price / popularity / rating / menu_order / comment_count); parent; parent_exclude; type (simple / grouped / external / variable / variation); sku; featured; category; category_operator (in / not_in / and); brand; brand_operator (in / not_in / and); tag; tag_operator (in / not_in / and); on_sale; min_price; max_price; stock_status (instock / outofstock / onbackorder); attributes; attribute_relation (in / and); catalog_visibility (any / visible / catalog / search / hidden); rating (1 / 2 / 3 / 4 / 5); related; calculate_price_range; calculate_stock_status_counts; calculate_attribute_counts; calculate_rating_counts; calculate_taxonomy_counts | - | no |
| `/wc/store/products/reviews` | GET | order (asc / desc); orderby (date / date_gmt / id / rating / product); category_id; product_id | - | no |
| `/wc/store/products/tags` | GET | search; exclude; include; order (asc / desc); orderby (name / slug / count); hide_empty; parent | - | no |

### D: `wc/store/v1` (31 routes)

Home: Out of scope: the shop's public checkout API for visitors.

| Route | Methods | Arguments | Home | QUILL today |
|---|---|---|---|---|
| `/wc/store/v1` | GET | namespace | - | no |
| `/wc/store/v1/batch` | POST | validation (require-all-validate / normal); requests | - | no |
| `/wc/store/v1/cart` | GET | - | - | no |
| `/wc/store/v1/cart/add-item` | POST | id; quantity; variation | - | no |
| `/wc/store/v1/cart/apply-coupon` | POST | code | - | no |
| `/wc/store/v1/cart/coupons` | GET, POST, DELETE | code; discount_type | - | no |
| `/wc/store/v1/cart/coupons/(?P<code>[\w-]+)` | GET, DELETE | code | - | no |
| `/wc/store/v1/cart/extensions` | POST | namespace; data | - | no |
| `/wc/store/v1/cart/items` | GET, POST, DELETE | extensions | - | no |
| `/wc/store/v1/cart/items/(?P<key>[\w-]{32})` | GET, POST, PUT, PATCH, DELETE | key; extensions; quantity | - | no |
| `/wc/store/v1/cart/remove-coupon` | POST | code | - | no |
| `/wc/store/v1/cart/remove-item` | POST | key | - | no |
| `/wc/store/v1/cart/select-shipping-rate` | POST | package_id; rate_id | - | no |
| `/wc/store/v1/cart/update-customer` | POST | billing_address; shipping_address | - | no |
| `/wc/store/v1/cart/update-item` | POST | key; quantity | - | no |
| `/wc/store/v1/checkout` | GET, POST, PUT, PATCH | payment_data; customer_password; expected_total; customer_note; billing_address; shipping_address; payment_method ( / bacs / cheque / cod); create_account; additional_fields; extensions; order_notes | - | no |
| `/wc/store/v1/checkout/(?P<id>[\d]+)` | POST | payment_data; customer_note; billing_address; shipping_address; payment_method ( / bacs / cheque / cod); additional_fields; extensions | - | no |
| `/wc/store/v1/order/(?P<id>[\d]+)` | GET | - | - | no |
| `/wc/store/v1/products` | GET | search; slug; after; before; date_column (date / date_gmt / modified / modified_gmt); exclude; include; order (asc / desc); orderby (date / modified / id / include / title / slug / price / popularity / rating / menu_order / comment_count); parent; parent_exclude; type (simple / grouped / external / variable / variation); sku; featured; category; category_operator (in / not_in / and); brand; brand_operator (in / not_in / and); tag; tag_operator (in / not_in / and); on_sale; min_price; max_price; stock_status (instock / outofstock / onbackorder); attributes; attribute_relation (in / and); catalog_visibility (any / visible / catalog / search / hidden); rating (1 / 2 / 3 / 4 / 5); related | - | no |
| `/wc/store/v1/products/(?P<id>[\d]+)` | GET | id | - | no |
| `/wc/store/v1/products/(?P<slug>[\S]+)` | GET | slug | - | no |
| `/wc/store/v1/products/attributes` | GET | - | - | no |
| `/wc/store/v1/products/attributes/(?P<attribute_id>[\d]+)/terms` | GET | attribute_id; search; exclude; include; order (asc / desc); orderby (name / slug / count / menu_order / name_num / id); hide_empty; parent; __experimental_visual | - | no |
| `/wc/store/v1/products/attributes/(?P<id>[\d]+)` | GET | id | - | no |
| `/wc/store/v1/products/brands` | GET | search; exclude; include; order (asc / desc); orderby (name / slug / count); hide_empty; parent | - | no |
| `/wc/store/v1/products/brands/(?P<identifier>[\w-]+)` | GET | identifier | - | no |
| `/wc/store/v1/products/categories` | GET | search; exclude; include; order (asc / desc); orderby (name / slug / count); hide_empty; parent | - | no |
| `/wc/store/v1/products/categories/(?P<id>[\d]+)` | GET | id | - | no |
| `/wc/store/v1/products/collection-data` | GET | search; slug; after; before; date_column (date / date_gmt / modified / modified_gmt); exclude; include; order (asc / desc); orderby (date / modified / id / include / title / slug / price / popularity / rating / menu_order / comment_count); parent; parent_exclude; type (simple / grouped / external / variable / variation); sku; featured; category; category_operator (in / not_in / and); brand; brand_operator (in / not_in / and); tag; tag_operator (in / not_in / and); on_sale; min_price; max_price; stock_status (instock / outofstock / onbackorder); attributes; attribute_relation (in / and); catalog_visibility (any / visible / catalog / search / hidden); rating (1 / 2 / 3 / 4 / 5); related; calculate_price_range; calculate_stock_status_counts; calculate_attribute_counts; calculate_rating_counts; calculate_taxonomy_counts | - | no |
| `/wc/store/v1/products/reviews` | GET | order (asc / desc); orderby (date / date_gmt / id / rating / product); category_id; product_id | - | no |
| `/wc/store/v1/products/tags` | GET | search; exclude; include; order (asc / desc); orderby (name / slug / count); hide_empty; parent | - | no |

### D: `wc/v1` (49 routes)

Home: Shop: older version of wc/v3; use wc/v3.

| Route | Methods | Arguments | Home | QUILL today |
|---|---|---|---|---|
| `/wc/v1` | GET | namespace | - | no |
| `/wc/v1/coupons` | GET, POST | search; after; before; exclude; include; order (asc / desc); orderby (date / id / include / title / slug / modified); filter; code; description; discount_type (percent / fixed_cart / fixed_product); amount; expiry_date; individual_use; product_ids; exclude_product_ids; usage_limit; usage_limit_per_user; limit_usage_to_x_items; free_shipping; product_categories; excluded_product_categories; exclude_sale_items; minimum_amount; maximum_amount; email_restrictions | - | no |
| `/wc/v1/coupons/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; code; description; discount_type (percent / fixed_cart / fixed_product); amount; expiry_date; individual_use; product_ids; exclude_product_ids; usage_limit; usage_limit_per_user; limit_usage_to_x_items; free_shipping; product_categories; excluded_product_categories; exclude_sale_items; minimum_amount; maximum_amount; email_restrictions; force | - | no |
| `/wc/v1/coupons/batch` | POST, PUT, PATCH | code; description; discount_type (percent / fixed_cart / fixed_product); amount; expiry_date; individual_use; product_ids; exclude_product_ids; usage_limit; usage_limit_per_user; limit_usage_to_x_items; free_shipping; product_categories; excluded_product_categories; exclude_sale_items; minimum_amount; maximum_amount; email_restrictions | - | no |
| `/wc/v1/customers` | GET, POST | search; exclude; include; order (asc / desc); orderby (id / include / name / registered_date); email; role (all / administrator / editor / author / contributor / subscriber / customer / shop_manager / wpseo_manager / wpseo_editor); first_name; last_name; username; password; billing; shipping | - | no |
| `/wc/v1/customers/(?P<customer_id>[\d]+)/downloads` | GET | customer_id | - | no |
| `/wc/v1/customers/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; email; first_name; last_name; username; password; billing; shipping; force; reassign | - | no |
| `/wc/v1/customers/batch` | POST, PUT, PATCH | email; first_name; last_name; username; password; billing; shipping | - | no |
| `/wc/v1/marketplace/product-preview` | GET | - | - | no |
| `/wc/v1/orders` | GET, POST | search; after; before; exclude; include; order (asc / desc); orderby (date / id / include / title / slug / modified); filter; status (any / pending / processing / on-hold / completed / cancelled / refunded / failed / checkout-draft); customer; product; dp; parent_id; status (pending / processing / on-hold / completed / cancelled / refunded / failed / checkout-draft); currency (AED / AFN / ALL / AMD / ANG / AOA / ARS / AUD / AWG / AZN / BAM / BBD / BDT / BGN and 150 more); customer_id; billing; shipping; payment_method; payment_method_title; set_paid; transaction_id; customer_note; line_items; shipping_lines; fee_lines; coupon_lines | - | no |
| `/wc/v1/orders/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; parent_id; status (pending / processing / on-hold / completed / cancelled / refunded / failed / checkout-draft); currency (AED / AFN / ALL / AMD / ANG / AOA / ARS / AUD / AWG / AZN / BAM / BBD / BDT / BGN and 150 more); customer_id; billing; shipping; payment_method; payment_method_title; set_paid; transaction_id; customer_note; line_items; shipping_lines; fee_lines; coupon_lines; force | - | no |
| `/wc/v1/orders/(?P<order_id>[\d]+)/notes` | GET, POST | order_id; note; customer_note | - | no |
| `/wc/v1/orders/(?P<order_id>[\d]+)/notes/(?P<id>[\d]+)` | GET, DELETE | id; order_id; force | - | no |
| `/wc/v1/orders/(?P<order_id>[\d]+)/refunds` | GET, POST | order_id; search; after; before; exclude; include; order (asc / desc); orderby (date / id / include / title / slug / modified); filter; status (any / pending / processing / on-hold / completed / cancelled / refunded / failed / checkout-draft); customer; product; dp; amount; reason | - | no |
| `/wc/v1/orders/(?P<order_id>[\d]+)/refunds/(?P<id>[\d]+)` | GET, DELETE | order_id; id; force | - | no |
| `/wc/v1/orders/batch` | POST, PUT, PATCH | parent_id; status (pending / processing / on-hold / completed / cancelled / refunded / failed / checkout-draft); currency (AED / AFN / ALL / AMD / ANG / AOA / ARS / AUD / AWG / AZN / BAM / BBD / BDT / BGN and 150 more); customer_id; billing; shipping; payment_method; payment_method_title; set_paid; transaction_id; customer_note; line_items; shipping_lines; fee_lines; coupon_lines | - | no |
| `/wc/v1/products` | GET, POST | search; after; before; exclude; include; order (asc / desc); orderby (date / id / include / title / slug / modified); filter; slug; status (any / future / draft / pending / private / publish); type (simple / grouped / external / variable); category; tag; shipping_class; attribute; attribute_term; sku; name; status (draft / pending / private / publish / future); featured; catalog_visibility (visible / catalog / search / hidden); description; short_description; regular_price; sale_price; date_on_sale_from; date_on_sale_to; virtual; downloadable; downloads; download_limit; download_expiry; download_type (standard); external_url; button_text; tax_status (taxable / shipping / none); tax_class; manage_stock; stock_quantity; in_stock; backorders (no / notify / yes); sold_individually; weight; dimensions; reviews_allowed; upsell_ids; cross_sell_ids; parent_id; purchase_note; categories; tags; images; attributes; default_attributes; variations; menu_order | - | no |
| `/wc/v1/products/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; name; slug; type (simple / grouped / external / variable); status (draft / pending / private / publish / future); featured; catalog_visibility (visible / catalog / search / hidden); description; short_description; sku; regular_price; sale_price; date_on_sale_from; date_on_sale_to; virtual; downloadable; downloads; download_limit; download_expiry; download_type (standard); external_url; button_text; tax_status (taxable / shipping / none); tax_class; manage_stock; stock_quantity; in_stock; backorders (no / notify / yes); sold_individually; weight; dimensions; shipping_class; reviews_allowed; upsell_ids; cross_sell_ids; parent_id; purchase_note; categories; tags; images; attributes; default_attributes; variations; menu_order; force | - | no |
| `/wc/v1/products/(?P<product_id>[\d]+)/reviews` | GET, POST | product_id; id; review; date_created; rating; name; email | - | no |
| `/wc/v1/products/(?P<product_id>[\d]+)/reviews/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | product_id; id; review; date_created; rating; name; email; force | - | no |
| `/wc/v1/products/attributes` | GET, POST | name; slug; type (select); order_by (menu_order / name / name_num / id); has_archives | - | no |
| `/wc/v1/products/attributes/(?P<attribute_id>[\d]+)/terms` | GET, POST | attribute_id; search; exclude; include; order (asc / desc); orderby (id / include / name / slug / term_group / description / count); hide_empty; parent; product; slug; name; description; menu_order | - | no |
| `/wc/v1/products/attributes/(?P<attribute_id>[\d]+)/terms/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; attribute_id; name; slug; description; menu_order; force | - | no |
| `/wc/v1/products/attributes/(?P<attribute_id>[\d]+)/terms/batch` | POST, PUT, PATCH | attribute_id; name; slug; description; menu_order | - | no |
| `/wc/v1/products/attributes/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; name; slug; type (select); order_by (menu_order / name / name_num / id); has_archives; force | - | no |
| `/wc/v1/products/attributes/batch` | POST, PUT, PATCH | name; slug; type (select); order_by (menu_order / name / name_num / id); has_archives | - | no |
| `/wc/v1/products/batch` | POST, PUT, PATCH | name; slug; type (simple / grouped / external / variable); status (draft / pending / private / publish / future); featured; catalog_visibility (visible / catalog / search / hidden); description; short_description; sku; regular_price; sale_price; date_on_sale_from; date_on_sale_to; virtual; downloadable; downloads; download_limit; download_expiry; download_type (standard); external_url; button_text; tax_status (taxable / shipping / none); tax_class; manage_stock; stock_quantity; in_stock; backorders (no / notify / yes); sold_individually; weight; dimensions; shipping_class; reviews_allowed; upsell_ids; cross_sell_ids; parent_id; purchase_note; categories; tags; images; attributes; default_attributes; variations; menu_order | - | no |
| `/wc/v1/products/categories` | GET, POST | search; exclude; include; order (asc / desc); orderby (id / include / name / slug / term_group / description / count); hide_empty; parent; product; slug; name; description; display (default / products / subcategories / both); image | - | no |
| `/wc/v1/products/categories/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; name; slug; parent; description; display (default / products / subcategories / both); image; force | - | no |
| `/wc/v1/products/categories/batch` | POST, PUT, PATCH | name; slug; parent; description; display (default / products / subcategories / both); image | - | no |
| `/wc/v1/products/shipping_classes` | GET, POST | search; exclude; include; order (asc / desc); orderby (id / include / name / slug / term_group / description / count); hide_empty; parent; product; slug; name; description | - | no |
| `/wc/v1/products/shipping_classes/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; name; slug; description; force | - | no |
| `/wc/v1/products/shipping_classes/batch` | POST, PUT, PATCH | name; slug; description | - | no |
| `/wc/v1/products/tags` | GET, POST | search; exclude; include; order (asc / desc); orderby (id / include / name / slug / term_group / description / count); hide_empty; parent; product; slug; name; description | - | no |
| `/wc/v1/products/tags/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; name; slug; description; force | - | no |
| `/wc/v1/products/tags/batch` | POST, PUT, PATCH | name; slug; description | - | no |
| `/wc/v1/reports` | GET | - | - | no |
| `/wc/v1/reports/sales` | GET | period (week / month / last_month / year); date_min; date_max | - | no |
| `/wc/v1/reports/top_sellers` | GET | period (week / month / last_month / year); date_min; date_max | - | no |
| `/wc/v1/taxes` | GET, POST | order (asc / desc); orderby (id / order / priority); class (standard / reduced-rate / zero-rate); country; state; postcode; city; rate; name; priority; compound; shipping; order | - | no |
| `/wc/v1/taxes/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; country; state; postcode; city; rate; name; priority; compound; shipping; order; class (standard / reduced-rate / zero-rate); force | - | no |
| `/wc/v1/taxes/batch` | POST, PUT, PATCH | country; state; postcode; city; rate; name; priority; compound; shipping; order; class (standard / reduced-rate / zero-rate) | - | no |
| `/wc/v1/taxes/classes` | GET, POST | name | - | no |
| `/wc/v1/taxes/classes/(?P<slug>\w[\w\s\-]*)` | DELETE | slug; force | - | no |
| `/wc/v1/webhooks` | GET, POST | search; after; before; exclude; include; order (asc / desc); orderby (date / id / title); status (all / active / paused / disabled); name; status (active / paused / disabled); topic; secret; delivery_url | - | no |
| `/wc/v1/webhooks/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; name; status (active / paused / disabled); topic; secret; force | - | no |
| `/wc/v1/webhooks/(?P<webhook_id>[\d]+)/deliveries` | GET | webhook_id | - | no |
| `/wc/v1/webhooks/(?P<webhook_id>[\d]+)/deliveries/(?P<id>[\d]+)` | GET | webhook_id; id | - | no |
| `/wc/v1/webhooks/batch` | POST, PUT, PATCH | name; status (active / paused / disabled); topic; secret | - | no |

### D: `wc/v2` (72 routes)

Home: Shop: older version of wc/v3; use wc/v3.

| Route | Methods | Arguments | Home | QUILL today |
|---|---|---|---|---|
| `/wc/v2` | GET | namespace | - | no |
| `/wc/v2/coupons` | GET, POST | search; after; before; modified_after; modified_before; dates_are_gmt; exclude; include; order (asc / desc); orderby (date / id / include / title / slug / modified); code; amount; status; discount_type (percent / fixed_cart / fixed_product); description; date_expires; date_expires_gmt; individual_use; product_ids; excluded_product_ids; usage_limit; usage_limit_per_user; limit_usage_to_x_items; free_shipping; product_categories; excluded_product_categories; exclude_sale_items; minimum_amount; maximum_amount; email_restrictions; meta_data | - | no |
| `/wc/v2/coupons/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; code; amount; status; discount_type (percent / fixed_cart / fixed_product); description; date_expires; date_expires_gmt; individual_use; product_ids; excluded_product_ids; usage_limit; usage_limit_per_user; limit_usage_to_x_items; free_shipping; product_categories; excluded_product_categories; exclude_sale_items; minimum_amount; maximum_amount; email_restrictions; meta_data; force | - | no |
| `/wc/v2/coupons/batch` | POST, PUT, PATCH | code; amount; status; discount_type (percent / fixed_cart / fixed_product); description; date_expires; date_expires_gmt; individual_use; product_ids; excluded_product_ids; usage_limit; usage_limit_per_user; limit_usage_to_x_items; free_shipping; product_categories; excluded_product_categories; exclude_sale_items; minimum_amount; maximum_amount; email_restrictions; meta_data | - | no |
| `/wc/v2/customers` | GET, POST | search; exclude; include; order (asc / desc); orderby (id / include / name / registered_date); email; role (all / administrator / editor / author / contributor / subscriber / customer / shop_manager / wpseo_manager / wpseo_editor); first_name; last_name; username; password; billing; shipping; meta_data | - | no |
| `/wc/v2/customers/(?P<customer_id>[\d]+)/downloads` | GET | customer_id | - | no |
| `/wc/v2/customers/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; email; first_name; last_name; username; password; billing; shipping; meta_data; force; reassign | - | no |
| `/wc/v2/customers/batch` | POST, PUT, PATCH | email; first_name; last_name; username; password; billing; shipping; meta_data | - | no |
| `/wc/v2/orders` | GET, POST | search; after; before; modified_after; modified_before; dates_are_gmt; exclude; include; order (asc / desc); orderby (date / id / include / title / slug / modified); parent; parent_exclude; status (any / trash / auto-draft / pending / processing / on-hold / completed / cancelled / refunded / failed / checkout-draft); customer; product; dp; order_item_display_meta; include_meta; exclude_meta; parent_id; status (auto-draft / pending / processing / on-hold / completed / cancelled / refunded / failed / checkout-draft); currency (AED / AFN / ALL / AMD / ANG / AOA / ARS / AUD / AWG / AZN / BAM / BBD / BDT / BGN and 150 more); customer_id; customer_note; billing; shipping; payment_method; payment_method_title; transaction_id; meta_data; line_items; shipping_lines; fee_lines; coupon_lines; set_paid | - | no |
| `/wc/v2/orders/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; parent_id; status (auto-draft / pending / processing / on-hold / completed / cancelled / refunded / failed / checkout-draft); currency (AED / AFN / ALL / AMD / ANG / AOA / ARS / AUD / AWG / AZN / BAM / BBD / BDT / BGN and 150 more); customer_id; customer_note; billing; shipping; payment_method; payment_method_title; transaction_id; meta_data; line_items; shipping_lines; fee_lines; coupon_lines; set_paid; force | - | no |
| `/wc/v2/orders/(?P<order_id>[\d]+)/notes` | GET, POST | order_id; type (any / customer / internal); note; customer_note | - | no |
| `/wc/v2/orders/(?P<order_id>[\d]+)/notes/(?P<id>[\d]+)` | GET, DELETE | id; order_id; force | - | no |
| `/wc/v2/orders/(?P<order_id>[\d]+)/refunds` | GET, POST | order_id; search; after; before; modified_after; modified_before; dates_are_gmt; exclude; include; order (asc / desc); orderby (date / id / include / title / slug / modified); parent; parent_exclude; dp; order_item_display_meta; include_meta; exclude_meta; amount; reason; refunded_by; meta_data; shipping_lines; fee_lines; api_refund | - | no |
| `/wc/v2/orders/(?P<order_id>[\d]+)/refunds/(?P<id>[\d]+)` | GET, DELETE | order_id; id; force | - | no |
| `/wc/v2/orders/batch` | POST, PUT, PATCH | parent_id; status (auto-draft / pending / processing / on-hold / completed / cancelled / refunded / failed / checkout-draft); currency (AED / AFN / ALL / AMD / ANG / AOA / ARS / AUD / AWG / AZN / BAM / BBD / BDT / BGN and 150 more); customer_id; customer_note; billing; shipping; payment_method; payment_method_title; transaction_id; meta_data; line_items; shipping_lines; fee_lines; coupon_lines; set_paid | - | no |
| `/wc/v2/payment_gateways` | GET | - | - | no |
| `/wc/v2/payment_gateways/(?P<id>[\w-]+)` | GET, POST, PUT, PATCH | id; title; description; order; enabled; settings | - | no |
| `/wc/v2/products` | GET, POST | search; after; before; modified_after; modified_before; dates_are_gmt; exclude; include; order (asc / desc); orderby (date / id / include / title / slug / modified / popularity / rating / post__in / price / sales / menu_order / random / popularity and 2 more); parent; parent_exclude; brand; slug; status (any / future / trash / draft / pending / private / publish); type (simple / grouped / external / variable); sku; featured; category; tag; shipping_class; attribute; attribute_term; in_stock; on_sale; min_price; max_price; include_meta; exclude_meta; image_size; name; status (draft / pending / private / publish / future); catalog_visibility (visible / catalog / search / hidden); description; short_description; regular_price; sale_price; date_on_sale_from; date_on_sale_from_gmt; date_on_sale_to; date_on_sale_to_gmt; virtual; downloadable; downloads; download_limit; download_expiry; external_url; button_text; tax_status (taxable / shipping / none); tax_class; manage_stock; stock_quantity; backorders (no / notify / yes); sold_individually; weight; dimensions; reviews_allowed; upsell_ids; cross_sell_ids; parent_id; purchase_note; categories; tags; images; attributes; default_attributes; grouped_products; menu_order; meta_data | - | no |
| `/wc/v2/products/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; image_size; name; slug; type (simple / grouped / external / variable); status (draft / pending / private / publish / future); featured; catalog_visibility (visible / catalog / search / hidden); description; short_description; sku; regular_price; sale_price; date_on_sale_from; date_on_sale_from_gmt; date_on_sale_to; date_on_sale_to_gmt; virtual; downloadable; downloads; download_limit; download_expiry; external_url; button_text; tax_status (taxable / shipping / none); tax_class; manage_stock; stock_quantity; in_stock; backorders (no / notify / yes); sold_individually; weight; dimensions; shipping_class; reviews_allowed; upsell_ids; cross_sell_ids; parent_id; purchase_note; categories; tags; images; attributes; default_attributes; grouped_products; menu_order; meta_data; force | - | no |
| `/wc/v2/products/(?P<id>[\d]+)/related` | GET | id | - | no |
| `/wc/v2/products/(?P<product_id>[\d]+)/reviews` | GET, POST | product_id; id; review; date_created; date_created_gmt; rating; name; email | - | no |
| `/wc/v2/products/(?P<product_id>[\d]+)/reviews/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | product_id; id; review; date_created; date_created_gmt; rating; name; email; force | - | no |
| `/wc/v2/products/(?P<product_id>[\d]+)/reviews/batch` | POST, PUT, PATCH | product_id; review; date_created; date_created_gmt; rating; name; email | - | no |
| `/wc/v2/products/(?P<product_id>[\d]+)/variations` | GET, POST | product_id; search; after; before; modified_after; modified_before; dates_are_gmt; exclude; include; order (asc / desc); orderby (date / id / include / title / slug / modified / menu_order); parent; parent_exclude; slug; status (any / future / trash / draft / pending / private / publish); type (simple / grouped / external / variable); sku; featured; category; tag; shipping_class; attribute; attribute_term; in_stock; on_sale; min_price; max_price; include_meta; exclude_meta; image_size; description; regular_price; sale_price; date_on_sale_from; date_on_sale_from_gmt; date_on_sale_to; date_on_sale_to_gmt; visible; virtual; downloadable; downloads; download_limit; download_expiry; tax_status (taxable / shipping / none); tax_class; manage_stock; stock_quantity; backorders (no / notify / yes); weight; dimensions; image; attributes; menu_order; meta_data | - | no |
| `/wc/v2/products/(?P<product_id>[\d]+)/variations/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | product_id; id; image_size; description; sku; regular_price; sale_price; date_on_sale_from; date_on_sale_from_gmt; date_on_sale_to; date_on_sale_to_gmt; visible; virtual; downloadable; downloads; download_limit; download_expiry; tax_status (taxable / shipping / none); tax_class; manage_stock; stock_quantity; in_stock; backorders (no / notify / yes); weight; dimensions; shipping_class; image; attributes; menu_order; meta_data; force | - | no |
| `/wc/v2/products/(?P<product_id>[\d]+)/variations/batch` | POST, PUT, PATCH | product_id; description; sku; regular_price; sale_price; date_on_sale_from; date_on_sale_from_gmt; date_on_sale_to; date_on_sale_to_gmt; visible; virtual; downloadable; downloads; download_limit; download_expiry; tax_status (taxable / shipping / none); tax_class; manage_stock; stock_quantity; in_stock; backorders (no / notify / yes); weight; dimensions; shipping_class; image; attributes; menu_order; meta_data | - | no |
| `/wc/v2/products/attributes` | GET, POST | name; slug; type (select); order_by (menu_order / name / name_num / id); has_archives | - | no |
| `/wc/v2/products/attributes/(?P<attribute_id>[\d]+)/terms` | GET, POST | attribute_id; search; exclude; include; order (asc / desc); orderby (id / include / name / slug / term_group / description / count); hide_empty; parent; product; slug; name; description; menu_order | - | no |
| `/wc/v2/products/attributes/(?P<attribute_id>[\d]+)/terms/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; attribute_id; name; slug; description; menu_order; force | - | no |
| `/wc/v2/products/attributes/(?P<attribute_id>[\d]+)/terms/batch` | POST, PUT, PATCH | attribute_id; name; slug; description; menu_order | - | no |
| `/wc/v2/products/attributes/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; name; slug; type (select); order_by (menu_order / name / name_num / id); has_archives; force | - | no |
| `/wc/v2/products/attributes/batch` | POST, PUT, PATCH | name; slug; type (select); order_by (menu_order / name / name_num / id); has_archives | - | no |
| `/wc/v2/products/batch` | POST, PUT, PATCH | name; slug; type (simple / grouped / external / variable); status (draft / pending / private / publish / future); featured; catalog_visibility (visible / catalog / search / hidden); description; short_description; sku; regular_price; sale_price; date_on_sale_from; date_on_sale_from_gmt; date_on_sale_to; date_on_sale_to_gmt; virtual; downloadable; downloads; download_limit; download_expiry; external_url; button_text; tax_status (taxable / shipping / none); tax_class; manage_stock; stock_quantity; in_stock; backorders (no / notify / yes); sold_individually; weight; dimensions; shipping_class; reviews_allowed; upsell_ids; cross_sell_ids; parent_id; purchase_note; categories; tags; images; attributes; default_attributes; grouped_products; menu_order; meta_data | - | no |
| `/wc/v2/products/brands` | GET, POST | search; exclude; include; order (asc / desc); orderby (id / include / name / slug / term_group / description / count); hide_empty; parent; product; slug; name; description; display (default / products / subcategories / both); image; menu_order | - | no |
| `/wc/v2/products/brands/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; name; slug; parent; description; display (default / products / subcategories / both); image; menu_order; force | - | no |
| `/wc/v2/products/brands/batch` | POST, PUT, PATCH | name; slug; parent; description; display (default / products / subcategories / both); image; menu_order | - | no |
| `/wc/v2/products/categories` | GET, POST | search; exclude; include; order (asc / desc); orderby (id / include / name / slug / term_group / description / count); hide_empty; parent; product; slug; name; description; display (default / products / subcategories / both); image | - | no |
| `/wc/v2/products/categories/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; name; slug; parent; description; display (default / products / subcategories / both); image; force | - | no |
| `/wc/v2/products/categories/batch` | POST, PUT, PATCH | name; slug; parent; description; display (default / products / subcategories / both); image | - | no |
| `/wc/v2/products/shipping_classes` | GET, POST | search; exclude; include; order (asc / desc); orderby (id / include / name / slug / term_group / description / count); hide_empty; parent; product; slug; name; description | - | no |
| `/wc/v2/products/shipping_classes/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; name; slug; description; force | - | no |
| `/wc/v2/products/shipping_classes/batch` | POST, PUT, PATCH | name; slug; description | - | no |
| `/wc/v2/products/tags` | GET, POST | search; exclude; include; order (asc / desc); orderby (id / include / name / slug / term_group / description / count); hide_empty; parent; product; slug; name; description | - | no |
| `/wc/v2/products/tags/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; name; slug; description; force | - | no |
| `/wc/v2/products/tags/batch` | POST, PUT, PATCH | name; slug; description | - | no |
| `/wc/v2/reports` | GET | - | - | no |
| `/wc/v2/reports/sales` | GET | period (week / month / last_month / year); date_min; date_max | - | no |
| `/wc/v2/reports/top_sellers` | GET | period (week / month / last_month / year); date_min; date_max | - | no |
| `/wc/v2/settings` | GET | - | - | no |
| `/wc/v2/settings/(?P<group_id>[\w-]+)` | GET | group | - | no |
| `/wc/v2/settings/(?P<group_id>[\w-]+)/(?P<id>[\w-]+)` | GET, POST, PUT, PATCH | group; id; value | - | no |
| `/wc/v2/settings/(?P<group_id>[\w-]+)/batch` | POST, PUT, PATCH | group; value | - | no |
| `/wc/v2/shipping/zones` | GET, POST | name; order | - | no |
| `/wc/v2/shipping/zones/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; name; order; force | - | no |
| `/wc/v2/shipping/zones/(?P<id>[\d]+)/locations` | GET, POST, PUT, PATCH | id; code; type (postcode / state / country / continent) | - | no |
| `/wc/v2/shipping/zones/(?P<zone_id>[\d]+)/methods` | GET, POST | zone_id; order; enabled; settings; method_id | - | no |
| `/wc/v2/shipping/zones/(?P<zone_id>[\d]+)/methods/(?P<instance_id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | zone_id; instance_id; order; enabled; settings; force | - | no |
| `/wc/v2/shipping_methods` | GET | - | - | no |
| `/wc/v2/shipping_methods/(?P<id>[\w-]+)` | GET | id | - | no |
| `/wc/v2/system_status` | GET | - | - | no |
| `/wc/v2/system_status/tools` | GET | - | - | no |
| `/wc/v2/system_status/tools/(?P<id>[\w-]+)` | GET, POST, PUT, PATCH | id; name; action; description; success; message | - | no |
| `/wc/v2/taxes` | GET, POST | order (asc / desc); orderby (id / order / priority); class (standard / reduced-rate / zero-rate); country; state; postcode; city; rate; name; priority; compound; shipping; order | - | no |
| `/wc/v2/taxes/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; country; state; postcode; city; rate; name; priority; compound; shipping; order; class (standard / reduced-rate / zero-rate); force | - | no |
| `/wc/v2/taxes/batch` | POST, PUT, PATCH | country; state; postcode; city; rate; name; priority; compound; shipping; order; class (standard / reduced-rate / zero-rate) | - | no |
| `/wc/v2/taxes/classes` | GET, POST | name | - | no |
| `/wc/v2/taxes/classes/(?P<slug>\w[\w\s\-]*)` | GET, DELETE | slug; force | - | no |
| `/wc/v2/webhooks` | GET, POST | search; after; before; exclude; include; order (asc / desc); orderby (date / id / title); status (all / active / paused / disabled); name; status (active / paused / disabled); topic; secret; delivery_url | - | no |
| `/wc/v2/webhooks/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; name; status (active / paused / disabled); topic; secret; force | - | no |
| `/wc/v2/webhooks/(?P<webhook_id>[\d]+)/deliveries` | GET | webhook_id | - | no |
| `/wc/v2/webhooks/(?P<webhook_id>[\d]+)/deliveries/(?P<id>[\d]+)` | GET | webhook_id; id | - | no |
| `/wc/v2/webhooks/batch` | POST, PUT, PATCH | name; status (active / paused / disabled); topic; secret | - | no |

### D: `wc/v3` (112 routes)

Home: Sites > site > Shop (products, orders, customers, coupons, reports, settings, taxes, shipping, payment gateways, webhooks).

| Route | Methods | Arguments | Home | QUILL today |
|---|---|---|---|---|
| `/wc/v3` | GET | namespace | - | yes |
| `/wc/v3/coupons` | GET, POST | search; after; before; modified_after; modified_before; dates_are_gmt; exclude; include; order (asc / desc); orderby (date / id / include / title / slug / modified); code; amount; status; discount_type (percent / fixed_cart / fixed_product); description; date_expires; date_expires_gmt; individual_use; product_ids; excluded_product_ids; usage_limit; usage_limit_per_user; limit_usage_to_x_items; free_shipping; product_categories; excluded_product_categories; exclude_sale_items; minimum_amount; maximum_amount; email_restrictions; meta_data | - | yes |
| `/wc/v3/coupons/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; code; amount; status; discount_type (percent / fixed_cart / fixed_product); description; date_expires; date_expires_gmt; individual_use; product_ids; excluded_product_ids; usage_limit; usage_limit_per_user; limit_usage_to_x_items; free_shipping; product_categories; excluded_product_categories; exclude_sale_items; minimum_amount; maximum_amount; email_restrictions; meta_data; force | - | yes |
| `/wc/v3/coupons/batch` | POST, PUT, PATCH | code; amount; status; discount_type (percent / fixed_cart / fixed_product); description; date_expires; date_expires_gmt; individual_use; product_ids; excluded_product_ids; usage_limit; usage_limit_per_user; limit_usage_to_x_items; free_shipping; product_categories; excluded_product_categories; exclude_sale_items; minimum_amount; maximum_amount; email_restrictions; meta_data | - | yes |
| `/wc/v3/customers` | GET, POST | search; exclude; include; order (asc / desc); orderby (id / include / name / registered_date); email; role (all / administrator / editor / author / contributor / subscriber / customer / shop_manager / wpseo_manager / wpseo_editor); first_name; last_name; username; password; billing; shipping; meta_data | - | yes |
| `/wc/v3/customers/(?P<customer_id>[\d]+)/downloads` | GET | customer_id | - | yes |
| `/wc/v3/customers/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; email; first_name; last_name; username; password; billing; shipping; meta_data; force; reassign | - | yes |
| `/wc/v3/customers/batch` | POST, PUT, PATCH | email; first_name; last_name; username; password; billing; shipping; meta_data | - | yes |
| `/wc/v3/data` | GET | - | - | yes |
| `/wc/v3/data/continents` | GET | - | - | yes |
| `/wc/v3/data/continents/(?P<location>[\w-]+)` | GET | continent | - | yes |
| `/wc/v3/data/countries` | GET | - | - | yes |
| `/wc/v3/data/countries/(?P<location>[\w-]+)` | GET | location | - | yes |
| `/wc/v3/data/currencies` | GET | - | - | yes |
| `/wc/v3/data/currencies/(?P<currency>[\w-]{3})` | GET | location | - | yes |
| `/wc/v3/data/currencies/current` | GET | - | - | yes |
| `/wc/v3/marketplace/create-order` | POST | product_id | - | yes |
| `/wc/v3/marketplace/featured` | GET | - | - | yes |
| `/wc/v3/marketplace/refresh` | POST | - | - | yes |
| `/wc/v3/marketplace/subscriptions` | GET | - | - | yes |
| `/wc/v3/marketplace/subscriptions/activate` | POST | product_key | - | yes |
| `/wc/v3/marketplace/subscriptions/activate-plugin` | POST | product_key | - | yes |
| `/wc/v3/marketplace/subscriptions/auto-update` | POST | product_key; enabled | - | yes |
| `/wc/v3/marketplace/subscriptions/connect` | POST | product_key | - | yes |
| `/wc/v3/marketplace/subscriptions/disconnect` | POST | product_key | - | yes |
| `/wc/v3/marketplace/subscriptions/install-url` | GET | product_key | - | yes |
| `/wc/v3/orders` | GET, POST | search; after; before; modified_after; modified_before; dates_are_gmt; exclude; include; order (asc / desc); orderby (date / id / include / title / slug / modified); parent; parent_exclude; status (any / trash / auto-draft / pending / processing / on-hold / completed / cancelled / refunded / failed / checkout-draft); customer; product; dp; order_item_display_meta; include_meta; exclude_meta; created_via; parent_id; status (auto-draft / pending / processing / on-hold / completed / cancelled / refunded / failed / checkout-draft); currency (AED / AFN / ALL / AMD / ANG / AOA / ARS / AUD / AWG / AZN / BAM / BBD / BDT / BGN and 150 more); customer_id; customer_note; billing; shipping; payment_method; payment_method_title; transaction_id; meta_data; line_items; shipping_lines; fee_lines; coupon_lines; set_paid; manual_update | - | yes |
| `/wc/v3/orders/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; parent_id; created_via; status (auto-draft / pending / processing / on-hold / completed / cancelled / refunded / failed / checkout-draft); currency (AED / AFN / ALL / AMD / ANG / AOA / ARS / AUD / AWG / AZN / BAM / BBD / BDT / BGN and 150 more); customer_id; customer_note; billing; shipping; payment_method; payment_method_title; transaction_id; meta_data; line_items; shipping_lines; fee_lines; coupon_lines; set_paid; manual_update; force | - | yes |
| `/wc/v3/orders/(?P<id>[\d]+)/actions/email_templates` | GET | id | - | yes |
| `/wc/v3/orders/(?P<id>[\d]+)/actions/send_email` | POST | id; email; force_email_update; template_id (new_order / cancelled_order / customer_cancelled_order / failed_order / customer_failed_order / customer_on_hold_order / customer_processing_order / customer_completed_order / customer_refunded_order / customer_invoice / customer_note / customer_reset_password / customer_new_account / admin_payment_gateway_enabled and 3 more) | - | yes |
| `/wc/v3/orders/(?P<id>[\d]+)/actions/send_order_details` | POST | id; email; force_email_update | - | yes |
| `/wc/v3/orders/(?P<id>[\d]+)/receipt` | POST, GET | id; expiration_date; expiration_days; force_new | - | yes |
| `/wc/v3/orders/(?P<order_id>[\d]+)/notes` | GET, POST | order_id; type (any / customer / internal); note; customer_note; added_by_user | - | yes |
| `/wc/v3/orders/(?P<order_id>[\d]+)/notes/(?P<id>[\d]+)` | GET, DELETE | id; order_id; force | - | yes |
| `/wc/v3/orders/(?P<order_id>[\d]+)/refunds` | GET, POST | order_id; search; after; before; modified_after; modified_before; dates_are_gmt; exclude; include; order (asc / desc); orderby (date / id / include / title / slug / modified); parent; parent_exclude; dp; order_item_display_meta; include_meta; exclude_meta; amount; reason; refunded_by; meta_data; shipping_lines; fee_lines; api_refund; api_restock; compute_totals | - | yes |
| `/wc/v3/orders/(?P<order_id>[\d]+)/refunds/(?P<id>[\d]+)` | GET, DELETE | order_id; id; force | - | yes |
| `/wc/v3/orders/(?P<order_id>[\d]+)/refunds/preview` | POST | order_id; line_items | - | yes |
| `/wc/v3/orders/batch` | POST, PUT, PATCH | parent_id; created_via; status (auto-draft / pending / processing / on-hold / completed / cancelled / refunded / failed / checkout-draft); currency (AED / AFN / ALL / AMD / ANG / AOA / ARS / AUD / AWG / AZN / BAM / BBD / BDT / BGN and 150 more); customer_id; customer_note; billing; shipping; payment_method; payment_method_title; transaction_id; meta_data; line_items; shipping_lines; fee_lines; coupon_lines; set_paid; manual_update | - | yes |
| `/wc/v3/orders/statuses` | GET | - | - | yes |
| `/wc/v3/payment_gateways` | GET | - | - | yes |
| `/wc/v3/payment_gateways/(?P<id>[\w-]+)` | GET, POST, PUT, PATCH | id; title; description; order; enabled; settings | - | yes |
| `/wc/v3/paypal-buttons/cancel-payment` | POST | - | - | yes |
| `/wc/v3/paypal-buttons/create-order` | POST | - | - | yes |
| `/wc/v3/paypal-standard/update-shipping` | POST | - | - | yes |
| `/wc/v3/paypal-webhooks` | POST | - | - | yes |
| `/wc/v3/pickup-locations` | POST, PUT, PATCH | pickup_location_settings; pickup_locations | - | yes |
| `/wc/v3/products` | GET, POST | search; after; before; modified_after; modified_before; dates_are_gmt; exclude; include; order (asc / desc); orderby (date / id / include / title / slug / modified / popularity / rating / post__in / price / sales / menu_order / random / popularity and 5 more); parent; parent_exclude; brand; slug; status (any / future / trash / draft / pending / private / publish); type (simple / grouped / external / variable); sku; featured; category; tag; shipping_class; attribute; attribute_term; on_sale; min_price; max_price; include_meta; exclude_meta; image_size; stock_status (instock / outofstock / onbackorder); search_sku; search_name_or_sku; search_fields (name / global_unique_id / description / short_description / sku); include_status (any / future / trash / draft / pending / private / publish); exclude_status (future / trash / draft / pending / private / publish); include_types (simple / grouped / external / variable); exclude_types (simple / grouped / external / variable); downloadable; virtual; pos_products_only; name; date_created; date_created_gmt; status (draft / pending / private / publish / future / auto-draft / trash); catalog_visibility (visible / catalog / search / hidden); description; short_description; global_unique_id; regular_price; sale_price; date_on_sale_from; date_on_sale_from_gmt; date_on_sale_to; date_on_sale_to_gmt; downloads; download_limit; download_expiry; external_url; button_text; tax_status (taxable / shipping / none); tax_class; manage_stock; stock_quantity; backorders (no / notify / yes); low_stock_amount; sold_individually; weight; dimensions; reviews_allowed; post_password; upsell_ids; cross_sell_ids; parent_id; purchase_note; categories; brands; tags; images; attributes; default_attributes; menu_order; meta_data | - | yes |
| `/wc/v3/products/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; image_size; name; slug; date_created; date_created_gmt; type (simple / grouped / external / variable); status (draft / pending / private / publish / future / auto-draft / trash); featured; catalog_visibility (visible / catalog / search / hidden); description; short_description; sku; global_unique_id; regular_price; sale_price; date_on_sale_from; date_on_sale_from_gmt; date_on_sale_to; date_on_sale_to_gmt; virtual; downloadable; downloads; download_limit; download_expiry; external_url; button_text; tax_status (taxable / shipping / none); tax_class; manage_stock; stock_quantity; stock_status (instock / outofstock / onbackorder); backorders (no / notify / yes); low_stock_amount; sold_individually; weight; dimensions; shipping_class; reviews_allowed; post_password; upsell_ids; cross_sell_ids; parent_id; purchase_note; categories; brands; tags; images; attributes; default_attributes; menu_order; meta_data; force | - | yes |
| `/wc/v3/products/(?P<id>[\d]+)/duplicate` | POST | id; name; slug; date_created; date_created_gmt; type (simple / grouped / external / variable); status (draft / pending / private / publish / future / auto-draft / trash); featured; catalog_visibility (visible / catalog / search / hidden); description; short_description; sku; global_unique_id; regular_price; sale_price; date_on_sale_from; date_on_sale_from_gmt; date_on_sale_to; date_on_sale_to_gmt; virtual; downloadable; downloads; download_limit; download_expiry; external_url; button_text; tax_status (taxable / shipping / none); tax_class; manage_stock; stock_quantity; stock_status (instock / outofstock / onbackorder); backorders (no / notify / yes); low_stock_amount; sold_individually; weight; dimensions; shipping_class; reviews_allowed; post_password; upsell_ids; cross_sell_ids; parent_id; purchase_note; categories; brands; tags; images; attributes; default_attributes; menu_order; meta_data | - | yes |
| `/wc/v3/products/(?P<id>[\d]+)/related` | GET | id | - | yes |
| `/wc/v3/products/(?P<product_id>[\d]+)/variations` | GET, POST | product_id; search; after; before; modified_after; modified_before; dates_are_gmt; exclude; include; order (asc / desc); orderby (date / id / include / title / slug / modified / menu_order); parent; parent_exclude; slug; status (any / future / trash / draft / pending / private / publish); sku; on_sale; min_price; max_price; include_meta; exclude_meta; image_size; stock_status (instock / outofstock / onbackorder); has_price; attributes; virtual; downloadable; include_status (any / future / trash / draft / pending / private / publish); exclude_status (future / trash / draft / pending / private / publish); pos_products_only; description; global_unique_id; regular_price; sale_price; date_on_sale_from; date_on_sale_from_gmt; date_on_sale_to; date_on_sale_to_gmt; status (draft / pending / private / publish); downloads; download_limit; download_expiry; tax_status (taxable / shipping / none); tax_class; manage_stock; stock_quantity; backorders (no / notify / yes); low_stock_amount; weight; dimensions; shipping_class; image; gallery_image_ids; menu_order; meta_data | - | yes |
| `/wc/v3/products/(?P<product_id>[\d]+)/variations/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | product_id; id; image_size; description; sku; global_unique_id; regular_price; sale_price; date_on_sale_from; date_on_sale_from_gmt; date_on_sale_to; date_on_sale_to_gmt; status (draft / pending / private / publish); virtual; downloadable; downloads; download_limit; download_expiry; tax_status (taxable / shipping / none); tax_class; manage_stock; stock_quantity; stock_status (instock / outofstock / onbackorder); backorders (no / notify / yes); low_stock_amount; weight; dimensions; shipping_class; image; gallery_image_ids; attributes; menu_order; meta_data; force | - | yes |
| `/wc/v3/products/(?P<product_id>[\d]+)/variations/batch` | POST, PUT, PATCH | product_id; description; sku; global_unique_id; regular_price; sale_price; date_on_sale_from; date_on_sale_from_gmt; date_on_sale_to; date_on_sale_to_gmt; status (draft / pending / private / publish); virtual; downloadable; downloads; download_limit; download_expiry; tax_status (taxable / shipping / none); tax_class; manage_stock; stock_quantity; stock_status (instock / outofstock / onbackorder); backorders (no / notify / yes); low_stock_amount; weight; dimensions; shipping_class; image; gallery_image_ids; attributes; menu_order; meta_data | - | yes |
| `/wc/v3/products/(?P<product_id>[\d]+)/variations/generate` | POST | product_id; delete; default_values; description; sku; global_unique_id; regular_price; sale_price; date_on_sale_from; date_on_sale_from_gmt; date_on_sale_to; date_on_sale_to_gmt; status (draft / pending / private / publish); virtual; downloadable; downloads; download_limit; download_expiry; tax_status (taxable / shipping / none); tax_class; manage_stock; stock_quantity; stock_status (instock / outofstock / onbackorder); backorders (no / notify / yes); low_stock_amount; weight; dimensions; shipping_class; image; gallery_image_ids; attributes; menu_order; meta_data | - | yes |
| `/wc/v3/products/attributes` | GET, POST | name; slug; type (select); order_by (menu_order / name / name_num / id); has_archives | - | yes |
| `/wc/v3/products/attributes/(?P<attribute_id>[\d]+)/terms` | GET, POST | attribute_id; search; exclude; include; order (asc / desc); orderby (id / include / name / slug / term_group / description / count); hide_empty; parent; product; slug; name; description; menu_order | - | yes |
| `/wc/v3/products/attributes/(?P<attribute_id>[\d]+)/terms/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; attribute_id; name; slug; description; menu_order; force | - | yes |
| `/wc/v3/products/attributes/(?P<attribute_id>[\d]+)/terms/batch` | POST, PUT, PATCH | attribute_id; name; slug; description; menu_order | - | yes |
| `/wc/v3/products/attributes/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; name; slug; type (select); order_by (menu_order / name / name_num / id); has_archives; force | - | yes |
| `/wc/v3/products/attributes/batch` | POST, PUT, PATCH | name; slug; type (select); order_by (menu_order / name / name_num / id); has_archives | - | yes |
| `/wc/v3/products/batch` | POST, PUT, PATCH | name; slug; date_created; date_created_gmt; type (simple / grouped / external / variable); status (draft / pending / private / publish / future / auto-draft / trash); featured; catalog_visibility (visible / catalog / search / hidden); description; short_description; sku; global_unique_id; regular_price; sale_price; date_on_sale_from; date_on_sale_from_gmt; date_on_sale_to; date_on_sale_to_gmt; virtual; downloadable; downloads; download_limit; download_expiry; external_url; button_text; tax_status (taxable / shipping / none); tax_class; manage_stock; stock_quantity; stock_status (instock / outofstock / onbackorder); backorders (no / notify / yes); low_stock_amount; sold_individually; weight; dimensions; shipping_class; reviews_allowed; post_password; upsell_ids; cross_sell_ids; parent_id; purchase_note; categories; brands; tags; images; attributes; default_attributes; menu_order; meta_data | - | yes |
| `/wc/v3/products/brands` | GET, POST | search; exclude; include; order (asc / desc); orderby (id / include / name / slug / term_group / description / count); hide_empty; parent; product; slug; name; description; display (default / products / subcategories / both); image; menu_order | - | yes |
| `/wc/v3/products/brands/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; name; slug; parent; description; display (default / products / subcategories / both); image; menu_order; force | - | yes |
| `/wc/v3/products/brands/batch` | POST, PUT, PATCH | name; slug; parent; description; display (default / products / subcategories / both); image; menu_order | - | yes |
| `/wc/v3/products/categories` | GET, POST | search; exclude; include; order (asc / desc); orderby (id / include / name / slug / term_group / description / count); hide_empty; parent; product; slug; name; description; display (default / products / subcategories / both); image | - | yes |
| `/wc/v3/products/categories/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; name; slug; parent; description; display (default / products / subcategories / both); image; force | - | yes |
| `/wc/v3/products/categories/batch` | POST, PUT, PATCH | name; slug; parent; description; display (default / products / subcategories / both); image | - | yes |
| `/wc/v3/products/custom-fields/names` | GET | search; order (asc / desc) | - | yes |
| `/wc/v3/products/reviews` | GET, POST | search; after; before; exclude; include; order (asc / desc); orderby (date / date_gmt / id / include / product); reviewer; reviewer_exclude; reviewer_email; product; status (all / hold / approved / spam / trash); product_id; product_name; status (approved / hold / spam / unspam / trash / untrash); review; rating | - | yes |
| `/wc/v3/products/reviews/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; product_id; product_name; status (approved / hold / spam / unspam / trash / untrash); reviewer; reviewer_email; review; rating; force | - | yes |
| `/wc/v3/products/reviews/batch` | POST, PUT, PATCH | product_id; product_name; status (approved / hold / spam / unspam / trash / untrash); reviewer; reviewer_email; review; rating | - | yes |
| `/wc/v3/products/shipping_classes` | GET, POST | search; exclude; include; order (asc / desc); orderby (id / include / name / slug / term_group / description / count); hide_empty; parent; product; slug; name; description | - | yes |
| `/wc/v3/products/shipping_classes/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; name; slug; description; force | - | yes |
| `/wc/v3/products/shipping_classes/batch` | POST, PUT, PATCH | name; slug; description | - | yes |
| `/wc/v3/products/shipping_classes/slug-suggestion` | GET | name; slug; description | - | yes |
| `/wc/v3/products/suggested-products` | GET | search; after; before; modified_after; modified_before; dates_are_gmt; exclude; include; order (asc / desc); orderby (date / id / include / title / slug / modified / popularity / rating / post__in / price / sales / menu_order / random / popularity and 2 more); parent; parent_exclude; brand; slug; status (any / future / trash / draft / pending / private / publish); type (simple / grouped / external / variable); sku; featured; category; tag; shipping_class; attribute; attribute_term; in_stock; on_sale; min_price; max_price; include_meta; exclude_meta; image_size; categories; tags; limit | - | yes |
| `/wc/v3/products/tags` | GET, POST | search; exclude; include; order (asc / desc); orderby (id / include / name / slug / term_group / description / count); hide_empty; parent; product; slug; name; description | - | yes |
| `/wc/v3/products/tags/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; name; slug; description; force | - | yes |
| `/wc/v3/products/tags/batch` | POST, PUT, PATCH | name; slug; description | - | yes |
| `/wc/v3/refunds` | GET | search; after; before; modified_after; modified_before; dates_are_gmt; exclude; include; order (asc / desc); orderby (date / id / include / title / slug / modified); parent; parent_exclude; dp; order_item_display_meta; include_meta; exclude_meta | - | yes |
| `/wc/v3/reports` | GET | - | - | yes |
| `/wc/v3/reports/coupons/totals` | GET | - | - | yes |
| `/wc/v3/reports/customers/totals` | GET | - | - | yes |
| `/wc/v3/reports/orders/totals` | GET | - | - | yes |
| `/wc/v3/reports/products/totals` | GET | - | - | yes |
| `/wc/v3/reports/reviews/totals` | GET | - | - | yes |
| `/wc/v3/reports/sales` | GET | period (week / month / last_month / year); date_min; date_max | - | yes |
| `/wc/v3/reports/top_sellers` | GET | period (week / month / last_month / year); date_min; date_max | - | yes |
| `/wc/v3/settings` | GET | - | - | yes |
| `/wc/v3/settings/(?P<group_id>[\w-]+)` | GET | group | - | yes |
| `/wc/v3/settings/(?P<group_id>[\w-]+)/(?P<id>[\w-]+)` | GET, POST, PUT, PATCH | group; id; value | - | yes |
| `/wc/v3/settings/(?P<group_id>[\w-]+)/batch` | POST, PUT, PATCH | group; value | - | yes |
| `/wc/v3/settings/batch` | POST, PUT, PATCH | - | - | yes |
| `/wc/v3/shipping/zones` | GET, POST | name; order | - | yes |
| `/wc/v3/shipping/zones/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; name; order; force | - | yes |
| `/wc/v3/shipping/zones/(?P<id>[\d]+)/locations` | GET, POST, PUT, PATCH | id; code; type (postcode / state / country / continent) | - | yes |
| `/wc/v3/shipping/zones/(?P<zone_id>[\d]+)/methods` | GET, POST | zone_id; order; enabled; settings; method_id | - | yes |
| `/wc/v3/shipping/zones/(?P<zone_id>[\d]+)/methods/(?P<instance_id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | zone_id; instance_id; order; enabled; settings; force | - | yes |
| `/wc/v3/shipping_methods` | GET | - | - | yes |
| `/wc/v3/shipping_methods/(?P<id>[\w-]+)` | GET | id | - | yes |
| `/wc/v3/system_status` | GET | - | - | yes |
| `/wc/v3/system_status/tools` | GET | - | - | yes |
| `/wc/v3/system_status/tools/(?P<id>[\w-]+)` | GET, POST, PUT, PATCH | id; name; action; description; success; message | - | yes |
| `/wc/v3/taxes` | GET, POST | order (asc / desc); orderby (id / order / priority); class (standard / reduced-rate / zero-rate); country; state; postcode; city; rate; name; priority; compound; shipping; order; postcodes; cities | - | yes |
| `/wc/v3/taxes/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; country; state; postcode; city; rate; name; priority; compound; shipping; order; class (standard / reduced-rate / zero-rate); postcodes; cities; force | - | yes |
| `/wc/v3/taxes/batch` | POST, PUT, PATCH | country; state; postcode; city; rate; name; priority; compound; shipping; order; class (standard / reduced-rate / zero-rate); postcodes; cities | - | yes |
| `/wc/v3/taxes/classes` | GET, POST | name | - | yes |
| `/wc/v3/taxes/classes/(?P<slug>\w[\w\s\-]*)` | GET, DELETE | slug; force | - | yes |
| `/wc/v3/variations` | GET | search; after; before; modified_after; modified_before; dates_are_gmt; exclude; include; order (asc / desc); orderby (date / id / include / title / slug / modified / menu_order); parent; parent_exclude; slug; status (any / future / trash / draft / pending / private / publish); sku; on_sale; min_price; max_price; include_meta; exclude_meta; image_size; stock_status (instock / outofstock / onbackorder); has_price; attributes; virtual; downloadable; include_status (any / future / trash / draft / pending / private / publish); exclude_status (future / trash / draft / pending / private / publish); pos_products_only | - | yes |
| `/wc/v3/webhooks` | GET, POST | search; after; before; exclude; include; order (asc / desc); orderby (date / id / title); status (all / active / paused / disabled); name; status (active / paused / disabled); topic; secret; delivery_url | - | yes |
| `/wc/v3/webhooks/(?P<id>[\d]+)` | GET, POST, PUT, PATCH, DELETE | id; name; status (active / paused / disabled); topic; secret; force | - | yes |
| `/wc/v3/webhooks/batch` | POST, PUT, PATCH | name; status (active / paused / disabled); topic; secret | - | yes |

### D: `wccom-site/v3` (8 routes)

Home: Out of scope: WooCommerce.com connection internals.

| Route | Methods | Arguments | Home | QUILL today |
|---|---|---|---|---|
| `/wccom-site/v3` | GET | namespace | - | no |
| `/wccom-site/v3/connection/disconnect` | POST, PUT, PATCH | - | - | no |
| `/wccom-site/v3/connection/status` | GET | - | - | no |
| `/wccom-site/v3/installer` | POST, PUT, PATCH | product-id; run-until-step (get_product_info / download_product / unpack_product / move_product / activate_product); idempotency-key | - | no |
| `/wccom-site/v3/installer/(?P<product_id>\d+)/state` | GET | product_id | - | no |
| `/wccom-site/v3/installer/reset` | POST, PUT, PATCH | product-id; idempotency-key | - | no |
| `/wccom-site/v3/ssr` | GET | - | - | no |
| `/wccom-site/v3/status` | GET | - | - | no |

### D: `wp-abilities/v1` (6 routes)

Home: Sites > site > Abilities (section 12).

| Route | Methods | Arguments | Home | QUILL today |
|---|---|---|---|---|
| `/wp-abilities/v1` | GET | namespace | - | yes |
| `/wp-abilities/v1/abilities` | GET | category; namespace; meta | - | yes |
| `/wp-abilities/v1/abilities/(?P<name>[a-zA-Z0-9\-\/]+)` | GET | name | - | yes |
| `/wp-abilities/v1/abilities/(?P<name>[a-zA-Z0-9\-\/]+?)/run` | GET, POST, PUT, PATCH, DELETE | name; input | - | yes |
| `/wp-abilities/v1/categories` | GET | - | - | yes |
| `/wp-abilities/v1/categories/(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*)` | GET | slug | - | yes |

### D: `wp-block-editor/v1` (4 routes)

Home: Editor plumbing: block editor settings, URL details, navigation fallback.

| Route | Methods | Arguments | Home | QUILL today |
|---|---|---|---|---|
| `/wp-block-editor/v1` | GET | namespace | - | yes |
| `/wp-block-editor/v1/export` | GET | - | - | yes |
| `/wp-block-editor/v1/navigation-fallback` | GET | - | - | yes |
| `/wp-block-editor/v1/url-details` | GET | url | - | yes |

### D: `wp-site-health/v1` (8 routes)

Home: Sites > site > Site Health; Needs My Attention > Site Health.

| Route | Methods | Arguments | Home | QUILL today |
|---|---|---|---|---|
| `/wp-site-health/v1` | GET | namespace | - | yes |
| `/wp-site-health/v1/directory-sizes` | GET | - | - | yes |
| `/wp-site-health/v1/tests/authorization-header` | GET | - | - | yes |
| `/wp-site-health/v1/tests/background-updates` | GET | - | - | yes |
| `/wp-site-health/v1/tests/dotorg-communication` | GET | - | - | yes |
| `/wp-site-health/v1/tests/https-status` | GET | - | - | yes |
| `/wp-site-health/v1/tests/loopback-requests` | GET | - | - | yes |
| `/wp-site-health/v1/tests/page-cache` | GET | - | - | yes |

### D: `yoast/v1` (61 routes)

Home: Post and page Properties > SEO; Sites > site > SEO (Yoast settings, redirects where the plan offers them).

| Route | Methods | Arguments | Home | QUILL today |
|---|---|---|---|---|
| `/yoast/v1` | GET | namespace | - | yes |
| `/yoast/v1/action_tracking` | POST | action | - | yes |
| `/yoast/v1/ai/free_sparks` | POST | - | - | yes |
| `/yoast/v1/ai_content_planner/banner_permanent_dismissal` | POST | is_dismissed | - | yes |
| `/yoast/v1/ai_content_planner/get_outline` | POST | post_type; language; editor (classic / elementor / gutenberg); title; intent; explanation; keyphrase; meta_description; category; recent_content | - | yes |
| `/yoast/v1/ai_content_planner/get_suggestions` | GET | post_type; language; editor (classic / elementor / gutenberg) | - | yes |
| `/yoast/v1/ai_generator/bust_subscription_cache` | POST | - | - | yes |
| `/yoast/v1/ai_generator/callback` | POST | access_jwt; refresh_jwt; code_challenge; user_id | - | yes |
| `/yoast/v1/ai_generator/consent` | POST | consent | - | yes |
| `/yoast/v1/ai_generator/get_suggestions` | POST | type (seo-title / meta-description / product-seo-title / product-meta-description / product-taxonomy-seo-title / product-taxonomy-meta-description / taxonomy-seo-title / taxonomy-meta-description); prompt_content; focus_keyphrase; language; platform (Google / Facebook / Twitter); editor (classic / elementor / gutenberg) | - | yes |
| `/yoast/v1/ai_generator/get_usage` | POST | is_woo_product_entity | - | yes |
| `/yoast/v1/ai_generator/refresh_callback` | POST | access_jwt; refresh_jwt; code_challenge; user_id | - | yes |
| `/yoast/v1/alerts/dismiss` | POST | key | - | yes |
| `/yoast/v1/available_posts` | GET | search; postType | - | yes |
| `/yoast/v1/bulk_editor/posts` | GET | content_type; search; status (publish / draft / pending / future); needs_improvement (seo_title / meta_description / social_title / social_description); include | - | yes |
| `/yoast/v1/bulk_editor/posts_content` | GET | ids | - | yes |
| `/yoast/v1/bulk_editor/update_scores` | POST | items | - | yes |
| `/yoast/v1/bulk_editor/update_search` | POST | items | - | yes |
| `/yoast/v1/bulk_editor/update_social` | POST | items | - | yes |
| `/yoast/v1/complete_task` | POST | options | - | yes |
| `/yoast/v1/configuration/check_capability` | GET | user_id | - | yes |
| `/yoast/v1/configuration/enable_tracking` | POST | tracking | - | yes |
| `/yoast/v1/configuration/get_configuration_state` | GET | - | - | yes |
| `/yoast/v1/configuration/save_configuration_state` | POST | finishedSteps | - | yes |
| `/yoast/v1/configuration/site_representation` | POST | company_or_person (company / person); company_name; company_logo; company_logo_id; person_logo; person_logo_id; company_or_person_user_id; description | - | yes |
| `/yoast/v1/configuration/social_profiles` | POST | facebook_site; twitter_site; other_social_urls | - | yes |
| `/yoast/v1/file_size` | GET | url | - | yes |
| `/yoast/v1/get_head` | GET | url | - | yes |
| `/yoast/v1/get_tasks` | GET | options | - | yes |
| `/yoast/v1/import/(?P<plugin>[\w-]+)/(?P<type>[\w-]+)` | POST | - | - | yes |
| `/yoast/v1/indexing/complete` | POST | - | - | yes |
| `/yoast/v1/indexing/general` | POST | - | - | yes |
| `/yoast/v1/indexing/indexables-complete` | POST | - | - | yes |
| `/yoast/v1/indexing/post-type-archives` | POST | - | - | yes |
| `/yoast/v1/indexing/posts` | POST | - | - | yes |
| `/yoast/v1/indexing/prepare` | POST | - | - | yes |
| `/yoast/v1/indexing/terms` | POST | - | - | yes |
| `/yoast/v1/integrations/set_active` | POST | active; integration | - | yes |
| `/yoast/v1/introductions/(?P<introduction_id>[\w-]+)/seen` | POST | introduction_id; is_seen | - | yes |
| `/yoast/v1/link-indexing/posts` | POST | - | - | yes |
| `/yoast/v1/link-indexing/terms` | POST | - | - | yes |
| `/yoast/v1/meta/search` | GET | - | - | yes |
| `/yoast/v1/new-content-type-visibility/dismiss-post-type` | POST | postTypeName | - | yes |
| `/yoast/v1/new-content-type-visibility/dismiss-taxonomy` | POST | taxonomyName | - | yes |
| `/yoast/v1/readability_scores` | GET | contentType; taxonomy; term; troubleshooting | - | yes |
| `/yoast/v1/semrush/authenticate` | POST | code | - | yes |
| `/yoast/v1/semrush/country_code` | POST | country_code | - | yes |
| `/yoast/v1/semrush/related_keyphrases` | GET | keyphrase; country_code | - | yes |
| `/yoast/v1/seo_scores` | GET | contentType; taxonomy; term; troubleshooting | - | yes |
| `/yoast/v1/setup_steps_tracking` | POST | setup_widget_loaded (yes / no); first_interaction_stage (install / activate / setup / grantConsent / successfullyConnected); last_interaction_stage (install / activate / setup / grantConsent / successfullyConnected); setup_widget_temporarily_dismissed (yes / no); setup_widget_permanently_dismissed (yes / no) | - | yes |
| `/yoast/v1/site_kit_configuration_permanent_dismissal` | POST | is_dismissed | - | yes |
| `/yoast/v1/statistics` | GET | - | - | yes |
| `/yoast/v1/wincher/account/limit` | GET | - | - | yes |
| `/yoast/v1/wincher/account/upgrade-campaign` | GET | - | - | yes |
| `/yoast/v1/wincher/authenticate` | POST | code; websiteId | - | yes |
| `/yoast/v1/wincher/authorization-url` | GET | - | - | yes |
| `/yoast/v1/wincher/keyphrases` | POST | keyphrases; permalink; startAt | - | yes |
| `/yoast/v1/wincher/keyphrases/track` | POST | keyphrases | - | yes |
| `/yoast/v1/wincher/keyphrases/untrack` | DELETE | - | - | yes |
| `/yoast/v1/wistia_embed_permission` | GET, POST | value | - | yes |
| `/yoast/v1/workouts` | GET, POST | - | - | yes |

