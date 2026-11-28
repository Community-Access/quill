# Chapter 10: Shop, events, SEO, memberships and redirects

## What this chapter covers

Many sites do more than publish. They sell things, list events, chase search
engines, run memberships, or send old addresses to new ones. Each of those
needs a plugin, and QUILL works with the commonest: WooCommerce, The Events
Calendar, Yoast SEO, Paid Memberships Pro and Redirection. It can also browse
newsletters made with SwiftLetter.

This chapter has a section for each. Skip the ones your site does not have.
You will look after products, orders and customers, events and venues, each
page's search appearance, members and their levels, and redirects.

By the end you can run the parts of your site that plugins add, from the same
Workbench as everything else. Forms plugins have chapters of their own, from
Chapter 11.

## How these work

Each plugin gets its own places in a site's branch of the Workbench, but only
when the site has that plugin. A site without it simply has no such place,
or says so in one sentence.

Every change shows you a preview first. Before anything is sent, QUILL reads
the thing again from the site, and if somebody changed it in the meantime,
nothing is sent and you are told which part changed. Press F5 and try again.
After the save, QUILL checks what the site kept, and tells you if it did not
keep something.

Ctrl+Z undoes a change wherever putting the old values back really restores
it. When something cannot be undone, such as a shipping zone deleted for
good, the preview says so. A command your role cannot use is dimmed, and F1
on it says which role could: shop changes need the Shop Manager or
Administrator role, events, venues and organizers the Author role or higher,
and membership changes an Administrator or Membership Manager. A chooser for
a new value starts on the value it has now.

In the editor, **File > WordPress > Plugin Fields...** changes the fields
these plugins add to the page you are writing, such as an event's date or a
product's price, and Properties shows them.

## A shop: WooCommerce

Each site with WooCommerce has a **Shop**. Its list is your products, with
price, stock and status. Under it are **Draft Products**, **On Sale**, **Out
of Stock**, **Shop Orders**, **Customers**, **Coupons**, **Shop Reports**,
**Store Settings**, **Product Reviews**, **Shipping Zones**, **Shipping
Classes**, **Tax Rates**, **Tax Classes**, **Attributes**, **Brands**,
**Webhooks**, **Payment Gateways** and **System Status**. Beside it is **Shop
Analytics**, WooCommerce Analytics' reports, described at the end of this
section.

### Products

- **File > New Here...** (`Ctrl+N`) on Shop makes a new product, as a draft.
- **Edit Product...** changes the regular and sale price, the stock, the
  status and the categories. Only what you changed is sent.
- **Change Many Products...** makes one change to every product you
  selected (`Ctrl+A` selects all shown): put them on sale at a percentage
  off, end a sale, raise or lower the price by a percentage, set the stock
  status or the status, or add or remove a category. The preview names each
  product's old and new value, and each product the change leaves alone and
  why (a variable product's prices are on its variations; a stock count sets
  its own status). Undo sends the old values back.
- **Properties...** (`Alt+Enter`) on a product has every field WooCommerce
  lets you change: SKU, description and short description, sale dates,
  weight and dimensions, shipping and tax class, images, downloads, upsells
  and cross-sells. The shipping class is chosen by name from the shop's
  Shipping Classes, or No shipping class. A list or a group of values is a
  box of JSON that QUILL checks before it saves.
- **Show Its Variations** lists a product's variations, and **Edit a
  Variation...** changes one's price, sale price, stock, or whether it is for
  sale.
- **Generate Variations...** on a variable product makes a variation for
  every combination of its attributes that it does not have yet. The
  preview says how many combinations there are and how many variations it
  has now; afterwards QUILL says how many it made. Existing variations are
  never changed or removed. WooCommerce makes at most 50 at a time, so a
  large product may need it again. A new variation has no price until you
  give it one with Edit a Variation. Ctrl+Z deletes the ones it made. On a
  product that is not variable, or has no attribute used for variations,
  QUILL says why and sends nothing.
- **Duplicate...** makes a copy, and **Move to Trash...** sends one to
  WooCommerce's Trash.

