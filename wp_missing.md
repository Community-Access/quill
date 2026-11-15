# WordPress: what is still missing

Checked 2026-11-14 on branch `codex/workbench-combined-2026-11-10`, uncommitted tree.

## How this was checked, and how to read it

I made a list of the jobs a WordPress site owner, editor, author, contributor and administrator actually do. I took it from every menu and submenu of wp-admin (WordPress 6.9 and 7.x), plus WooCommerce, The Events Calendar, Yoast SEO, Gravity Forms, Paid Memberships Pro, Redirection and QUILL Accessible Forms, and from the REST API reference. Then I looked for each job in the code: the editors' WordPress commands, the WordPress Workbench's tree, its row actions, the wp-admin map, the route coverage rules and the scope matrix. I also read wordpress.md (9.16 to 9.18 and section 19), complete.md section 7 and the Workbench PRD.

A job counts as done only when code does it. A doc line saying it is done was not enough.

Each job lands in one of five places:

- **Done**: QUILL does it, in the editor or the Workbench.
- **wp-admin only**: WordPress has no REST route for it, and QUILL already says so and opens the right wp-admin screen. Nothing to build unless we go outside REST.
- **Being built today**: another session is writing it right now. The files exist but are not finished or tested yet. Check again when that work lands.
- **Missing**: there is a route, or QUILL could do it locally, and nothing does it yet.
- **Deferred**: security, backups and updates, which you asked to wait. They have their own section near the end.

One caution. Other sessions were changing WordPress files while I read, so this is a snapshot. The Shop, Events and SEO lines were moving as I wrote.

## Built since this audit (2026-11-14, later the same day)

These were missing when the audit was written and are now built, with tests; none has met a live site yet. Their lines are gone from the lists below.

- Earlier Versions on post, page and custom-type rows in the Workbench.
- Replace File on a Media Library row: in place where a plugin route exists, otherwise upload and point every use at the new file (Ctrl+Z puts them back), or open Enable Media Replace, with a redirect offered through Redirection.
- Tools > WXR Files: Export Site as WXR, and Import WXR as Drafts.
- Check for Updates on WordPress.org: plugins, themes and WordPress itself say when an update is waiting.
- Check Every Link under By Name > Links, for the whole site, with a count and a stop.
- A Gravity Forms response's answers, edited on its Properties.
- wp-admin for This Place reaches the plugins' own screens, and the WooCommerce Settings row is corrected.
- Menus: Add Menu Item, Add New Pages Automatically, and Arrange Items (the Menus window on that menu).
- Offer to Ask the Site on an ability row, which had become impossible to turn on.

## The short version

The everyday jobs are done: writing, publishing, scheduling, media, comments, categories and tags, people, menus, widgets, templates and styles. What is left falls into four groups:

- A handful of small gaps in core WordPress (menu auto-add, revisions from a Workbench row, replacing a media file, WXR import and export, a complete link check).
- Plugin depth: the rest of WooCommerce, Gravity Forms entry editing, membership levels, and Redirection's groups and options.
- Updates, backups and security, which need either a plugin's API or a way in that is not REST (WP-CLI over SSH).
- Nothing at all has been tried on a live site with a screen reader since the Workbench work began.

| Area | Jobs | Done | wp-admin only | Being built today | Missing | Deferred |
|---|---|---|---|---|---|---|
| Posts and pages | 27 | 25 | 1 | 0 | 1 | 0 |
| Media | 15 | 12 | 2 | 0 | 1 | 0 |
| Categories, tags, taxonomies | 6 | 6 | 0 | 0 | 0 | 0 |
| Comments | 9 | 7 | 2 | 0 | 0 | 0 |
| Users | 15 | 10 | 5 | 0 | 0 | 0 |
| Menus and widgets | 11 | 10 | 0 | 0 | 1 | 0 |
| Appearance | 10 | 7 | 3 | 0 | 0 | 0 |
| Plugins and themes | 10 | 6 | 2 | 0 | 1 | 1 |
| Settings | 10 | 4 | 6 | 0 | 0 | 0 |
| Tools | 12 | 6 | 3 | 0 | 3 | 0 |
| Forms | 14 | 11 | 1 | 0 | 2 | 0 |
| Shop (WooCommerce) | 30 | 12 | 2 | 7 | 9 | 0 |
| Events | 9 | 5 | 3 | 1 | 0 | 0 |
| SEO | 9 | 4 | 1 | 2 | 2 | 0 |
| Memberships | 10 | 6 | 1 | 0 | 3 | 0 |
| Redirects | 3 | 2 | 0 | 0 | 1 | 0 |
| Multisite | 3 | 2 | 1 | 0 | 0 | 0 |
| Maintenance | 9 | 2 | 2 | 0 | 2 | 3 |
| Total | 212 | 137 | 35 | 10 | 26 | 4 |

