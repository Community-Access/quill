# WordPress regression testing for QUILL and QUILL Lite

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
    File with a video over 16 MB. Progress is spoken at each quarter, and the
    library item plays. On a site without the pieces route, QUILL says so and
    sends nothing.
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

Tests 56 to 62 need nothing from the site. Tests 63 to 68 need BITS
Accessible Forms installed and active on the test site first. It is not there
yet: installing it from `S:\code\baf` waits on Jeff (wordpress.md 17a.13,
question 3). Until then, run 63 to 68 only as far as the "needs BITS
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
    form, Next, and save it. Expect "Saved Ask us anything.bfl, a contact form
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
    .bfl file. Start one with New Form in the File menu, or open one."
63. **Publish Form.** With BITS Accessible Forms not installed, expect "Publish
    Form needs BITS Accessible Forms on QUILL WordPress Test Site, and the site
    does not offer it." Once it is installed: Publish as Live, then Publish.
    Expect "Published Ask us anything on QUILL WordPress Test Site, form" a
    number, "live." Publish again: the question says Update.
64. **Changed on the site.** Change the form's title in BITS Accessible Forms
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
