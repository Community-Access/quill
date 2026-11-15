# Chapter 6: Comments, categories, tags, people and menus

## What this chapter covers

A site grows things around your writing: the comments visitors leave, the
categories and tags that sort your posts, the people who write with you, and
the menus that help visitors find your pages. You look after all of them in
the WordPress Workbench.

In this chapter you will moderate and answer comments, tidy categories and
tags, add and change the people on your site, and build a menu, adding items
and putting them where they belong.

By the end your comments will be answered, your posts sorted, your team set
up, and every new page reachable from your menus. Chapter 2 explains how the
Workbench moves, if you have not read it yet.

## Comments

**Tools > WordPress > Comments...** opens the Workbench at the comments
waiting for you to approve. Each site's **Comments** has a place for each of
WordPress's four lists: **Waiting**, **Approved**, **Spam** and **Trash**.
**Needs My Attention > Comments Waiting** gathers the waiting ones from every
site, and **Held as Spam** the ones the sites doubted.

Each row gives the comment's author, the post it is on and when it came.
Press Enter to read it in full in the details pane.

On a comment:

- **Item > Approve, or Not Spam** (`Ctrl+Shift+A`) publishes a waiting
  comment, or releases one from Spam.
- **Item > Unapprove** (`Ctrl+Shift+U`) takes an approved comment off the
  site, so it waits again.
- **Item > Spam** (`Ctrl+Shift+S`) marks it as spam. The site's spam filter
  learns from it.
- **Item > Reply...** (`Ctrl+Shift+M`) answers the comment, published under
  your name.
- **Item > Not Spam, and Allow This Sender** (`Ctrl+Alt+W`) approves it, and
  says whether that person's next comments will go straight through.
- **Delete** moves it to the Trash, and **Item > Restore from Trash**
  (`Ctrl+Shift+R`) brings it back.
- **Alt+Enter** opens its Properties, where you can correct its text, such as
  a phone number somebody posted by mistake, or its date. The sheet also
  shows the IP address it came from.

**Many at once.** Select several comments and approve, spam or trash them in
one go. You hear how each one went, so one refusal does not stop the rest,
and Ctrl+Z puts back only the ones that changed.

**For the whole site,** the Site menu has:

- **Site > Comment Counts** (`Ctrl+Alt+Shift+C`): how many wait, are approved,
  are spam and are in the Trash;
- **Site > Empty Spam...** (`Ctrl+Alt+E`): delete every comment held as spam,
  for good, after you confirm;
- **Site > Empty Comment Trash...** (`Ctrl+Alt+Shift+E`): the same for the
  Trash.

On a post in the Workbench, **Item > Show Its Comments**
(`Ctrl+Alt+Shift+M`) lists just that post's comments. In a comment list, the
filter takes `comment_type:` as well as words, and **View > Columns...** can
add the commenter's website, IP address, the comment's type and the comment
it replies to.

The first time you use a site in a session, QUILL says how many comments are
waiting, such as "Community Radio: 3 comments waiting."

### A walk-through: answering a question in the comments

1. Choose **Tools > WordPress > Comments...**. The Workbench opens on the
   comments waiting.
2. Tab to the list, arrow to the comment, and press Enter to read it.
3. Press Ctrl+Shift+A to approve it, so it shows on the site.
4. Press Ctrl+Shift+M, type your answer and press OK.
5. In the tree, move to **Spam** and check nothing real has been caught
   there. If something has, press Ctrl+Shift+A on it.

The guided lesson on comments, in **Help > Tutorials**, does the same on a
test site.

## Categories and tags

Categories are the broad shelves of a blog, such as News and Events. Tags are
the small labels, such as "volunteers" or "spring fair". Only posts have
them.

**Tools > WordPress > Categories and Tags...** opens the Workbench at the
site's **Categories**, shown as a tree, each under its parent. **Tags** is
just below it. Each row gives the name, how many posts use it, and its slug.
A plugin's own ways of grouping, such as event categories or genres, are
under **More Taxonomies**.

On a category or tag:

- **Enter**, or **Show Its Posts**, lists the posts filed there.
- **Alt+Enter** changes its name, slug, description and parent. A new name
  shows on every post that has it.
- **Item > Merge Into...** (`Ctrl+Shift+G`) moves every post across to
  another and then deletes the empty one, in one step.
- **Item > Convert to Category or Tag...** (`Ctrl+Shift+K`) turns a tag into
  a category, or the other way round, and keeps its posts.
