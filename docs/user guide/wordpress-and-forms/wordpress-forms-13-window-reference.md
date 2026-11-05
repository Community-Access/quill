# Chapter 13: Every window, field and button

## What this chapter covers

This chapter is a reference. It goes through every WordPress command in menu
order and, for each one, says where it is, which WordPress roles can use it,
every field, list and button in its window, what each one does on your site,
and what you hear. The earlier chapters explain how to use these together;
come here when you want to know exactly what a button does before you press
it. The names are the ones on screen, without their underlined letters.
Forms windows are described in full in Chapters 8 and 9.

## How to read this chapter

**Where.** Every command is in the same menu in QUILL and QUILL Lite. Where a
command has a WordPress key, it is given as the letter to press after
Ctrl+Alt+Shift+Grave (Chapter 12).

**Who.** WordPress's standard roles, from least to most: Subscriber,
Contributor, Author, Editor, Administrator. QUILL asks your site what your
account may actually do, so a site that changes its roles with a plugin is
read correctly; the roles below are WordPress's defaults. In short:

- **Contributors** write and edit their own posts, but cannot publish or
  upload.
- **Authors** also publish their own posts and upload files. They cannot
  write pages.
- **Editors** also write and publish pages, edit everyone's posts, moderate
  comments and manage categories and tags.
- **Administrators** also run the site: settings, menus, widgets, users,
  plugins, themes, fonts and styles.

A window your role cannot use does not open; you hear one sentence, such as
"Your account on Community Radio is an Author, which cannot manage users."

**The shared shapes.** Most windows are one of five shapes, so their common
parts are described once here:

- **A list window** has the list, sometimes a **Find** field above it (type
  and press Enter to narrow the list), a read-only **Details** field saying
  more about the row you are on, one button per action, and **Close**.
  Enter runs the main action. A button that needs a row is dimmed until you
  are on one.
- **A choice window** has one list and OK and Cancel. Enter chooses.
- **A question window** has one field and OK and Cancel.
- **A confirmation** names the site and what will change, and has a button
  named for the change, such as **Move to Trash**, and Cancel. Nothing is
  sent until you press it.
- **A report** has a read-only **Report** field to read line by line, **Copy
  All**, and **Close**.

**The site.** A command that works on a whole site, not the page in front of
you, asks **Site** first when you have more than one: a choice window with
your default site selected.

## File > WordPress

### New Page and New Post

- **Where:** File > WordPress > New Page... (key G) and New Post... (key N).
- **Who:** a post, Contributor and up; a page, Editor and up.
- **The window:**
  - **Site:** which of your sites it belongs to, for good;
  - **Title:** filled in by you; the theme shows it;
  - **Slug:** filled in from the title as you type;
  - **Write in:** Markdown or HTML, which cannot change later;
  - for a post, a **Categories** group and a **Tags** group of check boxes;
  - **Create** and Cancel.
- **On the site:** nothing. The document is made on your computer.
- **You hear:** "New post for Community Radio. Ctrl+S keeps it on this
  computer; nothing is sent until you choose Save Draft to Site or Publish."

### Open Page or Post

- **Where:** File > WordPress > Open Page or Post... (key O).
- **Who:** Contributor and up; you see what your role may edit.
- **The windows:**
  - **Show:** a choice of Posts, Pages and any kind your site adds, such as
    Events;
  - **Open from** your site: a list window. The list is labelled Posts,
    Pages or Items; each row is the title, status and when it changed.
    **Find by title or status** narrows it. Buttons: **Open**, **Move to
    Trash...** and **Restore from Trash**;
  - **Open as:** "HTML, exactly as the site has it" or "Markdown, easier to
    read; anything Markdown cannot show is kept exactly";
  - **Unsaved Version,** when the site has a newer autosave: "Yes, open the
    unsaved version" or "No, open the copy on the site".
- **On the site:** reads the list and the page. Move to Trash and Restore
  from Trash change the page's status.
- **You hear:** "Opened Opening Hours from Community Radio." If you already
  have a working copy: "Opened your working copy of Opening Hours. Compare
  with Site shows what changed on the site since."

### Open by Web Address

- **Where:** File > WordPress > Open by Web Address... (key W).
- **Who:** Contributor and up.
- **The window:** a question, **Web address**, with the clipboard's address
  already in it.
