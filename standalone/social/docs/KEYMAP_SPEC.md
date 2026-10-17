# QUILL Social — Keyboard Reference
**Every key in this document works in the version you have.**

This is the list **Help > Keyboard Reference** opens. It gives the keys QUILL Social ships with, grouped by what you are doing, and says which menu each command lives on, so you can always reach a command by walking the menus if you forget its key. Pressing **F1** (Help > Keyboard Guide (shortcuts)) shows a shorter, in-app list of the keys *currently in effect*, including any you have changed.

Until 2026-10-17 this page was the design specification for the keyboard. It promised keys that were never bound — moving between panes with F6, jumping to a destination with Ctrl and a number, spell checking a post with F7, and more — so following it did nothing. Those are now listed separately at the end, without keys, as plans rather than instructions.

---

## How keys work in QUILL Social

- **Every menu row that has a key shows it** beside its name, so a screen reader reads the key as you arrow through the menu. Some commands have no key yet; they are reached through their menu. For example, Feeds > New Folder... has no key: press Alt+D to open the Feeds menu, then F for New Folder.
- **Keys act on the focused post.** Reply, Quote, Favourite, Bookmark and the other item commands work on whichever row of the post list is focused. With no post selected, Favourite, Bookmark, Boost and Reply say so rather than doing nothing silently.
- **Changing a key.** The keys for the commands in the F1 list can be changed by editing `keymap.json` in QUILL Social's data folder (`%APPDATA%\QuillSocial` on Windows, or the `data` folder beside a portable copy). Close QUILL Social first: it writes that file again when it closes. Example: to make Favourite answer Ctrl+J, change the line `"favourite": "Ctrl+F"` to `"favourite": "Ctrl+J"`, save, and start QUILL Social. F1 then lists Ctrl+J.
- **Limits of changing a key.** There is no window for this yet; it is the file or nothing. The menus keep showing, and keep answering to, the key QUILL Social shipped with. If two commands are given the same key, only one of them answers it, so give each its own. Commands that are not in the F1 list (most of the Feeds, Listen, Studio and Tools commands) cannot be changed.

---

## 1. Finding your place

| Key | Command | Menu | What you hear |
| :--- | :--- | :--- | :--- |
| **Ctrl+Shift+I** | Where Am I | Tools | Your workspace, account, network, and which post of how many you are on. |
| **Ctrl+Shift+C** | Command Center | Tools | A searchable list of commands; type part of a name, then Enter. |
| **Ctrl+L** | Search | Tools | Focus moves to the search box. Type, then Enter; results appear under Discover. |
| **F5** | Refresh | Tools | Pulls new posts from every active account and refreshes your feeds. |
| **F1** | Keyboard Guide (shortcuts) | Help | The in-app list of the keys in effect now. |

In the post list, **Up** and **Down** move between posts, **Left** and **Right** read the previous or next field of the focused post (author, text, time and the rest), and **Enter** opens the post in the Details pane. **Tab** and **Shift+Tab** move between the navigation tree, the search box, the post list and the details.

## 2. Reading and acting on a post

| Key | Command | Menu | What it does |
| :--- | :--- | :--- | :--- |
| **Ctrl+G** | Open conversation | Item | Opens the whole thread the focused post belongs to. |
| **Ctrl+O** | Open links | Item | Opens the links in the focused post in your browser. |
| **Ctrl+K** | Mark read | Item | Marks the focused post read. |
| **Ctrl+F** | Favourite | Item | Favourites (likes) the focused post, or takes the favourite off again. |
| **Alt+B** | Bookmark | Item | Bookmarks the focused post, or removes the bookmark; bookmarked posts gather under Bookmarks in the navigation tree. |
| **Ctrl+Shift+R** | Boost / Repost | Item | Boosts (reposts) the focused post to your followers, or undoes the boost. |
| **Ctrl+Enter** | Play media | Item | Plays the audio or video attached to the focused post. |