- **File > New Here...** (`Ctrl+N`) makes a new one.
- **Delete Permanently...** removes it, after a question that says how many
  posts use it. The posts stay.
- **Copy to Site...** copies it to another of your sites.

Choosing categories and tags for one post is in its Properties (Chapter 3).
To rename, split or merge a term across all your posts and pages, see By Name
in Chapter 9.

## People

**Tools > WordPress > Manage > Users...** opens the Workbench at the site's
**People > Users**. Each row gives the person's name, username, role and
email. You need to be an Administrator to change anyone but yourself.

**Adding a person.** In Users, press Ctrl+N. **Add a Person** is one sheet:
username, email, first and last name, website, language and role. QUILL
makes a strong password and never shows it. WordPress sends no welcome email
when a person is added this way, and the preview says so, so tell them
yourself. They choose their own password with "Lost your password?" on the
sign-in page.

On a person:

- **Show Their Posts** lists what they wrote.
- **Change Role...** gives them another role, after a preview.
- **Alt+Enter** changes their name, email, website, biography and language,
  and shows how many posts they have written.
- **Their Application Passwords...** lists the apps and computers signed in as
  them, with Revoke after you confirm.
- **Item > Send Password Reset** (`Ctrl+Shift+W`) opens their wp-admin screen,
  where WordPress sends the reset email.
- **Set New Password...** gives them a new password you type. QUILL never says
  it or keeps it.
- **Sign Out Everywhere...** opens their wp-admin screen, where Log Out
  Everywhere is one button. WordPress keeps sign-ins out of its REST API.
- **Remove...** takes them off the site. It asks who gets their posts first,
  and the preview counts them, so no writing is lost.
- **Who Has Never Signed In** lists the people with no sign-in on record.
  WordPress itself does not keep sign-in times where QUILL can read them, so
  this works only when a plugin on the site records the last sign-in and
  shares it (as `last_login`). On any other site it says it cannot tell,
  rather than calling everyone new.

Select several people to change all their roles, or remove them, in one go.

QUILL will never take away your own Administrator role, or remove the last
Administrator on a site, whatever you select.

**Many people at once.** **Invite from a Spreadsheet...**, on a person's
context menu, reads a CSV file with columns for email, role and name. The
preview lists every row it will add and every row it leaves out, and why.
Then it adds each person and says how each went.

**Your own profile.** **Site > Your Profile...** (`Ctrl+Alt+Shift+P`) changes
your own name, email, website, biography and language on the site.

**Application passwords.** **People > Application Passwords** lists the
passwords on your own account, with when each was made and last used.
Ctrl+N makes a new one and shows it once, so copy it then. Delete revokes
one. The one QUILL itself signs in with is marked, so you do not revoke it
by accident.

**Site > Roles and What They May Do** (`Ctrl+Alt+R`) explains each role on the
site in plain words.

WordPress cannot change what a role may do by itself; that takes a role
plugin. When the site's role plugin shares its roles with QUILL (QUILL looks
for the Members plugin's `members/v1` routes), the same command lists the
site's own roles instead, each with how many capabilities it has:

- Choose a role to change what it may do. Its capabilities are listed one a
  line; delete a line to take one away, or add a line to give one. The
  preview says what the role gains and loses, and Ctrl+Z puts it back.
- Choose **New Role...** to make one. Give it a name, then its capabilities,
  one a line. Ctrl+Z takes the new role away again.

A change to a role reaches everyone who has it at once, so read the preview
carefully. On a site without such a plugin, change roles in wp-admin, with
Members or User Role Editor.

## Menus

A menu is the list of links in your site's header or footer that visitors use
to find your pages. WordPress does not add a new page to a menu by itself,
unless you ask it to, which is why QUILL asks "Add it to a menu?" the first
time you publish a page.

**Tools > WordPress > Menus...** opens the Workbench at the site's **Menus and
Navigation**. Each row is a menu, with where the theme shows it and how many
items it has.

### Adding an item to a menu

Use this to add a page, a post, a category, a tag, an item of any other kind
your site shows in menus, or a link to any address.

1. Arrow to the menu in **Menus and Navigation**.
2. Press Ctrl+N and choose **A new item in** the menu, which is first. Or press
   the Applications key and choose **Add Menu Item...**.
3. Under **Kind of item**, choose what the item links to, such as Pages,
   Posts, Categories, Tags, one of your site's own kinds, or **Custom
   Links**.