### Orders

**Shop Orders** lists the newest orders. **Read in Full** reads one as a
receipt, without the customer's email, telephone or billing address.

- **Change Status...** moves an order on, such as to Completed. The preview
  says which email WooCommerce will send the customer.
- **Notes...** reads the order's notes and adds one, kept private or emailed
  to the customer.
- **Refund...** refunds one order. It checks the amount against what is left
  to refund, warns you whether the payment gateway really returns the money
  or only the record changes, and sends only when you type the amount
  exactly. A refund is never part of a batch, and cannot be undone.
- **Resend Order Details...** emails the customer the order's details again,
  for when the receipt never came.
- **Change Items...** changes a quantity, takes an item off (a quantity of
  0) or adds a product. WooCommerce works out the total again; any refund or
  payment for the difference is yours to make. It cannot be undone here:
  Change Items again puts it back.
- **Change Address...** changes the billing or the shipping address,
  sending only the fields you changed; Undo sends the old ones back.
- **New Order...** (`Ctrl+N` on Shop Orders) takes an order by telephone:
  choose a customer, or a guest by name and email, then each product and
  its quantity, then whether it starts as Pending payment, Processing or On
  hold. QUILL never marks it paid. Undo moves it to the Trash.
- **Open in the Shop's Dashboard** opens the order in wp-admin.

These are shop orders. Membership orders, from Paid Memberships Pro, are a
different thing, and each shop order says so.

### Customers and coupons

**Customers** lists the shop's customers, without their contact details.
**Customer Details** reads one person's email and addresses from WooCommerce
at that moment, and **Edit Customer...** changes their name and email, their
billing address or their shipping address. Both need a role that may see the
site's people.

**Coupons**: Ctrl+N makes one, **Edit Coupon...** changes it, and **Move to
Trash...** removes it.

### Reports, settings and reviews

- **Shop Reports** says the sales, the top sellers and the main totals, each
  as a sentence with a small table.
- **Store Settings** lists every group of WooCommerce's settings, each in
  words. **Change Setting...** offers the choices WooCommerce gives, and
  previews the old and new value. Settings that are passwords are never read
  out, shown in a row, or changed here.
- **Product Reviews** lists every review with its product, rating, reviewer
  and status. The reviewer's email is never shown. **Approve**, **Hold** and
  **Mark as Spam** work on one review or several, with a report of how each
  went. **Reply...** puts your answer under the review, **Edit Review...**
  corrects its words or rating, and Delete moves it to WooCommerce's Trash.

### Shipping and tax

- **Shipping Zones** lists each zone with the places it covers and its
  methods. Ctrl+N makes a zone. **Locations...** takes a list such as
  `country US, state US:AZ, postcode 85001`. **Methods...** lists the zone's
  methods: choose one to turn it on or off, change its cost or remove it, or
  add flat rate, free shipping or local pickup. **Rename...** and
  **Delete...** are there too.
- **Shipping Classes** lists each class, such as Heavy items, with its slug
  and how many products are in it. Ctrl+N makes one: give it a name, and a
  slug and description if you want them. **Change...** changes its name,
  slug or description, and Ctrl+Z puts them back. **Delete...** removes a
  class for good, after a preview naming the class and the site: its
  products are left with no shipping class, and any rate a zone set for it
  stops applying. A product is put in a class from its Properties.
- **Tax Rates**: Ctrl+N makes a rate, **Edit Tax Rate...** changes its name,
  percentage and where it applies, and **Delete...** removes one. A deleted
  rate comes back with Ctrl+Z.
- **Tax Classes**: Ctrl+N makes one, and **Delete...** removes it. Deleting a
  class takes its rates with it, and the preview warns you.

### Attributes, brands and webhooks

- **Attributes** lists product attributes such as Size. **Terms...** adds,
  renames or deletes an attribute's values.
- **Brands** is there when the site's WooCommerce has brands, from version
  9.6.
