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