- **On the site:** finds the page by its address, and opens it as above.
- **You hear:** the usual "Opened" sentence, or "That address is not on any
  of your connected sites."

### Open Local Draft

- **Where:** File > WordPress > Open Local Draft... (key L).
- **Who:** anyone; it reads only your computer.
- **The window:** a choice, **Drafts**, newest first, each with its site.
- **You hear:** "You have no local WordPress drafts yet." when there are none.

### Save Draft to Site

- **Where:** File > WordPress > Save Draft to Site (key D). Dimmed outside a
  WordPress page.
- **Who:** Contributor and up for posts; Editor and up for pages.
- **On the site:** creates or updates the page as a draft, uploads any
  pictures from your computer first, and keeps the site's copy in Previous
  Versions before replacing it.
- **You hear:** "Draft saved to Community Radio. It is not public." If the
  site's copy changed since you opened it, the **The Site Copy Changed**
  window asks **What now**: Compare the two, Open the site's copy, or Send
  mine anyway (which asks once more, **Send Mine**).

### Publish or Update

- **Where:** File > WordPress > Publish or Update... (key P). Called Submit
  for Review when your role cannot publish. Dimmed outside a WordPress page.
- **Who:** publishing posts, Author and up; pages, Editor and up;
  Contributors submit for review.
- **The window:** a confirmation titled, for example, "Publish on Community
  Radio", with the title and what Check Before Publishing found, and a
  **Publish** button, or **Publish Anyway** when there are findings.
- **On the site:** publishes the page, or updates it, keeping a private or
  scheduled status as it was.
- **You hear:** "Published on Community Radio. The address is on the
  clipboard." or "Submitted for review on Community Radio." For a new page,
  **Add to a Menu** asks: Yes, open Menus; Not this time; or No, and stop
  asking for that site.

### Schedule Publish

- **Where:** File > WordPress > Schedule Publish... (key E). Dimmed outside
  a WordPress page.