- **Webhooks** lists what each webhook sends, where to, and whether it is
  paused. Ctrl+N makes one: give it a name, choose what triggers it, and type
  the https address it goes to. WooCommerce makes the webhook's secret itself,
  and QUILL never reads it or says it. **Pause or Activate...** stops or starts
  one, and **Delete...** removes it for good.

### Payment gateways and system status

- **Payment Gateways** lists each way to pay, the ones turned on first, with
  what customers see at checkout. **Turn On...** or **Turn Off...** changes
  only that, after a preview, and Ctrl+Z turns it back. A gateway's settings
  hold its keys, so they stay in WooCommerce > Settings > Payments.
- **System Status** says the WooCommerce, WordPress, PHP and database versions,
  then lists WooCommerce's maintenance tools, such as clearing its cached
  data. **Run Tool...** runs one after a preview; it cannot be undone.

In the editor, **Tools > WordPress > Plugin Extras > Shop Orders...** lists
the newest orders, to read.

### Shop Analytics

WooCommerce Analytics has its own menu in wp-admin, beside WooCommerce, and in
the Workbench it is **Shop Analytics**, beside Shop. It is there when the site
lists WooCommerce Analytics' routes; WooCommerce turns Analytics on in
WooCommerce > Settings > Advanced > Features. Nothing in it changes the site.

Under it is one place for each report: **Revenue**, **Orders**, **Products**,
**Categories**, **Coupons**, **Taxes**, **Downloads**, **Stock** and
**Customers**. The first row of each is the total for the whole range. Then:

- **Revenue**, **Orders** and **Downloads** have a row for each day, week or
  month. Revenue gives orders, gross sales, returns, coupons, net sales, taxes,
  shipping and total sales; Orders gives the orders, net sales, the average
  order and the items in each.
- **Products**, **Categories**, **Coupons** and **Taxes** have a row for each
  product, category, coupon or tax rate that sold or was used, best first.
- **Stock** lists every product's stock as it is now, out of stock first.
- **Customers** lists customers, biggest spenders first, with their orders,
  total spent, average order and when they were last active. Emails and
  addresses stay out of the list.

When you arrive on a report, QUILL says its totals once, compared with the
same number of days just before, for example "Revenue on Radio, last 7 days:
$1,240 from 31 orders, up 12% on the 7 days before." Amounts are written the
way your store writes them, with its currency symbol and separators. F5 reads
the report again without repeating the sentence.

On any row of a report:

- **Date Range...** chooses the days: Today, Yesterday, Last 7 Days, Last 30
  Days, Month to Date, Last Month, This Year, Last Year, or **Custom...**, which
  asks for the first and last day, such as 2026-11-01. Last 7 Days is where it
  starts.
- **Interval...** chooses a row for each day, week or month.

Both are kept for every report on that site until you change them or close
the Workbench, so Revenue and Orders always cover the same days. Stock and
Customers say how things are now, so the range does not change them.

To keep a report, **Edit > Export List...** (Ctrl+Shift+X) writes the rows as
shown, the total first, as an Excel workbook, a CSV file or a Markdown table.
WooCommerce's charts, segments and advanced filters stay in its own screens:
**wp-admin for This Place** opens them.

## Events: The Events Calendar

Each site with The Events Calendar has an **Events Calendar**, which lists
the events coming up. Under it are **Past Events**, **Venues**,
**Organizers**, **Event Categories** and **Event Tags**.

Each event says its time zone, and the time on your own computer too.

- **File > New Here...** (`Ctrl+N`), or **New Event...**, makes an event as a
  draft, in the site's time zone unless you type another.
- **Edit Event...** changes its details, such as its title and times.
- **Events Between Dates...** lists the events in a range you give.
- **Categories and Tags...** lets you type the names the event should have,
  separated by commas.
- **Move to Trash...** removes one.

**Venues** and **Organizers** each have New, Edit and Move to Trash. **Event
Categories** and **Event Tags** list each one with how many events use it;
Ctrl+N makes one, and **Rename...** and **Delete...** are on the context menu.
Deleting one leaves the events alone.

An event that repeats, from Events Calendar Pro, says so. Its series is
changed in wp-admin, because the plugin does not share the rule that makes
it repeat.