Item > Flag for follow-up, Item > Accessibility check and Item > Send to QUILL have no key yet.

## 3. Writing

| Key | Command | Menu | What it does |
| :--- | :--- | :--- | :--- |
| **Ctrl+N** | New Post | Compose | Opens an empty composer for your default account. |
| **Ctrl+R** | Reply | Compose | Opens the composer as a reply to the focused post. |
| **Ctrl+Q** | Quote | Compose | Opens the composer quoting the focused post. |

Inside the composer, the buttons carry their own access keys: **Alt+P** Publish now, **Alt+S** Schedule, **Alt+D** Save draft, **Alt+A** Add media and **Alt+T** Edit alt text. Escape closes the composer.

## 4. Finding text in the list

| Key | Command | Menu | What it does |
| :--- | :--- | :--- | :--- |
| **Ctrl+Shift+F** | Find Text | Tools | Asks for a word or phrase and a direction, then moves to the first row that contains it. |
| **F3** | Find Next | Tools | Moves forward to the next row containing the same text. |
| **Shift+F3** | Find Previous | Tools | Moves back to the previous row containing it. |

Example: in Unified Home, press Ctrl+Shift+F, type `release`, press Enter. Focus lands on the first post that mentions a release and you hear its position, such as "3 of 20". Press F3 for the next one. Find searches the rows of the list you are looking at, in every kind of view (posts, feeds, GitHub items, drafts); it wraps around at the end and says "not found" when nothing matches. It does not search other views or the full text of articles. Find Text was on Ctrl+F until 2026-10-17, where Favourite always answered first.

## 5. Feeds

| Key | Command | Menu | What it does |
| :--- | :--- | :--- | :--- |
| **Ctrl+Shift+N** | Add Feed | Feeds | Subscribe by feed address, or paste a site's address and pick from the feeds it offers. |
| **Ctrl+Shift+P** | Feed settings | Feeds | Title, refresh interval, how long to keep articles, and keyword rules for the selected feed. |
| **Ctrl+Shift+K** | Mark all read | Feeds | Marks everything in the current view read and says how many. |
| **Ctrl+Z** | Undo mark all read | Feeds | Puts back exactly the items the last Mark all read changed. |

Feeds > New Folder..., the smart-folder commands, Import OPML..., Export OPML... and Unsubscribe from feed have no key yet.

## 6. Listening

| Key | Command | Menu | What it does |
| :--- | :--- | :--- | :--- |
| **Ctrl+Shift+L** | Listen to this view | Listen | Reads the unread articles in the current view aloud, one after another. |

Listen > Play / Pause, Next article, Previous article and Stop listening have no key yet; open the Listen menu with Alt+L.

## 7. Everything else

| Key | Command | Menu | What it does |
| :--- | :--- | :--- | :--- |
| **Ctrl+Shift+A** | Add Account | File | Connects an account: Mastodon or a Mastodon-compatible server, Lemmy, or Bluesky. |
| **Alt+F4** | Exit | File | Closes QUILL Social. Your reading place is remembered. |

The Studio menu (Drafts, Agenda / Calendar, Queue schedule, Approvals), the rest of the Tools menu (Catch Up, Insights / Analytics, Safety Center, Notification policies, Plugins, Outbox, Summarize this feed) and File > Preferences have no keys yet.

---

## Planned, not yet in this version

These were in the original design and are not bound to anything today. They are listed so you know they are coming, not so you try them:

- moving between the major panes with one key, forwards and backwards (use Tab and Shift+Tab today);
- jumping straight to one of nine pinned destinations;
- switching to the previous or next timeline in order;
- moving to the previous or next post in the same conversation, or by the same author;
- a context menu of actions for the focused post;
- spell checking and saving a draft from the composer with dedicated keys (use the composer's Save draft button, Alt+D, today);
- GitHub-specific variants of Open conversation, Reply and Bookmark.