These are counts from my list of jobs, not from a code metric, so read them as rough. The "wp-admin only" column is mostly WordPress's limit, not QUILL's.

## Missing in QUILL

The most useful to a site owner come first in each area. "Route" means the REST route that does it. "wp-admin" means there is no route.

### Posts and pages

Nothing missing.

Already done and worth knowing: Markdown or HTML on new items, open existing items as HTML (blocks kept) or Markdown (blocks kept as islands), drafts, publish, schedule, preview, conflict check, Properties with author, template, parent, format, pingbacks and featured image, bulk edit with Undo, Trash, Empty Trash, duplicate, the review queue, the calendar, site-wide Find and Replace, importing folders and spreadsheets as drafts, and Copy to Site. The post lock is wp-admin only, and QUILL opens the edit screen and says why.

### Media

Scaling the original and the media size settings are wp-admin only, and QUILL already says so.

### Categories, tags and custom taxonomies

Nothing missing. Add, rename, merge, convert, delete, hierarchy, term fields and Advanced Custom Fields, custom taxonomies found from the site, and Across Sites all work. Defining a new taxonomy needs the QUILL Site Types plugin, which has never run in a real WordPress (see "Built but not yet tried live").

### Comments

Nothing missing that REST allows. The comment blocklist (`disallowed_keys`), moderation keys, avatars, threading and notification settings are wp-admin only, and the scope matrix says so.

### Users

Nothing missing that REST allows. Password reset emails, the welcome email, Log Out Everywhere, profile preferences and editing roles are wp-admin only. Editing roles needs a plugin such as Members or User Role Editor, and neither has a REST API that I know of (unverified). QUILL opens the right screen for each.

### Menus and widgets

