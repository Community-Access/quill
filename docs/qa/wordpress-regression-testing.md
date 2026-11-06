# WordPress regression testing for QUILL and QUILL Lite

Payment checkout has an additional [acceptance checklist](forms-payments-acceptance.html).
Do not assume the test site's QAF plugin implements the payment contract;
Verify Payment Setup must report version-1 readiness before testing checkout.
No live payment acceptance is implied by the ordinary WordPress regression run.

A real WordPress site exists for testing every WordPress feature in QUILL and
QUILL Lite, with known content, so a test always starts from the same place
and its results can be compared from one build to the next.

- **Site:** https://lp.csedesigns.com/wordpress/
- **Dashboard:** https://lp.csedesigns.com/wordpress/wp-admin/
- **WordPress version:** 7.1.4 when it was built (2026-11-04). It is new
  enough for the application-password handback to `127.0.0.1` (wordpress.md
  4.2, tier 1).
- **Kind:** self-hosted. WordPress.com is tested separately, once QUILL's
  WordPress.com app is registered.

## Accounts

There is one account per role, so the role behaviour can be tested (wordpress.md
9.2):

| Username | Role | Can publish posts | Can publish pages | Can upload |
|---|---|---|---|---|
| quilladmin | Administrator | yes | yes | yes |
| quill-editor | Editor | yes | yes | yes |
| quill-author | Author | yes | no | yes |
| quill-contributor | Contributor | no | no | no |
| quill-subscriber | Subscriber | no | no | no |

The passwords are never written into this repository. They live on the
server, readable only by its owner:

- the sign-in passwords and an application password for each of the first
  four accounts: `~/app/wordpress-test/test-accounts.txt`;
- the administrator's sign-in password: `ADMIN_PASSWORD` in
  `~/app/wordpress-test/.env`.

To read them: `ssh lp.csedesigns.com cat app/wordpress-test/test-accounts.txt`.
Paste an application password into QUILL's Connect a Site; never into a chat,
an issue or a test file.

## Where the test passwords live

No password is ever in this repository. There are two copies, both private.

**On this computer, in Windows Credential Manager.** Each password is a
generic credential under the service
`QUILL WordPress test site (lp.csedesigns.com)`, with the user name
`<login> <kind>`, where kind is `sign-in` or `application`. There are nine:

- `quilladmin sign-in` and `quilladmin application`;
- `quill-editor sign-in` and `quill-editor application`;
- `quill-author sign-in` and `quill-author application`;
- `quill-contributor sign-in` and `quill-contributor application`;
- `quill-subscriber sign-in` (the subscriber has no application password).

The live run (`docs/qa/wordpress-live-run.py`) reads the application
passwords from there. If one is missing it looks next in the file named by
`QUILL_LIVE_ACCOUNTS`, then in `QUILL_LIVE_APP_PASSWORD_<LOGIN>` (for
example `QUILL_LIVE_APP_PASSWORD_QUILL_EDITOR`), and says which login it
could not find. It never prints a password.

**On the server.** `~/app/wordpress-test/test-accounts.txt` (mode 600) holds
the sign-in passwords of the four test accounts and the application
passwords of the first four logins, one per line, as
`<login> sign-in password: ...` and `<login> application password: ...`.
The administrator's sign-in password is `ADMIN_PASSWORD` in
`~/app/wordpress-test/.env`.

**Refreshing the local copy.** Whenever the server's copy changes, after
`setup.sh` builds a fresh site or a reset makes new passwords, copy them
across again:

```powershell
python docs/qa/wordpress-test-site/store-passwords.py --admin-sign-in
```

It reads the server's file over ssh, stores each entry in Credential
Manager, and prints only the names it stored. Without `--admin-sign-in` it
leaves the administrator's sign-in password alone. `reset.sh` as it is
written keeps the accounts and their passwords, so an ordinary reset needs
no refresh.

## What is on the site

The content is seeded by `~/app/wordpress-test/setup.sh`. Each seeded item
exists for a reason:

| Item | Kind and status | Tests |
|---|---|---|
| Welcome to the test site (`/welcome/`) | post, published, News, tags WordPress and Accessibility, 3 revisions, comments | Open by Web Address, Previous Versions (site history), Compare, Comments |
| Pinned news | post, published, sticky | Properties: Keep at the top of the blog |
| Things to check before publishing | post, draft, Training | Check Before Publishing (one problem of each kind) |
| Waiting for review | post, pending, by quill-contributor | Open with status Pending, Contributor's Submit for Review |
| Scheduled for next month | post, scheduled | Update keeps Scheduled |
| A private post | post, private | Update keeps Private |
| Password protected | post, published, password `quill` | Properties: password |
| Classic content | post, published, no block comments | Freeform content round trip |
| Written by the author | post, published, by quill-author | Author editing their own post |
| In the Trash | post, in the Trash | Open with Trash, restore |
| About Us (`/about/`), Contact | pages, published | Pages list, Open by Web Address |
| Meet the Team | page, child of About Us | Page parent |
| Every Block (`/every-block/`) | page, published | Block round trip (see below) |
| A Draft Page | page, draft | Drafts |
| Event announcement | synced pattern | Synced patterns |

**Media:**

- photo-volunteers, with alternative text;
- square-logo, with alternative text, set as the site logo and the site icon;
- wide-banner, no alternative text;
- decorative-divider, no alternative text;
- animated-ish (a GIF that is mostly text).

**Categories:** News, Training, JAWS Training (a child of Training), Product
Updates, Empty Category, and Uncategorized.

