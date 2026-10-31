# QUILL Social 0.3 Release Notes

Version 0.3.0 (build 2).

QUILL Social is new. It is a social reader and writer built for people who
use a screen reader and a keyboard. It brings your Mastodon and Bluesky
accounts, Lemmy servers and news feeds into one window, with one set of keys.

This is QUILL Social's first public release. The number is 0.3, not 1.0, on
purpose. The reading side is ready for daily use. The writing side works for
plain text posts, and some of what you will see in the menus is still early.
This page says which is which.

## The short version

Add an account, press F5, and read. Up and Down move between posts. Left and
Right read one part of a post at a time: who wrote it, the text, the time,
and the rest. Enter opens the whole post. Ctrl+N writes a new post. Every
command is on a menu, and every menu row says its key.

## Sharp at any display scaling

QUILL Social handles each monitor's scaling itself, so text stays sharp at 125, 150
and 200 percent and on monitors with different scaling, and windows and list
columns keep their proportions.

## What you can connect

Choose **File > Add Account...** (Ctrl+Shift+A). The Network list offers:

- **Mastodon.** Pick or type your server, choose **Sign in with browser**,
  approve access in your browser, paste the code it shows, and choose
  **Finish sign-in**. There is nothing to set up on the server first.
- **Pixelfed, GoToSocial and Firefish.** These servers speak Mastodon's
  language, so they sign in the same way.
- **Bluesky.** Choose **Open app password page**, make an app password on
  Bluesky, and paste it with your full handle, such as name.bsky.social.
  Use an app password, never your main password.
- **Lemmy.** Type the server, such as lemmy.world. QUILL Social reads that
  server's newest posts. No sign-in is needed, and none is used.
- **mock.** A practice network on your own computer, for trying the app with
  no account at all.

**Verify connection** in the same window tests your sign-in before you add
the account, and says what went wrong if it fails.

The first time QUILL Social opens, it adds a demo account called "Demo
timeline", so the window is not empty. Its posts are samples, not real ones.

## News feeds

QUILL Social is a feed reader too. It reads RSS, Atom and JSON Feed.

- **Feeds > Add Feed...** (Ctrl+Shift+N) takes a feed address. Paste a web
  site's address instead and it finds the site's feeds and lets you pick one.
- Put feeds in folders with **Feeds > New Folder...** (Ctrl+Alt+F). Each
  folder says its unread count in its own name, such as "News (12 unread)".
- **Feeds > Feed settings...** (Ctrl+Shift+P) sets how often a feed is
  checked, how long its articles are kept, and keyword rules that hide an
  article, mark it read, or star it.
- A feed that sends only a summary can fetch the full article instead.
- Articles are read as plain text, never as a web page. Links read as their
  text and address, and pictures read as their description.
- **Feeds > Import OPML...** (Ctrl+I) and **Feeds > Export OPML...** (Ctrl+E)
  move your feeds in from, or out to, another reader, folders included.
- Smart folders gather articles by a rule, such as one keyword or unread
  only: **Feeds > New smart folder...** (Ctrl+Shift+M).
- **Feeds > Mark all read** (Ctrl+Shift+K) says how many it marked.
  **Feeds > Undo mark all read** (Ctrl+Z) puts back exactly those.

Feeds are checked in the background while QUILL Social is open. New articles
are announced, and focus stays where it is.

## Listen to your reading list

**Listen > Listen to this view** (Ctrl+Shift+L) reads the unread articles in
the current view aloud, one after another, with a Windows voice. Before each
one you hear its title and where it is from.

- **Listen > Play / Pause** (Ctrl+Shift+Space)
- **Listen > Next article** (Ctrl+Shift+Period)
- **Listen > Previous article** (Ctrl+Shift+Comma)
- **Listen > Stop listening** (Ctrl+Shift+S)

Words like "Paused" and "Stopped" come from your screen reader, not the
reading voice, so the two never talk at once.

## Getting it

Two downloads. Choose one. Both run on Windows 10 and Windows 11, 64-bit.

- **QUILL-Social-Setup-Shared-0.3.0.exe**, the installer. It installs for
  your Windows account only, so it does not ask for administrator rights. It
  installs the shared QuillVille runtime if this computer does not already
  have it, then QUILL Social, with a Start menu entry and an uninstaller.
  Uninstalling never deletes your data.
- **QUILL-Social-Portable-0.3.0.zip**, the portable copy. Unpack it anywhere.
  It keeps your accounts list, posts, drafts and settings in its own data
  folder next to the app.

## The keys you will use most

These work in the main window. The composer and other windows have their own
buttons and access keys.

**Finding your place**

- Where Am I: Ctrl+Shift+I. Your account, network, and which post of how many
  you are on.
- Command Center: Ctrl+Shift+C. Type part of a command's name, then Enter.
- Search: Ctrl+L. Results appear under Discover.
- Find Text: Ctrl+Shift+F. Finds words in the list you are in. F3 finds the
  next one and Shift+F3 the previous one.