Menus can be created (New Here), deleted (Shift+Delete), have items added from the Workbench (Add Menu Item, or Ctrl+N with a menu selected) and edited (the editor's Menus window), add new top-level pages automatically (a check box on Properties, and a command), have locations set and earlier versions restored. Widgets can be added, changed, moved, removed and previewed.

### Appearance

Nothing missing that REST allows. Activating, installing, updating or deleting a theme, the classic Customizer and the theme file editor are wp-admin only, because `wp/v2/themes` only reads. Global Styles, templates and template parts (edit, create, reset, earlier versions), Additional CSS, patterns and fonts all work.

### Plugins and themes

- **Running updates** is in the deferred section below, because REST cannot do it.

Uploading a plugin as a zip file (every premium plugin) and turning automatic updates on or off are wp-admin only.

### Settings

Nothing missing that REST allows. Permalinks, media sizes, the privacy policy page, who may register and the default role, feeds, post by email and search engine visibility are wp-admin only. Search engine visibility is judged from the sitemap and says so.

### Tools

Site Health's Info tab and the privacy export and erase requests are wp-admin only, and QUILL opens them without pretending a request was done.

### Forms

QAF is covered end to end: build, publish, settings, status, delete, entries, views, spam and spam settings. Gravity Forms is close.

- **More than one notification or confirmation on a Gravity Form.** Who: forms that send different emails by answer. Route: the `notifications` and `confirmations` objects inside `gf/v2/forms/{id}`. Today QUILL's form editor edits the default confirmation and the Admin Notification and keeps the rest untouched.

Gravity Forms' own settings, add-ons and licence are wp-admin only.

### Shop (WooCommerce)

Being built today, in new uncommitted files (`workbench_shop_care.py`, `workbench_shop_setup.py`): product reviews, webhooks, customer details, editing one variation, shipping zones with their locations and methods, tax rates and classes, attributes and their terms, and brands. I found no commands wired to them in the window yet.

Still missing after that:

- **Edit every product field.** Who: shop managers. Route: `POST wc/v3/products/{id}`. Edit Product changes price, sale price, stock, status and categories only. Missing: SKU, description, short description, sale dates, weight and dimensions, shipping class, images, downloads, upsells and cross-sells, tax class.
- **Create an order, or change its items and addresses.** Who: shops taking phone orders. Route: `POST wc/v3/orders`, `POST wc/v3/orders/{id}`.
- **Resend an order email or invoice.** Who: a customer who says the receipt never came. Route: `wc/v3/orders/{id}/actions/send_email` and `send_order_details`, which were on the test site's index on 2026-11-04.
- **Payment gateways: turn on or off, and their settings.** Route: `wc/v3/payment_gateways/{id}`. Any key fields must stay write-only, as Store Settings already does.
- **System status and its tools** (clear transients, recount terms). Route: `wc/v3/system_status`, `system_status/tools/{id}`. This also gives the PHP and database versions that core REST does not.

Also missing but less urgent: editing many products at once (`products/batch`), generating variations (`products/{id}/variations/generate`), shipping classes (`products/shipping_classes`), and Analytics (`wc-analytics/reports/*`). Scheduled Actions and the extensions marketplace are wp-admin only. Subscriptions and Bookings are paid extensions with their own routes, not in scope.

### Events (The Events Calendar)

Events, venues and organizers (list, past, filter, new, edit, trash) are done. Event categories and tags are being built today (`workbench_event_terms.py`). Recurring events need Events Calendar Pro, and its series is changed in wp-admin, which QUILL says. Settings and the importer are wp-admin only. Tickets and RSVP (Event Tickets) are deferred plugins.

### SEO (Yoast SEO)

SEO title, description, keyphrase, show in search results, search appearance and site scores are done. Social title and description and the bulk editor are being built today (`workbench_seo_bulk.py`).

Still missing:

- **Canonical address, primary category and schema type per post.** Route: only where Yoast registers that post meta for REST, which most sites do not. I have not verified which of these the bulk editor routes carry. Otherwise they stay in the post's Yoast panel.
- **Rank Math.** It is the other common SEO plugin and has its own `rankmath/v1` namespace. QUILL has no adapter, so it is read only, under More from This Site. Whether to support it is a decision (below).

Yoast's settings, redirects (Premium), schema settings and indexing are wp-admin only, and the SEO node lists each with its screen.

### Memberships (Paid Memberships Pro)

Levels, orders, subscriptions and renewals due are listed. Change Membership Level, Cancel Membership, Check Membership Access and discount codes (look up one, make one) work.

- **Create or edit a membership level.** Who: the site owner changing a price or adding a tier. Route: PMPro's abilities, if the site offers a level-writing one, or `pmpro/v1/membership_level` (I believe it takes POST, unverified). Today levels are read only.
- **Members of a level, as a list.** Who: the owner emailing or counting one tier's members. Route: unverified. `pmpro/v1/recent_memberships` exists. Otherwise build it from users plus each person's levels, which is slow on big sites. Today you see a person's memberships one person at a time.
- **Every discount code, as a list.** `pmpro/v1` reads one code at a time. The list works only where an ability offers it, and otherwise opens wp-admin, which QUILL says.

Reports and payment settings are wp-admin only. The wp-admin map has only PMPro's Dashboard. Add Levels, Members, Orders, Discount Codes, Reports and Settings so "wp-admin for This Place" reaches each one.

### Redirects (Redirection)

List, add, change, turn on and off, delete, test an address, and the 404 log are built from Redirection's documentation and have never met a real install.

- **Groups, import and export, and Redirection's options.** Route: `redirection/v1/group`, `/import`, `/export`, `/setting` (from the plugin's docs, unverified). Coverage marks them planned.

### Multisite

Each subsite works as its own site, and Promote to Network is built. The Network Admin screens have no REST routes, so they are wp-admin only.