4. For anything but a custom link, type words from its name and press Enter,
   or leave the box empty to list them all, as View All does in wp-admin.
   Only published items are listed. For a kind with an archive page, such as
   Events, the archive is offered first.
5. Choose the one you want. Its name becomes the item's name.
6. Under **Under**, choose where it goes: **Top level of the menu**, or the
   item it should sit under, as a dropdown.
7. Under **Position**, choose **First**, or **After** one of the items
   already there. The end is chosen for you.
8. Read the preview. It says what is added, where, as a place such as "3 of
   7", and how many items move down to make room. Press **Add**.

For a custom link, QUILL asks for the **URL** and then the **Link text**, the
words the menu shows, and carries on from step 6.

Before it writes, QUILL reads the menu again. If somebody changed it in the
meantime, nothing is sent, and you are told. Afterwards you hear what was
added. Ctrl+Z takes the item out and puts the others back where they were.

### Adding new pages automatically

WordPress can add each new top-level page to a menu by itself, the moment it
is published.

1. Arrow to the menu in **Menus and Navigation**.
2. Press the Applications key and choose **Add New Pages Automatically...**.
3. The preview says whether it is on or off now, and what changes. Press
   **Turn On**, or **Turn Off**.

The same setting is a check box on the menu's Properties (Alt+Enter), labelled
"Automatically add new top-level pages to this menu", beside the menu's name
and description. Check it or uncheck it and press OK.

Either way, QUILL checks the setting has not changed on the site since you
looked, reads it back after saving, and Ctrl+Z turns it back. Pages already
in the menu stay where they are when you turn it off.

### More on a menu

- **File > New Here...** (`Ctrl+N`) on a menu asks whether you want a new
  item in it or **A new menu**. With no menu selected, it makes a menu.
- **Alt+Enter** changes the menu's name and description, and shows where the
  theme displays it.
- **Earlier Versions...** lists the states of the menu QUILL has seen. A
  classic menu keeps no history in WordPress, so QUILL keeps its own each time
  it reads one. Choose one to bring back the items removed since, after a
  preview. Ctrl+Z takes them out again.
- **Default Navigation Menu...**, on a block theme, says which Navigation menu
  the theme shows where none is chosen. On a site with none, WordPress makes
  one, so QUILL asks first.
- **Copy to Site...** copies the menu to another of your sites.
- **Delete Permanently...** (`Shift+Delete`) deletes the menu. The pages it
  linked to are not touched.

### Moving items around in a menu

The Menus window rearranges a menu's items. To open it, select a menu in the
Workbench's **Menus and Navigation**, press the Applications key, and choose
**Arrange Items...**. It also opens when you answer **Yes, open Menus** to the
"Add it to a menu?" question, with the new page already added at the end of
the menu you choose. **Other Menu...** in it opens another menu on the same
site.

Each row says the item, what kind of thing it links to, its level and its
place, such as "Sessions, page, level 1, 3 of 7".

- **Move Up** and **Move Down** change its place. Each press says the new one.
- **Move In** puts it under the item above it, as a dropdown. **Move Out**
  takes it back up a level.
- **Rename...** changes what the item says.
- **Remove...** takes it out of the menu. The page itself is not touched.
- **Check Menu** finds items with no name, and links to pages that are drafts
  or gone.
- **Locations...** chooses where the theme shows the menu, such as the header
  or the footer.

Sites with a block theme keep their menus in Navigation blocks. Those open in
the same window and work the same way. **Tools > WordPress > Menu History...**
lists earlier versions of a menu, and can make a Navigation block's menu
exactly as it was.

### A walk-through: putting a new page in the menu

1. Publish the new page. QUILL asks "Add it to a menu?".
2. Choose **Yes, open Menus**, and choose the menu. The Menus window opens
   with the page added at the end.
3. Press **Move Up** until it sits where you want it.
4. If it belongs under another item, such as About, press **Move In**.
5. Press **Check Menu** to make sure nothing points to a draft.
6. Close the window. The change is already on the site.

If you would rather every new top-level page joined the menu by itself, turn
on Add New Pages Automatically, as above.

## Where to next

- Previous: [Chapter 5: Pictures and the Media Library](wordpress-forms-05-pictures-and-media.html)
- Next: [Chapter 7: Checking before you publish](wordpress-forms-07-checking.html)
- [Contents](wordpress-forms-guide.html)