**Tags:** JAWS, Braille, WordPress, Accessibility, and Unused Tag.

**Comments on Welcome:** one approved, one waiting, one spam.

**Every Block** contains, in order:

- a paragraph and a heading;
- buttons and columns;
- details;
- an image with a caption;
- a table with a header row;
- a quote with a citation;
- code;
- a separator;
- a YouTube embed;
- Latest Posts (a void, dynamic block);
- a gallery shortcode (an island).

## Before each test run

Put the content back to its starting state:

```bash
ssh lp.csedesigns.com app/wordpress-test/reset.sh
```

It keeps the accounts, application passwords, settings and media, and reseeds
every page, post and pattern. Then confirm the site is as expected:

```bash
ssh lp.csedesigns.com app/wordpress-test/verify.sh
```

`verify.sh` signs in as each role with its application password, and prints
what each can do and what content exists. It never prints a password.

## The tests

Run each test in QUILL and again in QUILL Lite, with a screen reader and the
keyboard only. A result is a pass only when it is the same in both editors.
For each test, note the build, the editor, the screen reader, and pass or
fail.

Where the commands are (the same in both editors, from
`quill/core/wordpress/menu.py`):

- **File > WordPress:** New, Open, Open by Web Address, Open Local Draft,
  Save Draft to Site, Publish or Update, Schedule Publish, Open on Site, Copy
  Address, Properties, Previous Versions, Compare with Site, Move to Trash,
  Switch Site, Sites, Connect a Site.
- **Insert, Format > WordPress, View, Edit > WordPress:** blocks, pictures,
  links, Block Settings, Image Size, Mark Language, and block navigation.
- **Tools > WordPress:** the checks, the Media Library, Alt Text Review,
  Visual Review, Comments, Categories and Tags, Menus, Site Check, Site
  Settings, and the More Media and Manage submenus.

The rows about the page in front are dimmed outside a WordPress document. The
commands have no keys yet: use Alt+F, W, or the Command Palette.

### Connecting (4)

1. **Connect by hand.** Choose File > WordPress > Connect a Site, then enter the address, quill-editor and its
   application password. Expect "Connected to QUILL WordPress Test Site as
   Editor".
2. **Connect with the browser.** Use Get Password with My Browser and approve
   in the browser. Expect the password to come back by itself (tier 1, on
   WordPress 7.1).
3. **Wrong password.** Expect a plain sentence that names the site, with the
   dialog reopened and the fields kept.
4. **HTTP address.** Use `http://lp.csedesigns.com/wordpress`. Expect a refusal
   that explains HTTPS.
5. **Many sites.** Connect as quill-editor and again as quill-author, renaming
   one of them. In Sites, check the role on each row, Make Default, then
   Switch Site.
6. **Remove.** Expect only the connection to be forgotten; the site is
   unchanged.

### Writing and opening (5.1, 5.2)

7. **New Post, Markdown.** Check that the slug follows the title, and that the
   categories and tags are listed. Ctrl+S saves locally; check that the post
   is not on the site.
8. **New Page, HTML.**
9. **Open Page or Post.** Open Posts, with Find set to "draft", then
   "trash". Each row reads title, status and last changed.
10. **Open Every Block as Markdown,** change nothing, then Save Draft to Site.
    In the dashboard's code editor, the content must be byte for byte the
    same, with only blank lines between blocks normalised. Do it again as
    HTML.
11. **Open by Web Address** with `https://lp.csedesigns.com/wordpress/welcome/`
    on the clipboard. Then try `.../?p=<id>` and a page address.
12. **Open Local Draft** lists the drafts from test 7, with their site.

### Saving and publishing (5.3, 5.4, 9.2)

13. **Save Draft to Site** on test 7's post. Check the site has a draft and the
    public page does not.
14. **Publish or Update.** The confirmation names the title and the site;
    after publishing, the address is on the clipboard.
15. **Contributor.** As quill-contributor, Publish becomes Submit for Review.
    The post arrives as Pending.
16. **Author and pages.** As quill-author, publishing a page is refused in
    words.
17. **Private and Scheduled keep their status.** Open A private post, change
    a word, and Update. Do the same with Scheduled for next month.
18. **Conflict.**
    - Open Welcome in QUILL.
    - In the dashboard, edit and update it.
    - In QUILL, choose Update.
    - Expect nothing to be sent, and a sentence that names the change.
    - Then try each of Compare, Open the Site's Copy, and Send Mine Anyway.
19. **Closing never publishes.** Close an edited document; the site is
    unchanged.

### Properties, versions, Trash (5.5, 5.6)

20. **Properties on Pinned news.** Change the categories and tags, the
    excerpt, and Keep at the top of the blog. Send, and check them in the
    dashboard.
21. **Previous Versions on Welcome** lists the local versions and the 3 site
    revisions. View one, then Restore one; nothing is published.
22. **Compare with Site** after a local change.
23. **Move to Trash.** The confirmation names the item and the site, and the
    item appears under Trash in Open.

### Checks (7)

24. **Tools > WordPress > Check Before Publishing on "Things to check before publishing".** Expect
    each of these:
    - a heading 1 in the body;
    - a skipped heading level;
    - "click here";
    - a link whose text is its address;
    - a new tab not said;
    - a picture with no alternative text;
    - colour alone;
    - a table with no header row.

    **Go to It** reaches each one.

### Pictures (6)

25. **Tools > WordPress > Media Library.**
    - Rows read title, kind, size, alternative text and date.
    - Find: "banner".
    - Edit Alternative Text on wide-banner, and check it in the dashboard.