- **Who:** Author and up for posts; Editor and up for pages.
- **The window:** **Date (year-month-day)**, **Time**, **Time zone** (your
  site's first), and a **Problem** field at the top when the last try could
  not be used. Then a confirmation, **Schedule**. On a page already
  scheduled, **What now**: Change the schedule, or Publish now (**Publish
  Now**).
- **On the site:** sets the page to publish at that time.
- **You hear:** "Scheduled on Community Radio for" and the date and time.

### Open on Site and Copy Address

- **Where:** File > WordPress > Open on Site (key I) and Copy Address
  (key Y). Dimmed outside a WordPress page.
- **Who:** anyone who can open the page.
- **You hear:** "Address copied." or "Draft address copied. It needs a
  WordPress sign-in to open." Before the page is on the site: "This is not
  on Community Radio yet."

### Properties

- **Where:** File > WordPress > Properties... (key R). Dimmed outside a
  WordPress page.
- **Who:** whoever may edit the page.
- **The window:** **About** (read only: site, address, author, last
  change, reading level); **Title**; **Slug**; **Status** (Draft, Pending
  review, Published, Private);
  **Excerpt**; for a post, the **Categories** and **Tags** check boxes,
  **Allow comments**, **Keep at the top of the blog**; **Password to read it
  (optional)**; and any custom and plugin fields. OK and Cancel.
- **On the site:** nothing until your next send.
- **You hear:** "Kept with your copy: 2 categories, 3 tags. They go to the
  site when you next send."

### Custom Fields

- **Where:** File > WordPress > Custom Fields.... Dimmed outside a WordPress
  page.
- **Who:** whoever may edit the page.
- **The window:** one field per custom field your site registers for that
  kind of page, each labelled and explained by the site, and OK.
- **You hear:** "3 custom fields kept with your copy. They go to Community
  Radio when you next send." or "Community Radio has no custom fields for a
  post."

### Plugin Fields

- **Where:** File > WordPress > Plugin Fields.... Dimmed outside a WordPress
  page.
- **Who:** whoever may edit the item.
- **The window:** only the fields your site's plugins have:
  - The Events Calendar: **Starts**, **Ends**, **Venue**;
  - WooCommerce: **Regular price**, **Sale price**, and **Stock** where the
    shop counts it;
  - Yoast SEO or Rank Math: **SEO title** and **SEO description**, each with
    a read-only count against what search engines show.
- **On the site:** saves straight away; a price change asks first (**Change
  Price**).
- **You hear:** "Saved to Community Radio:" and what was saved.

### Previous Versions

- **Where:** File > WordPress > Previous Versions... (key V). Dimmed outside
  a WordPress page.
- **Who:** whoever may edit the page; the site's own history needs the right
  to edit it there.
- **The window:** a list window, **Versions**, newest first. Buttons:
  **View...** (a report, **Version**, of the whole text) and **Restore**.
- **On the site:** nothing. Restore only changes your document.
- **You hear:** "Version put in the editor. Nothing was sent; your text
  before is in Previous Versions."

### Compare with Site

- **Where:** File > WordPress > Compare with Site (key C). Dimmed outside a
  WordPress page.
- **The window:** a report, lines starting "Site:" and "Yours:".

### Move to Trash

- **Where:** File > WordPress > Move to Trash... (key T). Dimmed outside a
  WordPress page.
- **Who:** whoever may delete the page: your own posts, Author and up;
  anyone's, Editor and up.
- **The window:** a confirmation, **Move to Trash**.
- **On the site:** moves the page to WordPress's Trash.
- **You hear:** "'Hours' moved to the Trash on Community Radio."

### Send and Copy

All in File > WordPress > Send and Copy:

- **Send This Document to WordPress...** **Make it a**: post or page. Then
  the site. The draft is made, its pictures uploaded. Who: Contributor and
  up (Author and up with pictures, which need uploading).
- **Publish to Another Site...** Dimmed outside a WordPress page. **Copy
  to**: the other site. If that site lacks some categories or tags, a
  confirmation, **Create Them**, or Cancel to copy without them. Arrives as
  a draft.
- **Duplicate...** **Duplicate a**: post or page; then the item; then
  **Where**: this site or another. You hear "'Hours (copy)' is a new draft
  on Community Radio."
- **Send a Folder as Drafts...** A folder chooser; then a confirmation,
  **Send 3 Drafts**, which lists anything to look at in each file.
- **Download My Writing...** A folder chooser. Saving runs in the background,
  and you hear when it is done. Run it again to carry on or update.

### Switch Site, Sites and Connect a Site

- **Switch Site...** (key S): a choice, **Site**. You hear "Default site:
  Community Radio."
- **Sites...** (key Shift+S): the WordPress Sites list window. Buttons:
  **Add...**, **Rename...** (question, **Name**), **Verify**, **Make
  Default**, **Remove...** (confirmation, **Remove**), and **Which
  Password**, which says which of your application passwords QUILL signs in
  with.
- **Connect a Site...** (key A): the Connect a WordPress Site window, with
  **Kind of site**, **Site address**, **Username**, **Application
  password**, **Name for this site (optional)**, **Get Password with My
  Browser**, **Connect** and Cancel, and a **Problem** field after a failed
  try. Then, on older sites, **Paste the Application Password**, and
  sometimes **Your WordPress Username**. Any role can connect.

## Edit > WordPress

All dimmed outside a WordPress page. Who: anyone editing the page.

- **Next Block** and **Previous Block:** you hear the block, its place and
  its first words.
- **Where Am I:** you hear the block and what it sits inside.
- **Hear Where a Link Goes:** with no link at the caret, a question,
  **Address**; then a confirmation, **Insert Link**. Needs WordPress 5.9 or
  later.
- **Fix Link Text...:** the Fix Link Text list window, **Links**, with **Use
  the Page's Title** and **Use All Titles**. You hear "The link now says
  'About'." or "3 links now say where they go."

## View

All dimmed outside a WordPress page.

- **WordPress Blocks...** (key B): the Blocks list window. Buttons: **Go
  To**, **Move Up**, **Move Down**, **Duplicate**, **Remove...**
  (confirmation, **Remove Block**), **Change To...** (choice, **Kind of
  block**), **Group**, **Ungroup**. Changes only your document.
- **Preview Blocks:** a report, as your site draws the blocks. Nothing is
  saved on the site.
- **Block Notes...:** the Notes list window. Buttons: **Go to It**,
  **Reply...** (question, **Reply**), **Resolve or Reopen**, **Add Note...**.
  Needs WordPress 6.9 or later. Who: whoever may edit the page.
- **Play Media Here:** opens the player (see Media Library, below).

## Insert

All dimmed outside a WordPress page.

- **WordPress Block...:** the Insert Block list window, **Blocks**, with
  **Find**, **Insert**, and **WordPress.org Patterns...** (question, **Search
  for**; choice, **Patterns**; confirmation, **Insert** and the pattern's
  name). A block's own form follows, with one field, check box or list per
  setting.
- **Picture from the Media Library...:** a choice, **Files**; then the
  picture window. Who: Author and up.
- **Picture from This Computer...:** a file chooser, then the picture window.
  Uploads on your next send. Who: Author and up.
- **The picture window:** **Alternative text**, **Suggest Alternative
  Text**, **Decorative: it adds nothing a visitor needs**, **Caption**,
  **Display width** (choose or type pixels), **File size** (the library's
  sizes), **Use as featured image**, **Link to** (Nothing, The picture file,
  or an address you type), **Describe Image...**, **Insert** and Cancel. You
  hear "Picture inserted:" and its alternative text.
- **Link to a Page on This Site...:** a choice, **Page or post**. You hear
  "Link to 'About' inserted."
- **Note on This Block...:** a question, **Note**. In a Markdown document, a
  confirmation first, **Add Note**.
- **Make a Picture...:** the Picture Maker: **Describe the picture, or the
  change you want**, **Shape**, **Background**, **Colour** (for a solid
  background), **Make the picture** (then **Make the change**), **Suggest
  from Page Content**, **Versions**, **Description of the chosen version**,
  **Describe Image**, **Open in Image Viewer**, **Save As...**, **Insert into
  Document...**, **Open folder** and **Close**. A confirmation, **Make the
  Picture**, names the provider before anything is sent.
- **WordPress Icon...:** the Insert Icon list window, **Icons**, with
  **Find**, **Insert with a Label...** (question, **Label**) and **Insert as
  Decorative**. Needs WordPress 7.0 or later.

## Format > WordPress

All dimmed outside a WordPress page.

- **Block Settings...:** the block's own form. In a Markdown document a
  confirmation may come first, **Make Protected Block**. You hear "Block
  settings changed."
- **Image Size...:** a choice, **Size**, with Back to Earlier Size at the
  top when there is one. You hear "Picture shown at" and the size.
- **Mark Language...:** a question, **Language**. You hear, for example,
  "The selection is marked as French."

## Tools > WordPress: checking

- **Check Before Publishing...** (key K): the list window, **Things to look
  at**, with **Go to It**. Dimmed outside a WordPress page. Reads only your
  document.
- **Check This Page:** the list window, **Findings**, with **Explain...**,
  **Go to It**, **Write a Note for the Theme Author...**, **Page Shape...**
  and **Dead Links...**. Reads the public page; any role.
- **Check the Whole Site...:** a choice, **How thorough**; then the list
  window, **Problems**, with **Pages...** and **Fix in Bulk...** (a preview
  report, then a confirmation such as **Fix 17 Pages**). Fixing needs the
  right to edit those pages: Editor and up.
- **Undo Site Fix...:** the list window, **Fixes**, with **Undo...** and
  **View...**.
- **Site-wide Find and Replace...:** questions **Find** and **Replace
  with**; a choice, **How to match** (plain words or a pattern, any case or
  matching case); then the list window, **Matches**, with **Include or
  Skip**, **Include All**, **Skip All**, **Include Block Settings** and
  **Replace...** (confirmation, **Replace in 4 Pages**). Editor and up.
- **Write an Accessibility Statement...:** a question, **Contact**. Opens a
  new page draft; nothing is sent.
- **Palette Report:** a report. Any role.
- **In Short...:** uses your AI; puts a paragraph at the top. Dimmed outside
  a WordPress page.

## Tools > WordPress: pictures and media

- **Media Library...** (key M): the list window, **Files**, with **Find**,
  **Insert...**, **Play...**, **Used In**, **Attach to This Page or Post**,
  **Set as Featured Image**, **Suggest Alternative Text...**, **Describe
  Image...**, **Edit Alternative Text...** (question, **Alternative text**),
  **Copy Address** and **Remove from Library...** (confirmation, **Remove**).
  Who: Author and up; changing or removing someone else's file, Editor and
  up.
- **The player:** Play and Pause, Stop, Rewind and Forward (ten seconds),
  Where Am I, **Speed**, **Position**, **Volume**, Mute, **Captions**, **Go
  to Position...**, **Open in Quill Media Player**, **Open in Browser** and
  **Close**.
- **Alt Text Review...** (key X): the list window, **Pictures**, with
  **Edit...**, **Mark Decorative**, **Suggest...** and **Go to Picture**.
  Dimmed outside a WordPress page; changes only your document.
- **Alt Text for the Whole Library...:** the list window, **Pictures**, with
  **Write...**, **Suggest...** and **Save Now**. Author and up for your own
  files; Editor and up for everyone's.
- **Visual Review...:** a confirmation, **Send for Review**, naming what goes
  to your AI; then a report. Published pages only.

### More Media

All in Tools > WordPress > More Media. Uploading needs Author and up.

- **Upload Files...** (key U): a file chooser; then for each file the upload
  window: **Alternative text**, **Suggest Alternative Text**, **Decorative:
  it adds nothing a visitor needs**, **Title**, **Caption**, **Describe
  Image...**, **Upload** and Cancel. If the file is already there, a
  confirmation, **Use the One There**.
- **Upload from Web Address...:** a question, **Address**.
- **Paste Image:** the upload window, for the copied picture.
- **Upload a Large File...:** a file chooser. Needs a site that takes
  uploads in pieces; otherwise it says Upload Files sends it in one go.
- **Regenerate Sizes...:** a choice, **Picture**. Needs WordPress 6.9 or
  later.
- **Make a Smaller Copy...:** choices **Picture**, **Largest width** and
  **Format**; then a confirmation, **Upload**.
- **Edit a Picture on the Site...:** choices **Picture** and **Edit**
  (turn, flip or crop, where the site offers it); a confirmation, **Make
  Edited Copy**; then **Use It Here**.
- **Site Logo...:** the list window, **Logo and icon**, with **From the
  Library...**, **From a File...**, **From the Picture Maker...**, **Preview
  a Width...** and **Restore Earlier...**; then a confirmation naming the new picture.
  Administrator.
- **Preview and Review...:** a choice, **Preview a new width for**; a
  question, **Width in pixels**; then as Visual Review.
- **Captions for Video...:** a choice of video; the review question,
  **Captions, one on each line with its time**.
- **Transcript for Audio...:** a choice of sound file; the review question,
  **Transcript**; a choice, **Insert it**: folded or in full.
- **Make a Listening Version...:** dimmed outside a WordPress page. When one
  exists, a confirmation, **Make Again**.
- **Name Embeds:** dimmed outside a WordPress page. A report.
- **Publish a Document as a Page...:** a file chooser; a question, **Page
  title**; for a scanned file, a confirmation, **Read the Pages**. Editor
  and up, for the page.

## Tools > WordPress: the site's content

- **Comments...:** the list window, **Comments**, with **Show...** (choice,
  **Show**: Waiting, Approved, Spam, Trash), the status's own buttons
  (Approve, Unapprove, Spam, Not Spam, Trash, Restore), **Approve All...**,
  **Reply...**, **Edit...**, **Open on Site**, **Waiting Count on First
  Use**, **Mark**, **Mark Everything** and **Do with Marked...**. Editor and
  up.
- **Categories and Tags...:** a choice, **Manage**; then the list window
  with **Add...**, **Rename...**, **Merge Into...**, **Convert to Tag...**
  (or Category), **Find Unused...**, **Delete...** and **Make Default...**
  (categories). Editor and up; Make Default, Administrator.
- **Menus...:** a choice, **Menu**; then the list window, **Menu items**,
  with **Add Page...**, **Add Post...**, **Add Category...**, **Add
  Link...**, **Rename...**, **Move Up**, **Move Down**, **Move In**, **Move
  Out**, **Remove...**, **Check Menu**, **Other Menu...** and
  **Locations...**. Administrator.
- **Menu History...:** a choice, **Menu**; the list window, **Versions**,
  with **Bring Back Removed Items...** and **Restore This Version...**.
  Administrator.
- **Site Check:** a report. Administrator.
- **Site Settings...:** the list window, **Settings**, with **Change...**:
  Site title, Tagline, Site language, Time zone, Date format, Time format,
  First day of the week, Administrator email, Front page shows, Front page,
  Posts page, Posts per page, New posts take comments, New posts take
  pingbacks, Turn emoticons into pictures, Default post format, Site icon.
  Each change is a confirmation such as **Change Tagline**. Administrator.

## Tools > WordPress > Design

Block themes only. Administrator.

- **Style Variations...:** the list window, **Variations**, with **Apply...**
  (confirmation) and **Put Back the Previous Look...**.
- **Site Styles...:** the list window, **Styles**, with **Change...**
  (question, **Colour** or **Size**) and **Put Back the Previous Look...**.

## Tools > WordPress > Plugin Extras

Only with the plugin on the site.

- **Events Coming Up...:** the list window, **Events**, with **Open** and
  **Open on Site**.
- **New Event...:** **Name**, **Starts**, **Ends**, **Venue**, and **Make
  Draft**.
- **Shop Orders...:** the list window, **Orders**, read only, with **Copy
  Order...** (confirmation, **Copy Order**). Whoever the shop lets read
  its orders.

## Tools > WordPress > Manage

- **Users...:** the list window, **Users**, with **Add User...** (questions
  **Username**, **Email**, **Name**, a choice **Role**, and a confirmation),
  **Edit...**, **Change Role...**, **Delete...** (choice, **Give their posts
  and pages to**, then a confirmation), **Application Passwords...** and **My
  Profile...** (**Display name**, **Biography**, **Website**).
  Administrator; My Profile, every role.
- **Application Passwords...:** the list window, **Passwords**, with
  **Revoke...**. Every role, for their own.
- **Plugins...:** the list window, **Plugins**, with **Activate or
  Deactivate...**, **Add Plugin...** (question, **Plugin's WordPress.org
  name**), **Delete...** and **Open in Dashboard**. Administrator.
- **Themes...:** the list window, **Themes**, with **Open in Dashboard**.
  Administrator.
- **Fonts...:** the list window, **Fonts**, with **Install...** (choice,
  **Font**) and **Delete...**. Administrator; WordPress 6.5 or later and a
  block theme.
- **Synced Patterns...:** the list window, **Patterns**, with **Edit...**,
  **Rename...**, **Unsync...**, **Delete...** and **New from Selection...**;
  first a choice, **Category**, when the site sorts patterns. Contributor and
  up for patterns your role may change.
- **Widgets...:** a choice, **Widget area**; the list window, **Widgets**,
  with **Add Text...**, **Edit...**, **Move to Area...**, **Remove...** and
  **Open in Dashboard**. Administrator; classic themes.
- **Site Map...:** the list window, **Site map**, with **Open** and **Open on
  Site**.
- **Template Outline:** a report. Block themes.
- **Bulk Edit...:** a choice, **Edit**: Posts or Pages; the list window with
  **Select**, **Select All**, **Change...** (choices **Change** and **To**;
  then a confirmation) and **Undo Bulk Edit...**. Editor and up.
- **Page Order...:** the list window, **Pages**, with **Move Up**, **Move
  Down**, **Move In**, **Move Out** and **Open**. Editor and up.
- **Previous Looks...:** the list window, **Looks**, with **Palette
  Report...** and **Go Back to This Look...**. Administrator.
- **Space Used:** a report. Administrator.
- **Download a Copy of the Site's Design...:** a save window. Administrator,
  block themes.
- **AI Abilities...:** the list window, **Abilities**, with **Turn On or
  Off** (confirmation, **Turn On** and the ability's name). WordPress 6.9 or
  later.
- **Ask the Site...:** a question, **Question**; a confirmation, **Run** and
  the ability's name, before each ability; then a report.
- **Sign Out This Site...:** a choice, **After signing out**: remove the site
  from QUILL, or keep it in the list.

## Tools > WordPress > Your Sites

Across every connected site.

- **Coming Up...:** the list window, **Scheduled**, with **Open**.
- **What Changed on My Sites...:** the list window, **Changes**, with **Open
  in Browser**.

## Where to next

- Previous: [Chapter 12: Every WordPress and Forms key](wordpress-forms-12-keys.html)
- Next: [Appendix A: Every WordPress feature QUILL uses](wordpress-forms-appendix-a-features.html)
- [Contents](wordpress-forms-guide.html)