- Refresh: F5.
- Catch Up: Ctrl+Shift+H.
- Tab and Shift+Tab move between the navigation tree, the search box, the
  list and the details.

**Acting on the focused post**

- Reply: Ctrl+R. Quote: Ctrl+Q.
- Favourite: Ctrl+F. Boost / Repost: Ctrl+Shift+R. Bookmark: Alt+B.
  Press the key again to undo.
- Open conversation: Ctrl+G. Open links: Ctrl+O.
- Mark read: Ctrl+K. Flag for follow-up: Ctrl+Shift+G.
- Accessibility check: F7. It looks for missing picture descriptions and
  similar problems.
- Send to QUILL: Ctrl+Shift+Q. It saves the post and its conversation as a
  document you can open in QUILL, and says where.

**Writing**

- New Post: Ctrl+N.
- In the composer: Alt+P publishes now, Alt+S schedules, Alt+D saves a
  draft, Alt+A adds media and Alt+T edits its description. Escape closes the
  composer.
- Studio > Drafts... (Ctrl+Shift+D) opens a saved draft again.

**Help**

- F1: the keys in effect now, including any you changed.
- Help > User Guide: Ctrl+F1.
- Help > Keyboard Reference: Ctrl+Shift+F1. Every key, grouped by task, and
  how to change one.

You can also reach every command without a chord. Press Alt, the menu's
letter, then the command's letter. For example, Alt+S, then D opens Studio >
Drafts....

## Privacy and accounts

**What it signs in to.** Only the accounts you add. Mastodon and servers
like it are reached with the browser sign-in you approve. QUILL Social asks
for permission to read, to post, and to follow. Bluesky is reached with the
app password you make. Lemmy and news feeds need no sign-in.

**Where your sign-in is kept.** Your access token or app password goes to
Windows Credential Manager, under your Windows account. It is never written
to QUILL Social's own files. The portable copy does the same, so on another
computer you sign in again.

**What is stored on your computer.** Posts and articles you have loaded,
your read places, bookmarks, flags, folders, drafts, schedules, settings and
keys. An installed copy keeps them in `%APPDATA%\QuillSocial`. The portable
copy keeps them in its own data folder.

**What is sent where.**

- To your Mastodon-type server or Bluesky: requests for your timeline and
  notifications, the posts you publish, and your favourites, boosts and
  bookmarks.
- To a Lemmy server: a request for its newest posts.
- To a feed's web site: a request for the feed, and for the full article if
  you turned that on. Feeds must use a secure (https) address.
- Open links opens your web browser. Nothing else is sent anywhere.

**No AI service.** **Tools > Summarize this feed (AI)** (Ctrl+Alt+R) works on
your computer: it lists who posted and the first sentence of each post.
Nothing is sent to an AI company. The accessibility check also runs on your
computer.

## Known limitations

QUILL Social is 0.3. These are the gaps we know about.

**Writing**

- Posts are sent as text, with a content warning and visibility. Media,
  picture descriptions, polls and quotes can be set in the composer, but they
  are not sent yet.
- A reply sent with **Publish now** goes out as a new post, not as a reply.
  A scheduled reply to a Mastodon post does go out as a reply.
- On Bluesky, replies and split threads go out as separate posts.
- Scheduled posts go out only while QUILL Social is open. The schedule time
  is typed in UTC.
- Lemmy is read only: no posting, voting or notifications.

**Accounts**

- Bluesky works with accounts on bsky.social. An account on its own server
  cannot sign in yet.
- There is no way to remove an account from inside the app yet, and the demo
  account cannot be removed either.
- Bluesky bookmarks are kept in QUILL Social only.

**Early or sample parts**

- The GitHub section of the navigation tree shows sample items. You cannot
  connect a GitHub account yet.
- **Item > Play media** opens the player, but this version cannot play sound.
- **Tools > Insights / Analytics** is early and counts mostly the demo
  account's posts.
- Studio, Approvals, the Safety Center, Notification policies and Plugins
  work on what is stored on your computer. They are a start, not a finished
  publishing studio.
- Open conversation shows only the posts already loaded on your computer.

**Keys and help**

- Changing a key means editing a file while QUILL Social is closed. There is
  no window for it yet. **Help > Keyboard Reference** explains how.
- The Command Center does not list the Feeds, Listen and Find commands yet.
  Use their menus or keys.
- Moving between panes with one key, and jumping to a timeline by number,
  are planned. Use Tab and Shift+Tab today.
- There is no Check for Updates command in QUILL Social yet.

## Getting help

Press **F1** for the keys in effect now. **Help > User Guide** (Ctrl+F1)
and **Help > Keyboard Reference** (Ctrl+Shift+F1) open in your browser and
need no internet connection. **Help > About** (Alt+F1) says your version.

Questions and problems: write to **support@community-access.org**. Community
Access reads every message. If something in this list matters to you, tell
us, because that is how we choose what comes next.