26. **Insert > Picture from the Media Library** into a post. Check that the alternative text is
    kept per placement.
27. **Insert > Picture from This Computer.**
    - Inserted at once, and marked as not uploaded yet.
    - Uploaded on Save Draft to Site, with the address swapped in.
28. **Remove from Library** on a copy you uploaded in test 27. Check a backup
    is saved under Documents, Removed from WordPress.

### Comments, categories and tags (9.8, 9.13)

29. **Tools > WordPress > Comments.** Approve the waiting comment, reply to it, and mark one as
    spam.
30. **Tools > WordPress > Categories and Tags.**
    - Add a tag.
    - Rename Unused Tag.
    - Merge Empty Category into News. Expect the post count in the sentence,
      and the empty category deleted.
    - Delete a tag.

### Listen and watch (6.1a)

`setup.sh` seeds a three-second tone (quill-test-tone, WAV), a five-second
silent test-pattern video (quill-test-clip, MP4), its English captions
(quill-test-clip.en.vtt), and a Listen and Watch page with one audio block and
one video block.

31. **Play on the tone** in the Media Library.
    - A small player opens and the tone plays at once.
    - The keys are the ones in QUILL's player: Play and Pause, Stop, Rewind,
      Forward, Where am I, Speed, Volume and Mute. There are no chapter buttons.
    - Go to Position 0:00:02 moves there.
    - Close, and the tone stops. Try again with Escape and with Alt+F4.
32. **Play on the clip.** The picture shows with NVDA and with JAWS, and
    nothing else takes focus. Press Captions at about one second: expect "This
    is the QUILL test clip." Press it after five seconds: expect "No caption
    at" and the time.
33. **Nothing is saved.** After tests 31 and 32, check that the Downloads and
    Documents folders have no new copy of either file.
34. **Play on a picture** (photo-volunteers): expect "That file is not audio
    or video."
35. **Open in Browser** from the player: playback here pauses and the file
    opens in the browser. **Open in Quill Media Player** starts Quill Media
    Player where it is installed, and says so where it is not.
36. **Play Media Here** in the Listen and Watch page, with the caret on the
    audio block and then on the video block. On the paragraph, expect "There
    is no audio or video block at the caret."
37. **QUILL Lite.** Repeat 31, 32 and 36 in QUILL Lite.

### The site's own kinds (5.2)

38. **Events.** File > WordPress > Open Page or Post lists Posts, Pages and
    Events. Choose Events: "Open Day" is there. Open it, change a word, and
    Save Draft to Site, then Publish or Update. Check the site shows the
    change, then Move to Trash and restore it from the Open list.
39. **A role that cannot list kinds.** As quill-contributor, Open still offers
    Posts and Pages, and says nothing about the kinds it could not read.

### Every route (9.16)

Sign in as quill-admin unless a test says otherwise. Each command reads the
site's list of routes first; where a test says "a site without it", use a
WordPress older than the route, or a security plugin that hides it.

40. **Hear Where a Link Goes.** In a post, put the caret on a link to one of
    the site's pages and choose Edit > WordPress > Hear Where a Link Goes. It
    says the page's title and description. With the caret on no link, type
    an address with a typo: it says the page could not be reached and offers
    nothing to insert.
41. **Fix Link Text.** Add a "click here" link to the About page. Edit >
    WordPress > Fix Link Text lists it with "About"; Use the Page's Title
    makes the link say "About".
42. **Dead links.** Add a link to `/no-such-page/`, publish, and run Tools >
    WordPress > Check This Page. The summary says one link goes nowhere, and
    Dead Links names it.
43. **Insert Icon** (WordPress 7.0 or later). Insert > WordPress Icon lists the
    site's icons. Insert one with a label and one as decorative; publish and
    check with NVDA that the first is read by its label and the second is
    skipped. An empty label inserts nothing.
44. **Upload a Large File.** Tools > WordPress > More Media > Upload a Large
    File with a video over 16 MB. QUILL says its size and that it can take a
    while, then that it is in the Media Library, and the library item plays.
    A file bigger than the host accepts is refused in the site's own words.
    WordPress has no upload in pieces, so nothing goes to the sideload route.
45. **Regenerate Sizes.** After Edit a Picture on the Site, Tools > WordPress >
    More Media > Regenerate Sizes on that picture. The thumbnail in the
    Media Library shows the edit.
46. **Previous Looks** (block theme). Change a colour in Site Styles, then
    Tools > WordPress > Manage > Previous Looks. The earlier look is listed
    with its date and palette; Go Back to This Look restores it, and the look
    you left is now in the list.
47. **Menu History.** Open Tools > WordPress > Menus, remove an item, then
    Tools > WordPress > Menu History: Bring Back Removed Items puts it back at
    the end. For a Navigation block, Restore This Version restores it whole.
48. **Space Used.** Tools > WordPress > Manage > Space Used says the total and
    lists uploads, themes, plugins, WordPress and the database in words. As
    quill-editor it says the role cannot see it.
49. **Download a Copy of the Site's Design** (block theme). Tools > WordPress
    > Manage > Download a Copy of the Site's Design saves a zip that opens
    and holds the theme. On a classic theme it says only a block theme can.
50. **Send This Document to WordPress.** Open a Markdown file with a heading
    and a picture beside it, and choose File > WordPress > Send, Copy and
    Download > Send This Document to WordPress. The draft's title is the
    heading, the picture is in the Media Library, and the draft opens.