### Maintenance

- **Missed scheduled tasks beyond posts.** Search and Upkeep lists posts still Scheduled after their time. No other WP-Cron task is visible to REST. WP Crontrol is named as the plugin that lists them. I do not know that it has a REST API (unverified).

Caching (purge), maintenance mode, email delivery tests and an activity log (who changed what) all need plugins. They are in the Administration Areas node with "Open in Dashboard". Updates, backups and security are below.

## Built but not yet tried live

All of the following has tests over recorded or fake answers and none has met a real site with NVDA or JAWS. The checklist is `docs/qa/wordpress-regression-testing.md` (the Workbench section and the Live run section), and wordpress.md section 19 keeps the list.

- The whole Workbench, W1 to W8 and packages 1 to 14. It is now the default, so this comes before the next release.
- WooCommerce, The Events Calendar and Yoast SEO, signed in on the test site, which has all three. A refund only against a gateway's test mode.
- Redirection, and the slug-change redirect offer.
- QAF on the test site (it still runs BAF), the QAF migration, and the spam settings with a live submission.
- Gravity Forms building, conversion, feeds, results and test submissions. These need a licensed Gravity Forms with its REST API on.
- Paid Memberships Pro 3.9 or later on WordPress 6.9 or later, with a role whose PMPro capabilities were changed.
- Advanced Custom Fields read and write, and the QUILL Site Types plugin in a real WordPress.
- Copy to Site and Compare Sites between two real sites, and Promote to Network on a real multisite.
- The Practice Site from an installed build, not only from source.
- WordPress.com sign-in, which waits on the app's client ID.
- Payments: Stripe test mode, a PayPal sandbox, and a screen-reader pass through checkout.

## Security and backups (deferred by Jeff)

You asked to wait on these. Here is exactly what the Workbench can do with core WordPress alone, what needs a plugin, and what first-class support would look like.

### What core REST gives, with no plugin

Already built:

- **People and roles review.** Users with their roles (Group By Role gives counts, so "how many Administrators" is one look), Roles and What They May Do (read only), and guards that stop you removing yourself or the last Administrator.
- **Application passwords.** Every person's passwords with when each was made and last used, revoke one, Revoke Everywhere across sites, and Across Sites > Application Passwords. The one QUILL signs in with cannot be revoked by accident.
- **Plugin and theme versions.** Installed versions, and with consent, WordPress.org's view: closed plugins, plugins not updated in over two years, and what WordPress and PHP versions they need.
- **Site Health's security-related tests over REST.** HTTPS status, whether automatic updates can run, whether the site can reach WordPress.org, and the authorization header.
- **HTTPS and the certificate.** Expiry date from QUILL's own connection, with a warning inside 30 days.
- **XML-RPC.** An unsigned probe that says whether `xmlrpc.php` still answers. No password is sent.

What core REST cannot give, and why:

- **The file-editing constant** (`DISALLOW_FILE_EDIT`), debug mode, the PHP version and the database. These are Site Health's direct tests and its Info tab, which have no REST route. I am not certain `DISALLOW_FILE_EDIT` appears in the Info tab at all (unverified). Today QUILL opens Site Health > Info. A WooCommerce site gives PHP and database versions through `wc/v3/system_status`.
- **Failed sign-ins and lockouts.** Core keeps no record. Only a security plugin does.
- **Sessions.** Who is signed in where, and Log Out Everywhere, are wp-admin only.
- **Who may register, and the default role.** Not in `wp/v2/settings`.

Could be added with no plugin, using the same kind of unsigned probe as XML-RPC, and only for sites you connected:

- whether the user list answers without signing in (`/wp-json/wp/v2/users`), which lets strangers learn usernames;
- whether `wp-login.php?action=register` offers a sign-up form;
- whether `/wp-content/debug.log` can be downloaded;
- whether the home page sends the usual security headers (HSTS, X-Content-Type-Options, frame options);
- application passwords not used in 90 days, and inactive plugins and themes left installed, both from data QUILL already reads.

These would make a "Security Review" node under Site Health, each row a plain sentence with where the answer came from.

