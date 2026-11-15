# Chapter 10: Shop, events, SEO, memberships and redirects

## What this chapter covers

Many sites do more than publish. They sell things, list events, chase search
engines, run memberships, or send old addresses to new ones. Each of those
needs a plugin, and QUILL works with the commonest: WooCommerce, The Events
Calendar, Yoast SEO, Paid Memberships Pro and Redirection.

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
on it says which role could.

In the editor, **File > WordPress > Plugin Fields...** changes the fields
these plugins add to the page you are writing, such as an event's date or a
product's price, and Properties shows them.

## A shop: WooCommerce

Each site with WooCommerce has a **Shop**. Its list is your products, with
price, stock and status. Under it are **Draft Products**, **On Sale**, **Out
of Stock**, **Shop Orders**, **Customers**, **Coupons**, **Shop Reports**,
**Store Settings**, **Product Reviews**, **Shipping Zones**, **Tax Rates**,
**Tax Classes**, **Attributes**, **Brands** and **Webhooks**.

### Products

- **File > New Here...** (`Ctrl+N`) on Shop makes a new product, as a draft.
- **Edit Product...** changes the regular and sale price, the stock, the
  status and the categories. Only what you changed is sent.
- **Show Its Variations** lists a product's variations, and **Edit a
  Variation...** changes one's price, sale price, stock, or whether it is for
  sale.
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

In the editor, **Tools > WordPress > Plugin Extras > Shop Orders...** lists
the newest orders, to read.

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

In the editor, **Tools > WordPress > Plugin Extras > Events Coming Up...**
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

**Discount codes.** **Look Up a Discount Code...** reads one code, and **New
Discount Code...** makes one after a preview. Where the site cannot list
every code, the list says so and opens the wp-admin screen.

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

**404 Log**, under Redirects, lists addresses visitors asked for that were not
found. **Redirect This Address...** sends one somewhere, after a preview.

QUILL also offers a redirect at the moments you need one: when you change a
page's slug in Properties, and when Replace File gives a file a new address
(Chapter 5). Say yes, and the old address keeps working.

## A podcast

**Podcast**, in a site's branch, lists the site's podcast episodes: its
podcast content type if it has one, or else the posts that carry an episode's
player. A site with neither says so. QUILL Cast and QUILL Studio can post
episodes to your site (Chapter 5).

## Where to next

- Previous: [Chapter 9: Moving and copying content](wordpress-forms-09-moving-and-copying.html)
- Next: [Chapter 11: Writing a form](wordpress-forms-11-writing-forms.html)
- [Contents](wordpress-forms-guide.html)