51. **Publish to Another Site and Duplicate.** With two sites connected, copy
    a post with a category the other site lacks: QUILL asks before creating
    it, and the copy is a draft there with its pictures. Duplicate a page on
    the same site: the new draft is titled "(copy)" and opens.
52. **Download My Writing.** Save the site to an empty folder; check
    `index.md`, one file per page and post, and the pictures folder. Run it
    again: it says everything is already up to date.
53. **Send a Folder as Drafts.** A folder of three Markdown files, one with a
    "click here" link. The confirmation gives the count and says one has
    things to look at; three drafts arrive.
54. **Coming Up and What Changed.** Schedule a post on each site. Tools >
    WordPress > Your Sites > Coming Up lists both by date. Leave a comment
    as quill-contributor, then What Changed on My Sites lists it; run it
    again and it says nothing is new.
55. **QUILL Lite.** Repeat 40, 43, 50 and 54 in QUILL Lite.

### Forms (17a)

Tests 56 to 62 need nothing from the site. Tests 63 to 68 need QUILL
Accessible Forms installed and active on the test site first. It is not there
yet: installing it from `S:\code\baf` waits on Jeff (wordpress.md 17a.13,
question 3). Until then, run 63 to 68 only as far as the "needs QUILL
Accessible Forms" sentence in test 63.

Forms is on in every feature profile except Essential. The commands have no
keys: use the menus, or type "form" in the Command Palette. Where they are
(the same in both editors, from `quill/core/forms/menu.py`):

- **File:** New Form.
- **Insert:** Form Field. **View:** Form Outline. **Format:** Form Rules.
- **Tools > Forms:** Check This Form, Fill It In Yourself, Form Properties,
  Publish Form, Insert Form Into Page, Test on Site, Responses, Save As Web
  Page, Save As Word Document, Save As Large Print, Save As Braille-Ready
  Text, Draft a Form, Plain Language, Suggest Autofill Hints.

The tests build one form, "Ask us anything", as the guided Forms lessons do.

56. **New Form.** File > New Form, title "Ask us anything", template Contact
    form, Next, and save it. Expect "Saved Ask us anything.qaf, a contact form
    with 3 questions." and the form open. View > Form Outline starts "Page 1,
    3 questions".
57. **Form Field.** With the caret on Your message, Insert > Form Field,
    search "choose", pick Choose one, label "Best way to reply", choices
    Email and Phone. Expect "Inserted Best way to reply, choose one." Then
    add a Phone number question labelled "Phone number": "Inserted Phone
    number, phone number."
58. **Form Rules.** Format > Form Rules > Add Rule: when Best way to reply is
    `phone`, then Show, Phone number. Expect "Show Phone number when Best way
    to reply is Phone." and an `@when #reply is "phone"` line under the
    question. Typing `Phone` or `PHONE` gives the same rule: the answer is
    matched to the choice in any capitals.
59. **Check This Form.** Expect "Phone number has no autofill hint, so the
    browser cannot fill it in. The hint is tel." Go to It lands on the
    question. Add `@autocomplete "tel"` under it; Check Again lists only the
    "On the site today" lines.
60. **Fill It In Yourself.** Tab through: each label is read, with
    "required" where it is. Choosing Phone says "Phone number appears.";
    choosing Email says "Phone number is hidden." Submit shows What Would Be
    Sent, starting "Nothing was sent." Escape twice returns to the document.
61. **Save As Large Print and Braille-Ready Text.** Expect "Saved Ask us
    anything large print.docx, a large-print Word document, 18 point and up,
    with 5 questions, lines to write on and boxes to check." and "Saved Ask us
    anything.txt, braille-ready text with 5 questions, one a block." Open
    both; with the braille pack installed, also save the UEB contracted .brf.
    Repeat in Safe Mode: all four Save As commands still work.
62. **Not a form.** In an ordinary text document, run Check This Form from
    the Command Palette. Expect "Check This Form works in a form document, a
    .qaf file. Start one with New Form in the File menu, or open one."
63. **Publish Form.** With QUILL Accessible Forms not installed, expect "Publish
    Form needs QUILL Accessible Forms on QUILL WordPress Test Site, and the site
    does not offer it." Once it is installed: Publish as Live, then Publish.
    Expect "Published Ask us anything on QUILL WordPress Test Site, form" a
    number, "live." Publish again: the question says Update. While the
    site lists both `qaf/v1` and the older `baf/v1`, every request goes to
    `qaf/v1` (the alias answers reads only).
64. **Changed on the site.** Change the form's title in QUILL Accessible Forms
    on the site, then Publish Form. QUILL asks before publishing over it, and
    keeps the site's copy as a previous version.
65. **Insert Form Into Page and Test on Site.** Open the Contact page, put the
    caret after its first paragraph, Insert Form Into Page, choose the form,
    and Publish or Update. Test on Site in the form opens that page in the
    browser, where the form can be filled in with NVDA.
66. **Responses.** Send two responses from the site. Responses, with the form
    open, goes straight to "Responses to Ask us anything", newest first.
    Read, View, Find, Export to CSV, Open as Table and Export to Word each do
    what they say. Mark one, then Delete: it goes to the Trash in BITS
    Accessible Forms.
67. **New response count.** Restart, then run any site command for Forms.
    Expect, once a session, "QUILL WordPress Test Site:" and the number of new
    responses to Ask us anything. Say New Count turns it off.