In the editor, **Tools > WordPress > Plugin Extras > Upcoming Events...**
lists every event from today, and **New Event...** makes a draft event and
opens it.

## Search engines: Yoast SEO

Each site with Yoast SEO has an **SEO** place. It lists the newest posts and
pages, with what to look at on each.

- **Search Appearance** reads how the item shows in a search result: its
  title, its address and its description, and where each one gets cut off.
- **Edit SEO...** changes the SEO title, the meta description, the focus
  keyphrase, whether it shows in search results, and the social title,
  description and image. Anything the site does not share with QUILL, such
  as the social image on most sites, is named in the preview and left for the
  Yoast panel in wp-admin.
- **Bulk SEO Editor...** opens a window that lists every post and page with
  how long its SEO title and description are. Press Enter on one to change
  both, right there in the list. Each is saved on its own, after a preview. It
  needs Yoast's manage options right, which administrators and Yoast's SEO
  Manager role have.
- **Properties...**, on the row here or on the post in Posts or Pages, has an
  **SEO** page with the **canonical address**, the **primary category** (a
  post's, chosen by name from its own categories), and the **schema page
  type** and **schema article type**. Yoast's bulk editor cannot change these,
  so QUILL changes one only where your site shares that Yoast setting with
  QUILL, and then it is saved like any other field, checked first and
  afterwards. Most sites do not share them. Then the page shows what Yoast
  tells search engines, read only, and one sentence says these are changed in
  the post's Yoast panel.
- **Open in wp-admin** opens the post's editor in your browser, where that
  Yoast panel is.

**Site SEO**, under SEO, gives the site's SEO and readability scores in words.
**Open in Dashboard** goes to Yoast's own screens for everything else.

Rank Math's title and description are in Properties and Plugin Fields in the
editor, with a count that tells you when the text goes over what search
engines show. The same goes for Yoast's.

## Memberships: Paid Memberships Pro

Each site with Paid Memberships Pro has **Memberships**, with **Membership
Levels**, **Orders**, **Subscriptions**, **Renewals Due** and **Discount
Codes**. Card and billing details are never shown. **Needs My Attention >
Membership Orders** lists orders, on every site, that wait on a person:
pending, in review, waiting on payment, or failed.

**Levels.** **New Membership Level...** (`Ctrl+N` on Membership Levels) and
**Edit Membership Level...** ask the name, the initial payment, the
recurring payment and how often it is taken, when membership expires, and
whether new signups are allowed, then preview them. A change shows only what
changes, old and new; new prices are for new signups, because Paid
Memberships Pro does not change what members already pay. Undo puts it
back, or deletes a level you just made.

**Members of This Level...**, on a level, lists everyone who holds it now,
with their email addresses, to count them or write to them. Paid Memberships
Pro has no way to ask for a level's members, so QUILL asks the site about
each person in turn. Before it starts, it says how many people that is, and
on a big site it says plainly that it is slow. It runs in the background;
choose it again to stop, and the members found so far are kept. The members
open in a list, where **Copy Email Addresses** copies every address, with a
semicolon between, ready for the To box of a message.

**Discount codes.** Where the site offers Paid Memberships Pro's
discount-codes ability, **Discount Codes** lists every code. Elsewhere its
one row says that this site lists its codes only in wp-admin, and Enter
opens that screen in your browser. Either way, **Look Up a Discount Code...**
reads one code, and **New Discount Code...** makes one after a preview.

**A member.** On a person in **People > Users**:

- **Show Memberships...** reads their current and past levels.
- **Check Membership Access...** says whether they may see a post or page
  you choose, as Paid Memberships Pro decides it. Their Properties has an
  **Access** page with **Check a Post or Page...** for the same thing.
- **Change Membership Level...** gives them another level.
- **Cancel Membership...** cancels one of their levels.

Change and Cancel read the member and their subscriptions again each time.
The preview names the subscription, the payment gateway, the amount and the
next payment that stops, and says that nothing is refunded and that it cannot
be undone. Paid Memberships Pro's own checks still decide.

The full set needs WordPress 6.9 or later and Paid Memberships Pro 3.9 or
later. On an older site, QUILL uses the plugin's older way in, which does
less, and says so where it matters.

## Redirects: Redirection

A redirect sends visitors from an old address to a new one, so links in old
emails and search results still arrive. Each site with the Redirection plugin
has **Redirects**, listing where each one leads from and to, its code, how
many times it was used, and whether it is on.

- **File > New Here...** (`Ctrl+N`), or **Add Redirect...**, makes one after a
  preview.
- **Test an Address...** follows the redirects from an address you give, and
  names any chains and loops. Nothing is sent to the site.
- **Change Redirect...** changes where it leads, and **Turn On or Off** does
  what it says.
- **Delete Redirect...** deletes it for good, because the plugin keeps no
  Trash.
- **Export Redirects...** saves every redirect to a file on your computer:
  CSV, or the plugin's own JSON with its groups.
- **Import Redirects...** reads a CSV (from, to, and optionally a pattern
  flag and a code) or a Redirection JSON export, and previews every redirect
  it would add and every line it cannot use, with why: a line with no
  address, a code that is not a redirect, an address in the file twice, or
  one the site already redirects. Then it asks which group, and adds them
  one at a time.

**Redirect Groups**, under Redirects, lists the groups the plugin keeps
redirects in, with how many each holds and whether it is on. **New
Group...** (`Ctrl+N`), **Rename...** and **Turn On or Off** each preview
first and can be undone. **Delete Group...** deletes its redirects with it,
so it asks you to type the group's name.

**Redirect Options**, under Redirects, lists the plugin's own options that
QUILL knows, each with its value: how addresses are matched (capital letters,
a slash at the end, query parameters), how long the logs are kept, whether
they keep visitors' IP addresses, HTTPS and www, and how long browsers keep a
redirect. The last row says how many more options stay in Tools >
Redirection > Options. **Change Options...** (Enter), or `Alt+Enter`, opens
them all on one Properties sheet; OK previews only the options you changed,
sends only those, and checks what the site answers. Undo puts them back. A
site whose Redirection does not offer its options to QUILL says so on its one
row, and Enter opens the plugin's Options screen in your browser.

**404 Log**, under Redirects, lists addresses visitors asked for that were not
found. **Redirect This Address...** sends one somewhere, after a preview.

QUILL also offers a redirect at the moments you need one: when you change a
page's slug in Properties, and when Replace File gives a file a new address
(Chapter 5). Say yes, and the old address keeps working.

## Newsletters: SwiftLetter

SwiftLetter builds a newsletter from articles, runs an editorial review, and
makes a Word document and audio of the issue. Each site with SwiftLetter 1.1
or later has **SwiftLetter**. QUILL offers it on self-hosted WordPress sites,
including managed hosts where the plugin can be installed. A site connected
through WordPress.com says, in one sentence, that QUILL offers SwiftLetter
only on self-hosted sites.

QUILL browses newsletters and opens articles in the editor, where you write
and save them back as drafts. It never publishes: the issue is published from
SwiftLetter.

**SwiftLetter** lists the site's newsletters: each title, how many articles it
holds, and when it last changed. Two newsletters with the same title carry
their number, so you can tell them apart. The list reads three hundred
newsletters at first, like every Workbench list. When the site says how many
it has, the summary after the list says how many more there are, and **View >
Load More** reads three hundred more; **Load All** reads every one.

Each newsletter is also a node under SwiftLetter in the tree. On a newsletter
row, Enter is **Show Articles**: it selects that newsletter in the tree and
lists its articles. If the newsletter is not in the tree yet, QUILL says so,
and Refresh (F5) lists the newsletters again.

A newsletter's list has its articles in newsletter order, each with:

- its title;
- its review state, in words: **Reviewed**, **Not reviewed**, or **Changed
  since review** for an article reviewed and then edited. Only Reviewed counts
  towards publishing the issue;
- its place, such as "3 of 8".

The details pane says the article's newsletter and site, who last changed
its title or text and when, and whether your account can edit it. **Read in
Full** on the article's context menu moves you there. When SwiftLetter cannot
be sure who made the last change, it says **Editor unknown** rather than
guess. Whether you may edit or review is a hint from the site; SwiftLetter
still checks every request.

### Writing an article in the editor

On an article row, Enter is **Open in Editor**. QUILL reads the article
through SwiftLetter and asks how to open it:

- **HTML**, exactly as SwiftLetter has it; or
- **Markdown**, easier to read. Headings (with their anchors, written
  `## Planting day {#planting-day}`), links, lists, quotes and pictures with
  their descriptions are plain Markdown. Any block Markdown cannot show
  exactly is kept on a short `:::` line and goes back unchanged.

Either way SwiftLetter receives WordPress blocks. If Markdown would change an
article, QUILL opens it as HTML and says why. Once it is open, QUILL says its
title and review state. An account that cannot edit the article, or a site
whose SwiftLetter does not take saves from QUILL, opens it read-only and says
so. Opening the same article again opens your working copy on this computer;
Compare with Site shows what changed on the site since.

**File > WordPress > Save Draft to Site** sends the title and text, with the
version you opened, so SwiftLetter can tell whether anyone changed the article
since. QUILL saves a draft only: **Publish** on an article says that QUILL
never publishes SwiftLetter articles, and sends nothing. After a save:

- QUILL says "Draft saved to SwiftLetter" and the site's name. A reviewed
  article now reads **Changed since review**, and needs reviewing again before
  the issue can be published. The live newsletter is not changed until then.
- If WordPress changed the text as it stored it, QUILL says so, keeps your
  copy exactly as you wrote it, and Compare with Site shows the difference.
  Tidying that changes nothing a reader sees, such as the spacing WordPress
  adds in an image tag, is said the first time only.
- A save that would send what the site already has sends nothing, and says so.
- On a site with the SwiftLetter 1.1.0 test build, which does not send back
  what it stored, saving works the same; QUILL just cannot tell you whether
  WordPress tidied anything.

Before a Markdown save, QUILL turns the Markdown back into blocks. If any line
cannot be turned back without losing something (a `:::` line whose block is
missing, say), nothing is sent: QUILL names the line, and your Markdown stays
as it is.

QUILL never sends a save again by itself. When SwiftLetter refuses, QUILL says
SwiftLetter's own sentence, and your copy in QUILL is unchanged:

- **The article changed on the site** since you opened it. A window offers
  **Compare with Site** (the site's article against yours, read fresh; nothing
  is sent), **Reopen** (load the site's article into the document; yours is
  kept in Previous Versions, and Undo brings it back), and **Keep editing**.
- **Someone else is editing it in WordPress.** SwiftLetter's sentence names
  who. Save again once they have finished.
- **SwiftLetter needs the article's version**, or cannot read it. The window
  offers **Reopen**.
- **Anything else**, such as your account not being allowed to edit the
  article, or a site that cannot save safely: QUILL says SwiftLetter's
  sentence.

Compare with Site (on the WordPress menu) works on an article at any time.
Move to Trash does not: articles are trashed in SwiftLetter.

When the site refuses, the list says why: SwiftLetter is not active on the
site, the site's SwiftLetter needs an update, your account is not allowed to
browse newsletters, or the site's SwiftLetter is a newer version than this
QUILL understands. F1 on SwiftLetter, a newsletter or an article says what it
is.

Reordering, review and exports come in later updates, and this section will
grow with them.

## A podcast

**Podcast**, in a site's branch, lists the site's podcast episodes: its
podcast content type if it has one, or else the posts that carry an episode's
player. A site with neither says so. QUILL Cast and QUILL Studio can post
episodes to your site (Chapter 5).

## Where to next

- Previous: [Chapter 9: Moving and copying content](wordpress-forms-09-moving-and-copying.html)
- Next: [Chapter 11: Writing a form](wordpress-forms-11-writing-forms.html)
- [Contents](wordpress-forms-guide.html)