### What needs a plugin's API

I checked from what I know of each plugin, not against live installs, so every claim here is **unverified** until it is tried on the test site.

| Plugin | What its API offers | Usable by QUILL? |
|---|---|---|
| Solid Security (`ithemes-security/v1`) | Its own admin is built on REST: site scans, logs, lockouts, banned hosts, user groups, settings | Probably, with an application password and an admin account (unverified) |
| Wordfence (`wordfence/v1`) | Routes exist for Wordfence Central, signed with Central's own tokens | Probably not with an application password (unverified) |
| Shield Security (`shield/v1`) | A documented REST API, Pro only | Possibly, on Pro (unverified) |
| Two Factor (`two-factor/1.0`) | Per-person setup and backup codes | Partly. Whether it lists who has two-factor on is unverified |
| Jetpack Backup and Scan | Backups and threats go through WordPress.com's API, signed in with WordPress.com | Only after WordPress.com sign-in (unverified) |
| UpdraftPlus | No public REST API that I know of. UpdraftCentral uses its own protocol | No (unverified) |
| BlogVault | A hosted service. The plugin talks only to BlogVault | No (unverified) |
| WPvivid | No documented REST API that I know of | No (unverified) |

Two more ways in are worth knowing about, neither of them a security plugin:

- **MainWP.** A separate dashboard WordPress with a documented REST API that runs updates and, through its extensions, backups across child sites. If someone already uses it, QUILL could drive it (unverified for the current version).
- **Managed hosts.** Several hosts (Kinsta, WP Engine among them) offer APIs that list and make backups. This is per host and unverified.

Vulnerability data (a plugin version with a known hole) would come from Wordfence Intelligence, Patchstack or WPScan. Each needs a key, I believe (unverified), and a new egress row with consent.

### What first-class support could look like

- **Security Review node** (no plugin): the rows above, Needs My Attention picking up anything serious, and a weekly Watch.
- **Solid Security adapter** (if it checks out live): lockouts and the scan results as lists, Unban as a previewed action, and the log under the site.
- **Vulnerability check** (with consent): each plugin and theme version compared with one public database, flagged on its row and in Needs My Attention.
- **Backups, the honest version**: Take a Snapshot already saves content and, if asked, media. Say plainly what it leaves out (plugin tables, settings outside REST, theme and plugin files, passwords), add WXR export (above), and for a full backup open the backup plugin's screen.
- **Backups and updates over SSH with WP-CLI**: see Decisions. This is the only path to real updates and full database backups without a plugin.

## Decisions for Jeff

1. **Updates.** REST cannot update anything. The choices are:
   - keep opening Dashboard > Updates;
   - add WP-CLI over SSH for sites where you have SSH (`wp core update`, `wp plugin update`, `wp language core update`, `wp db export`), using QUILL's existing SSH client with its strict host-key policy, every command previewed;
   - drive MainWP or Jetpack where a site already has them.

   Either of the last two runs commands on a server, which is a new kind of thing for QUILL to do.
2. **Backups.** Snapshots and WXR only, or pick one backup plugin or host API to support first-class?
3. **Security.** Build the no-plugin Security Review first? If yes, are the unsigned probes (user list, registration, debug.log, headers) acceptable? They only ask your own site public questions, as the XML-RPC check already does. Then, which plugin first, if any? Solid Security looks the most REST-shaped, but that is unverified.
4. **Plugin scope drift.** The PRD's 2026-11-10 decision limits plugin integrations to QAF, Gravity Forms and PMPro. complete.md WP-G says the shop, events and SEO promises "are not current scope". Yet `workbench_coverage.py` says WooCommerce and Yoast are supported since 2026-11-13, wordpress.md section 19 says the same, and more of WooCommerce is being built today. Which is the record? If the three are in, the PRD and complete.md need updating. If they are out, today's Shop work should stop.
5. **Rank Math.** Support it alongside Yoast, or leave it read only?
6. **Live testing.** Everything above in "Built but not yet tried live" needs writes on the test host or plugins installed there, which only you can do. Which comes first? I suggest the Workbench core with NVDA and JAWS, because it is now the default.