68. **QUILL Lite, and Safe Mode.** Repeat 56 to 61, 63 and 66 in QUILL Lite.
69. **Form files.** In Explorer, Open with on `Ask us anything.qaf` lists
    QUILL and QUILL Lite. File > Open in each editor shows it under All
    supported files and under Forms, and the Forms commands are available
    once it is open. Rename a copy to `.bfl` and open it: it is still a
    form, and nothing is said about the older extension.
    Then in Safe Mode, Publish Form and Responses each say they are off in
    Safe Mode, while writing, checking, Fill It In Yourself and the four Save
    As commands still work.

### What the site lets you test that QUILL may not have yet

The site already has what the later parts of wordpress.md need. Add a test here
when each feature lands:

- the site logo and icon (6.10);
- synced patterns (9.13);
- the `batch/v1` route (Fix in Bulk, merge);
- revisions and autosaves (9.3);
- a scheduled post (5.8);
- a block island (Latest Posts, the gallery shortcode);
- the Classic content;
- a page hierarchy (Page Order);
- five roles (Users).

Known detail: WordPress lists the batch endpoint as the route `/batch/v1` in the
REST index, not as a namespace. A capability check must look at `routes`.

## Live run

Written by `docs/qa/wordpress-live-run.py`; run it again rather than editing this
section by hand. A result marked "no sign-in" was checked without signing in.

