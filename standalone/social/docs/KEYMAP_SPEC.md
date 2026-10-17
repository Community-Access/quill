# QUILL Social — Keyboard Reference
**Every key in this document works in the version you have.**

This is the list **Help > Keyboard Reference** opens. It gives the keys QUILL Social ships with, grouped by what you are doing, and says which menu each command lives on, so you can always reach a command by walking the menus if you forget its key. Pressing **F1** (Help > Keyboard Guide (shortcuts)) shows a shorter, in-app list of the keys *currently in effect*, including any you have changed.

Until 2026-10-17 this page was the design specification for the keyboard. It promised keys that were never bound — moving between panes with F6, jumping to a destination with Ctrl and a number, spell checking a post with F7, and more — so following it did nothing. Those are now listed separately at the end, without keys, as plans rather than instructions.

---

## How keys work in QUILL Social

- **Every menu command has a key, and every menu row shows it** beside its name, so a screen reader reads the key as you arrow through the menu. Since 2026-10-17 there are no exceptions: the 31 commands that used to be reachable only through their menu have keys of their own, listed in the tables below.
- **Every command also has its own letter in its menu.** Press Alt, the menu's letter, then the command's letter, one key at a time with nothing held down. No two commands in one menu share a letter. For example, Alt+D, then F opens Feeds > New Folder..., and Alt+L, then S stops listening.
- **Keys act on the focused post.** Reply, Quote, Favourite, Bookmark and the other item commands work on whichever row of the post list is focused. With no post selected, Favourite, Bookmark, Boost and Reply say so rather than doing nothing silently.
- **Changing a key.** Every key in this document can be changed by editing `keymap.json` in QUILL Social's data folder (`%APPDATA%\QuillSocial` on Windows, or the `data` folder beside a portable copy). Close QUILL Social first: it writes that file again when it closes. Example: to make Favourite answer Ctrl+J, change the line `"favourite": "Ctrl+F"` to `"favourite": "Ctrl+J"`, save, and start QUILL Social. Item > Favourite then shows Ctrl+J, Ctrl+J favourites the focused post, and F1 lists it. The names in the file are the command names F1 shows, with underscores for spaces (`listen_toggle` is Play / Pause, `delete_smart_folder` is Delete smart folder).
- **Limits of changing a key.** There is no window for this yet; it is the file or nothing. If two commands are given the same key, only one of them answers it, so give each its own. If your `keymap.json` was saved by an earlier version and already gives one of the new keys to another command, your choice stands and the new command is left without a key until you give it one; F1 shows which. File > Exit stays on Alt+F4, which Windows owns.

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
| **Ctrl+Shift+G** | Flag for follow-up | Item | Flags the focused post so it gathers under Flagged, or takes the flag off again. |
| **F7** | Accessibility check | Item | Checks the focused post for missing image descriptions and other problems, and reads you what it found. |
| **Ctrl+Shift+Q** | Send to QUILL | Item | Saves the focused post and its whole conversation as a Markdown document for QUILL, in the exports folder of QUILL Social's data folder, and says where. |

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
| **Ctrl+Alt+F** | New Folder | Feeds | Asks for a name and makes a folder for feeds. |
| **Ctrl+Shift+M** | New smart folder | Feeds | Saves a search across your feeds as a folder that keeps itself up to date. |
| **Ctrl+Alt+M** | Edit smart folder | Feeds | Changes the name or search of the smart folder selected in the navigation tree. |
| **Ctrl+Shift+Delete** | Delete smart folder | Feeds | Asks first, then deletes the selected smart folder. The articles it matched are not touched. |
| **Ctrl+I** | Import OPML | Feeds | Subscribes to every feed in an OPML file, keeping its folders. |
| **Ctrl+E** | Export OPML | Feeds | Saves your subscriptions and folders to an OPML file. |
| **Ctrl+Alt+U** | Unsubscribe from feed | Feeds | Asks first, then unsubscribes from the feed selected in the navigation tree and removes its cached items. |

The two keys that remove something both ask before they act, and answering No changes nothing.

## 6. Listening

| Key | Command | Menu | What it does |
| :--- | :--- | :--- | :--- |
| **Ctrl+Shift+L** | Listen to this view | Listen | Reads the unread articles in the current view aloud, one after another. |
| **Ctrl+Shift+Space** | Play / Pause | Listen | Pauses the reading, or carries on from where it paused. If nothing is being read yet, it starts Listen to this view. |
| **Ctrl+Shift+Period** | Next article | Listen | Skips to the next article. |
| **Ctrl+Shift+Comma** | Previous article | Listen | Goes back to the previous article. |
| **Ctrl+Shift+S** | Stop listening | Listen | Stops reading. |

Example: open a feed, press Ctrl+Shift+L, and the first unread article starts. Press Ctrl+Shift+Period to skip one you do not want, Ctrl+Shift+Space to pause while you answer the door and again to carry on, and Ctrl+Shift+S when you are done. The comma and period are the keys beside M, the same pair many players use for back and forward.

## 7. Planning posts (Studio)

| Key | Command | Menu | What it does |
| :--- | :--- | :--- | :--- |
| **Ctrl+Shift+D** | Drafts | Studio | Lists your saved drafts; open one to keep writing it. |
| **Ctrl+Shift+Y** | Agenda / Calendar | Studio | What is scheduled to publish, by day. |
| **Ctrl+Shift+U** | Queue schedule | Studio | The times of day queued posts go out. |
| **Ctrl+Shift+W** | Approvals | Studio | Posts waiting for someone to approve them before they publish. |

## 8. Everything else

| Key | Command | Menu | What it does |
| :--- | :--- | :--- | :--- |
| **Ctrl+Shift+A** | Add Account | File | Connects an account: Mastodon or a Mastodon-compatible server, Lemmy, or Bluesky. |
| **Ctrl+Comma** | Preferences | File | Announcement verbosity, high contrast and what each row speaks. |
| **Alt+F4** | Exit | File | Closes QUILL Social. Your reading place is remembered. |
| **Ctrl+Shift+H** | Catch Up | Tools | Opens Catch Up under Discover: a digest of what you missed. |
| **Ctrl+Alt+I** | Insights / Analytics | Tools | How your posts have done, as a report you can read line by line; you hear the number of posts sent and replies received. |
| **Ctrl+Alt+T** | Safety Center | Tools | Mutes, blocks and filters. |
| **Ctrl+Alt+P** | Notification policies | Tools | Quiet hours and which notifications reach you. |
| **Ctrl+Alt+G** | Plugins | Tools | Turn plugins on and off. |
| **Ctrl+Shift+B** | Outbox | Tools | Posts waiting to be sent, for example while you are offline. |
| **Ctrl+Alt+R** | Summarize this feed (AI) | Tools | A short summary of the current view, as a report. |
| **Ctrl+F1** | User Guide | Help | Opens the user guide in your browser. |
| **Ctrl+Shift+F1** | Keyboard Reference | Help | Opens this document. |
| **Alt+Shift+F1** | Product Requirements | Help | Opens the product requirements document. |
| **Alt+F1** | About | Help | The version of QUILL Social you have. |

Rarely used commands, such as the Help documents and the settings-like Tools windows, have longer keys on purpose, so the short ones stay free for what you do every few minutes. Ctrl+Alt keys and keyboard layouts: where the right Alt key types accented letters, a Ctrl+Alt key may run its command instead of typing the letter while the search box has focus; the menu always works.

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