- **Date:** 2026-11-05 04:16 UTC
- **Build:** 7efdc39da (feat/wordpress)
- **Mode:** dry run, signed in as quilladmin, quill-editor, quill-author, quill-contributor
- **Site:** QUILL WordPress Test Site (https://lp.csedesigns.com/wordpress), WordPress 7.1.4
- **Plugins:** WooCommerce 11.2.2 (`wc/v3`); Yoast SEO 28.8 (`yoast/v1`); The Events Calendar 6.18.3 (`tribe/events/v1`); BITS Accessible Forms 1.0.0 (`baf/v1`); Abilities (version not shown) (`wp-abilities/v1`)
- **Results:** 60 pass, 4 fail, 27 needs Jeff, 31 not run

### Site and routes

| Test | Check | Result | As | Detail |
|---|---|---|---|---|
| index | REST index answers and names the site | pass | no sign-in | 802 routes in 27 namespaces |
| index | Site version and application passwords (load_site_info) | pass | no sign-in | WordPress 7.1.4; application passwords offered |
| 9.15 | Plugins QUILL recognises (site_health.recognised) | pass | no sign-in | The Events Calendar, WooCommerce, Yoast SEO, Abilities for AI |
| 17a | Forms plugin namespace (site_namespace) | pass | no sign-in | baf/v1, 12 routes; QUILL module qaf_site |
| 17a | Forms route takes the model QUILL sends | needs Jeff | no sign-in | POST /baf/v1/forms lists bfl_source, config, description, settings, status, title but not model; the plugin on the site may predate set_model (BAF 045c682). Test 65 shows whether a published form has its fields |
| 9.16 | Every 9.16 route QUILL needs (routes.unavailable) | pass | no sign-in | all 11 offered: url_details, icons, pieces, post_process, style_revisions, navigation_revisions, menus, directory_sizes, export, media, writing |
| 9.15 | Every 9.15 route QUILL needs (site_features.unavailable) | pass | no sign-in | all offered: notes, edit_picture, which_password, library_alt, bulk_moderation |
| 9.15 | Picture edits the site takes (edit_modifiers) | pass | no sign-in | crop, flip, rotate |
| 44 | Upload in pieces matches the site's sideload route | fail | no sign-in | sideload requires image_size: it takes a generated sub-size of a picture, not a piece of a file, and QUILL's PieceUpload sends no image_size; finalize takes id, sub_sizes, not the total and pieces QUILL sends |
| 45 | Regenerate Sizes action is the site's (post-process) | pass | no sign-in | action create-image-subsizes |
| 9.15 | Every Site Health test listed (health_test_names) | pass | no sign-in | 6 tests: background-updates, loopback-requests, https-status, dotorg-communication, authorization-header, page-cache; signed out it says only an administrator can |
| 9.16 | Batch route found and sized (SiteInfo.supports) | pass | no sign-in | in routes, not namespaces; 25 per batch; methods POST, PUT, PATCH, DELETE |

### Public content

| Test | Check | Result | As | Detail |
|---|---|---|---|---|
| seed | Published posts are public, the rest are not | pass | no sign-in | 6 public posts; Pinned news sticky; no draft, pending, private or trash |
| seed | Pages and the page parent | pass | no sign-in | 10 public pages; Meet the Team is a child of About Us |
| 38 | Events type and Open Day are public | pass | no sign-in | Open Day, id 136, https://lp.csedesigns.com/wordpress/event/open-day/ |
| 9.15 | Properties' custom fields for an ordinary post | needs Jeff | no sign-in | Properties would show 35 fields on every post, 32 of them The Events Calendar's event, venue and organizer fields; Yoast's title and description are among the rest. Decide whether to hide another plugin's fields |
| 38 | Open Day's own address answers | fail | no sign-in | https://lp.csedesigns.com/wordpress/event/open-day/ answers 404 while ?event=open-day answers 200: the site's rewrite rules were not flushed after the Events type was registered (setup.sh needs 'wp rewrite flush'); a... |
| 9.6 | oEmbed for /welcome/, and the proxy needs a sign-in | pass | no sign-in | embed: rich, 'Welcome to the test site - QUILL WordPress Test Site'; proxy 401 signed out |

### Connecting (4)

| Test | Check | Result | As | Detail |
|---|---|---|---|---|
| 4 | HTTP address is refused, explaining HTTPS | pass | no sign-in | QUILL only connects to WordPress sites over HTTPS, so your password is never sent in the clear. Check that the address starts with https://. |
| 1 | Connect by hand as quilladmin | pass | quilladmin | Connected to QUILL WordPress Test Site as Administrator. |
| 1 | Connect by hand as quill-editor | pass | quill-editor | Connected to QUILL WordPress Test Site as Editor. |
| 1 | Connect by hand as quill-author | pass | quill-author | Connected to QUILL WordPress Test Site as Author. |
| 1 | Connect by hand as quill-contributor | pass | quill-contributor | Connected to QUILL WordPress Test Site as Contributor. |
| 3 | Wrong password: a plain sentence naming the site | pass | quill-editor | 401 incorrect_password: QUILL WordPress Test Site did not accept the application password. Check it belongs to this account, then reconnect. |
| 2 | Connect with the browser | needs Jeff | - | approving in a browser |
| 5, 6 | Many sites, Remove | needs Jeff | - | the Sites window |

### Writing and opening (5.1, 5.2)

| Test | Check | Result | As | Detail |
|---|---|---|---|---|
| 11 | Open by Web Address finds each address | pass | no sign-in | welcome/ (page 200) -> ('post', 118); about/ (page 200) -> ('page', 113); about/team/ (page 200) -> ('page', 115); ?p=118 (page 200) -> ('post', 118) |
| 7 | Categories and tags are listed | pass | quill-editor | 6 categories, 5 tags |
| 9 | Open lists drafts and the Trash | pass | quill-editor | 1 drafts, 1 in Trash; row: Things to check before publishing, Draft, last changed 4 November 2026, 8:49 AM |
| 10 | Every Block round trip, Markdown and HTML | pass | quill-editor | 25 blocks; byte for byte apart from blank lines |
| 11 | Open by Web Address, signed in | pass | quill-editor | welcome/ (page 200) -> ('post', 118); about/ (page 200) -> ('page', 113); about/team/ (page 200) -> ('page', 115); ?p=118 (page 200) -> ('post', 118) |
| 7, 8, 12 | New Post, New Page, Open Local Draft | needs Jeff | - | local documents in the editor |

### Saving and publishing (5.3, 5.4, 9.2)

| Test | Check | Result | As | Detail |
|---|---|---|---|---|
| 13 | Save Draft to Site: a draft, not public | not run | quill-editor | dry run: this one writes to the site |
| 14 | Publish or Update makes it public | not run | quill-editor | dry run: this one writes to the site |
| 15 | Contributor: Submit for Review, Pending | not run | quill-contributor | dry run: this one writes to the site |
| 16 | Author cannot publish a page | not run | quill-author | dry run: this one writes to the site |
| 17 | Private and Scheduled keep their status | not run | quilladmin | dry run: this one writes to the site |
| 18 | Conflict: a change on the site is found | not run | quilladmin | dry run: this one writes to the site |
| 14 | Publish confirmation and clipboard | needs Jeff | - | hearing the confirmation |
| 18 | Compare, Open the Site's Copy, Send Mine Anyway | needs Jeff | - | the conflict dialog |
| 19 | Closing never publishes | needs Jeff | - | closing a window |

### Properties, versions, Trash (5.5, 5.6)

| Test | Check | Result | As | Detail |
|---|---|---|---|---|
| 20 | Properties on Pinned news go to the site | not run | quill-editor | dry run: this one writes to the site |
| 21 | Welcome has its 3 site revisions | pass | quill-editor | 3 revisions, newest 2026-11-04T08:50:18 |
| 23 | Move to Trash, listed, restored | not run | quill-editor | dry run: this one writes to the site |
| 21, 22 | View, Restore, Compare with Site | needs Jeff | - | the versions window |

### Checks (7)

| Test | Check | Result | As | Detail |
|---|---|---|---|---|
| 24 | Check Before Publishing finds every seeded problem | pass | quill-editor | 9 findings: 9 things to look at: 6 problems, 3 to check |
| 24 | Go to It reaches each finding | needs Jeff | - | the caret and a screen reader |

### Pictures (6)

| Test | Check | Result | As | Detail |
|---|---|---|---|---|
| 25 | Media Library rows and Find: banner | pass | quill-editor | 9 items; banner: wide-banner, image, 2400 by 800, 8 KB, no alt text, uploaded 4 November 2026, 7:42 AM |
| 25 | Edit Alternative Text on wide-banner | not run | quill-editor | dry run: this one writes to the site |
| 27 | Upload a picture | not run | quill-editor | dry run: this one writes to the site |
| 28 | Remove from Library | not run | quilladmin | dry run: this one writes to the site |
| 26, 27 | Insert Picture from the library or this computer | needs Jeff | - | the image dialog |
| 28 | Remove from Library keeps a backup | needs Jeff | - | the Documents folder |

### Comments, categories and tags (9.8, 9.13)

| Test | Check | Result | As | Detail |
|---|---|---|---|---|
| 29 | Approve, reply, spam, many at once | not run | quilladmin | dry run: this one writes to the site |
| 30 | Add, rename and delete a tag; merge | not run | quilladmin | dry run: this one writes to the site |

### Listen and watch (6.1a)

| Test | Check | Result | As | Detail |
|---|---|---|---|---|
| 31-32 | Tone, clip and captions: public address and type | pass | no sign-in | quill-test-tone 200 audio/x-wav 48044 bytes; quill-test-clip 200 video/mp4 38176 bytes; quill-test-clip-en 200 text/vtt 124 bytes |
| 32 | Captions found and read (from_library, fetch_captions) | pass | no sign-in | 2 cues (English); 1 s: 'This is the QUILL test clip.'; 5.5 s: none |
| 34 | A picture is not playable (from_library) | pass | no sign-in | photo-volunteers: not playable; the tone: audio |
| 36 | Play Media Here on the rendered Listen and Watch page | pass | no sign-in | audio: A three-second test tone; video: quill-test-clip.mp4; paragraph: none (rendered HTML) |
| 36 | Play Media Here on the page's blocks | pass | quill-editor | audio: A three-second test tone; video: quill-test-clip.mp4; paragraph: none (raw blocks) |
| 31 | Play on the tone | needs Jeff | - | an ear: the tone, the keys, Close |
| 32 | The clip's picture with NVDA and JAWS | needs Jeff | - | eyes and a screen reader |
| 33 | Nothing is saved | needs Jeff | - | the Downloads and Documents folders |
| 35 | Open in Browser, Open in Quill Media Player | needs Jeff | - | a browser |
| 37 | QUILL Lite repeats 31, 32, 36 | needs Jeff | - | QUILL Lite |

### The site's own kinds (5.2)

| Test | Check | Result | As | Detail |
|---|---|---|---|---|
| 38 | An opened Event goes back to its own route | fail | no sign-in | load_item keeps the post type ('event') as the kind, so Save Draft to Site would send to /wp/v2/event, which the site does not have (the route is /wp/v2/events) |
| 11, 38 | Open by Web Address finds an Event | fail | no sign-in | not found as expected: event/open-day/ (page 404) -> None. find_by_address looks only in posts and pages |
| 38 | Open lists Events with Open Day | pass | quilladmin | kinds: Posts, Pages, Products, Events, Events, Calendar Embeds; Open Day listed |
| 38 | Open Day: change, send, Trash and restore | not run | quilladmin | dry run: this one writes to the site |
| 39 | Contributor still gets Posts and Pages | pass | quill-contributor | Posts, Pages, Events, Events, Calendar Embeds |

### More from the API (9.15)

| Test | Check | Result | As | Detail |
|---|---|---|---|---|
| TEC | Events Coming Up, signed out (plugin_events.coming_up) | pass | no sign-in | 0 upcoming events listed |
| sizes | Picture sizes offered by name and width | pass | quill-editor | Thumbnail, 150 wide; Medium, 300 wide; Medium large, 768 wide; Large, 1024 wide; 1536X1536, 1536 wide; Full size, 1600 wide |
| library alt | Pictures with no alt text, library-wide | pass | quill-editor | 4 pictures: animated-ish.gif, decorative-divider.png, wide-banner.png, woocommerce-placeholder.webp |
| media edit | Edit a Picture on the Site: rotate | not run | quill-editor | dry run: this one writes to the site |
| notes | Notes on blocks: add, reply, resolve | not run | quill-editor | dry run: this one writes to the site |
| introspect | Which application password, quilladmin | pass | quilladmin | On QUILL WordPress Test Site, QUILL is using the application password named QUILL regression tests, made 4 November 2026, 7:40 AM, last used 4 November 2026, 7:52 AM. |
| introspect | Which application password, quill-editor | pass | quill-editor | On QUILL WordPress Test Site, QUILL is using the application password named QUILL regression tests, made 4 November 2026, 7:40 AM, last used 4 November 2026, 7:52 AM. |
| introspect | Which application password, quill-author | pass | quill-author | On QUILL WordPress Test Site, QUILL is using the application password named QUILL regression tests, made 4 November 2026, 7:41 AM, last used 4 November 2026, 7:52 AM. |
| introspect | Which application password, quill-contributor | pass | quill-contributor | On QUILL WordPress Test Site, QUILL is using the application password named QUILL regression tests, made 4 November 2026, 7:41 AM, last used 4 November 2026, 7:52 AM. |
| custom fields | Custom fields on Welcome | pass | quill-editor | 35 fields, 2 left alone |
| styles | Style variations, each with its Palette Report | pass | quilladmin | Twenty Twenty-Five: 23 variations; first: Evening, 56 pairings, 32 below the minimum for body text |
| Site Styles | Site Styles: colours and sizes by name | pass | quilladmin | 8 colours, 5 sizes; Colour: Base (white), #FFFFFF, the page background; the text on it is 18.8 to 1, passes |
| patterns | Pattern Directory search, described in words | pass | quill-editor | 5 patterns; Contact Details, from WordPress.org's Pattern Directory. Contact Section. Blocks, in order: Columns, Column, Group, I... |
| pattern categories | Pattern categories for synced patterns | pass | quilladmin | 0 categories, 1 synced patterns read |
| TEC | The Events Calendar: venues and Coming Up | pass | quilladmin | 0 upcoming, 0 venues |
| TEC | New Event as a draft, then changed | not run | quilladmin | dry run: this one writes to the site |
| WooCommerce | Products in Properties, orders read only | not run | quilladmin | no products on the site; 0 orders read |
| WooCommerce | Light edit: price, then put back | not run | quilladmin | dry run: this one writes to the site |
| Yoast | SEO title and description with lengths | not run | quilladmin | dry run: this one writes to the site |
| Abilities | Abilities listed; a read-only one run | pass | quilladmin | 17 abilities; ran core/get-environment-info: {"environment": "staging", "php_version": "8.3.36", "db_server_info": "11.8.9... |
| Site Health | Every Site Health test, one line each | pass | quilladmin | 7 lines; good: Background updates are working.; good: Your site can perform loopback requests.; good: Your website is using an active HTTPS connection.; good: Can communicate with WordPress.org.; recommended: The auth... |
| Site Health | An editor hears it is for administrators | pass | quill-editor | Health checks: only an administrator can run them. |

### Every route (9.16)

| Test | Check | Result | As | Detail |
|---|---|---|---|---|
| 45 | Regenerate Sizes after the edit | not run | quill-editor | dry run: this one writes to the site |
| 40 | Hear Where a Link Goes, and a typo | pass | quill-editor | Goes to 'About Us - QUILL WordPress Test Site'. Typo: https://lp.csedesigns.com/wordpress/abuot-us-typo/ could not be reached: the page is not there. |
| 41 | Fix Link Text uses the page's title | pass | quill-editor | 'click here' became 'About Us - QUILL WordPress Test Site' |
| 42 | Dead links named | pass | quill-editor | 1 of 2 link goes nowhere. |
| 43 | Insert Icon: labelled, decorative, never unnamed | pass | quill-editor | 88 icons, first Arrow Down, WordPress; an empty label inserts nothing |
| 44 | Upload a Large File in pieces | not run | quill-editor | dry run: this one writes to the site |
| 46 | Previous Looks: change a colour, go back | not run | quilladmin | dry run: this one writes to the site |
| 47 | Menu History: menus and Navigation revisions read | pass | quilladmin | 1 menus (1 Navigation blocks), 0 revisions |
| 48 | Space Used in words; an editor cannot | pass | quilladmin | Uploads: 200 KB. Themes: 13.8 MB. Plugins: 122.7 MB. WordPress itself: 90.8 MB. Database: 6.2 MB. Altogether: 233.7 MB. Editor: Your account on QUILL WordPress Test Site is an Editor, which cannot see how much space t... |
| 49 | Download a Copy of the Site's Design | pass | quilladmin | twentytwentyfive.zip, 8190968 bytes, 254 files (kept in memory, not saved) |
| 50 | Send This Document to WordPress | not run | quill-editor | dry run: this one writes to the site |
| 51 | Duplicate makes a '(copy)' draft | not run | quilladmin | dry run: this one writes to the site |
| 52 | Download My Writing, then up to date | pass | quill-editor | 22 files, 3 pictures; again: Your writing on QUILL WordPress Test Site is in archive: 0 saved, 22 already up to date. |
| 53 | Send a Folder as Drafts | not run | quill-editor | dry run: this one writes to the site |
| 54 | Coming Up lists the scheduled post | pass | quilladmin | 1 item is scheduled on your site. The next is Scheduled for next month on QUILL WordPress Test Site, 4 December 2026, 5:00 PM. |
| 54 | What Changed lists a new comment once | not run | quill-contributor | dry run: this one writes to the site |
| 43 | Icons read by label, decorative skipped | needs Jeff | - | NVDA on the page |
| 44 | Progress spoken at each quarter | needs Jeff | - | an ear |
| 45 | The thumbnail shows the edit | needs Jeff | - | eyes |
| 47 | Bring Back Removed Items, Restore This Version | needs Jeff | - | the Menus window (the run reads the history only) |
| 55 | QUILL Lite repeats 40, 43, 50, 54 | needs Jeff | - | QUILL Lite |

### Forms (17a)

| Test | Check | Result | As | Detail |
|---|---|---|---|---|
| 63 | Publish Form as Live, then Update | not run | quilladmin | dry run: this one writes to the site |
| 64 | A change on the site is seen before publishing | not run | quilladmin | dry run: this one writes to the site |
| 65 | Insert Form Into Page: the page shows the form | not run | quilladmin | dry run: this one writes to the site |
| 66 | Responses: two sent, listed newest first, exported, deleted | not run | quilladmin | dry run: this one writes to the site |
| 56-62 | New Form to Not a form | needs Jeff | - | local; the editors and a screen reader |
| 64 | QUILL asks before publishing over the site's change | needs Jeff | - | the question |
| 65 | The form filled in with NVDA on the page | needs Jeff | - | NVDA in a browser |
| 67 | New response count after a restart | needs Jeff | - | restarting QUILL |
| 68 | QUILL Lite, and Safe Mode | needs Jeff | - | QUILL Lite and Safe Mode |

## Looking after the site

- **Where it runs:** on lp.csedesigns.com, in two Docker containers,
  `wordpress-test` (WordPress 7.x, PHP 8.3, Apache) and `wordpress-test-db`
  (MariaDB 11). Both are defined in `~/app/wordpress-test/docker-compose.yml`.
- **How it is reached:** the web stack's Caddy serves it at `/wordpress/`,
  through the `@wordpress_test` route in `~/app/web/caddy/Caddyfile`. That
  route sits above the redirect to letitglow.app, like the other
  lp.csedesigns.com routes. The Caddyfile was backed up before the change, as
  `Caddyfile.bak-2026-11-04-wordpress`.
- **Secrets:** in `.env` and `test-accounts.txt`, both chmod 600. Search
  engines are told not to index the site.
- **Reseed:** `reset.sh`.
- **Check:** `verify.sh`.
- **Logs:** `docker logs wordpress-test`.
- **Update WordPress:** `docker compose pull && docker compose up -d`, in
  `~/app/wordpress-test`.
- **Change the database password:** change it in MariaDB, update `.env`, then
  `docker compose up -d --force-recreate wordpress`. The container reads the
  password when it starts.
- **Remove it all:**
  1. Run `docker compose down -v` in `~/app/wordpress-test`.
  2. Delete the `@wordpress_test` route from the Caddyfile.
  3. Reload Caddy with
     `docker exec web-caddy-1 caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile`.
