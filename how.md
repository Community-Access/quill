# How WordPress works in QUILL and QUILL Lite: a UX walkthrough

Written 2026-11-14 from the code on branch codex/workbench-combined-2026-11-10, uncommitted tree, while other sessions were still changing WordPress files. It is a snapshot for review, not a user guide.

## How to read this

- Each H2 is one area; each H3 is one feature or command. Jump by heading.
- Under a feature, bullets say how to reach it, what opens, what each choice does, the exact preview or confirmation wording, what is announced after, what Ctrl+Z does, the F1 help, what Cancel does, what a role without permission hears, and, for a command with no key, its written reason. A bullet is left out when it does not apply; "not found in code" means it was looked for and is not there.
- Quoted text is what the code says, with placeholders in braces, such as {site} or {title}.
- "Review notes" under a feature are the UX concerns: oddities, inconsistencies, dead ends and awkward wording. They are collected again, ranked, in the last H2, "Review notes, all in one place".
- Keystroke paths spell the access letters: "Alt+F, W, O" means File, then WordPress, then Open Page or Post. Where a submenu has no access letter, the path says to arrow to it.
- "WordPress key, then O" means press Ctrl+Alt+Shift+Grave (Grave is the key left of 1), let go, then press O.
- The Workbench's context menu opens with the Applications key or Shift+F10 on a row. Its first row is what Enter does, Properties is last, and past eight rows the rest go under More.
- Everything was read from code, not run against a live site or with a screen reader. Where a finding was inferred rather than certain, the text says so ("verify", "plausible", "not verified").
- "Code:" bullets name the module files, for follow-up.

## Keys at a glance

### In both editors: the WordPress keys

Press Ctrl+Alt+Shift+Grave, then one letter, within four seconds. QUILL says "WordPress keys" when the layer starts, "Left WordPress keys" on Escape, and "No WordPress command on X." for a letter with nothing on it. The letters are the same in QUILL and QUILL Lite (quill/core/wordpress/menu.py LAYER_KEYS; quill/core/forms/menu.py for F).

- A - Connect a Site...
- B - WordPress Blocks... (View)
- C - Compare with Site
- D - Save Draft to Site
- E - Schedule Publish...
- F - Responses... (Forms)
- G - New Page...
- H - Open WordPress Workbench...
- Shift+H - This Post in the Workbench
- I - Open on Site
- K - Check Before Publishing...
- L - Open Local Draft...
- M - Media Library...
- N - New Post...
- O - Open Page or Post...
- P - Publish or Update...
- R - Properties...
- S - Switch Site...
- Shift+S - Sites...
- T - Move to Trash...
- U - Upload Files...
- V - Previous Versions...
- W - Open by Web Address...
- X - Alt Text Review...
- Y - Copy Address
- J, Q, Z and the digits have no command.

### In the editors: the menus

- File > WordPress: Alt+F, W.
- Insert, Format, View and Edit take WordPress rows at their ends (Format and Edit inside a WordPress submenu).
- Tools > WordPress: Alt+T, then arrow to WordPress (the submenu has no access letter in either editor).
- Tools > Forms holds the Forms commands (see "Forms (QAF)").

### In the WordPress Workbench window

These are the window's own keys (quill/core/wordpress/workbench_window_menu.py). They act only in the Workbench, never in the editor.

Moving around:

- F6 and Shift+F6 - next and previous pane (tree, filter, list, details, status bar)
- Alt+Left, Alt+Right - Back, Forward (Backspace is Back too)
- Alt+Up - Parent Node
- Ctrl+9 - Start Here
- Ctrl+1 - Needs My Attention
- Ctrl+2 - Current Site
- Ctrl+3 - Calendar
- Ctrl+5 - Watches
- Ctrl+6 - Practice Site
- Ctrl+0 - Across Sites
- Ctrl+Shift+1 to Ctrl+Shift+9 - Posts, Pages, Media, Comments, Users, Plugins, Appearance, Settings, Site Health
- Alt+1 - Where Am I; Alt+2 - Say Selection

The list and its view:

- Ctrl+E - Filter; Ctrl+Shift+F - Filter Builder; Ctrl+Alt+O - Show Only Like This; Ctrl+Alt+H - Hide Like This; Ctrl+Alt+M - Only Mine
- F5 - Refresh; Ctrl+Shift+L - Load More; Ctrl+Alt+L - Load All; Ctrl+Alt+C - Columns; Ctrl+Alt+G - Group By
- Ctrl+Shift+X - Export List; Ctrl+Shift+I - Import Posts from a Spreadsheet; Ctrl+Alt+Shift+I - Import a Folder of Documents

The selected row:

- Enter - its default action; Alt+Enter - Properties; Shift+Enter - Open on the Site; Ctrl+Enter - Preview on the Site; Ctrl+Shift+C - Copy Link
- Ctrl+N - New Here
- Ctrl+Shift+P - Publish or Update
- Ctrl+Shift+A - Approve, or Not Spam; Ctrl+Shift+U - Unapprove; Ctrl+Shift+S - Spam; Ctrl+Shift+M - Reply; Ctrl+Alt+W - Not Spam, and Allow This Sender
- Ctrl+Shift+G - Merge Into; Ctrl+Shift+K - Convert to Category or Tag
- Ctrl+Shift+D - Approve and Schedule; Ctrl+Shift+B - Send Back with a Note; Ctrl+Shift+J - Assign a Reviewer; Ctrl+Alt+Shift+D - Move to Another Day
- Ctrl+Shift+Y - Copy to Site; Ctrl+Shift+W - Send Password Reset; Ctrl+Alt+Shift+M - Show Its Comments
- Ctrl+Alt+N - Entry Notes; Ctrl+Alt+F - Star or Unstar Entry; Ctrl+Alt+U - Mark Entry Read or Unread; Ctrl+Alt+I - Resend Notifications (Gravity Forms entries)
- Delete - Move to Trash; Ctrl+Shift+R - Restore from Trash; Shift+Delete - Delete Permanently
- Ctrl+Z - Undo WordPress Change; Ctrl+Shift+H - Change History (Delete, Shift+Delete and Ctrl+Z act only in the list)

The site and the window:

- Alt+Shift+Enter - Site Properties; Shift+F1 - What Can I Do Here?; Ctrl+Alt+V - View As Role; Ctrl+Alt+A - Workbench Access; Ctrl+Alt+R - Roles and What They May Do
- Ctrl+Alt+E - Empty Spam; Ctrl+Alt+Shift+E - Empty Comment Trash; Ctrl+Alt+Shift+C - Comment Counts; Ctrl+Alt+Shift+P - Your Profile
- Ctrl+Alt+K - Compare Sites; Ctrl+Alt+T - Site Sets; Ctrl+Alt+Y - Across Sites Scope; Ctrl+Alt+S - Take a Snapshot; Ctrl+Alt+Shift+S - Put Back from a Snapshot; Ctrl+Alt+D - Read Site as Document
- Ctrl+Shift+O - Workbench Options; Ctrl+Shift+T - REST Console; Ctrl+Alt+Q - Run a Saved Request; Ctrl+Alt+Shift+F - Forget a Saved Request; Ctrl+Alt+B - Plain-Language Batch; Ctrl+Alt+P - Practice Site
- Ctrl+Shift+E - Switch to Editor; Alt+F4 - Close Workbench; F1 - Help for This View

Review notes:

- Three of these chords are reported not to fire as listed, because the window's key hook runs first: Ctrl+Shift+F and Ctrl+Alt+Shift+F move to the filter box, and Ctrl+Alt+R refreshes (see "The WordPress Workbench window").
- Several layer letters differ from the menu access letter of the same row (Check Before Publishing is P in the menu, K on the layer; Media Library is B in the menu, M on the layer), so the menu does not always teach the key.

## Getting connected

Everything WordPress in QUILL hangs off one feature switch, "core.wordpress", and a list of connected sites kept in "wordpress-sites.json" in QUILL's data folder (names, addresses, usernames, roles and WordPress versions only; each site's application password is kept in Windows Credential Manager, keyed by the site's id). A site is connected with an application password, typed by hand or fetched through the browser. One site in the list is the "default site", which is only where New and Open start; a document carries its own site for life. Switch Site changes the default, the Sites window manages the list, and Sign Out This Site (in Tools > WordPress > Manage) revokes and forgets a connection. Nearly every command that needs a site and finds none says "Connect a WordPress site first." and opens the Connect dialog. On first load, any WordPress connections saved by the older publishing framework are imported once.

### The WordPress feature switch

- What it is: the feature id "core.wordpress", named "WordPress" in the feature catalogue. Description in code: "Write, open, edit and publish WordPress pages and posts on as many sites as you like, self-hosted or WordPress.com, and manage their Media Library, comments, categories and tags, from File > WordPress. Nothing reaches a site without Save Draft to Site or Publish. Replaces the older Publishing features. On by default in every profile except Essential."
- How to reach it: Tools > Customize and Support > Profiles and Features... ("Alt+T, U, P"). The Essential profile sets it to off; every other profile leaves it on.
- When off: File > WordPress, and the WordPress rows in Insert, Format, View, Edit and Tools, are not built at all; the commands are not registered, so they are not in the Command Palette either (rows are registered as they are appended to the menu); the WordPress key prefix is ignored (the char hook checks the feature before starting the layer), so Ctrl+Alt+Shift+Grave passes through to the editor.
- Every command id starting "wordpress." maps to this feature (features.py feature_for_command).
- Code: features.py, feature_catalog.py, main_frame_wordpress.py.
- Review notes:
  - The catalogue description promises WordPress.com, but WordPress.com sign-in is not available in this build (see Connect a Site). The description is the first thing a person reads when deciding to turn the feature on.
  - The description says "from File > WordPress", but since the 2026-11 placement most commands live in Insert, Format, View, Edit and Tools. A person told to look in File will not find Media Library, Comments or Check Before Publishing there.

### Connect a Site

- How to reach it: File > WordPress > Connect a Site... ("Alt+F, W, A"). WordPress key, then A (Ctrl+Alt+Shift+Grave, then A). Also from the Sites window's Add... button, from any site command when no site is connected, and from Open by Web Address when the address is not on a connected site. Not document-only.
- What opens: a dialog titled "Connect a WordPress Site" (resizable). Controls in tab order:
  - "&Problem:" read-only multi-line field, present only when re-shown after a failure; holds the reason.
  - "&Kind of site:" choice: "My own WordPress site (self-hosted)" (default) or "A WordPress.com site". Choosing WordPress.com disables the Username and Application password fields.
  - "Site &address:" edit field.
  - "&Username:" edit field.
  - "Application &password:" password field.
  - "&Name for this site (optional):" edit field.
  - "Get Password with My &Browser" button.
  - "Connect" (default button, the OK button) and "Cancel". Neither carries an access key, on purpose (GATE-14).
- Connect with an empty Site address on a self-hosted site: focus goes back to Site address and the computer beeps (wx.Bell). Nothing is spoken.
- Get Password with My Browser with an empty Site address: the same beep and focus move.
- The address is tidied before use: spaces and a trailing slash removed, and "https://" added when there is no scheme. An "http://" address is kept as typed and then refused at the first request with: "QUILL only connects to WordPress sites over HTTPS, so your password is never sent in the clear. Check that the address starts with https://." (the one exception is the local Practice Site address).
- The manual route (Connect pressed): if Username or Application password is empty the dialog comes back with the Problem field reading "Enter the username and the application password, or press Get Password with My Browser." Otherwise QUILL reads the account and the site's own name in the background ("WordPress: connecting"), and only then saves. The site's name is, in order, what you typed in Name, the site's own title, the existing entry's name, or the address. Reconnecting with the same address and username updates the existing entry (same id) rather than adding a second one.
- The browser route (Get Password with My Browser): QUILL first reads the site's REST index in the background ("reading the site").
  - If the site has no Authorize Application address, the dialog comes back with: "This site has application passwords turned off, so QUILL cannot ask for one. Ask the site's administrator to turn them on, or make one in your WordPress profile if you can."
  - Tier 1, WordPress 7.0 or later (an assumption in signin.py, marked "Not yet confirmed"): QUILL listens once on 127.0.0.1 for up to 300 seconds, opens the site's Authorize Application page in the browser, and says "Approve QUILL in your browser. QUILL is waiting for <site name>." (or "the site" when it has no name). The browser tab, after approval or refusal, shows a small page headed "You're signed in" or "QUILL was not connected", with "You can close this tab and go back to QUILL."
  - Tier 2, older sites: QUILL opens the Authorize Application page and immediately shows "Paste the Application Password", with one field "Application &password:" (password style) and "Connect"/"Cancel". If the clipboard already holds something shaped like an application password (24 letters and digits, run together or in six groups of four), it is put in the field. If the username was left empty, a second dialog "Your WordPress Username" asks "&Username:". Then the manual route's verify-and-save runs.
- Announced after:
  - Success: "Connected to <site name> as <role>."
  - Manual-route failure: the dialog reopens with the failure in the Problem field (for example "<site> did not accept the sign-in. Check the username and application password, then reconnect.").
  - Browser tier 1, refused in the browser: "You chose not to connect QUILL. Nothing was saved."
  - Browser tier 1, nothing came back in 300 seconds: "QUILL stopped waiting for the browser. Try again when you are ready."
  - WordPress.com chosen: "WordPress.com sign-in is not available in this build yet. If your WordPress.com plan allows plugins, connect with an application password at your site's own address instead." The dialog has already closed.
  - Failure reading the site on the browser route: the failure sentence is spoken (the dialog does not reopen).
- F1: dialog: "Connect QUILL to a WordPress site so you can write, open and publish its pages and posts. You can connect as many sites as you like." Kind: "Self-hosted means the site runs on its own web address and hosting. Choose WordPress.com for a site hosted by WordPress.com; you will sign in with your browser." Site address: "The site's web address, for example https://example.org. QUILL only connects over HTTPS, so your password is never sent in the clear." Username: "The username or email you sign in to WordPress with." Application password: "An application password: a separate password WordPress makes for one app. It is not the password you sign in to the site with. Press Get Password with My Browser and QUILL fetches one for you; or make one in your WordPress profile and paste it here." Name: "What QUILL calls this site in lists and confirmations. Leave it empty to use the site's own title." Browser button: "Opens the site's own Authorize Application page in your browser. Approve QUILL there and the password comes back to QUILL by itself; on an older site, WordPress shows it to you to copy and paste here. For WordPress.com this is how you sign in." Problem: "Why the last attempt to connect did not work, and what to try." Paste dialog: "WordPress is showing a new application password in your browser. Copy it there, come back, and paste it here."; its field: "Paste the application password WordPress showed you. It is 24 letters and numbers, often in groups of four." Username dialog: "The username you approved QUILL with in the browser."
- Cancel: closes silently; nothing saved. Cancel on the Paste dialog also silent. Cancel on the Username dialog leaves the username empty, which reopens Connect with the "Enter the username and the application password" problem.
- Keyless: has a key (A).
- Code: wordpress_connect.py (ConnectFlow), wordpress_dialogs.py (ConnectSiteDialog, PastePasswordDialog), signin.py, signin_loopback.py, signin_base.py, sites.py, api.py.
- Review notes:
  - When the dialog comes back after a failure, the password field is always empty: ConnectSiteDialog never fills it from the previous answer. Any failure (a typo in the address, a slow host, a 500) means retyping or re-fetching the application password. On the browser route this is worse: the fetched password is thrown away and a new one must be minted, leaving an orphan password on the site each time.
  - Tier 2 reads the clipboard the instant the browser opens, before WordPress has even shown the password, so the "offer" is whatever was on the clipboard before. The module docstring says it offers the value "when focus comes back"; the code does not.
  - Tier 2 asks for a username when it is empty and, if cancelled, reopens Connect with an empty password field, so the pasted password is lost.
  - The Problem field's "&Problem:" and the password field's "Application &password:" both claim P whenever the error is shown, so Alt+P cycles between them instead of pressing (a GATE-14 duplicate that only exists on the retry, which is when a person is most likely to need it).
  - WordPress.com is offered as a choice, its help says "you will sign in with your browser", and the browser button's help says "For WordPress.com this is how you sign in"; the result is a dead end sentence after the dialog has already closed. Either hide the choice or keep the dialog open with the explanation in the Problem field.
  - "Approve QUILL in your browser..." is spoken at the moment the browser takes focus, so the screen reader is likely to talk over it. There is no way to cancel the 300-second wait from QUILL, and a listener failure is swallowed silently (the failure callback only cancels the listener).
  - The browser's done page says "You're signed in" before QUILL has verified anything; if verification then fails, the browser and QUILL disagree.
  - A failure on the browser route speaks a sentence and drops you back in the editor, while the same failure on the manual route reopens the dialog with a Problem field. Two behaviours for one dialog.
  - A malformed or state-mismatched reply from WordPress raises inside the success callback; no code here turns that into a spoken sentence (not found in code).
  - Connect and Get Password both beep with no words when the address is empty. A beep is not an explanation; a sentence in the Problem field, or speaking "Type the site's address first", would be.
  - "then reconnect" in the 401 sentence names an action with no command of that name; the way to replace a password is to run Connect a Site again with the same address and username, which nothing tells you.

### Sites

- How to reach it: File > WordPress > Sites... ("Alt+F, W, S"). WordPress key, then Shift+S. Not document-only.
- What opens: a list window titled "WordPress Sites". Controls in tab order:
  - "&Sites:" list. Each row: "<name>, <role>, <host>" (or "WordPress.com" in place of the host for a WordPress.com site), with ", default" on the default site. The first row is selected.
  - Buttons: "&Add...", "&Rename...", "&Verify", "Make &Default", "Re&move...", "&Which Password", "Close" (no access key; Escape).
  - There is no default button and no Enter action on a row.
- What each button does:
  - Add...: runs Connect a Site (above).
  - Rename...: dialog "Rename Site", field "&Name:" filled with the current name, OK/Cancel. OK with a non-blank name saves it and the list refreshes. Nothing is spoken.
  - Verify: in the background, reads the account. Announced: "<name> accepts QUILL. You are <role> there." The stored role is updated. Failure: the plain failure sentence.
  - Make Default: saves and says "<name> is now your default site."
  - Remove...: confirmation titled "Remove Site": "Remove <name> from QUILL? This forgets the connection and its password on this computer. Nothing on the site is changed, and your local drafts are kept." Buttons "Remove" and "Cancel"; Cancel is the default (NO_DEFAULT). On Remove: "<name> removed from QUILL." The application password is not revoked on the site.
  - Which Password: in the background asks the site which application password QUILL signs with. Announced: "On <site>, QUILL is using the application password named <name>, made <date>, last used <date>." or "<site> did not say which application password QUILL is using." On a site older than 5.9: "<site> cannot say which application password QUILL is using. That needs WordPress 5.9 or later." For a WordPress.com token: "QUILL signs in to <site> with a WordPress.com token, not an application password."
- F1: window: "Your connected WordPress sites. The default site is where New and Open start; every document stays with the site it came from." List: "Each site's name, your role on it, and where it is." Buttons: "Connect another WordPress site.", "Change what QUILL calls the selected site.", "Check the selected site still accepts QUILL's sign-in.", "Use the selected site for New and Open.", "Forget the selected site on this computer.", "Say which of your application passwords QUILL signs in to the selected site with. Sign Out This Site revokes exactly that one." Rename field: "What QUILL calls this site in lists and confirmations." Close: "Close this window. Escape does the same."
- With no sites: the window still opens with an empty list; every button except Add... is disabled. No sentence says the list is empty.
- Cancel: Close or Escape closes silently.
- Code: wordpress_commands.py (cmd_sites), wordpress_dialogs.py (ListWindow), wordpress_api_writing_commands.py (which_password_action), site_features.py (password_sentence).
- Review notes:
  - Add... is backwards. If you cancel the Connect dialog, the whole Sites window closes (the action returns CLOSE when the flow returns None). If you complete it, the list refreshes immediately, before the background verification has saved the new site, so the site you just added is not in the list until you close and reopen the window.
  - Verify, Which Password and Remove all go through the site client, which on first use in a session also counts waiting comments and may speak "<site>: N comments waiting." in the middle of a sign-in check (the same is true of Sign Out). Unrelated news arriving with a diagnostic.
  - Remove forgets the password locally but leaves it live on the site; Sign Out This Site (which does revoke it) lives in a different menu (Tools > WordPress > Manage). A person managing sites in this window will not find the safer action here.
  - There is no way to change the address, username or password of an existing site from this window. "Verify" can only tell you it is broken.
  - Sites and Switch Site both change the default site (Make Default, and Switch Site), with different sentences: "<name> is now your default site." versus "Default site: <name>."

### Switch Site

- How to reach it: File > WordPress > Switch Site... ("Alt+F, W, H"). WordPress key, then S. Not document-only.
- What opens: with two or more sites, a choice dialog titled "Switch Site", list "&Site:" of rows "<name>, <role>, <host>", with the default site selected; "OK" (default) and "Cancel".
- Announced after: "Default site: <name>." With one site: "<name> is your only site." With none: "Connect a WordPress site first." and the Connect dialog opens.
- F1: "Choose which of your WordPress sites to use. Your default site is selected." (the list adds " Press Enter to choose the selected one.").
- Cancel: silent.
- Code: wordpress_commands.py (cmd_switch_site, pick_site, need_site).
- Review notes:
  - "Switch Site" suggests the document in front moves to another site; it only changes where New and Open start. The help text ("Choose which of your WordPress sites to use") does not say so either.
  - It has the everyday key S while the Sites list has Shift+S, yet Switch Site is a subset of the Sites window's Make Default.
  - After "Connect a WordPress site first." the Connect dialog opens at once, so the sentence is very likely talked over by the dialog title. After connecting, the original command does not resume. This is true of every command that calls need_site.

### Sign Out This Site

- How to reach it: Tools > WordPress > Manage > Sign Out This Site... (Tools > WordPress has no access letter, so this is "Alt+T", arrow to WordPress, then "M, I"). No WordPress key. Not document-only. Listed here because it is the other half of connecting.
- What opens: with more than one site, the "Sign Out This Site" site chooser (as in Switch Site). Then a choice dialog titled "Sign Out This Site", list "&After signing out:" with "Remove <name> from QUILL" and "Keep <name> in the list, to connect again later"; "OK" (default) and "Cancel".
- Then in the background: QUILL asks which application password it signs with and revokes exactly that one on the site, then forgets it on this computer and, for the first choice, removes the site from the list.
- Announced after: "Signed out of <site>: the password <name> is revoked on the site and forgotten here, and the site is removed from QUILL." (or "kept in your list"). When the site would not say which password: "Signed out of <site>: the password is forgotten here, and the site is kept in your list. The site did not say which password QUILL used, so revoke it in Application Passwords or the dashboard if you want it gone there too."
- Failure: if the site cannot be reached, the failure sentence is spoken and nothing is forgotten locally.
- F1: "Signing out revokes QUILL's application password on <site> itself and forgets it on this computer. Your local drafts are kept either way."
- Cancel: silent at either step.
- Keyless: no chord; no written reason found (Tools rows are not in DEFAULT_KEYMAP, so the bound-command gate never sees them).
- Code: wordpress_people_commands.py (cmd_sign_out), site_features.py.
- Review notes:
  - The confirmation is a two-row list with a generic "OK" button. The action is not reversible on the site, so the button should say "Sign Out", as Remove Site's says "Remove".
  - "Keep <name> in the list, to connect again later" leaves a site in the list with no password; every later command on it will fail with the 401 sentence. Nothing marks such a site in the Sites list.
  - It lives four levels deep under Tools while Connect a Site, Sites and Switch Site are in File > WordPress.

### When no site is connected

- Commands that need a site (New Page, New Post, Open Page or Post, Switch Site, Send This Document to WordPress, Send a Folder as Drafts, Duplicate, Download My Writing, Sign Out, and others) call need_site: they say "Connect a WordPress site first." and open the Connect dialog. On cancel, nothing more is said.
- Open by Web Address says "That address is not on any of your connected sites. Connect the site first, then try again." and opens Connect with the address's scheme and host filled in.
- Document-only commands reached outside a WordPress document say one of two things. Commands that pass their name say "<command> works in a WordPress page or post. Open one with File, WordPress." Most do not, and say the generic: "This is not a WordPress document. Open one with Open Page or Post, or start one with New Page or New Post, in the WordPress menu under File."
- A WordPress document whose site has been removed: "The site this document belongs to is no longer in your list of sites. Connect it again with Connect a Site, and the document will find it."
- Review notes:
  - Which of the two "not a WordPress document" sentences you hear depends on whether the handler happened to pass its name; Save Draft, Publish, Properties, Open on Site, Copy Address, Trash, Compare, every block command and Image Size use the generic one.
  - "Connect it again with Connect a Site, and the document will find it" is only true when you reconnect with the same address and username and the old id survives; a removed site's id is gone, so the document's site id will not match a fresh connection (sites.py upsert matches by id, and a new connection after Remove gets a new id). Not verified at runtime, but nothing in the connect code looks up an orphaned document's site id.

## The editor's WordPress commands

In QUILL the WordPress commands are spread over the editor's own menus. File > WordPress ("Alt+F, W") holds what is about a whole document or a site, including a "Send and Copy" submenu. Insert, View and the Format > WordPress and Edit > WordPress submenus hold what you do inside a page. The table is quill/core/wordpress/menu.py; QUILL builds it in main_frame_wordpress.py, each row calling one shared handler on WordPressCommands. Rows in DOCUMENT_ONLY are dimmed unless a WordPress document is in front; reached another way (the WordPress keys, the Command Palette) the handler speaks why. Any row with a chord shows it in brackets at the end of its menu label, for example "Open Page or Post... (Ctrl+Alt+Shift+Grave, O)", because a two-press sequence cannot sit after the tab in a wx menu label. Every command that touches the site runs on a background task named "WordPress: <what>" and speaks its outcome in one sentence; failures speak the site's plain error sentence (for example "Your account on <site> is not allowed to do that."). No WordPress command has an alias in DEFAULT_ALIASES.

### The WordPress keys (the layer)

- How to reach it: press Ctrl+Alt+Shift+Grave (the key above Tab), release, then press one key within 4 seconds.
- Spoken: "WordPress keys" when the prefix is pressed. Escape: "Left WordPress keys". A letter with no command: "No WordPress command on X." (with X spelled as the layer saw it, modifiers included).
- The letters (LAYER_KEYS, plus the Forms key): G New Page, N New Post, O Open Page or Post, W Open by Web Address, L Open Local Draft, D Save Draft to Site, P Publish or Update, E Schedule Publish, I Open on Site, Y Copy Address, R Properties, V Previous Versions, C Compare with Site, T Move to Trash, S Switch Site, Shift+S Sites, A Connect a Site, M Media Library, B WordPress Blocks, K Check Before Publishing, U Upload Files, X Alt Text Review, H Open WordPress Workbench, Shift+H This Post in the Workbench, and F Forms Responses (from forms/menu.py).
- Rules in code: the letters are read from the live keymap, so a key moved in the Keyboard Manager moves here too. A non-character key (arrow, Tab, Enter) leaves the layer silently and goes on to the editor. A bare modifier going down (Shift on the way to Shift+S) is ignored. A key pressed after the 4 seconds is not the layer's and is typed as usual. Focus leaving or a menu opening cancels silently. If the user has put the QUILL key on Ctrl+Alt+Shift+Grave, the QUILL key wins and the WordPress layer never starts. The prefix only works while the WordPress feature is on.
- Document-only commands run from the layer even when their menu row is dimmed; the handler then speaks why.
- Code: keys.py, menu.py, main_frame_wordpress.py (_wordpress_key_event, _wordpress_prefix_matches), keymap.py (DEFAULT_KEYMAP via default_bindings).
- Review notes:
  - Any modifier still held when the letter is pressed makes a different key. Holding Ctrl+Alt+Shift through from the prefix and pressing O says "No WordPress command on Ctrl+Alt+Shift+O." Holding Shift only turns O into "Shift+O" and S into Sites instead of Switch Site. Since the prefix itself needs Shift, this will happen often; the layer could ignore modifiers held over from the prefix, or the "No WordPress command" sentence could say "release the keys first".
  - The timeout is silent. Press the prefix, think for five seconds, press P, and a "p" lands in the document with nothing said. "Left WordPress keys" on timeout, as on Escape, would cost one sentence.
  - The menus spell the chord as "(Ctrl+Alt+Shift+Grave, O)" on every row, read aloud in full on every visit to File > WordPress. The QUILL key is displayed as "QUILL Key + S"; the WordPress layer gets no friendly name ("WordPress Key + O" would be shorter and match the spoken "WordPress keys").
  - Only 24 of the about 45 editor-side commands have a letter. The per-page navigation commands (Next Block, Previous Block, Where Am I), the most frequent things a writer does in a block document, have none, and nothing records a reason (see "Keyless" below).
  - A command failure from the layer goes through _run_command, which reports exceptions with _set_status (status bar), not speech (not verified that the status bar is spoken).

### About "Keyless" for this section

- Rows with no chord in QUILL: Custom Fields, Plugin Fields, all five Send and Copy rows, all five Edit > WordPress rows, Preview Blocks, Block Notes, Play Media Here, all seven Insert rows, and all three Format > WordPress rows.
- No written reason was found for any of them. They are not in DEFAULT_KEYMAP at all (only the layer letters are), and the bound-command gate (tests/unit/core/test_family_rules_and_gates.py, "every editor command has a key or a written reason") only walks DEFAULT_KEYMAP, so it never sees them. Rule 8 ("every command has a key or a written reason") is therefore unenforced for WordPress.

### File > WordPress (the submenu itself)

- How to reach it: File > WordPress, "Alt+F, W". The access letter W is free in the File menu (File's own rows use N, O, P and others, not W).
- Within the submenu every row has a unique access letter (checked: P, N, O, W, L, D, U, E, I, Y, K, R, F, G, V, M, T, C, H, S, A).
- Review notes:
  - The submenu has 22 rows and four separators plus a submenu; with each label carrying "(Ctrl+Alt+Shift+Grave, X)", arrowing through it is long.
  - Several access letters are not the word's first letter and do not match the layer key (New Page is P in the menu and G on the layer; Publish is U in the menu and P on the layer; This Post in the Workbench is K in the menu and Shift+H on the layer; Compare is M in the menu and C on the layer; Sites is S in the menu and Shift+S on the layer, while S on the layer is Switch Site whose menu letter is H). The menu.py comment says "A row's own access letter wherever it is free, so the menu teaches the key", but for these rows the menu teaches a different key from the layer.

### New Page

- How to reach it: File > WordPress > New Page... ("Alt+F, W, P"). WordPress key, then G. Not document-only.
- What opens: dialog "New Page". Controls: "&Site:" choice (default site selected), "&Title:" field, "S&lug:" field (filled from the title as you type until you edit it), "Write in" radio box "Markdown" / "HTML" (last choice remembered for the session), then "Create" (default) and "Cancel". Pages show no categories or tags.
- Announced after: "New page for <site>. Ctrl+S keeps it on this computer; nothing is sent until you choose Save Draft to Site or Publish." The new document opens in the editor.
- F1: dialog: "Start a new page. Nothing is sent to the site until you choose Save Draft to Site or Publish." Site: "Which of your sites this belongs to. It stays with that site for good." Title: "The title. Your theme shows it at the top of the page, so the body does not need it again as a heading." Slug: "The last part of the web address. It is filled in from the title as you type; leave it to keep the suggestion." Write in: "Markdown is readable text characters for headings, lists and links; QUILL turns it into HTML when you send it. HTML is for exact control. This cannot change later."
- Cancel: silent.
- No site: "Connect a WordPress site first." and Connect opens.
- Code: wordpress_commands.py (_new), wordpress_item_dialogs.py (NewItemDialog).
- Review notes:
  - The "Write in" radio box has no access letter, and its label is not "&Write in"; every other field in the dialog has one.
  - The site is chosen inside the dialog, but for posts categories and tags are loaded from the default site before the dialog opens; choosing another site silently drops any categories and tags checked (the code sets them only when the chosen site is the default). Not an issue for pages, but the same dialog is used.

### New Post

- How to reach it: File > WordPress > New Post... ("Alt+F, W, N"). WordPress key, then N. Not document-only.
- What opens: first a background read of the default site's categories and tags ("loading categories and tags"), then dialog "New Post", the same as New Page plus two check-box groups, "Categories" and "Tags", when the site has any.
- Announced after: "New post for <site>. Ctrl+S keeps it on this computer; nothing is sent until you choose Save Draft to Site or Publish."
- F1: as New Page ("Start a new post..."); category group: "Check each category this post belongs to. Space checks or unchecks."; tag group: "Check each tag for this post. Space checks or unchecks."
- Failure: if the site cannot be reached for its categories, the failure sentence is spoken and no dialog opens, so you cannot start a post offline.
- Code: wordpress_commands.py, wordpress_item_dialogs.py.
- Review notes:
  - Categories and tags are lost without a word if you change the Site choice away from the default (see New Page).
  - Starting a post needs the network; starting a page does not. A writer offline cannot start a post at all, and the sentence they hear is a connection error, not "QUILL needs the site to list categories".
  - A site with hundreds of tags puts hundreds of check boxes in a scrolled group with no filter.

### Open Page or Post

- How to reach it: File > WordPress > Open Page or Post... ("Alt+F, W, O"). WordPress key, then O. Not document-only.
- What opens, in order:
  - With several sites, the "Open Page or Post" site chooser.
  - Background "reading what <site> holds", then a choice "Open Page or Post", list "&Show:" with "Posts", "Pages" and any other content types the site lists.
  - Background "listing <kind> on <site>", then a list window "Open from <site>": "&Find by title or status:" field (Enter filters), "&Posts:" / "&Pages:" / "&Items:" list (rows "<title>, <status>, last changed <date>", every status including Trash), buttons "&Open", "Move to &Trash...", "&Restore from Trash", "Close". Enter or double-click on a row opens it.
  - If you already have a working copy of that item, it opens straight away.
  - Otherwise, background load, then a check for a newer autosave: if there is one, choice "Unsaved Version", prompt "There is an unsaved version from <when>. Open that &instead?", rows "Yes, open the unsaved version from <when>" and "No, open the copy on the site".
  - Then choice "Open <title>", prompt "Open &as:", rows "HTML, exactly as the site has it" (selected) and "Markdown, easier to read; anything Markdown cannot show is kept exactly".
- Announced after: "Opened <title> from <site>." For an existing working copy: "Opened your working copy of <title>. Compare with Site shows what changed on the site since." Empty list: "<site> has no <kind>s yet."
- Move to Trash and Restore from Trash in this window: as Move to Trash below; restore says "'<title>' is back on <site> as a draft. Open it to publish it again." or "'<title>' is not in the Trash."
- F1: Show: "Posts are dated articles in the blog or news. Pages are lasting pages like About or Contact. Any other kinds are the site's own, such as events." Window: "Every <kind> on <site>, newest change first. Enter opens the selected one." List: "Each row says the title, its status, and when it last changed." Filter: "Type part of a title, or a status such as draft or trash, and press Enter." Open as: "HTML keeps every block exactly. Markdown shows ordinary text plainly and puts other blocks on short ::: lines; nothing is lost either way." Unsaved version: "An autosave newer than the copy on the site was found, from a browser or from QUILL. Whichever you open, the other stays on the site."
- Cancel: silent at every step.
- Code: wordpress_open_commands.py, wordpress_page_commands.py (offer_newer_autosave, restore_listed), wordpress_dialogs.py.
- Review notes:
  - Four to five dialogs to open one post (site, kind, list, autosave, format). The format question comes every time and always starts on HTML; New remembers the last format, Open does not.
  - The status filter only matches the raw status: rows say "Published" but typing "published" finds nothing; you must type "publish". "Pending review" rows need "pending", "Scheduled" needs "future".
  - Trash and Restore from this window do not refresh the list; the row still says its old status until you close and reopen.
  - Opening an item you already have a working copy of opens the local copy without checking the site, so you may edit a stale copy; the sentence tells you to run Compare yourself.
  - Trashed items are mixed in with live ones in the default list.
  - "<site> has no <kind>s yet." builds the plural by adding "s" to the type slug, so a custom type such as "tribe_events" is read as "tribe_eventss".
  - "Opened <title> from <site>." follows a document opening, whose new window title the reader announces anyway; the site name is the only new information.

### Open by Web Address

- How to reach it: File > WordPress > Open by Web Address... ("Alt+F, W, W"). WordPress key, then W. Not document-only.
- What opens: if the clipboard holds anything starting "http://" or "https://", nothing opens; that address is used at once. Otherwise a dialog "Open by Web Address", field "Web &address:", OK/Cancel.
- Then the address is matched to a connected site by host (ignoring "www."), and found by "?p=", "?page_id=", "?post=", its slug, or a custom type's slug; then it opens as in Open Page or Post (autosave offer, then Open as).
- Announced after: as Open Page or Post. Not on any site: "That address is not on any of your connected sites. Connect the site first, then try again." and the Connect dialog opens with that site's address. Not found: "QUILL could not find a page or post at that address on <site>. It may be an archive or a category page, which are not single items."
- F1: "Paste or type the address of any page or post on one of your sites."
- Cancel: silent.
- Code: wordpress_open_commands.py (cmd_open_by_address, find_by_address).
- Review notes:
  - Using the clipboard without asking is a trap: any web address copied for another reason is used silently, and if it is not on a connected site you are dropped into the Connect dialog for a stranger's site. At minimum the dialog should open with the clipboard address filled in, so the person can see and change it.
  - Nothing is spoken when the clipboard is used, so the person does not know which address QUILL took.

### Open Local Draft

- How to reach it: File > WordPress > Open Local Draft... ("Alt+F, W, L"). WordPress key, then L. Not document-only.
- What opens: choice "Open Local Draft", list "&Drafts:" with rows "<title or (untitled)>, <kind>, <site name or 'a site no longer connected'>, saved <date>", OK/Cancel.
- Announced after: nothing; the document opens. No drafts: "You have no local WordPress drafts yet."
- F1: "Your WordPress working copies on this computer, newest first."
- Cancel: silent.
- Code: wordpress_open_commands.py.
- Review notes:
  - Silent on success, while Open Page or Post says "Opened <title> from <site>." Inconsistent, though the silent one is the GATE-13-friendlier of the two.
  - "Drafts" here means every working copy, including copies of published posts; the name suggests only unsent drafts.
  - No filter on a list that will grow to every item ever opened.

### Save Draft to Site

- How to reach it: File > WordPress > Save Draft to Site ("Alt+F, W, D"). WordPress key, then D. Document-only.
- What happens: QUILL saves the file first (if that fails, it stops silently), then sends in the background ("WordPress: sending to <site>"). On a published item, a choice first: title "Save Draft to Site", prompt "This <page or post> is published. Save as a draft and take it off the site, or update the published <page or post>? &Choose:", rows "Update the published <kind>" (selected) and "Save as a draft and take it off the site".
- If Markdown lines could not become blocks: "<N> lines could not be turned into blocks; Check Before Publishing lists them." (the send continues).
- Conflict (the site changed since you opened it): "The copy on <site> was changed on <when>, after you opened it. Nothing was sent." then choice "The Site Copy Changed", "&What now:", rows "Compare the two", "Open the site's copy", "Send mine anyway". Send mine anyway confirms: "Replace the newer copy on <site> with yours? The site's copy is kept in Previous Versions." buttons "Send Mine"/"Cancel".
- Announced after: "Draft saved to <site>. It is not public." For a pending item: "Submitted for review on <site>." Network failure: QUILL re-reads the site; if nothing landed, a confirm "Not Sent": "'<title>' did not reach <site>. QUILL checked the site and nothing was changed there. Your copy is kept on this computer. Try again now?" buttons "Try Again"/"Cancel"; if the site is still unreachable: "<site> cannot be reached, so '<title>' is queued. QUILL sends it when the site answers again; your copy is kept on this computer."
- Outside a WordPress document: the generic "This is not a WordPress document..." sentence.
- Without permission: the site's sentence, for example "Your account on <site> is not allowed to change this item." or "Your account on <site> can only change items you wrote yourself."
- Undo: nothing on the site to undo; Previous Versions keeps the site's copy from before each update.
- F1: conflict list: "Someone changed the copy on the site after you opened yours. Nothing was sent." Save Draft choice: the question plus "Update keeps it on the site with your changes; a draft is only seen by people who can edit it."
- Code: wordpress_more_commands.py (_send, send_work, _conflict, _sent), wordpress_offline_commands.py.
- Review notes:
  - Choosing "Update the published <kind>" from Save Draft updates the live page with no further confirmation, while Publish or Update asks "Update '<title>' on <site>?". Save Draft is the command people press when they think it is safe.
  - The conflict sentence is announced immediately before the conflict dialog opens, so the dialog title is likely to cut it off; the dialog's own prompt does not repeat what happened.
  - "Open the site's copy" discards your working copy (it is kept in Previous Versions) without a confirmation.
  - The "lines could not be turned into blocks" sentence is spoken and then the send carries on; for Publish it is spoken just before the confirmation dialog, where it will be lost.

### Publish or Update

- How to reach it: File > WordPress > Publish or Update... ("Alt+F, W, U"). WordPress key, then P. Document-only.
- What opens: after saving the file and running Check Before Publishing's checks, a confirmation titled "Publish on <site>" (or "Update on <site>" for a published item): "Publish '<title>' on <site>?" followed by a blank line and the summary ("Ready to publish: no problems found", or "<N> things to look at: <n> problems, <m> to check") and up to eight findings as "- <message>" lines. Buttons "Publish" (or "Update", or "Publish Anyway" / "Update Anyway" when there are findings) and "Cancel"; Cancel is the default.
- Then the send, with the same conflict, failure and queue handling as Save Draft.
- Announced after: "Published on <site>. The address is on the clipboard." The published address replaces whatever was on the clipboard. For a contributor: "Submitted for review on <site>." A Private or Scheduled item keeps its status. After a page's first publish, unless turned off for the site, a choice "Add to a Menu", "&Add it to a menu?", rows "Yes, open Menus", "Not this time", "No, and stop asking for <site>"; the last says "QUILL will not ask again for <site>. Menus is in File, WordPress, Running the Site."
- Cancel: silent; nothing sent.
- Without permission: a contributor is shown "Publish '<title>' on <site>?" and the item is quietly sent as pending; see notes.
- F1: Add to a Menu: "Publishing a new page does not put it in the site's menus, so visitors may not find it. Menus is also in File, WordPress, Running the Site."
- Code: wordpress_more_commands.py (_confirm_publish, target_status), wordpress_page_commands.py (after_sent, offer_menu), checks.py.
- Review notes:
  - For a contributor the confirmation says "Publish" and the button says "Publish", but the item is submitted for review (target_status turns publish into pending). The question should say "Submit '<title>' for review on <site>?" when the account cannot publish.
  - Putting the address on the clipboard silently overwrites what the person had copied. Either ask, or say "The address replaced what was on the clipboard."
  - Two sentences in the Add to a Menu flow send people to "File, WordPress, Running the Site", a place that no longer exists; Menus is now Tools > WordPress > Menus.
  - With Cancel as the default, Enter in the confirmation cancels. Safe, but the labels passed to SetYesNoLabels ("Publish", "Update", "Publish Anyway") carry no "&", so the publish button has no access key; the route is Tab to it, then Space. Worth checking with a reader.

### Schedule Publish

- How to reach it: File > WordPress > Schedule Publish... ("Alt+F, W, E"). WordPress key, then E. Document-only.
- What opens: after saving the file, for an item already scheduled, a choice "Scheduled on <site>", "&What now:", rows "Change the schedule" and "Publish now". Otherwise (or after Change), a background read of the site's time zone, then dialog "Schedule Publish": optional "&Problem:", "&Date (year-month-day):" (tomorrow), "&Time:" ("09:00"), "Time &zone:" (site's zone first), "Schedule" (default) and "Cancel". A date QUILL cannot read brings the dialog back with the reason in Problem. Then a confirmation "Schedule on <site>": "Schedule '<title>' to publish on <site> on <spoken moment>, <zone>?" buttons "Schedule"/"Cancel".
- Publish now confirms with "Publish Now on <site>": "Publish '<title>' on <site> now, instead of at its scheduled time?" button "Publish Now".
- Announced after: "Scheduled on <site> for <spoken moment>, <zone>." Publish now: as Publish ("Published on <site>. The address is on the clipboard."). Conflict: "<conflict sentence> Use Compare with Site, then schedule again."
- Without permission: "Your role on <site>, <role>, cannot publish, so it cannot schedule either. Choose Publish or Update to submit it for review instead."
- F1: dialog: "Choose when '<title>' publishes on <site>. Nothing is sent until you confirm." Date: "The day to publish, as year, month and day with hyphens, for example 2026-11-20." Time: "The time to publish, in 24-hour hours and minutes such as 16:15, or like 4:15 PM." Zone: "The time zone the date and time are in. The site's own time zone is first when the site says what it is; type a letter to jump to a city." Problem: "Why the last date and time could not be used, and what to type." Scheduled choice: "'<title>' is scheduled to publish on <site> for <when>. Change the schedule picks a new time; Publish now makes it public straight away."
- Cancel: silent at each step.
- Code: wordpress_page_commands.py, wordpress_schedule_dialog.py, schedule.py.
- Review notes:
  - The role check happens only at the very end, after the person has typed a date and confirmed twice; a contributor should hear the refusal before the dialog opens (the account is already read for the time zone call's site).
  - Two confirmations in a row: the dialog's own "Schedule" button, then a "Schedule" message box. The second adds the spoken moment, which is useful, but it could be the dialog's purpose text instead.
  - The date is a typed field with a format in its label; there is no date picker (deliberate for screen readers, but the label "(year-month-day)" is long to hear on every Tab).

### Open on Site

- How to reach it: File > WordPress > Open on Site ("Alt+F, W, I"). WordPress key, then I. Document-only.
- What happens: opens the item's address in the default browser.
- Announced after: nothing on success. Not sent yet: "This is not on <site> yet. Save Draft to Site or Publish first." Outside a WordPress document: the generic sentence.
- Code: wordpress_commands.py (cmd_open_on_site).
- Review notes:
  - For a draft, the browser opens an address that needs a WordPress sign-in; Copy Address warns about this ("It needs a WordPress sign-in to open."), Open on Site does not.

### Copy Address

- How to reach it: File > WordPress > Copy Address ("Alt+F, W, Y"). WordPress key, then Y. Document-only.
- Announced after: "Address copied." for a published item; "Draft address copied. It needs a WordPress sign-in to open." otherwise. Not sent yet: "This is not on <site> yet, so it has no address."
- Code: wordpress_commands.py (cmd_copy_address).
- Review notes: none beyond the generic "not a WordPress document" sentence.

### This Post in the Workbench

- How to reach it: File > WordPress > This Post in the Workbench ("Alt+F, W, K"). WordPress key, then Shift+H. Document-only.
- What opens: the WordPress Workbench window, on this post's or page's list, with it selected (the Workbench itself is covered elsewhere).
- Announced: not sent yet: "<title> is not on <site> yet, so the Workbench has no post to show. Save Draft to Site sends it first." Site unknown to the Workbench: "<site> is not among the Workbench's sites." Outside a WordPress document: "This Post in the Workbench works in a WordPress page or post. Open one with File, WordPress."
- Code: wordpress_commands.py, wordpress_workbench_editor_side.py (open_on_document).
- Review notes:
  - When the site is not among the Workbench's sites, the Workbench window has already been opened before the sentence is spoken, so the person lands in a window that does not show what they asked for.
  - Menu letter K, layer key Shift+H: two different things to learn for one command.

### Properties

- How to reach it: File > WordPress > Properties... ("Alt+F, W, R"). WordPress key, then R. Document-only.
- What opens: for a post, first a background load of categories and tags (and of any plugin facts). Then the "WordPress Properties" sheet, the same item sheet the Workbench shows: a notebook of pages (the item sheet's pages limited to title, status, password, slug, excerpt, categories, tags, comment status, sticky, format, parent, template and featured image), plus a last "About" page with a read-only multi-line field of facts ("Site: ..., Kind: ..., Status: ..., Address: ..., Last changed on the site: ..." and a reading-level line). Buttons: "Copy as &Text", "OK", "&Apply", "Cancel". Ctrl+Tab moves between pages.
- What each choice does: OK and Apply keep changes with the working copy only; they go to the site with the next Save Draft to Site or Publish. Apply keeps the sheet open.
- Announced after: "Kept with your copy: <n> categories, <m> tags. They go to the site when you next send." plus " Not on the site, so left out: <names>." for unknown terms. Then, if the site registers custom fields, the Custom Fields dialog follows on its own (quietly, if there are none).
- Cancel: with nothing applied, silent. Cancel after Apply is treated as keeping what was applied.
- F1: sheet: "Everything about this page or post apart from its text, on the same sheet the WordPress Workbench shows. Changes are kept with your working copy and go to the site with your next Save Draft to Site or Publish." Notebook: "The sheet's pages. Ctrl+Tab moves to the next page." About: "Which site this belongs to, its address and when it last changed."
- Code: wordpress_more_commands.py (cmd_properties), wordpress_item_dialogs.py (ask_properties), workbench_copy_sheet.py, workbench_sheet_editor.py.
- Review notes:
  - The outcome sentence always counts categories and tags, so a page says "Kept with your copy: 0 categories, 0 tags." Pages have neither. It also speaks when nothing changed but Apply was pressed.
  - The facts a person most often wants (status, address) are on the last page of the notebook, not the first.
  - A second dialog (Custom Fields) can open straight after OK with no warning; a listener may think Properties reopened.
  - Opening Properties on a post needs the network (categories and tags); offline it fails with a connection sentence and the sheet does not open.

### Custom Fields

- How to reach it: File > WordPress > Custom Fields... ("Alt+F, W, F"). No WordPress key. Document-only.
- What opens: background "reading <site>'s custom fields" (only where the site offers them to this account), then a form dialog "Custom Fields" with one labelled field per registered meta field, "OK"/"Cancel". Lists and groups that QUILL cannot show as fields come next, one at a time.
- Announced after: "<n> custom field(s) kept with your copy. They go to <site> when you next send." or "No custom fields changed." None registered: "<site> has no custom fields for a <kind>." A number field with text: "<label> needs a number. Nothing was kept; try again."
- Without permission: "Your account on <site> is <a role>, which cannot change custom fields."
- Outside a WordPress document: "Custom Fields works in a WordPress page or post. Open one with File, WordPress."
- F1: dialog purpose: "The fields <site> adds to a <kind>, from its plugins and theme, such as an SEO title or an event date. ... Changes go to the site with your next Save Draft to Site or Publish."
- Cancel: silent.
- Keyless: no chord; no written reason found.
- Code: wordpress_api_writing_commands.py, wordpress_custom_field_lists.py, custom_fields.py, wordpress_block_dialogs.py.
- Review notes:
  - A non-number in a number field closes the dialog and discards every other field typed ("Nothing was kept; try again."). It should reopen with the values kept and the problem named.

### Plugin Fields

- How to reach it: File > WordPress > Plugin Fields... ("Alt+F, W, G"). No WordPress key. Document-only.
- What opens: background "reading what <site>'s plugins add", then dialog "Plugin Fields, <title>" with whatever applies: "&Starts:", "&Ends:", "&Venue:" (events), "&Regular price:", "S&ale price:", "Stoc&k:" (products), "SEO &title:", "SEO &description:" (SEO plugins). OK button "Save to Site", and Cancel.
- What happens: Save to Site sends at once (no next-send wait). A changed price asks first: "Change Price": "Change the price of <product> on <site>? Customers see it at once. Regular price <x>, sale price <y>." button "Change Price".
- Announced after: "Saved to <site>: the event's dates and venue, the price and stock, the SEO fields." (whichever apply). Not sent yet: "This is not on <site> yet. Save Draft to Site first; then its plugin fields can be filled in." Nothing to edit: "<site>'s plugins add no fields to this <kind>." Bad dates: "The event ends before it starts. Nothing was saved." or the parse error plus " Nothing was saved."
- Outside a WordPress document: "Plugin Fields works in a WordPress page or post. Open one with File, WordPress."
- Cancel: silent.
- Keyless: no chord; no written reason found.
- Code: wordpress_plugin_commands.py, wordpress_plugin_dialogs.py.
- Review notes:
  - Custom Fields and Properties keep changes until the next send; Plugin Fields, one row below, sends immediately. Same menu, same kind of data, opposite rule; the OK label "Save to Site" is the only hint.
  - Event dates and venue are always re-sent and always reported as saved, even when unchanged.
  - A bad date closes the dialog and loses everything typed.

### Previous Versions

- How to reach it: File > WordPress > Previous Versions... ("Alt+F, W, V"). WordPress key, then V. Document-only.
- What opens: background "reading the site's history", then a list window "Previous Versions": "&Versions:" list (QUILL's own kept versions as "<when>, <title>, <reason>", then the site's revisions as "<date>, <title>, On the site" or "Autosave on the site"), buttons "&View...", "&Restore", "Close".
- View... opens a read-only report "Version" with the title and text, buttons "Copy &All" and "Close".
- Restore keeps the current text as a version first, puts the chosen text in the editor, and closes the window.
- Announced after: Restore: "Version put in the editor. Nothing was sent; your text before is in Previous Versions." None: "There are no earlier versions of this yet."
- Undo: Restore writes through replace_text (select all, then write), an ordinary editor change, so the editor's Undo should take it back; plus the "before restore" copy in Previous Versions.
- F1: window: "Earlier versions of this document, newest first: the ones QUILL kept and the site's own history." List: "Each row says when, the title, and why it was kept." View: "The full text of this version. Copy a paragraph from it, or close and choose Restore."
- Code: wordpress_more_commands.py (cmd_versions, _show_versions).
- Review notes:
  - Restore replaces the text but not the title; a version with a different title restores only its body.
  - There is no "compare this version with mine"; the only way to see differences is to read both.
  - The View report is titled just "Version", which says nothing about which one.

### Compare with Site

- How to reach it: File > WordPress > Compare with Site ("Alt+F, W, M"). WordPress key, then C. Document-only.
- What opens: background "loading the site's copy", then a report "Compare with Site": a header "<n> lines only on <site>, <m> only in yours." and lines starting "Site:" or "Yours:", with "Copy &All" and "Close". Identical: "Your copy and the copy on <site> are the same." (in the report).
- Not sent yet: "This is not on the site yet, so there is nothing to compare with."
- F1: "The differences between the site's copy and yours. Lines starting 'Site:' are the site's; 'Yours:' are yours."
- Code: wordpress_commands.py (cmd_compare, compare_text).
- Review notes:
  - The comparison is of your text converted to HTML against the site's HTML, so a Markdown document shows block markup lines as differences the writer never typed.
  - "Same" is shown in a report window rather than simply spoken; a one-line answer does not need a dialog.
  - No action from the report (take the site's line, keep mine); it is read-only.

### Move to Trash

- How to reach it: File > WordPress > Move to Trash... ("Alt+F, W, T"). WordPress key, then T. Document-only. Also the Open list's "Move to &Trash..." button.
- What opens: confirmation "Move to Trash": "Move '<title>' on <site> to the Trash? It can be brought back: choose Trash as the status in Open." buttons "Move to Trash" / "Cancel" (Cancel default).
- Announced after: "'<title>' moved to the Trash on <site>." Only local: "This is only on this computer. There is nothing on the site to move to the Trash."
- Without permission: "Your account on <site> is not allowed to delete this item." (site sentence).
- Undo: none in QUILL; restore from the Open list's "Restore from Trash".
- Cancel: silent.
- Code: wordpress_commands.py (cmd_trash, trash).
- Review notes:
  - "choose Trash as the status in Open" describes a control that does not exist; Open has a find field where you type "trash", and a "Restore from Trash" button.
  - The document stays open in the editor afterwards with its local status set to trash; nothing says what Save Draft or Publish will do next with it.

### Send and Copy (submenu)

- How to reach it: File > WordPress > Send and Copy ("Alt+F, W, C"). Rows: Send This Document to WordPress (D), Publish to Another Site (P), Duplicate (U), Send a Folder as Drafts (F), Download My Writing (M). None has a WordPress key; no written reason found for any.

### Send This Document to WordPress

- How to reach it: File > WordPress > Send and Copy > Send This Document to WordPress... ("Alt+F, W, C, D"). Not document-only (it is for ordinary documents).
- What opens: the site chooser "Send This Document to WordPress" (several sites), then choice "Send This Document to WordPress", "&Make it a:", rows "Post", "Page".
- What happens: the first heading becomes the title (or the file name), pictures on this computer are queued for upload, a new WordPress document opens, and it is sent as a draft.
- Announced after: "Sending '<title>' to <site> as a new <kind> draft; its <n> pictures go to the Media Library." then, when the send finishes, "Draft saved to <site>. It is not public."
- Refusals: already WordPress: "This is already a WordPress document. Save Draft to Site sends it to its site." Empty: "This document is empty, so there is nothing to send." Without permission: "Your account on <site> is <a role>, which cannot write pages or posts." (or "upload files" when it has pictures).
- F1: "Whether the document becomes a post or a page. Either way it goes as a draft: nothing is public until you publish it."
- Cancel: silent.
- Code: wordpress_route_copies.py, cross_site.py.
- Review notes:
  - Two sentences for one action, the first while a new document window opens (likely talked over).
  - The title is taken from the first heading without showing it; a person cannot correct it before it lands on the site.

### Publish to Another Site

- How to reach it: File > WordPress > Send and Copy > Publish to Another Site... ("Alt+F, W, C, P"). Document-only.
- What opens: with three or more sites, choice "Publish to Another Site", "&Copy to:"; with exactly two, no question at all. If categories or tags are missing on the target: confirm "Categories and Tags": "<target> has no <names>. Create them there? Cancel copies without them." buttons "Create Them" / "Cancel".
- Announced after: "'<title>' is a draft on <target>. <n> pictures were uploaded there. Left without: <names>." Only one site: "<site> is your only site. Connect another with Connect a Site first."
- Outside a WordPress document: "Publish to Another Site works in a WordPress page or post. Open one with File, WordPress."
- Code: wordpress_route_copies.py (cmd_publish_elsewhere, _copy_to).
- Review notes:
  - The command is named "Publish" but always creates a draft. "Copy to Another Site" would say what it does.
  - With two sites there is no confirmation before content is created on the other site.
  - In the Categories and Tags message, "Cancel" does not cancel: it carries on and copies without them. A Cancel button that continues the action breaks a universal expectation; the buttons should be "Create Them" and "Copy Without Them", with a real Cancel.

### Duplicate

- How to reach it: File > WordPress > Send and Copy > Duplicate... ("Alt+F, W, C, U"). Not document-only.
- What opens: in a WordPress document already on the site, straight to "Duplicate", "&Where:" (when you have several sites), rows "This site, <site>" and the others. Elsewhere: site chooser "Duplicate", then "&Duplicate a:" Post/Page, then background listing and a choice "&Post:" or "&Page:" of items, then Where.
- Announced after: same site: "'<title>' is a new draft on <site>." and the new draft opens. Another site: as Publish to Another Site. Empty: "<site> has no <kind>s to duplicate."
- F1: "Whether to duplicate a post or a page."; "The <kind> to make a new draft from."; "Where the new draft of '<title>' goes."
- Code: wordpress_route_copies.py (cmd_duplicate).
- Review notes:
  - In a WordPress document, Duplicate copies the site's copy, not your unsent edits; Publish to Another Site copies your local text. Neighbouring rows, different sources, no word about it.
  - With one site, Duplicate in a document creates a draft on the site with no confirmation at all.
  - The item list is a plain choice with no filter.

### Send a Folder as Drafts

- How to reach it: File > WordPress > Send and Copy > Send a Folder as Drafts... ("Alt+F, W, C, F"). Not document-only.
- What opens: site chooser "Send a Folder as Drafts", then the Windows folder picker titled "Send a Folder as Drafts", then a confirmation "Send a Folder as Drafts": "Send <n> files to <site> as drafts? Check Before Publishing found things to look at in <k> of them." (or "found nothing to look at."), then up to 12 lines "- <file>: <title> (<k> things to look at)" and "- and <n> more"; button "Send <n> Drafts" / "Cancel".
- Announced after: "<n> drafts from <folder> are on <site>." plus " <k> could not be sent: <first failure>". No usable files: "<folder> has no Markdown, text, web-page or Word files to send. Nothing was sent."
- Code: wordpress_route_archive.py, writing_archive.py.
- Review notes:
  - Every file becomes a post; there is no Post or Page choice, unlike Send This Document.
  - Only the first failure is named.

### Download My Writing

- How to reach it: File > WordPress > Send and Copy > Download My Writing... ("Alt+F, W, C, M"). Not document-only (uses the document's site when in one, otherwise asks).
- What opens: the folder picker "Download My Writing from <site>" (new folders allowed), then, when Word is available, choice "Download My Writing", "&Save each page and post as:", rows "Markdown files (.md)" and "Word documents (.docx)".
- Announced: at start "Saving your writing on <site> to <folder>, in the background. QUILL says when it is done." (or "Carrying on saving" when resuming). At the end: "Your writing on <site> is in <folder>: <n> saved, <m> already up to date, <p> pictures. Left out: comments, revisions, categories, tags, excerpts, featured images, custom fields, and pictures kept on other sites (their links stay)." plus " <k> could not be saved; run it again to try those."
- F1: "Markdown keeps every block and opens in any editor; Word documents open in Word and QUILL. The pictures and the contents page are the same either way."
- Code: wordpress_route_archive.py, writing_archive.py, workbench_carry.py.
- Review notes:
  - "Saving ... QUILL says when it is done." is spoken before the permission check; a refused account then hears a second sentence contradicting the first.
  - The final sentence always ends with a long "Left out:" list, every time, even on a resume that saved nothing new.

### Insert menu rows (overview)

- How to reach them: Insert ("Alt+I"), at the foot after a separator. All seven are document-only except Make a Picture. None has a WordPress key; no written reason found.
- Review notes:
  - Every one of the seven WordPress access letters collides with an existing Insert row in QUILL: "WordPress &Block..." (B) with "Insert Code &Block"; "Pict&ure from the Media Library..." (U) with "Q&uick Insert..."; "Picture from This &Computer..." (C) with "Insert &Citation..."; "Li&nk to a Page on This Site..." (N) with "I&nsert HTML Tag..."; "N&ote on This Block..." (O) with "Insert Em&oji..."; "Make a Pictu&re..." (R) with "Insert Horizontal &Rule"; "WordPress &Icon..." (I) with "L&ist". In a Windows menu a repeated letter cycles the highlight instead of choosing, so none of these rows can be chosen by its letter. menu.py chose these letters for QUILL Lite's menus; nothing checks them against QUILL's.

### WordPress Block

- How to reach it: Insert > WordPress Block... ("Alt+I", then B, but B is shared; see overview). Document-only.
- What opens: background "loading the site's blocks and patterns", then a list window "Insert Block": "&Find:" field, "&Blocks:" list (QUILL's core blocks first, then the site's blocks, patterns and synced patterns), "&Insert" button, any Pattern Directory buttons, "Close". If the block needs answers, a form "Insert <block>" with OK labelled "Insert".
- Announced after: "<block> inserted." Nothing to insert: "<block> has nothing to insert." No blocks in document is not a condition here.
- Undo: one insert_text; one Undo takes it back (the module docstring states this).
- F1: window: "The blocks you can insert on <site>: QUILL's own core blocks first, then the site's other blocks, its patterns and its synced patterns." List: "Each block's name and what it is for. Press Insert to add it." Find: "Type part of a name and press Enter. \"but\" finds Button." Form: "What the new <block> block needs. Everything else can wait."
- Code: wordpress_block_commands.py, block_catalog.py, wordpress_pattern_commands.py.
- Review notes:
  - Menu says "WordPress Block", the window says "Insert Block", and the no-blocks sentence elsewhere says "Insert one with Insert Block". Three names for one command.
  - Enter on a row does nothing (no on_enter); you must Tab to Insert. Every other picker in this family (Open, Notes, Fix Link Text) honours Enter.
  - It needs the network even for QUILL's own core blocks; offline, nothing can be inserted.

### Picture from the Media Library

- How to reach it: Insert > Picture from the Media Library... ("Alt+I", then U, shared with Quick Insert). Document-only.
- What opens: the WordPress Workbench, on the site's Media, in picking mode, announced "Picking a file for <document>: Enter on a file inserts it." Without a window to come back to, a choice "Insert from Media Library", "&Files:". A picture then opens the picture dialog "Picture: <name>": "&Alternative text:", "&Suggest Alternative Text" button, "&Decorative: it adds nothing a visitor needs" check box, "&Caption:", "Display &width (<size>):" combo, "File si&ze:" choice, "Use as &featured image" check box, "&Link to:" combo ("Nothing", "The picture file"), "Describe &Image..." button, "Insert" (default) and "Cancel".
- Announced after: "Picture inserted: <alt or name>." For audio or video: "<Kind> inserted: <name>." If the AI wrote a fuller description, a confirm "Fuller Description": "Your AI also wrote a fuller description, as it does for a chart or a diagram. Add it as a paragraph after the picture, for you to edit?" button "Add Description". Empty library: "<site>'s Media Library is empty. Use Upload Files." Document changed while picking: "<title> is no longer in front, so nothing was inserted. Bring it forward and choose Insert again."
- Undo: one insert_text (plus a second for the fuller description).
- Code: wordpress_media_library.py, wordpress_workbench_editor_side.py, wordpress_item_dialogs.py (ImageDialog).
- Review notes:
  - Inserting a picture now opens a whole second window (the Workbench) rather than a dialog; for a screen-reader user that is a heavy context switch for a common task, and you must find your way back.
  - "Use Upload Files" points at a command in Tools > WordPress > More Media without saying where.

### Picture from This Computer

- How to reach it: Insert > Picture from This Computer... ("Alt+I", then C, shared with Citation). Document-only.
- What opens: the Windows file picker "Insert Picture from This Computer" (Pictures or All files), then the picture dialog as above (without File size).
- Announced after: "Picture inserted: <alt or name>. It is uploaded when you next send." Then the fuller-description offer, if any.
- Undo: one insert_text; the pending upload stays recorded in the working copy even if you Undo the text (not found in code that it is removed).
- Code: wordpress_media_library.py, wordpress_media_dialogs.py.
- Review notes:
  - Undoing the insert leaves the picture queued for upload (the pending upload is kept in the working copy and uploaded on the next send if the file exists; _upload_pending replaces the address only if it is in the text but uploads either way).

### Link to a Page on This Site

- How to reach it: Insert > Link to a Page on This Site... ("Alt+I", then N, shared with Insert HTML Tag). Document-only.
- What opens: background "listing what <site> has published", then choice "Link to a Page on This Site", "&Page or post:", rows "<title>, <kind>" (pages first, then posts; the document itself excluded).
- Announced after: "Link to '<title>' inserted." None: "<site> has no published pages or posts to link to."
- F1: "The published pages and posts on this site. The link goes in at the caret, using the selected text, or the page's title when nothing is selected."
- Outside a WordPress document: "Link to a Page on This Site works in a WordPress page or post. Open one with File, WordPress."
- Undo: one insert_text.
- Code: wordpress_link_commands.py.
- Review notes:
  - No filter on what can be hundreds of rows; first-letter navigation in a list box is the only help.
  - Drafts and scheduled pages cannot be linked to, with no word about why they are missing.

### Note on This Block

- How to reach it: Insert > Note on This Block... ("Alt+I", then O, shared with Insert Emoji). Document-only.
- What opens: in a Markdown document where the block would become protected, a confirm "Add Note": "Markdown has no way to write which note belongs to a block, so this block will become one protected line that keeps the note's link exactly. Its words can then be changed only through WordPress or an HTML document. Add the note?" button "Add Note". Then a multi-line text dialog "Add Note on <place>", "&Note:".
- Announced after: "Note added on <place> on <site>. Save Draft to Site or Publish to tie it to the block there." Block moved meanwhile: "Note added on <site>, but the block moved while it was sent, so it is not tied to a block yet." Not in a block: "The caret is not in a block. Move to one with Next Block, then add the note." Not on the site: "This is not on <site> yet, so it has no notes. Save Draft to Site first, then notes can be read and added."
- Without permission: "Your account on <site> is <a role>, which cannot read or write notes on blocks." Old WordPress: "Notes on blocks need WordPress 6.9 or later, and <site> runs <version>. Ask the site's administrator to update it."
- F1: "A note on <place>, for the people editing <site>. Visitors never see it; people in the block editor see it beside the block."
- Undo: the note itself is on the site at once and Undo does not remove it; the block change is one replace_text.
- Code: wordpress_notes_commands.py, block_notes.py.
- Review notes:
  - The note is sent to the site immediately, while the tie to the block waits for the next send; Undo in the editor takes back the tie but leaves an orphan note on the site.
  - The "protected line" warning is a heavy consequence (the block's words become uneditable in Markdown) for adding a comment; worth surfacing in the menu row or offering to switch to HTML.

### Make a Picture

- How to reach it: Insert > Make a Picture... ("Alt+I", then R, shared with Horizontal Rule). Not document-only.
- What opens: "Picture Maker" (shared with Studio): "&Describe the picture, or the change you want", "S&hape", "Bac&kground", "Co&lour", "&Make the picture", "&Versions", "Suggest from &Page Content", "Make a video &with this picture...", "Open &folder", "Close". Before anything is sent, a confirm "Make the Picture" with the AI consent wording, button "Make the Picture".
- Announced: "Making the picture. This can take a minute." Refusal: "Nothing was sent." Failure: "No picture was made: <error>". No AI: "AI help is not available in this window." Safe Mode: "QUILL is in Safe Mode, so AI is off and nothing was sent." Suggest: "Sending the selection to your chosen AI for a picture suggestion." (or "the page's text"), then "Suggestion ready. <why>". Insert into the document uploads at once and opens the picture dialog.
- Code: wordpress_picture_commands.py, studio_picture_maker.py, wordpress_picture_ai.py.
- Review notes:
  - It is not document-only, so a person can spend AI time making a picture in an ordinary document and only learn at Insert that "This is not a WordPress document...".
  - A made picture uploads the moment you insert it; a picture from this computer waits for the next send. Same menu, two rules.

### WordPress Icon

- How to reach it: Insert > WordPress Icon... ("Alt+I", then I, shared with List). Document-only.
- What opens: background "reading <site>'s icons", then a list window "Insert Icon": "&Find:", "&Icons:", "Insert with a &Label...", "Insert as &Decorative", "Close". Insert with a Label asks "Icon Label", "&Label:" (filled with the icon's name).
- Announced after: "Icon inserted, labelled '<label>'." or "Decorative icon <name> inserted; screen readers skip it." Blank label: "An icon needs a label that says what it means, or to be inserted as decorative. Nothing was inserted." No icons: "<site> has no icons to insert." Old WordPress: "<site> has no icon library. Icons arrived in WordPress 7.0."
- Without permission: "Your account on <site> is <a role>, which cannot insert icons."
- Outside a WordPress document: "Insert Icon works in a WordPress page or post. Open one with File, WordPress." (the menu calls it "WordPress Icon").
- F1: window: "<site>'s icons by name. Each goes in with a label that says what it means, or marked decorative so screen readers skip it; never unnamed." Label: "What the icon means, said by screen readers in its place: for example 'Phone us'. An icon that only decorates should be inserted as decorative."
- Undo: one insert_text.
- Code: wordpress_route_links.py, icons.py.
- Review notes: the refusal names it "Insert Icon"; the menu row says "WordPress Icon".

### Format > WordPress (submenu)

- How to reach it: Format > WordPress ("Alt+O, P"; Format is "F&ormat", the submenu "Word&Press"). Rows: Block Settings (S), Image Size (Z), Mark Language (L). All document-only; none has a key; no written reason found.

### Block Settings

- How to reach it: Format > WordPress > Block Settings... ("Alt+O, P, S"). Document-only.
- What opens: background "reading the theme's colours", then a form "Block Settings" (fields depend on the block). In Markdown, if the change would protect the block, confirm "Block Settings": "Markdown has no way to write these settings, so this block will become one protected line that keeps them exactly. Its words can then be changed only through WordPress or an HTML document. Change it?" button "Make Protected Block".
- Announced after: "Block settings changed." plus a contrast warning when a colour pair is weak. Not in a block: "The caret is not in a block. Move to one with Next Block, then try again." Others: "QUILL could not read this block.", "This block has no settings QUILL can change."
- F1: purpose "The settings of this <block> block." plus " <site> did not share its theme's colours." when it did not.
- Undo: one replace_text.
- Code: wordpress_block_commands.py, block_settings.py.
- Review notes: needs the network just to read colours; offline, no settings can be changed at all.

### Image Size

- How to reach it: Format > WordPress > Image Size... ("Alt+O, P, Z"). Document-only.
- What opens: background "reading the picture's sizes", then choice "Image Size", "&Size:", rows of sizes (", the size it is now" on the current one), with "Back to Earlier Size: <label>" first when there is one.
- Announced after: "Picture shown at <label>." Same size: "The picture is already that size." No caret on a picture: "Put the caret on a picture in the document first, then choose Image Size." Not in the library: "This picture is not in <site>'s Media Library, so it has no other sizes. Upload it first." Gone: "The picture has moved or gone from the document, so nothing changed."
- F1: "How wide the picture shows on the page, from the sizes WordPress made of it. Proportions are kept and nothing is cropped; only the markup changes. Back to Earlier Size puts the previous choice back."
- Undo: one replace_text.
- Code: wordpress_image_commands.py.
- Review notes: replace_text rewrites the whole document; the caret is then put back at the picture with go_to_offset, which is good.

### Mark Language

- How to reach it: Format > WordPress > Mark Language... ("Alt+O, P, L"). Document-only.
- What opens: text dialog "Mark Language", "&Language:" (last answer filled in).
- Announced after: "The selection is marked as <language>." or "The whole page is marked as <language>." Unknown: "QUILL does not know '<text>' as a language. Type a name such as French, or a code such as fr or pt-BR." Empty page: "There is nothing on the page to mark yet."
- F1: "The language of the selected words, as a name such as French or a code such as fr or pt-BR. With nothing selected, the whole page is marked. A visitor's screen reader switches voice there."
- Undo: one insert_text or replace_text.
- Code: wordpress_check_commands.py, page_report helpers.
- Review notes:
  - With nothing selected the whole page is wrapped with no confirmation; forgetting to select is the likely mistake, and the result changes the language of everything. A confirm, or "Nothing is selected: mark the whole page?", would catch it.

### View menu rows

- How to reach them: View ("Alt+V"), at the foot after a separator: WordPress Blocks (B, also WordPress key B), Preview Blocks (V), Block Notes (L), Play Media Here (M). All document-only.
- Review notes:
  - Three of the four access letters collide in QUILL's View menu: "WordPress &Blocks..." (B) with "&Browser Preview..."; "Pre&view Blocks" (V) with "Pre&view Side by Side"; "B&lock Notes..." (L) with "Announce &Lists". Only Play Media Here's M is free (from the rows found in main_frame_menu.py).

### WordPress Blocks

- How to reach it: View > WordPress Blocks... ("Alt+V", then B, shared with Browser Preview). WordPress key, then B. Document-only.
- What opens: a list window "Blocks": "&Blocks:" list (each block's kind and first words, ", inside <parent>" when nested), buttons "&Go To", "Move &Up", "Move Do&wn", "&Duplicate", "&Remove...", "&Change To...", "Gr&oup", "U&ngroup", "Close". Remove confirms: "Remove <block> from this document? Undo in the editor brings it back. Nothing changes on the site until you send it." button "Remove Block". Change To asks "Change To", "&Kind of block:".
- Announced after: "Moved up.", "Moved down.", "Duplicated. The copy is straight after it.", "Block removed.", "Changed to <kind>.", "Grouped.", "Ungrouped.", or the reason a change cannot be made ("QUILL cannot change this kind of block to another."). No blocks: "This document has no blocks yet. Insert one with Insert Block."
- Undo: each change is one replace_text; Undo in the editor takes it back (stated in the window's help).
- F1: window: "Every block in this document, in order. Each change here is one step that Undo in the editor takes back, and nothing else in the document moves." List: "Each block's kind and its first words; nested blocks say what they are in." Change To: "What this block becomes. Its words are kept."
- Code: wordpress_block_commands.py, block_edit.py, block_spans.py.
- Review notes:
  - After Move Up or Move Down the list keeps the same row number selected, so the selection stays put while the block moves; pressing Move Up twice swaps the pair back. The Rows type in wordpress_dialogs.py exists for exactly this ("a row moved down follows the row") and is not used here.
  - No Enter action; Enter on a row does nothing (Go To is a button).
  - Menu "WordPress Blocks", window title "Blocks", and the no-blocks sentence names "Insert Block", which the Insert menu calls "WordPress Block".

### Preview Blocks

- How to reach it: View > Preview Blocks ("Alt+V", then V, shared with Preview Side by Side). Document-only.
- What opens: background "rendering the blocks", then a report "Preview Blocks" with the rendered page as plain text in reading order ("(The page is empty.)" when empty), "Copy &All", "Close".
- Announced after the report closes, if any block failed: "<site> could not show <n> block(s): <first reason>".
- F1: "This document as <site> renders its blocks, as plain text in reading order. Nothing was saved to make it."
- Code: wordpress_block_commands.py, block_preview.py.
- Review notes: the failure count is spoken only after you close the report, when it is no longer useful; it belongs at the top of the report.

### Block Notes

- How to reach it: View > Block Notes... ("Alt+V", then L, shared with Announce Lists). Document-only.
- What opens: background "reading notes on <site>", then a list window "Notes, <site>": "&Notes:" list, "&Details:" read-only field, buttons "&Go to It", "&Reply...", "Re&solve or Reopen", "&Add Note...", "Close". Enter goes to the block. Reply asks "Reply to <author>", "&Reply:" (multi-line).
- Announced after: Reply: "Reply to <author>'s note saved on <site>." Resolve: "<author>'s note resolved on <site>." (or "reopened"). None: "No notes on this <kind> on <site>. Add Note puts one on the block at the caret." Block gone: "That note's block is not in your copy. It may have been removed here, or the note is on a newer version on the site."
- Without permission and old WordPress: as Note on This Block.
- F1: window purpose "The block editor's notes on this <kind>: <n>, <m> open. Each says who wrote it, on which block, and what it says. Visitors never see notes." List: "Each note's author, the block it is on, its words, how many replies, and whether it is resolved. Enter goes to the block."
- Code: wordpress_notes_commands.py.
- Review notes: the list is updated optimistically before the site answers; if the reply fails, the list still shows it.

### Play Media Here

- How to reach it: View > Play Media Here ("Alt+V", then M). Document-only.
- What opens: a player window "Play: <title>" with QUILL's player panel (play/pause, stop, rewind and forward, speed, position, volume), a video picture panel for video, and "&Captions" (video), "&Go to Position...", "Open in &Quill Media Player", "Open in &Browser", "Close".
- Announced: nothing at caret: "There is no audio or video block at the caret. Move to one, or insert one with Insert from Media Library." Captions: the caption text, "No caption at <time>.", or "This video has no captions track on <site>." No video picture: "On this computer the video's sound plays here; Open in Browser shows the picture." Player app: "Quill Media Player is not part of this release yet. Use Open in Browser." or "Opening <title> in Quill Media Player."
- F1: window: "Plays <title> from <site>, streamed from the site over HTTPS; nothing is saved on this computer. ... Closing the window stops playback." Video panel: "The video's picture. It is not a control: Tab moves past it, and the buttons control playback."
- Outside a WordPress document: "Play Media Here works in a WordPress page or post. Open one with File, WordPress."
- Code: wordpress_player_commands.py, wordpress_player_window.py, media_play.py.
- Review notes: "Insert from Media Library" is not the menu's name ("Picture from the Media Library...", which also inserts audio and video despite saying "Picture").

### Edit > WordPress (submenu)

- How to reach it: Edit > WordPress. The submenu title has no access letter ("WordPress", not "&WordPress"): press "Alt+E" and arrow to it. Rows: Next Block (N), Previous Block (P), Where Am I (W), Hear Where a Link Goes (H), Fix Link Text (L). All document-only. None has a WordPress key; no written reason found.
- Review notes:
  - The one submenu a writer would visit most while working in a page has no letter (the Edit menu's W is "&Word Prediction..."), and none of its rows has a chord, so moving block by block means Alt+E, arrows, Enter, N for every block. This is the strongest case in the section for a key.
  - The Command Palette now has two commands titled "Next Block" (navigate.next_block and wordpress.next_block) and two titled "Where Am I" (verbosity.where_am_i and wordpress.where_am_i), with no way to tell them apart by name.

### Next Block

- How to reach it: Edit > WordPress > Next Block ("Alt+E", arrow to WordPress, then N). Document-only.
- What happens: moves the caret to the start of the next block.
- Announced after: the block's kind, position and first words, from spoken_move, in the shape "Image block, 4 of 12: Volunteers at the spring fair" (the docstring's example). End: "No more blocks after this one." No blocks: "This document has no blocks yet. Insert one with Insert Block."
- Outside a WordPress document: the generic "This is not a WordPress document..." sentence.
- Code: wordpress_block_commands.py, block_spans.py.

### Previous Block

- How to reach it: Edit > WordPress > Previous Block ("Alt+E", arrow to WordPress, then P). Document-only.
- Announced after: as Next Block; at the start: "No blocks before this one."
- Code: wordpress_block_commands.py.

### Where Am I

- How to reach it: Edit > WordPress > Where Am I ("Alt+E", arrow to WordPress, then W). Document-only.
- Announced: which block the caret is in and what it sits inside, in the shape "Paragraph block: Morning sessions, inside column 1 of Columns" (where_am_i's docstring). Between blocks: "Not in a block. The next one is <block>." or "Not in a block, and there are no blocks after this point." No blocks: "This document has no blocks yet. Insert one with Insert Block."
- Code: wordpress_block_commands.py, block_spans.py.

### Hear Where a Link Goes

- How to reach it: Edit > WordPress > Hear Where a Link Goes ("Alt+E", arrow to WordPress, then H). Document-only.
- What happens: on a link, asks the site in the background ("asking <site> where the link goes") and speaks the target's title. With no link at the caret, a text dialog "Hear Where a Link Goes", "&Address:"; then the title is spoken and a confirm "Hear Where a Link Goes": "<target sentence>" blank line "Insert a link to it, with the words '<words>'?" button "Insert Link".
- Announced after: the target sentence: "Goes to '<title>'. <description>." or "<url> has no title." or "<url> could not be reached: <why>". After inserting: "Link to '<title>' inserted."
- Without permission: "Your account on <site> is <a role>, which cannot read where links go." Old WordPress: "<site> cannot read where a link goes. That needs WordPress 5.9 or later."
- F1: "There is no link at the caret. Type or paste a web address: QUILL asks the site what page is there and reads its title, then offers to insert the link."
- Undo: one insert_text.
- Code: wordpress_route_links.py, link_targets.py.
- Review notes:
  - The target sentence is spoken and then repeated as the first line of the confirm that opens at once, so it is said twice, and the spoken copy is the one likely to be cut off.
  - A "hear" command that turns into an "insert a link" command when there is no link at the caret is a surprise; the two would be clearer as separate rows.

### Fix Link Text

- How to reach it: Edit > WordPress > Fix Link Text... ("Alt+E", arrow to WordPress, then L). Document-only.
- What opens: background "asking <site> where <n> links go", then a list window "Fix Link Text": "&Links:" (rows "'<words>' goes to '<title>'", or "... goes to <url>, which has no title", or "Fixed: now '<title>'"), buttons "&Use the Page's Title", "Use &All Titles", "Close". Enter uses the title.
- Announced after: "The link now says '<title>'." or "That link has no page title to use; write its words yourself." Use All: "<n> links now say where they go." None: "No 'click here' or 'read more' links in this document."
- Without permission and old WordPress: as Hear Where a Link Goes.
- F1: window: "Links whose words do not say where they go, with the title of the page each one goes to. The site read each page; nothing was sent anywhere else." List: "Each vague link's words, and the title of the page it goes to."
- Undo: each fix is its own replace_text, so Use All Titles over ten links is ten Undo steps.
- Code: wordpress_route_links.py.
- Review notes:
  - Each fix rewrites the whole document with replace_text and never puts the caret back, so after closing the window the caret is at the end of the document, far from where you were.
  - Use All is several Undo steps, not one, unlike every Blocks window change.
  - There is no way to type your own words for a link from this window; the only choices are the page title or nothing.

### Tools > WordPress, at a glance

- Where it is: Alt+T opens Tools (the menu bar label is "&Tools" in main_frame_menu.py). The WordPress rows sit at the foot of Tools after a separator, in a submenu titled "WordPress" with no ampersand, so it has no access letter in QUILL either: arrow to it and press Right Arrow. menu.py says the letter was dropped because QUILL Lite's Tools uses W for Say Word Summary; QUILL builds the same title verbatim from the shared table.
- It only exists while the WordPress feature ("core.wordpress") is on.
- The WordPress key is a two-step layer. Press Ctrl+Alt+Shift+Grave, hear "WordPress keys", then press one letter within 4 seconds. Escape says "Left WordPress keys". A letter with no command says "No WordPress command on X." In this doc, "WordPress key, then K" means that sequence. If the user has moved the QUILL key onto Ctrl+Alt+Shift+Grave, the QUILL key wins and the WordPress layer goes quiet.
- In the menu, a row with a layer key shows it in brackets after the title, for example "Check Before Publishing... (Ctrl+Alt+Shift+Grave, K)". It goes in brackets rather than after a tab so wx cannot turn it into a fake accelerator (main_frame.py _menu_label).
- There are no DEFAULT_ALIASES entries for any WordPress command (keymap.py).
- The rows, in order:
  - Open WordPress Workbench... (no access letter; WordPress key, then H)
  - separator
  - Check Before &Publishing... (P; WordPress key, then K; document-only)
  - Check &This Page (T)
  - Check the &Whole Site... (W)
  - &Undo Site Fix... (U)
  - Site-wide &Find and Replace... (F)
  - Write an &Accessibility Statement... (A)
  - Pa&lette Report (L)
  - In &Short... (S; document-only)
  - separator
  - Media Li&brary... (B; WordPress key, then M; opens the Workbench)
  - Alt Te&xt Review... (X; WordPress key, then X; document-only)
  - Alt Text for the Whole Lib&rary... (R)
  - &Visual Review... (V)
  - M&ore Media (O), a submenu:
    - &Upload Files... (U; WordPress key, then U)
    - Upload from &Web Address... (W)
    - &Paste Image (P)
    - Upload a &Large File... (L)
    - &Regenerate Sizes... (R)
    - Make a S&maller Copy... (M)
    - Edit a Picture on the S&ite... (I)
    - Site L&ogo... (O)
    - Previ&ew and Review... (E)
    - separator
    - Captions for &Video... (V)
    - &Transcript for Audio... (T)
    - Make a Listening Versio&n... (N; document-only)
    - Name Em&beds (B; document-only)
    - Publish a &Document as a Page... (D)
  - separator
  - &Comments... (C; opens the Workbench)
  - Categories and Ta&gs... (G; opens the Workbench)
  - Me&nus... (N; opens the Workbench)
  - Menu &History... (H)
  - Site Chec&k (K; opens the Workbench)
  - Site S&ettings... (E; opens the Workbench)
  - &Design (D), a submenu:
    - Style &Variations... (V)
    - Site &Styles... (S)
  - Plug&in Extras (I), a submenu:
    - Events &Coming Up... (C)
    - New &Event... (E)
    - Shop &Orders... (O)
  - &Manage (M), a submenu:
    - &Users... (U; opens the Workbench)
    - &Application Passwords... (A; opens the Workbench)
    - P&lugins... (L; opens the Workbench)
    - T&hemes... (H; opens the Workbench)
    - &Fonts... (F; opens the Workbench)
    - S&ynced Patterns... (Y; opens the Workbench)
    - separator
    - &Widgets... (W; opens the Workbench)
    - Site Ma&p... (P; opens the Workbench)
    - Template &Outline (O)
    - separator
    - &Bulk Edit... (B)
    - Page O&rder... (R)
    - separator
    - Previous Loo&ks... (K)
    - &Space Used (S)
    - Download a Copy of the Site's &Design... (D)
    - separator
    - AI Abili&ties... (T; opens the Workbench)
    - Ask th&e Site... (E)
    - separator
    - S&ign Out This Site... (I)
  - &Your Sites (Y), a submenu:
    - Coming &Up... (U)
    - &What Changed on My Sites... (W)
- Only five of the 57 rows in Tools > WordPress have a WordPress key: Workbench (H), Check Before Publishing (K), Media Library (M), Alt Text Review (X) and Upload Files (U). The other layer letters belong to File and View rows.
- Document-only rows are dimmed unless a WordPress document is in front. This is checked by _refresh_wordpress_menu_items, which looks up the front document's working copy. In Tools the document-only rows are Check Before Publishing, In Short, Alt Text Review, Make a Listening Version and Name Embeds.
- Several more rows need a WordPress document but are not on the DOCUMENT_ONLY list, so they stay enabled and only refuse once chosen: Visual Review, Preview and Review, Paste Image, Captions for Video and Transcript for Audio. Details are under each command.
- Common behaviour for the site-wide rows:
  - The site is the front document's site.
  - Otherwise, with one site connected, that site is used without asking.
  - Otherwise a chooser opens, titled after the command: list "&Site:", default site selected, OK (default) and Cancel. Its F1 says "Choose which of your WordPress sites to use. Your default site is selected." Cancel is silent.
  - With no site connected, the command says "Connect a WordPress site first." and the Connect a Site flow starts.
- Common behaviour on failure: any background failure is spoken as one sentence from failure_sentence. A refused request reads like "Your account on {site} is not allowed to do that." or "{site} did not accept the sign-in. Check the username and application password, then reconnect." (api.py plain_error).
- Common side announcement: the first time any command touches a site in a session, QUILL also says "{site}: N comments waiting." (wordpress_admin_commands.py announce_waiting_once), and the same goes for new form responses. So the first command on a site can produce an extra sentence nobody asked for.
- Common list window (wordpress_dialogs.py ListWindow). It has an optional "&Search:" box, then the list, then an optional read-only "&Details:" box, then the action buttons, then a Close button (Escape). Its F1 says "Close this window. Escape does the same."
  - The window's "purpose" sentence is set only as help text (SetHelpText). It is never shown as text on screen, so F1 is the only way to hear it once the window is open.
- Common confirmation: a Yes/No message box whose Yes button is renamed to the action and whose No button is renamed Cancel. No is the default (wx.NO_DEFAULT), so Enter cancels.
- Common report window (ReportDialog): a read-only "&Report:" text box, a "Copy &All" button and a Close button.
- Review notes for the whole submenu:
  - 15 of the 57 rows now open the WordPress Workbench instead of their own window. workbench_door() calls open_from_door(), which always returns True. The docstrings in wordpress_commands.py and at each door still say "behind its flag" and "the developer flag sends this door". Both are stale, and every legacy window under those doors can no longer be reached from this menu.
  - The menu teaches one letter and the WordPress key uses another, against menu.py's own stated rule ("A row's own access letter wherever it is free, so the menu teaches the key"):
    - Check Before Publishing has access letter P, but its layer key is K. WordPress key, then P, publishes.
    - Media Library has access letter B, but its layer key is M. WordPress key, then B, opens View > WordPress Blocks.
    - Site Check holds the access letter K, the same letter that runs Check Before Publishing from the WordPress key.
  - Four rows start with or contain "Check": Check Before Publishing, Check This Page, Check the Whole Site and Site Check. Site Check is really Site Health and lives in another group. That is easy to confuse by ear.
  - "Coming Up" appears twice: Plugin Extras > Events Coming Up (its site chooser is titled "Coming Up") and Your Sites > Coming Up (scheduled posts). Both lists are titled "Coming Up, ..." or "Coming Up".
  - Keyless rows have no written reason. The bound-command gate (test_family_rules_and_gates.py) only walks DEFAULT_KEYMAP, the WordPress rows are registered at menu build time with try_register, and NOT_EDITOR_COMMANDS has no "wordpress." family. About 50 Tools rows therefore have neither a key nor a recorded rule 7 or rule 8 decision.
  - Every bracketed key is spoken as "Ctrl+Alt+Shift+Grave, K" as part of the item name. That is long on every arrow press, and the prefix is not the friendly "QUILL Key + ..." form the QUILL key gets.

### Open WordPress Workbench...

- How to reach it: Alt+T, then arrow to WordPress (no access letter) and press Right Arrow. "Open WordPress Workbench..." is the first row and has no access letter, by design: the menu.py comment says every letter of its name is taken. WordPress key, then H.
- What opens: the one WordPress Workbench window (wordpress_workbench_window.open_workbench). If it is already open, it is brought forward and keeps the place, row and filter it was left at. When it first opens, it starts at the current site's Inbox, or at the Start node when no site is connected. Focus goes to the tree.
- Announced after: nothing from this command itself. The Workbench window title is left to the screen reader.
- Safe Mode: QUILL_SAFE_MODE=1 is passed through to the Workbench.
- Code: wordpress_commands.py (cmd_workbench), wordpress_workbench_window.py.
- Review notes:
  - It is the only row in the submenu with no access letter. Opening it from the menu means arrowing to the top of the submenu or knowing the H layer key.
  - The trailing "..." suggests a dialog, but it opens a full peer window.

### Check Before Publishing...

- How to reach it: Alt+T, WordPress submenu, then P. WordPress key, then K.
- Document-only: dimmed outside a WordPress document. Reached some other way, for example from the Command Palette, it says: "This is not a WordPress document. Open one with Open Page or Post, or start one with New Page or New Post, in the WordPress menu under File." It uses the generic NOT_WORDPRESS sentence because cmd_check calls self.current() without a command name.
- What happens: the document is converted to what would be sent and checked on this computer (checks.check_content). The summary is spoken first, for example "Ready to publish: no problems found" or "2 things to look at: 1 problem, 1 to check".
- What opens: when there is at least one finding, a list window titled "Check Before Publishing".
  - The list "&Things to look at:". Its F1 says "Each one says what to look at and why. None of them stops you publishing."
  - A "&Go to It" button. Its F1 says "Close this and go to that place in the document."
  - Close.
  - The window's F1 purpose is the same summary sentence.
- Go to It: moves the caret to the excerpt and closes the window. If the spot cannot be found, it says "QUILL could not find that spot in the text; it may be inside a block line." Markdown-to-block conversion problems are listed too, as "Line N: ...", but have no excerpt, so Go to It on them always gives that sentence.
- Undo: nothing to undo. It changes nothing.
- Cancel: Escape or Close closes the window silently.
- Code: wordpress_more_commands.py, checks.py.
- Review notes:
  - The summary is announced just before a modal opens, so the dialog title announcement may cut it off. The purpose text that repeats it is reachable only with F1.
  - When there are no findings, nothing opens and only the summary is spoken. That is good, but it is the only feedback.
  - Go to It on a conversion-problem row is a guaranteed dead end. Those rows could go to their line number instead.

### Check This Page

- How to reach it: Alt+T, WordPress submenu, then T. No WordPress key.
- Not document-only.
  - In a WordPress document, it checks that page's published address.
  - In any other document, it uses the site chooser (titled "Check This Page") and checks the site's home page.
- Refusals before anything runs:
  - The document is not published: "Check This Page reads the published page, and this is not published on {site} yet. Check Before Publishing looks at your own text now."
  - axe-core is missing: "Check This Page needs axe-core, which is not in this copy of QUILL. Nothing was checked and nothing was downloaded. Check Before Publishing still checks your own text."
  - No browser: "Check This Page needs Microsoft Edge or Google Chrome, and neither is on this computer. QUILL does not download a browser. Check Before Publishing still checks your own text."
- What happens: the published page loads in a hidden browser and axe-core runs on it. The site's url-details route checks dead links when the site has that route.
- Announced after: a summary such as "{site}, {title}: 3 problems, 2 to check" or "{label}: no problems found by axe-core". When dead links were checked, a dead-link sentence is added.
- What opens: a list window titled "Check This Page".
  - Its purpose (F1 only) is the summary plus ". Checked with axe-core; the page was sent nowhere."
  - The list "&Findings:". Its F1 says "Each problem axe-core found, in plain words: how many places, whose it is, and who it affects."
  - "&Explain..." opens a report titled "Explain": the WCAG criterion, who it affects, and each place.
  - "&Go to It" goes to the spot in the document.
    - If the finding belongs to the theme or a plugin, it says "That one is in the theme or a plugin, not in your document. Write a Note for the Theme Author makes a report you can send them."
    - If no WordPress document is open, it says "Open the page in the editor first, then Go to It can take you there."
    - If the spot cannot be found, it says "QUILL could not find that place in your document; Explain shows what it looks like on the page."
  - "Write a &Note for the Theme Author..." opens a report titled "Note for the Theme Author", ready to paste. On a content finding it says instead "That one is in your own content, so you can fix it yourself; Go to It takes you there."
  - "Page &Shape..." opens a report titled "Page Shape": landmarks and headings in order.
  - "Dead &Links...", only when dead links were checked, opens a report titled "Dead Links" that starts "N of M links go nowhere."
  - Close.
- On failure: "Check This Page could not check {label}: {reason}"
- Cancel: the site chooser's Cancel is silent. The window's Close is silent.
- Code: wordpress_check_commands.py, page_audit.py.
- Review notes:
  - The summary is announced right before the modal opens, so it can be cut off.
  - A list with zero findings still opens a window with an empty list. Unlike Check Before Publishing, there is no early return when nothing was found.
  - The name says "This Page", but from a non-WordPress document it silently checks the site's home page. The chooser does not say so.

### Check the Whole Site...

- How to reach it: Alt+T, WordPress submenu, then W. No WordPress key.
- Site: the front document's site, otherwise the chooser (titled "Check the Whole Site").
- What happens: every published page and post is read on a background task, with no spoken progress while it reads. If none are found, it says "{site} has no published pages or posts to check."
- How thorough: when axe-core and a browser are available, a chooser titled "Check the Whole Site" opens with the list "&How thorough:".
  - The rows are "Your content only: fast, N pages" and "Your content and the visitor's view with axe-core: slower, loads every page in a hidden browser".
  - Its F1 says "The visitor's view also checks the theme, menus and footer, the way Check This Page does. Neither sends anything anywhere."
  - Without axe-core or a browser, the content-only check runs without asking.
- Progress for the visitor's view: after each 10 pages, "Checked 10 of 42 pages on {site}." If it fails partway: "The visitor's view stopped: {reason} The report has your content checks."
- Announced after: for example "{site}: 47 problems on 17 of 42 pages. 52 in October 2026." or "{site}: no problems found on N pages." The comparison with the last check comes from local history.
- What opens: a list window titled "Check the Whole Site", only when there are problems.
  - The list "&Problems:".
  - "&Details:", which lists the page titles.
  - "&Pages..." opens a list window titled with the problem name.
    - Its list is "&Pages:".
    - "&Open" opens the page in the editor.
    - "Open on the &Site" opens it in the browser.
  - "Fix in &Bulk..." works like this:
    - For a problem it cannot fix itself, it says "QUILL cannot fix this one by itself: each needs your words or your eyes. Choose Pages to open them one at a time."
    - When nothing is left to fix, it says "There is nothing left to fix for that problem."
    - Otherwise a report titled "Fix in Bulk: Preview" opens, with "Before:" and "After:" lines for each page. Its F1 says "Every page that will change, and how. Nothing has been sent yet."
    - Then a confirmation titled "Fix in Bulk on {site}": "{fix label} on N pages on {site}? A copy of each page as it is now is kept on this computer, so Undo Site Fix can put them all back." Yes is "Fix N Pages".
  - Close.
  - The purpose (F1 only) is the summary. For a content-only check it adds "Only your content was checked; Check This Page shows the visitor's view."
- Announced after a bulk fix: "Fixed N pages on {site}. Undo Site Fix puts them back." It may add "N pages could not be changed; try those again later." and "N pages changed on the site since and were left alone." If nothing changed: "Nothing was changed on {site}."
- Undo: Tools > WordPress > Undo Site Fix. Ctrl+Z does nothing, because the change is on the site.
- Code: wordpress_site_check_commands.py, site_report.py, site_fixes.py.
- Review notes:
  - Access-key collision (GATE-14): the list label "&Problems:" and the "&Pages..." button both claim P in one window, so Alt+P cycles focus instead of pressing. check_access_keys.py cannot see this, because the labels are runtime arguments to the shared ListWindow.
  - Reading every page can take a long time with no progress sentence; only the visitor pass reports progress.
  - Fix in Bulk is two modals in a row, the preview report and then the confirmation. Closing the preview with Escape does not cancel; the confirmation still follows.

### Undo Site Fix...

- How to reach it: Alt+T, WordPress submenu, then U. No WordPress key.
- Site: the front document's site, otherwise the chooser (titled "Undo Site Fix").
- When there is nothing to undo: "There are no site fixes to undo on {site}."
- What opens: a list window titled "Undo Site Fix".
  - Its purpose (F1 only): "Fixes and replacements made across {site}, newest first. Undo puts each page back as it was, except pages changed on the site since."
  - The list "&Fixes:". Its F1 says "When, what was done, and how many pages it changed."
  - "&Undo..." works like this:
    - On a fix already undone, it says "That fix has already been put back."
    - Otherwise the window closes and QUILL re-reads the pages.
    - If every page changed since, it says "Every page in that fix has changed on {site} since, so nothing was put back. Previous Versions on each page still has the older text."
    - Otherwise a confirmation titled "Undo Site Fix on {site}" opens: "Put back N pages on {site} as they were before: {label}?" It can add "N pages changed on the site since and will be left alone: {titles}." Yes is "Put Back N Pages".
  - "&View..." opens a report titled "Site Fix" that lists the pages.
  - Close.
- Announced after: "Put back N pages on {site}." It may add "N could not be changed; try Undo again later."
- Cancel: Close or the confirmation's Cancel is silent.
- Code: wordpress_site_check_commands.py.
- Review notes:
  - Only covers Fix in Bulk and Site-wide Find and Replace. Manage > Bulk Edit has its own separate "Undo Bulk Edit", and Style Variations and Site Styles have "Put Back the Previous Look". That is three undo models for site-wide changes.
  - Fixes that were already undone stay in the list. It is not clear from the code whether their spoken rows say so.

### Site-wide Find and Replace...

- How to reach it: Alt+T, WordPress submenu, then F. No WordPress key.
- Site: the front document's site, otherwise the chooser (titled "Site-wide Find and Replace").
- What opens: three dialogs in turn, all titled "Site-wide Find and Replace".
  - First, a text box "&Find:". Its F1 says "The words to find in every page and post on the site, published or not."
  - Second, a text box "&Replace with:". Its F1 says "What to put in their place. Leave it empty to remove the words."
  - Third, a list "&How to match:". The rows are "Plain words, any case", "Plain words, matching case", "A pattern (regular expression), any case" and "A pattern (regular expression), matching case". Its F1 says "Plain words is right almost every time. A pattern is for the technical."
  - Each has OK (default) and Cancel.
- A bad pattern is spoken as the pattern error's sentence.
- Announced after the search:
  - "N matches on M pages on {site}."
  - Or "No matches for '{find}' on {site}."
  - Or "'{find}' is only inside block settings on {site}, which Find and Replace leaves alone unless you choose Include Block Settings."
- What opens: a list window titled "Site-wide Find and Replace".
  - Its purpose (F1 only): "Every match for '{find}' on {site}, with its sentence. All are included to start with."
  - The list "&Matches:". Each row reads "Included: {title}: {context}" or "Skipped: ...".
  - "&Include or Skip" toggles the selected match.
  - "Include &All" and "S&kip All" set every match.
  - "Include &Block Settings" appears only when matches inside block comments were hidden. Its F1 warns that changing those can break a block.
  - "&Replace...":
    - With nothing included, it says "Nothing is included, so nothing was replaced."
    - Otherwise a confirmation titled "Replace on {site}" opens: "Replace N matches of '{find}' with '{replace}' on M pages on {site}? A copy of each page as it is now is kept on this computer, so Undo Site Fix can put them all back." Yes is "Replace in M Pages".
  - Close.
- Announced after: "Changed N pages on {site}. Undo Site Fix puts them back." It may add the failed and skipped tails described under Check the Whole Site.
- Undo: Tools > WordPress > Undo Site Fix.
- Cancel: Cancel on any of the three questions ends silently.
- Code: wordpress_find_replace_commands.py.
- Review notes:
  - Grammar: the confirmation always says "matches", so one match reads "Replace 1 matches of ...".
  - It takes three modal steps before any search. A single dialog with Find, Replace with, Match case and Pattern controls would be faster and closer to Word's Replace.
  - Toggling a match does not say the new state, but the row text changes ("Included" or "Skipped" first), which the list re-reads. That is fine.

### Write an Accessibility Statement...

- How to reach it: Alt+T, WordPress submenu, then A. No WordPress key.
- Site: the front document's site, otherwise the chooser (titled "Write an Accessibility Statement").
- What opens: after it reads the admin email in the background (only administrators can), a text dialog titled "Write an Accessibility Statement" with the box "&Contact:", prefilled with that email when it could be read. Its F1 says "How a visitor reaches you about a problem: an email address, a phone number or a contact page. The site's admin email is offered when your account can see it." OK and Cancel.
- What happens: a new local page draft (slug "accessibility") opens in the editor. It is built from the site name, the contact and the last whole-site check result.
- Announced after: "Accessibility statement draft for {site} is open. It is yours to edit; nothing is sent until you choose Save Draft to Site or Publish."
- Cancel: silent.
- Without permission: non-administrators just get an empty Contact box. There is no sentence saying why.
- Code: wordpress_check_commands.py, site_report.py.
- Review notes:
  - The draft is Markdown or HTML according to the format last chosen in New Page or New Post (self._last_format), not a choice offered here.
  - Leaving the contact empty and pressing OK still makes a statement with an empty contact. No check is made.

### Palette Report

- How to reach it: Alt+T, WordPress submenu, then L. No WordPress key. The title has no "...", yet it opens a window.
- Site: the front document's site, otherwise the chooser (titled "Palette Report").
- Announced after: "{theme} on {site}: N pairings, M below the WCAG AA minimum for body text." If it cannot read a palette: "QUILL could not read a colour palette from {site}'s theme."
- What opens: a report titled "Palette Report". The summary comes first, then every colour on every background with its ratio. Its F1 says "Every colour in the theme's palette on every background, with its contrast ratio. Body text needs 4.5 to 1; large text 3 to 1."
- Code: wordpress_check_commands.py, contrast.py.
- Review notes:
  - The title has no ellipsis but opens a report. That is inconsistent with the other rows.
  - A classic theme silently gives "could not read a colour palette", with no hint that block themes are needed. Design > Style Variations does explain this.
  - The same palette data is in Design > Style Variations and in Manage > Previous Looks > Palette Report. That is three doors to one report.

### In Short...

- How to reach it: Alt+T, WordPress submenu, then S. No WordPress key.
- Document-only: dimmed outside a WordPress document. Reached anyway, it speaks the generic NOT_WORDPRESS sentence.
- Refusals:
  - "AI help is not available in this window."
  - "There is nothing to summarise yet."
  - The editor's own AI gates speak for themselves: AI switched off, agreement not accepted, or a connection that cannot do text.
- What happens: up to 12,000 characters of the page's text go to the chosen AI with no confirmation step. The summary is put at the top of the document, the caret moves to the start, and a "before AI" version is kept locally.
- Announced after: "In Short is at the top of the page. Edit it like any paragraph; Undo takes it out." If the AI returns nothing: "The AI sent back nothing to use. Nothing was changed." AI errors are spoken as they come.
- Undo: Ctrl+Z, as the announcement says. The change is made by selecting the whole buffer and writing new text (host.replace_text). File > WordPress > Previous Versions also has the "before AI" copy.
- Code: wordpress_check_commands.py.
- Review notes:
  - It sends page text to AI with no "this will send N words to {AI}" confirmation. Visual Review asks first; this does not.
  - The trailing "..." suggests a dialog, but none opens.
  - It is a content-writing command, not site upkeep. It sits oddly in Tools beside site checks.

### Media Library...

- How to reach it: Alt+T, WordPress submenu, then B. WordPress key, then M.
- What opens: the WordPress Workbench at the current site's "Media" node. workbench_door("wordpress.media_library") always opens it. The old Media Library list window below that line in wordpress_media_library.py cannot be reached from here.
- With no site connected: the Workbench opens at Start. There is no "Connect a WordPress site first." and no Connect flow, unlike every non-door row.
- Code: wordpress_media_library.py, wordpress_workbench_window.py, workbench_tree.py (_DOORS).
- Review notes:
  - The code comment "the developer flag sends this door to the WordPress Workbench" is stale. There is no flag check.
  - Access letter B, but the layer key is M. WordPress key, then B, opens View > WordPress Blocks instead.

### Alt Text Review...

- How to reach it: Alt+T, WordPress submenu, then X. WordPress key, then X. This is the one Tools row whose access letter and layer key agree.
- Document-only: dimmed outside a WordPress document. Reached anyway, it speaks the generic NOT_WORDPRESS sentence.
- When there are no pictures: "This document has no pictures."
- What opens: a list window titled "Alt Text Review".
  - Its purpose (F1 only): "Every picture in this document with its alternative text: N pictures, M to look at. Empty, file-name-like and very long alternative text are marked."
  - The list "&Pictures:".
  - "&Details:" shows "Picture N: source", "Alternative text: ..." and either "Problem: ..." or "Decorative".
  - "&Edit..." opens a multiline text dialog titled "Alternative Text: {name}" with the box "&Alternative text:". Its F1 says "What this picture contributes here, for someone using a screen reader. If a person is shown and the page does not name them, add the name if it matters. Nothing changes until you choose OK."
  - "Mark Decorati&ve" empties the alt text on purpose.
  - "&Suggest..." asks the AI and then opens the same Alternative Text dialog prefilled. On OK it says "Alternative text set for picture N."
  - "&Go to Picture" closes the window with the caret on the picture.
  - Close.
- If the picture moved or was removed while the window was open: "That picture has moved or gone from the document."
- Undo: each Edit or Mark Decorative rewrites the whole buffer (host.replace_text), so each one is a separate whole-document edit for Ctrl+Z.
- Code: wordpress_image_commands.py, media_alt.py.
- Review notes:
  - Edit and Mark Decorative speak nothing afterward; only the row text changes. Suggest does announce. That is inconsistent.
  - The Alternative Text box is multiline, so Enter adds a new line instead of pressing OK. The user must Tab to OK.

### Alt Text for the Whole Library...

- How to reach it: Alt+T, WordPress submenu, then R. No WordPress key.
- Site: the front document's site, otherwise the chooser (titled "Alt Text for the Whole Library").
- Without permission:
  - "Your account on {site} is a {role}, which cannot change pictures in the Media Library."
  - Without the media route: "{site} does not offer its Media Library to QUILL."
- When nothing is missing: "Every picture in {site}'s Media Library has alternative text."
- What opens: a list window titled "Alt Text for the Whole Library, {site}".
  - Its purpose (F1 only) says how many pictures lack alt text and that every batch of them is saved together, with the rest saved on close.
  - The list "&Pictures:". Enter writes. Its F1 says "Each picture's name, and whether its alternative text is written, saved, or still missing. Enter writes it."
  - "&Details:".
  - "&Write..." opens a multiline dialog titled "Alternative Text: {name}". Its F1 says "What this picture shows, for someone using a screen reader. This becomes the library's default; each page can still say what it means there."
  - "&Suggest..." works the same way. On OK it says "Alternative text written for {name}. It is saved with the next batch."
  - "Save &Now". With nothing waiting it says "Nothing is waiting to be saved."
  - Close.
- Announced after each save: "N descriptions saved on {site}." It may add "N could not be saved; {site} refused them, so try those again."
- Cancel: closing the window saves whatever is still waiting. This is not a discard.
- Code: wordpress_picture_edit_commands.py, media_edit.py.
- Review notes:
  - Close saves. That is good for a long session, but Escape (usually "cancel") silently sends pending descriptions to the site.
  - The save on close announces after the window is gone. That is fine.

### Visual Review...

- How to reach it: Alt+T, WordPress submenu, then V. No WordPress key.
- Not on the DOCUMENT_ONLY list, so it is never dimmed. It still needs a WordPress document and, reached without one, speaks the generic NOT_WORDPRESS sentence.
- Refusal when the page is not published: "Visual Review looks at the published page, and this is not published on {site} yet. Publish it first. A draft opens only for someone signed in to WordPress in a browser, so QUILL cannot capture it."
- What happens:
  - QUILL says "Capturing the desktop and phone views of {url}." and captures the page on this computer.
  - A confirmation titled "Visual Review" then says exactly what would go to the AI (vr.consent_text). Yes is "Send for Review". Cancel says "Nothing was sent. The screenshots are in {folder}."
  - After Yes, the AI describes the page.
- What opens after: a report titled "Visual Review". It ends "This report is saved as text in {path}. After you Update the page, choose Visual Review again to review it again." Its F1 says "What a sighted visitor sees on the published page, on a desktop and a phone, then image by image. Each finding is labelled likely a problem, a design choice you may want, or worth checking."
- Code: wordpress_review_commands.py, visual_review.py, page_capture.py.
- Review notes:
  - It should be on DOCUMENT_ONLY (or work on the home page the way Check This Page does). Today it is enabled everywhere and refuses with a sentence that names File > WordPress rather than this command.
  - It is a good model of consent before sending; In Short and Ask the Site should match it.

### More Media > Upload Files...

- How to reach it: Alt+T, WordPress submenu, O for More Media, then U. WordPress key, then U.
- Site: the front document's site, otherwise the chooser (titled "Upload Files").
- What opens:
  - A standard Open dialog titled "Upload Files" that takes many files.
  - Then, for each file, a dialog titled "Upload: {name}". Its F1 says "What {site}'s Media Library keeps with this file. Upload sends the file and these details; Cancel skips this file and the others carry on."
  - For a picture, the controls in order:
    - "&Alternative text:" (multiline).
    - "&Suggest Alternative Text" (AI).
    - "&Decorative: it adds nothing a visitor needs" check box. Checking it disables the alt box.
    - "&Title:".
    - "&Caption:".
    - "Describe &Image...".
    - "Upload" (default) and "Cancel".
  - For any other file: Title, Caption, Upload and Cancel.
- Duplicates: a confirmation titled "Already in the Library": "{file} is already in {site}'s Media Library, as {title}. Use the one already there instead of uploading a second copy?" Yes is "Use the One There".
- Progress: "Uploading 2 of 5: {file}." or "Uploading {file} to {site}."
- Announced after:
  - "{file} uploaded to {site}." or "N of M files uploaded to {site}.", plus a count of files that were already there.
  - Or "Nothing was uploaded to {site}."
  - A file that cannot be read: "{file} could not be read: {reason}. The others carry on."
- Cancel: Cancel in the file picker is silent. Cancel in one file's details dialog skips only that file.
- Code: wordpress_media_upload.py, wordpress_media_dialogs.py.
- Review notes:
  - There is no way to cancel the whole batch from a details dialog. With 20 files, the user must Cancel 20 times.
  - Enter in the multiline Alt box adds a line instead of pressing Upload.

### More Media > Upload from Web Address...

- How to reach it: Alt+T, WordPress submenu, O, then W. No WordPress key.
- Site: the front document's site, otherwise the chooser (titled "Upload from Web Address").
- What opens: a text dialog titled "Upload from Web Address" with the box "&Address:". Its F1 says "The https:// address of a picture, sound, video or document. QUILL fetches it from that site onto this computer, then uploads it to {site}."
- Then: "Fetching the file from {host}." After that the same "Upload: {name}" details dialog and duplicate check as Upload Files run.
- Announced after: the same upload summary sentence. An address that cannot be used is spoken as its MediaDownloadError sentence.
- Cancel: an empty address or Cancel ends silently. Cancel in the details dialog says "Nothing was uploaded to {site}."
- Code: wordpress_media_upload.py, media_tools.py.

### More Media > Paste Image

- How to reach it: Alt+T, WordPress submenu, O, then P. No WordPress key.
- Not on the DOCUMENT_ONLY list, so it is always enabled. It needs a WordPress document and, reached without one, speaks the generic NOT_WORDPRESS sentence.
- Refusal: "There is no picture on the clipboard. Copy a picture first, then choose Paste Image."
- What opens: the picture dialog titled "Picture: Pasted picture", with these controls in order:
  - "&Alternative text:".
  - "&Suggest Alternative Text".
  - "&Decorative: it adds nothing a visitor needs".
  - "&Caption:".
  - "Display &width ({size}):".
  - "File si&ze:" (only when sizes are known).
  - "Use as &featured image".
  - "&Link to:".
  - "Describe &Image...".
  - "Insert" (default) and "Cancel".
- What happens: the picture is uploaded (with the duplicate check), and the markup is inserted at the caret.
- Announced after: "Picture inserted: {alt or file name}." On failure: "The picture was not uploaded. {problem}"
- Undo: Ctrl+Z removes the inserted markup. The uploaded file stays in the Media Library.
- Cancel: silent.
- Code: wordpress_media_upload.py, wordpress_item_dialogs.py.
- Review notes:
  - It is an insert-into-this-page command filed under Tools > More Media, while Insert has "Picture from This Computer". Paste Image belongs beside it, or in Edit.
  - It should be on DOCUMENT_ONLY.
  - No "..." even though a dialog opens.

### More Media > Upload a Large File...

- How to reach it: Alt+T, WordPress submenu, O, then L. No WordPress key.
- Site: the front document's site, otherwise the chooser (titled "Upload a Large File").
- What opens:
  - A file picker titled "Upload a Large File".
  - For a big file, after QUILL measures the site's space, a confirmation titled "Upload a Large File" with the ss.upload_warning text. Yes is "Upload". Cancel says "Nothing was uploaded."
  - Then "Uploading {file}, {size}, to {site}. A file this size can take a while; QUILL says when it is there."
- Announced after: "{file} is in {site}'s Media Library. Its address is on the clipboard."
- After the upload: a field dialog titled "Details of {title}". Its purpose: "What {site} says about the file. Cancel keeps what WordPress made from the file's name." The OK button is "Save Details". After saving: "Saved the details of {title} on {site}."
- Without permission: "Your account on {site} is a {role}, which cannot upload files." Without the route: "{site} does not offer its Media Library to QUILL."
- Code: wordpress_route_media.py, media_pieces.py, site_space.py.
- Review notes:
  - It puts the address on the clipboard without being asked, and Upload Files does not. That is inconsistent and overwrites the clipboard.
  - Having both "Upload Files" and "Upload a Large File" makes the user decide what "large" means. The code could choose for them.

### More Media > Regenerate Sizes...

- How to reach it: Alt+T, WordPress submenu, O, then R. No WordPress key.
- Site: the front document's site, otherwise the chooser.
- Refusals:
  - "{site} cannot remake a picture's sizes. That needs WordPress 6.9 or later."
  - "Your account on {site} is a {role}, which cannot change pictures in the Media Library."
  - "{site} has no pictures in its Media Library."
- What opens: a chooser titled "Regenerate Sizes" with the list "&Picture:". Its F1 explains it remakes the thumbnail, medium and large copies.
- Announced after: "{site} remade N sizes of {name}." or "{site} remade the sizes of {name}."
- Confirmation: none. It runs as soon as the picture is chosen.
- Cancel: silent.
- Code: wordpress_route_media.py.

### More Media > Make a Smaller Copy...

- How to reach it: Alt+T, WordPress submenu, O, then M. No WordPress key.
- What it works on:
  - In a WordPress document with the caret on a picture, it uses that picture. If the picture is not in the library: "This picture is not in {site}'s Media Library. Upload it first."
  - Otherwise a chooser titled "Make a Smaller Copy" opens with the list "&Picture:".
- What opens next:
  - A chooser "&Largest width:" (rows like "800 pixels wide"). If the picture is already small: "{name} is already N pixels wide or less."
  - A chooser "&Format:" (JPEG, WebP, PNG).
  - A confirmation titled "Make a Smaller Copy": "{name}. {report} The copy was made on this computer. Upload it to {site} as a new file? The original stays in the library." Yes is "Upload".
- Announced after: "Smaller copy uploaded to {site} as {file}. The original is still in the library." In a document it may instead say "Smaller copy uploaded to {site} and used here. The original is still in the library."
- Undo: when used in the document, Ctrl+Z restores the old address. The new file stays on the site.
- Code: wordpress_image_commands.py, media_tools.py.
- Review notes: three modals plus a confirmation for one shrink. A single dialog holding the width and format choices would halve the steps.

### More Media > Edit a Picture on the Site...

- How to reach it: Alt+T, WordPress submenu, O, then I. No WordPress key.
- What it works on: the picture at the caret in a WordPress document, otherwise a chooser titled "Edit a Picture on the Site" with the list "&Picture:".
- Refusals:
  - "{site} does not offer picture editing. It needs WordPress 5.5 or later; until then, make the change on this computer and upload the result."
  - "Your account on {site} is a {role}, which cannot edit pictures in the Media Library."
  - "{site} offers no edits QUILL can make to {name}."
- What opens:
  - A chooser titled "Edit {name}" with the list "&Edit:" (turn, flip, crop to a ratio).
  - A confirmation titled "Edit a Picture on the Site": "{edit}: {name}, on {site}? WordPress keeps the original and makes the edit a new picture in the library. The new picture is about W by H." Yes is "Make Edited Copy".
- Announced after: "Edited copy made on {site}: {name}, W by H. The original is unchanged." Then up to three more prompts follow in a row:
  - In a document, "Use the edited copy here, in place of the original?" (Yes is "Use It Here").
  - A "Regenerate Sizes" confirmation (Yes is "Regenerate Sizes").
  - When AI is on, Describe Image runs.
- Code: wordpress_picture_edit_commands.py, media_edit.py.
- Review notes: one command can chain up to five modals and several announcements. The follow-ups (Use here, Regenerate) could be check boxes in the first confirmation.

### More Media > Site Logo...

- How to reach it: Alt+T, WordPress submenu, O, then O. No WordPress key.
- Site: the front document's site, otherwise the chooser (titled "Site Logo").
- Refusals:
  - "Site Logo needs the Administrator role on {site}: changing the logo needs the manage_options permission, and your account does not have it."
  - "{site} does not use the standard site logo. Its theme uses a header image or a page builder's own logo, which belong to the theme's own controls."
- What opens: a list window titled "Site Logo: {site}".
  - The list "&Logo and icon:".
  - "From the &Library..." opens a chooser "&Image:".
  - "From a &File...".
  - "From the &Picture Maker...".
  - "Pre&view a Width..." asks "&Width in pixels:" and then runs Visual Review on the home page.
  - "&Restore Earlier..." opens a chooser "&Earlier logos and icons:". With nothing kept: "QUILL has not replaced a logo or icon on {site}."
  - Close.
- Confirmation for every replace: titled "Replace {Logo or Icon}": "Make {name} the {logo} on {site}? The current one stays in the Media Library, and Restore Earlier can put it back."
- Announced after: "The {logo} on {site} is now {name}." If it changed meanwhile: "Nothing was sent: the {logo} on {site} was changed since this window opened. Close it and open Site Logo again."
- Undo: Restore Earlier, inside this window.
- Code: wordpress_picture_commands.py.
- Review notes:
  - Access-key collision (GATE-14): the list label "&Logo and icon:" and the button "From the &Library..." both claim L in one window.
  - After a replace the list rows are not refreshed (the actions return None), so the window keeps showing the old logo until it is reopened.
  - The menu title "Site L&ogo" uses O, which is also the submenu's own letter (M&ore). That is harmless but means pressing O twice.

### More Media > Preview and Review...

- How to reach it: Alt+T, WordPress submenu, O, then E. No WordPress key.
- Not on the DOCUMENT_ONLY list, so it is always enabled. It needs a WordPress document and, reached without one, speaks the generic NOT_WORDPRESS sentence.
- Refusal when not published: a long sentence that starts "Preview and Review works on the published page. A draft's preview opens only for someone signed in to WordPress in a browser, and QUILL's application password works for the site's API, not for that sign-in, ..." (visual_review.PREVIEW_NEEDS_PUBLISHED).
- What opens:
  - A chooser titled "Preview and Review" with the list "&Preview a new width for:". The rows are "The picture {name}" for each picture, then "The site logo".
  - A text dialog "&Width in pixels:". A bad value gives "Type a width in pixels between 16 and 4000, such as 600."
  - Then the same capture, consent and report as Visual Review, with the report titled "Preview and Review".
- Code: wordpress_review_commands.py.
- Review notes:
  - The refusal sentence is about 60 words, far longer than the one-sentence rule the other commands follow.
  - It overlaps with Site Logo > Preview a Width.

### More Media > Captions for Video...

- How to reach it: Alt+T, WordPress submenu, O, then V. No WordPress key.
- Not on the DOCUMENT_ONLY list, so it is always enabled. It needs a WordPress document and otherwise speaks the generic NOT_WORDPRESS sentence.
- What opens:
  - A chooser titled "Captions for Video" with the list "&Video:". A video already in the document is preselected. With no videos: "There is no video in {site}'s Media Library yet. Upload a video first, then try again."
  - Then: "Making captions for {name} on this computer. This can take a few minutes; the review opens when it is done."
  - A multiline dialog titled "Review Captions" with the box "&Captions, one on each line with its time:". Its F1 explains how to correct cues, label speakers and add [applause]. A format error is spoken and the dialog opens again with the text kept.
- What happens: the WebVTT file is uploaded and wired to the video block, or a new video block is inserted at the caret.
- Announced after: "Captions uploaded to {site} and added to the video in this document. Visitors get them when you next Save Draft to Site or Publish." When no video block was found, it says "a new video block at the caret" instead. With no speech: "No speech was found in {name}, so there are no captions to make."
- Cancel: Cancel in Review Captions throws the transcription away with no sentence.
- Code: wordpress_listen_commands.py, listening.py.
- Review notes:
  - A Cancel after minutes of transcription is silent and loses the work. A "Discard the captions?" confirmation, or keeping a draft, would help.
  - It should be on DOCUMENT_ONLY.

### More Media > Transcript for Audio...

- How to reach it: Alt+T, WordPress submenu, O, then T. No WordPress key.
- Not on the DOCUMENT_ONLY list; it behaves the same way as Captions for Video.
- What opens:
  - A chooser titled "Transcript for Audio" with the list "&Audio file:".
  - The "Making a transcript for {name} on this computer..." sentence.
  - A multiline dialog titled "Review Transcript" with the box "&Transcript:".
  - A chooser titled "Insert Transcript" with the list "&Insert it:". The rows are "Folded under the player, as Read the transcript (recommended)" and "In full under the player".
- Announced after: "Transcript of {name} added under its player." or "... added at the caret, under a new player." With no speech: "No speech was found in {name}, so there is no transcript."
- Undo: Ctrl+Z removes the inserted text.
- Cancel: silent at every step. The transcription is lost.
- Code: wordpress_listen_commands.py.

### More Media > Make a Listening Version...

- How to reach it: Alt+T, WordPress submenu, O, then N. No WordPress key.
- Document-only: dimmed outside a WordPress document. Reached anyway, it speaks the generic NOT_WORDPRESS sentence.
- Refusal: "There is nothing to read yet. Write the {page or post} first, then make its listening version."
- Confirmation, only when one exists already: titled "Make a Listening Version". The message is "The listening version is up to date with this {noun}. Make it again anyway?" or "The listening version is out of date: ... Make it again? The new recording replaces the old one at the top." Yes is "Make Again".
- What happens: "Recording the listening version on this computer with your Read Aloud voice. This can take a few minutes." Then the MP3 is uploaded to the site and an audio block goes at the top of the document.
- Announced after: "Listening version uploaded to {site}, N minutes. It is at the top of the {noun}, labelled {label}."
- Undo: Ctrl+Z on the whole-buffer replace takes the block out. The MP3 stays in the Media Library.
- Code: wordpress_listen_pages.py.
- Review notes: the first time, it uploads a file to the site with no confirmation at all; only a remake asks.

### More Media > Name Embeds

- How to reach it: Alt+T, WordPress submenu, O, then B. No WordPress key.
- Document-only: dimmed outside a WordPress document. Reached anyway, it speaks the generic NOT_WORDPRESS sentence.
- Refusals: "This document has no embeds to name." and "Every embed in this document already has a caption."
- What happens: QUILL asks the site's oEmbed service what each embed is and adds captions in the document.
- What opens: a report titled "Name Embeds" that starts "N of M embeds named." with a line for each embed. Its F1 says "What each embedded link is, as the site's oEmbed service describes it, and whether a caption was added. Captions go to the site with your next send."
- Undo: Ctrl+Z on the whole-buffer replace.
- Code: wordpress_listen_pages.py.
- Review notes:
  - It edits the document with no preview or confirmation; the report comes after the fact.
  - It is a this-page command filed under media upkeep.

### More Media > Publish a Document as a Page...

- How to reach it: Alt+T, WordPress submenu, O, then D. No WordPress key.
- Site: the front document's site, otherwise the chooser.
- What opens:
  - A file picker titled "Publish a Document as a Page".
  - A text dialog with the box "Page &title:". Its F1 says "The new page's title. The document is converted on this computer, the original is uploaded to the Media Library, and the page opens as a draft linked to it."
  - Then: "Converting {file} on this computer."
  - For a scanned file, a confirmation: "{file} has no readable text: it looks scanned. Read its pages with OCR on this computer? Nothing is uploaded to read them." Yes is "Read the Pages".
  - If the file is already in the library: "{file} is already in {site}'s Media Library. Use the one already there? Cancel uploads a second copy." Yes is "Use That One".
- Announced after: "{file} is in {site}'s Media Library, and its text is open as a new page draft. Nothing is published until you choose Publish." With no readable text: "{file} has no text QUILL could read, so there is nothing to make a page from. Nothing was uploaded."
- Code: wordpress_listen_pages.py.
- Review notes:
  - The name says "Publish", but it uploads the original and opens a draft. The menu name overpromises.
  - In the duplicate prompt, Cancel (and Escape) means "upload a second copy". Cancel starts an action instead of stopping one, which is backwards for a keyboard user.
  - The original file is uploaded to the site with no confirmation.

### Comments...

- How to reach it: Alt+T, WordPress submenu, then C. No WordPress key.
- What opens: the WordPress Workbench at the current site's Comments > Waiting node ("comments_waiting"). cmd_comments() runs with status "hold" from the menu, so the door always fires.
- Code: wordpress_admin_commands.py, workbench_tree.py.
- Review notes: the legacy comments window under this door is unreachable from the menu, though cmd_comments(status=...) can still be called with another status from elsewhere.

### Categories and Tags...

- How to reach it: Alt+T, WordPress submenu, then G. No WordPress key.
- What opens: the Workbench at the current site's "Categories" node.
- Code: wordpress_terms_commands.py.

### Menus...

- How to reach it: Alt+T, WordPress submenu, then N. No WordPress key.
- What opens: the Workbench at "Menus and Navigation". The legacy window stays reachable only when cmd_menus is given a page or menu id from elsewhere.
- Code: wordpress_menu_commands.py.

### Menu History...

- How to reach it: Alt+T, WordPress submenu, then H. No WordPress key.
- Site: the front document's site, otherwise the chooser (titled "Menu History").
- Refusals:
  - "{site} does not offer its menus to QUILL."
  - "Your account on {site} is a {role}, which cannot change menus."
  - "{site} has no menus or Navigation blocks."
- What opens:
  - With more than one menu, a chooser titled "Menu History" with the list "&Menu:".
  - Then a list window titled "Menu History".
    - Its purpose (F1 only): "Earlier versions of {menu}, newest first."
    - The list "&Versions:".
    - "&Details:" shows the items then and the items removed since.
    - "&Bring Back Removed Items...".
    - "&Restore This Version..." (Navigation blocks only).
    - Close.
- When there are no versions: for a classic menu, "{menu} has no earlier versions yet. WordPress keeps none for a classic menu, so QUILL keeps one each time Menu History, the Menus window or the Workbench's Earlier Versions reads it; a change made after this can be undone." Otherwise "{menu} has no earlier versions on {site}."
- Confirmations:
  - "Bring Back Menu Items": "Add {names} back to {menu} on {site}, at the end?" Yes is "Bring Back".
  - "Restore This Version": "Make {menu} on {site} exactly as it was on {when}? Its current version is kept in this history." Yes is "Restore".
- Announced after: "N items back in {menu}, at the end." and "{menu} is as it was on {when}." When nothing is missing: "Every item from then is still in {menu}."
- Code: wordpress_route_history.py.
- Review notes:
  - "1 items back" grammar.
  - Menus now opens the Workbench, but Menu History is a separate legacy window beside it, and the Workbench has its own "Earlier Versions". That is two histories reached two ways.
  - The classic-menu empty message is about 50 words.

### Site Check

- How to reach it: Alt+T, WordPress submenu, then K. No WordPress key.
- What opens: the Workbench at the current site's "Site Health" node.
- Code: wordpress_manage_commands.py.
- Review notes: the name "Site Check" sits beside three other "Check" rows but means Site Health. Calling the row "Site Health" would match the node it opens and WordPress's own name.

### Site Settings...

- How to reach it: Alt+T, WordPress submenu, then E. No WordPress key.
- What opens: the Workbench at the current site's "Settings" node.
- Code: wordpress_manage_commands.py.

### Design > Style Variations...

- How to reach it: Alt+T, WordPress submenu, D for Design, then V. No WordPress key.
- Site: the front document's site, otherwise the chooser (titled "Style Variations").
- Refusals:
  - "{site} has no style variations to offer. They come with block themes, in WordPress 6.2 or later."
  - "Your account on {site} is a {role}, which cannot change the site's look."
  - "{theme} on {site} is not a block theme, so its look is set in the theme's own options rather than through WordPress."
  - "{theme} on {site} has no style variations."
- What opens: a list window titled "Style Variations, {site}".
  - The list "&Variations:". Each row reads "{name}: {how many pairings are too faint}".
  - "&Details:" holds the palette report lines.
  - "&Apply...".
  - "Put &Back the Previous Look...".
  - Close.
- Confirmations:
  - "Apply Style Variation": "Change the look of {site} to {name}? Visitors see it at once. QUILL keeps the current look on this computer, so Put Back the Previous Look can restore it." Yes is "Apply {name}".
  - "Put Back the Previous Look": "Put back the look {site} had before {reason}, kept {when}?" Yes is "Put Back". With nothing kept: "QUILL has no earlier look kept for {site}."
- Announced after: "{name} applied on {site}. Put Back the Previous Look restores the old one." and "The previous look is back on {site}."
- Undo: Put Back the Previous Look (a local copy). Manage > Previous Looks uses the site's own revisions.
- Code: wordpress_look_commands.py, site_styles.py.

### Design > Site Styles...

- How to reach it: Alt+T, WordPress submenu, D, then S. No WordPress key.
- Site and refusals: as Style Variations, with "{site} does not offer its site styles. They come with block themes, in WordPress 5.9 or later." and "{theme} on {site} sets no colours or font sizes."
- What opens: a list window titled "Site Styles, {site}".
  - The list "&Styles:". Each colour row includes its contrast.
  - "&Change..." opens a text dialog titled "Change {name}" with the box "&Colour:" or "&Size:". A bad value is spoken as its error sentence.
  - "Put &Back the Previous Look...".
  - Close.
- Confirmation: "Change Site Style". It says "Change {name} on {site} from {old} to {new}? {contrast sentence}. Visitors see it at once." or the font-size version. Yes is "Change {name}".
- Announced after: "{name} changed on {site}."
- Code: wordpress_look_commands.py.
- Review notes:
  - The list rows update to the new value as soon as Yes is pressed, before the save comes back. A failure then leaves the list showing a value the site does not have.
  - It is good that the confirmation says the contrast before anything is saved.

### Plugin Extras > Events Coming Up...

- How to reach it: Alt+T, WordPress submenu, I for Plugin Extras, then C. No WordPress key.
- Site: the front document's site, otherwise a chooser titled "Coming Up" (not "Events Coming Up").
- Refusals: "{site} does not have The Events Calendar, so there are no events for QUILL." and "Nothing is coming up on {site}."
- What opens: a list window titled "Coming Up, {site}".
  - The list "&Events:". Enter opens the event.
  - "&Open".
  - "Open on &Site".
  - Close.
- Code: wordpress_plugin_commands.py, events.py.
- Review notes: the chooser and window are titled "Coming Up", the same as Your Sites > Coming Up, which is a different list (scheduled posts across sites). By ear the two cannot be told apart.

### Plugin Extras > New Event...

- How to reach it: Alt+T, WordPress submenu, I, then E. No WordPress key.
- Refusals: the no-Events-Calendar sentence, and "Your account on {site} is a {role}, which cannot add events."
- What opens: a field dialog titled "New Event". Its purpose: "A new event on {site}, made as a draft. Nothing is public yet."
  - "&Name:".
  - "&Starts:" ("When it starts, such as 2026-11-21 10:00.").
  - "&Ends:".
  - "&Venue:" (a choice: "No venue" and the site's venues).
  - The OK button is "Make Draft".
- Validation (each is spoken and makes nothing):
  - "An event needs a name. Nothing was made."
  - A date parse error, followed by " Nothing was made."
  - "The event ends before it starts. Nothing was made."
- Announced after: "Event {title} made as a draft on {site}." The event then opens in the editor.
- Code: wordpress_plugin_commands.py.
- Review notes:
  - Dates are free text in one fixed format. A wrong guess closes the dialog and loses everything typed. Validation should keep the dialog open.

### Plugin Extras > Shop Orders...

- How to reach it: Alt+T, WordPress submenu, I, then O. No WordPress key.
- Refusals:
  - "{site} does not have WooCommerce, so it has no shop orders."
  - "Your account on {site} is a {role}, which cannot read the shop's orders."
  - "{site} has no orders yet."
- What opens: a list window titled "Shop Orders, {site}".
  - Its purpose says it is read only.
  - The list "&Orders:".
  - "&Details:".
  - "&Copy Order...".
  - Close.
- Confirmation: "Copy Order": "Copy order {n} to the clipboard? It includes the customer's name and shipping address, which then go wherever you paste them." Yes is "Copy Order".
- Announced after: "Order {n} copied."
- Code: wordpress_shop_commands.py.
- Review notes: a confirmation before a clipboard copy is unusual, but it is justified by the personal data, and it is clearly worded.

### Manage > Users...

- How to reach it: Alt+T, WordPress submenu, M for Manage, then U. No WordPress key.
- What opens: the Workbench at the current site's "Users" node.
- Code: wordpress_people_commands.py.

### Manage > Application Passwords...

- How to reach it: Alt+T, WordPress submenu, M, then A. No WordPress key.
- What opens: the Workbench at "Application Passwords".
- Code: wordpress_people_commands.py.

### Manage > Plugins...

- How to reach it: Alt+T, WordPress submenu, M, then L. No WordPress key.
- What opens: the Workbench at "Plugins".
- Code: wordpress_manage_commands.py.

### Manage > Themes...

- How to reach it: Alt+T, WordPress submenu, M, then H. No WordPress key.
- What opens: the Workbench at "Themes".
- Code: wordpress_manage_commands.py.

### Manage > Fonts...

- How to reach it: Alt+T, WordPress submenu, M, then F. No WordPress key.
- What opens: the Workbench at "Fonts".
- Code: wordpress_design_commands.py.

### Manage > Synced Patterns...

- How to reach it: Alt+T, WordPress submenu, M, then Y. No WordPress key.
- What opens: the Workbench at "Patterns".
- Code: wordpress_design_commands.py.
- Review notes: the menu says "Synced Patterns", but the node is "Patterns". Whether the Workbench filters it to synced patterns is not in this code.

### Manage > Widgets...

- How to reach it: Alt+T, WordPress submenu, M, then W. No WordPress key.
- What opens: the Workbench at "Widgets and Sidebars".
- Code: wordpress_menu_commands.py.

### Manage > Site Map...

- How to reach it: Alt+T, WordPress submenu, M, then P. No WordPress key.
- What opens: the Workbench at "Pages".
- Code: wordpress_structure_commands.py.
- Review notes: "Site Map" opens a node named "Pages", while Page Order (two rows down) is a separate legacy tree window over the same pages.

### Manage > Template Outline

- How to reach it: Alt+T, WordPress submenu, M, then O. No WordPress key.
- Site: the front document's site, otherwise the chooser.
- Refusal: "{site} uses a classic theme, so it has no block templates. Its sidebars and footer are in Widgets."
- What opens: a report titled "Template Outline, {site}" with the templates and parts and their blocks, indented by depth. When opened from a document, that document's template comes first. Its F1 says "The theme's templates and template parts, with the blocks in each, indented by depth. They explain things on a page that are not in the page. Change them in the site editor."
- Code: wordpress_structure_commands.py, site_structure.py.
- Review notes: there is no "..." although a window opens. Indentation by depth is hard to hear in a plain text box; a tree, or "level N" prefixes, would carry the structure.

### Manage > Bulk Edit...

- How to reach it: Alt+T, WordPress submenu, M, then B. No WordPress key.
- Site: the front document's site, otherwise the chooser (titled "Bulk Edit").
- What opens:
  - A chooser titled "Bulk Edit" with the list "&Edit:" and the rows "Posts" and "Pages".
  - Then a list window titled "Bulk Edit Posts, {site}" (or Pages).
    - Its purpose (F1 only): "Select the posts to change, then Change. Every change is one confirmation and one request, and Undo Bulk Edit puts the items back."
    - The list "&Posts:" or "&Pages:". Selected rows start "Selected, ".
    - "&Select" toggles the row and speaks nothing.
    - "Select &All" toggles all and says "N posts selected."
    - "&Change..." opens a chooser titled "Change" with "&Change:", then a chooser titled after the field with "&To:". With nothing selected it says "Select the posts to change first, with Select."
    - "&Undo Bulk Edit...".
    - Close.
- Confirmations:
  - "Bulk Edit": "{field}: {value}, for N posts on {site}? Undo Bulk Edit can put them back." Yes is "Change N".
  - "Undo Bulk Edit": "Put N items on {site} back as they were?" Yes is "Undo". With nothing to undo: "There is no bulk edit on {site} to undo."
- Announced after: "N posts changed on {site}." and "N items put back on {site}."
- Without permission:
  - "Your account on {site} is a {role}, which cannot edit other people's posts."
  - This edit_others_posts check is applied to Pages too.
- Undo: Undo Bulk Edit inside this window. It keeps only the last edit per site.
- Code: wordpress_structure_commands.py.
- Review notes:
  - The list rows are not refreshed after Change, so status and author still read the old values.
  - "1 posts" grammar.
  - The Workbench has its own batch editing (Phases 7 to 10), so this window duplicates it.

### Manage > Page Order...

- How to reach it: Alt+T, WordPress submenu, M, then R. No WordPress key.
- Without permission: "Your account on {site} is a {role}, which cannot arrange pages." When there are no pages: "{site} has no pages yet."
- What opens: a list window titled "Page Order, {site}".
  - The list "&Pages:" (each title with its level and place).
  - "Move &Up".
  - "Move &Down".
  - "Move &In".
  - "Move &Out".
  - "Op&en".
  - Close.
- What happens: each move saves to the site at once with no confirmation, then speaks the move sentence from site_structure.page_move. A move that cannot be made says "{title} cannot move that way."
- Undo: none. There is no undo for a page move.
- Code: wordpress_structure_commands.py.
- Review notes:
  - Moves go live on the site with no confirmation and no undo, so a mistaken Alt+I re-parents a page in public menus.
  - Focus returns to the list after a move, but because the rows are rebuilt the selection stays at the old index, not on the page that moved. The row the user hears next may be a different page.

### Manage > Previous Looks...

- How to reach it: Alt+T, WordPress submenu, M, then K. No WordPress key.
- Refusals:
  - "{site} keeps no history of its site styles. That needs a block theme and WordPress 6.3 or later."
  - "Your account on {site} is a {role}, which cannot change the site's styles."
  - "{site}'s theme has no site styles of its own, so it has no earlier looks."
  - "{site}'s styles have not been changed yet."
- What opens: a list window titled "Previous Looks".
  - The list "&Looks:".
  - "&Details:" holds the palette.
  - "&Palette Report..." opens a report titled "Palette Report".
  - "&Go Back to This Look...".
  - Close.
- Confirmation: "Go Back to This Look": "Make the look from {when} {site}'s current look? The look it has now is kept, so Previous Looks can bring it back." Yes is "Go Back".
- Announced after: "{site} has the look from {when} again."
- Code: wordpress_route_history.py.
- Review notes: the window title lacks the site name, unlike its siblings ("Style Variations, {site}").

### Manage > Space Used

- How to reach it: Alt+T, WordPress submenu, M, then S. No WordPress key.
- Refusals:
  - "{site} does not say how much space it uses. That needs WordPress 5.6 or later."
  - "Your account on {site} is a {role}, which cannot see how much space the site uses."
- Announced after: "{site} uses {size} altogether." or "{site} could not measure the space it uses."
- What opens: a report titled "Space Used" that starts "Space used on {site}:" with each part on its own line.
- Code: wordpress_route_media.py, site_space.py.
- Review notes: no "..." although a report opens. The total is announced and then repeated in the report.

### Manage > Download a Copy of the Site's Design...

- How to reach it: Alt+T, WordPress submenu, M, then D. No WordPress key.
- Refusals:
  - "{site} cannot export its design. Only a block theme on WordPress 5.9 or later can."
  - "Your account on {site} is a {role}, which cannot download the site's design."
- What opens: after the export, a Save As dialog titled "Download a Copy of the Site's Design" for zip files.
- Announced after: "A copy of {site}'s design is saved as {file}, {size}." Cancel says "Nothing was saved."
- Code: wordpress_route_media.py.

### Manage > AI Abilities...

- How to reach it: Alt+T, WordPress submenu, M, then T. No WordPress key.
- What opens: the Workbench at the current site's "Abilities" node.
- Code: wordpress_abilities_commands.py.
- Review notes:
  - The menu says "AI Abilities", but the node and the legacy window say "Abilities".
  - Ask the Site's refusal tells the user to "Turn them on one by one in Abilities", which now means a Workbench node. This code does not confirm that the Workbench node writes the same per-site choices (ability_choices).

### Manage > Ask the Site...

- How to reach it: Alt+T, WordPress submenu, M, then E. No WordPress key.
- Site: the front document's site, otherwise the chooser (titled "Ask the Site").
- Refusals:
  - "{site} offers no abilities for AI. That needs WordPress 6.9 or later, and a site or plugin that describes some."
  - "No ability of {site} is turned on. Turn them on one by one in Abilities, then ask again."
  - The AI-off gate speaks for itself.
- What opens: a multiline text dialog titled "Ask the Site, {site}" with the box "&Question:". Its F1 says "Ask about your site. The AI you chose in Choose Your AI may ask to use one of the abilities you turned on; QUILL asks you before it runs."
- Confirmation: when the AI plans to use an ability, "Run Ability" opens with ab.approval_message. Yes is "Run {ability}". Cancel says "Nothing was run on {site}."
- What opens after: a report titled "Ask the Site, {site}". Its F1 says "The AI's answer, then which of the site's abilities ran to get it."
- Cancel: an empty question or Cancel ends silently.
- Code: wordpress_abilities_commands.py, abilities.py.
- Review notes:
  - The question is sent to the AI with no consent step. Only running an ability asks.
  - The Question box is multiline, so Enter adds a line and Tab then Enter is needed to ask.

### Manage > Sign Out This Site...

- How to reach it: Alt+T, WordPress submenu, M, then I. No WordPress key.
- Site: always the chooser (titled "Sign Out This Site") when more than one site is connected, even inside a WordPress document. With one site, that site is used without asking.
- What opens: a chooser titled "Sign Out This Site" with the list "&After signing out:". The rows are "Remove {site} from QUILL" (selected) and "Keep {site} in the list, to connect again later". Its F1 says "Signing out revokes QUILL's application password on {site} itself and forgets it on this computer. Your local drafts are kept either way." OK (default) and Cancel.
- What happens: QUILL revokes exactly the password it signs in with (introspect) and forgets it here. With the Remove choice, it also removes the site from the list.
- Announced after: "Signed out of {site}: the password {name} is revoked on the site and forgotten here, and the site is removed from QUILL." or "... kept in your list." When the site cannot say which password QUILL used, it adds "The site did not say which password QUILL used, so revoke it in Application Passwords or the dashboard if you want it gone there too."
- Undo: none. Reconnecting needs a new application password.
- Cancel: silent.
- Code: wordpress_people_commands.py.
- Review notes:
  - It cannot be undone, and the only step is a two-row chooser whose preselected row is the more destructive one ("Remove"), with OK as the default. Enter twice (menu, then dialog) signs out and removes the site. There is no named confirmation, unlike every other destructive command here.
  - With one site there is no site chooser, so nothing on screen names the site before the chooser.
  - It calls self.api(profile) first, so on first use in a session it may announce "{site}: N comments waiting." just before signing out.

### Your Sites > Coming Up...

- How to reach it: Alt+T, WordPress submenu, Y for Your Sites, then U. No WordPress key.
- Site: every connected site at once. With none, it says "Connect a WordPress site first." and the Connect flow starts.
- Announced after:
  - "N items are scheduled on your N sites. The next is {title} on {site}, {when}."
  - Or "Nothing is scheduled on your site."
  - It may add "N sites did not answer."
- What opens: only when something is scheduled, a list window titled "Coming Up".
  - Its purpose (F1 only): "Everything scheduled on your sites, soonest first."
  - The list "&Scheduled:" (items, then "Did not answer: {site}" rows). Enter opens the item.
  - "&Open".
  - Close.
- Code: wordpress_route_archive.py, across_sites.py.
- Review notes:
  - Bug: Open or Enter on a "Did not answer: ..." row reads items[index] past the end of the list (open_it has no bounds check), which raises an exception instead of speaking.
  - "1 sites did not answer" grammar.
  - When every site fails and nothing is scheduled, no list opens, so the failed sites are named nowhere, unlike What Changed.

### Your Sites > What Changed on My Sites...

- How to reach it: Alt+T, WordPress submenu, Y, then W. No WordPress key.
- Site: every connected site.
- Announced after:
  - "N changes on M of your N sites."
  - Or, with one site, "N changes on your site since you last looked."
  - Or "Nothing new on your N sites since you last looked."
  - It may add "N sites did not answer."
- What opens: a list window titled "What Changed on My Sites".
  - Its purpose (F1 only): "What is new on your sites since you last looked here."
  - The list "&Changes:" (then "Did not answer:" rows).
  - "Open in &Browser". On a row with no page it says "That one has no page to open."
  - Close.
- Side effect: opening it marks every site that answered as looked at now, so the same changes do not show next time.
- Code: wordpress_route_archive.py, across_sites.py.
- Review notes:
  - The "looked at" mark is set before the user has read the list, so closing it by accident loses the changes.
  - Enter on a row does nothing (no on_enter), while Enter opens the item in Coming Up. The two sibling windows behave differently.

## QUILL Lite differences

QUILL Lite reaches every WordPress and Forms command QUILL has, through the same shared handlers: each Lite `cmd_wp_*` and `cmd_forms_*` method hands straight to the one `WordPressCommands` or `FormsCommands` object QUILL also uses, and both editors build their menus from the same two tables (`quill/core/wordpress/menu.py` and `quill/core/forms/menu.py`). A script check of every row in both tables found a Lite handler for each one, so no command is missing on either side. The differences are in how you reach things. Lite has no menu-route pass, so its labels never show an "(Alt+T, ...)" path and some submenus have no access letter at all. Lite's MDI windows change how the one Workbench behaves. And one feature gate (Form Payments) does not apply in Lite. The sections below cover only those differences. The commands themselves are described in the other sections.

### Where the rows sit in QUILL Lite

- How to reach it: the rows go where the tables put them in both editors. File > WordPress (submenu), the foot of Edit (Edit > WordPress submenu), the foot of View, the foot of Insert, the foot of Format (Format > WordPress submenu), and the foot of Tools (Tools > WordPress submenu, then Tools > Forms submenu). Forms adds File > New Form, Insert > Form Field, View > Form Outline, Format > Form Rules and Tools > Forms.
- In Lite's File menu, New Form comes straight after New Plain Text Document and File > WordPress comes after the Export rows. QUILL puts File > WordPress after Snapshots (`main_frame_menu.py`). Both are in File, but at a different point in the menu.
- The Tools menu tail order is the same in both: Tools > WordPress, then Tools > Forms, as the last two entries (`lite_placed_rows` WordPress first, then Forms; QUILL calls `_place_wordpress_rows` then `_place_forms_rows`).
- Practical Lite route: Tools > Forms is the last row of Tools and Tools > WordPress the second to last. Neither has a letter (see below), so the fastest way in is Alt+T, then Up Arrow once (Forms) or twice (WordPress), then Right Arrow. Edit > WordPress is the last row of Edit: Alt+E, Up Arrow, Right Arrow.
- Code: lite_window_wordpress.py, lite_window_forms.py, core/lite/commands.py, core/wordpress/menu.py, core/forms/menu.py.
- Review notes:
  - Lite's Tools menu has 30 entries, and the two submenus a WordPress user needs most are the last two, with no letter. That only works if the user knows that Up Arrow wraps to the bottom. No label says so.

### Access letters: what Lite has and QUILL computes

- Lite takes its letters straight from the tables, as written (`lite_window_menus.py` `_fill_menu`). A script walk of Lite's command table found no duplicate letters in File > WordPress, Tools > WordPress, Tools > Forms, Insert, View or Format.
- Tools > WordPress: no letter in Lite. The table title is plain "WordPress" because no letter of the name is free in Lite's Tools: Say &Word Summary holds W, and O, R, D, P, E and S are all held too. The module docstring in `wordpress/menu.py` says the same.
- Tools > Forms: no letter in Lite. F (File Encoding), O (Sound Scheme), R (Read-Only Guard), M (Manage Abbreviations) and S (Spelling) are all held (`forms/menu.py` docstring, confirmed by the table walk).
- Edit > WordPress: also no letter in Lite (the Edit table title is plain "WordPress").
- Format > WordPress: "Word&Press", so P.
- File > WordPress: "&WordPress", so W in Lite's File.
- File > New Form: "New For&m...", so M. Lite's Close Window (MDI) gives up M; its route is Ctrl+F4.
- Format > Form Rules: "For&m Rules...", so M. Lite's Switch Document Mode gives up M; its route is Alt+Shift+F.
- View > Form Outline: "&Form Outline...", so F. Insert > Form Field: "Form &Field...", so F.
- Tools > WordPress > Open WordPress Workbench: no letter in either editor ("Every letter of its name is taken in this menu, so its key is the WordPress layer's H"). It is the first row of the submenu, so Enter right after the submenu opens selects it.
- In QUILL, `menu_routes.py` runs over the built menu bar. It gives every submenu without a letter a free one, appending "(&Z)" when none of its own letters is free. It also appends the full Alt path to every enabled row that has no shortcut, for example "Check This Form... (Alt+T, x, C)". So in QUILL, Tools > Forms and Tools > WordPress get a letter whenever QUILL's Tools menu has one free. The exact letter depends on QUILL's whole Tools menu at runtime and was not computed for this walkthrough.
- QUILL's pass skips disabled rows, so it re-runs on every refresh (`_reapply_menu_routes`). A document-only row that becomes enabled gains its route then.
- Review notes:
  - This is the biggest Lite-versus-QUILL gap in this area. In QUILL every keyless Forms and WordPress row says its Alt path aloud. In Lite the same row says nothing, and its parent submenu has no letter to type. The house rule that every enabled item shows a keyboard route is met in QUILL and not in Lite. That is the permitted direction (Lite behind QUILL), but it is a real cost on every visit.
  - The layer letters and the menu letters disagree for eight rows. The table comment says "A row's own access letter wherever it is free, so the menu teaches the key", but File > WordPress has New &Page (layer G), P&ublish (layer P), Co&mpare (layer C), Switc&h Site (layer S), &Sites (layer Shift+S) and This Post in the Wor&kbench (layer Shift+H). Tools > WordPress has Check Before &Publishing (layer K) and Media Li&brary (layer M). The menu does not teach the layer key for these. Because the bracketed chord is in the label, you hear both and have to ignore one. This is the same in both editors.

### The WordPress key layer (shared, with three small differences)

- How to reach it: Ctrl+Alt+Shift+Grave, release, then one letter, in both editors. The prefix and the letters come from `wordpress/menu.py` `LAYER_KEYS` plus Forms' F (`forms/menu.py` `LAYER_KEYS`). The layer's state machine is `quill/core/wordpress/keys.py` `WordPressKeyLayer`, one implementation for both editors.
- Letters: A Connect a Site, B WordPress Blocks, C Compare with Site, D Save Draft to Site, E Schedule Publish, F Responses (Forms), G New Page, H Open WordPress Workbench, I Open on Site, K Check Before Publishing, L Open Local Draft, M Media Library, N New Post, O Open Page or Post, P Publish or Update, R Properties, S Switch Site, Shift+S Sites, T Move to Trash, U Upload Files, V Previous Versions, W Open by Web Address, X Alt Text Review, Y Copy Address, Shift+H This Post in the Workbench.
- Announced after: "WordPress keys" when the prefix is pressed. Escape: "Left WordPress keys". A letter with no command: "No WordPress command on Q." (with the key spelled). A key with no character (an arrow, Tab, Enter) leaves the layer silently and goes on to the editor. The layer times out after 4 seconds (`TIMEOUT_SECONDS`), and a key pressed after that is typed normally.
- How each editor sees the key:
  - QUILL checks it in the frame's char hook (`main_frame.py` `_wordpress_key_event`), and only while focus is in the document surface.
  - Lite checks it first thing in the editor control's key-down handler (`lite_window_typing.py` `_on_key_down`, then `_wordpress_key_down`). Both effectively answer only in the document.
- How each editor decides the layer is on:
  - QUILL needs the `core.wordpress` feature on, and steps aside when the user has moved the QUILL key onto the same chord ("the user put the QUILL key here; it wins").
  - Lite needs at least one `cmd_wp_` handler in the resolved command table ("the WordPress area is switched off: not our key, Forms' F or no"). Lite has no QUILL-key check.
- How each editor runs the command:
  - QUILL calls `_run_command(command_id)`.
  - Lite calls `run_unless_read_only(handler)`, so a layer key in Lite passes through the Read-Only Guard check. No WordPress or Forms handler is listed in `TEXT_CHANGING_HANDLERS`, though, so in practice the guard never refuses one.
- Both editors read the letters from the live keymap (`layer_from_bindings`), so moving a command in the Keyboard Manager moves its layer letter.
- Keyless: rows not in `LAYER_KEYS` have no chord and rely on menu letters and the Command Palette. `forms/menu.py` gives rule 9 as the reason for every Forms row except Responses.
- Code: core/wordpress/keys.py, lite_window_wordpress.py, main_frame_wordpress.py, lite_window_typing.py, lite_window_menus.py.
- Review notes:
  - Responses' label advertises a key that can be dead. If Forms is on and WordPress is off (separate features in QUILL, separate areas in Lite), both editors still show "Responses... (Ctrl+Alt+Shift+Grave, F)". The prefix is refused, though, because the layer belongs to WordPress. A Forms-only user is shown a chord that does nothing and is not told why.
  - In Lite, a layer command reached on a document under the Read-Only Guard runs anyway. Every Forms command that rewrites the document (Insert Form Field, Outline moves, Form Rules, Form Properties, Plain Language, Payments Setup) writes through `WriteText` on the control. Whether a read-only native edit control accepts that is not proven here; verify by hand. The menu route behaves the same way, since `_dispatch` also goes through `run_unless_read_only` and finds nothing to refuse.
  - The "WordPress keys" announcement is correct under GATE-13, because the prefix changes nothing on screen.

### Document-only dimming

- Both editors dim the rows in each table's `DOCUMENT_ONLY` set unless the right kind of document is in front.
  - WordPress rows: a document with a local WordPress copy (`local.copy_for_path`).
  - Forms rows: a path ending .qaf or .bfl (`is_form_path`).
- QUILL refreshes them from `_refresh_contextual_menu_items` (`_refresh_wordpress_menu_items`, `_refresh_forms_menu_items`). Lite refreshes them from `_sync_enabled_items` on every document change and on menu open.
- A dimmed row reached another way still runs: from the Command Palette, or in Lite from a layer key. Its handler then says why. For example: "Check This Form works in a form document, a .qaf file. Start one with New Form in the File menu, or open one."
- Not dimmed, by design: New Form, Insert Form Into Page, Responses and Draft a Form. Insert Form Into Page needs a WordPress page rather than a form, and says so: "Insert Form Into Page works in a WordPress page or post. Open one with File, WordPress, then try again."
- Code: lite_window_forms.py (`_sync_forms_items`), lite_window_wordpress.py (`_sync_wordpress_items`), main_frame_forms.py, main_frame_wordpress.py.
- Review notes:
  - Insert Form Into Page is enabled in every document, but it only works in a WordPress page. It could be dimmed by the WordPress `DOCUMENT_ONLY` test instead of always being enabled, and right now it is the only Tools > Forms row that is enabled in places it cannot work.
  - A form is recognised only by its file name. An unsaved buffer holding QAF text, or a form saved under another extension, dims every Forms row.

### Opening the WordPress Workbench from QUILL Lite

- How to reach it:
  - Tools > WordPress > Open WordPress Workbench (no letter; first row of the submenu), or WordPress key then H.
  - On a WordPress document: File > WordPress > This Post in the Workbench (Alt+F, W, K in Lite), or WordPress key then Shift+H.
  - In both editors several Tools > WordPress doors (Comments, Users, Plugins and others, `workbench_tree.py` `_DOORS`) open the Workbench at their node instead of a dialog.
- What opens: the same Workbench frame as in QUILL (`open_workbench`). There is only one per process (`_OPEN["wordpress"]`). Opening it again brings the existing frame forward, reloads the profiles, rebuilds the tree, and keeps the node, row and filter where you left them.
- Undo: the Workbench has its own Edit > Undo WordPress Change (Ctrl+Z), separate from the editor's undo.
- Code: wordpress_commands.py (`cmd_workbench`, `cmd_this_post_in_workbench`), wordpress_workbench_window.py (`open_workbench`, `open_from_door`), workbench_frame_actions.py.
- Review notes (Lite-specific, because Lite has a window per document):
  - The single Workbench is bound to the Lite window that first opened it. `editor=commands.host.parent` is that window, and the provider keeps that window's commands object and announcer. Opening the Workbench again from a second Lite window brings the same frame forward, still tied to the first window. Switch to Editor then returns to the first window, not the one you came from. If the first window has closed, it says "The editor that opened this window is closed."
  - The Workbench's Safe Mode comes only from the `QUILL_SAFE_MODE` environment variable (`cmd_workbench`, `open_from_door`). Forms decides Safe Mode with `safe_mode_on(host)`, which also reads the editor's own flag and the command line (`--safe-mode`). Launched with the flag rather than the variable, Forms commands refuse to reach the site while the Workbench may still write to it. This affects both editors.

### Command Palette, profiles and feature areas

- Both editors put every row in the Command Palette (Ctrl+Shift+P). QUILL registers each row with `commands.try_register`, using the title without "&" and without the trailing "...". Lite's palette reads its command table.
- Lite switches the two features as areas named "wordpress" and "forms". The WordPad and Notepad profiles leave both off ("Neither program had a way to publish to a website", "Neither program ever made a form"). QUILL switches them as `core.wordpress`, `core.forms` and a third feature, `core.forms_payments` ("Form Payments"), which is off in the Essential profile.
- Code: core/lite/features.py, core/lite/command_areas.py, core/features.py, core/feature_catalog.py.
- Review notes:
  - Lite has no Form Payments gate. `_payment_document` asks the host's editor for `_feature_enabled("core.forms_payments")`. A Lite window has no `_feature_enabled` method, so the check is skipped and Form Payments Setup, Insert Payment Field and Verify Payment Setup always run in Lite whenever Forms is on. In QUILL, with Form Payments off, the same rows stay visible and say "Turn on Form Payments in Features before using this command." This is a divergence, and in the "Lite has it, QUILL may not" direction the house rule forbids.
  - In QUILL, those three payment rows stay on the menu and enabled with the feature off. You find out the feature is off only by choosing one.
  - Both editors describe Forms as local when it is not. The Lite area description ends "Everything here runs on this computer", and QUILL's feature description says "Runs on this computer". But Publish Form, Insert Form Into Page, Test on Site, Responses, Verify Payment Setup and the three AI rows all reach a site or an AI.
  - Lite's Everything profile calls AI help "the one area here that does something outside this computer". WordPress and Forms also reach the network.

### Keys: no divergence

- Every WordPress and Forms default key is the same in both editors. QUILL's `DEFAULT_KEYMAP` takes them from `wordpress/keys.py` `default_bindings()`. Lite's rows carry the same layer chords from `lite_rows()`. The parity table `quill/core/lite/parity.py` maps each Lite layer handler to its QUILL command id, for example `cmd_forms_responses` to `forms.responses`, and has no `DIVERGENCES` entry for any WordPress or Forms row.
- No `DEFAULT_ALIASES` entry exists for any WordPress or Forms command (none found in `keymap.py`).
- The Workbench's own keys (Ctrl+Shift+A, Ctrl+Shift+S, Ctrl+Z, Alt+Enter and the rest) belong to the Workbench window (`workbench_window_menu.py`, `WORKBENCH_KEYMAPS` in `app_keymaps.py`), so they are identical whichever editor opened it.
- How labels show the layer chord:
  - In Lite, a two-press chord goes in brackets after the label, for example "Responses... (Ctrl+Alt+Shift+Grave, F)" (`lite_window_menus.py`), because wx would drop it after a tab.
  - QUILL's `_menu_label` shows the bound chord the same way.
- Code: core/keymap.py, core/lite/parity.py, core/wordpress/keys.py, lite_window_menus.py.

### Words that say QUILL inside QUILL Lite

- The shared Forms code speaks as QUILL in both editors. For example: New Form's purpose "QUILL writes it as plain text in the QAF form language", the failure "QUILL could not save {name}: ...", Add Rule's "QUILL writes it into the form", and Test on Site's "so QUILL opened it in QUILL Accessible Forms on the site".
- Review notes:
  - A Lite user hears "QUILL" for the editor they are in. Whether that is acceptable branding, or whether these strings should name the product through the host, is the owner's call.

## The WordPress Workbench window

The WordPress Workbench is one top-level window (title "WordPress Workbench") built on the shared Workbench frame: a Navigator tree on the left, then a filter box, an Items list, a read-only Details box and a focusable status bar on the right and bottom, with its own nine-menu bar (File, Edit, View, Go, Item, Site, Tools, Window, Help). The tree holds fixed nodes (Start Here, Needs My Attention, Sites, Calendar, Across Sites, Search, Practice Site, Help and Learning) and, under Sites, one copy of a large per-site template for every connected site. Lists load in the background when a node is selected; Enter runs a row's default action, the Applications key opens its context menu, Alt+Enter opens Properties. Everything below is read from the code (the frame in quill/ui/workbench_frame*.py, the provider in quill/ui/wordpress_workbench_window.py and its mixins, and the wx-free tables in quill/core/wordpress and quill/core/workbench). The per-node content (Posts, Media, Comments, Plugins and so on) is covered in other sections; this section covers the window itself. The review notes are the point: several are real defects found by reading the key routing, not style preferences.

### Opening it

- How to reach it from QUILL: Tools > WordPress > Open WordPress Workbench... (the first row of the Tools > WordPress submenu). The row has no access letter by design; the code comment says every letter of its name is taken in that menu. Its key is the WordPress layer: Ctrl+Alt+Shift+Grave, then H (menu.py LAYER_KEYS "H": "wordpress.workbench").
- This Post in the Workbench: File > WordPress > This Post in the Wor&kbench (Alt+F, W, K), or the WordPress layer then Shift+H. Note it lives in File > WordPress, not Tools > WordPress.
- The Tools > WordPress "doors" always open the Workbench now. Each classic command (Comments, Media Library, Manage Terms, Menus, Site Check, Site Settings, Site Map, Users, Application Passwords, Plugins, Themes, Fonts, Synced Patterns, Widgets, Abilities) calls workbench_door, which opens the Workbench on the matching node (door_node table in workbench_tree.py: for example Comments opens Comments > Waiting, Site Map opens Pages, Site Check opens Site Health).
- "Workbench as default" option: not found in code for WordPress. There is no setting; open_from_door always returns True and the retired classic windows are not an alternate route (wordpress_workbench_window.py docstring, "W6"). The GitHub Workbench has its own preference; WordPress has none.
- QUILL Lite: the same two commands, Tools > WordPress > Open WordPress Workbench and File > WordPress > This Post in the Workbench (lite_window_wordpress.py cmd_wp_workbench, cmd_wp_this_post_in_workbench), with the same WordPress layer keys, reaching the same shared code.
- What opens: one window per session. If it is already open, it is brought forward and, when no node was asked for, stays on the node, row, filter and scroll you left. Otherwise a new frame is built (980 by 680 DIP).
- Where it lands: with at least one site connected, Needs My Attention > Inbox; with none, Start Here. A door lands on its node of the first connected site in your site list.
- What is focused first: the Navigator tree (show() ends with tree.SetFocus()), with the landing node selected. The Inbox then loads in the background from every site.
- What is said on opening: nothing (GATE-13). The reader says the window title and the selected tree item. If the first load fails: "Could not load Inbox: " followed by the error text.
- With no sites connected: the Details box says Start Here's text and "You have 0 sites connected."; every Go key and every site command says "Connect a site first: File > WordPress > Connect a Site, in the editor."
- This Post in the Workbench, said in the editor before anything opens: "<title> is not on <site> yet, so the Workbench has no post to show. Save Draft to Site sends it first." when the document was never sent; "<site> is not among the Workbench's sites." when the site is not connected. Otherwise the window opens on Posts, Pages or the site's content type node, waits for discovery, selects the post's row and moves focus to the list. If the row is not in the first load it types the title into the filter box once; if still not found: "<title> is not in this list on <site>. It may have been deleted, or be in a status this list does not show." If the content type is unknown to the site: "<site> does not show this document's content type in its REST index, so <title> has no list here."
- Picking mode (Insert > Picture from the Media Library, other section): opens on the document site's Media and says "Picking a file for <document>: Enter on a file inserts it."
- Closing: Alt+F4, or File > Close Workbench (Alt+F, C). Escape never closes it. The editor stays open. Closing cancels pending background work and stops the Practice Site process if the Workbench started one (provider.close calls stop_process); nothing is said about that.
- Switch to Editor: Ctrl+Shift+E, or Window > Switch to Editor (Alt+W, E). Raises and focuses the editor that opened the window; says nothing on success, and "The editor that opened this window is closed." if it is gone.
- Code: wordpress_workbench_window.py (open_workbench, open_from_door, _start_ref), wordpress_workbench_editor_side.py, wordpress_commands.py, lite_window_wordpress.py, core/wordpress/menu.py, workbench_frame.py.
- Review notes:
  - Start Here still says "This is an early preview, behind a developer setting. Your Tools > WordPress windows still work." (workbench_help.py START_HERE). Both sentences are false now: there is no developer setting and the doors always open the Workbench. The first thing a new user reads is wrong.
  - A door opens on the FIRST site in the store, not the default site and not the site of the open document: current_site() falls back to next(iter(self._profiles)) because frame.current is still None when _start_ref runs. With two sites, Tools > WordPress > Users from a document on site B opens site A's Users.
  - The window does not remember its place across closes. The frame supports recall_place/remember_place hooks, but the WordPress provider implements neither, so every fresh open starts at Inbox with the tree collapsed. The GitHub Workbench does remember.
  - Closing the Workbench silently stops a running Practice Site. A person who opened the practice site from here and closes the window to write in the editor loses it without a word.
  - The workbench_door docstring (wordpress_commands.py) still says it returns False "without the developer flag"; it never does. Harmless to users, misleading to maintainers.

### Layout and panes

- Panes in F6 order: Navigator (tree), Filter (text box), Items (list), Details (read-only multi-line text), then the status bar. F6 moves forward, Shift+F6 back; also View > Next Pane (Alt+V, N) and View > Previous Pane (Alt+V, P). From the status bar F6 wraps to the tree. A status bar with no cell showing is skipped.
- Spoken names: the tree is named "Navigator", the list "Items", the filter box "Filter", the details box "Details". On screen the filter has the label "Filte&r:" (Alt+R jumps to it) and the details box the label "&Details" (Alt+D jumps to it). Neither letter collides with a menu title (F, E, V, G, I, S, T, W, H).
- Tab also moves tree, filter, list, details; the status bar takes no Tab stops (only F6 reaches it).
- F1 help strings: tree "Where you are. Arrows move, Right and Left open and close a branch, and typing jumps to a name. F6 moves to the filter box." (then replaced by the node's own help as you move); list "What is here. Enter does the default action, the Applications key lists the rest, and Alt+Enter opens Properties." (then replaced by node and row help); details "The selected row in full, or what this view shows and needs."
- Start Here: Go > Start Here, Ctrl+9 (Alt+G, S). Selects the Start Here node and puts focus on the tree. Start Here has no list; its text (START_HERE plus "You have N sites connected.") is put in the Details box.
- Keys the frame owns outside the menu: Escape clears the filter if it has text, otherwise goes Back; Backspace in the tree or list goes Back; Alt+Home goes to Inbox; Ctrl+R reloads (hidden alias of F5); Ctrl+Shift+F moves to the filter box (see review notes); Ctrl+Break says "Not available here."
- Code: workbench_frame.py (_build, panes, cycle_pane), workbench_frame_commands.py (_on_char_hook), workbench_frame_keys.py, workbench_help.py.
- Review notes:
  - Start Here's words live in the Details box, but Ctrl+9 leaves focus on the tree, over an empty list. A first-time user has to press F6 three times (filter, list, details) to read the page they asked for. Ctrl+9 should land in Details, or Start Here should open its text where focus goes.
  - Escape outside the filter box goes Back to the previous node, from any pane, including Details. "Read in Full" (Enter on a comment, plugin, fact and many other rows) moves focus to Details; the natural Escape to return to the list instead navigates the tree to a different node and throws away the list you were reading. Escape in Details should return to the list.
  - Backspace in the tree goes Back. The native tree's type-ahead uses letters, so this is safe, but Backspace as navigation is a browser idiom that surprises in a tree.

### The tree

- Built from WORDPRESS_TREE (workbench_tree.py) plus places from workbench_places.py, workbench_dashboard_places.py, workbench_sweep_places.py, workbench_pmpro_tree.py, workbench_shop.py and workbench_gravity_actions.py. The native wx.TreeCtrl with a hidden root; the reader says level and expanded state itself.
- Top-level nodes, in order, with their children:
  - Start Here (no list).
  - Needs My Attention (folder): Inbox; Comments Waiting; Pending Review; Scheduled; Drafts; Updates; Site Health; Accessibility; Broken Links; Held as Spam; Form Responses; Membership Orders; Watches.
  - Sites: lists the connected sites (columns Site, Address, Role); under it one node per site, labelled with the site's name.
  - Calendar: lists days; under it one Day node per day (dynamic).
  - Across Sites (folder): Tags and Categories; Plugins; Themes; People; Settings; Menus; Synced Patterns; Application Passwords; Fleet.
  - Search (words typed in the filter box are searched on every site).
  - Practice Site.
  - Help and Learning (folder): How WordPress Thinks (folder, text in Details); Words; Keys.
- Each site's children, in order (the site node itself is a folder):
  - Overview (At a Glance; Activity; wp-admin Screens).
  - Posts (Published; Drafts; Pending; Scheduled; Private; Trash; Group).
  - Pages (Published; Drafts; Pending; Scheduled; Private; Trash; Group).
  - More Content Types (one node per post type the site describes, each with its own status children).
  - Media (Pictures; Audio; Video; Documents; Unattached; Without Alt Text; Group; Housekeeping).
  - Comments (Waiting; Approved; Spam; Trash; Group).
  - Categories; Tags; More Taxonomies (one node per extra taxonomy).
  - Menus and Navigation.
  - Appearance (folder): Themes; Global Styles; Templates; Template Parts; Additional CSS; Patterns; Fonts; Widgets and Sidebars.
  - Forms (Responses; Held as Spam; Feeds; Results).
  - Memberships (folder): Membership Levels; Orders; Subscriptions; Renewals Due; Discount Codes.
  - Shop (Shop Orders; Draft Products; On Sale; Out of Stock; Customers; Coupons; Shop Reports; Store Settings; Product Reviews; Shipping Zones; Tax Rates; Tax Classes; Attributes; Brands; Webhooks).
  - Podcast.
  - Events Calendar (Past Events; Venues; Organizers; Event Categories; Event Tags).
  - SEO (Site SEO).
  - People (folder): Users; Application Passwords.
  - Plugins (Group).
  - Settings.
  - Site Health (Information; Security).
  - Abilities.
  - By Name (folder): Every Term; Field Values; Authors; Media Usage; Patterns Used; Links; Blocks and Shortcodes; Forms Used; Template Parts.
  - Content Audit; Privacy Requests; Redirects (404 Log); Search and Upkeep; Administration Areas; Content Model.
  - More from This Site (one node per REST namespace).
- Group nodes are labelled "Group" and are empty until View > Group By fills them with "value (count)" children.
- Lazy loading: the tree is built in full at once; nothing loads on expand. A list loads, off the UI thread, each time a node is SELECTED. Moving to another node before an answer arrives drops the stale answer (a generation counter). Discovered nodes (content types, taxonomies, namespaces) are added when each site's discovery finishes, by rebuilding the whole tree.
- What is announced on expand or select: nothing by the app (GATE-13). The Details box changes to the node's help; the tree's F1 text becomes the node's authored sentence (workbench_node_help.py NODE_HELP) plus the provider's words ("<label>, <site>.", plus "Gathered from every connected site, newest first." for Needs My Attention nodes, or "Open it with Right Arrow to see what it holds." for folders). A failed load is spoken: "Could not load <node>: <error>".
- Enter on a tree node moves focus to the list (even for a folder, whose list is empty). The tree's context menu is the "node" row type (see The context menu).
- Code: workbench_tree.py, workbench_places.py, workbench_dashboard_places.py, workbench_sweep_places.py, workbench_node_help.py, core/workbench/tree.py, workbench_frame.py (_build_tree, rebuild_tree, _show_node).
- Review notes:
  - Every site gets every plugin's branch whether or not the plugin is installed: Shop alone is 16 nodes, Events Calendar 6, Memberships 6, plus SEO, Podcast, Forms' Feeds and Results. That is well over 100 nodes per site, most of which, on a typical site, load only a sentence such as "<site> does not list WooCommerce's wc/v3 routes in its REST index, so it has no shop QUILL can read." For a screen-reader user arrowing through a site this is the single biggest cost in the window. Hide or collapse branches whose namespace is absent from the site's REST index.
  - Every tree selection fires a network load. Arrowing down through a site sends a request per node passed (stale answers are dropped, but the requests still go out). A short delay before loading, or loading only on Enter or a pause, would cut the traffic and the "Loading" churn in the status bar.
  - Discovery rebuilds the whole tree once per connected site shortly after opening. rebuild_tree deletes and re-adds every item, so any branch you expanded in the first seconds collapses again, and the current node is re-selected (the reader may say it again) and its list reloaded. Keep expansion state across rebuilds, or add discovered nodes in place.
  - "Drafts" under Needs My Attention is "Your own drafts, on every site" (NODE_HELP), but the label is just "Drafts", the same word as Posts > Drafts. "My Drafts" would say what it is.
  - "Site Health" and "Held as Spam" each appear twice with different meanings (across sites under Needs My Attention, and per site). The labels do not say which is which; only the position does.
  - Search has no Go key and no menu row; it is reachable only through the tree, and it only works with words typed into the filter box, which is not obvious from the node name.

### The list

- Columns: each node names its own (for example Posts: Title, Status, Author, Modified; Comments: Author, On, Status, When; Needs My Attention > Inbox: What, Site, When). Headers are made by capitalizing the column key with underscores turned to spaces ("alt_text" reads "Alt text").
- View > Columns..., Ctrl+Alt+C (Alt+V, C): a dialog titled "Columns" with one check box per column, in a group labelled "Columns to show:", then OK and Cancel. The node's own columns come first, then extras for the row kind (for posts: Date, Slug, Number, Type, Comments, Sticky, Format, Parent, Site). Announced after: "<n> columns."; with nothing checked: "A list needs one column at least, so nothing changed." Not on a list node: "Choose a list in the tree first."
- View > Group By..., Ctrl+Alt+G (Alt+V, G): works on Posts, Pages, Media, Comments and Plugins (and their Group node). A list dialog "Group By" with the prompt "Group by:" and rows "Nothing (no groups)" then each column title. Choosing a column fills the Group node with one child per value, "value (count)", and says "<n> groups under Group, by <column>."; choosing Nothing says "No groups." Elsewhere: "Group By works on Posts, Pages, Media, Comments and Plugins."
- View > Load More, Ctrl+Shift+L (Alt+V, M): asks for three more pages of 100. Says "Reading up to <n> rows." (600 after the first press) and reloads.
- View > Load All, Ctrl+Alt+L (Alt+V, L): asks for up to 100 pages (10,000 rows). Says "Reading every row. A big site takes a while." and reloads.
- First load is 3 pages (300 rows). When a list stops at its limit, the Items status cell adds ", more on the site".
- View > Refresh, F5 (Alt+V, R); Ctrl+R does the same. Reloads and keeps your place: the same item is selected and focused in one change, and a reload that found nothing new does not touch the list at all (list_place.py landing_index, same_cells).
- Multi-select: the list is a multi-selection report list: Shift+Arrows extend, Ctrl+Arrows and Ctrl+Space pick. Alt+2 says the count. Batch-aware commands (Trash, Restore, Publish, Approve and the others, Properties) act on every selected row.
- Enter: the row type's default action (the first row of its context menu): Open in Editor on posts and pages, View or Play on media, Read in Full on comments and most others (which moves focus to Details), Show Its Posts on terms and users, Open This Site on a site row.
- Empty list: nothing is said and no "empty" sentence is written; the Details box keeps the node's help and the Items cell says "0 shown". The frame has an empty_text hook for "why it is empty and what fills it", but the WordPress provider does not implement it.
- Code: workbench_frame.py (_set_columns, _fill_list, default_action), core/workbench/list_place.py, wordpress_workbench_lists.py, core/wordpress/workbench_listing.py.
- Review notes:
  - Column headers and the Columns dialog disagree on names: the list header is name.replace("_", " ").capitalize() in the frame, the dialog uses column_title, which renames some ("mime_type" is "File type" in the dialog, "Mime type" in the header; "id" is "Number" in the dialog and "Id" in the header). One function should name a column everywhere.
  - The Columns dialog's help says "Check each column the list shows, in this order. The first is what your screen reader says first." but the dialog cannot reorder anything; the order is fixed. Either offer Move Up and Move Down or drop "in this order".
  - Column choices, groupings and Load More depth are kept in memory only (column_choice, grouping, paging on the provider) and are lost when the window closes.
  - Group By counts come from the rows currently loaded and filtered (frame.rows), not from the site, so "Draft (12)" can be the 12 among the first 300, not the site's total. The node label gives no hint.
  - Load More, Load All, Refresh and remote filters announce when they START but never when they finish. A blind user hears "Reading every row. A big site takes a while." and then silence, with no signal that the list is ready except polling the Loading status cell. GATE-13 does not forbid saying a background result; "Loaded 1,240 rows." is exactly the kind of thing the reader cannot know.
  - The precise sentence cut_words builds ("The first 300 are shown, and the site has more. View > Load More reads 300 more; Load All reads every one.") is computed and stored but never shown or spoken; only the terse ", more on the site" reaches the Items cell.
  - "More on the site" is decided by count >= limit, so a site with exactly 300 posts is told there are more.
  - An empty list says nothing. "No comments are waiting on Radio." in Details (via the empty_text hook) would answer the first question a listener has.
  - Ctrl+A and Ctrl+C do nothing in the list: the frame has select_all and copy verbs, but the WordPress menu binds neither, and a native list view does not select all on Ctrl+A. Select-all-and-act is a common screen-reader workflow (for example Approve all waiting comments).
  - After any refresh the landing row is selected alone (focus_row deselects the others), so a multi-selection is lost after every batch action.

### The filter box and filter commands

- How to reach it: Ctrl+E, or Edit > Filter... (Alt+E, F), or Alt+R on its label, or F6 from the tree. The Filter status cell's Enter also moves there.
- What it does: Enter runs the filter. Plain words and key:value qualifiers are parsed into one query. On posts, pages, media, comments, users, terms, patterns and Search, both words and qualifiers go to the site (search argument and REST parameters), so the filter reaches the whole site; on other lists the words filter the loaded rows on this computer. Escape clears it. Moving to another node clears it silently ("A filter belongs to the list it was typed for").
- Help text (F1 in the box): "Type words to search the whole site, or qualifiers such as status:draft, category:news, -tag:old, author:3, after:2026-01-01 or modified:>2026-10-01. Enter runs it, Escape clears it, and Ctrl+Shift+F opens the Filter Builder."
- Aliases a person may type: category, tag, published (after), modified and changed (modified_after), type (media_type), mime, role, words (search), comment_type. A qualifier the route does not take fails the load: "Could not load <node>: This list cannot be filtered by <name>."
- Announced after Enter: "<n> shown." when filtered locally; "Filtering." when the site is asked (and nothing when the answer arrives).
- Filter Builder..., Ctrl+Shift+F (Alt+E, B): three dialogs in a row, each titled "Filter Builder": a list "Filter on:" (for posts: Status; Author number; Category, by name or number; Tag, by name or number; Published; Last changed; Sticky, yes or no; Parent number; Slug; Search in: post_title, post_content or post_excerpt; media, comments and users have their own short lists; other nodes offer their column names); a list "How:" with is, is not, after, before; a text box "Value:" ("Several values are separated by commas. Dates are written 2026-11-09."). The condition is appended to the filter box text and run. On Forms the Gravity Forms builder runs instead (other section).
- Show Only Like This..., Ctrl+Alt+O (Alt+E, O), and Hide Like This..., Ctrl+Alt+H (Alt+E, D): a list dialog titled "Show Only" or "Hide", prompt "Like this row by:", rows such as "Status: Draft" and "Author: Sam" (on site-filtered lists only status and author; on local lists every non-empty cell). The condition is added and run. With no row: "Choose a row first."; with nothing to offer: "This list can be narrowed by its words only. Type them in the filter box."
- Only Mine, Ctrl+Alt+M (Alt+E, M): toggles author:<your user number>. Adding runs the filter (says "<n> shown." or "Filtering."); removing says "Showing everyone's." Outside a site's list: "Only Mine works in a site's lists once the site has said who you are."
- Alt+1 reads the filter in words: "<path>, filtered to status is draft, containing radio".
- Code: core/workbench/filters.py, core/wordpress/workbench_filter.py, wordpress_workbench_people.py (do_filter_builder, _like, do_only_mine), workbench_frame.py (apply_filter, clear_filter).
- Review notes:
  - Ctrl+Shift+F never opens the Filter Builder. The frame's key hook (_on_char_hook: "if event.ControlDown() and event.ShiftDown() and code is F: self.filter.SetFocus()") runs before menu accelerators (the keep_list_key docstring states that order), so the chord only moves to the filter box. The menu shows Ctrl+Shift+F, the filter box help and the Keys node both teach it, and only the menu click works. This is a GitHub-only alias leaking into WordPress.
  - The same hook catches Ctrl+Alt+Shift+F (it checks Control and Shift, not Alt), so Tools > Forget a Saved Request's chord also just moves to the filter box.
  - "Filtering." is said and then nothing: the listener never hears how many rows the site sent back. Say "<n> shown." when the remote answer fills the list.
  - Filter wording is raw: Only Mine adds author:7, so Alt+1 says "filtered to author is 7", and the Filter Builder asks for "Author number" and "Parent number". People do not know their user number. describe() takes attribute labels but the WordPress window never passes any.
  - The Filter Builder offers "after" and "before" for every attribute, including Status and Slug, where they mean nothing, and offers no "contains". Operators should follow the attribute.
  - Only Mine's refusal ("once the site has said who you are") is wrong when the real problem is that you are on Needs My Attention or another non-site node.
  - Edit > Filter... has an ellipsis but opens no dialog; it only moves focus.
  - Filters are cleared without a word when you change nodes. A listener who filters Posts, checks Pages and comes back finds the filter gone. At least the Filter status cell shows "No filter".
  - describe_scope in workbench_filter.py (the "Filtered on this computer, 12 rows loaded" sentence the docstring promises) is not used anywhere in the UI.

### The Properties sheet and Site Properties

- How to reach Properties: Alt+Enter, Item > Properties... (Alt+I, P), the last row of every context menu ("Properties..."). With focus in the tree, or no row selected, Alt+Enter opens the site's sheet instead (or says "Alt+Enter on a row shows its Properties; Alt+Shift+Enter, the site's." when not inside a site).
- How to reach Site Properties: Alt+Shift+Enter, Site > Site Properties... (Alt+S, P), or the Site status cell's context menu, "Site Properties".
- What opens (one row): the object is read again first (off the UI thread; nothing is said while it reads), then a dialog titled "<title> Properties - <site>" (for example "Hello World Properties - Community Radio"). A notebook of pages; on each page a label and a control per field; then Copy as Text, OK, Cancel and Apply. Ctrl+Tab moves between pages.
- Item pages (workbench_sheets.py _item_sheet): General (Title, Slug, Status as a choice of publish, draft, pending, future, private; Password, masked and always empty, spoken "Password, hidden as you type"; Author as a choice; Published as text like 2026-11-09T14:00; Last changed and Address read only); Organize (Categories and Tags as comma lists by name or number; Format and Sticky on posts); Featured Image (chosen from the library, with the buttons "C&hoose from Library..." and "&Remove Featured Image"); Excerpt; Discussion (Comments and Pingbacks, open or closed); Template and Parent on pages (Template, Parent number, Order); Meta and an Advanced Custom Fields page where the site shows them. Other row kinds have their own static sheets or one built from the route's schema.
- Controls: text, numbers, dates and lists are text boxes (lists comma separated); choices are choice boxes; flags are check boxes; read-only or locked fields are read-only text boxes (Tab reaches them), with the reason in their F1 help: "<help> Read only for you: <reason>".
- Buttons, in Tab order: Copy as &Text, OK (no access key; Enter), &Apply, Cancel (no access key; Escape). On screen the order is Copy as Text, then OK, Cancel, Apply. A sheet you cannot save has only Copy as Text and Close.
- What each button does: OK saves what changed and closes at once; Apply saves and keeps the sheet open; Cancel and Escape close without saving and without asking; Copy as Text copies every page as plain text and says "Copied."
- Saving: only fields whose value changed are sent. The site's modified time is checked first; a conflict sends nothing and asks, in a Yes/No box titled "Changed on the Site": "<title> was changed on <site> after you opened it. Nothing was sent. Send your changes anyway, replacing theirs?" with the buttons "Use Mine" and "Cancel" (Cancel is the default).
- Preview: none for posts, pages, media, comments, terms or users. A site setting is previewed in a dialog "Change a Setting": summary "Change <label> on <site>. Ctrl+Z puts it back." and a line "<label> (<key>): <before> becomes <after>", button "Change". A setting that would lock someone out is refused with its reason.
- Announced after: "Saved <n> change(s) to <title> on <site>." plus " The site did not keep: <fields>." when the site ignored some; "Nothing changed on this row." when the body was empty; the error text on failure.
- Several rows (Alt+Enter with more than one selected, same kind and same site): a batch sheet titled "<n> items Properties - <site>" for posts, pages, custom items and media. Fields that differ show "Mixed" (choice "(Mixed: leave as it is)", check box third state) and are not sent; categories and tags have add and remove fields. Saving asks in "Change Several": "Change <n> items on <site>: <field> to <value>?" followed by up to 25 titles, button "Change Them". Announced: "Changed <good> of <total> on <site>." Failures ask "Some Were Not Changed": "<n> were not changed: ... Try them again?" with "Try Again". Refusals: "Several rows at once need to be the same kind, from one site."; "For several comments, use Approve, Unapprove, Spam or Delete."; "Several at once can be changed for posts, pages, custom items and media."
- Site Properties: titled "<site> Properties". Pages General (Name, Tagline, Address, WordPress version), Your Role (Role, What your role allows), Connection (Signs in as, Kind of site, Workbench access), REST Namespaces, Spam (Comments wait for approval, Spam plugins found, Form plugins found, Form spam checks, About spam here). All read only except the QUILL Accessible Forms part of the Spam page where the site allows it.
- Your Profile (Site > Your Profile..., below) uses the same editor.
- Undo: a single-row save records an undo ("Put <title> back as it was."); a batch records "Put <n> back as they were." Ctrl+Z.
- F1: on each field, its help; on the sheet, "Everything about it on one sheet. Ctrl+Tab moves between pages; OK saves and closes, Apply saves and stays."
- Without permission: every editable field is locked with the reason, and OK and Apply are not offered, when the row's kind is read only here ("This is read only here."), when Workbench access or View As Role forbids writing, or when your role lacks the capability ("Editing pages needs the Editor role or higher. You are an Author on Radio."). Single fields with their own requirement are locked one by one.
- Code: wordpress_workbench_sheets.py, workbench_sheet_editor.py, core/wordpress/workbench_sheets.py, core/wordpress/workbench_edit.py, wordpress_workbench_sheet_guards.py, core/workbench/properties.py. workbench_properties_sheet.py and workbench_properties_dialog.py are NOT used by the WordPress window (only GitHub's).
- Review notes:
  - WordPress gets the simpler sheet. GitHub's PropertiesSheet has Ctrl+S to apply, Ctrl+Enter for OK from a multi-line box, F5 reload, Ctrl+1 to Ctrl+9 page jumps, Ctrl+Shift+C copy, a "Sheet status" line showing what the last save did, and opens on the last page used. The WordPress sheet has none of these, so the two Workbenches teach different keys for the same window.
  - OK closes before the save is done. If the save then fails, or a conflict is answered Cancel, the typed changes are gone with no way back. Keep the sheet open until the site answers, or reopen it with the edits on failure.
  - Apply twice in one sheet will likely raise a false conflict: on_save always passes the modified time read when the sheet opened, so the second Apply finds the site's time changed by your own first Apply and asks "changed on the site after you opened it ... replacing theirs?". (Plausible; depends on the modified time changing between saves.)
  - Apply updates the sheet as if the save succeeded before the site answers; there is no status line on this sheet to show a failure.
  - Changing Status to publish on the sheet publishes immediately on OK, with no "Visitors will see them" confirmation, while Item > Publish or Update asks first. The same outcome should not have two confirmation levels.
  - Status values are raw slugs (publish, future, pending), and Comments and Pingbacks are "open" and "closed". WordPress's own screen says Published, Scheduled, Pending Review, Allow comments. A choice box can show words and send slugs.
  - The batch confirmation prints list values as Python tuples: "Add categories to ('News', 'Events')" (the f-string formats the tuple from value_of). Format lists as words.
  - The conflict box offers "Use Mine" and "Cancel"; the module docstring promises "Use Mine or Keep Theirs". "Keep Theirs" (and re-reading their version) is the more useful second choice than a bare Cancel that discards your edits silently.
  - Escape and Cancel discard edits without asking, even after many changes across pages.
  - Tab order (Copy as Text, OK, Apply, Cancel) does not match the visual order (OK, Cancel, Apply) because Apply is created before Cancel.
  - Field labels carry no access keys, so a long General page can only be walked with Tab.
  - Site Properties is almost all read-only text boxes inside a modal sheet with OK/Cancel semantics; "Close" is right, but a listener must Tab through every read-only box to reach it or press Escape.

### The context menu

- How to reach it: the Applications key or Shift+F10 on a list row (or right-click). With no row selected, or in the tree, you get the node's menu.
- Structure (core/workbench/actions.py ActionTable.menu_for, workbench_frame_actions.py _popup): the row type's rows in order, the first being the default (Enter); at most 8 entries show, so when there are more than 7 actions, 6 show, then a "More" submenu with the rest; Properties... is always the last row. A More holding a single row is not made. The frame also supports "Show Only" and "Hide" cell submenus before Properties, but the WordPress provider does not implement cell_rows, so they never appear.
- Examples (from WORDPRESS_ACTIONS):
  - A post or page: Open in Editor; Preview on the Site; Visual Review...; Publish or Update...; Move to Trash; Restore from Trash; More (Delete Permanently..., Copy Link, Copy to Site..., Approve and Schedule..., Send Back with a Note..., Assign a Reviewer..., Move to Another Day..., Show Its Comments, Earlier Versions..., Duplicate as Draft, Counts by Status, Empty Trash..., Open in wp-admin); Properties...
  - A comment: Read in Full; Approve, or Not Spam; Not Spam, and Allow This Sender; Unapprove; Spam; Reply...; More (Move to Trash, Restore from Trash, Delete Permanently...); Properties...
  - A user: Show Their Posts; Change Role...; Show Memberships...; Check Membership Access...; Change Membership Level...; Cancel Membership...; More (Their Application Passwords..., Sign Out Everywhere..., Invite from a Spreadsheet..., Send Password Reset, Set New Password..., Roles and What They May Do, Remove...); Properties...
  - A tree node: Refresh; New Here...; Load More; Load All; Columns...; Group By...; More (What Can I Do Here?, Counts by Status, Empty Trash..., wp-admin for This Place...); Properties...
  - A fact, help or problem row: Read in Full; Properties...
- Tiers (Tier in actions.py): READ (0), ORGANIZE (1, local or easily undone: Trash, Restore, moderation), WRITE (2, changes the site), DESTRUCTIVE (3, deletes or cannot be undone). The tier decides what Workbench Access allows (Read Only allows READ; Organize adds ORGANIZE; Full allows all). How each is confirmed is up to each handler, not the tier:
  - READ: never confirmed.
  - ORGANIZE: one row is done at once (Move to Trash of one post, Approve, Spam); several rows ask ("Move <n> items on <site> to the Trash?", button "Move to Trash"); moderation never asks, even for many.
  - WRITE: a preview or Yes/No naming the site and the items (Publish: "Publish <n> items on <site>? Visitors will see them." button "Publish"; Change Role preview with gains and losses, button "Change Role"; plugin "Activate <name> on <site>?").
  - DESTRUCTIVE: a Yes/No with No as default and "This cannot be undone." (Delete Permanently: "Delete <n> items from <site> permanently? This cannot be undone: <names>." button "Delete Permanently"; Revoke: button "Revoke"; Merge Into: a preview, button "Merge"; Convert: button "Convert").
- Greying by requirement: before the menu shows, each row is enabled only if provider.supports passes, which checks Workbench access (Safe Mode and View As Role count as Read Only) against the row's tier, then the capability from users/me (for example "edit" on a page means edit_pages, "publish" means publish_posts or publish_pages, "delete" on a term means manage_categories).
- What greyed rows say: in a context menu, nothing; the row is simply disabled. In the menu bar, the reason is put into the row's help string. If you run a refused command by key, the refusal is spoken: "<Doing this> needs the <Role> role or higher. You are <a role> on <site>." or "Workbench access on <site> is Read Only. Site > Workbench Access changes it." or "Safe Mode is on, so the Workbench only reads." or "You are viewing <site> as <Role>, which only reads. Site > View As Role ends it."
- Code: core/workbench/actions.py, core/wordpress/workbench_actions.py, workbench_frame_actions.py, wordpress_workbench_people.py (refusal_for), core/wordpress/workbench_permissions.py.
- Review notes:
  - The reason a row is greyed is never heard. The menu-bar reason goes into the item's help string, but the frame calls SetStatusBarPane(-1), so menu help is shown nowhere, and screen readers do not read menu help strings. In context menus no reason is set at all. The only place the real sentence appears is when a command is run by key.
  - The WordPress provider has no reason() hook, so the frame's fallback is used: every greyed row's reason is "Not available here." (workbench_frame_commands.py reason), including in Shift+F1's list (", greyed: Not available here."). The good refusal sentences exist in refusal_for but are not wired to reason().
  - Context menu rows show no keys and have no access letters, and "More" has none either. The help strings carry the keys ("Delete.", "Ctrl+Shift+P.") but, as above, are never displayed. A listener learns no chords from the context menu.
  - On a post, Copy Link and Delete Permanently sit inside More, behind Visual Review and Restore from Trash. Restore from Trash is shown on top even for a post that is not in the Trash (it then says "Nothing selected is in the Trash."). The top six should be the ones that apply to the row's state.
  - "Empty Trash..." (a whole-site, permanent action) is offered on a single post's context menu, under More. A row menu should hold only actions on the row; this one belongs on the node.
  - On a user, "Cancel Membership..." (DESTRUCTIVE) is on top while "Send Password Reset" is buried in More.
  - Greying only reflects permission, never applicability: a comment command on a post row is enabled and then says "Choose a comment or a form entry." when run (see the Item menu below).
  - Merge Into and Convert are DESTRUCTIVE and confirmed, but record nothing in Change History at all, while Delete Permanently records an entry marked cannot be undone. Change History is therefore not "every change made here".

### History and undo

- How to reach Undo: Ctrl+Z in the list, or Edit > Undo WordPress Change (Alt+E, U) from anywhere.
- How to reach Change History: Ctrl+Shift+H, or Edit > Change History... (Alt+E, H).
- What Undo does: takes the newest change in this session's history and runs its inverse off the UI thread, then refreshes. Spoken: the inverse's own sentence ("Restored <n> items from the Trash.", "Put <n> items back as they were.", "Put <title> back as it was.", "<name> is <Role> again.", "Moved them back to the Trash."). With nothing: "Nothing to undo." When the newest change has no inverse: "<summary> This cannot be undone."
- What Change History shows: a report dialog titled "Change History", a read-only multi-line box labelled "Report:" with "1. <summary>" lines newest first, " (cannot be undone)" after those without an inverse, then Copy All and Close. With nothing: "No changes made in the Workbench yet."
- Undoable here: Trash (restores), Restore (trashes again), Publish (puts the old statuses back), moderation (old statuses), one-row sheet saves, batch sheet saves, Change Role, plugin activate or deactivate.
- Recorded but not undoable: Delete Permanently, Remove person, Revoke application password, Set New Password, imports from a spreadsheet or folder, Plain-Language Batch, REST Console writes, Put Back from a Snapshot.
- Not recorded at all: Merge Into, Convert, New Here, Empty Spam, Empty Comment Trash, Reply, Allow This Sender (other sections may add more).
- Limits: 200 changes (ChangeHistory.limit); kept in memory for this window only, lost when it closes; no Redo command on the WordPress menu, though the model supports it.
- Ctrl+Z outside the list: in the filter box it undoes typing; in the tree or Details it does nothing and says nothing (keep_list_key swallows it). From the status bar: "Delete and Ctrl+Z act on the list. F6 moves back to it."
- Code: core/workbench/history.py, wordpress_workbench_sheets.py (do_undo, do_history), wordpress_workbench_commands.py, workbench_frame_keys.py.
- Review notes:
  - A change that cannot be undone blocks every earlier undo. next_undo() always returns the newest change, and undo() never removes one without an inverse. After one Delete Permanently, Import, REST Console write or Plain-Language Batch, every Ctrl+Z repeats "<summary> This cannot be undone." and the Trash you did five minutes earlier can no longer be undone from here. Ctrl+Z should skip (and say it skipped) entries with no inverse, or Change History should let you undo a chosen entry.
  - Change History is read only: you cannot pick an entry to undo, and entries have no times (Change.when is never set).
  - The undo message for summaries like the batch ("move all drafts by Sam to pending on Radio This cannot be undone.") reads as one run-on sentence; the summary needs its own full stop.
  - Ctrl+Z in the tree is silently ignored; a short "Ctrl+Z works in the list, or use Edit > Undo." would be better than nothing.
  - A failed undo leaves the change on top, so pressing Ctrl+Z again retries; that is reasonable, but the failure text is the raw error.

### The status bar

- How to reach it: F6 (after Details) or Shift+F6 from the tree. Left and Right (and Up and Down) move between cells, Home and End jump to the ends, Enter or Space does a cell's action, the Applications key or Shift+F10 opens its menu, Escape returns to where you were. Tab leaves it. The same facts are mirrored into a native status bar line, so a screen reader's read-status-bar key says them too.
- Cells, in order, each a button named "<name>, <value>" and shown only when it has a value:
  - Site: the site of the selected node (on Search, the selected row's site or "All connected sites"). Enter: the site's Overview. Menu: Site Properties.
  - Your role: "<Role> on <site>", or "Viewing as <Role> on <site>". Enter: the role-aware What Can I Do Here report. Menu: View As Role...
  - Items: "<n> shown", plus ", more on the site" when the list was cut, plus ", <n> selected" when more than one is selected. Enter: focus to the list.
  - Filter: the filter in words, or "No filter". Enter: the filter box. Menu: Clear Filter.
  - Loading: "Loading" or "Up to date, <HH:MM>". Enter: refresh. Menu: Refresh.
  - Waiting: "<n> comments waiting". Enter: Needs My Attention > Comments Waiting.
  - Link check: Check Every Link's progress while it runs. Enter stops it. Menu: Stop Checking Links.
  - Workbench access: Read Only, Organize or Full. Enter: Workbench Access.
- Every cell menu ends with Copy and Help for This Cell; Help for This Cell says "<name>. <help>".
- Nothing is announced when cells change (GATE-13).
- Where Am I, Alt+1 (View > Where Am I, Alt+V, W): says the tree path and the filter: "Sites, Community Radio, Posts, Drafts, filtered to author is 3". Before anything is shown: "Nowhere yet".
- Say Selection, Alt+2 (View > Say Selection, Alt+V, S): "<n> of <total> selected".
- Code: workbench_status_bar.py, wordpress_workbench_window_status.py, workbench_frame.py (where), workbench_frame_actions.py (say_selection).
- Review notes:
  - The Waiting cell's count is filled only when Needs My Attention > Comments Waiting has been loaded in this window; before that the cell is absent, and it goes stale until that node is loaded again. It reads like a live count and is not.
  - "1 comments waiting": the plural is fixed.
  - The Role cell's Enter opens the provider's role-aware report ("You are <Role> on <site>. ... <Action>: yes" or the refusal), which is what Shift+F1 promises but does not open (see Help). Two different What Can I Do Here windows exist.
  - The Filter cell is always present with "No filter", so F6 into the bar always lands on Site, Your role, Items, Filter, Loading before anything useful changes; fine, but the Items cell already says the count, so most visits read five cells to learn one fact.
  - A site name containing "&" becomes an access-key mnemonic in the cell's button label (SetLabel with the raw name). Minor, but it can swallow the character.

### F1, Shift+F1 and Help for This View

- F1, or Help > Help for This View (Alt+H, H): the shared Context Help dialog, titled "WordPress Workbench", with "Where you are: <node help>" and then the focused control's own help (the tree's is the node's sentence; the list's is the node's words plus "Enter on a row: <default action>. Shift+F1 lists everything you can do with the selected row, Alt+Enter shows all about it."; a row's is ROW_HELP for its kind).
- Shift+F1, or Site > What Can I Do Here? (Alt+S, W): the frame's action list, titled "What Can I Do Here", prompt "Actions for the selection:", a list of every action for the selected row's kind (or the node's), each "<label>, <key>" and greyed ones ", greyed: <reason>"; below it "About this action:" with the action's help; buttons Run (default, &R) and Close. Enter runs the selected action after the dialog closes; on a greyed one it beeps.
- Help and Learning nodes in the tree: How WordPress Thinks (a paragraph in Details), Words (18 glossary rows), Keys (18 key rows).
- Code: workbench_frame_help.py, workbench_help_dialogs.py, core/wordpress/workbench_node_help.py, core/wordpress/workbench_help.py, app_context_help.py.
- Review notes:
  - Shift+F1 opens the wrong window. "what_can_i_do" is a frame verb, so the frame's generic list runs and the provider's do_what_can_i_do (which starts "You are <Role> on <site>. Workbench access on <site> is <Access>." and gives the real refusal for each action) is unreachable from Shift+F1 and from the menu. The menu row's help says "What your role allows." and the Keys node says "Shift+F1: What your role lets you do here."; neither is what opens. The role-aware report is reachable only from the Your role status cell.
  - In the frame's list, every greyed row says "greyed: Not available here." (no reason hook), and "About this action" shows only the help, never the reason. So the window that exists to say why you cannot do something never says why.
  - The list is a plain list box; "greyed" rows are not disabled items, just text, and Enter on them only beeps.
  - F1 has no purpose sentence (no help_purpose hook) and no "open the guide" button: guide routes are registered only for GitHub windows (guide_opener.py), so the WordPress Workbench's F1 cannot open a user guide.
  - Alt+F1 (What Is This?), Ctrl+F1 (guide chapter), Ctrl+Shift+F1 (Search Help), Alt+Shift+F1 (Keys) and F9 (repeat last result) exist in the shared frame but are not on the WordPress menu, so they are not bound. The Keys node lists only 18 keys and is called "Every key the Workbench answers to" in its help; it omits Ctrl+9, Ctrl+N, F5, the Go row beyond Ctrl+1 and Ctrl+2, and the whole Site and Tools menus.
  - The Keys node teaches Ctrl+Shift+F for the Filter Builder, which does not work (see The filter box).
  - The Help menu has one row. Start Here (Ctrl+9) is on the Go menu, and What Can I Do Here? is on the Site menu; a listener looking for help in Help finds neither.

### Workbench Access, View As Role, and Roles

- Workbench Access: Ctrl+Alt+A, Site > Workbench Access... (Alt+S, A), or Enter on the Workbench access status cell. A list dialog titled "Workbench Access", prompt "How much may the Workbench change on <site>?", rows "Read Only: look, never change", "Organize: also Trash, Restore and moderate comments", "Full: everything your role allows", the current one selected; OK and Cancel. Kept per site on this computer (workbench_access.json); Full when never chosen. Announced after: "Workbench access on <site> is <Read Only|Organize|Full>." F1: "A limit on top of your role, kept for this site on this computer."
- View As Role: Ctrl+Alt+V, Site > View As Role... (Alt+S, V), or the Your role cell's menu. A list dialog "View As Role", prompt "See the site as:", rows "Myself, as I am", Subscriber, Contributor, Author, Editor, Administrator. Announced: "Viewing <site> as <Role>. Nothing can be changed until you stop." or "Viewing <site> as yourself again." While viewing, access is Read Only and refusals are computed with WordPress's default capabilities for that role. Kept for this window only.
- Roles and What They May Do: Ctrl+Alt+R, Site > Roles and What They May Do (Alt+S, R), or a user row's context menu (under More). A report dialog of each default role and what it adds, then "WordPress's REST API reads roles but cannot change what a role may do. A role plugin such as Members or User Role Editor does that in wp-admin."
- Code: core/wordpress/workbench_permissions.py, wordpress_workbench_people.py, wordpress_workbench_lists.py (do_roles).
- Review notes:
  - Workbench Access, Safe Mode and View As Role are enforced only for commands that appear in the selected row's action table (refusal_for returns "" for any command not in that table, and for no row). Menu-bar-only commands do not check access: Site > Empty Spam and Empty Comment Trash (permanent deletes), Edit > Import Posts and Import a Folder of Documents, Tools > WXR Files > Import WXR as Drafts, Site > Put Back from a Snapshot, Tools > REST Console (POST, PUT, PATCH and DELETE go straight through after its own preview), and New Here. So "Read Only: look, never change" and View As Role's "Nothing can be changed until you stop" are not true, and Safe Mode ("the Workbench only reads") can still delete every spam comment. This is the most serious finding in the window.
  - Ctrl+Alt+R does not open Roles: the frame's key hook treats any Ctrl+R without Shift, Alt included, as Reload ("event.ControlDown() and not event.ShiftDown() and code is R"), and it runs before the menu accelerator. Only the menu and the context menu reach it.
  - When you are not inside a site (for example on Needs My Attention), all three silently act on the first connected site; only the Workbench Access prompt names it.
  - View As Role always preselects "Myself, as I am", not the role you are currently viewing as.
  - View As Role is per window and forgotten on close; Workbench Access is per site and persistent. The status bar shows both, but nothing tells you that one survives and the other does not.

### Menu bar: File

- New Here... - Alt+F, N - Ctrl+N - makes something new on the current node (full treatment below).
- Open on the Site - Alt+F, S - Shift+Enter - the selected row, or the site, in your browser (below).
- Preview on the Site - Alt+F, V - Ctrl+Enter - a post or page's preview in your browser (below).
- (separator)
- Close Workbench - Alt+F, C - Alt+F4 - closes this window; the editor stays.
- Access letters: N, S, V, C, no collisions, none missing.
- Review notes:
  - New Here's menu help, "A new user or password, where you are.", is out of date: it also makes posts, pages, custom items, categories, tags, terms, menus, redirects, discount codes, shop and event items and forms.
  - File has no Close Window-style "Open the Editor" or Export; that is fine, but Export List and the imports live in Edit, where a Windows user would look under File.

### Menu bar: Edit

- Undo WordPress Change - Alt+E, U - Ctrl+Z - puts back the newest change (History and undo above).
- Change History... - Alt+E, H - Ctrl+Shift+H - the session's changes (above).
- (separator)
- Copy Link - Alt+E, L - Ctrl+Shift+C - copies the selected row's address (below).
- Filter... - Alt+E, F - Ctrl+E - moves to the filter box (The filter box above).
- Filter Builder... - Alt+E, B - Ctrl+Shift+F (menu only, see review) - builds a condition in three steps.
- Show Only Like This... - Alt+E, O - Ctrl+Alt+O - keeps rows like the selected one.
- Hide Like This... - Alt+E, D - Ctrl+Alt+H - hides rows like the selected one.
- Only Mine - Alt+E, M - Ctrl+Alt+M - only what you wrote, or everyone's again.
- (separator)
- Export List... - Alt+E, X - Ctrl+Shift+X - this list as Excel, CSV or Markdown (below).
- Import Posts from a Spreadsheet... - Alt+E, I - Ctrl+Shift+I - posts or pages from a file, previewed (below).
- Import a Folder of Documents... - Alt+E, T - Ctrl+Alt+Shift+I - each document a draft, previewed (below).
- Access letters: U, H, L, F, B, O, D, M, X, I, T, no collisions, none missing.
- Review notes:
  - No Cut, Copy, Paste or Select All rows: Ctrl+C and Ctrl+A do nothing in the list (see The list), and the familiar Edit menu shape is missing.
  - Only Mine is a toggle but is not a check item, so the menu does not say whether it is on.

### Menu bar: View

- Refresh - Alt+V, R - F5 - loads this view again (Ctrl+R too).
- Load More - Alt+V, M - Ctrl+Shift+L - three hundred more rows.
- Load All - Alt+V, L - Ctrl+Alt+L - every row, up to ten thousand.
- Columns... - Alt+V, C - Ctrl+Alt+C - choose the columns.
- Group By... - Alt+V, G - Ctrl+Alt+G - a child node per value.
- (separator)
- Back - Alt+V, B - Alt+Left - the view before ("Nothing to go back to." when none). Backspace and Escape too.
- Forward - Alt+V, F - Alt+Right - the view you went back from ("Nothing to go forward to.").
- (separator)
- Next Pane - Alt+V, N - F6.
- Previous Pane - Alt+V, P - Shift+F6.
- (separator)
- Where Am I - Alt+V, W - Alt+1 - path and filter, spoken.
- Say Selection - Alt+V, S - Alt+2 - "<n> of <total> selected".
- Access letters: R, M, L, C, G, B, F, N, P, W, S, no collisions, none missing.
- Review notes:
  - "Load All" says "Read every row the site has." but stops at 10,000 (ALL_PAGES 100 pages of 100).
  - Back's help mentions Backspace but not Escape, which also goes Back and is the more surprising of the two.

### Menu bar: Go

- Each Go row selects a node and puts focus on the tree. Site rows use the current site (the site of the selected node, else the first connected site); without any site: "Connect a site first: File > WordPress > Connect a Site, in the editor."
- Start Here - Alt+G, S - Ctrl+9 - Start Here (text in Details).
- Needs My Attention - Alt+G, N - Ctrl+1 - lands on Needs My Attention > Inbox (Alt+Home does the same).
- Current Site - Alt+G, I - Ctrl+2 - the site's Overview.
- Posts - Alt+G, P - Ctrl+Shift+1.
- Pages - Alt+G, A - Ctrl+Shift+2.
- Media - Alt+G, M - Ctrl+Shift+3.
- Comments - Alt+G, C - Ctrl+Shift+4.
- Users - Alt+G, U - Ctrl+Shift+5 - People > Users.
- Plugins - Alt+G, L - Ctrl+Shift+6.
- Appearance - Alt+G, E - Ctrl+Shift+7 - lands on Appearance > Themes.
- Settings - Alt+G, G - Ctrl+Shift+8.
- Site Health - Alt+G, H - Ctrl+Shift+9 - the site's Site Health.
- Across Sites - Alt+G, O - Ctrl+0 - the Across Sites folder (an empty list).
- Calendar - Alt+G, D - Ctrl+3 - every site's content by day.
- Watches - Alt+G, W - Ctrl+5 - Needs My Attention > Watches.
- Practice Site - Alt+G, R - Ctrl+6 - the Practice Site node.
- (separator)
- Parent Node - Alt+G, T - Alt+Up - selects the parent node and focuses the tree; at a top-level node it does nothing and says nothing.
- Keyless: none. Ctrl+4 and Ctrl+8 are deliberately unbound (window menu comment, decided 2026-11-13).
- Access letters: S, N, I, P, A, M, C, U, L, E, G, H, O, D, W, R, T, no collisions, none missing.
- Review notes:
  - Every Go key leaves focus on the tree, not the list. After Ctrl+Shift+4 (Comments) you still need F6 twice to reach the comments. A Go key is a "take me to the things" key; landing in the list (or making that an option) would save two presses every time.
  - The Go row's digits are not in the order of the tree: Ctrl+1 Needs My Attention, Ctrl+2 Current Site, Ctrl+3 Calendar, Ctrl+5 Watches, Ctrl+6 Practice Site, Ctrl+9 Start Here, Ctrl+0 Across Sites, with 4 and 8 empty. The menu lists them Start Here first but Start Here is Ctrl+9. Hard to learn by ear.
  - "Appearance" lands on Themes, and "Needs My Attention" lands on Inbox, not on the folder the label names; the Where Am I words will differ from the menu word.
  - Across Sites lands on a folder with an empty list; Ctrl+0 then Right Arrow is always needed.
  - Practice Site appears as Go > Practice Site (Ctrl+6) and Tools > Practice Site... (Ctrl+Alt+P), two rows with the same name doing different things (a node versus a start/stop dialog).
  - Parent Node at the top silently does nothing.

### Menu bar: Item

- Properties... - Alt+I, P - Alt+Enter - the selection's sheet (The Properties sheet above).
- Publish or Update... - Alt+I, U - Ctrl+Shift+P - publish the selection after a Yes/No (see the Posts section).
- Approve, or Not Spam - Alt+I, A - Ctrl+Shift+A - approve, or release spam (see the Comments section).
- Unapprove - Alt+I, N - Ctrl+Shift+U - back to waiting (see the Comments section).
- Spam - Alt+I, S - Ctrl+Shift+S - mark as spam (see the Comments section).
- Reply... - Alt+I, R - Ctrl+Shift+M - reply to a comment (see the Comments section).
- Not Spam, and Allow This Sender - Alt+I, L - Ctrl+Alt+W - approve and let the sender through (see the Comments section).
- Merge Into... - Alt+I, M - Ctrl+Shift+G - fold a term into another (see the Categories and Tags section).
- Convert to Category or Tag... - Alt+I, V - Ctrl+Shift+K (see the Categories and Tags section).
- Approve and Schedule... - Alt+I, C - Ctrl+Shift+D (see the editorial workflow section).
- Send Back with a Note... - Alt+I, B - Ctrl+Shift+B (see the editorial workflow section).
- Assign a Reviewer... - Alt+I, G - Ctrl+Shift+J (see the editorial workflow section).
- Move to Another Day... - Alt+I, Y - Ctrl+Alt+Shift+D (see the Calendar section).
- Copy to Site... - Alt+I, O - Ctrl+Shift+Y (see the Across Sites section).
- Send Password Reset - Alt+I, W - Ctrl+Shift+W - opens the person's wp-admin screen (see the People section).
- Show Its Comments - Alt+I, I - Ctrl+Alt+Shift+M (see the Comments section).
- Entry Notes... - no access letter - Ctrl+Alt+N (see the Forms section).
- Star or Unstar Entry - no access letter - Ctrl+Alt+F (see the Forms section).
- Mark Entry Read or Unread - no access letter - Ctrl+Alt+U (see the Forms section).
- Resend Notifications... - no access letter - Ctrl+Alt+I (see the Forms section).
- Gravity Forms (submenu) - Alt+I, F - then: Show Its Feeds (F); Show Its Results (R); Test This Form... (T); Change a Field Type... (Y); Edit Form... (E); New Gravity Form... (W); Copy as a QUILL Accessible Form... (Q); Copy QAF Form as a Gravity Form... (G); separator; Activate or Deactivate Feed... (A); Rename Feed... (N). None has a chord; KEYLESS reasons (workbench_gravity_actions.py) include "A form-design change made rarely (rule 9).", "Renaming a feed is rare (rule 9).", "New Here (Ctrl+N) on a site's Forms node reaches it." (see the Forms section).
- (separator)
- Move to Trash - Alt+I, T - Delete (list only) - into WordPress's Trash; Ctrl+Z restores. On a user it is Remove, on an application password Revoke (see the Posts and People sections).
- Restore from Trash - Alt+I, E - Ctrl+Shift+R (see the Posts section).
- Delete Permanently... - Alt+I, D - Shift+Delete (list only) - gone for good, after a Yes/No (see the Posts section).
- Access letters in use: P, U, A, N, S, R, L, M, V, C, B, G, Y, O, W, I, F, T, E, D. No collisions. Missing: the four Gravity entry rows (Entry Notes..., Star or Unstar Entry, Mark Entry Read or Unread, Resend Notifications...) have no "&" at all (GRAVITY_ITEM_ROWS labels). menus.problems() accepts a top-level row without a letter when it has a chord, so the gate passes.
- Review notes:
  - The four Gravity entry rows cannot be reached by letter. Free letters remain (H, J, K, Q, X, Z), so they could have them.
  - The Item menu has 23 top-level rows plus a 10-row submenu, for every row kind at once. Greying is by permission only, so on a post, Approve, Spam, Reply, Merge Into, Convert, Entry Notes, Star and the rest are all enabled and each says a refusal sentence when chosen ("Choose a comment or a form entry.", "Merge Into works on a category, tag or term."). A listener walks past 15 irrelevant rows to find Publish. Grey by row kind too, or build the Item menu from the selected row's action table (which is what the actions.py docstring says the Item menu is: "the same rows, in the same order").
  - Greying is computed only when a menu opens (EVT_MENU_OPEN), never on selection change. On Windows a disabled menu item's accelerator does not fire, so a chord greyed the last time you opened the menu (for example while access was Read Only) likely stays dead, silently, until you open that menu again. (Plausible; verify on Windows.)
  - Delete Permanently's help says "after you confirm by name", which suggests typing the name; the dialog only lists names and asks Yes or No. Say "after you confirm" or really ask for the name.
  - Delete and Shift+Delete do nothing, silently, in the tree and Details (keep_list_key swallows them); in the filter box they edit text, which is right.

### Menu bar: Site

- Site Properties... - Alt+S, P - Alt+Shift+Enter - the site's sheet (The Properties sheet above).
- What Can I Do Here? - Alt+S, W - Shift+F1 - the action list (Help above; see review there).
- View As Role... - Alt+S, V - Ctrl+Alt+V - (Workbench Access above).
- Workbench Access... - Alt+S, A - Ctrl+Alt+A - (above).
- Roles and What They May Do - Alt+S, R - Ctrl+Alt+R (menu only, see review) - (above).
- Empty Spam... - Alt+S, M - Ctrl+Alt+E - deletes every spam comment on the site after "Delete all <n> comments held as spam on <site> permanently? This cannot be undone." (button "Delete All") (see the Comments section).
- Empty Comment Trash... - Alt+S, E - Ctrl+Alt+Shift+E - the same for the comment Trash (see the Comments section).
- Comment Counts - Alt+S, C - Ctrl+Alt+Shift+C - waiting, approved, spam and Trash counts (see the Comments section).
- Your Profile... - Alt+S, Y - Ctrl+Alt+Shift+P - your own profile on this site (below).
- (separator)
- Compare Sites... - Alt+S, I - Ctrl+Alt+K (see the Across Sites section).
- Site Sets... - Alt+S, T - Ctrl+Alt+T (see the Across Sites section).
- Across Sites Scope... - Alt+S, O - Ctrl+Alt+Y (see the Across Sites section).
- Take a Snapshot... - Alt+S, N - Ctrl+Alt+S (see the Snapshots section).
- Put Back from a Snapshot... - Alt+S, K - Ctrl+Alt+Shift+S (see the Snapshots section).
- Read Site as Document - Alt+S, D - Ctrl+Alt+D - the site's pages as one document in the editor (below).
- Access letters: P, W, V, A, R, M, E, C, Y, I, T, O, N, K, D, no collisions, none missing.
- Review notes:
  - "Empty Spam" takes M and "Empty Comment Trash" takes E, so the two siblings that start with the same word do not share a letter pattern; acceptable, but E for "Empty" belonging to the second row is a trap for the first.
  - Empty Spam and Empty Comment Trash run under Read Only, Safe Mode and View As Role (see Workbench Access).
  - What Can I Do Here? belongs in Help.

### Menu bar: Tools

- Workbench Options... - Alt+T, O - Ctrl+Shift+O - which Watches run (below).
- REST Console... - Alt+T, R - Ctrl+Shift+T - any route on the site (below).
- Run a Saved Request... - Alt+T, Q - Ctrl+Alt+Q - pick a saved request, then the console (below).
- Saved Requests (submenu) - Alt+T, V - then 1 to 9 - your saved requests (below).
- Forget a Saved Request... - Alt+T, F - Ctrl+Alt+Shift+F (menu only, see review) - remove one (below).
- Plain-Language Batch... - Alt+T, L - Ctrl+Alt+B - a change said in words (below).
- Practice Site... - Alt+T, P - Ctrl+Alt+P - start, stop, connect or reset the practice site (see the Practice Site section).
- WXR Files (submenu) - Alt+T, W - then Export Site as WXR... (E) and Import WXR as Drafts... (I); no chords, KEYLESS reasons "Moving hosts or keeping a copy: a few times a site's life (rule 9)." and "Moving content in happens once per move (rule 9)." (see the WXR section).
- Access letters: O, R, Q, V, F, L, P, W, no collisions, none missing.
- Review notes:
  - Workbench Options holds only Watches. The name promises the window's options (columns, landing node, Go-key focus, announcements) and delivers one checklist; "Watches..." would be honest, or the options should grow.

### Menu bar: Window

- Switch to Editor - Alt+W, E - Ctrl+Shift+E - brings the editor forward (Opening it above).
- Access letters: E. One row.
- Review notes:
  - The menu could also list the editor's other open windows; with one row it is a long way to one command that already has a key.

### Menu bar: Help

- Help for This View - Alt+H, H - F1 - the layered Context Help (F1 above).
- Access letters: H. One row.
- Review notes:
  - Start Here, What Can I Do Here?, How WordPress Thinks, Words and Keys are all help and none is here.

### New Here

- How to reach it: Ctrl+N, File > New Here... (Alt+F, N), or New Here... on a tree node's context menu.
- What it makes, by node: Posts and its status nodes, a post; Pages, a page; a content type node, an item of that type; Categories, Tags or a taxonomy node, a term; Menus and Navigation, a menu (with a menu row selected it first asks "New Here", "Make:", rows "A new item in <menu>" and "A new menu"); Users and Application Passwords, a person or an application password (see the People section); Discount Codes, Redirects, shop and event nodes, Forms (a Gravity form) and Content Model each hand off to their own command (other sections).
- What opens for posts, pages and terms: one small text dialog per field, in a row, each titled "New <Noun>": "Title:" ("The title it starts with. It is saved as a draft."); for terms "Name:", for categories "Parent number (optional):" ("0 or empty for a top level."), then "Description (optional):". OK and Cancel; Cancel at any step stops.
- Announced after: "Made the <noun> <name> on <site> as a draft." (items) or without "as a draft" (terms, menus); empty name: "It needs a name, so nothing was made."; elsewhere: "New Here makes posts, pages, custom items, categories, tags, terms, menus, people and application passwords. Choose one of those nodes first."
- Undo: not recorded; Ctrl+Z does not remove what was made.
- Without permission: not checked (see Workbench Access); the site's own refusal is spoken if it refuses.
- Code: wordpress_workbench_lists.py (do_new_here), wordpress_workbench_people.py, core/wordpress/workbench_create.py.
- Review notes:
  - A new post or page is made on the site and then left there: it is not opened in the editor, the new row is not selected, and the person must find it in the list. "Made the post X on Radio as a draft." followed by opening it in the editor (or at least selecting the row) is the expected flow.
  - A category asks for its parent by number. The site has the category list; a choice would do.
  - A chain of one-field dialogs, each with the same title, is slow and gives no sense of how many steps remain.
  - Not in Change History, so Ctrl+Z cannot undo an accidental Ctrl+N.

### Open on the Site, Preview, Copy Link

- Open on the Site: Shift+Enter, File > Open on the Site (Alt+F, S), and on several context menus. Opens the selected row's address in your browser; with no row (or a row without an address), the site's home page. Spoken only on failure: "This has no address on the site yet."
- Preview on the Site: Ctrl+Enter, File > Preview on the Site (Alt+F, V), the second row of a post's context menu. A post or page only; adds preview=true to the address unless it is published. Spoken: "Preview works on a post or page." when not one; "This has no address on the site yet."
- Copy Link: Ctrl+Shift+C, Edit > Copy Link (Alt+E, L), a context-menu row (under More on posts). Copies the selected row's address, or the site's address when there is none. Spoken: "Copied." or "Could not copy."
- Code: wordpress_workbench_commands.py (do_open_on_site, do_preview), workbench_frame_actions.py (copy_link, copy_text), wordpress_workbench_window.py (url).
- Review notes:
  - With nothing selected, or on Needs My Attention, Open on the Site and Copy Link fall back to the FIRST connected site's address and say only "Copied." A listener cannot tell they copied a home page rather than the row. Say what was copied ("Copied the address of Hello World.") or refuse without a row.
  - Shift+Enter and Ctrl+Enter are window accelerators, so they also fire from the filter box, where a listener pressing Shift+Enter by habit opens a browser instead of running the filter.
  - Preview of a draft needs a signed-in browser; nothing says so if the browser is not signed in to wp-admin.

### Export List

- How to reach it: Ctrl+Shift+X, Edit > Export List... (Alt+E, X).
- What opens: a standard Save dialog titled "Export List" with types "Excel workbook (*.xlsx)", "CSV (*.csv)" and "Markdown table (*.md)", asking before overwriting.
- What it writes: the list as shown, the chosen columns (by their dialog titles) and the rows currently in the list (filtered, loaded so far).
- Announced after: "Exported <n> rows to <file name>. Left out: columns you have hidden (<names>), each item's full text, its pictures and files, and rows outside the list as shown (filtered out, or not loaded yet)." With no rows: "There is nothing in the list to export."
- Code: wordpress_workbench_bold_lists.py (do_export_list), core/wordpress/workbench_io.py, core/wordpress/workbench_carry.py.
- Review notes:
  - The left-out sentence is spoken in full on every export. It is honest but long; the hidden-columns part is news, the rest is the same every time and could be in the help.
  - When the list stopped at its 300-row limit, the export silently writes 300 rows; the generic "not loaded yet" phrase does not say that this export is short. Say "300 of more than 300; Load All first for every row."
  - The file is written on the UI thread; a 10,000-row Excel export will freeze the window briefly.

### Import Posts from a Spreadsheet

- How to reach it: Ctrl+Shift+I, Edit > Import Posts from a Spreadsheet... (Alt+E, I).
- What opens: an Open dialog titled "Import Posts from a Spreadsheet" filtered to "Spreadsheets (*.xlsx;*.csv)". Then a preview dialog titled "Import into <site>": a "Summary:" box ("<n> posts will be made on <site> as drafts (or pending or private, where a Status column says so); <m> are skipped."), and an "Each change:" list starting with which column fills which field and which are left out, then a line per row; buttons Import (default) and Cancel.
- Pages or posts: pages when the current node is under Pages, otherwise posts.
- Announced after: "Imported <made> of <total> into <site>." then a report dialog "Import into <site>" with a sentence per row and a "Left out:" section ("Not carried from a spreadsheet: pictures and featured images, authors (each item is yours), custom fields, comments and publishing (published or scheduled rows are drafts)."). An unreadable file: "<name> could not be read: <error>".
- Undo: recorded as "Imported <n> posts into <site>." with no undo; it then blocks Ctrl+Z (see History).
- Without permission: not checked by the Workbench (see Workbench Access).
- Code: wordpress_workbench_bold_lists.py, core/wordpress/workbench_io.py, core/wordpress/workbench_carry.py.
- Review notes:
  - Importing from the Media or Comments node makes posts, without saying that it chose posts; the preview's first words should say "posts" or "pages" explicitly and let you switch.
  - The Open dialog offers no "All files" choice (the helper choose_spreadsheet in wordpress_workbench_dialogs.py, which says "Spreadsheets saved as CSV", is a different, unused-here dialog).
  - The import could easily be undone (move the new drafts to the Trash) but is not.

### Import a Folder of Documents

- How to reach it: Ctrl+Alt+Shift+I, Edit > Import a Folder of Documents... (Alt+E, T).
- What opens: a folder dialog titled "Import a Folder of Documents" (must exist), then the folder is read in the background, then the same "Import into <site>" preview, headed "Each file's first heading is its title; files are made in name order. Pictures beside a file are uploaded, and links between the files are pointed at their drafts." and a "Left out: <line>." per thing not carried.
- Announced: "<folder> has no Markdown, text or Word files." when empty; after: "Imported <made> of <total> into <site>." and a per-file report.
- Undo, permission: as for the spreadsheet import.
- Code: wordpress_workbench_bold_lists.py, core/wordpress/workbench_carry.py.
- Review notes:
  - The chord Ctrl+Alt+Shift+I is a four-key chord for an action used a few times a year; rule 9 would say a letter is enough.
  - Same Undo and access gaps as the spreadsheet import.

### Workbench Options

- How to reach it: Ctrl+Shift+O, Tools > Workbench Options... (Alt+T, O).
- What opens: a dialog "Workbench Options" with a group "Options:" of check boxes, one per Watch: "Watch: New comments waiting", "Watch: New form responses", "Watch: Plugin updates available", "Watch: Scheduled posts going live", "Watch: A site not answering, and answering again", "Watch: Items with a reviewer leaving the queue", "Watch: Site Health status changes", "Watch: Form spam questions, once a week"; OK and Cancel. All off until checked.
- F1: "Every Watch is off until you check it: nothing is asked of your sites for Watches before then. A checked Watch asks each connected site over the internet at most every fifteen minutes while the editor is open, and says only what changed; its first look is silent. Space checks or unchecks."
- Announced after OK: "Workbench options saved." Saved in workbench_options.json beside the site list.
- Code: wordpress_workbench_options.py, core/wordpress/workbench_options.py, core/wordpress/workbench_watches.py.
- Review notes:
  - Every check box starts with "Watch:", so a listener hears "Watch" eight times; the group could be labelled "Watches" and the boxes left plain.
  - The fifteen-minute interval (watch_minutes) is stored but not offered.
  - The module docstring names quill.core.wordpress.workbench_flag.workbench_window_enabled, a flag the doors no longer read.

### REST Console

- How to reach it: Ctrl+Shift+T, Tools > REST Console... (Alt+T, R).
- What opens: a dialog "REST Console - <site>" with, in Tab order: Route (combo box, completes from the site's index with Down Arrow, Alt+R), Method (GET, POST, PUT, PATCH, DELETE, OPTIONS, Alt+M), Parameters or body (multi-line, name=value lines or JSON, Alt+P), Needs (read only, the capability and the methods the route takes, Alt+N), Accepts (read only, the route's arguments for the method, Alt+T), Answer (a tree of the answer, Alt+A), then the buttons Send (default, Alt+S), Copy JSON (Alt+J), What It Returns (Alt+W), Save Request (Alt+V), Close (Escape).
- Send: a missing required argument stops it and is spoken; reads (GET, OPTIONS) go at once; a write first shows a preview "Send to the Site": "<METHOD> <route> on <site>. This can change the site. It needs: <needs>." with a line per value and "Check: <problem>" lines, button Send.
- Announced after: "<METHOD> <route>: answered." and the Answer tree is filled and its top item selected. "Type a route first." with no route. Errors are spoken.
- What It Returns: a report "What <route> Returns" listing the fields from OPTIONS, or "The route does not describe what it returns."
- Save Request: asks "Save Request", "Name:" (prefilled "<METHOD> <route>"); says "Saved <name>. It is in Tools > Saved Requests."
- Undo: a write is recorded "<METHOD> <route> on <site> from the REST Console." with no undo (blocks Ctrl+Z).
- Code: wordpress_rest_console.py, wordpress_workbench_bold.py (do_rest_console), core/wordpress/workbench_rest_routes.py, core/wordpress/workbench_io.py.
- Review notes:
  - The console ignores Workbench Access, Safe Mode and View As Role: a DELETE goes through under Read Only after only its own preview.
  - do_rest_console calls self.ensure(...) on the UI thread before the dialog opens, which may block on two network reads for a site not yet read.
  - "answered." is said even when the site answered with a WordPress error object in a 200 body; the listener has to open the tree to learn it failed.
  - The docstring calls the copy button "Copy Answer"; it is "Copy JSON". The help on Save Request warns "Do not type a password into the parameters of one you keep." which is the right warning but the saved file is not encrypted; a stronger guard (refuse to save a parameter named password) would be safer.

### Run a Saved Request, the Saved Requests submenu, Forget a Saved Request

- Run a Saved Request: Ctrl+Alt+Q, Tools > Run a Saved Request... (Alt+T, Q). A list dialog "Run a Saved Request", "Request:"; OK opens the REST Console filled in; a GET or OPTIONS is sent at once, a write waits for Send and its preview. With none saved: "No saved requests yet: the REST Console's Save Request button keeps one."
- Saved Requests submenu: Tools > Saved Requests (Alt+T, V), filled each time the menu opens: "&1 <name>" to "&9 <name>" (first nine only), or a disabled "(None yet)". Choosing one does what Run a Saved Request does. A request whose site is no longer connected runs on the current site.
- Forget a Saved Request: Ctrl+Alt+Shift+F, Tools > Forget a Saved Request... (Alt+T, F). The same chooser, titled "Forget a Saved Request"; removes it without asking and says "Forgot <name>."
- Code: wordpress_workbench_bold_more.py, core/wordpress/workbench_rest_saved.py, workbench_frame_commands.py (fill_dynamic_menus).
- Review notes:
  - Ctrl+Alt+Shift+F does not reach Forget: the frame's Ctrl+Shift+F hook catches it and moves to the filter box.
  - run_saved also calls ensure on the UI thread.
  - A saved request for a site that is gone silently runs against a different site (the current one). For a saved write, that is a risk; say which site it will use, or refuse.
  - Only nine show in the submenu with no "More..." row; the tenth is reachable only through Run a Saved Request.

### Plain-Language Batch

- How to reach it: Ctrl+Alt+B, Tools > Plain-Language Batch... (Alt+T, L).
- What opens: a text dialog "Plain-Language Batch", "What to do:", with help giving examples ("move all drafts by Sam to pending on Radio; or add tag 2026 to posts in category Events on every site; or remove tag Old from all published pages ...") and "Nothing is sent until you check the list that follows and press Change."
- Then, after the sites are read: a check-box dialog "Plain-Language Batch", "Change these:", one box per item "<site>: <title>", all checked, OK and Cancel. Sites refused by access or role appear as a sentence in the summary.
- Announced: a phrase the grammar cannot read says its error; nothing found: "Nothing to change. <summary>"; after: "Batch done: <ok> of <checked> changed." and a report dialog with the phrase and a line per item.
- Undo: recorded with the phrase as its summary and no undo (blocks Ctrl+Z).
- Code: wordpress_workbench_bold_more.py, core/wordpress/workbench_plain_batch.py.
- Review notes:
  - The help says "press Change" but the button is OK (ask_checks uses the default OK label). Name the button Change, as the other previews do.
  - The checklist is the only preview: it lists items but not the change itself per item (for example "Draft becomes Pending"); the phrase is only in the F1 help. Put the change sentence above the list.
  - A batch over many items cannot be undone, although every item's before-state was read.

### Read Site as Document

- How to reach it: Ctrl+Alt+D, Site > Read Site as Document (Alt+S, D).
- What opens: a list dialog "Read Site as Document", "Read:", rows "The whole site", "The pages in one menu", "The posts in one category"; for a menu or category, a second list of them.
- What it does: builds a Markdown document (a heading per page) in the background, saves it under the data folder (wordpress_read_site), and opens it in the editor.
- Announced after: "<site> is open as a document, a heading per page. File > Export makes Word, EPUB or DAISY from it." None to choose: "<site> has no menus to read." / "categories".
- Code: wordpress_workbench_bold.py (do_read_site, _read_scope).
- Review notes:
  - The row has no ellipsis although it opens a dialog first.
  - Nothing is said while a large site is read; a long silence follows the choice.

### Your Profile

- How to reach it: Ctrl+Alt+Shift+P, Site > Your Profile... (Alt+S, Y).
- What opens: your own user sheet, titled "Your Profile - <site>", the user sheet without its Role page, with the same OK, Cancel, Apply and Copy as Text (The Properties sheet above). Nothing is said while it reads.
- Announced after save: "Saved <n> change(s) to <your name> on <site>."; if the site has not identified you: "<site> has not said who you are yet."
- Without permission: Workbench access still applies (fields locked under Read Only or View As Role).
- Code: wordpress_workbench_people_bulk.py (do_your_profile), wordpress_workbench_sheets.py.
- Review notes:
  - A four-key chord for an occasional command; most people change their profile a few times ever.

### Keyless rows and written reasons

- Gravity Forms submenu rows and WXR Files rows have no chords; their reasons are in KEYLESS (workbench_gravity_actions.py, workbench_site_files_actions.py), quoted above. The Saved Requests submenu is numbered instead.
- Context-menu-only rows (Open in Editor, Visual Review..., Duplicate as Draft, Counts by Status, Empty Trash..., wp-admin rows and the rest) have their reasons in the parity and admin KEYLESS tables (other sections), for example "Permanent and occasional: never a bare key (rules 4 and 9)." for Empty Trash.

### Summary of review notes, most serious first

- Workbench Access, Safe Mode and View As Role do not stop menu-bar-only commands: Empty Spam, Empty Comment Trash, Import Posts, Import a Folder, Import WXR, Put Back from a Snapshot, New Here and REST Console writes all run under Read Only.
- Three chords are dead because the frame's key hook runs before the menu: Ctrl+Shift+F (Filter Builder, moves to the filter box), Ctrl+Alt+Shift+F (Forget a Saved Request, same), Ctrl+Alt+R (Roles, reloads instead).
- One change that cannot be undone blocks every earlier undo; Ctrl+Z repeats "<summary> This cannot be undone." forever.
- Shift+F1 and Site > What Can I Do Here? open the frame's generic list, not the role-aware report; greyed rows everywhere say only "Not available here."
- Reasons for greyed rows are put where nobody hears them (menu help with the status bar help pane disabled).
- Every site shows every plugin's branch (over 100 nodes), and each tree selection fires a network load.
- Long operations (Load More, Load All, Refresh, remote filters) announce their start but never their result.
- The Properties sheet closes on OK before the save is known, loses edits on failure, likely false-conflicts on a second Apply, and lacks the GitHub sheet's keys.
- Escape outside the filter box goes Back to another node, including from Details after Read in Full.
- Start Here still calls the Workbench an early preview behind a developer setting, and its text is three F6 presses from where Ctrl+9 puts you.

## Posts and pages

Posts, Pages and every content type a plugin adds share one row kind, "item". Enter opens the item in the editor, Alt+Enter opens its Properties sheet, and the row's context menu (Applications key or Shift+F10) offers nineteen commands plus Properties. Because the menu shows at most eight entries, six commands sit on top and thirteen go under a More submenu, including several that have chords (Delete Permanently, Approve and Schedule, Send Back, Copy to Site) and several that have none and appear nowhere else (Earlier Versions, Duplicate as Draft, Counts by Status, Empty Trash, Open in wp-admin). Publishing, scheduling and the editorial queue each preview before sending, but they disagree with one another about defaults, wording and whether Ctrl+Z can take them back. What follows is grounded in quill/core/wordpress/workbench_actions.py, workbench_parity_actions.py, workbench_gap_actions.py, workbench_window_menu.py and the quill/ui/wordpress_workbench_*.py handlers.

### The tree nodes and what the list shows

- Posts: Go > Posts, Ctrl+Shift+1 (Alt+G, P). Lists every status at once (the node's preset is status "any"). Columns: Title, Status, Author, Modified.
- Under Posts: Published, Drafts, Pending, Scheduled, Private and Trash, each one status, same four columns; and Group, which View > Group By (Ctrl+Alt+G) fills with one child per value.
- Pages: Go > Pages, Ctrl+Shift+2 (Alt+G, A). Shown as a tree by parent. Columns: Title, Level, Status, Modified. The same six status children and Group sit under it.
- More Content Types: one row per plugin post type (columns Type, Route, Taxonomies); Enter opens that type's own node, whose items have the Posts columns.
- View > Columns (Ctrl+Alt+C) adds, for items: Date, Slug, Number, Type, Comments, Sticky, Format, Parent, Site.
- The details pane sentence for a row: "{title}. {Status}, scheduled for {date}. Last changed {date}. By {author}." (the "scheduled for" part only on a scheduled item). An author whose name was not read shows as "user 3".
- A list reads 300 rows first. When it stops short the Items cell says "The first 300 are shown, and the site has more. View > Load More reads 300 more; Load All reads every one." Load More is Ctrl+Shift+L, Load All Ctrl+Alt+L.
- F1 on the tree, Posts: "The site's posts, newest change first. Enter opens one in the editor." Pages: "The site's pages, as a tree by parent. Enter opens one in the editor." A content type: "Items of one kind a plugin added. Enter opens one in the editor." More Content Types: "The kinds of content this site's plugins add, such as Events." Status children have no sentence of their own and borrow their parent's (node_help strips the last "_part"). Group: "The rows of the list above that share one value, from View > Group By."
- F1 on an item row: "A post, page or item. Enter opens it in the editor, Alt+Enter its Properties; Earlier Versions on the context menu compares and restores the site's revisions."
- Code: workbench_tree.py, workbench_rows.py (item_row), workbench_listing.py, workbench_node_help.py.
- Review note: the six status children under Pages use the Posts columns and are not tree-ordered, so Pages > Drafts loses the Level column the Pages node has. Moving from Pages to Pages > Drafts silently changes the column set.
- Review note: the extra column titled "Comments" shows the item's comment_status ("open" or "closed"), not a count. A listener will expect a number. Calling it "Comments allowed" would fix that.
- Review note: dates in the list and details pane are made from modified_gmt and date_gmt by friendly_date, which the code documents as "UTC as given". Nothing in the cell says UTC, so a site in another time zone hears times that look local and are not.

### The item row's context menu, as it is actually laid out

- Shown on top, in order: Open in Editor, Preview on the Site, Visual Review..., Publish or Update..., Move to Trash, Restore from Trash.
- Then a submenu labelled "More" holding, in order: Delete Permanently..., Copy Link, Copy to Site..., Approve and Schedule..., Send Back with a Note..., Assign a Reviewer..., Move to Another Day..., Show Its Comments, Earlier Versions..., Duplicate as Draft, Counts by Status, Empty Trash..., Open in wp-admin.
- Then Properties... last.
- Rows whose capability or Workbench access is not met are disabled (greyed). The menu itself does not say why. The reason is spoken only when you press the row's chord, or listed by What Can I Do Here? (Shift+F1, Alt+S, W) as "{label}: {reason}" or "{label}: yes".
- The tree node's own context menu (Shift+F10 on the tree, or on an empty list) is: Refresh, New Here..., Load More, Load All, Columns..., Group By..., then More (What Can I Do Here?, Counts by Status, Empty Trash..., wp-admin for This Place...), then Properties....
- Code: quill/core/workbench/actions.py (menu_for, split_for_menu), quill/ui/workbench_frame_actions.py (_popup).
- Review note: "More" is appended with no access key, and the context menu labels carry no chord text. The chords live only in each row's help string, which goes to the status bar and is not normally spoken. So the context menu never teaches a listener that Delete Permanently is Shift+Delete or Approve and Schedule is Ctrl+Shift+D.
- Review note: actions.py promises that "the same rows, in the same order, are the Item menu, so More never hides anything that only a right-click could reach". The WordPress Item menu breaks that promise. Open in Editor, Visual Review, Earlier Versions, Duplicate as Draft, Counts by Status, Empty Trash and Open in wp-admin are only on the context menu, and the Item menu's order differs from the context menu's.
- Review note: Delete Permanently, a tier 3 command, sits first under More, directly above the harmless Copy Link. One arrow press separates a copy from a permanent delete. The confirmation stops it, but its placement is still careless.
- Review note: a greyed row gives no reason when you arrow onto it. The reason is reachable through Shift+F1, but nothing in the menu points there.

### Open in Editor

- How to reach it: Enter on the row (the default), or the first context-menu row "Open in Editor". It has no Item menu entry.
- What opens: the editor's own open path (WordPressCommands.open_item), so the item opens as a document in the editor. The Workbench stays open behind.
- Announced after, only on failure: "Choose a post or page to open in the editor." and "{site} is no longer in your list of sites."
- Undo: nothing to undo; it only opens.
- F1 (row): see the item row help above.
- Without permission: needs edit_posts, or edit_pages on a page. Enter then says, for example, "Editing pages needs the Editor role or higher. You are an Author on {site}." With Workbench access set to Read Only, Enter still opens it, because the row is tier 0.
- Keyless: Enter is its key; no written KEYLESS reason exists because it has a key.
- Code: wordpress_workbench_commands.py (do_open_in_editor).
- Review note: an Author pressing Enter on someone else's page hears a refusal and nothing else. Offering to open it read only, or pointing at Preview on the Site (Ctrl+Enter), would turn the dead end into a choice.

### Preview on the Site

- How to reach it: Ctrl+Enter; File > Preview on the Site (Alt+F, V); context-menu row 2.
- What opens: your browser at the item's link. When the item is not published, "preview=true" is added to the address.
- Announced after, only on failure: "Preview works on a post or page." and "This has no address on the site yet."
- Undo: not applicable.
- Without permission: no requirement; never greyed.
- Code: wordpress_workbench_commands.py (do_preview).
- Review note: a draft's preview link only works for someone signed in to WordPress in that browser. Open in wp-admin says "You must be signed in to wp-admin in your browser" and Visual Review explains the same limit, but Preview says nothing, so the first time someone previews a draft they meet a login page with no warning.
- Review note: Open on the Site (Shift+Enter, File > Open on the Site, Alt+F, S) is the published address. It is not on the item context menu at all, though it is on the Site row's.

### Visual Review...

- How to reach it: context menu only, row 3. No chord and no Item menu entry.
- What opens: the editor's Visual Review. The page is captured, then a confirmation titled "Visual Review" asks before anything goes to your AI, with the button "Send for Review". Cancel there says "Nothing was sent. The screenshots are in {folder}."
- Announced when the item is not published: "Visual Review looks at the published page, and this is not published on {site} yet. Publish it first. A draft opens only for someone signed in to WordPress in a browser, so QUILL cannot capture it."
- Menu help: "The editor's Visual Review of this published page: it is captured, and described by your AI only after you say yes. Nothing on the site changes."
- Without permission: no requirement; never greyed.
- Keyless: "A page is reviewed after a redesign, now and then (rule 9)."
- Code: wordpress_workbench_commands.py (do_visual_review), wordpress_review_commands.py.
- Review note: the row is enabled on drafts, pending and scheduled items, where it can only refuse. It is one of the six top rows, so most of the time it is the wrong thing to offer there. It should be greyed, or say before it starts, when the row's status is not "publish".

### Publish or Update...

- How to reach it: Ctrl+Shift+P; Item > Publish or Update (Alt+I, U); context-menu row 4.
- What it acts on: the selected items that are not already published. If none qualify: "Nothing selected is waiting to be published." Items from more than one site: "Publish items from one site at a time."
- What opens: a Yes/No message box titled "Publish". It reads "Publish {n} item(s) on {site}? Visitors will see them." followed by "- {title}" for up to twenty items and "and {n} more". The buttons are "Publish" and "Cancel". Cancel is the default, so Enter cancels.
- Announced after: "Published {n} items on {site}." When some failed: " {k} were not: {reason}; {reason}; {reason}" (the first three).
- Undo: recorded. Ctrl+Z sends each item back to its old status and says "Put {n} items back as they were."
- Menu help: "Make the selected items public, after a preview. Ctrl+Shift+P."
- Without permission: needs publish_posts, or publish_pages on a page. For example: "Publishing pages needs the Editor role or higher. You are an Author on {site}." Under Organize or Read Only access: "Workbench access on {site} is Organize. Site > Workbench Access changes it."
- Cancel: nothing sent, nothing said.
- Code: wordpress_workbench_commands.py (do_publish), workbench_edit.py (run_batch).
- Review note: the label promises "or Update", but published items are filtered out before anything happens, so on a published post the only result is "Nothing selected is waiting to be published." Either drop "or Update" or make it update.
- Review note: there are two ways to publish now. This one uses a message box whose default is Cancel and records an undo. Approve and Schedule with an empty time uses a preview list whose default is Publish and records no undo (see below). The same act has two dialogs, two default buttons and two answers to Ctrl+Z.
- Review note: the help says "after a preview", but this is a message box, not the Workbench's preview window.
- Review note: when every item fails, an undo is still recorded, and Ctrl+Z says "Put 0 items back as they were."

### Approve and Schedule...

- How to reach it: Ctrl+Shift+D; Item > Approve and Schedule (Alt+I, C); context menu, under More.
- What opens first: a one-line text box titled "Approve and Schedule", with the prompt "Publish on (2026-11-20 9:00 AM), or empty for now:". OK is the default; Cancel stops. Help: "A day and time on the site's own clock. A time that happens twice when the clocks go back takes first or second after it. Empty publishes now."
- Empty time: a preview window titled "Approve and Publish". Summary: "Publish {n} on {site} now." The "Each change" list holds the titles. The button is "Publish" and it is the default, so Enter publishes.
- With a time: the site's time zone is read in the background, then a preview titled "Approve and Schedule". Summary: "Approve {n} on {site} and schedule them for {words}." The button is "Schedule". {words} reads like "Friday 20 November 2026, 9:00 AM at the site (Europe/London)", followed by the time where you are, or ", which is the same time here".
- Errors (the text box does not come back; you start again): "Type the day as year, month and day, for example 2026-11-20."; "Type the time as 24-hour hours and minutes, or like 4:15 PM."; "{time} does not happen on {day} in {zone}: the clocks go forward then. Choose another time."; "{time} happens twice on {day} in {zone}, because the clocks go back. Type first or second after the time to say which."; "Choose a time that is in the future."; "QUILL does not know the time zone {key}. Choose another."
- Announced after: "{n} published." or "{n} scheduled for {words}."
- Undo: a Change History entry is recorded with no undo. Ctrl+Z then says "Published on {site}. This cannot be undone." or "Scheduled on {site}. This cannot be undone."
- Menu help: "Publish it now or at a time you give. Ctrl+Shift+D."
- Without permission: needs publish_posts or publish_pages, the same sentences as Publish.
- Code: wordpress_workbench_bold_queue.py (do_approve_schedule), workbench_editorial.py (site_moment, moment_words), schedule.py.
- Review note: it does not look at status. It will "approve" a post that is already published and reschedule it into the future, which takes it off the site until then. Move to Another Day warns about exactly that ("Published items moved to a future time are scheduled again, and are off the site until then.") and this command does not.
- Review note: the items are sent one at a time in a single loop with no per-item outcome. If the third of five fails, the error is said, the first two are already changed, the rest are not, and nothing says which. Publish, Trash and moderation all report each item.
- Review note: a typing mistake in the time throws away what was typed. The error is spoken after the dialog has closed, and the person must press Ctrl+Shift+D and type it all again.
- Review note: "{n} published." and "Publish {n} on {site} now." say a bare number with no noun ("1 published."), unlike Publish's "Published 1 item on {site}."

### Send Back with a Note...

- How to reach it: Ctrl+Shift+B; Item > Send Back with a Note (Alt+I, B); context menu, under More.
- What opens: a multi-line text box titled "Send Back with a Note", prompt "What needs changing:". Enter adds a new line, so Tab to OK. Help: "A note on the draft, which its writer and reviewer read in the editor."
- Empty note: nothing happens and nothing is said.
- Preview or confirmation: none. After OK, each item gets the note (block notes) and is set to draft.
- Announced after: "Sent back {n} as drafts, with your note. WordPress sends no email."
- Undo: recorded with no undo. Ctrl+Z says "Sent back {n} on {site}. This cannot be undone."
- Menu help: "Back to draft, with a note for its writer. Ctrl+Shift+B."
- Without permission: needs edit_posts or edit_pages ("Editing posts needs the Contributor role or higher. You are a Subscriber on {site}.").
- Code: wordpress_workbench_bold_queue.py (do_send_back), block_notes.py.
- Review note: critical. It does not check status. On a published post it sets the post to draft, so the post disappears from the site, with no preview, no warning and no undo. The module's own docstring says "every change is previewed", and this one is not.
- Review note: an empty note cancels silently. A listener who pressed OK by accident on an empty box hears nothing and cannot tell whether anything was sent.
- Review note: "Sent back 1 as drafts" reads oddly for one item.

### Assign a Reviewer...

- How to reach it: Ctrl+Shift+J; Item > Assign a Reviewer (Alt+I, G); context menu, under More.
- What opens: first the site is asked for people with edit_others_posts; if it will not list them, for authors (who=authors). If names come back, a list titled "Assign a Reviewer", prompt "Reviewer:", help "The people on the site who may edit and publish others' posts." If none come back, a text box "Reviewer's name:", help "The site would not list its editors, so type the reviewer's name."
- Then a multi-line box titled "Assign a Reviewer", prompt "A note for {reviewer}:". It may be left empty; Cancel stops.
- Preview or confirmation: none.
- Announced after: "{reviewer} reviews {n}. WordPress sends no email for this: the note is on the draft, where its writer and the reviewer read it, and the Review Watch on this computer says when it leaves the queue."
- Undo: recorded with no undo. Ctrl+Z says "{reviewer} asked to review on {site}. This cannot be undone."
- Without permission: needs edit_posts or edit_pages.
- Code: wordpress_workbench_bold_queue.py (do_assign_reviewer, _reviewer_then), workbench_editorial.py (assign_reviewer, NOTICE_WORDS).
- Review note: the fallback list is who=authors, which includes Contributors and Authors who cannot publish others' posts. The list's own help still says "who may edit and publish others' posts", so the fallback can offer people the help says are not there.
- Review note: a typed name is not checked against anyone on the site; a misspelt reviewer is accepted and recorded.
- Review note: the closing sentence is about forty words and is said every time. A short "Asked {reviewer} to review {n}. No email is sent." would carry the same fact; the Review Watch explanation belongs in F1.

### Move to Another Day...

- How to reach it: Ctrl+Alt+Shift+D; Item > Move to Another Day (Alt+I, Y); context menu, under More.
- What opens: a one-line text box titled "Move to Another Day", prompt "New day and time (2026-11-20 9:00 AM):", already filled with the first selected item's date as "2026-11-20 09:00" (24-hour). Help: "On the site's own clock. A time that happens twice when the clocks go back takes first or second after it. The preview says it in your time too."
- Then a preview titled "Move to Another Day", summary "Move {n} on {site} to {words}.", the titles listed, plus, when a published item moves into the future, "Published items moved to a future time are scheduled again, and are off the site until then." The button is "Move", the default.
- Errors: as Approve and Schedule. "Choose a time that is in the future." applies only when every selected item is scheduled.
- Announced after: "Moved {n} to {words}."
- Undo: recorded with no undo. Ctrl+Z says "Moved to another day on {site}. This cannot be undone."
- Without permission: needs edit_posts or edit_pages.
- Code: wordpress_workbench_bold_queue.py (do_move_day).
- Review note: the old date of every item is known before the move, so this is one of the easiest changes to undo, and it is not undoable.
- Review note: with several items selected, the box shows only the first one's date and every item gets the same new moment. The preview does not show each item's old date, so a listener cannot hear what is being lost.

### Copy Link

- How to reach it: Ctrl+Shift+C; Edit > Copy Link (Alt+E, L); context menu, under More.
- Announced after: "Copied." or "Could not copy."
- Undo: not applicable.
- Without permission: none.
- Code: quill/ui/workbench_frame_actions.py (copy_link), wordpress_workbench_window.py (url).
- Review note: when a row has no link, the provider falls back to the site's own address, and the outcome is still just "Copied." A listener pasting expects the post and gets the home page.

### Copy to Site...

- How to reach it: Ctrl+Shift+Y; Item > Copy to Site (Alt+I, O); context menu, under More.
- What opens: with only one site connected, "Connect a second site first: File > WordPress > Connect a Site." Otherwise a list titled "Copy to Site", prompt "Site:", help "Which of your other connected sites." A practice-site crossing check may ask first. If your role or Workbench access on the target refuses writing, that refusal is said and nothing else happens.
- Preview: a preview window titled "Copy from {source} to {target}". Its summary: "Copy from {source} to {target}: {a} made, {b} replaced, {c} skipped, and {d} pictures uploaded. New items are drafts; a replaced item keeps its status on {target}. Links to {source} are pointed at {target}." Each line is "Make {kind} {title}.", "Replace {kind} {title}." or "Skip {kind} {title}: {why}", then "Upload the picture {url}" and "Left out: {thing}". The button is "Copy".
- Announced after: "Copied to {target}; new items are drafts there." or "Copied to {target}, except {n}; the report says which.", and then a report window titled "Copy to {target}".
- Undo: recorded with no undo. Ctrl+Z says "Copied {n} from {source} to {target}. This cannot be undone."
- Menu help: "To another of your sites, after a preview. Ctrl+Shift+Y."
- Without permission: no requirement on the source row, so it is never greyed; the target's refusal is checked when you choose it.
- Code: wordpress_workbench_bold.py (do_copy_to_site), workbench_site_copy.py.
- Review note: "Replace" overwrites an existing item on the target site, and nothing can put it back. The preview line "Replace post About." is the only warning, and it is phrased like the harmless "Make" lines. A replace deserves its own sentence in the summary saying it cannot be undone.

### Show Its Comments

- How to reach it: Ctrl+Alt+Shift+M; Item > Show Its Comments (Alt+I, I); context menu, under More.
- What happens: the Comments node is selected with "post:{id}" in the filter box, focus goes to the list, and then this is said: "{n} comments on {title}, approved and waiting together."
- Failure: "Show Its Comments works on a post or page."
- Without permission: none.
- Code: wordpress_workbench_moderation.py (do_show_comments), workbench_moderation.py (post_comment_count).
- Review note: the count is spoken after focus has already moved to the list, so it competes with the screen reader reading the first focused row. One or the other gets cut off. Saying the count first, or putting it in the status bar, avoids the collision.

### Earlier Versions... (in progress)

- Status: the code exists in the working tree and is not committed. Present: the context-menu row (workbench_gap_actions.py, ITEM_VERSIONS), the handler (wordpress_workbench_gaps.py), the core (workbench_item_versions.py), the row F1 sentence, and unit tests (test_wp_workbench_gaps.py, test_wp_workbench_gaps_core.py). Not found: a wordpress.md engineering log entry or user-guide text for Earlier Versions on post rows. Treat everything here as in progress.
- How to reach it: context menu only, under More. No chord and no Item menu entry.
- What opens: the item and its revisions and autosaves are read. Versions identical to the item now are left out. If none remain: "{title} has no earlier versions on {site}." Otherwise a list titled "Earlier Versions of {title}", prompt "Versions:", one row each as "Saved {date}, {title}, a revision" or "..., an autosave", newest first. Help: "Each version the site kept, newest first. OK compares it with the item now, and that preview is where it is restored."
- Preview: a preview window titled "Restore {title}". Summary: "Put back the version of {title} saved {date} on {site}? WordPress keeps the version it has now as a revision too." Lines: "Title: {now} becomes {then}." when the title differs, then the content compared line by line. The button is "Restore".
- Announced after: "Restored {title} to its version of {date}."
- When someone changed the item meanwhile: "{title} was changed on the site after QUILL read it. Nothing was sent; read it again and choose the version there."
- Undo: recorded. Ctrl+Z sends back the title and content as they were and says "{title} is back as it was." If the item changed after the restore: "{title} was changed on the site after the restore, so it was left as it is."
- Menu help: "The site's revisions and autosaves of this item, newest first; each is compared with the item now, line by line, and restored after that preview. The item is read again first, and Ctrl+Z puts it back."
- Without permission: needs edit_posts or edit_pages; tier 2, so Organize and Read Only access refuse it.
- Keyless: "Looked for after a mistake, rarely (rule 9)."
- Code: wordpress_workbench_gaps.py, workbench_item_versions.py, workbench_gap_actions.py.
- Review note: the date in the summary and the announcement is made by stripping "Saved " and cutting at the first comma. friendly_date writes "3 November 2026, 4:12 PM", so the time is cut off. Two versions saved the same day sound identical in the summary and in the closing sentence.
- Review note: in the list, OK means "compare", not "restore". That is a reasonable two-step design, but it is the reverse of Their Application Passwords, where OK in a list means "revoke". The same list dialog means different things in different places.
- Review note: only the title and content are restored. WordPress's own restore also brings back the excerpt; the preview does not say the excerpt is left alone.

### Duplicate as Draft

- How to reach it: context menu only, under More.
- What opens: a Yes/No message box titled "Duplicate as Draft": "Make a draft copy of {title} on {site}, called {title} (copy)? Visitors will not see it." The buttons are "Make a Copy" and "Cancel", and Cancel is the default.
- Announced after: "{title} (copy) is a new draft on {site}. Ctrl+Z moves it to the Trash."
- Undo: recorded. Ctrl+Z moves the copy to the Trash and says "Moved {title} to the Trash."
- Without permission: needs edit_posts or edit_pages; tier 2.
- Keyless: "A copy is made now and then, from the row's context menu (rule 9)."
- Code: wordpress_workbench_parity.py (do_duplicate), workbench_parity.py (duplicate).
- Review note: after the copy is made the list refreshes, and nothing in the handler moves the selection to the copy. Unless the refresh happens to land there, the next Enter opens the original rather than the copy someone presumably wanted to edit. Offering "Open the copy in the editor?" would close the loop.

### Counts by Status

- How to reach it: the item row's context menu (More), or the tree node's context menu (More). No chord.
- Announced: "Posts on {site}: All 12, Mine 3, Published 8, Drafts 2, Pending 1, Scheduled 0, Private 0, Trash 2." Pages say "Pages", and a content type its own name. A view the site refuses is left out. If every view is refused: "{site} would not count its posts for this account." In the wrong place: "Counts by Status works in a site's posts, pages, content types or media."
- Menu help: "How many there are in each of wp-admin's views: All, Mine, Published, Drafts, Pending, Scheduled, Private and Trash; for media, each type and Unattached."
- Without permission: none.
- Keyless: "The tree's status nodes and the status bar count as you go; every count at once is asked now and then (rule 9)."
- Code: wordpress_workbench_parity.py (do_status_counts), workbench_parity.py (status_counts, counts_text).
- Review note: a refused view is silently dropped, so "Private" may simply be missing from the sentence with no hint why. "Private: not shown to you" would be honest.

### Empty Trash...

- How to reach it: the item row's context menu (More), or the tree node's context menu (More). No chord.
- What opens: every item of that kind in the Trash is read. If there are none: "The Trash on {site} has no posts." Otherwise a preview window titled "Empty Trash". Summary: "Delete {n} posts in the Trash on {site} permanently? This cannot be undone, and Ctrl+Z will not bring them back." The list holds the titles. The button is "Delete Permanently".
- Announced after: "Deleted {n} items from the Trash permanently on {site}." with " Not done: {reasons}." when some failed.
- Undo: recorded with no undo, so Ctrl+Z says "{that sentence} This cannot be undone."
- Without permission: needs delete_posts or delete_pages; tier 3, so only Full access. In the wrong place: "Empty Trash works in a site's posts, pages or content types."
- Keyless: "Permanent and occasional: never a bare key (rules 4 and 9)."
- Code: wordpress_workbench_parity.py (do_empty_trash).
- Review note: critical. The preview window makes its action button the default, so Enter in this dialog permanently deletes the whole Trash. Delete Permanently on one item uses a message box whose default is Cancel. The most destructive command in this section is the easiest one to confirm by accident. Every tier 3 preview should default to Cancel.
- Review note: offered on any item row, even a published post in Posts > Published, where it empties the Trash of that whole kind rather than doing anything to the selected row. Its place on the row menu suggests it acts on the row.

### Open in wp-admin

- How to reach it: context menu only, under More (last before Properties).
- Announced before the browser opens: "Opening wp-admin's editor for it, which shows who is editing it now and takes over the lock; WordPress's REST API does not expose the edit lock. You must be signed in to wp-admin in your browser."
- Menu help: "The wp-admin screen for what WordPress's REST API cannot do here: who is editing it now, and for media, scaling the original by numbers. In your browser."
- Keyless: "Leaves QUILL for wp-admin, only for what REST cannot do (rule 9)."
- Code: wordpress_workbench_parity.py (do_dashboard_screen), workbench_parity.py (dashboard_screen).
- Review note: a hand-off to wp-admin. The sentence is honest but long, and it is said every time. The REST explanation could live in F1, leaving "Opening wp-admin's editor. Sign in there if asked."

### Move to Trash

- How to reach it: Delete in the list; Item > Move to Trash (Alt+I, T); context-menu row 5.
- What opens: one item goes straight to the Trash with no question. Several ask first, in a message box titled "Move to Trash": "Move {n} items on {site} to the Trash?", with "Move to Trash" and "Cancel" (Cancel default).
- Announced after: "Moved {n} item(s) to the Trash on {site}. Ctrl+Z puts them back." With failures, "Moved {k} of {n} items to the Trash on {site}. Not done: {title}: {reason}." (the first three, then "and {n} more").
- Already in the Trash: "That is already in the Trash. Shift+Delete deletes it permanently."
- From the status bar: "Delete and Ctrl+Z act on the list. F6 moves back to it."
- Undo: recorded. Ctrl+Z restores each moved item to the status it had (published stays published) and says "Restored {n} items from the Trash."
- Menu help: "Into WordPress's Trash, where Restore brings it back. Delete."
- Without permission: needs delete_posts or delete_pages ("Deleting pages needs the Editor role or higher. You are an Author on {site}."); tier 1, so Organize access allows it and Read Only refuses.
- Code: wordpress_workbench_commands.py (do_trash), workbench_edit.py (trash, restore), workbench_parity.py (each, outcome).
- Review note: "Ctrl+Z puts them back." is said for a single item too.

### Restore from Trash

- How to reach it: Ctrl+Shift+R; Item > Restore from Trash (Alt+I, E); context-menu row 6.
- What it acts on: the selected items whose status is trash; otherwise "Nothing selected is in the Trash."
- Announced after: "Restored {n} items from the Trash, as drafts or waiting on {site}."
- Undo: recorded. Ctrl+Z moves them back and says "Moved them back to the Trash."
- Menu help: "Out of the Trash, as a draft."
- Without permission: needs edit_posts or edit_pages; tier 1.
- Code: wordpress_workbench_commands.py (do_restore).
- Review note: two restores behave differently. Ctrl+Z after Trash puts a published post back as published. Restore from Trash on the same post brings it back as a draft, which is WordPress's own rule. A listener who trashed a post yesterday and restores it today finds it is no longer on the site, and the closing sentence's "as drafts or waiting" is easy to miss.
- Review note: it is one of the six top rows on every item, including published posts where it can only say "Nothing selected is in the Trash." It is most useful in the Trash node, where it is the only row that matters.

### Delete Permanently...

- How to reach it: Shift+Delete in the list; Item > Delete Permanently (Alt+I, D); context menu, first row under More.
- What opens: a Yes/No message box titled "Delete Permanently": "Delete {n} item(s) from {site} permanently? This cannot be undone: {first five titles}" and " and more" beyond five. The buttons are "Delete Permanently" and "Cancel", and Cancel is the default.
- Announced after: "Deleted {n} items permanently on {site}. This cannot be undone." with " Not done: ..." for failures.
- Undo: recorded with no undo. Ctrl+Z says "Deleted {n} items permanently on {site}. This cannot be undone." (see the undo section below for what that does to older changes).
- Menu help: "Gone for good, after you confirm by name. Shift+Delete."
- Without permission: needs delete_posts or delete_pages; tier 3, Full access only.
- Code: wordpress_workbench_commands.py (do_delete_permanently).
- Review note: "after you confirm by name" suggests typing the name, which some products require for a permanent delete. It is a Yes/No box that lists the names. The help should say "after a confirmation that names it".
- Review note: it works on items that are not in the Trash, skipping WordPress's safety net. wp-admin offers Delete Permanently only from the Trash view.

### New Here (Ctrl+N), on Posts, Pages and content types

- How to reach it: Ctrl+N; File > New Here (Alt+F, N); the tree node context menu row 2.
- What opens: a one-line text box titled "New Post" (or "New Page", or "New {type}"), prompt "Title:", help "The title it starts with. It is saved as a draft." It also works on the status children such as Posts > Drafts.
- Empty title: "It needs a name, so nothing was made."
- Preview or confirmation: none; it is made at once as a draft.
- Announced after: "Made the post {title} on {site} as a draft."
- Undo: not recorded in Change History, so Ctrl+Z afterwards undoes whatever was recorded before it.
- Menu help: "Make something new here. Ctrl+N." (context menu) and "A new user or password, where you are." (File menu).
- Without permission: no requirement. Nothing checks your Workbench access first, because the check is looked up on the selected row's own actions, and New Here is a node action. A site that refuses the draft says so.
- Code: wordpress_workbench_lists.py (do_new_here), workbench_create.py (creatable, create).
- Review note: the File menu's help, "A new user or password, where you are.", is stale. New Here now makes posts, pages, terms, menus and more.
- Review note: in Posts > Pending or Posts > Scheduled the new item is still a draft, so it does not appear in the list you are standing in. Nothing says where it went, and focus does not move to it. Offering to open the new draft in the editor would finish the job.
- Review note: Read Only access, Safe Mode and View As Role ("Nothing can be changed until you stop") do not stop Ctrl+N here.

### Properties (Alt+Enter), one item

- How to reach it: Alt+Enter; Item > Properties (Alt+I, P); the last context-menu row.
- What opens: the item is read again, then a sheet titled "{title} Properties - {site}" with a page per tab (Ctrl+Tab moves between tabs).
- General: Title; Slug ("The last part of its address."); Status, a choice of publish, draft, pending, future, private; Password, a masked box that opens empty ("Visitors type this to read it. Write only: what you type replaces it."); Author, a choice of "Name (number)"; Published, a date such as 2026-11-09T14:00; Last changed (read only); Address (read only).
- Organize: one list field per taxonomy the item carries (Categories, Tags and any plugin's), "by name or number, separated by commas"; on posts, Format (standard, aside, chat, gallery, link, image, quote, status, video) and Sticky (a check box, "Kept at the top of the posts page.").
- Featured Image: the picture by title and number, with buttons "Choose from Library..." (Alt+H) and "Remove Featured Image" (Alt+R). Choose from Library lists the site's pictures as "{title}, alt text: {alt}" or "{title}, no alt text".
- Excerpt: one multi-line field.
- Discussion: Comments and Pingbacks, each open or closed.
- Template and Parent (pages, and items with a parent): Template (a choice, with "Default template" in words), Parent number ("0 for a top-level page."), Order.
- Meta, from the route's registered meta; and a page for Advanced Custom Fields where the site shows them.
- Buttons: Copy as Text (Alt+T), OK, Apply (Alt+A), Cancel. A sheet you may not save shows Close instead of Cancel, and fields you may not change are read-only text boxes whose F1 is the reason.
- Announced after a save: "Saved {n} changes to {title} on {site}." plus " The site did not keep: {fields}." when the answer differs; "Nothing changed on this row."; a term name that matches nothing: "{label}: nothing on {site} is called {names}. Make it first, or check the spelling."
- Conflict: a message box titled "Changed on the Site": "{title} was changed on {site} after you opened it. Nothing was sent. Send your changes anyway, replacing theirs?" with "Use Mine" and "Cancel".
- After a slug change the redirect offer may follow (Redirection plugin).
- Undo: recorded. Ctrl+Z says "Put {title} back as it was."
- Without permission: the whole sheet is read only with the role or access sentence as every field's F1.
- Code: wordpress_workbench_sheets.py, workbench_sheets.py (_item_sheet, values_for), workbench_edit.py (save), quill/ui/workbench_sheet_editor.py.
- Review note: the Status, Comments, Pingbacks and Format choices are WordPress's raw slugs ("publish", "future", "open"). The list column says "Published" and "Scheduled" for the same values. A listener meets two vocabularies for one field.
- Review note: Published is typed as "2026-11-09T14:00", while Approve and Schedule and Move to Another Day take "2026-11-20 9:00 AM". Three ways to set a date, two formats.

### Properties on several items at once

- How to reach it: select several rows, then Alt+Enter.
- What opens: a sheet titled "{n} items Properties - {site}". Fields that differ show "Mixed" and are never sent if left. General: Status, Author number, Comments, Pingbacks, Sticky (three-state), Template, Parent number, Featured image (with Choose from Library and Remove Featured Image). Categories and Tags: Add categories, Remove categories, Add tags, Remove tags.
- Refusals: rows of different kinds or sites: "Several rows at once need to be the same kind, from one site."
- Confirmation: a message box titled "Change Several": "Change {n} items on {site}: {Field} to {value}?" and the titles (first 25), with "Change Them" and "Cancel" (Cancel default).
- Announced after: "Changed {k} of {n} on {site}." Failures then ask, in a box titled "Some Were Not Changed", "{n} were not changed: ... Try them again?" with "Try Again".
- Undo: recorded. Ctrl+Z says "Put {n} back as they were."
- Code: wordpress_workbench_sheets.py (_batch_sheet, _bodies, _send_batch), wordpress_workbench_batch_sheets.py.
- Review note: critical. Add categories, Remove categories, Add tags and Remove tags only understand "News (12)" or "12". A plain name such as "News" is silently dropped (the code calls term_ids with no name table and ignores what it cannot match). The confirmation still says "Add categories to News", the save reports success, and nothing was filed. The one-item sheet refuses an unknown name out loud; the batch sheet should resolve or refuse names the same way.
- Review note: on one item Author is a choice of names; on several it is "Author number", a text box wanting a number. The same field asks two different things.

### Ctrl+Z and Change History, as they behave across these sections

- How to reach them: Edit > Undo WordPress Change, Ctrl+Z (Alt+E, U), in the list only; Edit > Change History, Ctrl+Shift+H (Alt+E, H).
- Change History opens a read-only report titled "Change History", newest first, numbered, with " (cannot be undone)" after entries that cannot be. Copy All copies it. With nothing yet: "No changes made in the Workbench yet."
- Ctrl+Z with nothing recorded: "Nothing to undo."
- Changes recorded with an undo: Publish, Move to Trash, Restore from Trash, Approve, Unapprove, Spam, Not Spam, Duplicate as Draft, Properties saves (one or several), Earlier Versions, Attach, Detach, Replace File (repoint path), Change Role (one or several).
- Changes recorded with no undo: Delete Permanently, Empty Trash, Approve and Schedule, Send Back with a Note, Assign a Reviewer, Move to Another Day, Copy to Site, Edit Picture, Replace File (in place), Remove (one or several), Set New Password, Add a Person, Invite from a Spreadsheet, Revoke (both places).
- Changes not recorded at all: New Here (items, terms and New Application Password), Reply, Not Spam and Allow This Sender, Merge Into, Convert to Category or Tag, Empty Spam, Empty Comment Trash, Regenerate Sizes.
- Code: quill/core/workbench/history.py, wordpress_workbench_sheets.py (do_undo, do_history).
- Review note: critical. When the newest entry has no undo, Ctrl+Z says "{summary} This cannot be undone." and leaves that entry on top. It never moves past it, so every older change that could be undone becomes unreachable for the rest of the session. One Delete Permanently, Send Back or Move to Another Day locks out the undo of everything before it. Skipping past an entry that cannot be undone, and saying so, would keep the rest reachable.
- Review note: critical, the opposite problem. Reply, Merge Into, Convert, Allow This Sender, New Here and the two Empty commands are not recorded. Pressing Ctrl+Z straight after a Reply does not touch the reply; it undoes whatever came before it (an Approve, a role change) and says so in words that do not mention the reply. A listener expects Ctrl+Z to undo the last thing they did.
- Review note: when an undo itself fails (a conflict), the error is said and the entry stays on top, so the next Ctrl+Z tries the same failing undo again.
- Review note: the summary is reused as the start of the refusal, so the listener hears, for example, "Published on {site}. This cannot be undone.", a sentence about what was done followed by one about what cannot be. "Cannot undo: published on {site}." would put the answer first.

## Media

The Media Library is one list with six filtered children. Its rows are "media" rows. Enter opens the file in your browser (View or Play), except in picking mode, where Enter inserts it into the document that asked. The context menu has thirteen commands plus Properties: six on top, seven under More. WordPress keeps no Trash for media, so Delete says so and points at Shift+Delete. Replace File, just built, is the most involved command in the Workbench and has the most review notes. Alt text, the field that matters most to this audience, is on the second tab of Properties.

### The tree nodes and what the list shows

- Media: Go > Media, Ctrl+Shift+3 (Alt+G, M). Columns: Title, Type, Alt text, Uploaded.
- Under Media: Pictures, Audio, Video, Documents, Unattached and Without Alt Text, with the same columns; Group (View > Group By); and the Housekeeping node (files used nowhere, duplicates, very large files and so on, covered in its own section).
- The Type cell says picture, audio, video or document. The Alt text cell is "none" for a picture without alt text and empty for anything that is not a picture.
- View > Columns adds: File type, Size, Attached ("post 12" or "not attached"), Author, Number, Slug, Site.
- The details pane: "{title}, picture, 1.2 MB, alt text: {alt}, uploaded {date}." or "..., no alt text, ...".
- F1 on the tree, Media: "Pictures, audio, video and documents in the media library." Without Alt Text: "Pictures with no alt text, which a screen reader cannot describe." Unattached: "Media not attached to any post or page." Pictures, Audio, Video and Documents borrow Media's sentence.
- F1 on a media row: "A file in the media library. Enter opens it; Alt+Enter edits its alt text."
- Needs My Attention > Accessibility lists pictures without alt text from every site, as media rows with the same menu.
- Code: workbench_tree.py, workbench_rows.py (media_row), workbench_listing.py.

### The media row's context menu

- On top: View or Play, Insert into the Document, Copy Link, Copy to Site..., Replace File..., Edit Picture....
- Under More: Regenerate Sizes, Attach to a Post or Page..., Detach, Download..., Counts by Status, Open in wp-admin, Delete Permanently....
- Then Properties....
- Review note: Insert into the Document is the second row on every media row, and it works only in picking mode. Outside picking mode it is enabled and can only explain itself. It should be hidden, or greyed, unless the Workbench was opened by Insert > Picture from the Media Library.
- Review note: Edit Picture, Regenerate Sizes and Download are offered on audio, video and documents too. Edit Picture and Regenerate Sizes refuse with "Edit Picture works on a picture in the Media Library." and "Regenerate Sizes works on a picture in the Media Library." Greying them on non-pictures would spare a round trip.
- Review note: the Item menu has none of the media commands except Copy to Site and Delete Permanently, and its Delete row still reads "Move to Trash" on a media row.

### View or Play

- How to reach it: Enter (the default); the first context-menu row; Shift+Enter (Open on the Site) does the same.
- What opens: your browser at the file's address (source_url).
- Failure: "This has no address on the site yet."
- Menu help: "Open the file in your browser."
- Without permission: none.
- Code: wordpress_workbench_commands.py (do_open_on_site).
- Review note: Enter, the most-pressed key, leaves QUILL. Arrowing through the library and pressing Enter to hear what a file is takes the listener into a browser tab every time. Read in Full (the details pane), or an in-app play for audio, would be a gentler default, with View or Play second.

### Insert into the Document

- How to reach it: Enter in picking mode; the context-menu row 2 at any time.
- Picking mode starts from the editor's Insert > Picture from the Media Library. The Workbench opens on that site's Media and says "Picking a file for {document}: Enter on a file inserts it." Enter on a file then inserts it at the caret through the editor's picture dialog, and the editor comes back to the front. Picking ends after one insert or when the Workbench closes.
- Outside picking mode: "Insert into the Document works after Insert > Picture from the Media Library opens the Workbench; then Enter on a file inserts it."
- On a file from another site: "That file is on {site}, and {document} is on {other}. Choose a file in {other}'s Media."
- Menu help: "At the caret of the document Insert > Picture from the Media Library came from; there, Enter does this."
- Keyless: "Enter does it in picking mode, the only time it applies."
- Code: wordpress_workbench_editor_side.py (picked_command, do_insert_picked, open_for_picking).
- Review note: picking mode changes what Enter does, and nothing on the window says so after the first announcement. A listener who arrows away to the tree and back has no cue that Enter now inserts instead of opening a browser. Saying "Picking" in the status bar or the window title would keep the mode audible.

### Copy Link

- How to reach it: Ctrl+Shift+C; Edit > Copy Link (Alt+E, L); context-menu row 3.
- Announced: "Copied." or "Could not copy."
- Menu help: "The file's address. Ctrl+Shift+C."
- Code: quill/ui/workbench_frame_actions.py.

### Copy to Site...

- The same command, dialogs and wording as on posts (see Posts and pages). Recorded with no undo.

### Replace File... (just built)

- How to reach it: context-menu row 5 on a media row. No chord and no Item menu entry.
- What opens first: a standard Open box titled "Replace {title} with", All files. Then size and type are checked: "{name} is larger than the 64 MB QUILL sends in one file." and "{name} is a {type}, which a WordPress Media Library does not take."
- The site's index, plugins and the file itself are then read in the background.
- Path one, the site lists a replace route (a plugin's): a preview titled "Replace File". Summary: "Replace {title} on {site} with {new name}?" Lines: "Now: {old file in words}.", "New: {new file in words}.", "The address stays the same: {address}", "Pictures have their sizes remade after the file is replaced.", "The type changes from {a} to {b}." when it does, "Sent to {route}, a route {site}'s plugin lists; QUILL reads the file back afterwards to check the address.", and "The old file cannot be put back by QUILL." The button is "Replace File", the default.
- Path one, announced after: "Replaced. The address is the same, {address}, and the site now has {file in words}." or, when the read-back address differs, "The site took the file, but its address is now {new}, not {old}. Links to the old address may break." Recorded with no undo.
- Path two, no replace route: a list titled "Replace File", prompt "How:", with "Upload it as a new file and point every use at it (the address changes)" and, only when Enable Media Replace is active, "Open Enable Media Replace in wp-admin (the address stays the same)". Help: "WordPress has no way to swap a file in place over REST, and {site} lists no plugin route that does. Uploading as a new file gives it a new address; QUILL then points every post, page, pattern and featured image that used the old file at the new one. Enable Media Replace, where it is active, keeps the address, but only in wp-admin."
- Enable Media Replace chosen: "Opening {title}'s edit screen, where Enable Media Replace's Replace Media box is. You must be signed in to wp-admin in your browser. Press F5 here after." Then the browser opens.
- Upload and repoint chosen: every use is found, then a preview titled "Replace File". Summary: "Upload {new name} to {site} as a new file and point every use of {title} at it? The file's address changes." Lines: Now and New; "The address changes. The old one is {address}; the new one is whatever the site gives the upload."; "{n} items use it, and each is pointed at the new file:"; one line per item ("Post About: {where it is used}"); "Not changed: ..." and "Not read, so not changed: ..."; "Ctrl+Z puts every item back; the new file stays in the library." The button is "Upload and Repoint", the default.
- After that preview, a list titled "The Old File", prompt "Old file:", with "Keep the old file in the library" and "Delete the old file permanently once every use is moved (cannot be undone)". Help: "WordPress's Media Library has no Trash, so the old file is either kept or deleted for good. Deleting happens only when every use was moved."
- Then, only where the Redirection plugin is present, a Yes/No box titled "Add a Redirect": "Add a redirect on {site} from {old address} to the new file's address, so links from other websites keep working? It goes through the Redirection plugin." with "Add Redirect" and "Cancel".
- Path two, announced after: "The file's address changes; QUILL updated {n} places that used it." then " {k} were not changed: {first}." when some failed, then the redirect outcome ("A redirect now sends the old address to the new one." or "No redirect was added: the Redirection plugin has no group to keep it in, so links from other websites to the old address will break." or "The redirect was not added ({reason}), so links from other websites to the old address will break.") or, with no redirect, " Links from other websites to the old address will break unless a redirect is added.", and finally " The old file is still in the library." or " The old file was deleted."
- Undo: on path two, recorded. Ctrl+Z puts every edited item back and adds " The new file stays in the library." On path one, recorded with no undo.
- Menu help: "Put a new file in this one's place, after a preview of both. Where the site has a replace route the address stays the same; otherwise the new file is uploaded and every page, post and featured image that used the old one is pointed at it, which Ctrl+Z puts back."
- Without permission: needs upload_files ("Changing media needs the Author role or higher. You are a Contributor on {site}."); tier 2, Full access only.
- Keyless: "Opens a file picker and a preview, now and then (rule 9)."
- Code: wordpress_workbench_media_replace.py, media_replace.py, workbench_site_files_actions.py.
- Review note: critical. If you chose "Delete the old file permanently", Ctrl+Z still puts every item back, pointing them at the old file, which no longer exists. The undo turns a working site into one full of broken images and links. Either refuse the undo after a delete, or refuse the delete when an undo is wanted, and say so in the old-file choice.
- Review note: the two decisions with the largest consequences, deleting the old file and adding a redirect, are asked after the preview, so the preview the listener approved did not include them. Asking them first, and showing them as lines in the preview, would make the preview true.
- Review note: when Enable Media Replace is not active, the "How:" list has a single row. It is a dialog with one choice, and Enter just accepts it. Saying the fact in the preview's summary would remove a step.
- Review note: the help text says "every page, post and featured image" and the dialog says "every post, page, pattern and featured image". Small, but a listener checking whether patterns are covered hears two answers.
- Review note: the closing sentence after a repoint can run past sixty words. Splitting it into the outcome now and the rest in a report window would be easier to follow.

### Edit Picture...

- How to reach it: context-menu row 6. No chord.
- What opens: the edits the site's REST index allows are read, then a list titled "Edit {title}", prompt "Edit:", with the rows the site takes from: "Turn a quarter to the right", "Turn a quarter to the left", "Turn upside down", "Flip left to right, as in a mirror", "Flip top to bottom", "Crop to a square", "Crop to 4 by 3, landscape", "Crop to 16 by 9, widescreen", "Crop to 3 by 4, portrait", then "Crop by numbers, in percent..." when crop is allowed, and "Scale the original to a size (opens wp-admin)..." always. Help: "The edits {site} takes. It is {w} by {h}. WordPress keeps the original and makes the edit a new picture. Scale opens wp-admin, because the REST route cannot scale."
- Crop by numbers: a text box titled "Crop by Numbers", prompt "Crop, in percent (left, top, width, height):", filled with "0, 0, 100, 100". Errors (the dialog closes): "Give four numbers in percent: from the left, from the top, width and height, such as 10, 0, 80, 100.", "Width and height must be more than 0, and nothing below 0.", "The crop goes past the picture's edge: left plus width, and top plus height, may be at most 100."
- Scale: hands off to Open in wp-admin.
- Preview: titled "Edit Picture". Summary: "Edit {title} on {site}? WordPress keeps the original and makes the edit a new picture in the library." Lines: the edit in words ("Turn a quarter to the right." or "The crop keeps 80 percent of the width, starting 10 percent from the left, and 100 percent of the height, starting 0 percent from the top.") and "Sent to wp/v2/media/{id}/edit". The button is "Make Edited Copy".
- Announced after: "Edited copy made on {site}: {name}. The original is unchanged; Shift+Delete on the copy removes it."
- Undo: recorded with no undo, which blocks older undos (see Posts and pages).
- Without permission: needs upload_files; tier 2. Not a picture: "Edit Picture works on a picture in the Media Library."
- Keyless: "Opens a dialog, a few times a site's life (rule 9)."
- Code: wordpress_workbench_parity.py (do_edit_picture, _send_picture_edit), workbench_parity.py, media_edit.py.
- Review note: the preview's line "Sent to wp/v2/media/{id}/edit" is a REST route, not words. It is jargon in a dialog that otherwise speaks plainly.
- Review note: the edit is undoable in practice (delete the copy), and the closing sentence even says how, but Ctrl+Z will not do it and instead blocks everything older.
- Review note: a crop typing mistake closes the dialog and loses the four numbers.

### Regenerate Sizes

- How to reach it: context menu, under More.
- No confirmation. Announced after: "Sizes remade for {title} on {site}: {n} sizes."
- Undo: not recorded.
- Menu help: "Remake the picture's thumbnail and other sizes from its original."
- Without permission: needs upload_files; tier 2.
- Keyless: "Needed after an edit or a theme change, rarely (rule 9)."
- Code: wordpress_workbench_parity.py (do_regenerate_sizes), media_pieces.py.

### Attach to a Post or Page...

- How to reach it: context menu, under More.
- What opens: a text box titled "Attach {title}", prompt "Post or page, by words or number:", help "Words from its title, or its number. QUILL lists what matches." Words are searched on the site; several matches give a list titled "Attach {title}", prompt "Attach to:", rows "{title} ({type})", help "The post or page the file is attached to."
- No match: "Nothing on {site} matches {words}."
- Confirmation: a message box titled "Attach": "Attach {title} to {name} on {site}?" with "Attach" and "Cancel".
- Announced after: "{title} is attached to {name}. Ctrl+Z undoes it." A conflict: "{reason} Press F5 and try again."
- Undo: recorded. Ctrl+Z says "{title} put back."
- Menu help: "Find a post or page by words or number and attach the file to it. Ctrl+Z puts it back."
- Without permission: needs upload_files; tier 2.
- Keyless: "Uploads from the editor attach themselves; this is the exception (rule 9)."
- Code: wordpress_workbench_parity.py (do_attach, _save_post).
- Review note: a number skips the search and is not checked. "Attach {title} to number 99 on {site}?" is asked even if post 99 does not exist, and the name in the confirmation is "number 99", not a title.

### Detach

- How to reach it: context menu, under More.
- Not attached: "{title} is not attached to anything."
- Confirmation: a message box titled "Detach": "Detach {title} from post {number} on {site}? It stays in the library." with "Detach" and "Cancel".
- Announced after: "{title} is attached to nothing. Ctrl+Z attaches it again."
- Undo: recorded. Ctrl+Z says "{title} put back."
- Menu help: "Leave it in the library, attached to nothing. Ctrl+Z attaches it again."
- Keyless: "The rare undoing of an attachment (rule 9)."
- Code: wordpress_workbench_parity.py (do_detach).
- Review note: the confirmation names the post by number only ("from post 412"). The listener cannot tell what they are detaching it from.

### Download...

- How to reach it: context menu, under More.
- What opens: a standard Save As box titled "Download", with the file's own name filled in; overwriting asks first.
- Announced after: "Saved {title} to {full path}."
- Menu help: "Save the file to this computer, where you choose."
- Without permission: none.
- Keyless: "Opens a Save As box, now and then (rule 9)."
- Code: wordpress_workbench_parity.py (do_download), media_tools.py.
- Review note: the closing sentence reads out the whole path, which can be long. "Saved {file name}." is enough, since the person just chose the folder.
- Review note: the 2026-11-13 audit table says a file over 512 MB "opens in the browser". The code does not do that. download_file raises a too-big error and that error is what is said.

### Counts by Status (media)

- Announced: "Media on {site}: All {n}, Mine {n}, Pictures {n}, Audio {n}, Video {n}, Documents {n}, Unattached {n}."
- Otherwise as on posts.

### Open in wp-admin (media)

- Announced: "Opening wp-admin's Edit Media screen, whose Edit Image scales the original to a width and height; WordPress's REST edit route only rotates, flips and crops. You must be signed in to wp-admin in your browser."
- A hand-off to wp-admin.

### Delete Permanently... (media), and the Delete key

- How to reach it: Shift+Delete; Item > Delete Permanently (Alt+I, D); context menu, last under More.
- The same message box as on posts: "Delete {n} item(s) from {site} permanently? This cannot be undone: {names}." Cancel is the default.
- Announced after: "Deleted {n} items permanently on {site}. This cannot be undone."
- Delete (the Trash key) on a media row: "WordPress keeps no Trash for this, so it can only be deleted permanently, with Shift+Delete."
- Without permission: needs upload_files ("Changing media needs the Author role or higher."); tier 3.
- Code: wordpress_workbench_commands.py.
- Review note: the confirmation does not say where the file is used. By Name > Media Usage and Housekeeping already know, and the Housekeeping node "shows usage before Move to Trash". The plain Delete Permanently on a Media row can remove a picture that twenty pages show, with no warning.
- Review note: the role sentence says "Changing media" for a permanent delete, which undersells it.

### Properties (Alt+Enter), one file

- What opens: a sheet titled "{title} Properties - {site}".
- General: Title; File (read-only link); Type; Size; Dimensions ("{w} by {h}"); Uploaded; Uploaded by.
- Alt Text and Caption: Alt text ("What a picture shows, for people who cannot see it."); Caption (multi-line).
- Description: one multi-line field.
- Attached To: "Attached to number".
- Sizes: read only, one line per size ("thumbnail: 150 by 150").
- Buttons, saving, conflicts and Ctrl+Z as on posts ("Saved 1 change to {title} on {site}."; undo "Put {title} back as it was.").
- Without permission: needs upload_files; otherwise the sheet is read only with the reason.
- Code: workbench_sheets.py (_STATIC "media"), wordpress_workbench_sheets.py.
- Review note: the row's own F1 says "Alt+Enter edits its alt text", but alt text is on the second tab. Alt+Enter lands on Title, and the listener must press Ctrl+Tab to reach Alt text. For a library whose main accessibility job is alt text, Alt Text and Caption should be the first page, or Alt text the first field.
- Review note: "Uploaded by" reads author_name, which the media route does not send and values_for does not fill. It is very likely always empty.
- Review note: "Attached to number" is a bare number field. Attach to a Post or Page finds posts by words; the sheet does not.

### Properties on several files

- Select several media rows and press Alt+Enter: a sheet titled "{n} items Properties - {site}" with Title, Alt text, Caption and Description, Mixed where they differ.
- Confirmation "Change Several", outcome "Changed {k} of {n} on {site}.", Ctrl+Z "Put {n} back as they were."
- Review note: setting one Alt text on many different pictures is rarely right, and nothing warns that every selected picture will get the same description.

### New Here on Media

- Ctrl+N on Media says: "New Here makes posts, pages, custom items, categories, tags, terms, menus, people and application passwords. Choose one of those nodes first."
- Review note: wp-admin's Media screen has Add New. Uploading from the Workbench is not offered here; the sentence lists everything except what the listener is looking at.

## Categories and tags

Categories, Tags and every taxonomy a plugin adds share the "term" row. Enter shows the posts filed under the term. The context menu has five commands and Properties, so nothing hides under More. Merge Into and Convert are tier 3 and preview with a count, but neither is recorded in Change History, and Convert previews less than Merge does.

### The tree nodes and what the list shows

- Categories: a tree by parent. Columns: Name, Level, Count, Slug.
- Tags: Columns: Name, Count, Slug.
- More Taxonomies: one row per plugin taxonomy; Enter opens its own node of terms.
- View > Columns adds: Number, Description, Parent, Site.
- The details pane: "{name}, {n} items." followed by the description when there is one.
- F1 on the tree, Categories: "The site's categories, as a tree. Show Its Posts lists what is filed there." Tags: "The site's tags. Merge Into folds one into another." More Taxonomies: "The ways of grouping this site's plugins add." A plugin taxonomy: "The terms of one taxonomy a plugin added."
- F1 on a term row: "A category, tag or term. Enter lists its posts; Merge Into folds it into another."
- There is no Go menu row for Categories or Tags.
- Code: workbench_tree.py, workbench_rows.py (term_row).
- Review note: Categories and Tags have no Go key, while Posts to Site Health each have one. A listener reaches them by the tree.

### The term row's context menu

- In order: Show Its Posts, Merge Into..., Convert to Category or Tag..., Copy to Site..., Delete Permanently..., Properties....

### Show Its Posts

- How to reach it: Enter (the default); context-menu row 1.
- What happens: the Posts node is selected with "categories:{id}" (or "tags:{id}", or the taxonomy's own name) in the filter box, the filter runs, and focus goes to the list. The filter says "{n} shown." or "Filtering."
- Menu help: "The posts filed under it."
- Without permission: none.
- Code: wordpress_workbench_commands.py (do_show_posts, _show_filtered).
- Review note: it always lands in Posts. For a plugin taxonomy that belongs to a custom content type (an Events category, say), the Posts list is filtered to nothing, or refuses the filter. It should open the content type the taxonomy is on.
- Review note: when the filter goes to the site, the first thing said is "Filtering.", and the count of what was found is not announced when it arrives.

### Merge Into...

- How to reach it: Ctrl+Shift+G; Item > Merge Into (Alt+I, M); context-menu row 2.
- What opens: a list titled "Merge {name} Into", prompt "Into:", listing the other rows in the current list by name. Help: "Everything filed under {name} is filed under the one you choose, then {name} is deleted."
- Refusals: "Merge Into works on a category, tag or term." and "There is no other term here to merge into."
- Then everything filed under it is counted, and a preview titled "Merge {name} Into {target}". Summary: "{n} items filed under {name} will be filed under {target}, then {name} is deleted. This cannot be undone with Ctrl+Z." Lines: one per item, as "posts 123". The button is "Merge", the default.
- Announced after: "Merged {name} into {target}." or "{n} items could not be moved, so {name} was kept. Try again in a moment."
- Undo: not recorded. The preview says Ctrl+Z will not undo it; pressing Ctrl+Z will undo whatever change came before.
- Menu help: "File its posts under another term, then delete it. Ctrl+Shift+G."
- Without permission: needs manage_categories ("Managing categories and tags needs the Editor role or higher. You are an Author on {site}."); tier 3, Full access only.
- Code: wordpress_workbench_lists.py (do_merge_into), workbench_create.py (merge_preview, merge_terms).
- Review note: the preview's lines are a route word and a number ("posts 123", "posts 98"), not titles. A listener hears a column of numbers and cannot check what moves.
- Review note: the "Into:" list holds only the rows already loaded, by name only. Two categories called "News" under different parents sound identical, and a term past the first 300 is not offered.
- Review note: the tier 3 preview defaults to Merge, so Enter merges and deletes.

### Convert to Category or Tag...

- How to reach it: Ctrl+Shift+K; Item > Convert to Category or Tag (Alt+I, V); context-menu row 3.
- Refusals: "Convert works on a category or a tag." and "Only a category becomes a tag, or a tag a category."
- What opens: a Yes/No message box titled "Make {name} a Category" (or "a Tag"): "Make {name} a category on {site}? Every post filed under it moves to the category, and the old one is deleted." with "Convert" and "Cancel" (Cancel default).
- Announced after: "{name} is now a category." or "{n} posts could not be moved, so {name} was kept."
- Undo: not recorded.
- Menu help: "Make a tag a category, or a category a tag, posts and all. Ctrl+Shift+K."
- Without permission: needs manage_categories; tier 3.
- Code: wordpress_workbench_lists.py (do_convert_term), workbench_create.py (convert_term).
- Review note: Convert does the same kind of change as Merge (move every post, delete the term) but previews less. It gives no count, no list and no "cannot be undone" warning; Merge gives all three. They should share one preview.
- Review note: on a partial failure the new term has already been made and some posts already moved, yet the sentence says only that the old term "was kept". The site is left with both terms and the posts split between them, and the listener is not told.
- Review note: converting a category with child categories or a parent says nothing about the hierarchy, which a tag cannot hold.

### Copy to Site... (terms)

- The same command and dialogs as on posts. Recorded with no undo.

### Delete Permanently... (terms), and the Delete key

- Shift+Delete; Item > Delete Permanently (Alt+I, D); context-menu row 5. The same message box: "Delete {n} item(s) from {site} permanently? This cannot be undone: {names}." Cancel default.
- Announced after: "Deleted {n} items permanently on {site}. This cannot be undone."
- Delete on a term row: "WordPress keeps no Trash for this, so it can only be deleted permanently, with Shift+Delete."
- Without permission: needs manage_categories; tier 3.
- Review note: the confirmation does not say how many posts lose the term, though the Count column already knows. "News is on 34 posts" belongs in that sentence.

### New Here (Ctrl+N), on Categories, Tags and plugin taxonomies

- Categories: three text boxes in a row, each titled "New Category": "Name:" ("Its name, as the site shows it."), "Parent number (optional):" ("0 or empty for a top level."), "Description (optional):" ("A sentence about it, or nothing.").
- Tags and plugin taxonomies: "Name:" and "Description (optional):".
- Empty name: "It needs a name, so nothing was made."
- Announced after: "Made the category {name} on {site}."
- Undo: not recorded.
- Code: wordpress_workbench_lists.py (do_new_here), workbench_create.py.
- Review note: three separate modal dialogs, one after another, each with its own title read out, where one small form would do. Escape on the second throws away the first.
- Review note: the parent is asked by number only. Anything that is not a number is silently ignored and the category is made at the top level.

### Properties (Alt+Enter), a term

- What opens: a sheet titled "{name} Properties - {site}". General: Name, Slug, Description, Parent number ("0 for none. Categories only."). Count: Items and Address, read only. Custom Fields, when the taxonomy has registered meta or Advanced Custom Fields.
- Save, conflicts and Ctrl+Z as on posts.
- Without permission: needs manage_categories.
- Several terms at once: "Several at once can be changed for posts, pages, custom items and media."
- Code: workbench_sheets.py (_STATIC "term").
- Review note: Parent number is shown on tags too, with help that says "Categories only." A field that cannot apply should not be there.

## Comments

Comments share one row kind across the site's Comments node, its four status children, and Needs My Attention > Comments Waiting. Enter reads the comment in the details pane. Moderation (Approve, Unapprove, Spam, Not Spam) is fast, one key each, works on many rows, reports each one, and Ctrl+Z puts them back. Around it, though, Reply posts with no preview and no undo, Not Spam does not mean approved, Allow This Sender cannot actually allow anyone, and the two Empty commands on the Site menu escape the Workbench's access limits.

### The tree nodes and what the list shows

- Comments: Go > Comments, Ctrl+Shift+4 (Alt+G, C). Columns: Author, On, Status, When.
- Under Comments: Waiting, Approved, Spam, Trash, and Group.
- Status cells say Waiting, Approved, Spam or Trash.
- View > Columns adds: Email, Website, IP address, Type, Parent, Post, Number, Site. Email and IP address come only for someone who can moderate comments.
- The details pane: "{author} on {post}, {date}: {the comment's text}."
- F1 on the tree, Comments: "Every comment on the site. Delete moves one to the Trash." Waiting, Approved, Spam and Trash borrow it. Needs My Attention > Comments Waiting: "Comments held for moderation on every site. Ctrl+Shift+A approves."
- F1 on a comment row: "A comment. Ctrl+Shift+A approves, Ctrl+Shift+S marks it as spam."
- Code: workbench_tree.py, workbench_rows.py (comment_row).

### The comment row's context menu

- On top: Read in Full, Approve or Not Spam, Not Spam and Allow This Sender, Unapprove, Spam, Reply....
- Under More: Move to Trash, Restore from Trash, Delete Permanently....
- Then Properties....

### Read in Full

- How to reach it: Enter (the default); context-menu row 1.
- What happens: focus moves to the details pane, which holds the comment's sentence. Nothing is announced; the screen reader reads the pane.
- Menu help: "Move to the details pane to read it."
- Code: wordpress_workbench_commands.py (do_read).

### Approve, or Not Spam

- How to reach it: Ctrl+Shift+A; Item > Approve, or Not Spam (Alt+I, A); context-menu row 2.
- What it does: on a waiting or unapproved comment, approves it. On a comment held as spam, it does not approve: it puts the comment back in the Waiting queue (status hold), which tells the site's spam plugin it was not spam. Works on several selected comments, one outcome each.
- Preview or confirmation: none.
- Announced after: "{n} item(s) approved on {site}." When every selected comment was spam: "Not spam: {n} item(s) on {site}, and the site was told." With failures: "{k} of {n} items approved on {site}. Not changed: {reason}; ..."
- Refusal on the wrong row: "Choose a comment or a form entry."
- Undo: recorded. Ctrl+Z puts each changed comment back to its old status and says "Put {n} items back as they were."
- Menu help: "Approve it; on a comment held as spam, Not Spam. Ctrl+Shift+A."
- Without permission: needs moderate_comments ("Moderating comments needs the Editor role or higher. You are an Author on {site}."); tier 1, so Organize access allows it.
- Code: wordpress_workbench_commands.py (_moderate, do_approve), workbench_edit.py (set_comment_status).
- Review note: "Not spam: 1 item on {site}, and the site was told." does not say the comment is now waiting, not published. A listener who pressed Approve on a spam comment reasonably believes it is now visible. It needs a second Ctrl+Shift+A, and nothing says so. Either approve it, or say "back in Waiting; Ctrl+Shift+A again approves it".
- Review note: the noun is "item", not "comment", in every moderation sentence ("1 item approved"). It is shared with form entries, but in the Comments list it is the wrong word.
- Review note: a mixed selection of spam and held comments gets the plain "approved" sentence, although the spam ones went back to Waiting instead.

### Not Spam, and Allow This Sender

- How to reach it: Ctrl+Alt+W; Item > Not Spam, and Allow This Sender (Alt+I, L); context-menu row 3.
- What it does: approves the comment (straight to approved, unlike Approve on spam), then reads the site's discussion settings to explain what that means.
- Announced after, when the site lets previously approved commenters through: "{author}'s comment is approved, so WordPress lets their next comments through: it allows anyone with an approved comment already. To block them again, mark a comment of theirs as spam." When the site holds every comment: "{author}'s comment is approved. This site holds every comment for moderation, so their next one will wait too; Settings > Discussion in wp-admin changes that."
- Refusal on the wrong row: "Allow This Sender works on a comment."
- Undo: not recorded, so Ctrl+Z undoes something older instead.
- Menu help: "Approve it and let this person's next comments through. Ctrl+Alt+W."
- Without permission: needs moderate_comments; tier 1.
- Code: wordpress_workbench_lists.py (do_allow_sender), workbench_create.py (allow_sender_words).
- Review note: the name promises an allow list that does not exist. The command is "Approve" plus an explanation of WordPress's own rule, and on a site that holds every comment the closing sentence admits the sender is not allowed at all. "Approve and Explain" would be honest; or it should be greyed on such sites.
- Review note: reading the discussion settings needs manage_options. For an Editor the read fails, the empty settings fall back to the first sentence, and an Editor is told the sender's next comments get through whether or not that is true on this site.
- Review note: unlike Approve, it is not recorded, so the two moderation commands next to each other have different undo stories.

### Unapprove

- How to reach it: Ctrl+Shift+U; Item > Unapprove (Alt+I, N); context-menu row 4.
- Announced after: "{n} item(s) unapproved on {site}."
- Undo: recorded, "Put {n} items back as they were."
- Menu help: "Back to waiting. Ctrl+Shift+U."
- Without permission: needs moderate_comments; tier 1.
- Review note: the sentence says "unapproved" while the list and status cell say "Waiting". "Back to Waiting" would match what the listener then hears in the list.

### Spam

- How to reach it: Ctrl+Shift+S; Item > Spam (Alt+I, S); context-menu row 5.
- No confirmation. Announced after: "{n} item(s) marked as spam on {site}."
- Undo: recorded, "Put {n} items back as they were."
- Menu help: "Mark it as spam, which the site's spam plugin learns from. Ctrl+Shift+S."
- Without permission: needs moderate_comments; tier 1.

### Reply...

- How to reach it: Ctrl+Shift+M; Item > Reply (Alt+I, R); context-menu row 6.
- What opens: a multi-line text box titled "Reply to {author}", prompt "Reply:", help "Your reply to {author}, posted as you on {site}." Enter adds a line, so Tab to OK. An empty reply is not sent and nothing is said.
- Preview or confirmation: none; OK posts the reply, threaded under the comment.
- Announced after: "Replied to {author} on {site}."
- Refusal: "Choose a comment to reply to."
- Undo: not recorded. Ctrl+Z afterwards undoes whatever was recorded before the reply.
- Menu help: "Write a reply, posted as you. Ctrl+Shift+M."
- Without permission: needs moderate_comments; tier 2, Full access only.
- Code: wordpress_workbench_commands.py (do_reply), comments.py.
- Review note: a reply is public the moment OK is pressed, and nothing can take it back from here. A multi-line box where Enter does not submit is safe, but there is no preview and no undo for a public post. At least record it, with Ctrl+Z moving the reply to the Trash.
- Review note: needing moderate_comments means an Author cannot reply to comments on their own posts from the Workbench, although WordPress lets them.
- Review note: Approve and Reply (wp-admin's one action) is two commands here: Ctrl+Shift+A, then Ctrl+Shift+M. The audit table says so, but nothing in the Reply dialog notes that replying to a waiting comment leaves it waiting.

### Move to Trash, Restore from Trash, Delete Permanently (comments)

- Move to Trash: Delete; Alt+I, T; under More. Same flow as posts. Announced: "Moved {n} item(s) to the Trash on {site}. Ctrl+Z puts them back." Ctrl+Z puts each back to its old status.
- Restore from Trash: Ctrl+Shift+R; Alt+I, E; under More. A comment comes back as Waiting. Announced: "Restored {n} items from the Trash, as drafts or waiting on {site}."
- Delete Permanently: Shift+Delete; Alt+I, D; under More. The same message box, Cancel default.
- Without permission: all need moderate_comments. Move to Trash and Restore are tier 1; Delete Permanently tier 3.
- Review note: the Restore row's help says "Out of the Trash, as a draft.", which is wrong for a comment; comments come back Waiting.
- Review note: Move to Trash, the action Delete performs and the F1 for the node names, is under More on the comment menu, while Read in Full takes the top.

### Empty Spam...

- How to reach it: Ctrl+Alt+E; Site > Empty Spam (Alt+S, M). Not on any context menu.
- What opens: the spam comments are counted first. None: "No comments are held as spam on {site}." Otherwise a message box titled "Empty Spam": "Delete all {n} comments held as spam on {site} permanently? This cannot be undone." with "Delete All" and "Cancel" (Cancel default).
- Announced after: "Deleted {k} spam comments on {site}." plus " {n} could not be deleted." for failures.
- No site: "Choose a site first."
- Undo: not recorded.
- Menu help: "Delete every comment held as spam on this site, after you confirm."
- Without permission: no capability is checked before it runs; the site refuses each delete if you may not moderate, and those count as "could not be deleted".
- Code: wordpress_workbench_lists.py (do_empty_spam), workbench_create.py (spam_comments, empty_spam).
- Review note: critical. Empty Spam is not a row action, so the Workbench's access check never sees it. Read Only access, Safe Mode, and View As Role, whose own sentence says "Nothing can be changed until you stop", all let Ctrl+Alt+E permanently delete every spam comment after one Yes.
- Review note: "Delete all 1 comments held as spam" for a single comment; Empty Comment Trash gets the singular right.
- Review note: an Editor without the right role hears the confirmation, says yes, and then hears "Deleted 0 spam comments on {site}. 37 could not be deleted." with no reason. A refusal before the question would be kinder.

### Empty Comment Trash...

- How to reach it: Ctrl+Alt+Shift+E; Site > Empty Comment Trash (Alt+S, E).
- What opens: the Trash is counted. Empty: "The comment Trash on {site} is empty." Otherwise a message box titled "Empty Comment Trash": "Delete all {n} comments in the Trash on {site} permanently? This cannot be undone." with "Delete All" and "Cancel" (Cancel default).
- Announced after: "Deleted {k} comments from the Trash on {site}." plus " {n} could not be deleted."
- Undo: not recorded.
- Menu help: "Delete every comment in this site's Trash, after you confirm."
- Without permission: not checked before; the same access gap as Empty Spam.
- Code: wordpress_workbench_moderation.py (do_empty_comment_trash).
- Review note: the same critical access gap as Empty Spam.
- Review note: the two Empty commands sit on the Site menu with access letters M and E, next to each other, and both are destructive. Empty Trash for posts is on the row menu instead. Three "empty" commands live in two places.

### Comment Counts

- How to reach it: Ctrl+Alt+Shift+C; Site > Comment Counts (Alt+S, C).
- Announced: "{site}: 4 waiting, 120 approved, 37 spam and 2 in the Trash; 124 in All, which is waiting and approved together. 2 are yours."
- Menu help: "How many comments wait, are approved, are spam and are in the Trash."
- Code: wordpress_workbench_moderation.py (do_comment_counts), workbench_moderation.py (counts_sentence).
- Review note: "1 are yours" for one comment.
- Review note: the sentence is long and fixed in order. "4 waiting" is what a moderator wants first, and it is first, which is good; "which is waiting and approved together" is an explanation that belongs in F1 after the first hearing.

### Show Its Comments

- On a post or page row; see Posts and pages. It lands here, filtered to the post.

### Properties (Alt+Enter), a comment

- What opens: a sheet titled "Comment by {author} on {post} Properties - {site}" (the row title is its "what" cell).
- General: Author; Email ("Shown only to people who can moderate comments."); Website; IP address (read only, "Where it was sent from. WordPress shows it only to people who can moderate comments."); Written, a date in the site's own time, editable ("When it was written, in the site's own time, such as 2026-11-03T09:00:00. Change it as wp-admin's Edit Comment does."); Status, a choice of approved, hold, spam, trash; Type (read only).
- Text: the comment, multi-line.
- Post: Post number and Post, read only.
- Thread: "Reply to comment number", read only.
- Custom Fields when the site registers comment meta.
- Saving: a comment has no modified time, so its status, text and author fields stand in for the conflict check; a change made elsewhere since opening asks "Use Mine".
- Ctrl+Z: "Put {title} back as it was."
- Without permission: needs moderate_comments; the sheet is read only otherwise.
- Several comments at once: "For several comments, use Approve, Unapprove, Spam or Delete."
- Code: workbench_sheets.py (_STATIC "comment"), workbench_moderation.py (version_of, SHEET_HELP).
- Review note: the Status choice offers "hold", WordPress's internal word, where the list says "Waiting".
- Review note: the sheet's title is built from the row's title, which for a comment is "Comment by {author} on {post}", so the reader hears "Comment by Ann on Hello World Properties - Community Radio". It is long and runs two names together.

### New Here on Comments

- Ctrl+N says: "New Here makes posts, pages, custom items, categories, tags, terms, menus, people and application passwords. Choose one of those nodes first."

## People

People has two lists: Users, everyone on the site with their role, and Application Passwords, your own. A user row's context menu has thirteen commands plus Properties. The three Paid Memberships Pro rows take three of the six top places on every site, whether or not it runs that plugin, so Remove, Set New Password and Send Password Reset are under More. The guards against locking yourself out are careful and well worded. But the Delete and Shift+Delete keys reach Remove and Revoke by a side door that skips the Workbench's access check, and on Application Passwords Shift+Delete skips the guard that protects the password QUILL itself signs in with.

### The tree nodes and what the list shows

- People: a folder holding Users and Application Passwords. F1: "The people on the site and the passwords made for apps."
- Users: Go > Users, Ctrl+Shift+5 (Alt+G, U). Columns: Name, Username, Role, Email. View > Columns adds Number, Slug, Registered, Site. F1: "The people on the site, with their roles. Site > Roles explains each role."
- A role you lack list_users for refuses the node: "Seeing the people on the site needs the Administrator role or higher. You are an Editor on {site}."
- The details pane for a person: "{name}, {username}, {role}, {email}."
- F1 on a user row: "A person on the site. Change Role, Remove, and any exposed membership details are on the context menu."
- Application Passwords: Columns Name, Created, Last used ("never" when unused). F1: "Your application passwords on this site. Ctrl+N makes one." The row for the one QUILL uses adds " QUILL on this computer signs in with it." to its details sentence. F1 on the row: "An application password. Delete revokes it."
- Code: workbench_tree.py, workbench_rows.py (user_row), workbench_load.py (load_app_passwords).
- Review note: F1 on Users says "Site > Roles explains each role", but the Site menu's row is "Roles and What They May Do" (Ctrl+Alt+R).

### The user row's context menu

- On top: Show Their Posts, Change Role..., Show Memberships..., Check Membership Access..., Change Membership Level..., Cancel Membership....
- Under More: Their Application Passwords..., Sign Out Everywhere..., Invite from a Spreadsheet..., Send Password Reset, Set New Password..., Roles and What They May Do, Remove....
- Then Properties....
- Review note: the three Paid Memberships Pro rows are offered and enabled on every site, including sites without the plugin, and they hold three of the six top places. Remove, Set New Password and Send Password Reset, which every WordPress site has, are pushed under More. Membership rows should appear only where Paid Memberships Pro answers, or go last.
- Review note: "Invite from a Spreadsheet" adds new people to the site; it is not about the selected person, yet it sits on the person's row.

### Show Their Posts

- How to reach it: Enter (the default); context-menu row 1.
- What happens: the Posts node with "author:{id}" in the filter box; focus moves to the list.
- Menu help: "The posts they wrote."
- Review note: only Posts. Their pages and content-type items are not shown, and nothing says so.

### Change Role...

- How to reach it: context-menu row 2. No chord and no Item menu entry.
- Your own account, refused before any dialog: "You cannot take away your own Administrator role from here: you would lose the right to put it back. Ask another administrator to do it." or "You cannot change your own role from here: the new role could take away the right to change it back. Ask an administrator to do it."
- One person: a list titled "Change Role for {name}", prompt "Role:", rows Subscriber, Contributor, Author, Editor, Administrator, starting on their current role. Help: "What this person may do on the site." Choosing the role they already have closes with nothing said.
- Then a preview titled "Change Role". Summary: "Change {name}'s role on {site}. Ctrl+Z puts it back." Lines: "{name}: Author becomes Editor", "Can now: {plain words}; ...", "Can no longer: ...". The button is "Change Role", the default.
- The last Administrator, refused when sent: "This is the site's only Administrator. Make someone else an Administrator first."
- Announced after: "{name} is now {Role} on {site}."
- Undo: recorded. Ctrl+Z says "{name} is {old role} again."
- Several people: a list titled "Change Role for {n} people", help "What these people may do on the site. Anyone the change would lock out is left as they are, and the preview says why." Then a message box titled "Change Role": "Make {n} people {Role} on {site}? {names}." and, on a new line, "Left as they are: {who and why}." The buttons are "Change Role" and "Cancel", Cancel default. Nobody can change: "Nobody selected changes: {reasons}." Different sites: "Change roles on one site at a time." Announced after: "{n} people now {Role} on {site}." with " Not changed: ..." Ctrl+Z: "Put {n} people back in their old roles."
- Menu help: "Choose another role for this person."
- Without permission: needs promote_users ("Changing someone's role needs the Administrator role or higher. You are an Editor on {site}."); tier 2.
- Keyless: no written reason found in any KEYLESS dict.
- Code: wordpress_workbench_people.py (do_change_role), wordpress_workbench_people_bulk.py (do_change_role), workbench_permissions.py (role_change_problem, role_change_preview), workbench_people.py.
- Review note: one person gets a preview window that lists what they gain and lose, and Enter confirms. Several people get a message box with no gains or losses, and Enter cancels. The bigger change gets the smaller preview and the opposite default.
- Review note: a person with a role the site defines itself (a shop manager, say) opens the list on Subscriber, because only the five default roles are offered. One Enter and one more Enter in the preview demotes them. Custom roles should be listed, or the list should start on nothing.
- Review note: the role can also be changed on the Properties sheet's Role page. The same guards apply there, but no gains-and-losses preview does.

### Show Memberships...

- One line: reads this person's current and past Paid Memberships Pro levels into a report window. See the Memberships section; Check Membership Access, Change Membership Level and Cancel Membership are covered there too.

### Their Application Passwords...

- How to reach it: context menu, under More.
- Refused for someone else's without edit_users: "WordPress shows {name}'s application passwords only to someone who may edit them, the edit_users capability, which your role on {site} does not have."
- None: "{name} has no application passwords on {site}."
- What opens: a list titled "Application Passwords for {name}", prompt "Passwords:", one line per password with when it was made and last used. Help: "{name}'s application passwords on {site}, with when each was made and last used. OK offers to revoke the one chosen; Cancel only reads."
- OK on one: a message box titled "Revoke Application Password": "Revoke {password} for {name} on {site}? Whatever signs in with it stops working, and it cannot be brought back." with "Revoke" and "Cancel". The one QUILL signs in with is refused: "QUILL signs in to {site} with this application password, so revoking it here would lock the Workbench out. Make a new password and reconnect the site first, then revoke this one."
- Announced after: "Revoked {password} for {name} on {site}."
- Undo: recorded with no undo.
- Menu help: "This person's application passwords, read from the site, with Revoke after you confirm. Another person's need the edit_users capability."
- Without permission: needs edit_users; tier 0.
- Keyless: "Checked when a device is lost or a person leaves (rule 9)."
- Code: wordpress_workbench_people_admin.py.
- Review note: in a list whose purpose is reading, OK means "revoke". Cancel is the only way to just read. A listener who presses Enter to choose a password to hear about gets a revoke question.
- Review note: the row is tier 0 (reading), but it leads to a permanent revoke. Read Only Workbench access, Safe Mode and View As Role therefore do not stop the revoke.

### Sign Out Everywhere...

- How to reach it: context menu, under More.
- Announced, then the browser opens: "WordPress keeps sign-in sessions out of its REST API: there is no route that lists them or ends them. So the Workbench opens {name}'s screen in wp-admin, where Log Out Everywhere is one button." (for yourself: "your profile" and "Log Out Everywhere Else").
- Keyless: "Leaves QUILL for wp-admin, after a lost device (rule 9)."
- Review note: a hand-off to wp-admin with a trailing ellipsis in the label, though no dialog follows.

### Invite from a Spreadsheet...

- How to reach it: context menu, under More.
- One line: a standard Open box for a CSV of email, role and name, a preview titled "Invite from a Spreadsheet" with a line per row and the button "Add {n}", then "Added {k} of {n} people to {site}." Recorded with no undo. Needs create_users; tier 2.

### Send Password Reset

- How to reach it: Ctrl+Shift+W; Item > Send Password Reset (Alt+I, W); context menu, under More.
- Announced, then the browser opens on the person's wp-admin screen: "WordPress has no REST route for a password reset, so the Workbench opens {name}'s screen in wp-admin, where Send Reset Link sends them the email."
- Refusal on the wrong row: "Choose a person in Users first."
- Menu help: "Opens their wp-admin screen to send the reset email. Ctrl+Shift+W."
- Without permission: needs edit_users. Because edit_users has no plain words in the refusal table, a role without it hears "Doing this (edit users) needs the Administrator role or higher. You are an Editor on {site}."
- Code: wordpress_workbench_lists.py (do_send_password_reset), workbench_create.py (password_reset_pointer).
- Review note: the label says it sends a reset; it opens a web page. It has a chord, unlike the other hand-offs, so a listener pressing Ctrl+Shift+W in a hurry leaves QUILL.
- Review note: two other texts promise more than it does. The Add a Person note says "Send Password Reset on their row opens wp-admin" (correct), but the Invite note says "Send Password Reset on their row sends them the link to choose their own" (not true).
- Review note: the refusal sentence "Doing this (edit users)" is the fallback for a capability missing from the plain-words table. edit_users needs an entry, such as "Changing other people's accounts".

### Set New Password...

- How to reach it: context menu, under More.
- What opens: a one-line text box titled "Set New Password for {name}", prompt "New password:", already holding a strong generated password, shown as plain text. Help: "A strong password is offered; change it if you like. The password is shown as text, the way wp-admin shows the one it suggests, so you can read or copy it. QUILL sends it once and never says it, logs it or keeps it."
- Problems, said after the box closes: "Type a password, or keep the strong one offered.", "The password starts or ends with a space, which is easy to lose. Take it out.", "Use at least 12 characters; the one offered is 24."
- Confirmation: a message box titled "Set New Password": "Set a new password for {name} on {site}? Their old one stops working at once and their browser sign-ins end. Application passwords keep working. WordPress sends no email for this, so give it to them yourself. It cannot be put back." On your own account it adds: " This is your own account: QUILL keeps working, because it signs in with an application password." The buttons are "Set Password" and "Cancel", Cancel default.
- Announced after: "New password set for {name} on {site}."
- Undo: recorded with no undo.
- Menu help: "Give them a new sign-in password: a strong one is offered, then previewed."
- Without permission: needs edit_users (the "Doing this (edit users)" sentence); tier 2.
- Keyless: "Set when a person is locked out, rarely; never a bare key (rule 9)."
- Code: wordpress_workbench_people_bulk.py (do_set_password), workbench_people_bulk.py (password_problem, set_password).
- Review note: a password the check rejects closes the box first. A listener who typed their own password hears the problem and must start again from the menu, with the generated one back in the box. The check should keep the box open.
- Review note: the help says "previewed", but it is a confirmation message box. The password is never shown again in it.
- Review note: being recorded with no undo, it blocks Ctrl+Z for everything done before it in the session.

### Roles and What They May Do

- How to reach it: Ctrl+Alt+R; Site > Roles and What They May Do (Alt+S, R); context menu, under More.
- What opens: a read-only report titled "Roles and What They May Do", one paragraph per role ("Subscriber: Can ...", then "Everything above, and can ..."), ending "WordPress's REST API reads roles but cannot change what a role may do. A role plugin such as Members or User Role Editor does that in wp-admin." Copy All and Close.
- Code: wordpress_workbench_lists.py (do_roles), workbench_create.py (role_rows).

### Remove...

- How to reach it: context menu, last under More ("Remove..."); Delete on a user row; Shift+Delete on a user row. The Item menu row for Delete still reads "Move to Trash".
- Your own account: "You cannot remove your own account from here."
- What opens: everyone on the site is read, then a list titled "Remove {name}", prompt "Give their posts to:", everyone else by name. Help: "WordPress needs someone to own what this person wrote." Nobody else: "There is nobody else to give this person's posts to."
- Their posts are counted, then a message box titled "Remove": "Remove {name}? {n} posts move to {other}. This cannot be undone." with "Remove" and "Cancel", Cancel default.
- The last Administrator, refused when sent: "This is the site's only Administrator, so it cannot be removed."
- Announced after: "Removed {name} from {site}; their posts are {other}'s."
- Several people: a list titled "Remove {n} people"; the message box "Remove {n} people from {site}? {names}. {n} posts move to {other}. This cannot be undone." and, on a new line, "Kept: {who and why}." Announced after: "Removed {n} people from {site}; their posts are {other}'s." with " Not removed: ..." and " This cannot be undone."
- Undo: recorded with no undo.
- Menu help: "Remove this person, with their content given to someone else. Delete."
- Without permission: needs delete_users ("Removing people needs the Administrator role or higher. You are an Editor on {site}."); tier 3, Full access only, when reached from the menu.
- Code: wordpress_workbench_people.py (do_remove_user), wordpress_workbench_people_bulk.py (do_remove_user, _confirm_removal), workbench_people.py (remove_preview, remove_user).
- Review note: critical. Delete and Shift+Delete on a user row run Move to Trash and Delete Permanently, which hand over to Remove. The Workbench checks a command against the row's own menu rows, and the user row has no Trash or Delete Permanently row, so neither the tier 3 access check nor the delete_users check runs. With Read Only access, Safe Mode or View As Role, Delete on a person still opens Remove, and Yes still removes them.
- Review note: the "Give their posts to" list includes Subscribers, who cannot edit what they are given. wp-admin offers everyone too, but a hint ("Subscriber") beside each name would help.
- Review note: the one-person confirmation does not name the site, unlike the several-people one.

### Properties (Alt+Enter), a person

- What opens: the person is read again, then a sheet titled "{name} Properties - {site}".
- General: Display name, Username (read only), Email, Nickname, First name, Last name, Website, Biography, Language ("A WordPress language code such as en_US, for their wp-admin. Empty uses the site's language."), Posts written (read only, counted).
- Role: Role, a choice of the five roles, which needs promote_users. A save that would lock someone out is refused with the same sentences as Change Role.
- Custom Fields when the site registers user meta.
- Saving: users have no modified time, so their edited fields stand in for the conflict check. Ctrl+Z: "Put {name} back as it was."
- Without permission: needs edit_users to save; your own row may always be saved.
- Code: workbench_sheets.py (_STATIC "user"), wordpress_workbench_sheets.py, workbench_people.py (check_role_save).
- Review note: Language wants a code such as en_US typed by hand. wp-admin offers a list of installed languages.

### New Here (Ctrl+N) in Users: Add a Person

- How to reach it: Ctrl+N; File > New Here (Alt+F, N) with Users selected.
- What opens: a sheet titled "Add a Person - {site}". General: Username ("The name they sign in with. It cannot be changed later."), Email, First name, Last name, Display name, Website, Language. Role: Role, Subscriber to start, whose help ends with the no-email note.
- OK refuses with: "A new person needs a username: the name they sign in with.", "A new person needs an email address WordPress can reach them at.", "{role} is not a role this site has."
- Confirmation: a message box titled "Add a Person": "Add {name} ({username}), {email}, to {site} as {Role}? WordPress's REST API makes the account but sends no email, so there is no choice to send one. They get a long random password nobody sees; Send Password Reset on their row opens wp-admin, where one button emails them the link to choose their own." with "Add" and "Cancel".
- Announced after: "Added {name} to {site}."
- Undo: recorded with no undo.
- Without permission: no requirement is checked before the sheet opens; the site refuses without create_users.
- Code: wordpress_workbench_people_bulk.py (add_person), workbench_people_bulk.py (NEW_USER_SHEET, new_user_body, new_user_preview).
- Review note: the most important fact, that no email goes and the person cannot sign in until someone sends a reset, is in the help of the second tab and in the confirmation. It is not visible on the first tab, where the listener fills everything in.
- Review note: an account just added is easy to remove, but Ctrl+Z will not, and its entry blocks every earlier undo.

### Your Profile...

- How to reach it: Ctrl+Alt+Shift+P; Site > Your Profile (Alt+S, Y).
- What opens: your own sheet, titled "Your Profile - {site}", with the General page only; the Role page is left out so nobody demotes themselves here.
- Refusals: "Choose a site first." and "{site} has not said who you are yet."
- Saving and Ctrl+Z as for a person.
- Code: wordpress_workbench_people_bulk.py (do_your_profile).

### Application Passwords: New Here (Ctrl+N)

- How to reach it: Ctrl+N with Application Passwords selected; File > New Here.
- What opens: a text box titled "New Application Password", prompt "Name:", help "A name for what will use it, such as QUILL on the laptop." An empty name closes with nothing said.
- No confirmation; the password is made at once.
- Then a report window titled "New Password for {site}", holding "{name}", a blank line, the secret, a blank line, and "Copy it now: {site} shows it only once." Help: "The new application password. Select it and copy it; once this closes, the site will not show it again." Copy All and Close.
- Undo: not recorded.
- Code: wordpress_workbench_people.py (_new_password), workbench_people.py (create_app_password).
- Review note: Copy All copies the name and the instruction too, not just the secret. A listener pasting it into another app's password field pastes three lines. A "Copy Password" button that copies only the secret would fix it.

### Application Passwords: Revoke...

- How to reach it: Delete on the row; the context menu "Revoke..." (row 2). Shift+Delete reaches a different path (see the review note).
- The password QUILL signs in with: "QUILL signs in to {site} with this application password, so revoking it here would lock the Workbench out. Make a new password and reconnect the site first, then revoke this one."
- Confirmation: a message box titled "Revoke Application Password": "Revoke the application password {name} on {site}? Anything signing in with it stops working, and a revoked password cannot be restored." with "Revoke" and "Cancel", Cancel default.
- Announced after: "Revoked {name} on {site}."
- Undo: recorded with no undo.
- Menu help: "Stop this password working, after you confirm. Delete."
- Without permission: no capability; tier 3, Full access only, when chosen from the menu.
- Code: wordpress_workbench_commands.py (do_revoke), workbench_permissions.py (revoke_refusal).
- Review note: critical. Shift+Delete on an application password row runs the generic Delete Permanently, which has no case for application passwords. It asks "Delete 1 item from {site} permanently? This cannot be undone: {name}." and then deletes the password's route. It skips the guard above, so Shift+Delete on the row marked "QUILL on this computer signs in with it" revokes the password the Workbench is using and locks it out mid-session.
- Review note: Delete reaches Revoke without the tier 3 access check, for the same reason as Remove on a person: the row has no Trash row for the check to find.

### Application Passwords: Properties

- A read-only sheet: Name, Made, Last used, Last address. The button is Close. "This is read only here." is the F1 of every field.

## Menus

The Workbench shows a site's classic menus as one flat list under Sites > site > Menus and Navigation. Each menu is one row; the menu's items are not listed anywhere in the Workbench. A menu row offers Read in Full (the default), Add Menu Item, Add New Pages Automatically, Arrange Items, Earlier Versions, Default Navigation Menu, Copy to Site and Properties. Adding an item is now careful and complete (every kind, Search or View All, under and after any item, preview, re-read, undo). Everything else you do to an existing menu's items (rename, move, remove) is not done in the Workbench itself: Arrange Items (added 2026-11-14) hands the menu to the editor's older Menus window, which does those jobs without previews or Ctrl+Z. Before it, the editor's Tools > WordPress > Menus door had replaced that window with the Workbench, leaving no way to rearrange a menu at all.

### The Menus and Navigation node

- How to reach it: in the tree, Sites > site > Menus and Navigation (it sits after More Taxonomies and before Appearance). There is no Go key for it: the Go menu's Ctrl+Shift+1 to Ctrl+Shift+9 are Posts, Pages, Media, Comments, Users, Plugins, Appearance, Settings and Site Health. The editor's Tools > WordPress > Menus... opens the Workbench at this node (the door table in workbench_tree.py maps `wordpress.menus` to `menus`).
- What the list shows: columns menu, locations, items. Each row's detail (the details pane and Read in Full) is `{name}, shown in: {places}.`, where places is the menu's theme locations joined with commas, or `none`.
- F1 on the node: "The site's menus and where the theme shows them."
- F1 on a row: "A menu. Enter reads where it is shown; Ctrl+N or Add Menu Item adds to it, and Alt+Enter has its Properties, with whether new top-level pages join it by themselves."
- Without permission: the node itself needs nothing to list. The write rows need `edit_theme_options`, which in WordPress's default roles only an Administrator has, so an Editor sees them greyed.
- Code: workbench_tree.py, workbench_load_structure.py (load_menus), workbench_node_help.py.
- Review notes:
  - The items column is always empty: load_menus fills `"items": ""` for every row. A listener hears a column header with nothing under it on every row.
  - The locations column shows WordPress's location slugs exactly as `wp/v2/menus` sends them (for example `primary`), not the theme's names for them ("Primary Menu"). Not translated anywhere I could find.
  - The list reads `wp/v2/menus`, which is classic menus only. A block theme's Navigation menus (`wp_navigation` posts) do not appear in this node at all. The only trace of them is the Default Navigation Menu command, which names one by number.
  - There is no way to see a menu's items in the Workbench itself: no child node per menu, no items in the detail, nothing in Properties. The only way is Arrange Items, which leaves the Workbench for another window.
  - Rename an item, move it up, down, in or out, and remove it: not in the Workbench's own rows. The editor's Menus window (wordpress_menu_commands.py) has Rename, Move Up, Move Down, Move In, Move Out, Remove, Check Menu and Locations; `cmd_menus` returns early through `workbench_door("wordpress.menus")` (and `open_from_door` always returns True), so from the editor's Tools menu that window is gone, and it is now reached only through Arrange Items or the editor's add-this-page-to-a-menu path.
  - No Go key for Menus, although it is one of the places people visit most in wp-admin after Posts and Pages.

### Read in Full (menu row, default)

- How to reach it: Enter on a menu row, or the first row of its context menu (Applications key or Shift+F10).
- What it does: moves focus to the details pane, which holds `{name}, shown in: {places}.` Nothing else.
- Announced after: nothing; focus moves.
- Code: wordpress_workbench_commands.py (do_read).
- Review notes:
  - The default action of a menu reads one short sentence that the list row already said. For a menu, Enter is the one key people press expecting to go inside; here it goes to a pane that cannot show the items.

### Add Menu Item...

- How to reach it: context-menu label "Add Menu Item..." on a menu row. Also Ctrl+N (New Here) with a menu row selected, which first asks the New Here question (see "New Here on Menus" below). Not on the Item menu.
- What opens, in order (each a separate small dialog; each choice dialog is one list box labelled by its prompt, then OK (default) and Cancel; each text dialog is one text box, then OK (default) and Cancel):
  - First QUILL reads the site in the background ("reading what {menu} can hold").
  - Dialog title "Add Menu Item to {menu}", list "Kind of item:" (access key K). Rows are every post type and taxonomy the site shows in menus, in this order: Pages, Posts, other post types by slug, then Custom Links, then Categories, Tags, other taxonomies. F1: "What the new item links to: a page, a post, an item of any other type, a category, a tag or other term, or a custom link to any address."
  - For Custom Links: dialog "Add a Custom Link", text box "URL:" (access key U) prefilled with `https://`; then a second dialog with the same title, text box "Link text:" (access key L).
  - For anything else: dialog "Add {kind} to {menu}", text box "Search, or leave empty to view all:" (access key S). F1 says only published items are listed. Then QUILL searches ("finding {kind}"), and a list dialog "Add {kind} to {menu}" with list "{kind}:" of titles. With an empty search on a post type that has an archive, the first row is `All {kind} (the archive page)`.
  - Where it goes: if the menu has any items, dialog "Where {title} Goes", list "Under:" (access key U) with "Top level of the menu" first, then `Under {item}, level {n}` for every item. Then, if the chosen level already has items, the same title with list "Position:" (access key P): `First`, then `After {item}` for each sibling; the last row (the end) is preselected.
  - Preview: title "Add Menu Item to {menu}"; first control the read-only Summary box (access key S), then the "Each change:" list (access key E), then the button "Add" (default) and Cancel.
- Preview wording: summary `Add {title} to the menu {menu} on {site}?`. Lines: `Adds: {title}, {kind}` (plus `, to {url}` for a custom link); `Where: {under}, {after}, {n} of {total}.` (under is `under {item}` or `at the top level`; after is `first` or `after {item}`); and, when items move, `The {n} items after it there move down one.`
- Announced after: the site's own result: `Added {name} to the menu.` or, if the site put it elsewhere, `Sent {title}, but the site did not keep it where it was asked to go.` The list refreshes.
- Failures announced:
  - Not a menu row: `Choose a menu in Menus and Navigation first.`
  - Custom link with empty text: `A custom link needs link text, so nothing was added.`
  - Nothing found: `{site} has no published {kind}{ matching words}.`
  - Menu changed after the preview: `The menu was changed on the site after the preview. Nothing was sent.` or `The item it was to go under is no longer in the menu. Nothing was sent.`
  - Any other error: the site's plain error text, or `That did not work.`
- Undo: Ctrl+Z (Undo WordPress Change) deletes the new item and puts back the items it renumbered. Spoken: `Took {title} out of {menu} again.` Change History lists `Added {title} to {menu} on {site}.`
- F1: the dialogs' help texts quoted above; the row's help: "A page, post, category, tag, custom link or item of any other type, found by search or from the whole list, placed under any item and after any other, then previewed. Ctrl+N with a menu selected does it too. Ctrl+Z takes it out again."
- Cancel: Cancel or Escape at any step stops with nothing sent and nothing said. Leaving the URL as `https://`, or clearing it, also stops silently.
- Without permission: needs `edit_theme_options`, tier Write. The context-menu row is greyed. Run anyway (for example from What Can I Do Here?), the refusal is `Changing menus and the theme's options needs the Administrator role or higher. You are an Editor on {site}.` Under Workbench Access Read Only or Organize: `Workbench access on {site} is {Read Only or Organize}. Site > Workbench Access changes it.`
- Keyless: "Ctrl+N does it with a menu selected, through New Here (rule 5)."
- Code: menu_item_add.py, wordpress_workbench_menu_items.py, workbench_dashboard_places.py (MENU_ROWS, KEYLESS).
- Review notes:
  - Up to six dialogs in a row for one item (kind, search, pick, under, position, preview). Each is correct, but there is no single "Add Menu Item" dialog where the kind, the item and the place can be reviewed together and changed before the preview. A wrong choice at step five means Cancel and start again.
  - View All reads at most 100 items (`LIMIT = 100`, one page) and never says it stopped. On a site with 300 pages, page 101 onward is silently missing from View All; only Search finds it.
  - Search results that share a title (two pages both called "Contact") are indistinguishable in the list: rows are titles only, with no parent, date or address.
  - Custom Links sits in the middle of the kinds list (after the post types, before Categories). wp-admin's panel order is the reason, but in a list box a listener has to arrow past every custom post type to find it.
  - The "Where" step is skipped entirely for an empty menu and the position step for an empty level, which is good, but the preview then says `Where: at the top level, first, 1 of 1.` with no hint that the Under question was skipped.
  - Ctrl+N with a menu selected bypasses the context menu's permission check: `run` checks `new_here` (which needs nothing), then calls `do_add_menu_item` directly. An Editor walks all six dialogs and only fails when the site refuses the write. Not tested on a live site; read from wordpress_workbench_lists.py and wordpress_workbench_window.py.

### Add New Pages Automatically...

- How to reach it: context-menu label "Add New Pages Automatically..." on a menu row. Also the check box "Automatically add new top-level pages to this menu" on the menu's Properties sheet.
- What opens: QUILL reads the menu's current setting ("reading {menu}'s settings"), then a preview titled "Add New Pages Automatically": Summary box, "Each change:" list, the button "Turn On" or "Turn Off" (default) and Cancel.
- Preview wording, turning on: summary `Turn On automatically add new top-level pages to this menu for {menu} on {site}?`; lines `Now: off. New pages are added to menus by hand.` and `After: on. Each new top-level page published joins the end of {menu}.`
- Preview wording, turning off: summary `Turn Off automatically add new top-level pages to this menu for {menu} on {site}?`; lines `Now: on. New top-level pages are added to {menu} by themselves.` and `After: off. Pages already in the menu stay; new ones are not added.`
- Announced after: `Adding new pages automatically to {menu} is on.` (or off). If the site did not keep it: `{site} did not keep the change; it is still {on or off}.` If it changed meanwhile: `The menu's setting was changed on the site meanwhile. Nothing was sent.`
- Undo: Ctrl+Z turns it back; spoken `Adding new pages automatically to {menu} is {on or off} again.`
- Cancel: nothing sent, nothing said.
- Without permission: needs `edit_theme_options` (Administrator); the refusal sentence is the one under Add Menu Item.
- Keyless: "Set once per menu; also a check box on Properties (rule 9)."
- Code: menu_item_add.py (AUTO_ADD_LABEL, read_auto_add, set_auto_add), wordpress_workbench_menu_items.py.
- Review notes:
  - The summary is built from the check box label lowercased, so it reads "Turn On automatically add new top-level pages to this menu for Main on Radio?", which is ungrammatical spoken English. Something like "Turn on adding new top-level pages to Main?" would read better.
  - The command is a toggle with no indication of the current state in its label. You learn the state only from the preview's Now line. That is acceptable because the preview always comes first, but the context-menu label could say "Turn On..." or "Turn Off...".
  - Two routes to one setting: this command (previewed, re-read before and after) and the Properties check box (a sheet save: conflict check, no preview, undone by Ctrl+Z as `Put {menu number} back as it was.`). Same result, two different confirmation styles.

### Arrange Items...

- Status: appeared in workbench_dashboard_places.py (MENU_ROWS), wordpress_workbench_menu_items.py (do_arrange_menu_items) and wordpress_menu_commands.py (cmd_menus gained `menu_id` and `profile`) at about 15:26 on 2026-11-14, while this pass was being written. No engineering-log entry yet. Described as the code stood then.
- How to reach it: context-menu label "Arrange Items..." on a menu row, after Add New Pages Automatically. No key.
- What opens: the editor's Menus window for that menu, titled `{menu}, {site}`, purpose `The menu {menu} on {site}, as a tree. Items under another item are a level deeper.`; a list "Menu items:" (access key S) of each item's name, what it goes to, its level and its place among its neighbours; then buttons Add Page..., Add Post..., Add Category..., Add Link..., Rename..., Move Up, Move Down, Move In, Move Out, Remove..., Check Menu ("Find items with no name, and links to drafts or deleted pages."), Other Menu... and Locations... ("Choose where the theme shows this menu, such as the header or footer.").
- What each does, as written in that window: Rename `Change what the selected item says.` (spoken `Renamed to {new}.`); Move Up, Move Down, Move In, Move Out (`{item} cannot move that way.` when it cannot); Remove asks `Remove {item} from {menu} on {site}? The page or link itself is not touched.` (plus ` Its {n} items move up into its place.`), button `Remove {item}`, then `{item} removed from {menu}.`; the Add buttons add at the end (`{name} added to {menu}, at the end.`).
- Preview or confirmation: none except Remove. Row help: "Each change is sent when you make it."
- Undo: Ctrl+Z in the Workbench does not undo these; the window records nothing in the Workbench's Change History. The editor's Menu History (Tools > WordPress > Menu History...) is the way back.
- Without permission: needs `edit_theme_options`, tier Write, as the other menu writes.
- Keyless: "Opens the Menus window for a reshuffle, now and then (rule 9)."
- Code: workbench_dashboard_places.py, wordpress_workbench_menu_items.py, wordpress_menu_commands.py.
- Review notes:
  - It restores the missing jobs, but as a different window with different rules: no previews, no Ctrl+Z, its own Add buttons that duplicate Add Menu Item with fewer choices (end only). A person learns two ways to add to a menu that behave differently.
  - The label says "Arrange" but the window also renames, removes, adds and sets locations; "Edit Items..." or "Open in the Menus Window..." would set the right expectation.
  - When the window closes, the Workbench list is not known to refresh (not verified).

### Earlier Versions... (menu)

- How to reach it: context-menu label "Earlier Versions..." on a menu row.
- What opens: QUILL reads the menu and records a snapshot of it now ("reading {menu}'s earlier versions"). If it has older snapshots, a list dialog "Earlier Versions of {menu}", list "Versions:" (access key V), rows like `{date}, {n} items, {m} items since removed` or `{date}, {n} items, same items as now`. F1: "Each earlier state QUILL kept, newest first, with items since removed." Then a preview titled "Bring Back Items to {menu}" with the button "Bring Back".
- Preview wording: summary `Add back the {n} items {menu} has lost since then, at its end?`; one line per item, `Added back: {title}`.
- Announced after: `Brought back {n} items to {menu}.`
- Failures announced:
  - Not a menu row: `Choose a menu first.`
  - No snapshots yet: `{menu} has no earlier versions yet. WordPress keeps none for a classic menu, so QUILL keeps its own each time it reads one, starting now.`
  - Chosen version lost nothing: `Every item from then is still in {menu}.`
  - Menu gone: `{menu number} is no longer on {site}.` (the row's title falls back to the menu's id, see Properties below).
- Undo: Ctrl+Z deletes the items brought back; spoken `Took the {n} items out of {menu} again.`
- Cancel: nothing sent.
- Without permission: needs `edit_theme_options`.
- Keyless: "Looked for after a mistake, rarely (rule 9)."
- Code: wordpress_workbench_widgets.py (do_menu_versions), looks_history.py (MenuSnapshots, MenuVersion).
- Review notes:
  - It only brings back removed items, and puts them at the end of the menu at the top level, not where they were. A restored submenu comes back flattened. The preview does say "at its end", but not "at the top level".
  - It cannot undo a rename or a move, only a removal, although the label "Earlier Versions" suggests a full restore.
  - History starts only the first time QUILL reads the menu, and only on this computer. The first use always says there are no versions, which teaches the user the command does nothing.
  - If the version lost nothing the brought-back count can never be zero here, but between the preview and the write another person could restore items, and the announcement would then say "Brought back 0 items" (the work re-checks what is missing). Minor.

### Default Navigation Menu...

- How to reach it: context-menu label "Default Navigation Menu..." on a menu row.
- What opens: a standard Yes/No message box titled "Default Navigation Menu" with buttons "Ask" and "Cancel"; Cancel is the default (No default).
- Confirmation wording: `Ask {site} which Navigation menu a block theme shows where none is chosen? If the site has no Navigation menu yet, WordPress makes one from its classic menu or its pages.`
- Announced after: `Where a block theme has no menu chosen, {site} shows {title}, Navigation menu {id}.` Failure: `The site did not name a default Navigation menu.`
- Undo: none recorded. If WordPress made a new Navigation menu, nothing in the Workbench can remove it.
- Without permission: needs `edit_theme_options`.
- Keyless: "Asked once when setting up a block theme (rule 9)."
- Code: wordpress_workbench_widgets.py (do_default_navigation), looks_history.py (navigation_fallback).
- Review notes:
  - It sits on a classic menu's row but answers a question about block Navigation menus, which this node does not list. A person on a classic theme gets a question that does not apply to them.
  - The answer speaks the menu's number (`Navigation menu 1234`), which means nothing to a listener and cannot be used anywhere in the Workbench.
  - The tier is Read, but it can create a menu on the site. The confirmation is honest about that; the history is not (no entry, no undo).

### Copy to Site... (menu)

- How to reach it: context-menu label "Copy to Site..."; Item menu Copy to Site, Ctrl+Shift+Y.
- What opens: always a list dialog "Copy to Site", list "Site:" (help "Which of your other connected sites."), even when only one other site is connected. Then a preview titled "Copy from {source} to {target}" with the button "Copy", listing each planned step, pictures to upload (`Upload the picture {url}`) and `Left out: ...` lines.
- Announced after: `Copied to {target}; new items are drafts there.` or, with failures, `Copied to {target}, except {n}; the report says which.` and a report titled "Copy to {target}".
- Failures: no other site: `Connect a second site first: File > WordPress > Connect a Site.` Nothing selected: `Select what to copy first.`
- Undo: none. Change History records `Copied {n} from {source} to {target}.`, and Ctrl+Z says `Copied {n} from {source} to {target}. This cannot be undone.`
- Without permission: the target site is checked as a Write; the refusal is the Workbench access sentence or the role sentence for the target.
- Code: wordpress_workbench_bold.py, workbench_site_copy.py.
- Review notes:
  - "Copied 3 from Radio to Studio." is missing its noun.
  - For a menu, the copy replaces the target menu's links (workbench_site_copy.py says "its links there are replaced"). That is a destructive change on the target with no undo; check that the preview says it plainly.

### Properties (menu)

- How to reach it: Alt+Enter on a menu row, the last context-menu row "Properties...", or Item > Properties.
- What opens: the shared Properties sheet titled `{menu number} Properties - {site}` (for example `12 Properties - Radio`), one page "General" with: Menu name (text), Description (multi-line), Automatically add new top-level pages to this menu (check box, needs `edit_theme_options`), Shown in (list, read only).
- Field help: Menu name "The menu's name in wp-admin."; Description "A note about the menu; visitors do not see it."; the check box "Checked, each new top-level page published from now on is added to the end of this menu by WordPress itself."; Shown in "The theme's places this menu is shown in."
- Announced after a save: `Saved 1 change to {menu number} on {site}.` (or `Saved {n} changes`), plus ` The site did not keep: ...` when a field was dropped. No preview before a menu sheet save.
- Undo: Ctrl+Z, spoken `Put {menu number} back as it was.`
- Without permission: a field the role cannot change is read only, with the refusal sentence as its F1 help.
- Code: menu_item_add.py (MENU_SHEET), workbench_sheets.py, wordpress_workbench_sheets.py.
- Review notes:
  - The sheet title, the saved sentence and the undo sentence all name the menu by its number, not its name: WbRow.title looks for a title, name, what, plugin, theme, setting, form or site cell, and a menu row's name is in a `menu` cell, so the title falls back to the row key (the menu id). The menu commands work around it with their own `_named()`, the sheet does not.
  - This is the only place to rename a menu, and Shown in is read only: choosing which theme location shows a menu is only in the Menus window's Locations... (through Arrange Items).
  - Shown in lists location slugs, as in the list.

### New Here on Menus (Ctrl+N)

- How to reach it: Ctrl+N or File > New Here..., or the node context menu's "New Here...", with the Menus and Navigation node current.
- What opens: with a menu row selected, a list dialog "New Here", list "Make:" with `A new item in {menu}` (first, preselected) and `A new menu`. F1 "An item in the selected menu, as Add Menu Item does, or another menu." The first goes to Add Menu Item. The second (or Ctrl+N with no row selected) asks, in a dialog titled "New Menu", text box "Name:" (help "Its name, as the site shows it.").
- Announced after: `Made the menu {name} on {site}.` Empty name: `It needs a name, so nothing was made.`
- Undo: none recorded. Ctrl+Z after making a menu undoes whatever change came before it.
- Without permission: New Here has no requirement, so nothing is greyed; the site refuses an Editor at write time.
- Code: wordpress_workbench_lists.py (do_new_here, _item_or_menu), workbench_create.py.
- Review notes:
  - A new menu is made with no preview and no undo, unlike every other write in this node. Worse, because it is not in Change History, Ctrl+Z right after it silently undoes the previous, unrelated change.
  - File > New Here's own help still says "A new user or password, where you are.", which is out of date in every node.
  - Delete a menu: not found in the Workbench.

## Widgets

Classic themes' widget areas are under Sites > site > Appearance > Widgets and Sidebars, one row per area. A widget area's context menu adds, changes, moves and removes its widgets, for every widget type the site registers: a legacy widget is filled in on the form WordPress itself draws, turned into QUILL's own labelled controls; a block widget is edited as text. Add and Change are previewed as a visitor would see the widget; Remove asks first; every change is undone with Ctrl+Z. The widgets themselves are never rows, so every command starts from the area and asks which widget.

### The Widgets and Sidebars node

- How to reach it: Sites > site > Appearance > Widgets and Sidebars. Ctrl+Shift+7 (Go > Appearance) lands on Themes, not here, so it is Ctrl+Shift+7 then arrows in the tree. The editor's Tools > WordPress > Manage > Widgets... opens the Workbench here.
- What the list shows: columns sidebar, widgets, status: the area's name, how many widgets it holds, and WordPress's status word as sent (`active` or `inactive`). Detail: `{name}, {n} widgets.`
- F1 on the node: "The classic theme's widget areas. Each row's context menu adds, changes, moves, removes and previews its widgets, of every kind the site has."
- F1 on a row: "A widget area and its widgets. Add, Change, Move and Remove a Widget are on the context menu, for every kind of widget the site has."
- Context menu: Read in Full (default), Add a Widget..., Change a Widget..., Move a Widget..., Remove a Widget..., Preview Widgets, then Show Only and Hide submenus, then Properties....
- Code: workbench_tree.py, workbench_load_structure.py (load_sidebars), workbench_dashboard_places.py (WIDGET_ROWS).
- Naming: in every dialog title and spoken sentence below, `{area}` is the widget area's id, not its name. WbRow.title looks for a title, name, what, plugin, theme, setting, form or site cell; an area's name is in a `sidebar` cell, so the title falls back to the row key, WordPress's sidebar id. So the dialogs say "Add a Widget to sidebar-1" and "Removed Text widget: Hours from sidebar-1; it is in Inactive Widgets.", and the Properties sheet is titled `sidebar-1 Properties - {site}`. (The list row itself shows the name.)
- Review notes:
  - The id-for-name problem above is the first thing to fix: every widget sentence names an area the way only a theme developer would.
  - The detail says `{n} widgets.` and nothing about what they are. To hear the widgets you must run Preview Widgets, which opens a report.
  - "1 widgets" is said for an area with one widget (no singular form in load_sidebars).
  - On a block theme this node is normally empty or shows only WordPress's inactive area; nothing says "your theme uses the Site Editor instead; see Templates and Template Parts".

### Read in Full (widget area, default)

- How to reach it: Enter, or the first context-menu row.
- What it does: focus to the details pane, which says `{name}, {n} widgets.`
- Code: wordpress_workbench_commands.py.

### Add a Widget...

- How to reach it: context-menu label "Add a Widget..." on a widget area row.
- What opens:
  - QUILL reads the site's widget types ("reading the kinds of widget").
  - List dialog "Add a Widget to {area}", list "Kind of widget:" (access key K); each row `{name}: {description}`, Block first. F1: "Block holds any block, as text; the rest each have their own settings."
  - For Block: dialog "Add a Block Widget to {area}", multi-line text box "Text:" (access key T), help "The words of a paragraph block, shown in this area on every page."
  - For any other kind: QUILL reads its form ("reading {kind}'s form") and shows it as a QUILL form titled "Add {kind}", purpose "The widget's own settings, as WordPress draws them.", one labelled control per field of WordPress's own form (text boxes, check boxes, choices), access keys assigned automatically, then OK and Cancel. A kind whose form has no fields skips this dialog.
  - Preview: title "Add {kind}", button "Add".
- Preview wording: summary `Add this {kind} widget to {area} on {site}? It shows on every page that has this area.`; one line `Visitors see: {what WordPress renders}` (or `(nothing yet)`).
- Announced after: `Added a {kind} widget to {area} on {site}.`; the list refreshes.
- Failures: not an area: `Choose a widget area in Widgets and Sidebars first.`; no types: `{site} lists no kinds of widget.`; an empty block text stops silently.
- Undo: Ctrl+Z deletes it; spoken `Removed the {kind} widget again.`
- Cancel: at any step, nothing sent.
- Without permission: needs `edit_theme_options` (Administrator), tier Write.
- Keyless: "Widgets are added a few times a site's life (rule 9)."
- Code: wordpress_workbench_widgets.py, widget_types.py, site_structure.py.
- Review notes:
  - The help says Block "holds any block, as text", but Add makes only a paragraph block from plain words (`paragraph_block(text)`). You cannot add a heading, a list or a Latest Posts block from here; only Change edits a block widget's markup.
  - The widget is always added at the end of the area. There is no position choice, unlike Add Menu Item.
  - "Visitors see:" is WordPress's rendering turned into words, which is the right idea; for a widget that renders nothing until configured, "(nothing yet)" is clear.

### Change a Widget...

- How to reach it: context-menu label "Change a Widget...".
- What opens:
  - QUILL reads the area's widgets. With more than one, list dialog "Change a Widget", list "Widget:" (access key W), each widget as spoken (a block widget by its first block's description, a legacy one as `{kind} widget: {words}`), in page order. With one widget it is chosen without asking.
  - A block widget: dialog "Change {widget}", multi-line text box "Block markup:" (access key B) holding the raw markup; help "The widget's block markup. OK reads the change back before it is sent."
  - A legacy widget: its own form, titled "Change {widget}".
  - Preview: title "Change {widget}", button "Save".
- Preview wording: summary `Save {widget} in {area} on {site}?`. For a block widget the lines are a line-by-line change list (`Line {n} removed: ...`, `Line {n} added: ...`, at most a set number then `And {n} more line changes.`, or `No line changes.`). For a legacy widget: `Visitors saw: {before}` and `Visitors will see: {after}`.
- Announced after: `Saved {widget} in {area} on {site}.`
- Failures: `{area} has no widgets.`
- Undo: Ctrl+Z; spoken `{widget} is back as it was.`
- Cancel: unchanged block text, or Cancel, stops silently.
- Without permission: `edit_theme_options`.
- Keyless: "Widgets change a few times a site's life (rule 9)."
- Code: wordpress_workbench_widgets.py, widget_types.py.
- Review notes:
  - A legacy widget whose form has no fields returns no answers, and the command then stops without a word (`if not data: return`). The person hears nothing and does not know why.
  - Unchanged block markup also stops silently, while Edit Block Markup for templates says `{title} is unchanged, so nothing was sent.` Inconsistent.

### Move a Widget...

- How to reach it: context-menu label "Move a Widget...".
- What opens: the same widget choice (title "Move a Widget"), then list dialog "Move {widget}", list "To:" (access key T) of the other areas; help "The widget area it moves to; it goes at the end there."
- Preview or confirmation: none. Choosing the area and pressing OK moves it.
- Announced after: `Moved {widget} from {area} to {target}.` No other area: `{site} has no other widget area to move it to.`
- Undo: Ctrl+Z; spoken `{widget} is back in {area}.`
- Without permission: `edit_theme_options`.
- Keyless: "Rare rearranging of widget areas (rule 9)."
- Review notes:
  - The only widget write with no preview. Moving a widget changes every page that shows either area, the same reach Add's preview warns about.
  - The undo puts it back at the end of the original area, not in its old position.
  - Moving within an area (reordering) is not offered.

### Remove a Widget...

- How to reach it: context-menu label "Remove a Widget...".
- What opens: the widget choice (title "Remove a Widget"), then a Yes/No message box titled "Remove a Widget" with buttons "Remove" and "Cancel", Cancel the default.
- Confirmation wording: `Take {widget} out of {area} on {site}? WordPress keeps it in Inactive Widgets, and Ctrl+Z puts it back.`
- Announced after: `Removed {widget} from {area}; it is in Inactive Widgets.`
- Undo: Ctrl+Z moves it back; spoken `{widget} is back in {area}.`
- Without permission: `edit_theme_options`.
- Keyless: "Rare, and it takes a widget off every page (rules 4 and 9)."
- Review notes:
  - Good: honest about where it goes and how to undo it.
  - The confirmation is a message box, while Add and Change use the preview window; a listener meets two confirmation styles for one family of commands.

### Preview Widgets

- How to reach it: context-menu label "Preview Widgets".
- What opens: after "rendering the widgets in {area}", a report window titled "Widgets in {area}": a read-only multi-line box "Report:" (access key R), then "Copy All" and "Close". One line per widget, `{widget}: {what a visitor sees}` or `{widget}: (shows nothing)`; or `{area} has no widgets.`
- F1: "Each widget in this area, then what a visitor sees of it."
- Keyless: "Read Widgets does it now and then, from the context menu (rule 9)."
- Review notes:
  - The keyless reason calls it "Read Widgets"; the menu calls it "Preview Widgets". The written reason names a command that does not exist.
  - This is the only way to hear the widgets at all; it would serve better as the area's default (Enter) than Read in Full.

### Properties (widget area)

- How to reach it: Alt+Enter, the last context-menu row, or Item > Properties.
- What opens: no sheet is written for widget areas, so QUILL builds one from the `wp/v2/sidebars` route's schema: page General and, for multi-line fields, page More. Field labels are the schema's own title or description, cut to 60 characters; fields the schema marks read-only are read only.
- Code: workbench_sheets.py (schema_sheet, _schema_field), wordpress_workbench_sheets.py.
- Review notes:
  - Labels are WordPress's developer descriptions (for example the route's description of before_widget HTML), not words a site owner uses. Not verified on a live site which fields end up editable.

### wp-admin for This Place (Widgets and Sidebars)

- How to reach it: the tree's context menu on the node (Applications key on the tree), under More, "wp-admin for This Place...".
- What it does: the node has one nearest screen, Appearance > Widgets, so it opens without a choice: `Sidebars and their widgets are in Widgets and Sidebars. Opening Appearance > Widgets on {site} in your browser.`
- Review notes:
  - It tells you the Workbench does all of it, then opens wp-admin anyway. When the map says `workbench`, the sentence could ask first or explain what wp-admin adds (drag-and-drop, the Customizer's live preview).

## Appearance and the Site Editor

Appearance is a folder node under each site holding Themes, Global Styles, Templates, Template Parts, Additional CSS, Patterns, Fonts and Widgets and Sidebars (Widgets has its own section above; theme row actions are in "Plugins and themes" below). What REST allows is done in place: a block theme's palette colours and font sizes, its templates and template parts as block markup, and its Additional CSS, each previewed line by line and undone with Ctrl+Z. Themes are read only (WordPress's REST API cannot switch, install or update them), patterns and fonts are lists with almost nothing to do, and style variations and Previous Looks are not in the Workbench at all: they stay in the editor's Tools > WordPress menu.

### The Appearance folder and its Go key

- How to reach it: Ctrl+Shift+7, Go > Appearance (`Appearanc&e`, help "Themes, templates, patterns."). It lands on Appearance > Themes, not on the Appearance folder (GO_NODES maps `go_appearance` to `themes`).
- What the list shows: the folder has no loader, so its list is its children; the node's text adds " Open it with Right Arrow to see what it holds."
- F1: "Themes, templates, patterns, fonts and widgets."
- Code: workbench_window_menu.py (GO_NODES), workbench_tree.py, workbench_node_help.py.
- Review notes:
  - F1 for Appearance does not mention Global Styles, Template Parts or Additional CSS, which are three of its eight children.
  - Go > Appearance landing on Themes means the key never shows you the folder; the help "Themes, templates, patterns." suggests otherwise. For an Editor (who cannot list themes) Ctrl+Shift+7 lands on a node that only says they lack the role.

### The Themes node

- How to reach it: Ctrl+Shift+7; Appearance > Themes; the editor's Tools > WordPress > Manage > Themes... door.
- What the list shows: columns theme, version, status (`active` or `inactive`). Detail: `{name}, version {version}, {status}. REST only reads themes: Activate and Open in Dashboard go to wp-admin.` After Check for Updates on WordPress.org the version cell can read `{installed}, update waiting: {latest}` (see "Plugins and themes").
- F1 on the node: "The installed themes. WordPress's REST API only reads them, so Open in Dashboard activates, installs and updates in wp-admin; Find a Theme on WordPress.org searches."
- F1 on a row: "A theme. REST only reads themes: Activate and Open in Dashboard go to Appearance > Themes in wp-admin. Check for Updates on WordPress.org says whether one waits."
- Context menu: Read in Full (default), Activate..., Find a Theme on WordPress.org..., Open in Dashboard, Check for Updates on WordPress.org..., Show Only and Hide, Properties....
- Without permission: the node needs `switch_themes`; for anyone below Administrator the node shows `Changing the theme needs the Administrator role or higher. You are an Editor on {site}.` instead of a list.
- Code: workbench_load.py (load_themes), workbench_actions.py, workbench_people.py (_NODE_NEEDS).
- Review notes:
  - The refusal says "Changing the theme" when the person only tried to look. An Editor cannot even read which theme is active from the Workbench, although that is harmless information (At a Glance does name the theme).

### Properties (theme)

- How to reach it: Alt+Enter, last context-menu row, Item > Properties.
- What opens: sheet `{theme} Properties - {site}`, page General, every field read only: Name, Version, Status, Author, Description (multi-line), Parent theme. Each field is a written read-only field, so its F1 is `{label}, as the site says it.` (themes are also in the sheet's no-edit set).
- Code: workbench_sheets.py, wordpress_workbench_batch_sheets.py (_NO_EDIT).
- Review notes:
  - No "Requires WordPress", "Requires PHP", "Tested up to", screenshot description or tags, all of which `wp/v2/themes` sends; a person choosing between themes has only the description.

### The Global Styles node

- How to reach it: Appearance > Global Styles.
- What the list shows: columns setting, kind, value, contrast. One row per palette colour and font size of the active block theme, merged with the site's own overrides. Kind is `Colour` or `Font size`. For a colour the detail and the contrast cell are a sentence like `{name}, {colour}, {ratio} on the page background, {passes or fails}` (exact wording from site_styles.contrast_sentence); for a font size, `{name}, font size {value}.`
- Empty cases: a classic theme gives one fact row, `Global Styles: The active theme does not expose WordPress global styles.`; a block theme without a palette or sizes, `{theme} exposes no palette or font sizes.`; and when the account cannot read the overrides, an extra row `User styles: This account cannot read the site's own style overrides; these rows show the active theme's defaults.`
- F1 on the node: "The site's global styles: colours, type and spacing."
- F1 on a row: "A palette colour or font size in the active block theme. Change... previews the new value."
- Context menu: Read in Full (default), Change..., Show Only and Hide, Properties....
- Code: workbench_load_structure.py (load_global_styles), site_styles.py.
- Review notes:
  - F1 promises spacing; the node lists colours and font sizes only. Font families, spacing, element styles (links, headings, buttons) and block styles are not listed.
  - The contrast column is good and rare. It measures against the page background and text colour only; a colour used as a button background against white text is not judged.

### Change... (global style)

- How to reach it: context-menu label "Change..." on a Global Styles row.
- What opens: dialog "Change {name}", text box "New value:" (access key N) holding the current value. Help: for a colour "Type a colour such as #1a4d2e."; for a font size "Type a font size with its unit, such as 1.125rem or 18px." Then a Yes/No message box titled "Change {name}", buttons "Change {name}" and "Cancel", with Cancel the default.
- Confirmation wording: `Change {name} on {site} from {old} to {new}? Visitors see this change immediately. Undo WordPress Change can put the previous style back.` For a colour, a contrast sentence for the new value is added.
- Announced after: `{name} changed on {site}. Undo WordPress Change can restore its previous value.`
- Failures announced:
  - Unreadable colour: `QUILL cannot read {value} as a colour. Type it as a hex code such as #1a4d2e, or as rgb(26, 77, 46).`
  - Unreadable size: `QUILL cannot read {value} as a font size. Type a number with its unit, such as 1.125rem or 18px.`
  - Same value: `{name} on {site} already has that value.`
  - Theme changed: `The active theme on {site} changed. Refresh this list first.`
  - Value changed elsewhere: `{name} on {site} changed since this list loaded. Refresh and try again.`
  - No record: `The active theme on {site} has no editable style record.`, or, before anything opens, `This theme has no site-specific style record to change.`
  - Not verified: `The site did not verify the new value for {name}.`
- Undo: Ctrl+Z; spoken `Restored {name} on {site}.`, or `Not undone: {name} on {site} changed again on the site.` QUILL also keeps the previous styles in a local backup file before saving (site_styles.keep_previous).
- Cancel: nothing sent.
- Without permission: needs `edit_theme_options`, tier Write; refusal `Changing menus and the theme's options needs the Administrator role or higher. You are ...`
- Keyless: no written reason found in the KEYLESS tables I read.
- Code: wordpress_workbench_bold_styles.py, site_styles.py.
- Review notes:
  - F1 says "Change... previews the new value", but this is a plain message box, not the preview window every other Site Editor write uses, and Cancel is its default button. Inconsistent with Edit Additional CSS and Edit Block Markup.
  - The module's own comment says "Enter on a Global Styles row changes that colour or font size"; Enter actually reads (Read in Full is the default).
  - Colours are typed as hex or rgb. Named colours, and choosing from the theme's own palette, are not offered. A listener has no way to hear a colour except as a code plus a nearest-colour name.
  - The confirmation repeats the old and new values and then a contrast sentence that repeats the new value again; long for a message box.

### Properties (global style)

- What opens: sheet `{name} Properties - {site}`, page General: Name, Kind, Value, Contrast, all read only (each F1 `{label}, as the site says it.`; global styles are also in the no-edit set). Changing goes through Change....
- Review notes:
  - Alt+Enter cannot change the value although Properties is where values change in most lists, and nothing on the sheet points to Change....

### The Templates and Template Parts nodes

- How to reach them: Appearance > Templates; Appearance > Template Parts.
- What the list shows: columns title, source, slug. Source is `customized` (the site's own copy) or `from the theme`. Detail: `{title}, {source}.`
- F1 on Templates: "The block theme's templates. Edit Block Markup, Earlier Versions, Reset to the Theme's Version and New Template are on each row's context menu."
- F1 on Template Parts: "The block theme's template parts, such as the header and footer, edited like templates."
- F1 on a row: "A template or template part. Edit Block Markup changes it after a preview; Reset to the Theme's Version takes a customized one back to the theme's."
- Context menu: Read in Full (default), Edit Block Markup..., Earlier Versions..., Reset to the Theme's Version..., New Template..., Open in the Site Editor, Show Only and Hide, Properties....
- Code: workbench_load_structure.py (load_templates), workbench_dashboard_places.py (TEMPLATE_ROWS), workbench_site_editor.py, wordpress_workbench_site_editor.py.
- Review notes:
  - New Template is only on a row's context menu. On an empty Templates list (a classic theme, or a fresh one) there is no row, so there is no way to make the first template; Ctrl+N (New Here) on Templates says `New Here makes posts, pages, custom items, categories, tags, terms, menus, people and application passwords. Choose one of those nodes first.`
  - A template part's area (header, footer, general) is not a column, though it is what tells parts apart.

### Edit Block Markup...

- How to reach it: context-menu label "Edit Block Markup..." on a template or template part.
- What opens: QUILL reads it ("reading {title}"), then dialog `{Template or Template part}: {title}`, multi-line text box "Block markup:" (access key B) with the markup, OK and Cancel. Help: "The block markup, as WordPress stores it: each block is an HTML comment that opens and closes it. Change the text, then OK reads the change back before anything is sent." Then a preview titled `Save {Template}: {title}`, button "Save".
- Preview wording: summary `Save the {template or template part} {title} on {site}?`, plus, for one from the theme, ` It comes from the theme, so the site keeps its own copy; Reset to the Theme's Version goes back.` Lines: the line-by-line change list (`Line {n} removed: ...`, `Line {n} added: ...`, `And {n} more line changes.`).
- Announced after: `Saved the {noun} {title} on {site}.` Unchanged: `{title} is unchanged, so nothing was sent.`
- Failures: `{title} was changed on the site after QUILL read it. Nothing was sent; read it again and make the change there.`; `The site kept a different version of {title}.`; `The site did not send the template.`; not a template row: `Choose a template or template part first.`
- Undo: Ctrl+Z; a customized one gets its old text back, a theme one is reset to the theme; spoken `{title} is back as it was on {site}.`
- Without permission: `edit_theme_options` (Administrator).
- Keyless: "Templates change a few times a site's life (rule 9)."
- Review notes:
  - Editing a whole template as raw block comments in a plain text box is honest and complete, but heavy: a header part is often hundreds of lines of nested comments. The editor's own block tools are not offered here (no "Open in Editor" for a template).
  - The conflict message says "read it again and make the change there" but does not offer to reload; your edit is lost.

### Earlier Versions... (template)

- How to reach it: context-menu label "Earlier Versions..." on a template row.
- What opens: list dialog "Earlier Versions of {title}", list "Versions:" (access key V) with rows `Saved {when}`; help "Each earlier version the site kept, newest first. OK previews it." Then preview "Restore {title}", button "Restore".
- Preview wording: summary `Put back the version of {title} saved {when}?`; lines: the change list from now to then.
- Announced after: `Restored {title} to its version of {when}.` None: `{title} has no earlier versions on the site.`
- Undo: Ctrl+Z; spoken `{title} is back as it was.`
- Without permission: `edit_theme_options`.
- Keyless: "Looked for after a mistake, rarely (rule 9)."
- Review notes:
  - A template still from the theme always says it has no earlier versions, without saying why (only customized copies have revisions).
  - Rows are dates only; no author, no size of change.

### Reset to the Theme's Version...

- How to reach it: context-menu label "Reset to the Theme's Version...".
- What opens: QUILL reads the template and the theme's own version. Then a preview titled "Reset {title}" (button "Reset") or, for a template the theme never had, "Delete {title}" (button "Delete").
- Preview wording, reset: summary `Reset {title} to the theme's version on {site}?`; lines: the change list, or `The theme's version could not be read for this preview.`
- Preview wording, delete: summary `The theme has no {title}, so resetting deletes this {noun} from {site}. Pages that use it fall back to the theme's own.`; line `{n} lines of block markup are removed.`
- Announced after: `{title} on {site} is the theme's version again.` or `Deleted the {noun} {title} from {site}.` Already the theme's: `{title} already is the theme's version; nothing to reset.`
- Undo: Ctrl+Z puts the site's copy back; spoken `{title} is the site's own copy again.`
- Without permission: `edit_theme_options`, tier Destructive.
- Keyless: "Removes the site's copy: never a bare key (rules 4 and 9)."
- Review notes:
  - The row's help says "Confirmed by name", but the confirmation is the ordinary preview with a Reset or Delete button; nothing is typed.

### New Template...

- How to reach it: context-menu label "New Template..." on any template or template part row.
- What opens: dialog "New Template" (or "New Template Part" from a part's row), text box "Name (slug):" (access key N). Help: "Lowercase letters, numbers and hyphens: single-post-news for one post, page-about for one page, category-news for a category. It starts from the template WordPress would use for that name today." Then a preview titled "New Template" or "New Template part", button "Make It".
- Preview wording: summary `Make the {noun} {slug} on {site}? It starts as a copy of {base}.` or `... It starts empty.`; lines: the markup it starts with, as added lines.
- Announced after: `Made the {noun} {slug} on {site}.` Bad slug: `{slug} cannot be a template's name: use lowercase letters, numbers and hyphens.`
- Undo: Ctrl+Z deletes it; spoken `Deleted the {noun} {slug} again.`
- Without permission: `edit_theme_options`.
- Keyless: "A new template is made a few times a site's life (rule 9)."
- Review notes:
  - For a template part the help still says it starts from the template WordPress would use, but the code never looks one up for a part: it always starts empty.
  - A part is made with no area (header, footer), so it lands in General; not offered.
  - The preview title capitalises only the first word: "New Template part".

### Open in the Site Editor

- How to reach it: context-menu label "Open in the Site Editor".
- What it does: opens `wp-admin/site-editor.php?postType=...&postId=...` in the browser and says `Opened {title} in the Site Editor on {site}, in your browser.` No address: `{site} has no address QUILL knows.`
- Keyless: "Leaves QUILL for the browser, now and then (rule 9)."
- Review notes:
  - Fine as a hand-off. The Site Editor is one of the least accessible screens in wp-admin, so its help could say what it is for ("to lay it out by sight") as the row help does.

### Properties (template)

- What opens: a sheet built from the template route's schema, labels from the schema's descriptions cut to 60 characters, read-only fields as the schema marks them.
- Review notes:
  - Field labels are developer descriptions (for example the schema's sentence describing the slug), and a 60-character cut can end mid-word.
  - Not verified whether the content field is editable here; if it is, it is a second route to change a template that skips Edit Block Markup's line-by-line preview.

### The Additional CSS node

- How to reach it: Appearance > Additional CSS.
- What the list shows: one row. Block theme: columns screen, reach; screen `Additional CSS`, reach `{n} lines of Additional CSS` or `No Additional CSS yet`; detail `{said} in {theme}'s site styles. It begins: {first line} Edit Additional CSS changes it; each save is kept in Previous Looks.` Classic theme: a wp-admin row, reach `Only in wp-admin`, detail `{theme} is a classic theme, which keeps its Additional CSS in the Customizer; no REST route reaches it. Enter opens Appearance > Customize > Additional CSS in your browser.`
- F1 on the node: "The site's Additional CSS. In a block theme Edit Additional CSS changes it after a preview, and each save is kept in Previous Looks; a classic theme's opens the Customizer."
- F1 on the block row: "The site's Additional CSS. Edit Additional CSS changes it, after a preview."
- Context menu, block theme: Read in Full (default), Edit Additional CSS..., Properties.... Classic theme (it is a wp-admin Screens row): Open in Dashboard (default), Go to Its Place in the Workbench, Read in Full, Properties....
- Review notes:
  - The column header "reach" holds a line count on a block theme. A listener hears "reach, 12 lines of Additional CSS".
  - On a classic theme, Enter announces only ` Opening Appearance > Customize > Additional CSS on {site} in your browser.`: the row's raw data has no `why`, so the reason sentence before "Opening" is empty.
  - On a classic theme, Go to Its Place in the Workbench selects Additional CSS, the node you are already in.

### Edit Additional CSS...

- How to reach it: context-menu label "Edit Additional CSS..." on the block theme's row.
- What opens: dialog `Additional CSS: {site}`, multi-line text box "CSS:" (access key C). Help: "The site's Additional CSS. It applies to every page of the site; OK reads the change back before anything is sent." Then preview "Save Additional CSS", button "Save".
- Preview wording: summary `Save the Additional CSS of {site}? CSS changes how every page of the site looks. WordPress keeps the version it replaces in Previous Looks.`; lines: the change list.
- Announced after: `Saved the Additional CSS of {site}.` Unchanged: `The Additional CSS is unchanged, so nothing was sent.` Checked before the preview: `Nothing was sent. WordPress refuses markup such as <style> in CSS; take the tags out.`, `Nothing was sent. A closing brace comes before its opening one.`, `Nothing was sent. {n} opening brace(s) never closed.` Conflict: `The site's Additional CSS was changed after QUILL read it. Nothing was sent; read it again and make the change there.` Wrong row: `Choose the Additional CSS row of a block theme first.`
- Undo: Ctrl+Z; spoken `The Additional CSS of {site} is back as it was.`
- Without permission: `edit_theme_options`. Note WordPress itself needs `edit_css` for this route.
- Keyless: "Additional CSS changes a few times a site's life (rule 9)."
- Review notes:
  - Good brace and markup checks before the preview, said in one sentence.
  - "Kept in Previous Looks" points at a feature the Workbench does not have; Previous Looks is only in the editor (Tools > WordPress > Manage > Previous Looks...).
  - A failed check throws the typed text away; the person has to retype the whole edit.

### The Patterns node

- How to reach it: Appearance > Patterns; the editor's Tools > WordPress > Manage > Synced Patterns... door.
- What the list shows: columns title, status, modified, from `wp/v2/blocks`. Detail: `{title}, a synced pattern, {status}.`
- F1 on the node: "Synced patterns: blocks you reuse, changed in one place." F1 on a row: "A synced pattern."
- Context menu: Read in Full (default), Copy to Site... (Ctrl+Shift+Y), Show Only and Hide, Properties....
- Properties: built from the blocks route's schema.
- Code: workbench_load_structure.py (load_patterns), workbench_actions.py.
- Review notes:
  - `wp/v2/blocks` returns unsynced patterns too, but every row says "a synced pattern" (not verified on a live site whether unsynced ones are filtered).
  - No way to edit a pattern's blocks, rename it, make one or delete one from its row. The editor's old Synced Patterns window had Edit (a "Blocks:" text box and a "Save Synced Pattern" confirmation), but its door now opens this node instead. Regression unless the schema sheet covers it (not verified).
  - Pattern categories: not found.
  - Row help "A synced pattern." is the shortest F1 in the Workbench and says nothing about what can be done.

### The Fonts node

- How to reach it: Appearance > Fonts; the editor's Tools > WordPress > Manage > Fonts... door.
- What the list shows: columns family, slug, from `wp/v2/font-families`. Detail: `{name}, a font family installed on the site.`
- F1 on the node: "The fonts the site has installed." F1 on a row: "An installed font."
- Context menu: Read in Full (default), Show Only and Hide, Properties....
- Review notes:
  - Install a font and delete a font: not found in the Workbench. The editor's old Fonts window (wordpress_design_commands.py) offers both (`Install {name}`, `Delete {name}`), but its door now opens this read-only list. Regression.
  - No font faces (weights and styles) are listed; the Properties sheet shows the raw family settings.

### Style variations and Previous Looks

- How to reach them: not in the Workbench. In the editor, Tools > WordPress > Design > Style Variations... and Site Styles..., and Tools > WordPress > Manage > Previous Looks....
- Review notes:
  - Three Workbench help strings say "kept in Previous Looks", but there is no Previous Looks node or command in the Workbench. Either add the node (Appearance > Previous Looks, listing global-styles revisions) or say "in the editor's Tools > WordPress > Manage > Previous Looks".
  - Switching a block theme's style variation, one of the most common appearance jobs, has no place in the Appearance branch.

### wp-admin for This Place (Appearance nodes)

- How to reach it: tree context menu on the node, under More, "wp-admin for This Place...".
- What it offers, by node (from workbench_admin_map.py):
  - Themes: a list dialog "wp-admin for This Place", list "Screens:" (access key S), rows `{screen}: {reach}`: "Appearance > Themes: Part in the Workbench, the rest in wp-admin", "Appearance > Themes > Add New Theme: Only in wp-admin", "Appearance > Customize: Part in the Workbench, the rest in wp-admin", "Tools > Theme File Editor: Only in wp-admin".
  - Templates: Appearance > Editor (opens directly).
  - Global Styles: Appearance > Editor > Styles.
  - Additional CSS: Appearance > Customize > Additional CSS.
  - Template Parts, Patterns, Fonts and the Appearance folder: none; spoken `No wp-admin screen is nearer to this place than the Workbench itself. Overview > wp-admin Screens lists them all.`
- Announced: `{why} Opening {screen} on {site} in your browser.`
- Review notes:
  - Template Parts finds nothing, while Templates finds the Site Editor: the lookup falls back from `template_parts` to `template`, which is not a node key.
  - Customize is mapped to Themes, not to the Appearance folder, so on a classic theme the Customizer is two levels away from where people expect it.

## Plugins and themes

Plugins are a real list you can act on: WordPress's REST API activates, deactivates, installs and deletes plugins, so the Workbench does those (install from WordPress.org's directory, after consent and a preview). Updating a plugin, automatic updates, and every theme change except reading are not on the REST API, so those rows hand you to wp-admin, saying why first. New since wp_missing.md: Check for Updates on WordPress.org compares each plugin, theme and WordPress itself with WordPress.org's current version and marks the row "update waiting", "up to date" or "unknown". The wp-admin map now knows the plugins' own screens. Both are being worked on today (see "What exists and what is in progress" at the end of this section).

### The Plugins node

- How to reach it: Ctrl+Shift+6 (Go > Plugins, `P&lugins`, help "This site's plugins."); Sites > site > Plugins; the editor's Tools > WordPress > Manage > Plugins... door.
- What the list shows: columns plugin, version, status, author, sorted by name. Status is `active`, `inactive` or `network active`. Detail: `{name}, version {version}, {active or inactive}, by {author}. Updates and automatic updates are in wp-admin: Open in Dashboard.` After Check on WordPress.org, ` WordPress.org: {facts}` is added; after Check for Updates, the version cell may read `{installed}, update waiting: {latest}` and the detail gains a sentence (below).
- Group By: Plugins is one of the nodes View > Group By (Ctrl+Alt+G) can split into child nodes by a column, for example by status.
- F1 on the node: "The installed plugins, active and not."
- F1 on a row: "A plugin. Activate or Deactivate is on the context menu, and Check for Updates on WordPress.org says whether one waits; updates run in wp-admin, through Open in Dashboard."
- Context menu: Read in Full (default), Activate or Deactivate, Check on WordPress.org..., Find a Plugin on WordPress.org..., Open in Dashboard, Check for Updates on WordPress.org..., Show Only and Hide, Properties.... (Six rows plus Properties, so no More submenu.)
- Without permission: the node needs `activate_plugins`; anyone below Administrator sees `Turning plugins on and off needs the Administrator role or higher. You are an Editor on {site}.` instead of the list.
- Code: workbench_load.py (load_plugins), workbench_actions.py, workbench_admin_actions.py (PLUGIN_ROWS), workbench_gap_actions.py (UPDATE_CHECK).
- Review notes:
  - Every row's detail ends with "Updates and automatic updates are in wp-admin: Open in Dashboard." The same sentence on every one of forty plugins is exactly the chattiness GATE-13 warns about; say it once in the node's F1 or the status bar.
  - Delete a plugin: not found as a row action, although `wp/v2/plugins` can delete (the map's Plugins row says "Activate, deactivate, install and delete are in Plugins").
  - The refusal for an Editor talks about turning plugins on and off when they only opened the list.

### Read in Full (plugin, default)

- How to reach it: Enter, or the first context-menu row.
- What it does: focus to the details pane with the detail sentence above.

### Activate or Deactivate

- How to reach it: context-menu label "Activate or Deactivate". No key.
- What opens: a Yes/No message box titled "Activate" or "Deactivate", buttons "Activate" or "Deactivate" and "Cancel"; Cancel is the default.
- Confirmation wording: `Activate {plugin} on {site}?` or `Deactivate {plugin} on {site}?`. For QUILL Accessible Forms (or its older name, BITS Accessible Forms), `Deactivate` adds `QUILL relies on this plugin for QUILL's Forms commands and Held as Spam for form entries. Turning it off stops that.` (or the older-name wording).
- Refused before asking: deactivating the Application Passwords plugin: `QUILL signs in to {site} through this plugin, so turning it off here would lock the Workbench out before it could turn it back on. Turn it off in wp-admin's Plugins screen if you mean to.`
- Announced after: `{plugin} is now active on {site}.` or `... inactive on {site}.` The site is then read again in the background (types, fields and permissions), and the tree is rebuilt.
- Undo: Ctrl+Z sets the old status back; spoken `{plugin} put back.`
- Without permission: needs `activate_plugins`, tier Write; refusal `Turning plugins on and off needs the Administrator role or higher. You are ...`; under Read Only or Organize access, the access sentence.
- Keyless: no written reason found in the KEYLESS tables I read.
- Code: wordpress_workbench_commands.py (do_toggle_plugin), workbench_permissions.py (deactivate_refusal, deactivate_warning).
- Review notes:
  - The label "Activate or Deactivate" does not say which it will do for this row. A listener must read the status column first or wait for the message box. Label it from the row's status ("Deactivate..." on an active plugin), and add the ellipsis since it asks.
  - The plugin's Properties sheet has an editable Status choice (active, inactive). Saving it goes through the generic sheet save, which has no preview and never calls `deactivate_refusal` or `deactivate_warning`. So Alt+Enter, Status, inactive, OK can turn off the Application Passwords plugin that the context menu refuses to touch, locking the Workbench out. Read from wordpress_workbench_sheets.py and workbench_sheets.py; not tried live. This is the most serious finding in this section.
  - "{plugin} put back." does not say which state it went back to.
  - Network-active plugins on a multisite: deactivating sends `inactive` from a single site's route; not verified what WordPress does.

### Check on WordPress.org...

- How to reach it: context-menu label "Check on WordPress.org..." on a plugin row.
- What opens: the first time in this window, a Yes/No message box titled "Ask WordPress.org", buttons "Ask" and "Cancel" (Cancel default): `Ask WordPress.org's plugin directory? QUILL sends the words you type, or the short names (slugs) of the plugins in question, to api.wordpress.org. No site address, account or password is sent.` Then a report window titled `Plugins on {site}, from WordPress.org`, one line per plugin, `{name}: {facts}`, then a blank line and two limits: `WordPress's REST API cannot update a plugin or turn its automatic updates on or off.` and the no-rollback paragraph (`There is no rollback: WordPress's REST API cannot put a plugin back to an earlier version. ...`).
- The facts: `{name}, version {v}, by {author}, rated {x} of 5 by {n} people, {n}+ active installs, last updated {date}, tested up to WordPress {v}, needs WordPress {v} and PHP {v}.` plus a warning when it applies: `WordPress.org closed {name} on {date} ({reason}): it gets no updates there and cannot be installed from it.` or `{name} has not been updated on WordPress.org since {date}, over two years: it may be abandoned.` Not listed: `{name} is not in the WordPress.org directory (a paid, custom or retired plugin), so QUILL cannot say whether it is kept up to date.`
- Announced: declining the consent says `Nothing was sent to WordPress.org.` The facts are then added to every plugin row's detail for the rest of this window.
- F1 of the report: "Each plugin on this site as WordPress.org's directory describes it, with a warning for any it has closed or not seen updated in two years."
- Without permission: no requirement (tier Read); the Plugins node itself needs `activate_plugins`.
- Keyless: "Checked now and then, after you agree to ask (rule 9)."
- Code: wordpress_workbench_admin_commands.py (do_plugin_directory), dotorg.py.
- Review notes:
  - The row command checks every plugin on the site, not the row it was chosen on; the label reads as if it is about this plugin.
  - Consent is asked once per window per kind of question (plugins, themes, updates, languages): four separate "Ask WordPress.org" boxes for one source. Reasonable for privacy, but the person may agree four times in one session and is never told the agreement lasts only until the window closes.

### Find a Plugin on WordPress.org...

- How to reach it: context-menu label "Find a Plugin on WordPress.org..." on a plugin row.
- What opens: dialog "Find a Plugin on WordPress.org", text box "Search for:" (access key S), help "Words in the plugin's name or description. Only these words are sent."; then (first time) the plugins consent box above; then list dialog "Plugins on WordPress.org", list "Plugins:" (access key P), each row the plugin's facts with its description; then a preview titled "Install {name}", button "Install".
- Preview wording: summary `Each site installs {name} ({slug}) from WordPress.org, inactive. A plugin not in the WordPress.org directory fails on that site and the rest go on. WordPress's REST API cannot update a plugin or turn its automatic updates on or off. There is no rollback: ...`; lines `{site}: installs {slug}, left inactive` and the plugin's facts.
- Announced after: `{name} installed on 1 of 1 sites, inactive.` with ` Not installed: {site}: {error}` on failure. None found: `WordPress.org has no plugin matching {words}.` Not on a site row: `Find a Plugin works on a site's Plugins list.`
- Undo: none recorded.
- Without permission: needs `install_plugins`, tier Write; refusal `Doing this (install plugins) needs the Administrator role or higher. You are ...` (install_plugins has no plain-words entry in the refusal table).
- Keyless: "A new plugin is added a few times a year, previewed (rule 9)."
- Code: wordpress_workbench_admin_commands.py (do_find_plugin, _install_preview).
- Review notes:
  - The consent question comes after you have typed the search, so declining wastes the typing; Check on WordPress.org asks first.
  - The install is not in Change History. Ctrl+Z right after it undoes the change before it, silently. Either record it with an undo (delete the inactive plugin) or record it as "cannot be undone".
  - After installing, the plugin is inactive and the next step (Activate) is not offered; the person must find the new row and use Activate or Deactivate.
  - "installed on 1 of 1 sites" is the multi-site sentence reused for one site.
  - The refusal sentence reads "Doing this (install plugins)", the only place a raw capability name is spoken.
  - The command needs a plugin row to be selected; on a site with no plugins listed there is no row, so no way to find the first plugin.

### Open in Dashboard (plugin)

- How to reach it: context-menu label "Open in Dashboard" on a plugin row.
- What it does: says `WordPress's REST API cannot update a plugin or turn its automatic updates on or off. Opening Plugins on {site} in your browser.` and opens `wp-admin/plugins.php`. No address: `{site} has no address QUILL knows, so Plugins cannot be opened.`
- Keyless: "Leaves QUILL for the browser, now and then (rule 9)."
- Code: wordpress_workbench_admin_commands.py (do_open_dashboard), workbench_no_rest.py.
- Review notes:
  - The row help shared with themes says "for a theme, activating and installing", on a plugin row.
  - It opens the whole Plugins screen, not this plugin; the person has to find the plugin again in wp-admin's table.
  - After an update waiting is found, the detail says "Dashboard > Updates runs it", but Open in Dashboard on a plugin row goes to Plugins, not Dashboard > Updates.

### Check for Updates on WordPress.org... ("update waiting")

- How to reach it: context-menu label "Check for Updates on WordPress.org..." on a plugin row, a theme row, and a Needs My Attention > Updates row. No key.
- What opens: the first time in this window, a Yes/No message box titled "Ask WordPress.org", buttons "Ask" and "Cancel" (Cancel default): `Ask WordPress.org which versions are current? QUILL sends the short names (slugs) of this site's plugins and themes to api.wordpress.org, and asks for the current WordPress. No site address, installed version, account or password is sent.` Then it works in the background ("asking WordPress.org for current versions"); no further dialog.
- What changes: for this window, every plugin, theme and Updates row of that site is marked. The Update cell (Updates node) or the version cell (Plugins and Themes) reads one of:
  - `Update waiting: version {latest}` (on Plugins and Themes the version cell becomes `{installed}, update waiting: {latest}`), detail `WordPress.org has version {latest}; this site has {installed}, so an update waits. Dashboard > Updates runs it.`
  - `Up to date`, detail `WordPress.org has version {latest}, the version installed.`
  - `Unknown: the site does not say its version`, detail `WordPress.org has version {latest}; the site does not say which it has.`
  - `Unknown: not on WordPress.org`, detail `WordPress.org does not list it (a paid, custom or closed one), so whether an update waits is unknown.`
- Announced after: `{n} update(s) waiting on {site}: {names, up to six} and more.` or `Nothing on {site} has an update waiting on WordPress.org.`, then ` {n} not on WordPress.org, so unknown.` when any are unknown. Wrong row: `Choose a plugin, a theme or a row under Needs My Attention > Updates first.`
- Undo: nothing to undo (reads only).
- F1: the row's help, "After you agree to ask WordPress.org, compare this site's WordPress, plugins and themes with the versions WordPress.org has now, and mark each row update waiting, up to date or unknown. Only short names are sent. Paid plugins WordPress.org does not list say unknown."
- Without permission: no requirement; tier Read.
- Keyless: "Asked now and then, after you agree to ask (rule 9)."
- Code: workbench_update_check.py, wordpress_workbench_gaps.py (do_check_updates, with_update_facts), wordpress_workbench_window.py (rows marked on load).
- Review notes:
  - This is the cheapest real win wp_missing.md asked for, and it is here. But it checks one site per run. On Needs My Attention > Updates, which gathers every site, you must run it once per site (choosing a row of each), and the marks last only until the window closes. There is no "check every site" and no Watch that uses it.
  - The Watch "Plugin updates available" (workbench_watches.py) still looks only for an update field the site itself sends, which core WordPress never sends, so the Watch stays silent even after this check finds updates.
  - A plugin WordPress.org has closed is marked `Unknown: not on WordPress.org` (latest_plugins returns None for a closed plugin). A closed plugin is a security warning, not an unknown; Check on WordPress.org says "closed", this check hides it.
  - Each row's detail keeps the earlier sentence too, so an Updates row can say "REST does not say whether an update waits." and then "so an update waits." in one detail.
  - The command is on every plugin row, but it checks all of the site's plugins and themes and WordPress; the label suggests it is about the row.
  - Up to 100 theme lookups, one request a theme; plugins one request each. On a site with many plugins this is slow, with no progress said beyond the background task name.

### Properties (plugin)

- How to reach it: Alt+Enter, last context-menu row, Item > Properties.
- What opens: sheet `{plugin} Properties - {site}`, page General: Name, Version, Author, Description (multi-line), Status (a choice of `active` and `inactive`, needs `activate_plugins`), Needs WordPress, Home page (a link). All but Status read only.
- Announced after a save: `Saved 1 change to {plugin} on {site}.`; Ctrl+Z `Put {plugin} back as it was.`
- Review notes:
  - See Activate or Deactivate: the Status choice skips the lockout refusal, the QUILL-relies-on warning and the confirmation.
  - No "update waiting", WordPress.org facts, "Needs PHP" or "Network only" on the sheet, though the row's detail and `wp/v2/plugins` carry them.

### Theme rows: Activate...

- How to reach it: context-menu label "Activate..." on a theme row (Appearance > Themes).
- What it does: no dialog. Says `WordPress's REST API only reads themes: it cannot activate, update or delete one, or turn its automatic updates on. Opening Appearance > Themes on {site} in your browser.` and opens `wp-admin/themes.php?theme={stylesheet}`. Already active: `{theme} is already the theme on {site}.`
- Without permission: needs `switch_themes`; the Themes node already refuses non-administrators.
- Keyless: no written reason found in the KEYLESS tables I read.
- Code: wordpress_workbench_admin_commands.py (do_activate_theme), workbench_no_rest.py.
- Review notes:
  - The label has an ellipsis but opens no dialog; it opens the browser.
  - The spoken reason starts with "it cannot activate" immediately after you asked to activate, which sounds like a failure. Lead with the hand-off: "Activating happens in wp-admin; opening Appearance > Themes ...".
  - Nothing comes back: the Workbench does not notice the switch until a later read, when (up to five minutes later, on the next request) it announces `{site} changed since QUILL last looked: the theme is now {stylesheet and version}...` out of context.

### Theme rows: Find a Theme on WordPress.org...

- How to reach it: context-menu label "Find a Theme on WordPress.org...".
- What opens: dialog "Find a Theme on WordPress.org", text box "Search for:" (access key S), prefilled with the selected theme's name; help "Words in the theme's name or description. Only these words are sent." Then (first time) the consent box: `Search WordPress.org's theme directory? QUILL sends the words you type to api.wordpress.org, and nothing about your sites.` Then list dialog "Themes on WordPress.org", list "Themes:" (access key T), help "Each theme in words. OK opens Add New for it on your site." Each row `{name}, version {v}, by {author}, rated {x} of 5 by {n} people, needs WordPress {v} and PHP {v}. {description}`.
- What happens after OK: wp-admin's Add New Theme screen opens, searching for the slug, saying `WordPress's REST API cannot install a theme. Opening Appearance > Themes > Add New on {site} in your browser.`
- Announced: none found `WordPress.org has no theme matching {words}.`
- Keyless: "Choosing a new theme happens a few times a year (rule 9)."
- Review notes:
  - Prefilling the search with the theme you already have makes the first search find that theme. An empty box would be the better start.
  - The search, the consent and the list all happen in QUILL, then the job is finished in wp-admin's theme browser, which is visual and searches again. The hand-off is honest but it is a dead end for a screen-reader user who wanted QUILL to install it.
  - No requirement is checked, although installing a theme needs `install_themes`.

### Theme rows: Open in Dashboard and Check for Updates

- Open in Dashboard: says `WordPress's REST API only reads themes: it cannot activate, update or delete one, or turn its automatic updates on. Opening Appearance > Themes on {site} in your browser.` and opens `wp-admin/themes.php`.
- Check for Updates on WordPress.org...: as for plugins; theme rows get `{installed}, update waiting: {latest}` in their version cell.
- Review notes:
  - Activate... and Open in Dashboard open the same screen with the same sentence (Activate adds `?theme=`); two rows, one job.
  - Delete a theme, update a theme, theme auto-updates: wp-admin only, said in the row; no Workbench path.

### wp-admin map rows for plugins

- Where they show: Sites > site > Overview > wp-admin Screens lists every screen (core and, where the site's REST index has the plugin's namespace, the plugin's screens), and "wp-admin for This Place..." on a node's tree context menu (under More) offers the screens whose nearest node it is.
- The core Plugins rows (from workbench_admin_map.py):
  - "Plugins > Installed Plugins", `wp-admin/plugins.php`, nearest Plugins, "Part in the Workbench, the rest in wp-admin": `Activate, deactivate, install and delete are in Plugins; updates and automatic updates are not in REST.`
  - "Plugins > Add New Plugin", `wp-admin/plugin-install.php`, nearest Plugins, "All of it in the Workbench": `Find a Plugin on WordPress.org installs one, after a preview.`
  - "Tools > Plugin File Editor", `wp-admin/plugin-editor.php`, nearest Plugins, "Only in wp-admin": `No REST route edits plugin files, and many hosts turn this screen off.`
- The plugin screens (from workbench_admin_map_plugins.py), each offered only when the site lists the plugin's namespace:
  - Gravity Forms (`gf/v2`): Forms > Forms (nearest Forms, both), Forms > Entries (Responses, all in the Workbench), Forms > Settings (Forms, only in wp-admin).
  - QUILL Accessible Forms (`qaf/v1`): Accessible Forms, `admin.php?page=qaf` (Forms, all in the Workbench). The source marks this slug unverified.
  - Redirection (`redirection/v1`): Tools > Redirection (Redirects, both), Tools > Redirection > 404s (404 Log, all in the Workbench).
  - WooCommerce (`wc/v3`): Products > All Products (Shop), WooCommerce > Orders (Shop Orders), Analytics > Overview (Shop Reports), WooCommerce > Settings (Store Settings), all "both"; WooCommerce > Status > Scheduled Actions and WooCommerce > Extensions (Shop, only in wp-admin).
  - The Events Calendar (`tribe/events/v1`): Events, Venues, Organizers, Event Categories (all in the Workbench), Events > Settings and Events > Import (only in wp-admin).
  - Yoast SEO (`yoast/v1`): Yoast SEO > Settings, nearest Settings, only in wp-admin.
  - Paid Memberships Pro (`pmpro/v1`): Dashboard, Settings > Levels, Members, Orders, Discount Codes (both), Reports and Settings > Payment Gateway (only in wp-admin).
- A row's detail: `{screen}, {path}. {reach}. {says} Nearest place in the Workbench: {place}. Enter opens it in your browser.`
- Row actions and wording: see "The wp-admin Screens node" under Tools.
- Review notes:
  - The WooCommerce Settings row now says Store Settings changes settings, which fixes the stale line wp_missing.md flagged.
  - Only seven plugins are mapped. Every other installed plugin's settings screen (a cache plugin, a security plugin, an SEO plugin other than Yoast) is not reachable through wp-admin for This Place on Plugins. A plugin row has no "Open Its Settings" action. Not found in code.
  - "wp-admin for This Place" is on the tree's node menu, under More, fourth of four. On the Plugins list you must move to the tree, open its context menu, open More, and find it. It is not on the plugin row's own menu.
  - "All of it in the Workbench" for Add New Plugin is generous: wp-admin's screen also uploads a plugin zip, which the Workbench cannot.

### What exists and what is in progress

- Exists in code now (read 2026-11-14 at the end of this pass): Check for Updates on WordPress.org on plugin, theme and Updates rows; marking rows `Update waiting: version {latest}`, `Up to date`, `Unknown: not on WordPress.org`, `Unknown: the site does not say its version`; the spoken summary; marks kept for the window. Plugin screens for Gravity Forms, QAF, Redirection, WooCommerce, The Events Calendar, Yoast SEO and Paid Memberships Pro in the wp-admin map.
- In progress (another worker was changing workbench_update_check.py, workbench_actions.py, workbench_admin_map_plugins.py and wordpress_workbench_gaps.py during this pass; no engineering-log entry for either yet): anything beyond the above, such as checking every site at once, a Watch that uses WordPress.org's answer, an update column on the Plugins list, or more plugins in the map. Treat the descriptions above as a snapshot.

## Settings

Sites > site > Settings lists the settings WordPress's REST API reads and writes (`wp/v2/settings`), each with a plain sentence of what it does on this site, using the site's own values as the example: "Posts page: News, so visitors see your latest posts at ...". This is one of the best-explained lists in the Workbench. Changing a setting is done on its Properties sheet, with a preview and Ctrl+Z. The weak spot is that sheet: every setting, whatever its kind, is changed by typing its raw stored value into one text box.

### The Settings node

- How to reach it: Ctrl+Shift+8 (Go > Settings, `Settin&gs`, help "This site's settings."); Sites > site > Settings; the editor's Tools > WordPress > Site Settings... door.
- What the list shows: columns setting, value, in this order where the site sends them: Site title, Tagline, Site language, Time zone, Date format, Time format, First day of the week, Administrator email, Front page shows, Front page, Posts page, Posts per page, New posts take comments, New posts take pingbacks, Turn emoticons into pictures, Default post format, Site icon. The value is friendly: pages by title (or `page {n}`, or `none`), choices by their words (`Your latest posts`, `Yes`, `Monday`, `Standard`), the on/off setting as `yes` or `no`, the icon as `picture {n}` or `none`, empty text as `(empty)`.
- Detail: `{label}: {value}. {explanation}`, for example the date format's `{format}: a date reads {example}.`, start of week `Calendars start their week on {day}.`, email `{address}: where WordPress sends notices meant for whoever runs the site. Changing it sends a confirmation there first.`, emoticons `Typed :-) becomes a picture, which a screen reader names by its alt text.` or `Typed :-) stays as text, the way a screen reader reads it best.`
- F1 on the node: "The site's settings the REST API can read and change."
- F1 on a row: "A setting. Alt+Enter changes it."
- Context menu: Read in Full (default), Language Pack Status..., Show Only and Hide, Properties....
- Without permission: the node needs `manage_options`; anyone below Administrator sees `Changing site settings needs the Administrator role or higher. You are an Editor on {site}.` instead of the list.
- Code: workbench_load.py (load_settings), site_admin.py (SETTINGS_FIELDS, CHOICES, settings_value_text), workbench_settings_help.py.
- Review notes:
  - The explanations are excellent and should be the model for other lists.
  - The refusal says "Changing" to someone who only opened the list. An Editor cannot even read the site's time zone or date format here.
  - Missing from the list because REST does not carry them (said only in the wp-admin map rows): who may register, the default role, the WordPress and site addresses, permalinks, search engine visibility, the privacy policy page, media sizes, discussion's moderation settings.
  - The Site icon reads `picture {number}`; the picture's title is not looked up, unlike the front and posts pages.

### Read in Full (setting, default)

- How to reach it: Enter, or the first context-menu row.
- What it does: focus to the details pane with the explanation.
- Review notes:
  - Row help says "Alt+Enter changes it", which is right, but Enter is what people press to change a value in a list; a setting's Enter could open the change directly.

### Properties: Change a Setting

- How to reach it: Alt+Enter on a setting row, the last context-menu row, or Item > Properties.
- What opens: sheet `{label} Properties - {site}`, page General: Setting (read only, the label) and Value (a text box, needs `manage_options`). Then, after OK, a preview titled "Change a Setting", button "Change".
- Preview wording: summary `Change {label} on {site}. Ctrl+Z puts it back.`; one line `{label} ({key}): {old} becomes {new}`, with `(empty)` for an empty value.
- Refused before the preview: a site address (`url`, `home`, `siteurl`): `The site address is not changed from the Workbench. QUILL signs in at the site's address, and a wrong address locks everyone out of wp-admin too. Change it in wp-admin's Settings > General, then reconnect the site.`; the default role set to administrator: `New users are never made Administrators by default: anyone who signs up would control the site. Choose Subscriber, or another role without manage_options.`
- Announced after: `Saved 1 change to {label} on {site}.`, plus ` The site did not keep: ...` when WordPress dropped it.
- Undo: Ctrl+Z; spoken `Put {label} back as it was.`
- Cancel: Cancel on the sheet or the preview sends nothing.
- Without permission: the Value field is read only, with the refusal as its F1 help.
- Code: workbench_sheets.py (the Setting sheet), wordpress_workbench_sheet_guards.py (setting_cleared), workbench_permissions.py (setting_refusal, setting_preview), workbench_edit.py (the save sends the typed text as the value).
- Review notes:
  - The Value box holds the raw stored value, not the friendly one the list shows: `posts` or `page` for Front page shows, a page number for Front page and Posts page, `0` to `6` for First day of the week, `open` or `closed`, an empty string for the standard post format, and the raw on/off for emoticons. The list knows the words (CHOICES) but the sheet offers no choice list, no page picker and no check box. A listener has to know WordPress's internal values to change most of these.
  - The value is sent as typed text, without converting it to a number or a true/false (workbench_edit.py puts the string straight into the body). Whether WordPress accepts "6" for start_of_week or "false" for use_smilies was not checked live.
  - The preview shows raw values too: "Front page (page_on_front): 12 becomes 34" tells a listener nothing about which pages those are.
  - The site-address and default-role guards can never fire from this list, because neither setting is in SETTINGS_FIELDS. Harmless, but the protection is in code nobody reaches here.
  - One setting per sheet: there is no batch sheet for settings, so changing title and tagline is two round trips.

### Language Pack Status...

- How to reach it: context-menu label "Language Pack Status..." on any setting row.
- What opens: the first time in this window, a Yes/No box titled "Ask WordPress.org", buttons "Ask" and "Cancel" (Cancel default): `Ask WordPress.org which language packs it has? QUILL sends each WordPress version number your sites run to api.wordpress.org, and nothing else.` Then a report window titled "Language Pack Status", one sentence per connected site (from dotorg.site_languages), then Copy All and Close. Report F1: "Each site's language and whether WordPress.org has its pack. Installing a pack is done in Dashboard > Updates or Settings > General."
- Announced: declining says `Nothing was sent to WordPress.org.`
- Without permission: no requirement; it reads each site's settings, so a site where you are not an Administrator may fail.
- Keyless: "Checked after a WordPress release, not daily (rule 9)."
- Code: wordpress_workbench_admin_commands.py (do_language_packs), dotorg.py.
- Review notes:
  - It is on one site's setting rows but reports on every connected site. The label and placement suggest this site.
  - Installing a missing pack is wp-admin only (`WordPress's REST API cannot install or update a language pack.`), but the report has no "open Settings > General" action.

### wp-admin for This Place (Settings)

- How to reach it: tree context menu on Settings, under More, "wp-admin for This Place...".
- What it offers: list dialog "wp-admin for This Place", list "Screens:", rows: "Settings > General: Part in the Workbench, the rest in wp-admin", "Settings > Writing: Part in the Workbench, the rest in wp-admin", "Settings > Reading: Part in the Workbench, the rest in wp-admin", "Settings > Permalinks: Only in wp-admin", "Settings > Privacy: Only in wp-admin", and, where Yoast SEO is present, "Yoast SEO > Settings: Only in wp-admin". Help: "The wp-admin screens nearest here. OK opens the one chosen."
- Announced: `{why} Opening {screen} on {site} in your browser.`, for example `Title, tagline, email, language, time zone and formats are in Settings; who may register, the default role and the WordPress and site addresses are only in wp-admin. QUILL never changes the addresses: a typo locks the owner out. Opening Settings > General on {site} in your browser.`
- Review notes:
  - Settings > Media and Settings > Discussion are mapped to Media and Comments, so they do not appear here, where a person who knows wp-admin's Settings menu looks for them.
  - The reason sentences are long, and every one is spoken before the browser opens.

## Tools

There is no Tools node in the Workbench's site tree. workbench_tree.py has no `tools` node, and none of the site template's children is called Tools. wp-admin's Tools menu is instead spread across the tree by the wp-admin map: Site Health is its own node, privacy requests are Privacy Requests, Redirection is Redirects, import and export point at Posts, and the rest is "only in wp-admin". The places to reach these screens are Overview > wp-admin Screens (a list of every screen) and "wp-admin for This Place..." on a node's tree context menu. This section covers those, Privacy Requests and Administration Areas. The Workbench's own menu-bar Tools menu (Workbench Options, REST Console, Saved Requests, Plain-Language Batch, Practice Site, WXR Files) is out of scope here.

### Where wp-admin's Tools screens land

From ADMIN_MAP in workbench_admin_map.py (screen, address, nearest node, reach, what is said):

- Tools > Available Tools, `wp-admin/tools.php`, nearest More from This Site, only in wp-admin: `The categories and tags converter and Press This are not in REST.`
- Tools > Import, `wp-admin/import.php`, nearest Posts, only in wp-admin: `Importers are not in REST; Send a Folder as Drafts, in the editor, sends files.`
- Tools > Export, `wp-admin/export.php`, nearest Posts, only in wp-admin: `The WXR export is not in REST; Download My Writing, in the editor, saves posts.`
- Tools > Site Health > Status, `wp-admin/site-health.php`, nearest Site Health, all in the Workbench: `Every test the site offers over REST runs in Site Health.`
- Tools > Site Health > Info, `wp-admin/site-health.php?tab=debug`, nearest Site Health > Information, only in wp-admin: `The server, database and constants have no REST route.`
- Tools > Export Personal Data and Tools > Erase Personal Data, nearest Privacy Requests, only in wp-admin: `Privacy requests have no REST route.`
- Tools > Theme File Editor (nearest Themes) and Tools > Plugin File Editor (nearest Plugins), only in wp-admin: `No REST route edits theme files, and many hosts turn this screen off.` (plugin files likewise).
- Tools > Redirection and Tools > Redirection > 404s (where the Redirection plugin is), nearest Redirects and 404 Log.
- Review notes:
  - The Import and Export rows are stale. The Workbench's own Tools menu now has WXR Files > Export Site as WXR... and Import WXR as Drafts... (engineering log, 2026-11-14), yet the map still says "The WXR export is not in REST; Download My Writing, in the editor, saves posts." and marks both "Only in wp-admin". A person following the map is sent to the browser for something QUILL now does.
  - Tools > Available Tools maps to More from This Site, a list of REST namespaces; nothing there relates to the categories and tags converter. The Workbench does have Convert to Category or Tag... (Ctrl+Shift+K) on a term row, which the map does not mention.
  - With no Tools node, a person who knows wp-admin ("Tools > Site Health") has to know that Site Health is directly under the site, and that privacy is under Privacy Requests. The wp-admin Screens list is the only bridge, and it is under Overview, not where Tools would be.

### The wp-admin Screens node

- How to reach it: Sites > site > Overview > wp-admin Screens.
- What the list shows: columns screen, place, reach; one row per screen in ADMIN_MAP that this site has (a plugin's screens only where its REST namespace is listed). Reach is `All of it in the Workbench`, `Part in the Workbench, the rest in wp-admin`, or `Only in wp-admin`. Detail: `{screen}, {path}. {reach}. {says} Nearest place in the Workbench: {place}. Enter opens it in your browser.`
- F1 on the node: "Every wp-admin screen, the place in the Workbench nearest to it, and how much of it REST reaches. Enter opens the screen in your browser."
- F1 on a row: "A wp-admin screen. Enter opens it in your browser after saying what REST cannot do there; Go to Its Place selects the nearest node in the Workbench."
- Context menu: Open in Dashboard (default), Go to Its Place in the Workbench, Read in Full, Show Only and Hide, Properties....
- Code: workbench_dashboard_places.py (DASHBOARD_NODES, SCREEN_ROWS), workbench_admin_map.py, workbench_admin_map_plugins.py, workbench_dashboard.py.
- Review notes:
  - A row's spoken detail is long: name, raw path, reach, reason, place, instruction. The path (`wp-admin/options-general.php`) is the least useful part for a listener and comes second.
  - There is no filter by reach, so finding "what can I only do in wp-admin" means Filter Builder or Show Only on the reach cell.

### Open in Dashboard (wp-admin Screens row, default)

- How to reach it: Enter on a row, or the first context-menu row.
- What it does: says `{says} Opening {screen} on {site} in your browser.` and opens the screen's full address. No address: `{site} has no address QUILL knows, so {screen} cannot be opened.`
- Keyless: "Enter does it on a wp-admin Screens row."
- Code: wordpress_workbench_site_editor.py (do_open_admin_screen, _open_screen_row).
- Review notes:
  - For a screen marked "All of it in the Workbench", Enter still leaves for the browser, after saying the Workbench does it all. The default for those rows could be Go to Its Place.

### Go to Its Place in the Workbench

- How to reach it: context-menu label "Go to Its Place in the Workbench".
- What it does: selects the nearest node in the tree and moves focus to the tree. When the node does not exist for this site: `{row title} has no place in the Workbench on {site}.` Wrong row: `Choose a wp-admin screen first.`
- Keyless: "The tree is a keystroke away; this is a shortcut to it (rule 9)."
- Review notes:
  - Nothing is announced on success beyond what the tree says on focus, which is right by GATE-13.
  - The failure sentence names the row by its internal key (for example `plugin_install has no place ...`): a wp-admin Screens row has no title-like cell, so its title falls back to its key.

### Properties (wp-admin Screens row)

- What opens: no sheet is written, and the row has no route, so a read-only sheet of its raw data: fields Node, Why, Name, labelled from the keys. Node shows the internal node key (`overview`, `site_health_info`). The sheet title is `{screen key} Properties - {site}`.
- Review notes:
  - Not useful: everything here is already in the detail, and Node is an internal name. The engine requires Properties last on every menu, so it cannot be removed, but it could show the screen, path, reach and reason with proper labels.

### wp-admin for This Place...

- How to reach it: on the tree, the node's context menu (Applications key or Shift+F10 on the tree, or on an empty list), under More: the node menu is Refresh, New Here..., Load More, Load All, Columns..., Group By..., then More (What Can I Do Here?, Counts by Status, Empty Trash..., wp-admin for This Place...), then Properties.
- What opens: if the node has one nearest screen, nothing: it opens it. If several, a list dialog "wp-admin for This Place", list "Screens:" (access key S), rows `{screen}: {reach}`, help "The wp-admin screens nearest here. OK opens the one chosen." A status or group child borrows its parent's screens.
- Announced: `{says} Opening {screen} on {site} in your browser.` None: `No wp-admin screen is nearer to this place than the Workbench itself. Overview > wp-admin Screens lists them all.` Not on a site: `wp-admin for This Place works on a site's nodes.`
- Keyless: "Leaves QUILL for wp-admin, only for what REST cannot do (rule 9)."
- Code: workbench_dashboard_places.py (NODE_ROWS), wordpress_workbench_site_editor.py (do_admin_here), workbench_admin_map.py (screens_for).
- Review notes:
  - Buried: fourth of four under More, on the tree's menu only. A row's own menu never has it. For the job it exists for (the thing REST cannot do here), it should be one level up.
  - The keyless reason says "only for what REST cannot do", but it also opens screens the map marks "All of it in the Workbench" (Menus, Widgets, Posts), with no question first.
  - "Empty Trash..." and "Counts by Status" sit beside it on every node's menu, including Menus, Settings and Site Health, where they mean nothing.

### The Privacy Requests node

- How to reach it: Sites > site > Privacy Requests.
- What the list shows: columns problem, status. Normally two rows, "Export Personal Data" and "Erase Personal Data", each with status `in wp-admin`. Detail for export: `Export requests are kept in wp-admin: Tools > Export Personal Data. Enter opens it in your browser, where you add, confirm and send each export. WordPress's REST API has no route for these requests, so QUILL cannot list, confirm or complete them, and cannot tell afterwards whether they were done.` (Erase: the same shape, "add, confirm and erase each request".) If the site's REST index does list a privacy-request route (a plugin's), the rows are that route instead: `{site} offers {route} for requests.`
- F1 on the node: "Where wp-admin keeps personal data export and erase requests; Enter opens it."
- F1 on a row: "A wp-admin screen for privacy requests. Enter opens it in your browser."
- Context menu: Open This wp-admin Screen (default), Read in Full, Show Only and Hide, Properties....
- Code: workbench_sweep.py (privacy_rows), workbench_sweep_places.py, wordpress_workbench_sweep.py.

### Open This wp-admin Screen (privacy)

- How to reach it: Enter, or the first context-menu row.
- What it does: opens the screen, then says `Opened {screen} for {site} in your browser. Requests are confirmed and done there; QUILL cannot see whether they were.` Wrong row: `Choose Export or Erase Personal Data first.`
- Keyless: "Enter opens it; privacy requests are rare (rule 9)."
- Review notes:
  - Honest and complete for what REST allows. It is a pure hand-off: the node lists two fixed rows, not the requests, so it cannot tell you whether any request is waiting, which is the one thing a site owner needs from it (a legal deadline applies to these).
  - When a plugin route exists the rows become plain problem rows (Read in Full and Properties only) that name the route, with no way to open or act on the requests.

### Administration Areas

- How to reach it: Sites > site > Administration Areas.
- What the list shows: columns area, where, plugins; one row per area of running a site (Redirects, Privacy requests, Content audit, Media housekeeping, Search and sitemaps, Scheduled tasks, SSL and the address, Someone else is editing, Backups, Security, sign-ins and two-factor, Caching and speed, Multilingual sites, Consent and cookies, Email delivery, Newsletters and subscribers, Courses, and more), each with where QUILL handles it, the plugins that provide it, and a boundary sentence (for example `No cache is purged by QUILL. QUILL has no adapter for these plugins: ...`).
- F1 on the node: "Every part of running a site: what QUILL does, and where the rest is."
- F1 on a row: "One part of running a site. Enter goes where QUILL or wp-admin handles it."
- Context menu: Go There (default), Read in Full, Show Only and Hide, Properties....
- Code: workbench_coverage.py (THIRD_SWEEP), workbench_sweep_places.py, wordpress_workbench_sweep.py.

### Go There (administration area)

- How to reach it: Enter, or the first context-menu row.
- What it does: selects QUILL's node for the area if there is one (focus to the tree); else the plugin's namespace under More from This Site, if the site has it; else opens the wp-admin screen and says `Opened {full address} in your browser.`
- Keyless: "Enter does it on the row."
- Review notes:
  - The browser case speaks the whole address (`Opened {full address} in your browser.`, the row's link, which for most areas ends in `wp-admin/plugins.php?plugin_status=active`). Every other hand-off says the screen's name.
  - For Backups, Security, Caching and most others the "screen" is the Plugins list filtered to active, not the plugin's own screen, so Go There lands on a generic list.
  - This list is the closest thing to a Tools node, and it is good orientation, but it is a flat list of 20-odd areas with long boundary sentences read in full.

### Import and export

- In the site tree: no node. The map's Import and Export rows say only in wp-admin (see above). The Workbench menu bar's Tools > WXR Files does WXR export and import (out of scope here).
- Review notes:
  - Fix the map rows so wp-admin for This Place on Posts and the wp-admin Screens list point at WXR Files instead of sending people to wp-admin.

### The Abilities node

- How to reach it: Sites > site > Abilities, a child of the site after Site Health. The editor's Tools > WordPress > Manage > AI Abilities... opens the Workbench here.
- What the list shows: columns ability, plugin, category, says; one row per ability the site's Abilities API offers (WordPress 6.9 or later).
- F1 on the node: "What the site's Abilities API offers, each a command you can run."
- F1 on a row: "An ability the site offers. Enter runs it, after a preview."
- Context menu, in order: Run... (default, Enter), Offer to Ask the Site, Properties...
- Code: workbench_tree.py, workbench_actions.py, wordpress_workbench_discovered.py.

### Run... (ability row, default)

- How to reach it: Enter on an ability row, or the context menu's first row. No key besides Enter.
- What opens: the shared sheet editor titled "Run {ability} - {site}", one field per input the ability takes. OK keeps the values; then a preview titled "Run {ability}" with the button "Run".
- Announced after: a report window titled "{ability} - {site}" with the ability's answer; its F1 says "What the ability answered."
- Cancel: closing the sheet without values, or Cancel on the preview, runs nothing and says nothing.
- Without permission: the row is listed as tier Read, but the access check raises it to Write for an ability that is not read-only, and to Destructive for one the site marks destructive (refusal_for in wordpress_workbench_people.py). Under a lower Workbench Access the access sentence is said; a WordPress role the site refuses comes back as the result.
- Keyless: no written reason found (Enter is its route).
- Review notes:
  - The menu cannot show in advance whether a given ability will change the site; the tier is only decided when it runs, so a Read Only window hears the refusal after choosing Run.
  - The cancel path is silent, unlike most Workbench previews.

### Offer to Ask the Site (ability row)

- How to reach it: an ability row's context menu (Applications key or Shift+F10), second row, "Offer to Ask the Site". Not in the Item menu, no key.
- What it does: turns on or off whether Ask the Site (Tools > WordPress > Manage > Ask the Site...) may suggest this ability. The choice is kept on this computer, per site, in the same per-site choices the editor's Abilities window used. Row help: "Turn on or off whether Ask the Site may suggest this ability. Kept on this computer; QUILL still asks you before every run."
- Confirmation: only when turning on an ability that is not read-only. Title "Offer to Ask the Site", message "Let Ask the Site offer {ability} on {site}? It can change the site. QUILL still asks you every time before it runs.", buttons Offer It and Cancel. Turning a read-only ability on, or any ability off, is immediate.
- Announced after: "Ask the Site may now offer {ability} on {site}." or "Ask the Site no longer offers {ability} on {site}."
- Failures: "Offer to Ask the Site works on one of the site's abilities." (wrong row); "Ask the Site is not available for {site} here." (site not connected here).
- Undo: nothing recorded; Ctrl+Z does not reverse it. Run the command again.
- Cancel: nothing changes, nothing is said.
- Keyless: no written reason found in code.
- Code: wordpress_workbench_discovered.py (do_offer_to_ask), workbench_actions.py.
- Review notes:
  - Before this row existed (added 2026-11-14, coordinator report), the AI Abilities door sent people to the Workbench, where nothing could turn an ability on, so Ask the Site's refusal "Turn them on one by one in Abilities" was a dead end. It is now reachable, but only from the context menu.
  - The label is a toggle that does not say its current state; the list has no column showing which abilities are offered. A person must remember, or run it and listen to the outcome to find out (which flips it).
  - Consider "Offered to Ask the Site" as a column, or the label changing to "Stop Offering to Ask the Site" when on.

## Site Health and maintenance

Upkeep is spread over several places: Sites > site > Site Health (WordPress's own tests over REST, plus QUILL's checks) with its Information and Security children; Needs My Attention > Site Health and Updates (gathered from every site); and the site's Search and Upkeep, Content Audit, Redirects with its 404 Log, and Media > Housekeeping. Almost everything here reads and explains; the only writes are redirects and moving an audit finding to the Trash. The writing is careful about where each answer comes from and what REST cannot say. The weak points are lists that are long but say little (Updates), problem rows with nothing to do but read, and two places that disagree about search engine visibility.

### The Site Health node

- How to reach it: Ctrl+Shift+9 (Go > Site Health, `Site &Health`, help "This site's health checks."); Sites > site > Site Health; the editor's Tools > WordPress > Site Check door.
- What the list shows: columns test, status, says, critical first, then should be improved, information, good. Status words are `Critical`, `Should be improved`, `Good` or `Information`. Rows come from QUILL's own checks and WordPress's tests: `WordPress version: {v}.`; `HTTPS: the site's address uses HTTPS.` or `HTTPS: the site's address does not use HTTPS. Visitors' browsers will call it not secure.` (critical); `Time zone: {zone}.` or `Time zone: a fixed offset of {n} hours. A city keeps daylight saving right.`; a permalinks line; settings lines; one line per Site Health test the site lists under `wp-site-health/v1/tests/` (its own label); for a failing authorization header, `What this means for QUILL: the web server drops the Authorization header before WordPress sees it, so application passwords cannot work. ...`; `{plugin}: recognised. QUILL offers {what}.` for The Events Calendar, WooCommerce, Yoast SEO, Rank Math and Abilities for AI; and always `Search engine visibility: WordPress does not share this over its API; it is under Settings, Reading in the dashboard.`
- When tests cannot run: `Health checks: only an administrator can run them.`, `{test}: the site could not run this test.`, or `PHP version, updates and loopback: this site does not offer its health checks to QUILL.`
- F1 on the node: "WordPress's own checks of how well the site is set up."
- F1 on a row: "A problem a check found. Enter reads what it means."
- Context menu: Read in Full (default), Show Only and Hide, Properties....
- Code: workbench_load.py (load_health), site_admin.py (site_check), site_health.py.
- Review notes:
  - The test column is the first sentence of the line and the says column is the whole line, so every row reads its first sentence twice.
  - Good rows say "A problem a check found." on F1, even for `HTTPS: the site's address uses HTTPS.`
  - Every test runs each time the node loads (each test is its own request; the loopback test waits on the site), with no cache; opening Site Health is slow on a slow host. Not measured.
  - "Search engine visibility: WordPress does not share this over its API" contradicts Search and Upkeep, which does judge it (from the sitemap) and says where its answer comes from. Two answers to one question in one tree.
  - Nothing to do on a problem row: no "Open in Dashboard" to the test's own screen, no "how to fix" link, although WordPress's test answers carry an actions link. The only hand-off is through the node's wp-admin for This Place (Tools > Site Health > Status, marked "All of it in the Workbench").

### Read in Full and Properties (Site Health row)

- Read in Full: Enter; focus to the details pane, which holds the line.
- Properties: no route and no written sheet, so a read-only sheet of the row's cells: Test, Problem, Status, Says, Site. Its title is `{row number} Properties - {site}` (the row has no title-like cell, so its title is its index).
- Review notes:
  - Test and Problem hold the same text; Says repeats it. Five fields, two facts.

### Information (Site Health > Information)

- How to reach it: Sites > site > Site Health > Information.
- What the list shows: columns test, status, says. First row "Server, database and constants" (an open-in-wp-admin row): `The Info tab (server, PHP, database and constants) has no REST route. Tools > Site Health > Info in wp-admin has it, and its Copy Site Info to Clipboard button gives your host the whole report. Enter opens it in your browser.` Then "Tests on REST": `The tests this site offers over REST, run in the Site Health node: {names}.` Then the directory sizes, one row each from the site's directory-sizes route, `{part}: {size}.` or `{part}: the site could not measure it ({why}).`, and `Altogether: {size}.`; or one row `Directory sizes: only an administrator can read them.`
- F1 on the node: "What REST covers of Site Health's Info tab: the tests and the directory sizes. The server, database and constants are only in wp-admin; their row opens Site Health Info."
- Context menu, first row: Open in Dashboard (default), Read in Full, Show Only and Hide, Properties.... Other rows: Read in Full (default), Show Only and Hide, Properties....
- Code: workbench_health_info.py, site_space.py.
- Review notes:
  - Open in Dashboard on that row opens the browser silently: it runs the generic open-on-site command, which speaks nothing, while Open in Dashboard on a plugin or theme row says its reason first. (The reason is in the row's detail, already heard.)
  - The directory sizes are the Workbench's only "space used" view; the editor's Tools > WordPress > Manage > Space Used is separate. WordPress computes these sizes on request, so this node can be the slowest in the tree; nothing warns.

### Security (Site Health > Security)

- How to reach it: Sites > site > Site Health > Security.
- What the list shows: two rows. "XML-RPC": status `Should be improved` when `xmlrpc.php` answers (`XML-RPC is on: xmlrpc.php answers and lists {n} methods, including pingbacks and methods that take a password. If nothing you use needs it (the Jetpack app and some old phone apps do), turn it off with a security plugin or at the web server. Whether a plugin has turned off only its sign-in cannot be told without trying a password, which QUILL never does.`), `Good` when blocked (`XML-RPC is off: xmlrpc.php does not answer ({why}). Nothing in QUILL needs it.`), else `XML-RPC: QUILL could not tell whether xmlrpc.php answers ({why}).` Then "QUILL and XML-RPC", information: `QUILL never uses XML-RPC: every job it does has a REST route, and XML-RPC takes a password on every call, lets one request try many passwords, and carries pingbacks that can be aimed at other sites.`
- F1 on the node: "Whether the site still answers on XML-RPC, which QUILL never uses, checked without a password."
- Context menu: Read in Full (default), Show Only and Hide, Properties....
- Code: workbench_health_info.py (xmlrpc_check, security_rows).
- Review notes:
  - Clear and careful. The name "Security" promises more than one check; the Administration Areas row for security plugins is where the rest is said, and nothing here links to it.

### Needs My Attention > Site Health

- How to reach it: Ctrl+1 (Go > Needs My Attention) then Site Health in the tree; or Needs My Attention > Site Health.
- What the list shows: columns problem, site, status; only the Critical and Should be improved rows from every connected site's Site Health list.
- F1 on the node: "Site Health problems on every site, worst first."
- Context menu: as for a Site Health row (Read in Full, Properties).
- Code: workbench_attention.py (_health).
- Review notes:
  - It runs every site's full Site Health (every test on every site) to keep a few rows; on several sites this is slow.
  - "Worst first" holds within a site; across sites the gathered rows are not re-sorted by status (not verified on a live run).

### Needs My Attention > Updates

- How to reach it: Needs My Attention > Updates.
- What the list shows: columns what, site, installed, update. For each site: a WordPress row (`WordPress {v} on {site}. WordPress's REST API does not say whether a newer WordPress or new translations wait; Dashboard > Updates does.`), an "Automatic updates" row from Site Health's background-updates test where the site offers it (`Automatic updates on {site}, from Site Health: {label}.`, or `Automatic updates on {site}: only an administrator can run this Site Health test.`), then every plugin and every theme with its installed version. The update cell is `Not reported over REST` until Check for Updates on WordPress.org marks it (see "Plugins and themes"); a plugin whose payload carries an update field says `Version {v} reported by the site`. Each row's detail ends ` REST does not say whether an update waits.` (or what the site reports) and, where the site says, ` It updates itself automatically.` or ` It does not update itself.`, then ` Enter opens Dashboard > Updates in your browser.` A site where you cannot list plugins gives one row: `Your role on {site} cannot list its plugins.`
- F1 on the node: "WordPress, plugin and theme versions; Check for Updates on WordPress.org, on any row's context menu, says which have an update waiting. Enter opens Dashboard > Updates."
- F1 on a row: "A version on the site and whether an update waits, once Check for Updates on WordPress.org has asked. Enter opens Dashboard > Updates in your browser."
- Context menu: Open Dashboard Updates in the Browser (default), Read in Full, Check for Updates on WordPress.org..., Show Only and Hide, Properties....
- Code: workbench_updates.py, workbench_attention.py, workbench_update_check.py.
- Review notes:
  - This is the least "needs my attention" list in Needs My Attention: it lists every plugin and theme on every site, waiting or not. Even after Check for Updates, the up-to-date rows stay. It should list only what waits (after the check) or be renamed Versions.
  - Check for Updates runs per site, so with five sites the person runs it five times from rows of each site; the marks are lost when the window closes.
  - Open Dashboard Updates in the Browser opens silently (the generic open-on-site command), while the detail already said it.
  - The Properties sheet for a plugin or theme row is the raw REST payload (fields labelled from their keys, for example "Plugin uri", "Requires php", "Textdomain"); for the WordPress row, the four cells.

### Open Dashboard Updates in the Browser (Updates row, default)

- How to reach it: Enter on an Updates row.
- What it does: opens `wp-admin/update-core.php` for the row's site. Nothing is spoken. If the row has no link (the site's address unknown), the command falls back to the site's own address, and says `This has no address on the site yet.` only when that is empty too.
- Keyless: it is Enter.
- Review notes:
  - Updates are the one maintenance job a site owner must do, and here it is a pure hand-off to wp-admin's Updates screen, which is a long form of check boxes. Said honestly in every row; still a dead end.

### The Search and Upkeep node

- How to reach it: Sites > site > Search and Upkeep.
- What the list shows: columns what, state, source. Rows: search engine visibility (from `blog_public` if the site sends it, else judged from `wp-sitemap.xml`: `{site} lets search engines index it.`, `{site} asks search engines not to index it.`, `{site} serves WordPress's sitemap, so it probably lets search engines index it.`, `{site} serves no WordPress sitemap. That happens when it asks search engines not ...`, or `QUILL could not tell whether {site} asks not to be indexed.`); the sitemap (`{address} lists {n} sitemaps: {names}.`, or `{site} did not serve {address}...`); missed schedules (`Missed schedule: {title}`, `{title} was due on {date} and is still waiting. WordPress publishes on a visit through WP-Cron; Approve and Schedule on its row in Posts or Pages publishes it now.`, or `Nothing scheduled is overdue.`); the certificate (`{site}'s certificate is good until {date}, {n} days from now.`, `{site}'s certificate expired {n} days ago.`, `{site} is connected over plain HTTP, so there is no certificate to read.`, or `QUILL's connection to {site} checked its certificate, which is valid today. Its expiry date was not handed over, so no warning can be given ahead of time.`); and editing locks (`Being edited: {title}`, `{person} has {title} open in WordPress's editor now. ...`, `Changed in the last 15 minutes: {title}`, or `No one is seen editing a post or page now.`). Each detail ends with ` Where this comes from: {source}`.
- F1 on the node: "Search visibility, the sitemap, missed schedules, the certificate and who is editing, each with where QUILL's answer comes from."
- F1 on a row: "One upkeep check, ending with where its answer comes from."
- Context menu: Read in Full (default), Open Where It Is Checked, Show Only and Hide, Properties....
- Code: workbench_upkeep.py, workbench_sweep_places.py.
- Review notes:
  - Strong: every row says how it knows. The certificate warning inside 30 days is the kind of thing a site owner never sees until it is too late.
  - A missed schedule's detail says `Approve and Schedule on its row in Posts or Pages publishes it now.`, but that command is not on the upkeep row; you have to find the post again elsewhere.

### Open Where It Is Checked

- How to reach it: context-menu label "Open Where It Is Checked" on an upkeep row.
- What it does: opens the row's page or wp-admin screen (for visibility, Settings > Reading) in the browser. Nothing is spoken. A row with no link of its own (the certificate, for example) opens the site's home page instead, silently; only when the site's address is unknown too does it say `This has no address on the site yet.`
- Review notes:
  - On rows without their own link, "Open Where It Is Checked" opening the home page is a silent wrong answer.
  - Same command id as "Open on the Site" (Shift+Enter) elsewhere, under another label; Shift+Enter does the same here, which is not said.

### Content Audit and Media > Housekeeping

- How to reach them: Sites > site > Content Audit; Sites > site > Media > Housekeeping.
- What the lists show: columns problem, status. Content Audit: "Pages nobody links to, pages not changed in a year, duplicate titles and text, very long or short pages, hard reading, headings that skip a level." (node F1). Housekeeping: "Files used nowhere, files uploaded twice, very large files, video without captions, audio without a transcript; usage shows before Move to Trash." (node F1).
- F1 on a row: "Something the audit found. Enter reads it; Show Where It Is Used comes before Move to Trash."
- Context menu: Read in Full (default), Show Where It Is Used, Move to Trash..., Open on the Site, Show Only and Hide, Properties....
- Code: workbench_sweep.py, workbench_sweep_places.py, wordpress_workbench_sweep.py.

### Show Where It Is Used

- What opens: a report window titled `Where {title} Is Used`, one line per post or page, `{place} uses it` (or `links to it`), or `Nothing in the posts and pages read uses it.` F1: "Each post or page that uses or links to it, one a line."
- Keyless: "Read before tidying up, a few times a year (rule 9)."

### Move to Trash... (audit finding)

- What opens: a preview titled `Move {title} to the Trash`, button "Move to Trash". Summary `Move {title} on {site} to the Trash, where Restore brings it back.`; for media, `Move {title} on {site} to the Trash. WordPress keeps media in a Trash only where the site turns that on; where it does not, nothing is deleted and QUILL says so.` Lines: where it is used, as above.
- Announced after: `Moved {title} to the Trash on {site}. Restore from Trash brings it back.` For media on a site without a media Trash: `{site} keeps no Trash for media, so {title} was not deleted. Delete Permanently on its row in Media does that, after you confirm.`
- Undo: none recorded; Restore from Trash on the item's own row (in its Trash node) brings it back.
- Without permission: needs `delete_posts`, tier Organize.
- Keyless: "Tidying after an audit is occasional, and previewed (rule 9)."
- Review notes:
  - Ctrl+Z does not undo it, although the item is only in the Trash and every other Trash move in the Workbench is undoable. Ctrl+Z here undoes the change before it.
  - Good that usage is shown in the preview itself, not only on request.

### The Redirects node and its 404 Log

- How to reach them: Sites > site > Redirects; Redirects > 404 Log.
- What the lists show: Redirects: columns source, target, code, hits, state, from the Redirection plugin's `redirection/v1` routes. 404 Log: columns address, when, from.
- F1 on Redirects: "The Redirection plugin's redirects: add with Ctrl+N, change, test, turn off." On 404 Log: "Addresses visitors asked for that were not found; redirect any of them." Row F1: "One redirect: from, to, its code and hits. Test an Address follows it." and "An address that was not found. Redirect This Address sends it somewhere."
- Redirect row menu: Read in Full (default), Test an Address..., Add Redirect..., Change Redirect..., Turn On or Off, Delete Redirect..., Open on the Site, Show Only and Hide, Properties.... 404 row menu: Read in Full (default), Redirect This Address..., Test an Address..., Show Only and Hide, Properties....
- Without the plugin: `{site} does not have the Redirection plugin's REST namespace, so QUILL cannot change its redirects. Administration Areas says where they are kept.`
- Code: workbench_redirects.py, workbench_sweep_places.py, wordpress_workbench_sweep.py.

### Add Redirect..., Redirect This Address... and Change Redirect...

- How to reach them: Ctrl+N (New Here) on Redirects, or the context-menu labels.
- What opens, in order, each its own dialog titled "Add Redirect", "Redirect This Address" or "Change Redirect": text box "Old address, from this site (such as /old-page/):" (help "The address visitors arrive at. A path on this site."); text box "New address it leads to:" (help "Where visitors are sent instead: a path on this site or a full address."); list "Kind of redirect:" with `301, moved for good`, `302, found elsewhere for now`, `307, for now`, `308, for good` (help "301 tells search engines the move is for good; 302 and 307 are for now."); when the plugin has more than one group, list "Group to keep it in:" (help "The Redirection plugin keeps every redirect in a group. Redirections is the usual one."); then a preview titled "Redirect Preview", button "Save Redirect".
- Preview wording: summary `On {site}: add a redirect.` or `On {site}: change this redirect.`; lines `From: {old}`, `To: {new}`, `Kind: {code}`.
- Announced after: `Saved on {site}: {old} now leads to {new}.` No group: `The Redirection plugin on {site} has no group to keep a redirect in. Add one under Tools, Redirection, Groups, then try again.`
- Undo: none recorded.
- Without permission: needs `manage_options`, tier Write.
- Keyless: Add, "Ctrl+N (New Here) on Redirects reaches it; no chord of its own."; Change, "Redirects change rarely (rule 9)."; Redirect This Address, "Reviewing the 404 log is a monthly job (rule 9)."
- Review notes:
  - None of the three prompts has an access key (no `&` in "Old address...", "New address it leads to:", "Kind of redirect:", "Group to keep it in:"), unlike every other Workbench dialog.
  - A redirect write is not in Change History: Ctrl+Z after saving undoes something else.
  - "Kind: 301" in the preview drops the words the list used ("moved for good").

### Turn On or Off and Delete Redirect...

- What opens: a Yes/No message box. Toggle: title and button "Turn Off" or "Turn On", `{Turn Off or Turn On} the redirect from {source} on {site}?`. Delete: title and button "Delete Redirect", `Delete the redirect from {source} to {target} on {site}? The Redirection plugin keeps no Trash, so it is gone for good.`
- Announced after: `The redirect from {source} is off.` (or on); `Deleted the redirect from {source} on {site}.`
- Undo: none.
- Keyless: toggle "Redirects are turned off rarely (rule 9)."; delete "A destructive, rare job: never a bare key (rule 4)."
- Review notes:
  - Delete Redirect's row help says "Gone for good, after you confirm by name", but it is an ordinary Yes/No box; nothing is typed, unlike Delete Permanently elsewhere.
  - "Turn On or Off" does not say which it will do.

### Test an Address...

- What opens: dialog "Test an Address", text box "Address on this site to follow:" (no access key), prefilled from the row; help "QUILL follows the redirects it read from this site. Nothing is sent." Then a report titled "Test an Address", hop by hop.
- Keyless: "Asked when a link is reported broken, now and then (rule 9)."
- Review notes:
  - Useful and safe. The help's "Nothing is sent" is true of the test; the first run does read every redirect from the site.

### Space used

- Where: the directory sizes in Site Health > Information (above). There is no space node or upkeep row for it; the editor's Tools > WordPress > Manage > Space Used is the other place.
- Review notes:
  - wordpress.md marks Space Used in Site Check "in progress"; in the Workbench it is a set of Information rows, readable only by an administrator.

## Snapshots and moving sites

These are the commands that copy a whole site, or part of one, somewhere else: to a folder on this computer (Take a Snapshot), back onto the site (Put Back from a Snapshot), to another connected site (Copy to Site), side by side with another site (Compare Sites), and to or from a WordPress export file (Tools > WXR Files). All of them run their network work in the background (the window's two-worker task pool, shared with list loading) and say one sentence when done. Snapshot, Put Back, Compare, Copy and both WXR commands are window-menu commands, not row actions, except Copy to Site, which is also on several row menus. Every finding below was read from the code on 2026-11-14; nothing here has been tried against a live site.

### Take a Snapshot

- How to reach it: Site menu, Take a Snapshot (Alt+S, N); chord Ctrl+Alt+S. Not on any context menu.
- Which site: the site of the selected node, otherwise the current site. With no site at all it says "Connect a site first: File > WordPress > Connect a Site, in the editor."
- What opens: a chooser titled "Take a Snapshot".
  - Tab order: list labelled "Save:" (access key S), then OK (the default button, no access key), then Cancel.
  - Choices: "Everything but the media files" (selected first) and "Everything, with the media files too".
  - Enter, double-click or OK takes the selected choice.
  - What is saved either way: every post, page, category, tag, menu, menu item, synced pattern, media record and the settings `wp/v2/settings` gives. The second choice also downloads each media file into a "media files" folder.
- Where it goes: the Workbench data folder, then `wordpress_snapshots`, then the site's profile id (for example `wp-1a2b3c4d5e6f`), then a folder named for the time, such as `2026-11-14 101500`. It holds one JSON file per part plus `snapshot.json`, which records what was taken, what the site refused, and what is never taken.
- Preview or confirmation: none. Nothing is written to the site, so that is reasonable.
- Announced after: "Snapshot of {site} saved: {counts}. In {full folder path}. Left out: {left-out list joined by semicolons}."
  - Counts look like "12 posts, 4 pages, 3 categories, 10 tags, 2 menus, 15 menu items, 1 patterns, 40 media, 31 settings". The count words never go singular.
  - The left-out list always includes "people, passwords, plugins, themes, revisions and comments: never taken". Without media files it also includes "the media files themselves (not asked for; records kept)". It adds a line for each part the site refused ("{part}: the site would not give it ({why})") and for each media file that failed.
- Failure: a part the site refuses is recorded and named in the spoken sentence, not treated as empty. Any other error (a disk error, say) speaks the error text, or "That did not work."
- Undo: not needed; nothing changed on the site.
- F1: the chooser's help is "Every post, page, pattern, term, menu, setting and media record of {site}, to this computer. The media files themselves only if you choose; people, passwords, plugins, themes, revisions and comments are never saved." On the list it adds "Press Enter to choose the selected one."
- Cancel: Escape or Cancel closes the chooser. Nothing is said.
- Without permission: no Workbench Access or role check, which is right for a read. What the account cannot read goes into the left-out list instead.
- Code: workbench_snapshot.py (take_snapshot, snapshot_left_out, snapshot_counts_words), wordpress_workbench_bold.py (do_snapshot), wordpress_dialogs.py (ask_choice).
- Review notes:
  - Review note: the completion sentence is very long to hear. It reads out a full Windows path with a profile id, then the whole left-out list. A screen-reader user gets a 30-plus-word path read character-ish, and no way to act on it. Offer "Open the Snapshot Folder" or a report instead.
  - Review note: custom post types are not taken. Only `wp/v2/posts` and `wp/v2/pages` are read, so Events, Products, Podcast episodes and the rest are left out. So are templates, template parts, global styles, block-theme Navigation menus (`wp_navigation`) and form-plugin data. None of these appears in the left-out list, which names only "people, passwords, plugins, themes, revisions and comments". The person is told a snapshot is complete when it is not.
  - Review note: the menu help says "Everything but media, saved here." That is wrong both ways: media records are always saved, and much more than media is left out (see the note above).
  - Review note: "1 patterns", "1 media" and the like: the count words are never made singular.
  - Review note: there is no way to list, open, rename or delete snapshots from the Workbench. They pile up, with media files possibly large, in the data folder.
  - Review note: Ctrl+Alt+S (take a snapshot) is one modifier away from Ctrl+Alt+Shift+S (Put Back, which writes to the site) and from Ctrl+Shift+S (mark as Spam). Put Back is protected by a picker and a preview, so the risk is a startled moment rather than data loss. On keyboards where Ctrl+Alt is AltGr, these chords may also collide with typing in the filter box.

### Put Back from a Snapshot

- How to reach it: Site menu, Put Back from a Snapshot (Alt+S, K); chord Ctrl+Alt+Shift+S. Not on any context menu.
- Before anything opens:
  - No site: "Connect a site first: File > WordPress > Connect a Site, in the editor."
  - No snapshot of this site: "There is no snapshot of {site} yet: Site > Take a Snapshot makes one."
- What opens, step 1: a chooser titled "Put Back from a Snapshot".
  - List labelled "Snapshot:" (access key S), then OK (default), then Cancel.
  - Rows are the snapshot folder names, newest first, such as "2026-11-14 101500".
  - Help: "The snapshots of this site, newest first. The next step previews exactly what would be put back."
- Step 2, only when the snapshot was taken on the Practice Site and this site is real: the practice crossing question, titled "Put Back from a Snapshot: from the Practice Site to a Real Site".
  - Wording: "Put Back from a Snapshot would send what is on {practice}, the practice site on this computer, to {real}: a real site that other people can see. Work on the practice site never goes anywhere else unless you choose it here. Send it to {real}?"
  - Buttons: "Send to {site}", and "Cancel", which is the default.
- Step 3: the site is read in the background ("comparing with the snapshot"). If nothing differs: "{site} already matches the snapshot of {name}."
- Step 4: a preview titled "Put Back {snapshot name}".
  - Tab order: "Summary:" (read-only multi-line text), then "Each change:" (a list box with the first line selected), then "Put Back" (the default button), then Cancel.
  - Summary: "{n} changes on {site}. Posts, pages, patterns, categories and tags changed since the snapshot are set back to it; WordPress keeps a revision of each post and page it changes, so this can be undone from Revisions. Ones deleted since are made again as drafts, at new addresses. Menus, settings, people, plugins and media files are not put back."
  - Each line is either "Put back the {kind} {title}: it changed since the snapshot." or "Make the {kind} {title} again, as a draft: it was deleted."
- Announced after: "Put back {done} of {total} on {site}." If any line failed, a report titled "Put Back from a Snapshot" opens. It has one line per item: "Put back: {kind} {title}.", "Made again: {kind} {title}." or "Not put back: {kind} {title}: {why}". The list then reloads.
- Failure while planning: if the site refuses to list any one of the five kinds, the whole plan stops and only the site's error sentence is spoken. Nothing is previewed.
- Undo: Ctrl+Z says "Put back the snapshot {name}. This cannot be undone." The change is recorded with no undo, even though the preview says the change "can be undone from Revisions" (that means one post at a time, in wp-admin).
- F1: the chooser help quoted above. The preview dialog's help is "What the change will do, before anything is sent. The button names the change; Cancel sends nothing."
- Cancel: Escape at any step sends nothing and says nothing.
- Without permission: not found in code. The command never calls `write_refusal`, and `refusal_for` returns nothing for a command that is not a row action. Workbench Access "Read Only", Safe Mode and View As Role therefore do not stop it. Only WordPress itself refuses, line by line, and the report shows "Not put back: ...".
- Code: workbench_snapshot.py (restore_plan, run_restore, RESTORE_TERMS, snapshot_source), wordpress_workbench_bold.py (do_restore_snapshot), wordpress_workbench_bold_practice.py (practice_crossing_ok), workbench_practice.py (crossing_warning), wordpress_workbench_dialogs.py (PreviewDialog).
- Review notes:
  - Review note (critical): Put Back writes to the site with no Workbench Access, Safe Mode or View As Role check. A person who set a site to Read Only, or who is in Safe Mode, can still overwrite posts and pages from this menu.
  - Review note (critical): it puts back far less than "set back to it" promises. For posts, pages and patterns only the title, content and excerpt are compared and sent; for terms, only the name and description. Status, slug, date, author, categories, tags, featured image, parent and menu order are never compared or restored. A post unpublished since the snapshot stays unpublished, and the preview does not say so.
  - Review note (critical): an item deleted since the snapshot is "made again as a draft, at a new address" with only title, content and excerpt. Its categories, tags, featured image and parent are lost. A deleted category made again gets a new id, and no post is re-filed under it.
  - Review note: items moved to the Trash since the snapshot are probably treated as deleted, because WordPress's `status=any` leaves out trashed items. Put Back then makes a duplicate draft while the original still sits in the Trash. A Restore from Trash would have been the right move. Worth checking on the live site.
  - Review note: the chooser shows only a timestamp. There are no counts, no "with media files", no "taken on the practice site", and no way to read what a snapshot holds before choosing it.
  - Review note: it is all or nothing. The preview is a read-only list, with no check boxes to put back only some items, unlike Split in By Name, which uses check boxes.
  - Review note: the preview's default button is "Put Back", so Enter in the list sends the change. The confirmation dialogs elsewhere (crossing, Reset, Check Every Link) default to Cancel. Two different safety habits sit in the same window.
  - Review note: the plan reads every post and page of the site (up to 1000 pages of 100) with no progress or count. A big site sits silent for a long time.

### Copy to Site

- How to reach it:
  - Item menu, Copy to Site (Alt+I, O); chord Ctrl+Shift+Y.
  - Context menu "Copy to Site..." on item (post, page, custom item), media, term, pattern, menu, form and Gravity Forms form rows.
  - Row help: "To another of your sites, after a preview. Ctrl+Shift+Y."
- Before anything opens:
  - Nothing selected: "Select what to copy first."
  - Only one site connected: "Connect a second site first: File > WordPress > Connect a Site."
- What opens, step 1: a chooser titled "Copy to Site".
  - List labelled "Site:" (access key S), then OK (default), then Cancel.
  - Rows are every other connected site (not limited by the Across Sites scope).
  - Help: "Which of your other connected sites."
- Step 2, only from the Practice Site to a real site: the crossing question, titled "Copy to Site: from the Practice Site to a Real Site". Wording as under Put Back, with "Copy to Site" as the action. Buttons "Send to {site}" and "Cancel" (the default).
- Step 3: the target's permission is checked for the first selected row's kind (see Without permission).
- Step 4: the plan is read in the background ("planning the copy to {target}"), then a preview titled "Copy from {source} to {target}" opens.
  - Summary: "Copy from {source} to {target}: {n} made, {n} replaced, {n} skipped, and {n} pictures uploaded. New items are drafts; a replaced item keeps its status on {target}. Links to {source} are pointed at {target}."
  - Each change list:
    - one line per item: "Make {kind} {title}." or "Replace {kind} {title}: {why}" or "Skip ...";
    - then "Upload the picture {url}" for each picture;
    - then "Left out: {line}", always including "Not copied: comments, revisions, custom fields, publishing (a new item is a draft, a private one included), sticky and template choices, and taxonomies other than categories and tags." It adds a line for private items and for plugin blocks the target may lack.
  - Button: "Copy" (the default), and Cancel.
- Announced after:
  - Success: "Copied to {target}; new items are drafts there."
  - Partial: "Copied to {target}, except {n}; the report says which.", then a report titled "Copy to {target}" with one outcome line per item, the failed pictures, and the left-out section.
- Undo: Ctrl+Z says "Copied {n} from {source} to {target}. This cannot be undone." No undo is recorded. A replaced item on the target can be recovered only from its WordPress revisions.
- F1: the context-menu row help above. The preview dialog's generic help.
- Cancel: at any step, sends nothing, says nothing.
- Without permission: `write_refusal` on the target, using the first selected row's kind. You hear one of:
  - "Workbench access on {site} is Read Only. Site > Workbench Access changes it." (or Organize);
  - "Safe Mode is on, so the Workbench only reads.";
  - "You are viewing {site} as {Role}, which only reads. Site > View As Role ends it.";
  - the role sentence: "{What} needs the {Role} role or higher. You are {a role} on {site}."
- Code: workbench_site_copy.py (plan_copy, run_copy, CopyPlan.summary, CopyLine.sentence), workbench_site_copy_order.py (terms and files first), workbench_carry.py (COPY_LEFT_OUT, copy_left_out), wordpress_workbench_bold.py (do_copy_to_site).
- Review notes:
  - Review note: the success sentence says "new items are drafts there", even when every line was a Replace. A replaced published page goes live at once, and the spoken outcome hides that. Say how many were replaced live.
  - Review note: the permission check uses only the first selected row's kind. A mixed selection (a post plus a menu) is checked against post rights only.
  - Review note: "Connect a second site first: File > WordPress > Connect a Site." The Workbench's own File menu has no WordPress submenu. The path exists only in the editor, and unlike `_site_now`'s sentence this one does not say "in the editor".
  - Review note: there is no undo, and this is a write to another site. Ctrl+Z also cannot reach any earlier undoable change while this entry is newest, because `do_undo` only looks at the newest entry (see the Needs My Attention section's note on the undo stack).
  - Review note: the module docstring says custom terms travel; COPY_LEFT_OUT says "taxonomies other than categories and tags" do not. The preview is the one the person hears, so it is probably right, but the two disagree.
  - Review note: "Left out:" lines are mixed into the same "Each change" list as the actions, so arrowing through the plan reads things that will not happen as if they were steps.

### Compare Sites

- How to reach it: Site menu, Compare Sites (Alt+S, I); chord Ctrl+Alt+K. Menu help "What differs from another."
- What opens: the same "Compare Sites" chooser ("Site:" list of every other site, OK default, Cancel; help "Which of your other connected sites."). The first site is the current one.
- Then: background "comparing sites", then a report titled "{site} and {other}".
  - Tab order: "Report:" (read-only text), then "Copy All" (access key A), then Close.
  - One line per difference, in the form "{kind} {slug}: {words}". Examples:
    - "post about-us: titles differ, text differs";
    - "page contact: only on {other}";
    - "post news: publish here, draft there";
    - "category events: descriptions differ".
  - When nothing differs: "Their posts, pages, patterns, categories, tags and menus are the same."
  - Always last: "Not compared: media files, revisions, menu links, settings, people, plugins and themes."
  - Limits are said: "only the first 2000 on {site} compared", and "not compared: {site} said {why}" when a kind could not be read.
- Announced after: nothing spoken; the report opens. That is right under GATE-13, since the dialog title and text are read anyway.
- Undo: nothing to undo.
- F1: "What differs between the two sites, by kind and address (slug), and what is not compared." On the text it adds "Read it line by line; copy any part with Ctrl+C."
- Cancel: Escape at the chooser.
- Without permission: none needed; what cannot be read is said in the report.
- Code: workbench_snapshot.py (compare_sites, COMPARE_KINDS, COMPARE_OMITS), wordpress_workbench_bold.py (do_compare_sites).
- Review notes:
  - Review note: status words are WordPress's raw values ("publish here, future there"), not the plain words used elsewhere ("published", "scheduled").
  - Review note: custom post types are not compared, and the omissions line does not name them.
  - Review note: it is a dead end. Nothing in the report leads to Copy to Site or Make Them the Same for a line, so acting on a difference means finding the item again by hand.
  - Review note: the report is one flat list with no per-kind headings or counts at the top. On a big pair of sites the person must arrow through every line to learn the scale.

### Export Site as WXR

- How to reach it: Tools menu, WXR Files submenu, Export Site as WXR (Alt+T, W, E). Keyless; the written reason (KEYLESS) is "Moving hosts or keeping a copy: a few times a site's life (rule 9)."
- Submenu help: "WordPress export files (WXR), written and read on this computer." Row help: "This site, or part of it, as a WordPress export file any WordPress imports."
- What opens, step 1: a chooser titled "Export Site as WXR", list labelled "Export:" (access key E). The choices:
  - "Everything: posts, pages, patterns, other types, files, menus, comments"
  - "Posts only"
  - "Pages only"
  - "Posts and pages in a date range..."
  - "Posts in one category..."
  - Help: "What of {site} goes in the file. A part takes only the people, terms and files its items use, as WordPress's own exporter does; comments and menus go only with Everything."
- Date range: two text questions in a row, both titled "Export Site as WXR".
  - "From (year-month-day, or blank):" (access key F), then "To (year-month-day, or blank):" (access key T).
  - Help: "A day written as 2026-01-31. Leave From blank to start at the first post, To blank to end today. Both days are included."
  - A bad day says "{text} is not a day written as year-month-day, such as 2026-01-31." and the export stops.
- One category: the categories are read in the background ("reading {site}'s categories"), then a chooser "Category:" with rows like "News (12 posts)". Help: "The posts filed under this category go in the file." With none: "{site} has no categories QUILL can read."
- Then a standard Save dialog titled "Export Site as WXR". The filter is "WordPress export files (*.xml)", and it asks before overwriting. A name with no extension gets ".xml".
- Announced after: "{Wrote sentence} {check sentence}".
  - Example: "Wrote site.xml: 12 post, 3 page, 40 attachment, 2 wp_block, 5 comments, 2 authors, 9 terms. site.xml is a well-formed WXR 1.2 file with 62 items."
  - A report titled "Export Site as WXR" then opens: "{site}: {scope words}.", the same sentence, then "Left out:" with one line per thing. The lines always include "what only WordPress's own exporter carries: custom fields REST does not show, comment, term and user meta, post passwords, and serialised plugin settings".
  - If the check failed, a second sentence: "The file did not pass its check; it is kept so you can look at it."
- Undo: nothing to undo; the file stays.
- F1: the chooser help quoted. The report's help is "What went into the WXR file, the check of it, then what was left out."
- Cancel: any step stops quietly, the Save dialog included.
- Without permission: reads only. Items the account cannot read are named in the left-out list ("{what} that are not published: the account may not read drafts, private or scheduled ones").
- Code: wxr_export.py (export_wxr, Scope, ExportReport), wxr_read.py (validate_wxr), workbench_site_files_actions.py (WXR_SUB, KEYLESS), wordpress_workbench_wxr.py (do_export_wxr).
- Review notes:
  - Review note: the counts are spoken with WordPress post-type slugs and never go plural: "12 post, 40 attachment, 2 wp_block". Use the plain names ("posts", "files", "synced patterns").
  - Review note: the outcome is spoken and then the report opens with the same sentence. The dialog's arrival cuts the speech off, and the person hears it twice. Speak nothing, or open nothing (GATE-13).
  - Review note: one bad date ends the whole export, and From and To are not checked against each other, so From after To gives an empty file. Ask again on the same field instead.
  - Review note: the Save dialog suggests no file name (such as "{site} {date}.xml"), so the person types one every time.
  - Review note: an Everything export writes commenters' emails and IP addresses (`wp:comment_author_email`, `wp:comment_author_IP`) and authors' emails to a plain file. That matches WordPress, but neither the chooser nor the report says the file holds personal data.
  - Review note: no Practice Site crossing guard. That is correct for the export itself, but see Import below.

### Import WXR as Drafts

- How to reach it: Tools menu, WXR Files, Import WXR as Drafts (Alt+T, W, I). Keyless; the reason is "Moving content in happens once per move (rule 9)." Row help: "A WordPress export file from any site, previewed, then made here as drafts."
- What opens, step 1: a standard Open dialog titled "Import WXR as Drafts", with the same .xml filter; the file must exist.
- Step 2: the file is read and matched in the background ("reading {file name}"). With nothing usable: "{file} has nothing {site} can take as a draft."
- Step 3, when authors do not match and there is more than one person on the site: a chooser titled "Import WXR as Drafts".
  - List labelled "Give unmatched authors' items to:" (access key G), with the site's people.
  - Help: "{n} authors in the file have no account on {site} with the same login or email: {first five}."
- Step 4: a preview titled "Import WXR as Drafts".
  - Summary: "Make {n} items from {file} on {site}, all as drafts? Ctrl+Z moves them to the Trash afterwards."
  - Each change: "From {title} ({url}), WXR {version}."; "Author {login} is {person} here." or "Author {login} is not on this site; given to {person}."; "New {category/tag/term}: {name}."; one "{Type}: {title}." per item; "{n} files to download from {hosts} ..."; and "Left out: ..." lines.
  - Button: "Import as Drafts" (the default), and Cancel.
- Step 5, only when the file names attachments: a chooser titled "Files in the Export".
  - List labelled "Files:", with the second choice selected first.
  - Choices: "Download the {n} files from {hosts} and upload them to {site}" and "Skip the files; the text keeps pointing at the old site".
  - Help: "Downloading asks {hosts} for each file by the address the export names, over HTTPS, up to 64 MB each, sending no password. Skipping leaves the pictures where they are."
- Announced after: "Imported {count} of {n} items from {file} into {site} as drafts, with {uploaded} files. Ctrl+Z moves the drafts to the Trash." Then a report titled "Import WXR as Drafts" with every term, file and item line ("Made the category News.", "Uploaded photo.jpg.", "Not made: {title}: {why}", and so on). The list then reloads.
- Undo: Ctrl+Z (when at least one draft was made) speaks "Moved {n} imported drafts to the Trash." It adds "Not moved: ..." for any it could not move, and "The {n} uploaded files and {n} new terms stay; remove them from Media and the term lists if you do not want them."
- F1: the help strings above. The report's help is "What happened to each term, file and item, then what was left out."
- Cancel: Escape at any step, the Files question included, sends nothing.
- Without permission: not found in code. No `write_refusal` is called, so Read Only access, Safe Mode and View As Role do not stop the import; only WordPress refuses, item by item.
- Code: wxr_read.py (read_wxr), wxr_import.py (plan_import, send_import, undo_import, ImportPlan.lines), wordpress_workbench_wxr.py (do_import_wxr, _import_planned, _send_import).
- Review notes:
  - Review note (critical): the import skips Workbench Access, Safe Mode and View As Role, as Put Back does. It can make hundreds of drafts, terms and uploads on a site marked Read Only.
  - Review note: the order of questions is backwards. The person presses "Import as Drafts" and is then asked about files, and Cancel there throws away the yes they just gave. Ask about files before the preview, and show the choice in the preview.
  - Review note: the spoken result always ends "Ctrl+Z moves the drafts to the Trash", even when nothing was made. In that case no undo is recorded, and Ctrl+Z says "... This cannot be undone." The two sentences contradict each other.
  - Review note: no Practice Site guard. A WXR exported from the Practice Site can be imported into a real site with no crossing question, which is the very path the guard exists to stop.
  - Review note: undo leaves the new terms and uploaded files behind. It says so, but the person must then clean up by hand across two lists.

## By Name

By Name is a node under each site (Sites > {site} > By Name) that lists everything on the site by its name or value: terms, custom field values, authors, media, synced patterns, links, blocks and shortcodes, forms and template parts. Each row is one value and where it is used, so a change made from the row reaches every post and page that uses it, after a preview item by item. The lists come from one scan of the site, kept for five minutes. Check Every Link, the newest command, lives on these rows.

### The By Name node and its children

- How to reach it:
  - In the tree: Sites, a site, then By Name; Right Arrow opens the children.
  - No Go chord and no menu row.
  - The By Name node itself has no loader, so selecting it shows an empty list with its help in the details pane.
- Children, in order (each loads "scan:{kind}", columns "Value" and "Used"):
  - Every Term
  - Field Values
  - Authors
  - Media Usage
  - Patterns Used
  - Links
  - Blocks and Shortcodes
  - Forms Used
  - Template Parts
- What each row says: "Value" is the name ("News (category)", "Venue: Main Hall", "Sam", "logo.png", an address); "Used" is "{n} posts" or "{n} places". The detail is "{name}: in {n} places. Used on: {first 20 titles}...".
- A site that refused a list shows a first row "Not read on {site}". Its detail: "On {site}, QUILL could not read {routes and reasons}. What is listed from {site} may be incomplete, and nothing there is counted as unused or missing."
- F1 (node help):
  - By Name: "Everything on this site by name: terms, fields, authors, media, links, blocks."
  - Every Term: "Every term of every taxonomy, with how many posts each has."
  - Field Values: "Every custom field value, and how many items have it."
  - Authors: "Every author, with what they have written by status."
  - Media Usage: "Every file in the library, and where it is used."
  - Patterns Used: "Synced patterns, and the pages that use them."
  - Links: "Every link in the content, and the pages it is on. Check Every Link, on a row's context menu, checks them all in the background."
  - Blocks and Shortcodes: "Blocks and shortcodes, and the pages that use them."
  - Forms Used: "Forms placed in pages, and where."
  - Template Parts: "A block theme's template parts, and the templates that place them."
- F1 (row help, kind "value"): "One value, wherever it is used. Enter lists where. Under Links, Check Every Link checks the whole site's links in the background."
- Code: workbench_places.py (BY_NAME_NODES, places_rows "value"), workbench_across.py (SITE_KINDS, scan_site, kind_rows), wordpress_workbench_across.py (site_scan, scan_rows), workbench_node_help.py.
- Review notes:
  - Review note: F5 does not re-read. The scan is kept for five minutes (`_SCAN_SECONDS = 300`), and `refresh` does not clear it; only a By Name change does. After editing on the site, F5 shows the old answer, silently.
  - Review note: the scan reads at most 10 pages of 100 (1000 posts and 1000 pages, and the same for terms, media and people), and a cap is never said. On a bigger site, Rename Everywhere and Replace Everywhere change "everywhere" except the items past 1000, and the preview looks complete. The unread note covers refusals, not truncation.
  - Review note: the By Name node's F1 lists "terms, fields, authors, media, links, blocks" and leaves out patterns, forms and template parts, which are three of its nine children.
  - Review note: only posts and pages are scanned (`wp/v2/posts`, `wp/v2/pages`). Custom types that use a term, field or link are not counted, so a Rename can leave them behind. Check Every Link, by contrast, includes custom types.

### The value row's context menu

- How to reach it: Applications key or Shift+F10 on a row.
- The menu has eight actions plus Properties, so it splits:
  - Top: Where It Is Used, Rename Everywhere..., Split..., Merge Into..., Reassign..., Replace Everywhere...
  - Then "More", which holds Find Items Missing This Field and Check Every Link...
  - Then the window's own "Show Only" and "Hide" cell-filter submenus.
  - Last: Properties...
- Every action is offered on every By Name kind. An action a kind does not allow stays enabled and, when chosen, speaks the reason from the scope matrix. Examples:
  - Rename on a Links row: "Replace changes the address on every page."
  - Merge on an author: "WordPress joins two people only when one is deleted, with reassignment, in People."
- Keyless: every value command has a written reason in KEYLESS (workbench_places.py):
  - Where It Is Used: "The rows' Enter, so it needs no chord of its own."
  - Rename Everywhere: "Renaming everywhere is occasional and previewed (rule 9)."
  - Split: "Splitting a term or value is occasional and previewed (rule 9)."
  - Merge Into: "Merging is occasional and previewed (rule 9)."
  - Reassign: "Reassigning is occasional and previewed (rule 9)."
  - Replace Everywhere: "Replacing everywhere is occasional and previewed (rule 9)."
  - Find Items Missing This Field: "A check made now and then, on field rows only (rule 9)."
  - Check Every Link: "A whole-site run after a reorganisation, rarely (rule 9)." (in workbench_gap_actions.py)
- Code: workbench_places.py, workbench_gap_actions.py (CHECK_LINKS), quill/core/workbench/actions.py (MENU_TOP_LIMIT 8, menu_for), workbench_frame_actions.py (_popup, can_run), workbench_scope_matrix.py (by_name_support).
- Review notes:
  - Review note (critical for discoverability): Check Every Link, the only command built for Links rows, is buried under More. Meanwhile Rename, Split, Merge and Reassign, which all refuse on a Links row, sit on top. On every other kind, Check Every Link sits under More and refuses. The menu does not adapt to the kind it is on.
  - Review note: refused actions are enabled rather than disabled or hidden, so a screen-reader user tries each one to learn which work. The scope matrix already knows (`by_name_support`). Use it in `supports` so they read "unavailable", or leave them out.

### Where It Is Used (Enter)

- How to reach it: Enter on a value row (the default), or the context menu. Row help: "Each page that uses it."
- What opens: a report titled "Where {value} Is Used".
  - Text: one title per line, or "Nowhere in the posts and pages read."
  - Buttons: Copy All, Close.
- F1: "Each post or page that uses it, one a line."
- Review note: it is a read-only text report, not a list, so there is no way to open one of those posts from it. Compare the Broken Links window, which has "Open in Editor".

### Rename Everywhere

- Allowed on: terms (name and slug), field values, template parts (title). Refused on the rest with the matrix reason.
- Tier and permission: WRITE. Workbench Access must be Full. Terms need manage_categories, template parts edit_theme_options, everything else edit_others_posts. A refusal speaks the access or role sentence.
- What opens, by kind:
  - Terms: "New name:" (access key N), filled with the current name; then "New slug (empty keeps it):" (access key S). Both titled "Rename Everywhere".
  - Template parts: "New title:".
  - Fields: "New value for {key}:".
  - An empty answer, or an unchanged one, stops quietly.
- Preview: titled "Rename Everywhere...", with the ellipsis in the title.
  - Summary: "{value} is renamed. {n} changes on {site}." plus the unread note if any.
  - Lines: "{site}: {title}: {words}", up to 200, then "and {n} more", then any "Not read on ..." lines.
  - Button: "Rename Everywhere" (the default), and Cancel.
- Nothing to change: "Nothing the scan read uses {value}."
- Announced after: "Rename Everywhere: {good} of {n} changed." If any failed: " {n} not: {first failure}." and a report "Rename Everywhere: Each Item" with "Done. ..." and "Not done. ..." lines. Items changed on the site since the scan are left alone and reported (the conflict stamp).
- Undo: Ctrl+Z sends each item's "before" back: "Put {n} back as they were."
- Cancel: any step, nothing sent.
- Code: workbench_by_name.py (plan_term_rename, plan_part_rename, plan_field, apply_edits, undo_edits, outcome_report), wordpress_workbench_by_name.py (do_rename_value, _bn_send).
- Review note: the preview's title keeps the menu's ellipsis ("Rename Everywhere..."). Every other preview in the window has a plain title. It is read as the dialog title on every open.

### Split

- Allowed on: terms (chosen items move to a new term), field values (chosen items get a new value), authors (chosen items go to another person).
- What opens:
  - A check-box list titled "Split", labelled "Items that move".
    - The group's access key is stripped (`prompt.replace("&", "")`).
    - Help: "Check each item that moves. The ones left unchecked stay as they are. Space checks or unchecks."
  - Then, by kind: terms get "New term:"; fields get "New value for {key}:"; authors get a chooser "Give them to:" with help "The new author."
- Preview: "Split...". Summary "{n} items move to the new term {name}." (or "{n} items change." or "{n} items go to {person}."). Button "Split".
- Announced after: "Split: {good} of {n} changed."
- Undo: Ctrl+Z puts items back, and for terms deletes the new term: "Put {n} back as they were. {name} was deleted again."
- Review notes:
  - Review note: pressing OK with nothing checked does nothing and says nothing (`if not picked: return None`). Say "Nothing checked, so nothing moves."
  - Review note: the check-box group has no access key. It is the only control, so that is minor.

### Merge Into

- Allowed on: terms (every item moves to another term, then this term is deleted for good), field values (every item takes another value already in use).
- What opens: a chooser titled "Merge Into", labelled "Merge into:".
  - For terms, the rows are the other terms of the same taxonomy. Help: "The term every item moves to. This term is then deleted."
  - For fields, the rows are the other values of that field. Help: "The value every item with this one takes."
- Preview: "Merge Into...". Button "Merge Into".
  - Terms summary: "Every item moves to {target}; this term is deleted. {n} changes on {site}. This cannot be undone."
- Announced after: "Merge Into: {good} of {n} changed. The old term was deleted." or "... The old term was kept, because not every item moved."
- Undo: terms, none; Ctrl+Z says "{said} This cannot be undone." Fields are undoable.
- Review notes:
  - Review note: tier mismatch. This row is Tier WRITE (`merge_value`), while Merge Into on a term row is Tier DESTRUCTIVE (workbench_actions.py), for the same irreversible term deletion. Under Organize access both are refused, but the tiers should agree, and DESTRUCTIVE elsewhere means confirm by name.
  - Review note: the chooser lists every other term with no post counts, so the person cannot tell "News (300 posts)" from "news (1 post)". The By Name row itself shows the counts.

### Reassign

- Allowed on: terms (items move to another existing term, which stays) and authors (every item goes to another person).
- What opens: a chooser titled "Reassign". Terms: "Move items to:", help "The term every item moves to. This term stays, with no items." Authors: "Give everything to:", help "The new author."
- Preview "Reassign...", summary "Every item moves to {target}." or "Everything goes to {person}.", button "Reassign".
- Announced after: "Reassign: {good} of {n} changed." Undo: Ctrl+Z puts them back.

### Replace Everywhere

- Allowed on: media (another library file), synced patterns (another pattern), links (another address), blocks (shortcodes only), forms (another form by number).
- What opens, titled "Replace Everywhere":
  - Media and patterns: a chooser "Use instead:", help "What every page uses instead."
  - Links: "New address:", help "The address every link to this one gets instead."
  - Blocks: "New shortcode name:", help "Another shortcode's name, such as gallery."
  - Forms: "Other form, such as Form 7:", help "The form every page places instead."
- If the plan finds nothing to change, its reason is spoken.
- Preview "Replace Everywhere...", summary "Every page using {key} uses {new}. {n} changes on {site}.", button "Replace Everywhere".
- Announced after: "Replace Everywhere: {good} of {n} changed." Undo: Ctrl+Z puts every item's content back.
- Review note: the media chooser lists bare file names from the library ("IMG_2041.jpg"), with no title or alt text. For a screen-reader user choosing a replacement picture by file name alone is guesswork.

### Find Items Missing This Field

- How to reach it: the context menu's More submenu, on a Field Values row. Elsewhere it says "Find Items Missing This Field works on a row of By Name > Field Values."
- What opens: a report titled "Items Missing {key}", listing one title per line, or "Every post and page read has a value for {key}.", plus the unread note.
- F1: "Each post or page with no value for the field, one a line."
- Review note: like Where It Is Used, it is a dead-end text report with no Open.

### Check Every Link

State on 2026-11-14 (code checked at the end of this pass): the row action, the handler, the core module, the status-bar cell, the node and row help, and two tests exist. Not yet present: an entry in the engineering log (docs/design/wordpress.md has no Check Every Link entry), any user guide, keyboard reference or command catalogue text (nothing under docs/ names it), and a live-site run. Those parts are in progress.

- How to reach it:
  - Context menu on a By Name > Links row, under More: "Check Every Link...". Applications key, then down to More, Right Arrow, then down past Find Items Missing This Field.
  - Help: "Every link in every published post, page and item on this site, checked by the site in the background, with a running count in the status bar. Choose it again, or press Enter on the status bar's Link check, to stop. The broken links are listed with what holds each."
  - Keyless (reason quoted above). Tier READ, no capability needed.
- On the wrong row: "Check Every Link works on a row of By Name > Links."
- What opens: a Yes/Cancel question titled "Check Every Link".
  - Wording: "Check every link in {site}'s published posts, pages and items? The site fetches each address itself, which can take some minutes; it runs in the background, the status bar counts, and choosing this again stops it."
  - Buttons: "Check", and "Cancel" (the default).
- While it runs: the status bar's "Link check" cell.
  - Reach it with F6 from the details pane, or Shift+F6 from the tree.
  - First "Reading {site}'s published items", then "{checked} of {total} links on {site}, {broken} broken. Enter stops". It repaints every fifth link.
  - Cell help: "Check Every Link's count while it runs. Enter stops it; what it found is kept."
  - Its context menu: "Stop Checking Links".
  - When no check runs the cell is empty.
- Stopping: choose Check Every Link again on any value row, press Enter on the cell, or use its menu.
  - Spoken: "Stopping the link check; what it found so far is kept."
  - If none runs: "No link check is running."
- Announced after:
  - No link-check route on the site: "{site} does not offer WordPress's link-check route, so its links cannot be checked from here. Check This Page still works."
  - Otherwise one of:
    - "{site}'s {n} published items link to no other pages."
    - "All {n} links in {site}'s {n} published items work."
    - "{broken} of {n} links on {site} lead nowhere."
    - "Stopped after {checked} of {n} links on {site}; {broken} links lead nowhere so far."
- Then, if anything is broken: a window titled "Broken Links on {site}".
  - "Broken links:" list. Each row: "{url}, in {title} ({kind}), ... and {n} more: {why}."
  - "Details:" text: the url, why, then each holder "{title} ({kind}): {link}".
  - Buttons: "Open in Editor" (access key O; help "Open the first item that holds this link in the editor, to fix it.") and Close.
- Undo: nothing changes on the site.
- F1: the node and row help quoted under By Name, and the cell help.
- Cancel: Cancel on the question starts nothing.
- Without permission: item types the account cannot read (401, 403 or 404) are skipped silently.
- Code: workbench_link_check.py (has_link_route, collect_links, check_links, outcome, BrokenLink.spoken), workbench_gap_actions.py (CHECK_LINKS, KEYLESS), wordpress_workbench_gaps.py (do_check_every_link, stop_link_check, link_check_status, _show_broken), wordpress_workbench_window_status.py (the Link check cell), link_targets.py (read_target).
- Review notes:
  - Review note (critical for discoverability): see the menu note above. The command is under More, and only one of nine By Name kinds can use it. A Links node command, or a node context-menu row, would be easier to find than a row command that ignores its row.
  - Review note: the label never changes. While a check runs, the same "Check Every Link..." row, with its ellipsis promising a dialog, silently means Stop. Show "Stop Checking Links" while one runs.
  - Review note: one check at a time across all sites, and choosing it on another site's Links row stops the running check instead of starting one. The person hears "Stopping the link check..." when they meant "check this site".
  - Review note: skipped types are silent. A custom type the account cannot read is dropped with no line, so "All 300 links ... work" can be said for a partial read. By Name's unread rows exist for exactly this.
  - Review note: the result is spoken and then the Broken Links window opens with the same sentence as its purpose. The window title interrupts the speech (GATE-13, said twice).
  - Review note: "Open in Editor" opens only the first item that holds the link. A link on 22 pages needs 22 trips, with no way to choose which holder; the details pane lists them but they cannot be opened. Replace Everywhere is the bulk fix and is not offered from this window.
  - Review note: the check runs on the window's two-worker pool, which list loading also uses. A run that takes minutes takes one worker, and with any other long job (a Practice Site start, a big Put Back plan) no node in the window loads until one finishes. See the Practice Site note.
  - Review note: it competes with Needs My Attention > Broken Links (a sample of the first 40 links). The two are not linked: the Broken Links node does not offer "check everything", and this command's results do not feed that node.

## Across Sites

Across Sites puts the same name side by side on every connected site, or on a Site Set: tags and categories, plugins, themes, people, settings, menus, synced patterns and application passwords, plus the Fleet, which is every site in one list. Each row says where the copies differ and which sites lack it, and its context menu can make them the same, promote a plugin to a multisite network, revoke a leaked password everywhere, compare global styles, or install a missing plugin. Site Sets and Across Sites Scope decide which sites are included. The Calendar is a separate account-level node that also spans every site, so it is covered here too.

### The Across Sites node

- How to reach it:
  - Go menu, Across Sites (Alt+G, O); chord Ctrl+0. Go help: "The same name on every site."
  - It is an account-level node in the tree.
  - The node has no loader: it shows an empty list with its help in the details pane, and Right Arrow opens its children.
- Children (each loads "across:{kind}"; columns Name, Sites, Versions, Missing):
  - Tags and Categories
  - Plugins
  - Themes
  - People
  - Settings
  - Menus
  - Synced Patterns
  - Application Passwords
  - Fleet (columns Site, State, Health, Backups, Security, Updates)
- Each row:
  - Name: the name, or the email for people.
  - Sites: how many sites have it.
  - Versions: how many variants.
  - Missing: the sites without it.
  - Detail: "{sentence}. Variants: {variant}: {sites}; ... . Missing from: {sites}. Not read on: {sites}." Plugin and theme rows then add the across_note, such as " Activating, deactivating and installing from WordPress.org work here; updating and automatic updates are not on WordPress's REST API, so Open in Dashboard goes to each site's Plugins screen."
  - A site that refused the list is a first row, and is never counted as missing.
- F1 (node help):
  - Across Sites: "The same name on every site, or a Site Set: where copies differ, what is missing."
  - Tags and Categories: "Each tag and category by name, on every site: differing slugs, sites without."
  - Plugins: "Each plugin by name, on every site: versions, active or not, missing."
  - Themes: "Each theme by name, on every site."
  - People: "Each person, by email, on every site, with their role on each."
  - Settings: "Each setting, on every site, and where the values drift."
  - Application Passwords: "Each application password by name and person, on every site."
  - Menus: "Each menu by name, on every site: its items, and the sites without it."
  - Synced Patterns: "Each synced pattern by title, on every site: its content, where missing."
  - Fleet: "Every site in one list: health, backups, security and updates, each known, unknown, unavailable or stale."
- F1 (row help):
  - across: "One name across sites. Alt+Enter shows its variants and the sites missing it."
  - fleet: "One site in the fleet. Enter selects it in the tree; Alt+Enter reads each state."
- Code: workbench_places.py (ACROSS_NODES, places_rows "across" and "fleet"), workbench_across.py (ACROSS_KINDS, gather_across, across_rows), workbench_fleet.py, wordpress_workbench_across.py (across_list, across_sheet), workbench_node_help.py.
- Review notes:
  - Review note: Ctrl+0 lands on an empty container. The person hears the node and an empty list, and must know to press Right Arrow. Ctrl+1 (Needs My Attention) avoids this by landing on Inbox, a child. Ctrl+0 could land on Tags and Categories, or the container could list its children as rows.
  - Review note: a row's detail is one long run-on sentence of variants, missing sites and, for plugins and themes, the same REST disclaimer on every row. Arrowing down a 40-plugin list repeats the disclaimer 40 times if the details pane is read. Put the disclaimer in the node's help once.
  - Review note: the Plugins variant is "version {v}, {status}", which mixes two facts into one variant. See Make Them the Same.

### Across row context menu

- How to reach it: Applications key or Shift+F10 on an across row. The rows (seven actions plus Properties, so no More):
  - Read in Full (default, Enter): moves focus to the details pane.
  - Make Them the Same...
  - Promote to Network...
  - Revoke Everywhere...
  - Compare Global Styles
  - Install on Sites Missing It...
  - Open in Dashboard
  - Then Show Only and Hide submenus, then Properties...
- Keyless reasons (workbench_places.py KEYLESS and workbench_admin_actions.py):
  - Make Them the Same: "Aligning sites is occasional and previewed site by site (rule 9)."
  - Promote to Network: "Done once per plugin on a network, rarely (rule 9)."
  - Compare Global Styles: "Comparing styles across sites is occasional (rule 9)."
  - Revoke Everywhere: "Revoking a leaked password everywhere is rare (rule 9)."
  - Install on Sites Missing It: "Filling the gaps across sites is occasional and previewed." (workbench_admin_actions.py; it cites no rule number, unlike its neighbours).
  - Open in Dashboard: "Leaves QUILL for the browser, now and then (rule 9)."
- Every action is offered on every across kind and refuses with the matrix reason on kinds it does not serve. Examples:
  - "Revoke Everywhere works on a row of Across Sites > Application Passwords."
  - "Install on Sites Missing It works on Across Sites > Plugins and Themes."
  - "Promote to Network works on a plugin, in Across Sites > Plugins. {reason}"
- Review notes:
  - Review note (critical): across rows carry no site (`WbRow("across", "", ...)`), so the window's `refusal_for` returns nothing for every across action. Each handler must check access itself:
    - Make Them the Same and Revoke Everywhere check per site.
    - Install on Sites Missing It checks nothing.
    - Promote to Network checks only `activate_plugins`, not Workbench Access.
    - Under Read Only access, Safe Mode or View As Role, those last two still write.
  - Review note: Revoke Everywhere is irreversible ("a revoked password cannot be restored") but is Tier WRITE, the same tier as Make Them the Same. It should be DESTRUCTIVE, like Delete Permanently, with a confirmation by name.
  - Review note: five of seven actions refuse on most kinds. Hide the rows a kind cannot use; the scope matrix already says which.

### Make Them the Same

- Allowed on: tags and categories (name, slug, description; made where missing), plugins (active or not), settings (the value), people (the role), synced patterns (content; made where missing), themes (opens each site's Themes screen), menus (items copied as links). Application passwords are refused: "A password is made on each site and shown once; it cannot be copied."
- What opens, step 1: a chooser titled "Make {name} the Same".
  - Labelled "Which version wins:" (access key W). The rows are the variant words, such as "slug news" or "version 2.3, active".
  - Help: "Every site in scope is changed to match the version you choose."
- Step 2, when every holder of the winner is the Practice Site and a real site would change: the crossing question, titled "Make {name} the Same: from the Practice Site to a Real Site".
- Step 3: each target site is checked. Refused sites become "Not changed. {site}: {name}: {reason}" lines. A site the list could not be read on is never written to: "not read: {why}; nothing is sent there".
- Step 4, the preview, titled "Make {name} the Same":
  - Ordinary kinds:
    - Summary: "{n} sites get {name} as {winner}."
    - Lines: "{site}: {name}: {words}", for example "slug news-old becomes news", "inactive becomes active", "role author becomes editor", "made, as the winner has it". Then the "Not changed. ..." lines.
    - Button: "Make Them the Same".
  - Themes:
    - Summary: "WordPress's REST API cannot activate a theme, so QUILL opens each site's Themes screen in your browser, to activate {name} there."
    - Lines: "{site}: opens Appearance > Themes for {stylesheet}".
    - Button: "Open Them".
  - Menus:
    - Summary: "{n} sites get the {name} menu's items as links, pointed at each site's own address. Their items are replaced, and this cannot be undone."
    - Lines: "{site}: replaces its items" or "{site}: makes the menu".
    - Button: "Make Them the Same".
- Nothing to send: "Nothing to send: {first refusal}." or "Every site already matches."
- Announced after:
  - Ordinary kinds: "{name}: {good} of {n} sites changed to {winner}."
  - Themes: "Opened {n} Themes screens; activate {name} on each."
  - Menus: "{name}: {good} of {n} sites now have the same menu."
  - If any site failed, a report "Make {name} the Same: Each Site" with "Done." and "Not done." lines.
- Undo: Ctrl+Z puts back every edit that has a "before" ("Put {n} back as they were."). Made-where-missing items and menus cannot be undone.
- Code: workbench_across.py (same_everywhere_plan), workbench_across_ops.py (MAKE_SAME_KINDS, make_same_edits, _edit_for, menu_copy, theme_screens), wordpress_workbench_across.py (do_make_same, _make_themes_same, _make_menus_same, _across_refusal).
- Review notes:
  - Review note (critical): for plugins, the variant includes the version, but the edit sends only `{"status": ...}`. Choose "version 2.3, active" when another site has "version 2.1, active": the plan says "changes from version 2.1, active to version 2.3, active", the request changes nothing, and the outcome says "2 of 2 sites changed to version 2.3, active". That is a false success. Either compare plugin status only, or say plainly that versions are not changed and point to Open in Dashboard.
  - Review note: Make Them the Same on Settings can push values such as `siteurl`, `home` or `admin_email` from one site to the others. Those are in `wp/v2/settings`. The preview lists them, but nothing warns that some settings are site-identity values that must never be the same.
  - Review note: the winner chooser shows only variant words, not which sites hold each variant or how many. The person must read the row's Properties first to know which is the majority.

### Promote to Network

- Allowed on: Across Sites > Plugins rows only.
- What happens: each site holding the plugin is checked in the background ("checking for a network").
  - Not a network: "{site} is not a multisite network: its plugin schema has no network-active ..." (the full sentence is in workbench_across_ops.py network_refusal).
  - Lacking rights: "Promote to Network needs a super admin of {site}'s network."
  - If none qualifies, that first reason is spoken and nothing opens.
- Practice guard (together): titled "Promote to Network: the Practice Site and Real Sites Together". Wording: "Promote to Network would change {real}, a real site that other people can see, in the same step as {practice}, the practice site on this computer. Practice and real sites are changed together only if you choose it here. Change {real} too?" Buttons "Change {site} Too" (or "Change Them Too") and "Cancel" (the default).
- Preview, titled "Promote to Network":
  - Summary: "{name} runs on every site of each network below, and no single site can deactivate it. WordPress refuses unless you are a super admin."
  - Lines: "{site}: becomes network-active" plus "Not changed. {why}".
  - Button: "Promote".
- Announced after: "{name}: network-active on {good} of {n} networks." A failure report opens if any failed.
- Undo: none. Ctrl+Z says "{said} This cannot be undone."
- Without permission: only `activate_plugins` is checked. Workbench Access, Safe Mode and View As Role are not (see the access note above).

### Revoke Everywhere

- Allowed on: Across Sites > Application Passwords rows. The key is "{password name}, {person}".
- Checks: each site's `write_refusal`, plus `edit_users` when the password is not yours. Refused sites become "Not changed." lines.
  - Nothing to revoke: "Nothing to revoke: {first refusal}." or "No site has it."
- Practice guard (together), as above, with "Revoke Everywhere".
- Preview, titled "Revoke Everywhere":
  - Summary: "{name} is revoked on {n} sites. Anything signing in with it stops working, and this cannot be undone: a revoked password cannot be restored."
  - Lines: "{site}: revokes {name}".
  - Button: "Revoke" (the default).
- Announced after: "{name}: revoked on {good} of {n} sites. It cannot be undone."
- Undo: Ctrl+Z then says "{name}: revoked on {good} of {n} sites. It cannot be undone. This cannot be undone."
- Review notes:
  - Review note: the Ctrl+Z sentence is doubled: "It cannot be undone. This cannot be undone." `do_undo` appends its own "This cannot be undone." to a summary that already says it.
  - Review note: a destructive, irreversible action whose preview defaults to "Revoke" on Enter. Every other irreversible action in the window (Delete Permanently, Reset) asks with Cancel as the default.

### Compare Global Styles

- Allowed on: Themes rows. On other kinds it speaks "Only themes have global styles."
- What happens: every site in scope is read in the background ("comparing global styles").
- Announced after: "{n} of {m} styles differ across {k} sites; {s} are the same." or "No site's global styles could be read." Then a report "Compare Global Styles" with the summary, each unreadable site, and "{style}: {site} {value}; {site} {value}" for each style that differs.
- F1: "Each style that differs, with each site's value; unread sites say why."
- Review notes:
  - Review note: it compares every site's styles in effect, not the selected theme's. The row the person chose makes no difference beyond being a theme row.
  - Review note: spoken, and then a report with the same sentence opens (GATE-13).

### Install on Sites Missing It

- Allowed on: Plugins and Themes rows. Otherwise "Install on Sites Missing It works on Across Sites > Plugins and Themes."
  - Nothing missing: "Every site in scope already has {name}."
- Practice guard: when only the Practice Site holds it, the crossing question titled "Install on Sites Missing It: from the Practice Site to a Real Site".
- Themes: a preview titled "Install on Sites Missing It".
  - Summary: "WordPress's REST API cannot install a theme, so QUILL opens Appearance > Themes > Add New for {name} on {n} sites in your browser."
  - Lines: "{site}: opens Add New, searching for {slug}". Button "Open Them".
  - Nothing is spoken after; the browser tabs open.
- Plugins:
  - Without a WordPress.org slug: "{name} does not say its WordPress.org name, so it cannot be installed."
  - Otherwise, on first use in the window, the WordPress.org consent question (Yes button "Ask", default Cancel). Declining speaks "Nothing was sent to WordPress.org." and the preview still opens, with "Not checked on WordPress.org." as a line.
  - Preview "Install on Sites Missing It": "Each site installs {name} ({slug}) from WordPress.org, inactive. A plugin not in the WordPress.org directory fails on that site and the rest go on." plus the update limits. Lines "{site}: installs {slug}, left inactive". Button "Install".
- Announced after: "{name} installed on {made} of {n} sites, inactive." plus " Not installed: {first three}" when some failed.
- Undo: none recorded; nothing goes into Change History at all.
- Without permission: not found in code. No access or capability check on the target sites. WordPress refuses per site, and the refusal shows in "Not installed".
- Review notes:
  - Review note (critical): installs plugins with no Workbench Access, Safe Mode or View As Role check, and no `install_plugins` check.
  - Review note: plugin installs are not recorded in Change History, so they do not appear in Edit > Change History either. Every other site change in this section is recorded.
  - Review note: declining WordPress.org consent still goes straight to an install preview, which installs from WordPress.org anyway. Saying no to "ask WordPress.org" and then pressing Install sends the request to the site, which itself asks WordPress.org. The consent wording should make clear what "no" covers.

### Open in Dashboard

- On an across row, when more than one site applies: a chooser "Which site:", help "The site whose wp-admin screen opens in your browser."; the browser then opens that screen. On a row with no screen: "Open in Dashboard works on a plugin, a theme, or Across Sites row."
- Review note: one site at a time. "Open it on every site missing it" is what Install already does for themes, but Open in Dashboard has no "all" choice.

### Properties on an across row (Alt+Enter)

- What opens: a read-only sheet with three pages.
  - General: "About" (the detail).
  - Variants: one "{variant}: {sites}" a line.
  - Missing From: the missing sites and "Not read on {site}: {reasons}", or "Every site in scope has it."
- Review note: the sheet's only purpose is reading; it adds no actions. Fine, but the row's detail already holds the same text.

### Site Sets

- How to reach it: Site menu, Site Sets (Alt+S, T); chord Ctrl+Alt+T. Menu help "Name a set of your sites."
- What opens, step 1: a text question titled "Site Sets", labelled "Name of the set:" (access key N). Help: "Such as Client sites. A name you have used before changes that set." Empty stops quietly.
- Step 2: a check-box list titled "Site Set: {name}", labelled "Sites in the set" (access key stripped). Every connected site is listed; members are already checked. Help: "Check each site that belongs to the set. None checked removes the set. Space checks or unchecks."
- Announced after: "{name}: {n} sites." or "Removed {name}."
- Stored: `workbench_options.json` beside the site list, by site display name.
- Undo: none (a local setting; not recorded).
- Cancel: either step, nothing saved.
- Code: workbench_options.py (site_sets), wordpress_workbench_across.py (do_site_sets).
- Review notes:
  - Review note: the person types a set name blind. Existing sets are never listed, so changing "Client sites" means remembering its exact spelling, and a typo silently makes a second set. Start with a chooser of existing sets plus "New Set...".
  - Review note: there is no rename. A set is deleted only by unchecking every site, which is not discoverable from the first dialog.
  - Review note: members are stored by display name. Renaming a site, or a Practice Site picking up " (practice)", drops it from every set with no word said.

### Across Sites Scope

- How to reach it: Site menu, Across Sites Scope (Alt+S, O); chord Ctrl+Alt+Y. Menu help "Every site, or one set."
- What opens: a chooser titled "Across Sites Scope", labelled "Across:" (access key A). Rows: "Every site", then each set name. Help: "Which sites Across Sites and the Fleet cover. Site Sets makes a set."
- Announced after: "Across Sites covers every site." or "Across Sites covers {set}." The current list then reloads.
- Code: wordpress_workbench_across.py (do_scope, scope_sites).
- Review notes:
  - Review note (critical for trust): the scope is invisible and short-lived.
    - It is not in Where Am I (Alt+1), not in the status bar, and not in the node help.
    - It is kept only on the provider object (`self.scope`), so closing the window returns it to every site.
    - The chooser always starts on "Every site", whatever the current scope.
    - A person who set "Client sites" yesterday and presses Make Them the Same today is changing every site.
  - Review note: the scope covers Across Sites, the Fleet and Compare Global Styles only. The Calendar, Needs My Attention, Watches and Copy to Site's site list ignore it. The help names "Across Sites and the Fleet", which is accurate but easy to miss.
  - Review note: if the chosen set is removed, the scope silently becomes every site (`members is None`).

### Calendar

- How to reach it: Go menu, Calendar (Alt+G, D); chord Ctrl+3 (kept here because this window has no AI menu; the comment in workbench_window_menu.py records the 2026-11-13 decision). Go help "Every site's content, by day."
- What it lists: one row per day from 14 days ago onward, with every scheduled post and page however far ahead, from every connected site (not the Across scope), custom types included.
  - Columns: Day, Scheduled, Published.
  - Day text: "Tuesday 12 November". Detail: "Tuesday 12 November: 2 scheduled, 1 published. Enter lists them."
  - A site or type that would not answer is a first row: "Could not ask {site}, {kind}: {why}".
- Day nodes: a dynamic "Day" child appears under Calendar for each day, labelled with the same day words. After a load that found new days, the tree is rebuilt.
- Row menu (kind "day"): "Open This Day" (default, help "List what the day holds."), then Properties. Enter selects that day's node in the tree and moves focus there. Its list has item rows (Title, Site, Status, Date) with the full item menu, including Move to Another Day... (Ctrl+Alt+Shift+D) and Copy to Site.
- F1:
  - Calendar node: "Every site's scheduled and published content, a day to a node."
  - Day node: "What was published or is scheduled on one day, on every site."
  - Day row: "A day with scheduled or published content. Enter lists it."
- Code: workbench_bold.py core (calendar_days, day_words), wordpress_workbench_bold.py (calendar_rows, day_rows, day_children, do_open_day, _days_changed).
- Review notes:
  - Review note: days run oldest first, so the list opens on two weeks ago. Today and the coming week, the part people plan with, are in the middle. Start at today, or select today's row.
  - Review note: the day words have no year, so late December and early January read the same pattern with no year cue.
  - Review note: each status and type is capped at 300 (`max_pages=3`), and no row says so.
  - Review note: rebuilding the tree after each Calendar load (`wx.CallAfter(self._days_changed)`) may make the screen reader re-announce the tree or move its virtual position. Worth a JAWS and NVDA check.

### Fleet

- Under Across Sites. Rows: one per site in scope, with WordPress version, comments waiting, and Health, Backups, Security and Updates, each "known", "unknown", "unavailable" or "stale".
- A site that does not answer: "not answering: {why}", and each column says "unknown: the site did not answer". A site that answered before keeps its last facts, marked "stale, as read {n minutes ago}; not answering now: {why}".
- Row menu: "Open This Site" (default, "Select it in the tree."), Properties.
- Review note: it is read only and that is said ("The Fleet only reads; it changes nothing."). It is a good summary view, but nothing links a "critical" health state to Needs My Attention > Site Health.

## Needs My Attention and Watches

Needs My Attention is the account-level node that gathers, from every connected site, what is waiting on the person: comments to moderate, items waiting for review, scheduled items, their drafts, updates, health problems, missing alt text, broken links, spam, form responses and membership orders, plus Inbox, which mixes four of them. Watches are the background half: each kind is off until checked in Tools > Workbench Options, then the editor's two-minute timer asks the sites at most every fifteen minutes and speaks what changed. Watches are a separate node under Needs My Attention that shows each Watch's state.

### Needs My Attention and Inbox

- How to reach it:
  - Go menu, Needs My Attention (Alt+G, N); chord Ctrl+1. Go help "What needs you, on every site."
  - Ctrl+1 lands on the Inbox node, the first child, not on the container.
  - The status bar's "Waiting" cell (when comments wait) goes to Comments Waiting on Enter. Help: "Comments waiting on your sites, when there are any. Enter goes to them."
- Children, in order:
  - Inbox (columns What, Site, When)
  - Comments Waiting
  - Pending Review
  - Scheduled
  - Drafts
  - Updates
  - Site Health
  - Accessibility
  - Broken Links
  - Held as Spam
  - Form Responses
  - Membership Orders
  - Watches
- What Inbox holds:
  - Comments waiting, prefixed "Comment: {title}".
  - Pending review, prefixed "Pending review: ...".
  - Held as spam, prefixed "Held as spam: ...".
  - Form responses, prefixed "Form response: ...".
  - All newest first.
  - A site that fails is a first row: "Could not ask {site}", with detail "{site} did not answer: {why}".
- Row menus: each Inbox row keeps its own kind's menu (a comment row gets Approve and Spam, an item row Open in Editor and Publish), even though the node's row type is "mixed".
- F1:
  - Needs My Attention: "What waits on you, gathered from every connected site."
  - Inbox: "Everything below Needs My Attention, newest first, from every site."
  - Comments Waiting: "Comments held for moderation on every site. Ctrl+Shift+A approves."
  - Scheduled: "Posts and pages that will publish themselves, with their dates."
  - Drafts: "Your own drafts, on every site."
  - Held as Spam: "Comments and form entries a site doubted. Ctrl+Shift+A releases one."
  - Broken Links: "Dead web links found in a bounded sample of published posts and pages on every site."
  - mixed row: "Something that needs you. Enter reads it in full."
- Without permission: a site with no sites connected shows the "no instance" text. What a role cannot read is a site error row.
- Undo: per row action (comments: Ctrl+Z puts the old status back).
- Code: workbench_attention.py (ATTENTION, gather, _inbox, unreachable_row), workbench_tree.py (the attention nodes), workbench_window_menu.py (GO_NODES), wordpress_workbench_window_status.py (Waiting cell).
- Review notes:
  - Review note: Inbox's F1 says "Everything below Needs My Attention". It actually holds four of the twelve: waiting comments, pending review, spam and form responses. Scheduled, drafts, updates, health, accessibility, broken links and membership orders are not in it.
  - Review note: a stopped Practice Site stays connected. Every Needs My Attention node then starts with "Could not ask Practice Site" every time QUILL starts (the site stops when QUILL closes). Mark a practice site as stopped rather than failed, or leave it out of the account-level lists while it is not running.
  - Review note: "Could not ask {site}" rows have kind "fact", so their F1 says "A fact about the site. Enter reads it in the details pane." That is accurate enough, but it would help to say what to do (check the connection, or Site Properties).
  - Review note: Broken Links here is a sample (first 40 unique links, said in its row). Its F1 does not mention Check Every Link under By Name > Links, the full version.

### Watches node

- How to reach it: Go menu, Watches (Alt+G, W); chord Ctrl+5. Go help "What the Workbench watches for you." In the tree it is the last child of Needs My Attention.
- What it lists (columns Watch, State; rows are facts):
  - One row per Watch kind, "on" or "off":
    - "New comments waiting"
    - "New form responses"
    - "Plugin updates available"
    - "Scheduled posts going live"
    - "A site not answering, and answering again"
    - "Items with a reviewer leaving the queue"
    - "Site Health status changes"
    - "Form spam questions, once a week"
  - "How often": "at most every {n} minutes, while QUILL is open; Tools > Workbench Options turns each on or off".
  - When any Watch is on:
    - "Last round": "none yet", or "{day month, HH:MM}, {n} minutes ago". When stale it adds "; that is stale: QUILL was closed, asleep or offline since".
    - Then one row per site: "not answering since {when}", "answering; last heard {when}" or "not checked yet".
- Row menu: kind "fact", so Read in Full (Enter, moves to details) and Properties only.
- F1:
  - Node: "What you asked the Workbench to keep an eye on."
  - Row: "A fact about the site. Enter reads it in the details pane."
- Code: wordpress_workbench_bold.py (fixed_rows, family "watches"), workbench_watches.py (KINDS, status_facts), workbench_tree.py.
- Review notes:
  - Review note: the rows read "on" and "off" but cannot be changed where they are. Space or Enter on "New comments waiting off" does nothing useful. Let Enter (or a context-menu row) turn a Watch on or off, or open Workbench Options with that Watch focused.
  - Review note: the row F1 ("A fact about the site") is wrong for a Watch row, which is about the account.
  - Review note: nothing the Watches said is kept. There is no "what changed" list on this node, so a sentence missed while away from the computer is gone. The node shows when the last round ran, but not what it found.

### Workbench Options (choosing Watches)

- How to reach it: Tools menu, Workbench Options (Alt+T, O); chord Ctrl+Shift+O. Menu help "Choose which Watches the Workbench announces."
- What opens: a check-box list titled "Workbench Options", labelled "Options" (the access key is stripped). Eight check boxes, one per kind: "Watch: New comments waiting", "Watch: New form responses", "Watch: Plugin updates available", "Watch: Scheduled posts going live", "Watch: A site not answering, and answering again", "Watch: Items with a reviewer leaving the queue", "Watch: Site Health status changes", "Watch: Form spam questions, once a week". Then OK (the default) and Cancel.
- Help (F1): "Every Watch is off until you check it: nothing is asked of your sites for Watches before then. A checked Watch asks each connected site over the internet at most every fifteen minutes while the editor is open, and says only what changed; its first look is silent. Space checks or unchecks."
- Announced after: "Workbench options saved."
- Stored: `workbench_options.json` (watches, watch_minutes, site_sets), shared by QUILL and QUILL Lite.
- Undo: none (a local setting).
- Cancel: nothing saved.
- Code: wordpress_workbench_options.py (do_options), workbench_options.py, wordpress_workbench_dialogs.py (ask_checks).
- Review notes:
  - Review note: the consent is only in F1. Checking a box starts network requests to every site, but the visible label says only "Watch: New comments waiting", and the screen reader reads the help only if F1 is pressed.
  - Review note: the interval is not a choice. `watch_minutes` (minimum 15) exists in the options file and is shown on the Watches node, but no dialog sets it.
  - Review note: "Workbench options saved." does not say what is now on. Saying "3 Watches on: comments, form responses, site down." would confirm the change without a trip to the Watches node.
  - Review note: the window is titled "Workbench Options" but holds only Watches. Site Sets, which share the same file, live in another dialog.
  - Review note: the help says "while the editor is open"; the Watches node says "while QUILL is open". Watches run from the editor's timer, in QUILL and in QUILL Lite, whether or not the Workbench is open. One wording, please.

### What Watches announce, and when

- When: the editor's two-minute WordPress timer calls `watch_round`. A round runs only if a Watch is on, at least one site is connected, no round is already running, and at least max(15, watch_minutes) minutes have passed since the last. The round's time is saved before any site is asked, so QUILL and QUILL Lite open together do not both run it.
- The first look at each Watch on each site is silent. A change is said once.
- Spoken sentences (each through the editor's announce, which speaks and brailles, one announce per sentence):
  - Comments: "{n} new comment waiting on {site}." or "{n} new comments waiting on {site}."
  - Scheduled going live: "Now published on {site}: {titles}."
  - Form responses: "A new form response on {site}."
  - Plugin updates: "Updates available on {site}: {plugin names}."
  - Site down: "{site} is not answering. Watches will try again next round."
  - Site back: "{site} answers again."
  - Reviews: "{title} on {site} was published.", "... was approved and scheduled.", "... was sent back to its writer.", "... was moved to the Trash." or "... was published privately."
  - Site Health: "Site Health on {site}: {test} is now critical; {test} is now good."
  - Form spam (weekly): "Form spam questions on {site}, week {2026-W46}: {n} asked, {n} answered, {n} answered wrongly, {n} sent anyway." It adds " Up from {n} asked the week before.", " Down from ..." or " The same as the week before."
- Without permission: Site Health is silent for anyone but an administrator. A list the account may not read is silent.
- Code: wordpress_watch_commands.py (watch_round), workbench_watches.py (check, _site_round, _health, _reviews, due, MIN_MINUTES), workbench_qaf_spam_edit.py (weekly_watch), workbench_editorial.py (queue_status).
- Review notes:
  - Review note (critical): one failed read silences every other Watch on that site. `_site_round` runs the comments check first, and any `WordPressApiError` (for example an Author account refused on held comments) is caught around the whole site (`except WordPressApiError: continue`). Form responses, updates, health and reviews on that site are then never said, every round, and nothing tells the person.
  - Review note: "Plugin updates available" depends on an `update` or `new_version` field in `wp/v2/plugins`. Core WordPress does not send it (the Fleet's own docstring says core REST "does not report waiting updates"). On most sites this Watch will never speak, and its label promises otherwise.
  - Review note: a round can produce a burst. Eight kinds times several sites, each sentence a separate announce, arrive at once and may interrupt each other or whatever the person is reading in the editor. Combine a round into one sentence ("3 changes: ...") with the details on the Watches node.
  - Review note: "A new form response on {site}." is said whatever the count. Ten new responses sound like one. Watches only track the newest id, so the count is not known; say "New form responses".
  - Review note: comments waiting are read one page of 100 (`max_pages=1`). On a site with a large backlog, new comments past the first 100 are not counted.
  - Review note: the Practice Site stops whenever QUILL closes. With "A site not answering" on, the next session can say "Practice Site is not answering..." and later "Practice Site answers again." for something the person never meant to watch.
  - Review note: ISO week codes ("2026-W46") are spoken as is in the form-spam sentence. "the week of 9 November" would be friendlier.
  - Review note: Watches ignore Across Sites Scope and Site Sets; every connected site is asked.

## Practice Site

The Practice Site is a WordPress site that runs on this computer only (WordPress Playground on the bundled Node, at http://127.0.0.1:9400), for learning with nothing at stake. It has a node that reports its state and a Tools dialog that starts, stops, connects and resets it. Every command that would carry practice work to a real site asks first, by name, with Cancel as the default.

### Practice Site node

- How to reach it: Go menu, Practice Site (Alt+G, R); chord Ctrl+6. Go help "The WordPress site on this computer." Also in the tree as an account-level node.
- What it lists (columns Fact, Value):
  - "Playground's tool": the path, or "not in this build".
  - "Node.js": the path, or "not found".
  - "WordPress core": the path, or "not bundled".
  - "Running": "yes, at http://127.0.0.1:9400" or "no".
  - "What to do": what is missing, or "Tools > Practice Site starts it."
- Row menu: kind "fact", so Read in Full and Properties only. Nothing on the node starts or stops the site.
- F1:
  - Node: "A practice WordPress site on this computer, where nothing is at stake."
  - Rows: "A fact about the site. Enter reads it in the details pane."
- Code: wordpress_workbench_bold.py (fixed_rows, the practice branch), workbench_practice.py (find_cli, missing_words, site_url).
- Review notes:
  - Review note: the node reports but cannot act. Its "What to do" row says "Tools > Practice Site starts it." Enter on that row, or a node context-menu row, should simply open the Practice Site dialog.
  - Review note: the first three rows are file paths, which are long to hear and matter only when something is missing. "Ready" or the missing piece would be enough, with paths in Properties.

### The Practice Site dialog

- How to reach it: Tools menu, Practice Site (Alt+T, P); chord Ctrl+Alt+P. Menu help "Start, stop, connect or reset it."
- Before it opens:
  - If the site had stopped by itself: "The Practice Site stopped. Its saved data is still there."
  - If it is not running and a piece is missing, that sentence is spoken and nothing opens. The sentences:
    - "The practice site needs WordPress Playground's tool, which this build of QUILL does not include yet. A build made with scripts/fetch_build_deps.py --only wp-playground-cli has it."
    - "The practice site needs Node.js, which ships with QUILL's shared runtime."
    - "The practice site needs its pinned WordPress core files in this build of QUILL."
- What opens: a chooser titled "Practice Site", labelled "Do:" (access key D). OK is the default.
  - Help: "A WordPress site on this computer only, for learning with nothing at stake. Reset puts it back as new. Press Enter to choose the selected one."
  - The choices depend on state:
    - Not running: "Start the Practice Site", "Reset the Practice Site".
    - Running: "Connect It as Practice Site", "Stop the Practice Site".
- Code: wordpress_workbench_bold_practice.py (do_practice, _connect_practice, RESET_WARNING), workbench_practice.py, workbench_practice_process.py (start_process, wait_for_site, stop_process, the port check).

### Start the Practice Site

- What happens: in the background ("starting the Practice Site"), Playground starts on 127.0.0.1 port 9400 only, tied to QUILL so it stops when QUILL closes. QUILL waits up to five minutes for WordPress to answer; a first start took nearly three minutes in the 2026-11-13 run.
- Announced after:
  - Success: "The Practice Site is running at http://127.0.0.1:9400. Connect it in a moment."
  - It ended while starting: "The Practice Site stopped as it was starting. Start it again or reset it."
- Failures, spoken as the error:
  - Port taken: "Something on this computer is already using port 9400, which the Practice Site needs. If another copy of QUILL or QUILL Lite has its Practice Site running, stop it there first, then start this one again."
  - Died early: "The Practice Site stopped before WordPress was ready. It said: {last line} Start it again, or reset it if this keeps happening."
  - Timed out: "The Practice Site did not become ready within 300 seconds, so QUILL stopped it. Start it again; if it still does not start, reset it."
  - Window closed first: "The Workbench closed before the Practice Site started."
  - Core files: "The bundled WordPress core failed its SHA-256 check. Re-stage the Practice Site." or "... could not be unpacked. Reset the Practice Site." or "... is incomplete. Re-stage the Practice Site."
- Review notes:
  - Review note (critical): a start of up to five minutes is silent. No "Starting; this can take three minutes the first time" is said at the start, and nothing is said during it. The person cannot tell a slow start from a hung one. Say the expected wait up front, and give a status-bar cell like Check Every Link's.
  - Review note: the start holds one of the window's two background workers for up to five minutes. With a link check running, no node can load until one finishes (see Check Every Link).
  - Review note: "Connect it in a moment." means opening the dialog again and choosing Connect. Starting and connecting are two trips for what is always wanted together. Connect when the start finishes, or offer "Start and Connect".

### Connect It as Practice Site

- Only offered while it runs.
- What happens: QUILL reads the one-time password file the site wrote, stores the password in Windows Credential Manager, adds or updates a site profile named "Practice Site" ("Practice Site (local)", "Practice Site (local 2)" if taken), deletes the password file, and rebuilds the tree.
- Announced after:
  - "{name} is connected. It is under Sites."
  - "{name} is connected. It is under Sites, but the one-time password file could not be removed. Reset the practice site to remove it."
  - No password file yet, but already connected: "{name} is already connected. It is under Sites."
  - No password file and not connected: "The practice site is still starting. Try Connect again in a moment."
- Without permission: none needed; local only.
- Review notes:
  - Review note: Connect stays on the menu after connecting. Choosing it again says "already connected", which is fine, but the dialog could say "Connected" in the choice instead.
  - Review note: the site always shows under Sites as "(practice)" (practice_label), which is the right protection; every preview and history line carries it.

### Stop the Practice Site

- Only offered while it runs. It stops Playground and every process under it.
- Announced after: "The practice site has stopped."
- Review notes:
  - Review note: "practice site" is lower case here and in Reset's sentence, but "Practice Site" in the menu, the dialog title, Start's sentence and the node. A small thing, but braille shows it.
  - Review note: Stop runs on the UI thread (`stop_process` is called directly, not through `background`). On Windows this may run taskkill and wait, which freezes the window briefly with no announcement.
  - Review note: the profile stays connected after Stop, so every account-level node (Needs My Attention, Calendar) lists "Could not ask Practice Site" until it is started again or forgotten.

### Reset the Practice Site

- Only offered while it is stopped.
- What opens: a Yes/Cancel question titled "Reset the Practice Site".
  - Wording: "Reset the Practice Site? This permanently deletes everything on it: every post, page, upload, comment, user, plugin and setting you made or changed there. QUILL also forgets its Practice Site connection and removes its stored password from Windows Credential Manager. Your real WordPress sites are not touched. This cannot be undone. The next start builds a brand-new site with the starter content."
  - Buttons: "Reset", and "Cancel" (the default).
- What happens: in the background ("resetting the Practice Site"), the folder is emptied, the stored password is removed, the profile is removed from the site list, and the tree is rebuilt.
- Announced after: "The practice site is new again. Start it to use it."
- Undo: none, and the warning says so plainly. This is the model the other irreversible actions (Revoke Everywhere, Merge Into) should follow.
- Review notes:
  - Review note: Reset is unreachable when a piece is missing. The dialog does not open at all if the tool, Node or core files are absent, so a person cannot clear an old practice site's data and its stored password on a build that no longer has the tool. Reset needs only the folder.
  - Review note: a snapshot of the Practice Site survives a Reset (snapshots are keyed by the profile id, which Reset forgets). Those snapshots can no longer be reached from Put Back, because Put Back looks under the current profile's id. They are orphaned on disk.

### The practice crossing question (used by other commands)

- Asked by: Copy to Site, Make Them the Same, Install on Sites Missing It, Put Back from a Snapshot (a snapshot taken on the Practice Site, onto a real site), and in its together form by Promote to Network and Revoke Everywhere.
- Wording (crossing): "{action} would send what is on {practice}, the practice site on this computer, to {real}: a real site that other people can see. Work on the practice site never goes anywhere else unless you choose it here. Send it to {real}?" Titled "{action}: from the Practice Site to a Real Site". Buttons "Send to {site}" (or "Send to Them") and "Cancel" (the default).
- Wording (together): quoted under Promote to Network. Titled "{action}: the Practice Site and Real Sites Together". Buttons "Change {site} Too" (or "Change Them Too") and "Cancel".
- Code: wordpress_workbench_bold_practice.py (practice_crossing_ok), workbench_practice.py (crossing_warning, together_warning, is_practice_address, practice_label).
- Review notes:
  - Review note: WXR is a gap in the guard. Export from the Practice Site, then Import WXR as Drafts into a real site, carries practice work across with no question.
  - Review note: the question comes before the command's own preview, so the person agrees to "send it" before seeing what "it" is. That order is deliberate in the code ("every cross-site write calls this before its own preview"). A sentence in the preview ("This comes from the Practice Site") would keep the reminder in view at the moment of the real decision.
  - Review note: on the Cancel default, Enter cancels. That is the right default for this question, and it is the opposite of every preview's default, so the same Enter key means "go ahead" one dialog later.

### Undo across this section (Ctrl+Z, Edit > Undo WordPress Change)

- How it works: `do_undo` looks only at the newest Change History entry. If that entry has no undo, it speaks "{summary} This cannot be undone." and stops.
- Recorded with no undo: Copy to Site, Put Back from a Snapshot, Make Them the Same for menus, Promote to Network, Revoke Everywhere, a By Name Merge of terms, and an import that made nothing. Install on Sites Missing It is not recorded at all.
- Code: quill/core/workbench/history.py (ChangeHistory), wordpress_workbench_sheets.py (do_undo, do_history).
- Review notes:
  - Review note (critical): a non-undoable entry blocks the whole stack. After any of the commands above, Ctrl+Z can no longer reach the undoable change made just before it (a Trash, a Rename Everywhere). The person hears "... This cannot be undone." and may conclude the earlier change cannot be undone either. Skip past non-undoable entries, or say "The newest change cannot be undone; Change History lists the earlier ones."
  - Review note: summaries that already say "It cannot be undone." get " This cannot be undone." added (Revoke Everywhere).

## Forms (QAF)

QUILL Accessible Forms (QAF) lives in two places. The first is the editor, in both QUILL and QUILL Lite. There a form is a plain-text .qaf document written in the QAF form language: you write it, check it, fill it in yourself, export it, publish it to a WordPress site that runs the QAF plugin, place it on a page, and read the responses. All of that runs from the shared `FormsCommands` class, through one menu table (`quill/core/forms/menu.py`). The second place is the WordPress Workbench, which shows each site's QAF forms and responses as rows. There you change a form's status and settings, delete a form, mark responses Spam or Not Spam, search responses, and manage QAF's spam questions. Writing, checking, Fill It In Yourself and the exports are local. Everything that reaches a site or an AI is off in Safe Mode, and the editor says "{command} is off in Safe Mode, because it would reach your site or an AI. Writing, checking, Fill It In Yourself and saving in other formats still work." The two Responses surfaces do not offer the same things, and that is the main review finding below. The Gravity Forms copy commands are named here only; see the Gravity Forms section for them.

### Forms in the menus, and the one Forms key

- How to reach it: File > New Form; Insert > Form Field; View > Form Outline; Format > Form Rules; Tools > Forms, which holds everything else in four groups.
  - Check This Form, Fill It In Yourself, Form Properties, Form Payments Setup, Insert Payment Field, Verify Payment Setup.
  - Publish Form, Insert Form Into Page, Test on Site, Responses.
  - Save As Web Page, Save As Word Document, Save As Large Print, Save As Braille-Ready Text.
  - Draft a Form, Plain Language, Suggest Autofill Hints.
- Access letters inside Tools > Forms (from the table, the same in Lite): &Check, &Fill, Form &Properties, Form Payments &Setup, Insert Payment Fi&eld, &Verify, P&ublish, &Insert Form Into Page, &Test, &Responses, Save As &Web Page, Save As Wor&d, Save As &Large Print, Save As &Braille-Ready Text, Dr&aft, Plain Lan&guage, Suggest Autofill &Hints.
- The one Forms key is Responses, on the WordPress layer: WordPress key, then F (Ctrl+Alt+Shift+Grave, then F). Per `forms/menu.py`, it was "decided 2026-11-13" and given "by frequency (rule 3)".
- Keyless: every other Forms row. Reason in `forms/menu.py`: "Every other Forms command keeps no chord, each for rule 9: writing a form is occasional, and its menu letters and the Command Palette are its way in."
- Code: core/forms/menu.py, main_frame_forms.py, lite_window_forms.py, forms_commands.py.
- Review notes:
  - With 17 rows in four groups, Tools > Forms is long. The editing commands (Check, Fill In, Properties) are mixed in with payments.
  - Payments has three rows here, and a fourth door through the payment kind in Insert Form Field.

### New Form

- How to reach it: File > New Form (Alt+F, M in Lite; QUILL's letter comes from the route pass, M in the table). Command Palette "New Form". No key (rule 9). Enabled in every document.
- What opens: a "New Form" dialog. Its purpose, read by F1 on the dialog: "Start a form from a template. QUILL writes it as plain text in the QAF form language, saves it, and opens it; change anything afterwards." Controls in tab order:
  - "&Title:" edit box (help "The form's name, as visitors will see it.").
  - "Te&mplate:" choice (help "What to start from. Each template is a few questions you can change.").
  - The Next button (default), then Cancel.
- Templates, each listed as "Name: description":
  - Blank: "One question to start from."
  - Contact form: "Name, email address and a message."
  - Event registration: "Name, email, how many are coming, and access arrangements, asked only when needed."
  - Membership renewal: "Contact details, membership level, and how they would like the newsletter."
  - Survey: "A rating, a yes or no, and room to say more."
  - Accessibility feedback: "Where the problem was, what happened, what they use, and whether to reply."
  - Volunteer sign-up: "Contact details, the days they can help, and what they would like to do."
- After Next: the standard Save As window, titled "Save the New Form". The file type is "Forms (*.qaf)" and the suggested name comes from the title. It asks before overwriting. A name typed without .qaf gets .qaf added.
- Announced after: "Saved {file}, a {template name in lower case} with {n} questions." ("question." when there is one). The new form opens in the editor. On a write error: "QUILL could not save {file}: {reason}."
- Undo: none needed. The file is written to disk and opened. Nothing in the current document changes.
- F1: the dialog's purpose and each field's help (SetHelpText in `BlockFormDialog`).
- Cancel: Cancel in either step stops silently. Nothing is written.
- Code: forms_commands.py (`cmd_new_form`), forms_templates.py, forms_dialogs.py (`ask_save_path`), wordpress_block_dialogs.py.
- Review notes:
  - The announcement uses "a" before every template name: "a event registration with 4 questions" and "a accessibility feedback with ...". It is also odd for "a blank with 1 question".
  - The dialog's purpose is reachable only through F1. Nothing on screen states it.
  - Cancelling silently is correct here.

### Insert > Form Field

- How to reach it: Insert > Form Field (Alt+I, F). Palette "Form Field". No key (rule 9). Dimmed unless a form document is in front.
- What opens, step 1: an "Insert Form Field" list window. Purpose: "Every kind of question a form can ask, with Section and Page Break first. Type to narrow the list, then choose one; the next window asks only what it needs." Controls in tab order:
  - "&Search:" box. Help: "Type words, such as date or choose, and press Enter to narrow the list."
  - "&Kind of question:" list. Each row reads "Kind: description", for example "Email: An email address, checked as it is typed."
  - "&Details:" read-only box.
  - The C&hoose button, then Close.
  - Enter on the list chooses.
- Step 2: a dialog titled "Insert {kind}" with an Insert button (default) and Cancel.
  - For a Page Break: only "Page &title (optional):".
  - For a Section: only "&Label:".
  - For other kinds: "&Label:", "&Id (optional):", "&Required" check box, "&Help text:" (multi-line).
  - For a choice kind, add "&Choices, one per line:" and a "Choice li&brary:" choice ("None", then each library as "{label}, {n} choices").
- Choosing the payment kind goes straight to Insert Payment Field.
- Announced after:
  - "Inserted {name}, {kind in lower case}." The caret moves to the new question.
  - A page break says "Page break inserted. Page {n} starts here."
  - The new item goes after the item at the caret. If the caret is on a section, a question goes inside it.
- Undo: Ctrl+Z in the editor takes the whole insert back (`apply` rewrites the text as one replace).
- F1: SetHelpText on the dialog and on every field.
- Cancel: silent at either step.
- Code: forms_commands.py (`cmd_insert_field`, `_insert`), forms_dialogs.py (`pick_from_list`), forms_field_types.py.
- Review notes:
  - The payment kind is offered in the list even where Form Payments is turned off in QUILL. It then answers with the Features refusal.
  - When choices and a library are both left empty on a choice kind, a placeholder "Choice 1" is added without saying so.

### View > Form Outline

- How to reach it: View > Form Outline (Alt+V, F). Palette "Form Outline". No key. Dimmed outside a form document.
- What opens: a list window titled "Form Outline". Purpose: "Every page, section and question in this form, in order. Each change here is one step that Undo in the editor takes back. Alt+Shift and the arrows move the selected question: up and down, or into and out of a section." Tab order: the "&Questions:" list, then the buttons:
  - &Go to It (also Enter).
  - Move &Up and Move &Down (also Alt+Shift+Up and Alt+Shift+Down).
  - Move &In and Move Ou&t (also Alt+Shift+Right and Alt+Shift+Left).
  - &Rename..., &Change Id..., Change T&ype..., Du&plicate, Re&move....
  - Close.
- Confirmations:
  - Remove: "Remove {name} from this form? Undo in the editor brings it back.", with Remove and Cancel buttons. No is the default.
  - Change Type asks only when something is adjusted or dropped. It shows the plan's summary and review lines, with a "Change Type" button.
- Announced after:
  - Moves: "Moved up." / "Moved down." / "Moved to page {n}." / "Moved into {section}." / "Moved out of {section}."
  - Duplicate: "Duplicated. The copy is straight after it."
  - Rename: "Renamed to {label}."
  - Change Id: "The id is now {id}."
  - Change Type: "Changed to {type}."
  - Refusals: "It is already first." / "It is already last." / "There is no section just above it to move into." / "A section cannot go inside another section here." / "It is not inside a section." / "That is a page. Move or change its questions instead." / "An id is letters, digits and underscores, and does not start with a digit." / "The id {id} is already used in this form." / "A section cannot become a question." / "This field needs {...} before it can become {type}."
  - Cancelling a sub-dialog: "Nothing changed."
- Undo: every change is one Ctrl+Z step in the editor, after the window closes.
- F1: the window's purpose, the list's help ("Each page, section and question, with what it needs. Press Enter to go to it; Alt+Shift and the arrow keys move it.") and each button's help.
- Cancel: Close or Escape leaves without changing anything.
- Code: forms_outline_commands.py, forms_dialogs.py (`show_outline_window`, `OUTLINE_KEYS`), forms_doc.py.
- Review notes:
  - Cancelling Rename, Change Id or Change Type speaks "Nothing changed." That is a spoken result for a cancel, where every other Cancel in Forms is silent. This is mild chattiness.
  - An Alt+Shift+arrow move on a disabled action only beeps (`wx.Bell`). Nothing is spoken.

### Format > Form Rules

- How to reach it: Format > Form Rules (Alt+O, M in Lite). Palette "Form Rules". No key. Dimmed outside a form document.
- What opens: a list window titled "Form Rules". Purpose: "Every rule in this form as a sentence: what shows or hides a question, what is worked out, and what is required when. Add Rule builds one from three choices." Tab order:
  - The "&Rules:" list. Each row is a sentence such as "Show {name} when {condition}."
  - The buttons &Add Rule..., &Edit..., Re&move..., &Go to It, then Close.
  - Enter goes to the question.
- Add Rule: a dialog titled "Add Rule", with an Add Rule button (default) and Cancel. Fields:
  - "&When this question:" choice.
  - "&Is:" choice: is, is not, is filled in, is empty, contains, is more than, is less than.
  - "This &answer:" edit box.
  - "Or write the condition &yourself:" edit box.
  - "&Then:" choice: Show, Hide, Require, Make optional, Enable, Disable, Skip to.
  - "To this &question or page:" choice.
- Edit: a dialog titled "Edit Rule" with "&Condition:" ("Leave it empty to remove the rule.").
- Remove confirmation: "Remove this rule? {sentence} Undo in the editor brings it back.", with a Remove Rule button.
- Announced after:
  - Add: "{Action} {name} when {sentence}."
  - Edit: "Rule changed." (or "Rule removed." when emptied).
  - Remove: "Rule removed."
  - A bad condition: "That rule cannot be read: {problem}".
  - A form with no questions: "This form has no questions for a rule to use yet."
- Undo: one Ctrl+Z step each, in the editor.
- F1: the purpose, the list's help ("Each rule as a sentence. Press Enter to go to the question it is on.") and each field's help.
- Cancel: silent.
- Code: forms_outline_commands.py (`cmd_rules`, `_add_rule`), forms_rules.py.
- Review notes:
  - Enter or Go to It on a free-standing rule row (the kind stored in the form's rules list) does nothing at all, silently (`go` returns None when the row's kind is "rule"). The list help promises "Press Enter to go to the question it is on."
  - The Add Rule dialog's Then default is "show" and its target default is the last question. A rule added with every default is "Show {last question} when {first question} is """. That is valid, but probably not what was meant.

### Tools > Forms > Check This Form

- How to reach it: Tools > Forms > Check This Form (Alt+T, then the Forms submenu, then C). No key. Dimmed outside a form document.
- What opens: when there are findings, a list window titled "Check This Form". Purpose: "{n} things to fix in this form, most serious first. Go to It takes you to the line; Check Again after you change it." Tab order: the "&Findings:" list, &Go to It, Check &Again, Close. Enter goes to the finding.
- Announced after:
  - With no findings, no window opens and it says "Check This Form found nothing to fix."
  - A finding about the whole form: "That finding is about the whole form, not one line."
  - Findings include reading problems, "QUILL keeps this as written and cannot read it: {line}", structural problems, accessibility findings and divergences.
- Undo: not applicable. It reads only.
- F1: the purpose, the list's help ("Each finding says what to fix. Press Enter to go to it.") and the button help.
- Code: forms_commands.py (`cmd_check`), forms_check.py.
- Review notes:
  - Check Again is a dead end. The window is modal, so you cannot change the form while it is open, and "Check Again after you change it" can never show anything new. When Check Again does empty the list, nothing is spoken.

### Tools > Forms > Fill It In Yourself

- How to reach it: Tools > Forms > Fill It In Yourself (F in the submenu). No key. Dimmed outside a form document.
- What opens: a dialog titled "Fill It In Yourself: {form title or Untitled form}". Purpose: "Your form as a visitor meets it. Tab through the questions and answer them; rules show and hide questions as you go, and worked-out answers update. Submit sends nothing: it shows what would have been sent."
- Controls in tab order:
  - "&Language:" choice, only when the form has more than one language.
  - A page heading ("Page 1 of 2: {title}").
  - The questions as native controls: an edit box, a check box, radio buttons in a labelled group, a drop-down list (first entry "(no answer)"), or a read-only box for worked-out answers. A question that is required has " (required)" in its name.
  - The buttons &Back, &Next, &Submit (Submit is enabled only on the last page), then Close.
- Announced before it opens:
  - "This form has no questions to fill in yet."
  - When some of the form cannot be read: "QUILL could not read all of this form, so some questions may be missing. Check This Form says where."
- Announced while filling in:
  - "{names} appears." / "{names} are hidden." when a rule shows or hides questions.
  - The new heading after Back or Next.
  - "{n} questions need an answer: {names}." when Next finds required questions empty. Focus moves to the first of them.
  - A question that only works on the site reads "QUILL cannot show a {type} question here. It works on the site."
- Submit opens a report, "What Would Be Sent", starting "Nothing was sent. This is what the form would send:", then question-and-answer lines and "Still needs an answer: ..." when relevant. The report has a "&Report:" box, a Copy &All button and Close.
- Undo: not applicable. The document is never changed.
- F1: the purpose, plus per-control help (the question's own help text, or "{name}: answer it as a visitor would.").
- Code: forms_commands.py (`cmd_fill_in`), forms_fill_window.py, forms_fill.py.
- Review notes:
  - Submit does not check the last page's required questions the way Next does. It only lists them at the bottom of the report.
  - Next both moves focus (which the screen reader reads) and announces the page heading. Those two can talk over each other. The heading is not otherwise spoken, so the announcement is allowed under GATE-13, but listen for collisions.

### Tools > Forms > Form Properties

- How to reach it: Tools > Forms > Form Properties (P in the submenu). No key. Dimmed outside a form document.
- What opens: a "Form Properties" dialog. Purpose: "Everything about this form that is not a question." Tab order:
  - "&Title:", "&Description:" (multi-line), "&Language:", "&Submit button:", "Success &message:" (multi-line), "&Redirect to:".
  - "Let visitors save and &continue later" check box.
  - A read-only box, spoken as "On the site (read only)". It holds lines such as "CAPTCHA: on.", "Spam trap (honeypot): off.", "Email notifications: {n}." and "Form id on the site: {id or not published yet}."
  - OK (default), then Cancel.
- Announced after: "Form properties saved in the document."
- Undo: one Ctrl+Z step in the editor.
- F1: the purpose and each field's help. The read-only box says "What the site decides for this form: spam protection, notifications and where it is published. Read it line by line; it changes nothing here."
- Cancel: silent.
- Code: forms_commands.py (`cmd_properties`, `_set_properties`), forms_dialogs.py (`ask_properties`).
- Review notes:
  - Emptying the Title is silently ignored: the old title is kept, with no message.
  - The read-only box's label "On the site (read only):" has no access key, so the only way to reach the box is Tab.
  - It says "saved in the document" even when nothing changed.

### Tools > Forms > Form Payments Setup, Insert Payment Field, Verify Payment Setup

- How to reach them: Tools > Forms > Form Payments &Setup / Insert Payment Fi&eld / &Verify Payment Setup. No keys. Dimmed outside a form document.
- Gates, in order:
  - In QUILL only, the Form Payments feature: "Turn on Form Payments in Features before using this command."
  - A form must be in front.
  - When the form source has errors: "Fix the form's source errors with Check This Form first."
- Form Payments Setup: a dialog titled "Form Payments Setup". Purpose: "Configure this form locally. Publish Form sends it to your site. Set provider credentials and webhooks in WordPress, then Verify Payment Setup." Fields:
  - "&Providers:" (Stripe; Stripe, then PayPal; PayPal; PayPal, then Stripe).
  - "&Currency:".
  - "&Mode:" (Payment, Donation).
  - "C&apture:" (Automatic, Manual).
  - "&Test mode" check box.
  - "&Statement descriptor:".
  - A Save in Form button (default), then Cancel.
- Turning Test mode off asks first, in "Use Live Payments": "After publishing, this form can charge real money on a live-configured site. Save live payment mode in this form?", with a "Use Live Mode" button.
- Setup announces:
  - Success: "Payment settings saved in this form. Publish Form sends them to the site."
  - A problem: "Payment setup was not saved. {problem}".
- Insert Payment Field:
  - If the form already has one: "This form already has its payment field. Edit that field's source."
  - Otherwise a dialog titled "Insert Payment Field". Purpose: "Add one checkout field. Defaults use Stripe in test mode; Form Payments Setup changes providers and currency. No card data is collected in QUILL." Fields: "&Label:" (Payment), "&Amount:" (25), "Donation mi&nimum:", "Donation ma&ximum:", then Insert and Cancel.
  - Announces "Inserted payment field. Check Form Payments Setup before publishing."
  - Bad numbers: "Enter a positive amount, #field-id, or donation; bounds are numbers."
  - Other problems: "Payment field was not inserted. {problem}".
- Verify Payment Setup:
  - A Safe Mode check, then the site choice.
  - A confirmation: "Read payment configuration and webhook readiness from {site} ({address})? Credentials are managed in that site's WordPress dashboard.", with a "Read Setup" button.
  - Then a report, "Payment Setup on {site}", with "Test mode", "Live mode" or "Mode not reported", plus "{provider}: configured, webhook ready" style lines.
- Undo: Setup and Insert are one Ctrl+Z step each. Verify reads only.
- F1: dialog purposes and field help. The Test mode check box: "Keep this on while testing. Turning it off allows real charges after publishing to a live-configured site."
- Code: forms_payments_commands.py, core/forms/payments.py, core/forms/payment_site.py.
- Review notes:
  - Insert Payment Field always adds the field at the end of the last page, whatever the caret position. Insert Form Field places items at the caret.
  - The Lite gate bypass is described under QUILL Lite differences.

### Tools > Forms > Publish Form

- How to reach it: Tools > Forms > P&ublish Form. No key. Dimmed outside a form document. Off in Safe Mode.
- Before anything is sent:
  - Readability: "Publish Form stopped: this form has {n} problems to fix first. Check This Form, in Tools, Forms, lists them with Go to It."
  - A site:
    - With no sites: "Connect a WordPress site first, with Connect a Site in File, WordPress."
    - With one site, or a form already published from this file, that site is used without asking.
    - Otherwise a "&Site:" choice, help "Which of your WordPress sites has QUILL Accessible Forms. Your default site is selected."
  - QAF is checked on the site. Without it: "Publish Form needs QUILL Accessible Forms on {site}, and the site does not offer it. Install and activate the plugin there, then try again."
- What opens, a new form:
  - A "&Publish as:" choice: "Live: people can fill it in wherever it is placed" or "Draft: on the site, but nobody can fill it in yet".
  - Then the confirmation "Publish {title} to {site} as a new form?", with a Publish button.
- What opens, an already published form:
  - "Update {title} on {site}? People who fill it in see the new version at once.", with an Update button.
  - If the site's copy changed after your last publish: "{title} was changed on {site} at {time}, after you last published it. Publish yours over it? QUILL keeps the site's copy on this computer as a previous version.", with a "Publish Over It" button.
  - Either way, a form with payments adds " Payment mode: {test payments only, or LIVE payments: real money}, {CURRENCY}, {providers}. QUILL will first read the site's payment and webhook readiness."
- Announced after:
  - "Published {title} on {site}, form {id}, live. Insert Form Into Page puts it on a page." ("Updated" for an update; "a draft" for a draft.)
  - If the site did not answer with an id: "{site} did not say whether it kept the form."
  - Failures are one plain sentence from the shared WordPress failure wording.
- Undo: none on the site. Before an update, the site's previous copy is kept on this computer.
- F1: the choice's help. The confirmation is a standard message box.
- Cancel: silent at each step.
- Code: forms_publish_commands.py, forms_site_base.py, core/forms/qaf_site.py, core/forms/published.py.
- Review notes:
  - After the first publish, Publish Form never asks for a site again: the stored link wins (`choose_site` returns the preferred site first). There is no route in the editor to publish the same form to a second site.
  - Nothing is spoken while QUILL reads the site and then publishes. The task names ("reading {site}", "publishing to {site}") are not announced, so on a slow site there is silence between the button and the result.

### Tools > Forms > Insert Form Into Page

- How to reach it: Tools > Forms > &Insert Form Into Page. No key. Never dimmed. Off in Safe Mode.
- Requires a WordPress page or post in front. Otherwise: "Insert Form Into Page works in a WordPress page or post. Open one with File, WordPress, then try again."
- If the page's site has gone: "The site this page belongs to is no longer in your list of sites. Connect it again with Connect a Site."
- What opens: an "Insert Form Into Page" choice with "&Form:". Each row reads "{title}, {n} responses[, status]". The form last published from this computer is selected. Help: "The forms on this site, with how many responses each has had. The one you published last from this computer is selected."
- Announced after:
  - "Inserted the {title} form, as {a block or a shortcode}. It shows on the page once the page is sent." A draft adds " It is a draft, so visitors see nothing until it is live."
  - A site with no forms: "{site} has no forms yet. Publish one with Publish Form, then insert it."
- Undo: one Ctrl+Z step in the editor (an insert at the caret).
- Code: forms_publish_commands.py (`cmd_insert_into_page`), core/forms/qaf_site.py (`placement`).

### Tools > Forms > Test on Site

- How to reach it: Tools > Forms > &Test on Site. No key. Dimmed outside a form document. Off in Safe Mode.
- Requires the form to be published: "This form is not on a site yet. Publish it with Publish Form, then Test on Site opens it there."
- A form with payments asks first, in "Test Payment on Site": "Read the published payment form on {site} and open its checkout in your browser? QUILL will refuse if the published form is not in test mode.", with a "Test Payment" button. A live-mode form is refused with "The published form is not in payment test mode. Publish a test-mode form to a test-configured site before trying checkout."
- Announced after:
  - When a page shows the form: "Opened {page}[, a {status} page] on {site}, where the form is." It opens in the browser.
  - When no page does: "No page on {site} shows {title} yet, so QUILL opened it in QUILL Accessible Forms on the site. Insert Form Into Page puts it on a page."
  - A draft adds " It is a draft, so only you can see it there."
  - Test payments add the test-card hint, for example "To pay in test mode, use Stripe's test card 4242 4242 4242 4242 with any future date and any three-digit code ... Never a real card."
- Code: forms_publish_commands.py (`cmd_test_on_site`, `_open_test`).

### Tools > Forms > Responses (the editor's Responses window)

- How to reach it: Tools > Forms > &Responses. Also WordPress key, then F (Ctrl+Alt+Shift+Grave, F). Works from any document. Off in Safe Mode.
- Which form:
  - From a published form document, its own site and form, with no question.
  - Otherwise the site choice, then a "Responses" choice with "&Form:" (help "Whose responses to read. Each form says how many it has had."). A site with no forms: "{site} has no forms yet, so there are no responses."
- When the form has none: "{title} on {site} has no responses yet."
- What opens: a list window titled "Responses to {title}". Purpose: "{n} responses to {title} on {site}, newest first. They stay on this computer only while this window is open." Tab order:
  - The "&Responses:" list. Each row gives the number, when it was sent and who sent it. Marked rows start with "Marked, ".
  - Buttons: Refresh &Payment Status, &Read (also Enter), &View..., &Find..., Mar&k, Export to &CSV..., Open as &Table..., Export to &Word..., Su&mmarise..., &Delete..., Say &New Count, then Close.
- What each button does:
  - Read: a report titled "Response {id}", one answer a line.
  - View: "View Responses" with "&View:": "List, newest first", "Grouped by date", "Grouped by place".
  - Find: "Find in Responses" with "&Find:". Announces "{n} responses with {words}." or "Every response."
  - Mark: toggles the "Marked, " prefix on the row. Nothing is spoken.
  - Export to CSV: a Save As titled "Export Responses to CSV", named "{title} responses.csv". Announces "Saved {n} responses to {file}."
  - Open as Table: the same as Export to CSV, then opens the file and closes the window.
  - Export to Word: with a row selected and more than one shown, asks "&Export:" ("Response {id} only" or "All {n} shown"). Then a Save As titled "Export Responses to Word". Announces "Saved {n} responses to {file}."
  - Summarise: asks "Send the answers in {n} responses to {title} to your chosen AI? They may include names, email addresses and anything else people wrote. QUILL asks every time.", with a "Send {n}" button. Then a report, "Summary of responses to {title}".
  - Delete: acts on the marked rows, or the selected row. Asks "Delete {n} responses to {title} on {site}? They go to the Trash in QUILL Accessible Forms.", with a "Delete {n}" button. Announces "{n} responses moved to the Trash on {site}."
  - Say New Count: announces "QUILL will now (or no longer) say how many new responses there are when you first use {site} in a session."
  - Refresh Payment Status: asks "Read the latest responses and payment status from {site}? This reads the site's webhook-confirmed state; it never captures a payment.", with a Refresh button. It closes the window and reopens it.
- Also spoken, once per site per session: the first time a site is used, "{site}: {n} new responses to {form}." when there are new responses (`announce_new_responses_once`).
- Undo: nothing on the site. Deleted responses go to QAF's Trash, which can be restored only in wp-admin.
- F1: the window purpose, the list help ("Each response: its number, when it was sent, who sent it and the form. Press Enter to read one.") and each button's help.
- Code: forms_responses_commands.py, forms_ai_commands.py (`summarise_responses`), forms_site_base.py, core/forms/responses.py.
- Review notes:
  - Access-key collision. The list label "&Responses:" and the button "&Read" both claim R in one window. Under GATE-14, Windows cycles between the two instead of pressing, so Alt+R may never press Read. The dialogs are built at runtime, so the static gate may not see it. Verify.
  - Refresh Payment Status is the first button in the bar, and is shown for every form, payment or not. The first Tab stop after the list is a payments command most forms never need.
  - Delete takes the rows out of the list before the site has answered. If the delete then fails, only the failure sentence is spoken, and the rows stay gone from the window until it is reopened.
  - Mark is silent. Whether the reader re-reads the changed row after `set_rows` is not certain. Listen for it.
  - From a published form document, Responses always opens that form. To read another form's responses you must first switch to a document that is not a form. Nothing says so.
  - This window and the Workbench's Responses do different jobs. The editor has Read, Find, Mark, Export, Summarise and Delete, but no Spam or Not Spam. The Workbench has Spam, Not Spam, Search on the Site and Saved Views, but no Delete and no Export of QAF responses. Someone handling spam and exports has to use both.

### Tools > Forms > Save As Web Page, Word Document, Large Print, Braille-Ready Text

- How to reach them: Tools > Forms > Save As &Web Page / Save As Wor&d Document / Save As &Large Print / Save As &Braille-Ready Text. No keys. Dimmed outside a form document. All local, and they work in Safe Mode.
- Before each export, the same readability check as Publish Form ("{command} stopped: this form has {n} problems to fix first. ...").
- Web Page:
  - A "Save As Web Page" question, "&Send answers to:". Help: "The web address the form sends its answers to, starting https://. Leave it empty for a form to print or read, which sends nothing."
  - A bad address: "That is not a web address. Start it with https://, or leave it empty."
  - Then a Save As. Announces "Saved {file}, a web page with {n} questions. It sends its answers to {address}." (or "It sends its answers nowhere").
- Word Document announces "Saved {file}, a Word form with {n} questions, lines to write on and boxes to check."
- Large Print announces "Saved {file}, a large-print Word document, 18 point and up, with {n} questions, lines to write on and boxes to check."
- Braille-Ready Text:
  - When the braille pack is installed, a "&Save as:" choice: "Braille-ready text, 40 cells a line (.txt)" or "Braille file, translated to UEB contracted (.brf)".
  - Announces "Saved {file}, braille-ready text with {n} questions, one a block." or "Saved {file}, a braille file in UEB contracted, with {n} questions."
  - Failures: "The braille translation came back empty. Nothing was saved." or "The braille translation did not work: {reason}. Nothing was saved."
- Any write failure: "QUILL could not save {file}: {reason}."
- Undo: not applicable. A file is written. The document is unchanged.
- Code: forms_export_commands.py, core/forms/interop_html.py, core/forms/export_word.py.

### Tools > Forms > Draft a Form, Plain Language, Suggest Autofill Hints

- How to reach them: Tools > Forms > Dr&aft a Form / Plain Lan&guage / Suggest Autofill &Hints. No keys. Draft a Form works from any document. The other two are dimmed outside a form document. All three are off in Safe Mode.
- Draft a Form:
  - A "Draft a Form" question, "&Describe the form:" (multi-line). Help: "A sentence or two: who fills it in, and what you need to know. Only this description goes to your chosen AI. You read the draft before it is used."
  - Then it announces "Draft a Form sends your description, and nothing else, to your chosen AI." and sends.
  - The answer is shown in a report, "Draft a Form: the proposal".
  - Then the confirmation "Use this draft of {n} questions? It will {replace the form in front, or save it as a new form}.[ It has {n} reading problems to fix.]", with a "Use It" button.
- Draft a Form, announced after:
  - Replacing: "The draft is in, {n} questions. Undo takes it out."
  - Saving: a "Save the Drafted Form" Save As, then "Saved {file}, a drafted form with {n} questions."
  - Unreadable: "The AI's draft could not be read as a form. Nothing was changed."
- Plain Language and Suggest Autofill Hints:
  - Each announces what it sends. Plain Language: "Plain Language sends the labels and help text of {n} questions to your chosen AI. No answers are sent." Suggest Autofill Hints: "Suggest Autofill Hints sends the labels and types of {n} questions to your chosen AI. No answers are sent."
  - Each shows "{command}: the proposal", then asks "Apply {n} rewordings (or suggestions)? It is one step, and Undo takes it all out.", with an Apply button.
  - After: "{n} rewordings applied. Undo takes them all out." or "{n} suggestions applied. ...".
  - Nothing to do: "Your AI found nothing to make plainer. Nothing was changed." / "Your AI suggested nothing usable. Nothing was changed." / "Every question that takes an autofill hint has one, and every format rule has help. Nothing to suggest."
  - Switched documents while waiting: "{command}: the form is no longer in front, so nothing changed."
  - AI failure: "{command}: the AI did not answer. {reason}."
- Undo: one Ctrl+Z step for each applied change.
- Code: forms_ai_commands.py, core/forms/ai_prompts.py.
- Review notes:
  - Draft a Form sends as soon as you press OK. Only a spoken sentence comes first, with no confirmation, which is acceptable because only your own description goes. Summarise asks every time, as it should, because it sends people's answers.
  - "The draft is in ... Undo takes it out" replaces the whole form, including any rules or properties you wrote. The confirmation says "replace the form in front", which is honest, but it is a large single step.

### Workbench: the Forms node and its rows

- How to reach it: in the WordPress Workbench, open a site in the tree, then Forms. Under it are Responses and Held as Spam (Held as Spam is not on the site's home page, `home=False`). The Attention area also has Form Responses and a mixed Held as Spam (comments and form entries).
- Rows:
  - The Forms list has one row per form, with the columns form, plugin, entries and status.
  - Responses and Held as Spam have one row per response, with the columns form, plugin, status and when. The status words are "Received", "Held as spam" and "Trash".
  - QAF responses are read for each form, newest first, at most 3 pages a form and at most 300 in all (`_MAX_ENTRIES`).
- Details pane:
  - A form: "{title}, {n} responses, {status}."
  - A response: "{form}, QUILL Accessible Forms, {site},[ held as spam] {date}." plus up to three answers. For a held QAF response it adds QAF's reason, for example "Held because: {reason} ({check} check, score {n} of {max})."
- A site with no form plugin answers: "{site} has no forms plugin QUILL can read. QUILL Accessible Forms and Gravity Forms are found by their REST routes; this site lists neither."
- F1 (node help):
  - Forms: "The site's forms, from every form plugin QUILL reads."
  - Responses: "Responses to the site's forms."
  - Held as Spam: "Form responses held as spam."
  - Attention > Form Responses: "New form responses, from every site with a form plugin QUILL reads."
  - Attention > Held as Spam: "Comments and form entries a site doubted. Ctrl+Shift+A releases one."
  - The form row: "A form. Enter lists its responses."
  - The response row: "A form response. Enter reads it in full. On Gravity Forms, the context menu also has Notes, Star, Mark Read and Resend Notifications, and Properties changes its answers."
- Code: core/wordpress/workbench_forms.py, workbench_tree.py, workbench_node_help.py.
- Review notes:
  - Four nodes say "Responses" or "Held as Spam" in two places each. Forms > Responses and Attention > Form Responses are the same thing under two names. Forms > Held as Spam and Attention > Held as Spam share a name and differ in scope (the Attention one also has comments).
  - The 300-row and 3-page caps cut the list silently. A busy form shows fewer responses than its count, and nothing says the list is partial.
  - The response row's help mentions only Gravity Forms extras. It never says that Ctrl+Shift+S marks spam and Ctrl+Shift+A releases.

### Workbench: Show Its Responses (on a form row)

- How to reach it: Enter on a form row (the row's default). Also the context menu (Applications key or Shift+F10) > Show Its Responses.
- What it does: selects the site's Forms > Responses node, filtered to `form:"{title}"`.
- F1: ActionRow help "The form's responses."
- Code: wordpress_workbench_commands.py (`do_show_entries`).
- Review notes:
  - The filter goes by the form's title, not its id. Two forms with the same title, or a title that is part of another title, may share one filtered list. This is plausible from the code; verify how the filter matches.
  - It shows only Received responses. Held-as-spam responses to the same form are in a different node, and nothing tells you they exist.

### Workbench: Change Form Status (QAF form row)

- How to reach it: the form row's context menu > Change Form Status.... Keyless: "A form opens or closes a few times a year (rule 9)."
- What opens: a choice titled "Change Form Status - {title}", with "&New status:". The rows are the two statuses the form is not in now: "a draft, not shown to visitors", "open, taking responses", "closed, shown but not taking responses". Help: "Whether the form takes responses."
- Then a preview titled "Change Form Status". It has a "&Summary:" box ("{title} on {site} becomes {new}.") and an "&Each change:" list, for example "{title} on {site}: open, taking responses becomes closed, shown but not taking responses.", "Anyone who opens a page with it can no longer send a response." and "Its questions and past responses are not changed." Buttons: Change Status (default), then Cancel.
- Announced after: "{title} on {site} is {phrase}." The list refreshes.
- Failure: the site's own sentence (the Workbench's failure handler), or "That did not work."
- Undo: none. Nothing is recorded in Change History, so Ctrl+Z does not undo it.
- Without permission: the row is tier WRITE, with no capability named. Under Read Only or Organize access it says "Workbench access on {site} is {words}. Site > Workbench Access changes it.", and in Safe Mode "Safe Mode is on, so the Workbench only reads." A WordPress role QAF refuses is reported only as the site's error after sending.
- A Gravity Forms row: "That is a QUILL Accessible Forms command; choose one of its forms."
- F1: ActionRow help "Draft, open or closed, after a preview. QUILL Accessible Forms only."; the preview's help.
- Code: wordpress_workbench_forms_site.py, core/wordpress/workbench_forms_site.py, workbench_plugin_actions.py.
- Review notes:
  - The preview's summary uses the raw status word ("becomes inactive", "becomes active") while the lines and the result use the friendly phrase ("closed, shown but not taking responses"). Two vocabularies in one preview.
  - There is no undo, and no Change History entry. A Ctrl+Z pressed afterwards undoes whatever was recorded before, which may be an earlier spam mark, not this status change. This is plausible from the `_record` and history design; verify.

### Workbench: Form Settings (QAF form row)

- How to reach it: the context menu > Form Settings.... Keyless: "A form's settings are set when it is made (rule 9)."
- What opens:
  - The settings are read in the background first.
  - Then a choice titled "Form Settings - {title}", with "&Settings (Enter changes one):". Each row is "{setting}: {value}". Lists and objects are left out ("Lists such as conditional logic are changed in the form builder.").
  - Then a question with the setting's name as its label. Help: "Its new value: on or off for a switch, a number for a count."
  - Then a preview titled "Form Settings", with lines "{title} on {site}: {setting} is {old} and becomes {new}." and "Every other setting is sent back as it is. Visitors see the change at once." The button is Change Setting.
- Announced after:
  - "Changed {setting} on {title}."
  - Errors: "This setting is on or off. Nothing was changed." / "This setting is a whole number. Nothing was changed." / "That is its value already. Nothing was changed." / "{title} returned no settings QUILL can read."
- Undo: none. Not in Change History.
- Without permission: as Change Form Status (tier WRITE, no capability named).
- Code: wordpress_workbench_forms_site.py (`do_form_settings`), core/wordpress/workbench_forms_site.py.
- Review notes:
  - Settings are shown by their raw keys with underscores turned into spaces (for example "save continue enabled"). They are not friendly labels.
  - Only one setting can be changed per trip. Changing three means three round trips through the menu.

### Workbench: Saved Views and Search Responses on the Site (QAF form row)

- How to reach them: the context menu > Saved Views / Search Responses on the Site.... Keyless. Saved Views: "Saved views are read now and then (rule 9)." Search: "The filter box finds within loaded rows; this asks the site."
- Saved Views:
  - A report titled "Saved Views - {site}", one line per view: "{name}: {kind} view of {form}, {status}".
  - With none: "This site has no saved views of its responses."
- Search Responses:
  - A question titled "Search Responses - {title}", with "&Words:" (help "Found in any answer, on the site.").
  - Then a report titled "Responses with {words} - {title}", with lines "Response {id}, {date}: {answers}", or "No response has those words."
- Undo: not applicable. Both only read.
- Code: wordpress_workbench_forms_site.py, core/wordpress/workbench_forms_site.py.
- Review notes:
  - Saved Views is offered on one form's row but lists every view on the site. Views of other forms are named "form {id}", because only this form's title is known.
  - Search results are a read-only report, not rows. You cannot mark a found response as spam, or open it, from there. It searches Received responses only (`status: active`), so held spam is never found.

### Workbench: Delete Form (QAF form row)

- How to reach it: the context menu > Delete Form.... Keyless: "Deleting a form deletes its responses: never a bare key (rule 4)." Shift+Delete, the Workbench's Delete Permanently key, is not on form rows.
- What opens: a preview titled "Delete Form". Summary: "Delete {title} and its responses from {site}." Lines:
  - "{title} is deleted from {site}, for good: the plugin keeps no Trash for forms."
  - "Its {n} responses, their notes and uploaded files are deleted with it."
  - "Pages that show it will show nothing in its place. Export the responses first (Tools > Forms > Responses) if you need them."
  - "To go ahead, you will type the form's name, {title}, exactly."
  - Button: "Go On to Confirm".
- Then a question titled "Delete Form": "&Type the form's name, {title}, to delete it:". Help: "The form is deleted only when this is its name exactly. Cancel deletes nothing."
- Announced after: "Deleted {title} and its responses from {site}." On a mismatch: "The name typed did not match, so nothing was deleted."
- Undo: none, and the preview says so.
- Without permission: tier DESTRUCTIVE, no capability named. Under anything but Full access, the access sentence.
- Code: wordpress_workbench_forms_site.py (`do_delete_form`).
- Review notes:
  - Pressing Cancel at the name question also says "The name typed did not match, so nothing was deleted." That reads as an error for a deliberate cancel.
  - "Export the responses first (Tools > Forms > Responses)" sends a Workbench user to the editor's menu, because the Workbench cannot export QAF responses itself.

### Workbench: Not Spam and Spam (on a response row)

- How to reach it: the response row's context menu > Not Spam / Spam. Also Item > Approve, or Not Spam (Ctrl+Shift+A) and Item > Spam (Ctrl+Shift+S), on one row or a selection.
- What it does:
  - QAF: `POST qaf/v1/entries/{id}/spam` or `.../not-spam`, which tells QAF's spam providers and sends a released response's notifications. An older QAF answers 404 or 405, and only the status is set, "which moves it but tells nobody".
  - Gravity Forms: the whole entry is sent back with its status changed.
  - There is no preview or confirmation (tier ORGANIZE).
- Announced after:
  - "Not spam: {n} items on {site}, and the site was told." when every selected row was held as spam.
  - Otherwise "{N} items approved on {site}." or "{N} items marked as spam on {site}."
  - Partial failure appends " Not changed: {reasons}".
  - With no response or comment selected: "Choose a comment or a form entry."
- Undo: Ctrl+Z (Edit > Undo WordPress Change) marks the responses back the other way, and is recorded in Change History (Ctrl+Shift+H).
- Without permission: needs "forms", which maps to `edit_posts`. Under Read Only access: "Workbench access on {site} is {words}. Site > Workbench Access changes it." For a role below Contributor: "Editing posts needs the Contributor role or higher. You are a Subscriber on {site}."
- F1: ActionRow help "Back to the form's entries. Ctrl+Shift+A." and "Hold it as spam. Ctrl+Shift+S."
- Code: wordpress_workbench_commands.py (`_moderate`, `do_approve`, `do_spam`), core/wordpress/workbench_forms.py (`set_entry_spam`), core/wordpress/workbench_qaf_spam.py (`mark_entry`).
- Review notes:
  - "and the site was told" is said even when an older QAF only moved the response and told nobody. `mark_entry` returns the providers it told, and nothing reads that list.
  - The wording is borrowed from comments. Marking a response spam says "1 item marked as spam", and Not Spam on a response that was not held says "1 item approved". Responses are never "approved".
  - Item > Unapprove (Ctrl+Shift+U) on a response acts as Not Spam but announces "1 item unapproved on {site}."
  - Undo reverses every selected response, including any whose change failed. After Not Spam on a response that was already Received, Ctrl+Z marks it as spam. Plausible from `_moderate`; verify.
  - The permission refusal talks about "Editing posts" when the person is marking a form response. That is accurate to the capability, but confusing.
  - QAF responses also show Notes... and Resend Notifications... in the context menu (the Gravity rows are shared). Both refuse with "That is a Gravity Forms command. Choose a Gravity Forms form, entry or feed; QUILL Accessible Forms keeps no notes, feeds or notifications." Star or Unstar and Mark Read or Unread do work on QAF responses ("Starred {n} entries on {site}." and similar, with undo). The node help says these four are Gravity Forms only.

### Workbench: the site row's QAF spam commands

- How to reach them: a site row's context menu > Form Spam Questions... / Form Spam by Week. Both keyless. Questions: "A site's own questions are written once and changed now and then, from the site's context menu (rule 9); the settings beside them are on Alt+Shift+Enter." Weeks: "Read now and then, when spam is in question (rule 9); the weekly Watch says each new week's numbers without being asked."
- Form Spam Questions:
  - Read in the background, then a choice titled "Form Spam Questions - {site}" with "&Questions (Enter on one changes or removes it):". The first row is "Add a question...", then "{question} Right answers: {answers}." for each.
  - Add: "&Question:", then "&Right answers (a semicolon between):", then a preview titled "Add a Spam Question" with an Add Question button. Announces "Added the question. The site asks it now: {question}" or "The site took the question, but reading the bank back, it is not there."
  - On an existing question: "&What to do:" with "Change its words...", "Change its answers..." or "Remove it...". Each change has its own preview: "Change a Spam Question" ("Was: ...", "Becomes: ...") or "Remove a Spam Question". Announces "Changed the question, and read it back from the site." or "Removed the question; the site no longer asks it." (or the matching read-back failure).
  - A site not on qaf/v1 gets the namespace note, for example "This site runs the older BITS Accessible Forms (baf/v1). Its spam settings can be read here, but are changed in wp-admin until the site has QUILL Accessible Forms."
- Form Spam by Week:
  - A report titled "Form Spam by Week - {site}": the namespace note, then "This week, {week}: {n} asked, {n} answered, {n} answered wrongly, {n} sent anyway." and the earlier weeks. With none: "No weeks yet."
  - The weekly Watch says, without being asked, "Form spam questions on {site}, week {line} Up from {n} asked the week before." (or Down).
- The site's Properties, Spam page (Alt+Shift+Enter per the row help):
  - Shows QAF's checks as check boxes, the limits as numbers, "Ask a question" as a choice, the question kinds as check boxes, "Offer Send Anyway after this many wrong answers", and a write-only "New OOPSpam key" field.
  - OK or Apply shows a preview titled "Change Form Spam Settings", with a Save Settings button.
  - Then it announces "Saved {n} spam settings, and read them back from the site." or "Saved ..., but reading them back, {problems}. Check Settings, Spam in wp-admin."
  - A conflict: "The spam settings were changed on the site since they were read, so nothing was sent. Open the site's Properties again to see them as they are now."
  - Without permission, the fields are read only, with the reason as their F1 help: "Changing the spam settings needs the site's Manage Options capability, or QUILL Accessible Forms' own Manage Settings."
- Undo: none for questions or settings. Not in Change History.
- Without permission: both rows are tier WRITE (Questions) or READ (Weeks), with no capability named. The site's own refusal is spoken by the failure handler.
- Code: wordpress_workbench_qaf_spam.py, core/wordpress/workbench_qaf_spam_edit.py, core/wordpress/workbench_qaf_spam.py.
- Review notes:
  - Cancelling the Question prompt of Add a question announces "A question needs its words and at least one right answer. Nothing was added." That is a reproach for a deliberate Cancel.
  - The Spam page's save remembers the revision read when the sheet opened. A second Apply in the same sheet, after a first that succeeded, sends the old revision and is likely to be refused as a conflict caused by your own first save. Plausible from `site_sheet_with_spam`; verify.
  - `on_save` returns True as soon as the background save starts. The sheet can close before a conflict is reported, and the edits typed into it are lost with it.
  - These two commands sit on every site row, including sites with no QAF. There they answer "This site has no QUILL Accessible Forms." only after a background read.

### Workbench: Copy commands between QAF and Gravity Forms

- Copy as a Gravity Form... is on a QAF form row ("A new Gravity Forms form from this one, after a preview of what cannot carry over"), on a site that has Gravity Forms too. Copy as a QUILL Accessible Form... is on a Gravity Forms form row.
- Copy to Site... and Properties... (Alt+Enter) are the Workbench's shared rows on a form row.
- See the Gravity Forms section for how the copy commands work.
- Code: core/wordpress/workbench_gravity_actions.py (`GRAVITY_QAF_ROWS`, `GRAVITY_BUILD_ROWS`).

## Gravity Forms

Gravity Forms lives under each site's Forms node, beside QUILL Accessible Forms (QAF). QUILL finds it only when the site's REST index lists the gf/v2 namespace. You can work through responses with four Ctrl+Alt chords (Notes, Star, Read, Resend), mark them spam or not spam, and change a response's answers in its Properties sheet. On forms, you can read feeds and results, send a test entry, change one field's control, edit or build a whole form in QUILL's own form editor, and copy a form between Gravity Forms and QAF. Every change that reaches the site is previewed. Most changes have a Ctrl+Z. The commands without a chord sit under Item, Gravity Forms (Alt+I, then F), and each has an access letter. Note for the review: in git, every Gravity Forms module and its tests are still untracked files (status "??"), the entries mixin included.

### Where Gravity Forms appears in the tree

- Sites > site > Forms: one row per form from every form plugin QUILL reads. Columns: form, plugin, entries, status. A Gravity Forms row has the row type "gravity_form" and the plugin cell "Gravity Forms". Its status cell is always "active", whatever the form's real state (hard-coded in workbench_forms.py, _gravity_rows).
- Sites > site > Forms > Responses: entries from every form plugin, newest first. Columns: form, plugin, status ("Received", "Held as spam" or "Trash"), when. For Gravity Forms, at most 300 rows, read one page unless the Filter Builder sent conditions to the site.
- Sites > site > Forms > Held as Spam: the same columns. Entries whose status is spam.
- Sites > site > Forms > Feeds: every add-on feed of every Gravity Forms form. Columns: name, form, addon, status ("Active" or "Inactive"). The details pane says, for example, "Newsletter, a Mailchimp feed on Contact, active. It runs when this form is submitted."
- Sites > site > Forms > Results: quiz, poll and survey results. One row per answer. Columns: form, question, answer, count, share ("40 percent"). The details pane holds the whole question as one sentence: "Favourite colour, 12 responses: Red 5, 42 percent; Blue 7, 58 percent." While Gravity Forms is still counting, the only row says: "Gravity Forms is still counting the results of {form}. Press F5 in a moment."
- A site with no forms plugin: the Forms node's error is "{site} has no forms plugin QUILL can read. QUILL Accessible Forms and Gravity Forms are found by their REST routes; this site lists neither."
- Node F1 (workbench_node_help.py): Forms "The site's forms, from every form plugin QUILL reads."; Responses "Responses to the site's forms."; Held as Spam "Form responses held as spam."; Feeds "Each Gravity Forms form's add-on feeds, such as Mailchimp, Stripe or Zapier, and whether each is active. A form's Show Its Feeds lands here filtered to it."; Results "Quiz, poll and survey results from Gravity Forms: a row per answer with its count and share, and the question's results as one sentence in the details pane."
- Review notes: a response row's title is "{form title} entry", so every response to one form has the same name. "Added a note to Contact entry on Example Site" never says which entry. The entry number is in the Properties sheet but not in any spoken outcome.
- Review notes: the list shows no column that tells two responses apart (no submitter name or email). Only the details pane carries the first three answers.

### Context menus on Gravity Forms rows (order as shown)

- A response (form_entry), 7 rows plus Properties, so there is no More submenu: Read in Full (default, Enter), Not Spam, Spam, Notes..., Star or Unstar, Mark Read or Unread, Resend Notifications..., Properties....
- A form (gravity_form), 9 rows plus Properties, so 6 show and 3 go under More: Show Its Responses (default), Change a Field Type..., Show Its Feeds, Show Its Results, Test This Form..., Edit Form..., Properties..., then More: New Gravity Form..., Copy as a QUILL Accessible Form..., Copy to Site....
- A feed (gravity_feed): Read in Full (default), Activate or Deactivate..., Rename..., Delete Permanently..., Properties....
- A result (gravity_result): Read in Full (default), Properties....
- A QAF form row on a site that has Gravity Forms too also offers "Copy as a Gravity Form...".
- Review notes: New Gravity Form is under More on every form row, but it acts on the site, not on the form you are on. On the form menu it is the only row that ignores the selection.
- Review notes: the form row's F1 sentence says "Enter lists responses; the context menu shows its feeds and results, tests it, and changes a field type." It does not mention Edit Form, New Gravity Form or the two Copy commands.

### The Item menu for Gravity Forms

- Four rows sit on the Item menu itself, each with a chord and no access letter: "Entry Notes..." Ctrl+Alt+N, "Star or Unstar Entry" Ctrl+Alt+F, "Mark Entry Read or Unread" Ctrl+Alt+U, "Resend Notifications..." Ctrl+Alt+I.
- Item > Gravity &Forms (Alt+I, then F) holds the rest, each with an access letter: Show Its &Feeds (F), Show Its &Results (R), &Test This Form... (T), Change a Field T&ype... (Y), &Edit Form... (E), Ne&w Gravity Form... (W), Copy as a &QUILL Accessible Form... (Q), Copy QAF Form as a &Gravity Form... (G), then a separator, &Activate or Deactivate Feed... (A), Re&name Feed... (N).
- Review notes: the four chord rows have no access letter, so walking Item by letter cannot reach them. Every other Item row has one.
- Review notes: Ctrl+Alt+F for Star and Ctrl+Alt+I for Resend are hard to guess. The help says "Star it to come back to. Ctrl+Alt+F." and gives no hint why F (flag) or I.
- Review notes: the labels differ between the two menus: "Notes..." on the context menu and "Entry Notes..." on Item; "Star or Unstar" against "Star or Unstar Entry"; "Copy as a Gravity Form..." against "Copy QAF Form as a Gravity Form...". A listener who learns one name hears another.

### Permissions (applies to every Gravity Forms command)

- Each command first checks that it is on a Gravity Forms row. On any other row it says: "That is a Gravity Forms command. Choose a Gravity Forms form, entry or feed; QUILL Accessible Forms keeps no notes, feeds or notifications." Star and Mark Read are the exception: they also work on QAF responses.
- Then the Gravity Forms permission. gform_full_access (what an administrator has) counts for all of them. The sentence is "{words} needs the Gravity Forms permission {capability with spaces}. You are {role} on {site}." For example: "Reading an entry's notes needs the Gravity Forms permission gravityforms view entry notes. You are Editor on Example Site."
- The permission each command needs (NEEDS and CAPABILITIES in workbench_gravity_actions.py and workbench_gravity.py): Notes, gravityforms_view_entry_notes; adding a note, gravityforms_edit_entry_notes; Star, Read and Resend, gravityforms_edit_entries; feed Activate, Rename and Delete, gravityforms_edit_forms; Edit Form, gravityforms_edit_forms; New Gravity Form and Copy as a Gravity Form, gravityforms_create_form; Change a Field Type, gravityforms_create_form.
- Then the Workbench access tier. The sentence is "Workbench access on {site} is {words}. Site > Workbench Access changes it." In Safe Mode it is "Safe Mode is on, so the Workbench only reads." Under View As Role it is "You are viewing {site} as {Role}, which only reads. Site > View As Role ends it."
- A row the person may not use is greyed on the menu. Its chord speaks the refusal instead.
- Review notes: "You are Editor on" has no article. The core permission sentence elsewhere says "You are an Editor on". Two styles of the same message sit side by side in one window.
- Review notes: Change a Field Type checks gravityforms_create_form, but Edit Form, which can change every field, checks gravityforms_edit_forms. Someone who may edit forms but not create them can rebuild a whole form in the editor, yet is refused the smaller job.
- Review notes: Not Spam and Spam on a response check the WordPress capability edit_posts (requirement "forms"). They do not check a Gravity Forms permission, unlike every other Gravity entry command.

### Read in Full (response, feed, result)

- How to reach it: Enter on the row, or the first row of the context menu.
- What it does: moves focus to the details pane. For a response, the pane reads "{form}, Gravity Forms, {site}, {when}." followed by up to three answers, each "{field id}: {first 80 characters}". A held one adds " held as spam".
- Review notes: the details pane names answers by field number ("3: Jane"), not by question label. Properties does better (labels from the form). The pane is what a listener hears first.
- Code: workbench_forms.py (_entry_row, _answers_sentence).

### Not Spam (response)

- How to reach it: context menu "Not Spam"; Ctrl+Shift+A; Item > "&Approve, or Not Spam" (Alt+I, A).
- What opens: nothing. It runs on every selected comment and response at once.
- What it does: for Gravity Forms it sends the whole entry back with status "active" (PUT gf/v2/entries/{id}).
- Announced after: if every selected row was spam, "Not spam: {n} item(s) on {site}, and the site was told." Otherwise "{N} item(s) approved on {site}." Failures add " Not changed: {up to three reasons}".
- Undo: Ctrl+Z, which sends spam again: "Put {n} items back as they were."
- F1 (row): "A form response. Enter reads it in full. On Gravity Forms, the context menu also has Notes, Star, Mark Read and Resend Notifications, and Properties changes its answers."
- Without permission: the edit_posts sentence, for example "... needs the Contributor role or higher. You are a Subscriber on {site}." (the lowest role that has edit_posts).
- Keyless: it has a chord, Ctrl+Shift+A.
- Code: wordpress_workbench_commands.py (_moderate), workbench_forms.py (set_entry_spam).
- Review notes: "and the site was told" is true for QAF, which reports to its spam providers. For Gravity Forms only the status changes; no spam service hears about it. The sentence overclaims.
- Review notes: on a response that is not spam, the outcome says "approved", a comment word that means nothing for a form entry.
- Review notes: set_entry_spam sends row.raw, the entry as it was when the list loaded. It does not read the entry again first, unlike Star, Read and answers. An answer changed in wp-admin since the list loaded is overwritten with the old copy. This is a silent data-loss risk.
- Review notes: Unapprove (Ctrl+Shift+U, on the Item menu) on a response also sets it not spam, while its label says "Back to waiting".

### Spam (response)

- How to reach it: context menu "Spam"; Ctrl+Shift+S; Item > &Spam (Alt+I, S).
- What it does: sends the whole entry with status "spam". There is no preview.
- Announced after: "{N} item(s) marked as spam on {site}." plus any " Not changed: ...".
- Undo: Ctrl+Z puts it back as active.
- Code: as Not Spam.
- Review notes: the same stale-copy risk as Not Spam. The help "Hold it as spam." is the only explanation; nothing says whether Gravity Forms then hides it from the Responses node (it moves to Held as Spam after the refresh).

### Notes... (response)

- How to reach it: context menu "Notes..."; Ctrl+Alt+N; Item > "Entry Notes..." (no access letter).
- What opens, when you may add notes: a preview dialog titled "Notes - {form} entry". Tab order: Summary (read-only text, "{n} notes on {form} entry on {site}."), "Each change:" list (one note a line, oldest first, "{who}, {date}: {text}", with "(note type)" when not a user note, or "This entry has no notes yet."), then the default button "Add a Note...", then Cancel.
- Choosing Add a Note... opens "Add a Note - {form} entry": a multiline "Note:" box, OK (default) and Cancel. Help: "A note on this entry, kept by Gravity Forms on {site} and signed as you. Visitors never see it."
- What opens, when you may only read: a report window "Notes - {form} entry" with the Report text, Copy All and Close. The last line is the reason, for example "Adding a note to an entry needs the Gravity Forms permission gravityforms edit entry notes."
- Announced after: "Added a note to {form} entry on {site}." An empty note sends nothing and says nothing.
- Undo: Ctrl+Z deletes the note: "Removed the note from {form} entry."
- Cancel: closing the preview leaves without adding.
- Keyless: it has a chord.
- Code: wordpress_workbench_gravity_entries.py (do_entry_notes, _add_note), workbench_gravity.py (read_notes, note_lines, add_note).
- Review notes: the notes are shown in a dialog built for change previews. The list is labelled "Each change:" and its help says "One line for each thing the change creates, replaces or skips". Both are wrong for reading notes, and the listener hears them every time.
- Review notes: Enter in the notes list presses the default button "Add a Note...". A person reading notes with Enter in mind ends up in the Add a Note box.
- Review notes: long notes are one list row each; a listbox truncates nothing, but there is no way to read one note in a text box or copy it, except the read-only report version for people who cannot add.

### Star or Unstar (response)

- How to reach it: context menu "Star or Unstar"; Ctrl+Alt+F; Item > "Star or Unstar Entry".
- What opens: nothing. It works on every selected response from one site. A Gravity Forms entry is read again and sent whole with is_starred changed.
- Direction: the first selected row decides. If it is not starred, every selected row is starred, even ones already starred.
- Announced after: "Starred {n} entries on {site}." or "Unstarred 1 entry on {site}." Mixed sites: "Change entries from one site at a time." Nothing chosen: "Choose a Gravity Forms or QUILL Accessible Forms response first."
- Undo: Ctrl+Z: "Put {n} entries back as they were."
- Also on QAF responses.
- Code: wordpress_workbench_gravity_entries.py (_toggle_flag), workbench_gravity.py (set_entry_flag).
- Review notes: the list has no Starred column, so after the refresh nothing tells a listener which rows are starred except Properties.

### Mark Read or Unread (response)

- How to reach it: context menu "Mark Read or Unread"; Ctrl+Alt+U; Item > "Mark Entry Read or Unread".
- Behaviour, outcomes and undo: as Star. Spoken "Marked read {n} entries on {site}." or "Marked unread 1 entry on {site}."
- Review notes: "Marked read 3 entries" reads oddly; "Marked 3 entries read" would be natural English. No Read column either.

### Resend Notifications... (response)

- How to reach it: context menu "Resend Notifications..."; Ctrl+Alt+I; Item > "Resend Notifications...".
- What opens: first a check-box dialog "Resend Notifications - {form} entry". Its group is "Notifications to send again", one check box per notification, each "{name}: to {recipients}", with ", sent on {event}" for one not sent on submission and ", turned off" for an inactive one. Recipients are worked out for this entry: "the address in Email, jane@example.com", "the site's admin email", routing as "{email} when {field} is {value}", plus ", with a blind copy to {bcc}". Active submission notifications start checked. OK (default), Cancel.
- Preview: "Resend Notifications". Summary "Send {n} notification(s) again for {form} entry on {site}?". Lines: each chosen notification, then "Each person listed gets the email again, as if the form had just been sent." Button "Resend".
- Announced after: "Gravity Forms sent {n} notification(s) again for {form} entry: {names}." If it sent none: "Gravity Forms sent none for {form} entry. A notification's own conditions may not match this entry." No notifications on the form: "The form behind {form} entry has no notifications to send."
- Undo: none. The change is recorded without an undo.
- Code: wordpress_workbench_gravity_entries.py (do_resend_notifications), workbench_gravity.py (entry_notifications, resend_notifications).
- Review notes: because it is recorded with no undo, Ctrl+Z straight after says "{that sentence} cannot be undone." (history.py), with a doubled full stop ("Admin Notification. cannot be undone."). It also blocks Ctrl+Z for every change before it, since the history never steps past an un-undoable change.
- Review notes: unchecking every box and pressing OK returns an empty list. The code treats that as Cancel and says nothing.

### Properties on a response, and editing its answers

- How to reach it: Alt+Enter on a Gravity Forms response, or Properties... (last row of the context menu), or Item > &Properties... (Alt+I, P).
- What opens: a sheet titled "{form} entry Properties - {site}", with three pages:
  - General: Entry number, Form, Status, Received, Last changed, Sent from (a link) (all read only), then two check boxes, Starred and Read.
  - Answers: one editable field per answer, in field order (1, 1.3, 2, 10). Each is labelled with the form's admin label or label, and a part of a field gets "{field}, {part}" (for example "Name, First"). When two answers share a label, the label adds " (field {id})". Answers longer than 80 characters or with a line break get a multiline box. Help: "The visitor's answer to {label}. Saving previews the change, then sends the whole response back; Ctrl+Z puts the old answer back."
  - Notes: the notes, read only, one a line. If they cannot be read, the page shows the site's error or "Gravity Forms did not return the notes."
- Saving: if nothing changed, "Nothing changed on this entry." Changed answers get a preview, "Change Answers", whose summary is "Change {n} answer(s) in {form} entry on {site}? Gravity Forms keeps no earlier version, so Ctrl+Z is the way back." Lines: "{label}: {old or (empty)} becomes {new or (empty)}". Button "Change". Starred and Read changes alone are sent with no preview.
- Conflict check: just before writing, the entry is read again. If its date_updated moved, or any answer being changed no longer says what the sheet showed, nothing is sent and QUILL says: "This response was changed in Gravity Forms after QUILL read it. Nothing was sent; open its Properties again and make the change there."
- Announced after: "Saved {n} change(s) to {form} entry on {site}."
- Without permission: "Changing an entry needs the Gravity Forms permission gravityforms edit entries." (or the Workbench access sentence), said on save. The sheet's fields are locked earlier only by the WordPress capability edit_posts.
- Undo: Ctrl+Z sends the old answers and flags back: "Put {form} entry back as it was." The undo does not check date_updated.
- Status: built. The core is workbench_gravity_answers.py (answer_ids, answer_labels, set_answers) and the UI is gravity_sheet and gravity_entry_save in wordpress_workbench_gravity_entries.py, wired through wordpress_workbench_sheets.py. Tests exist in tests/unit/core/wordpress/test_wp_workbench_gaps_core.py and tests/unit/ui/wordpress/test_wp_workbench_gaps.py. Not yet in the engineering log (docs/design/wordpress.md has no entry for it); wp_missing.md still lists it as missing.
- Code: wordpress_workbench_gravity_entries.py, workbench_gravity_answers.py, wordpress_workbench_sheets.py.
- Review notes: a choice answer (drop-down, radio, check box part) is a plain text box. Nothing offers the form's choices, so a typo stores a value the form never allowed. The same goes for dates and numbers: no check before sending.
- Review notes: a check-box field's parts each become a field ("Toppings, Cheese"), and the value is the choice value, not "checked". An empty part means unchecked, which a listener must guess.
- Review notes: fields locked by edit_posts give a WordPress-role reason, then the save gives a Gravity Forms reason. A person can be told two different things for the same edit.
- Review notes: the undo sends without the date_updated check, so Ctrl+Z after someone else's later edit overwrites it.
- Review notes: the sheet's title is "{form} entry Properties", with no entry number. The number is only inside General.

### Properties on a feed or a result

- What opens: a read-only sheet titled "{Gravity Feed}" or "{Gravity Result}" (the kind, title-cased), with one General page. It has one multiline field per top-level key the site sent, labelled from the key ("Addon slug", "Meta", "Is active").
- Review notes: this is a raw dump. Meta is JSON text, and the key names are Gravity Forms' own. Nothing here is editable, although Rename and Activate exist on the menu.

### Properties on a form

- What opens: a form row is not one of the three Gravity sheet kinds, so it gets the generic sheet. That is the route's schema if OPTIONS answers, else a read-only list of every top-level key, with fields, notifications and confirmations as JSON text.
- Review notes: the sheet title comes from the row's title, which for a form row is its plugin cell, so the title is "Gravity Forms Properties - {site}", not the form's name. (The commands work around this with a replace; the sheet does not.)
- Review notes: the generic sheet is not where a form is edited (Edit Form is), but nothing on it says so.

### Show Its Responses (form)

- How to reach it: Enter on a form row, or the first context-menu row.
- What it does: selects Responses and puts the form's name in the filter.
- F1 (row): "A Gravity Forms form. Enter lists responses; the context menu shows its feeds and results, tests it, and changes a field type."
- Code: wordpress_workbench_commands.py (do_show_entries).

### Show Its Feeds (form)

- How to reach it: context menu "Show Its Feeds"; Alt+I, F, F.
- What it does: selects Forms > Feeds, puts form:"{title}" in the filter box, applies it, and moves focus to the list. Nothing is announced; the screen reader reads the list.
- On a non-Gravity row: "Choose a Gravity Forms form first."
- Keyless: "Once per question about a form; Enter-and-filter on Forms > Feeds."
- Code: wordpress_workbench_gravity_forms.py.
- Review notes: filtering by title means two forms with the same title share their feeds in the view.

### Show Its Results (form)

- How to reach it: context menu "Show Its Results"; Alt+I, F, R.
- What it does: as Show Its Feeds, on Forms > Results.
- Keyless: "Read after a poll closes, not daily; Forms > Results is one key."
- Review notes: a form with no quiz, poll or survey field adds no rows (load_results skips it), so the filtered list is empty and nothing from the Gravity Forms code says the form has nothing to count.

### Test This Form... (form)

- How to reach it: context menu "Test This Form..."; Alt+I, F, T.
- What opens: "Test This Form - {title}", a multiline "Test values, one input a line:" box filled with lines like "input_1: QUILL test", "input_2: test@example.com", "input_3_3: Quill". Help: "Each line is a Gravity Forms input and the value QUILL will send. Change any value after the colon; delete a line to leave that input empty." It adds " QUILL leaves these empty: {labels}." for captcha, upload, signature and administrative fields. OK and Cancel.
- Check first: the values go to Gravity Forms' validation route; nothing is saved. If refused, a report "Not Accepted - {title}" lists "{label}: {message}" lines; help "What Gravity Forms refused in the test values. Nothing was saved."
- Preview: "Submit a Test Entry". Summary "Send a test entry to {title} on {site}?". Lines: on a practice site, "{site} is a practice site, so the test entry costs nothing."; on a live site, "{site} is a live site. A practice site is better for tests: this entry is real, and its emails and feeds reach real people and services." Then "Gravity Forms already checked these values; nothing has been saved yet.", each "{label} ({input}): {value}", and "Ctrl+Z afterwards moves the test entry to Gravity Forms' Trash." Button "Submit Test Entry".
- Announced after: "Gravity Forms accepted the test entry to {title} on {site}, entry {id}." plus " It said: {confirmation}". If refused at submission: "Gravity Forms did not accept the test entry: {reasons}".
- Undo: Ctrl+Z: "Moved test entry {id} to the Trash."
- Keyless: "Run after editing a form, a few times a year (rule 9): a letter."
- Code: wordpress_workbench_gravity_forms.py, workbench_gravity_submit.py.
- Review notes: the edit box uses Gravity Forms' input names (input_3_3), not question labels. A listener cannot tell which line is which question until the preview, which shows labels. This is the biggest usability gap in Test This Form.
- Review notes: on a live site the warning is one line in a list. It is not a separate confirmation, and the default button still submits. Feeds such as Stripe or Mailchimp fire for real.

### Change a Field Type... (form)

- How to reach it: context menu "Change a Field Type..."; Alt+I, F, Y.
- What opens: "Change a Field Type - {title}", a list labelled "Field:", one row per field QUILL can convert, "{id}: {label} ({type name})". Help: "Choose a text, email, number or choice field in this Gravity Forms form." Then "Change Field Type", a list labelled "New control:" with all seven types ("Single line text (text)", "Paragraph text (textarea)", "Email address (email)", "Number (number)", "Drop-down list (select)", "Radio buttons (radio)", "Checkboxes (checkbox)"), starting on the current one.
- Preview: "Update Gravity Forms Field". Summary "Change {label} (field {id}) from {old} to {new}." Lines: "Site: {site}", "Form: {title}", "Kept: ...", "Adjusted: ..." (for example "added a starter choice so the new control can be filled in"), "Cannot carry over: ...", "QUILL will send the complete form, preserving its other fields and settings." Button "Update Form".
- Announced after: "Changed {label} in {title} on {site}." If the form reads back wrong: "{title} on {site} was saved, but it reads back differently: {problems} Ctrl+Z puts the form back as it was." Same type chosen: "The field already uses that control." No convertible fields: "{title} has no fields QUILL can convert." If the form changed while you reviewed: "{title} on {site} changed while you reviewed the conversion. Reopen the form and review the current fields."
- Undo: Ctrl+Z: "Restored {label} in {title}." It refuses if the form changed since: "{title} on {site} changed since this conversion. QUILL did not replace the newer form." Redo is offered.
- Without permission: "Changing a form's fields needs the Gravity Forms permission gravityforms create form. You are {role} on {site}." On a QAF row: "This is not a Gravity Forms form. QAF fields are changed in Form Outline."
- Keyless: "A form-design change made rarely (rule 9)."
- Code: wordpress_workbench_gravity_commands.py, workbench_forms.py (GRAVITY_FIELD_TYPES, plan_gravity_field_type_change, gravity_replacement_problems).
- Review notes: the type names here ("Single line text", "Drop-down list") differ from the form editor's ("Single Line Text", "Drop Down"). One product, two vocabularies.
- Review notes: "Cannot carry over" lists raw Gravity Forms keys ("enableChoiceValue", "randomize") that mean nothing to a listener.
- Review notes: the help for the editor's Type box points here to change a type ("Change a Field Type on the form changes it later"), but only 7 of the editor's 18 types convert. A Phone or Date field never appears in the Field list, with no sentence saying why.

### Edit Form... (form)

- How to reach it: context menu "Edit Form..."; Alt+I, F, E.
- What opens: the form editor, "Edit Gravity Form - {title}". Tab order:
  - Title, Description (multiline), Button text, Label placement (Top aligned, Left aligned, Right aligned), Confirmation message (multiline; disabled when the default confirmation sends people to a page, with help saying so), Notification to (disabled when the Admin Notification goes to a field or by routing), Notification subject (disabled when there is no notification).
  - Fields: a list, one row a field, such as "2. Email, Email, required", with a condition said short or "has conditional logic QUILL keeps". An empty form shows "No fields yet. Insert or Add Field adds one."
  - Buttons: Add Field... (A), Edit Field... (E), Move Up (U), Move Down (W), Remove Field (R), Condition... (N).
  - Review and Save... (default, OK), Cancel.
  - In the Fields list: Enter edits, Insert adds after, Delete removes, Ctrl+Up and Ctrl+Down move.
- Add Field / Edit Field: "Add Field" or "Edit Field - {name}". Controls: Type (a choice of 18; disabled when editing), Label, Description, Required check box, Placeholder, Default value, Admin label, CSS class, Choices (one a line; "text = value" stores a value; a leading asterisk preselects), Content (HTML blocks only), Check box text (Consent only). Controls that do not apply to the type are hidden. OK, Cancel.
- Condition: "Condition - {name}". When (Always show this field, Show this field when, Hide this field when), Field (only earlier fields), Test (is, is not), Value (a combo box of the field's choices). OK, Cancel.
- Spoken inside the editor: "{name} moved to {n} of {total}." or "{name} is already first." / "... last."; "Removed {name}. Answers already given to it stay in the entries."; for a field QUILL does not build: "{name} is a {type} field. QUILL keeps it as it is; change it in Gravity Forms, or move or remove it here."; for complex logic: "{name} has conditional logic with more than one rule. QUILL keeps it as it is; change it in Gravity Forms."; with no earlier field: "A condition depends on a question before this one, and there is none."
- Check before saving: if the accessibility checks find anything, a preview "Check Before Saving" says "{n} things to look at in {title} before it is saved. Cancel goes back to the editor, on the first of them." Each finding is a line (for example "Field 3 (text) has no label. Give it one.", "Two questions are both called Name: fields 1 and 4. A listener cannot tell them apart; ..."). Button "Save Anyway". Cancel reopens the editor with focus on the first field named.
- Preview: "Save Gravity Form". Summary "Save {title} on {site}." Lines: "Site: {site}", each setting changed ("Title: {new} (was {old})."), "Add field {n}: {name}, {type}.", "Change {name}: {what}.", "Remove {name}. Answers already given to it stay in the entries.", "Fields move: {the whole order}.", and always "Entries are never read, changed or deleted: only the form itself is sent." Button "Save Form".
- Announced after: "Saved {title} on {site}. Entries were not touched." If it reads back wrong: "{title} on {site} was saved, but it reads back differently: {problems} Ctrl+Z puts it back as it was." Unchanged: "Nothing changed in {title}; nothing was sent." Changed on the site meanwhile: "{title} changed on the site since you opened it. Nothing was sent; open it again to see the newer form."
- Undo: Ctrl+Z: "Put {title} back as it was on {site}." Redo: "Saved {title} again on {site}."
- Without permission: "That needs the Gravity Forms permission gravityforms edit forms. You are {role} on {site}." No gf/v2 routes: "Gravity Forms is not on {site}: the site's REST index has no gf/v2 routes. Its REST API must be turned on in Forms > Settings > REST API."
- Keyless: "Designing a form is occasional work, not daily (rule 9)."
- Code: wordpress_workbench_gravity_build.py, wordpress_gravity_editor.py, wordpress_gravity_field_dialogs.py, gravity_build.py, gravity_build_checks.py, gravity_build_save.py.
- Review notes: Cancel (or Escape) in the editor throws away every edit with no "Discard changes?" question. After the Check Before Saving loop it is easy to lose a session's work with one Escape.
- Review notes: Remove Field takes effect at once in the editor with no confirmation. The preview catches it before anything is sent, but there is no in-editor undo.
- Review notes: the save preview says label placement as its code: "Label placement: left_label (was top_label)."
- Review notes: "Fields move:" speaks the entire field order, not what moved. On a 30-field form one move is a very long line.
- Review notes: the Choices syntax ("text = value", leading asterisk) is power-user markup typed into a text box, with the rules only in F1 help.
- Review notes: only the default confirmation and the Admin Notification are editable; others are kept untouched, and the editor never says that more exist.

### New Gravity Form... (site, from a Forms row or node)

- How to reach it: Ctrl+N (New Here) on a site's Forms node; More > "New Gravity Form..." on a form row; Alt+I, F, W.
- What opens: "New Gravity Form", one "Title:" box. Help: "The new form's name. The editor opens next; nothing is sent until you review and save." Then the same editor, titled "New Gravity Form - {title}", starting with no fields, a Submit button, the default confirmation and an Admin Notification.
- Preview: "Save Gravity Form", summary "Make {title} on {site}.", lines starting "New form: {title}." Button "Make Form".
- Announced after: "Made {title} on {site}. Entries were not touched."
- Undo: Ctrl+Z: "Moved {title} to Gravity Forms' Trash on {site}, where it can be restored."
- Without permission: "That needs the Gravity Forms permission gravityforms create form. You are {role} on {site}."
- Keyless: "New Here (Ctrl+N) on a site's Forms node reaches it."
- Review notes: Ctrl+N on Forms always means a Gravity form. On a QAF-only site it says "Gravity Forms is not on {site}: ..." instead of making a QAF form or saying how to make one.
- Review notes: "Entries were not touched." after making a brand-new form is noise.
- Review notes: Ctrl+N on Forms > Responses, Feeds or Results is not mapped and gives the generic New Here sentence.

### Copy as a QUILL Accessible Form... (Gravity form)

- How to reach it: More > "Copy as a QUILL Accessible Form..." on a Gravity form row; Alt+I, F, Q.
- Preview: "Copy as a QUILL Accessible Form". Summary "Make a QUILL Accessible Forms draft from {title} on {site}." Lines: "Site: {site}", "New QUILL Accessible Forms draft: {title}.", each "Cannot carry over: {thing}" (for example "The label placement cannot carry over; labels go above their fields."), "Entries stay with the Gravity Forms form; none are copied." Button "Make Draft".
- Announced after: "Made a QUILL Accessible Forms draft of {title} on {site}. Delete it in Forms if you do not want it." An invalid conversion: "QUILL could not make a valid QUILL Accessible Forms form: {first problem}". No QAF on the site: "QUILL Accessible Forms is not on {site}."
- Undo: none. Ctrl+Z says it cannot be undone and blocks earlier undos.
- Keyless: "Moving a form between plugins is a once-off (rule 9)."
- Review notes: every other "make" command in this area undoes with Ctrl+Z; this one tells the person to go and delete the draft themselves.

### Copy as a Gravity Form... (QAF form)

- How to reach it: on a QAF form row, context menu "Copy as a Gravity Form..."; Alt+I, F, G ("Copy QAF Form as a Gravity Form...").
- Preview: "Copy as a Gravity Form". Summary "Make a Gravity Forms form from {title} on {site}." Lines: "Site: {site}", "New Gravity Forms form: {title}, {n} fields.", "Cannot carry over: ..." lines (for example "Only the first notification carries over."), "Responses stay with the QUILL Accessible Forms form; none are copied." Button "Make Gravity Form".
- Announced after: "Made {title} on {site}. Entries were not touched."
- Undo: Ctrl+Z moves it to Gravity Forms' Trash.
- Without permission: the gravityforms create form sentence.
- Review notes: the new Gravity form goes straight to the site with no accessibility check, while Edit Form and New Gravity Form both run Check Before Saving.

### Activate or Deactivate... (feed)

- How to reach it: context menu "Activate or Deactivate..."; Alt+I, F, A ("Activate or Deactivate Feed...").
- What it does: reads the feed again, then previews. Title "Activate Feed" or "Deactivate Feed". Summary "Activate {name} on {site}?". Lines: "A {addon} feed on {form}. Submissions will reach it again." (or "Submissions will stop reaching it."), "Active: no becomes yes.", "Every other setting of the feed is sent back exactly as the site has it." Button "Activate" or "Deactivate".
- Announced after: "{name} is now active on {site}." or "... inactive ...". Feed not returned: "Gravity Forms did not return {name} on {site}."
- Undo: Ctrl+Z sends the whole feed as it was: "Put {name} back as it was."
- Without permission: "Changing a form's feeds needs the Gravity Forms permission gravityforms edit forms. You are {role} on {site}."
- Keyless: "Switching an add-on on or off is rare and previewed (rule 9)."
- Code: wordpress_workbench_gravity_forms.py, workbench_gravity.py (feed_body).

### Rename... (feed)

- How to reach it: context menu "Rename..."; Alt+I, F, N ("Rename Feed...").
- What opens: "Rename Feed - {name}", a "Feed name:" box. Then a preview "Rename Feed": "Rename {name} on {site}?", lines "Name: {old} becomes {new}." and "Every other setting ...". Button "Rename".
- Announced after: "Renamed the feed to {new} on {site}." The same name or a blank one sends nothing and says nothing.
- Undo: Ctrl+Z.
- Keyless: "Renaming a feed is rare (rule 9)."

### Delete Permanently... (feed)

- How to reach it: context menu "Delete Permanently..."; Shift+Delete; Alt+I, D.
- Preview: "Delete Feeds". Summary "Delete {n} feed(s) from {site} permanently?". Lines: "{name}: a {addon} feed on {form}, {active|inactive}." then "Gravity Forms keeps no Trash for feeds. Ctrl+Z here makes each again with the same settings and a new number." Button "Delete Permanently".
- Announced after: "Deleted {n} feed(s) from {site}."
- Undo: Ctrl+Z makes them again: "Made {n} feed(s) again on {site}."
- Review notes: the Item menu help for Delete Permanently says "Gone for good, after you confirm by name." A feed is confirmed with a button, not by name, and Ctrl+Z brings it back, so the same row says two contradictory things.
- Review notes: feed row F1 says "Shift+Delete deletes it", which is the only place the key is taught for feeds.

### Filter Builder on Responses (Gravity)

- How to reach it: Edit > Filter Builder... on Responses or Held as Spam on a site with Gravity Forms.
- What opens: a run of choice dialogs, all titled "Filter Builder": Form, then "Filter on:" (Gravity Forms' field filters), then "How:" (is / is not, only when both exist), then "Value:" (a choice of allowed answers, or a text box: "Part of it is enough"), then, when another site-side condition exists, "Keep the responses that match:" with "All of the conditions" / "Any of the conditions".
- What it does: the conditions are sent to the site as gf/v2/entries search; the status bar uses the site's own count.
- Without a form: "{site} has no Gravity Forms forms to filter by." / "Gravity Forms offers no field filters for {title}."
- Code: wordpress_workbench_gravity_forms.py, workbench_gravity_search.py.
- Review notes: on a site with both QAF and Gravity Forms, Filter Builder on Responses always opens the Gravity Forms builder (gravity_filter_builder returns True whenever the site has Gravity Forms), so QAF responses cannot be filtered by their questions there.
- Review notes: five or six dialogs in a row to build one condition, each titled only "Filter Builder", so the title never tells a listener which step they are on.

## Shop

The Shop node is WooCommerce, read through wc/v3. Products, orders, coupons, customers, reports, store settings, reviews, shipping, taxes, attributes, brands and webhooks each have a node under Shop. Every write is previewed, and a refund needs the amount typed again. None of the shop commands is on the Item menu: they are context-menu rows (Applications key or Shift+F10), plus Ctrl+N (New Here) on a node and Delete (Move to Trash) on a row. Most rows name no capability, so they are not greyed for a role that cannot use them; WooCommerce refuses and the site's error is spoken. Undo is uneven. The newer commands (reviews, zones, taxes, attributes, brands, webhooks, customers, variations) record a Ctrl+Z. Products, orders, coupons and store settings record nothing at all.

### Where the Shop appears in the tree

- Sites > site > Shop: products. Columns: name, price, stock, status. F1: "WooCommerce's products, from its wc/v3 routes. Ctrl+N makes one; the context menu edits price, stock, status and categories after a preview. A site without WooCommerce says so. Shop Orders, below, are the shop's orders."
- Shop > Shop Orders: columns what, status, customer, total, date. Each order is read as a receipt, with no email, telephone or billing address.
- Shop > Draft Products, On Sale, Out of Stock: filters of the products list (same columns).
- Shop > Customers (name, username, registered, paying), Coupons (code, discount, used, expires), Shop Reports (report, says), Store Settings (group, setting, value), Product Reviews (product, rating, reviewer, status, date), Shipping Zones (zone, locations, methods), Tax Rates (name, rate, where, class), Tax Classes (name, slug), Attributes (name, slug), Brands (name, slug, products), Webhooks (name, topic, status, delivery).
- A site without WooCommerce: "{site} does not list WooCommerce's wc/v3 routes in its REST index, so it has no shop QUILL can read. Membership orders from Paid Memberships Pro are under Needs My Attention > Membership Orders."
- Node F1 for each is in workbench_plugin_nodes.py (PLUGIN_NODE_HELP), for example Coupons "WooCommerce's coupons. Ctrl+N makes one, Edit Coupon changes one, and Delete moves one to the Trash, each after a preview."
- Review notes: the Shop node sits under the site even on a site without WooCommerce; opening it is how you learn there is none.
- Review notes: nothing gates a shop row by capability (needs is "" for products, orders, coupons, settings). An Editor sees every row enabled, fills in five dialogs, previews, and only then hears WooCommerce's refusal.

### Properties on shop rows (all kinds)

- Alt+Enter opens a generic sheet. It is built from the route's schema when OPTIONS answers, otherwise it is a read-only list of every field the site sent, labelled from the key ("Regular price", "Stock quantity").
- Review notes: this is not tailored. A product can have dozens of WooCommerce fields, in WooCommerce's order. The "Edit Product..." command and the sheet are two different ways to change a product, with different checks.

### Products: context menu

- Order: Open on the Site (default, Enter), Read in Full, Edit Product..., Show Its Variations, Duplicate..., New Product..., Properties..., then More: Copy Link, Move to Trash..., Edit a Variation....
- F1 (row): "A WooCommerce product. Enter opens it on the site; the context menu edits its price, stock, status and categories, reads and edits its variations, duplicates it, and Delete moves it to the Trash, each after a preview."
- Review notes: Enter leaves QUILL for the browser. On every other row type, Enter stays in QUILL. A listener pressing Enter to read a product is sent to the browser.
- Review notes: Move to Trash is under More, though Delete runs it.

### Edit Product...

- What opens: five dialogs in a row, each titled "Edit Product - {name}": "Regular price:", "Sale price (blank for none):", "Stock count (blank to leave):", "Categories (a comma between):" (each filled with the current value), then a list "Status:" (published, draft, pending review, private).
- Preview: "Edit Product", summary "Change {name} on {site}.", the old and new of each changed field. Button "Change Product".
- Announced after: "Changed {name} on {site}." Bad input: "{reason} Nothing was changed." Nothing different: "Nothing about {name} would change."
- Undo: none recorded. Ctrl+Z undoes whatever change came before this one, perhaps on another site.
- Keyless: "Prices and stock change now and then, behind a preview (rule 9)."
- Code: wordpress_workbench_shop_commands.py, workbench_shop_catalog.py.
- Review notes: the Status list does not start on the product's current status (no initial), so OK on a published product makes it published only by luck of order. If the first row is chosen by accident, a draft becomes published. The preview catches it, but only if the person reads it.
- Review notes: five modal dialogs for one change is slow. One sheet with five fields would be quicker to review and to correct.

### Show Its Variations

- What opens: a report "Variations - {name}", one variation a line. A simple product: "{name} has no variations; it is not a variable product."
- Keyless: "Read when a variable product is in question (rule 9)."

### Edit a Variation...

- What opens: "Edit Variation - {name}", a list "Variation:", then three boxes (Regular price, Sale price, Stock count), then a list "Status:".
- Preview: "Edit Variation", "Change a variation of {name} on {site}.", the old and new values. Button "Change Variation".
- Announced after: "Changed {name}, {variation} on {site}." with " The site did not keep: ..." when it did not. A simple product: "{name} has no variations; it is not a variable product."
- Undo: Ctrl+Z: "Put {name}, {variation} back."
- Conflict: "{name} was changed on {site} after QUILL read it ({fields}). Nothing was sent. F5 reads it again."
- Keyless: "Prices and stock change now and then, behind a preview (rule 9)."
- Review notes: Edit a Variation has an undo and a conflict check; Edit Product, its sibling, has neither.

### Duplicate...

- Preview: "Duplicate Product", "Copy {name} on {site}.", lines "WooCommerce copies {name} on {site}, with its prices, stock settings, categories and variations." and "The copy is a draft named with (Copy) after it; the original is not changed." Button "Duplicate".
- Announced after: "Made a draft copy of {name} on {site}."
- Undo: none.

### New Product...

- How to reach it: Ctrl+N on Shop, Draft Products, On Sale or Out of Stock; the context menu.
- What opens: "New Product", "Name:" then "Price:" ("Such as 12.50, or blank to set it later.").
- Preview: lines "A new product on {site}: {name}, {type}, {price}." and "It is made as a draft, so shoppers cannot see or buy it until you publish it (Edit Product, status published)." Button "Make Product".
- Announced after: "Made {name} on {site}, as a draft."
- Undo: none.
- Keyless: "Ctrl+N (New Here) on its node runs it; the context menu has it too."
- Review notes: New Product is on every product's menu, though it ignores the product.

### Move to Trash... (product)

- How to reach it: Delete on the row; More > Move to Trash....
- Preview: "Move Product to Trash", lines "{name} moves to WooCommerce's Trash on {site}; shoppers can no longer buy it." and "Past orders keep their lines. Restore it from Products > Trash in wp-admin." Button "Move to Trash".
- Announced after: "Moved {name} to the Trash on {site}."
- Undo: none. The preview sends the person to wp-admin.
- Review notes: a Trash that can only be emptied or restored in wp-admin is a dead end. Reviews, by contrast, restore with Ctrl+Z.

### Copy Link and Open on the Site (product)

- Copy Link: Ctrl+Shift+C, the product's address. Open on the Site: Enter, in the browser.

### Shop orders: context menu

- Order: Open in the Shop's Dashboard (default, Enter), Read in Full ("The order as a receipt, in the details pane."), Change Status..., Notes..., Refund..., Properties....
- F1 (row): "A WooCommerce shop order. Not a membership order. The context menu changes its status, reads and adds notes, and makes a refund, which moves money and asks you to type the amount first."
- Review notes: Enter opens wp-admin in the browser. Reading the order, which is what most visits are for, is the second row.

### Change Status... (order)

- What opens: "Change Status - {order}", a list "New status:" of every status except the current one (pending payment, processing, on hold, completed, cancelled, refunded, failed).
- Preview: "Change Order Status", summary "Shop order {n} on {site} becomes {status}.", lines "Shop order {n} on {site}: {old} becomes {new}.", the email it sends (for example "WooCommerce emails the customer that the order is complete. Each email is sent only if it is turned on in WooCommerce > Settings > Emails."; for refunded, "... but no money moves: a status is only a word. Use Refund to return money."), then "Stock and payments are not changed by QUILL." Button "Change Status".
- Announced after: "Shop order {n} on {site} is {status}."
- Undo: none.
- Keyless: "Each status change can email a customer: never a bare key."
- Review notes: a customer email is sent and there is no undo. That is correct, but the outcome sentence does not say the email went.

### Notes... (order)

- What opens: a list "Notes - Shop order {n}", "Notes, newest first:", each note "{when}, {private or to the customer}, by {author}: {text}", then two rows "Add a private note..." and "Add a note to the customer...".
- Adding: "Add a Note - Shop order {n}", a "Note:" box, then a preview "Add a Note": private, "A private note on shop order {n}, {site}. The customer does not see it." and "It says: {text}"; to the customer, "A note on shop order {n}, {site}, sent to the customer.", "WooCommerce emails it to them now, and it shows on their order page.", "It says: ...". Button "Add Note".
- Announced after: "Added the note to shop order {n}." or "... , and WooCommerce emailed it to the customer."
- Undo: none.
- Review notes: notes are listed in a single-line choice list; Enter on a note closes the dialog with nothing done. The two "Add" rows sit after every note, so on a busy order they are a long arrow away (End reaches them).
- Review notes: the Gravity Forms notes and the shop notes are two different dialogs for the same idea.

### Refund... (order)

- What opens: one order only ("A refund is made one order at a time, never for a selection. Select one order."). Then "Refund - Shop order {n}": "Amount to refund:", "Reason (kept with the order):", then "How:" with "Return the money through the payment gateway" or "Record the refund only; I return the money myself".
- Preview: "Refund", summary "Money warning: refund {amount} {currency} on shop order {n}." Lines include the gateway sentence ("WooCommerce asks {gateway} to return {money} to the customer. This moves real money and cannot be taken back from QUILL or from WooCommerce."), "Reason recorded: ...", "Left to refund afterwards: ...", "Stock is not put back, and WooCommerce may email the customer about the refund.", "To go ahead, you will type the amount, {amount}, exactly." Button "Go On to Confirm".
- Confirm: "Type the amount, {amount}, to refund it:". A mismatch: "The amount typed did not match, so nothing was refunded."
- Announced after: "Refunded {amount} {currency} on shop order {n}, through the payment gateway." or "..., as a record only."
- Undo: none (money).
- Keyless: "A refund moves money: tier 3, never a bare key, never batched."
- Review notes: the strongest confirmation in the Workbench, and well worded. The only gap: the "How" list starts on the gateway, so OK on autopilot moves money.

### Customers

- Context menu: Read in Full (default), Customer Details, Edit Customer..., Properties....
- Customer Details: a report "Customer Details - {name}" with email and addresses. Help: "Personal details, read from WooCommerce now and kept only while this is open." A role without list_users: "WooCommerce lets only roles that can list people read a customer's details, and yours on {site} cannot."
- Edit Customer...: "Change:" list (Name and email, Billing address, Shipping address), then one dialog per field, each filled. Preview "Edit Customer", "Change {name}'s details on {site}." Button "Change Customer". Announced "Changed {name}'s details on {site}." Undo: "Put {name}'s back."
- Keyless: "Read when an order or a customer is in question (rule 9)." / "A customer's details change rarely, behind a preview (rule 9)."
- Review notes: editing a billing address is one dialog per address line, about ten in a row, and Cancel on the eighth loses the first seven.

### Coupons

- Context menu: Read in Full (default), Edit Coupon..., New Coupon..., Move to Trash..., Properties....
- New Coupon (Ctrl+N on Coupons) and Edit Coupon: dialogs "Code:", "Discount:" (a percentage off, a fixed amount off the whole cart, a fixed amount off each product), "Amount:", "Expires (YYYY-MM-DD, blank for never):", "Uses allowed (blank for no limit):". Preview button "Make Coupon" or "Change Coupon". Announced "Made coupon {code} on {site}." / "Changed coupon {code} on {site}."
- Move to Trash (Delete): preview "Move Coupon to Trash", lines "Coupon {code} moves to WooCommerce's Trash on {site} and stops working at checkout." and "Orders that used it keep their discount. Restore it from Marketing > Coupons in wp-admin." Announced "Moved coupon {code} to the Trash on {site}."
- Undo: none for any coupon command.
- Review notes: on Edit Coupon the Discount list does not start on the coupon's current kind, so a percent coupon edited for its date becomes a cart discount unless the person moves back to the first row.

### Shop Reports

- Rows: one sentence per report (sales this month, top sellers, totals of orders, products, customers, coupons and reviews). Enter reads its small table in the details pane.
- Context menu: Read in Full, Properties.
- F1 (row): "One WooCommerce report as a sentence; Enter reads its table."

### Store Settings: Change Setting...

- Rows: one per setting, "group, setting, value" in words.
- What opens: "Change Setting - {label}", a "New value:" list of WooCommerce's choices, or a text box filled with the value in words.
- Preview: "Change Setting", "Change a WooCommerce setting on {site}.", lines "WooCommerce > Settings > {group} > {label} on {site}: {old} becomes {new}." and "It takes effect for shoppers at once. Nothing else is changed." Button "Change Setting".
- Refusals: a password-style setting, "{label} is a password-style setting, so QUILL neither reads it aloud nor changes it. Change it in WooCommerce > Settings in wp-admin."; a multi-select, "{label} takes several values at once; change it in WooCommerce > Settings in wp-admin, where each is a check box."; same value, "That is its value already. Nothing was changed."
- Announced after: "Changed {label} on {site}."
- Undo: none.
- Keyless: "Store settings change a few times a year (rule 9)."
- Review notes: the choice list does not start on the current value, so a listener cannot hear what is set without leaving the dialog.

### Product Reviews

- Context menu: Read in Full (default), Approve, Hold, Mark as Spam, Reply..., Edit Review..., Move to Trash..., Properties....
- Approve, Hold, Mark as Spam: work on the selection (one site: "Change reviews on one site at a time."). Preview "{Approved|Held|Marked as spam} Reviews", "{n} review(s) on {site}." Announced "{what}: {n} done." or "... {m} not done." with a report window when more than one or any failed.
- Reply...: "Reply - {title}", a "Reply:" box; preview "Reply to Review", "Under {reviewer}'s review of {product}:", the text, "It shows on the product's page as soon as it is sent." Button "Send Reply". Announced "Replied to the review on {site}." Undo: "Moved the reply to the Trash."
- Edit Review...: "Review:" then "Rating (1 to 5):"; preview lines "{Field}: {old} becomes {new}." and "The reviewer is not told." Announced "Changed the review on {site}."
- Move to Trash (Delete): preview lines are each review's details and "Ctrl+Z takes them out of the Trash again."
- Undo: Ctrl+Z on all of these.
- Review notes: the shop's best-behaved area, with selection, outcomes, undo and conflict checks. It shows what the product, order and coupon commands are missing.

### Shipping Zones, Tax Rates, Tax Classes, Attributes, Brands, Webhooks

- Zones: Locations... (one box, "country US, state US:AZ, postcode 85001, continent EU", a comma between), Methods... (a list of methods plus "Add a method..."; on a method, "Do:" Turn it off/on, Change its cost, Remove it), New Shipping Zone..., Rename..., Delete.... The zone for everywhere else: "The zone for everywhere else covers what no other zone does; it has no locations." / "The zone for everywhere else cannot be deleted; remove its methods instead."
- Tax Rates: Edit Tax Rate... (Name, Rate (percent), Country code, State code, Postal codes, City), New Tax Rate..., Delete.... Delete preview: "There is no Trash. Ctrl+Z makes the rate again with the same fields."
- Tax Classes: New Tax Class..., Delete... ("Every rate in it goes with it, and products in it are taxed as standard.").
- Attributes: Terms... (a list of values plus add; on a value, "Do:" Rename it, Delete it), New Attribute..., Rename..., Delete....
- Brands: New Brand..., Rename..., Delete....
- Webhooks: Pause or Activate..., New Webhook... (Name, Send when, Delivery address; "it must start with https://"), Delete... ("Webhooks have no Trash, so this cannot be undone; Pause stops it without deleting it.").
- Undo: made items delete again; renames and edits put back; a deleted tax rate is made again; other deletes have none.
- Keyless: "Set up once and changed a few times a year, behind a preview (rule 9)." Deletes: "A delete for good, with no Trash: never a bare key (rule 4)."
- Review notes: the Delete command for zones, attributes and brands is labelled "Delete..." while the help on the Item menu says Delete Permanently is "confirm by name". Here it is a preview button, which is fine, but three words for the same idea (Delete, Delete Permanently, Remove) appear in one product.
- Review notes: removing a shipping method sends at once after the preview and records no undo.

## Events

The Events Calendar lives at Sites > site > Events Calendar, read through tribe/events/v1. Upcoming events come first, and Past Events, Venues, Organizers, Event Categories and Event Tags are below it. Times are said in each event's own time zone, with your computer's time added. A recurring occurrence from Events Calendar Pro is refused for Edit, Trash and Categories and Tags, with a pointer to wp-admin. Writes are previewed. Events, venues and organizers have no undo; event categories and tags do.

### Where events appear in the tree

- Events Calendar (columns title, when, venue, status), F1: "The Events Calendar's events from now on, soonest first, through tribe/events/v1. Ctrl+N makes one; times are in each event's own time zone, and yours is said too."
- Past Events, Venues (name, where, phone), Organizers (name, phone, website), Event Categories (name, slug, events), Event Tags (name, slug, events).
- An event's details: "{title}, {when}, {zone} ({abbr}). On your computer's clock it starts {time}. At {venue}. Cost {cost}." and, for a recurring one, the recurring sentence.
- A site without the plugin: "{site} does not list The Events Calendar's tribe/events/v1 routes in its REST index, so it has no events QUILL can read."

### Events: context menu

- Order: Open on the Site (default, Enter), Read in Full, Edit Event..., New Event..., Events Between Dates..., Copy Link, Properties..., then More: Move to Trash..., Categories and Tags....
- F1 (row): "An event in The Events Calendar. Edit Event changes it after a preview; Delete moves it to the Trash; Categories and Tags sets its terms. A recurring event says so and is changed in wp-admin."
- Review notes: as with products, Enter goes to the browser.

### New Event...

- How to reach it: Ctrl+N on Events Calendar or Past Events; the context menu.
- What opens: dialogs titled "New Event": "Title:", "Starts (YYYY-MM-DD HH:MM):", "Ends (YYYY-MM-DD HH:MM):", "Time zone (blank for the site's):", "Cost (blank for none):", then "All day:" (No, it has times / Yes, all day), then "Venue:" (No venue, then each venue).
- Preview: "New Event", "Make {title} on {site}.", lines starting "A new event on {site}: {title}, {when}." and "Times are in {zone}." Button "Make Event".
- Announced after: "Made {title} on {site}, as a draft." Errors: "An event needs a title. Nothing was made." / "The event ends before it starts. Nothing was made."
- Undo: none.
- Keyless: "Ctrl+N (New Here) on its node runs it; the context menu has it too."
- Code: wordpress_workbench_event_commands.py, workbench_events.py, plugin_events.py.
- Review notes: there is no way to choose an organizer or categories at creation; categories need a second command.
- Review notes: typing "YYYY-MM-DD HH:MM" by hand is error-prone; no date picker or "tomorrow at 7" understanding.

### Edit Event...

- What opens: the same five boxes, filled, then "All day:", which does not start on the event's current setting.
- Preview: "Edit Event", "Change {title} on {site}." Button "Change Event". Announced "Changed {title} on {site}." Nothing different: "Nothing about {title} would change."
- Recurring: "This is one occurrence of a recurring series from Events Calendar Pro. The REST API gives each occurrence but not the series' rule, so the series is changed or removed in Events in wp-admin, not here."
- Undo: none.
- Keyless: "An event's details change now and then, behind a preview (rule 9)."
- Review notes: the help and the PLUGIN_ACTION_ROWS text both promise "title, start, end, time zone, venue and cost", but Edit Event never asks for the venue; it keeps the old one. A wrong promise.
- Review notes: "All day:" starting on "No" means an all-day event edited for its cost becomes timed unless the person changes it back.

### Events Between Dates...

- What opens: "From (YYYY-MM-DD):", "To (YYYY-MM-DD):", then a report "Events from {from} to {to} - {site}", one event a line, or "No events in those dates." Bad dates: "The last date is before the first."
- Keyless: "Asked when planning, now and then (rule 9)."
- Review notes: a report rather than a filtered list, so you cannot act on what you find.

### Move to Trash... (event, venue, organizer)

- How to reach it: Delete on the row; the context menu (under More for events).
- Preview: "Move {Event|Venue|Organizer} to Trash", lines "{name} moves to the Trash on {site}." and "It leaves the calendar; restore it from Events > Trash in wp-admin." (venues: "Events at it lose their venue; restore it from Events > Venues > Trash."; organizers: "Events lose this organizer; restore it from Events > Organizers > Trash.").
- Announced after: "Moved {name} to the Trash on {site}."
- Undo: none; restore is a wp-admin hand-off.

### Categories and Tags... (event)

- What opens: "Categories and Tags - {title}", "Categories (a comma between):" then "Tags (a comma between):", each filled with the current names.
- Announced after: "Changed {title}'s categories and tags on {site}." plus " The site did not keep: ..." when it did not. A conflict: "{title}'s categories changed on {site} after QUILL read them..." Unchanged: "{title}'s categories and tags would not change."
- Undo: Ctrl+Z: "Put {title}'s terms back."
- Keyless: "An event's terms are set when it is made (rule 9)."
- Review notes: names typed must match existing terms; there is no list to choose from, though QUILL has just read them.

### Venues and Organizers

- Venue menu: Read in Full (default), Edit Venue..., New Venue..., Move to Trash..., Properties.... Organizer menu: the same with Organizer.
- New and Edit: "Name:", then one dialog per field. Venue: Address, City, State or province, Postal code, Country, Phone, Website. Organizer: Phone, Website, Email. Preview button "Make Venue" / "Change Venue" (or Organizer). Announced "Made the venue {name} on {site}." / "Changed the venue {name} on {site}."
- Undo: none.
- Review notes: eight dialogs to make a venue, and a blank answer on an edit clears that field, which the preview shows but which is easy to do by Enter-Enter-Enter.

### Event Categories and Tags

- Menu: Read in Full (default), New Event Category... (or New Event Tag...), Rename..., Delete..., Properties....
- New: one "Name:" box, preview "A new {category} on {site}: {name}." Announced "Made the {category} {name} on {site}." Undo deletes it: "Deleted the {category} again."
- Rename: preview "{old} becomes {new}." and "Its events keep it under the new name." Undo: "Named it {old} again."
- Delete: preview "There is no Trash: its events lose it, and keep everything else." Announced "Deleted the {category} {name} on {site}." No undo.
- Keyless: "A delete for good, with no Trash: never a bare key (rule 4)."

## SEO

SEO means Yoast SEO only, read through yoast/v1 and each item's meta. Other SEO plugins are not read here. Sites > site > SEO lists the newest posts and pages with their SEO title, description, indexing and focus keyphrase. SEO > Site SEO gives the site's scores and the jobs only Yoast's own screens can do. Search Appearance reads what a search engine shows. Edit SEO changes one item. The Bulk SEO Editor changes many items from one list. Edits are previewed and undo with Ctrl+Z.

### Where SEO appears in the tree

- SEO: columns title, seo_title, description, index, keyphrase. F1: "Yoast SEO for the newest posts and pages: the title and description search engines are given, whether it is indexed, and its focus keyphrase. Edit SEO changes them."
- SEO > Site SEO: columns what, says. Rows include, among the scores, the wp-admin-only jobs: "Search appearance for each content type", "Site representation and social profiles", "Optimise SEO data (indexing)", "Redirects, schema and breadcrumbs", "Related keyphrases and rank tracking", "Yoast's AI features", each with why and Enter opening wp-admin.
- No Yoast: "{site} does not list Yoast SEO's yoast/v1 routes in its REST index, so QUILL has no Yoast SEO to read there. Titles and descriptions another SEO plugin registers are on each item's Properties."
- Review notes: the node is called "SEO" but is Yoast-only. A Rank Math or All in One SEO site hears only the error.

### SEO item context menu

- Order: Search Appearance (default, Enter), Edit SEO..., Open on the Site, Bulk SEO Editor..., Properties....
- F1 (row): "A post or page with its Yoast SEO. Search Appearance reads what a search engine shows; Edit SEO changes the title, description, keyphrase, indexing and social title, description and image; the Bulk SEO Editor changes many in one window."

### Search Appearance

- What opens: a report "Search Appearance - {title}" with the title, address and description a search engine shows, each with "... (cut off after {n} characters)" where it would be cut.
- Keyless: "Enter runs it on an SEO row, its default."

### Edit SEO...

- What opens: dialogs titled "Edit SEO - {title}": "SEO title:", "Meta description:", "Focus keyphrase:", "Social title:", "Social description:", "Social image address:", then a list "Show in search results:" (as the content type's default; no, kept out of search results; yes, shown in search results).
- Preview: "Edit SEO", "Change Yoast SEO for {title} on {site}.", the old and new of each changed field, for example "{Social title}: not set becomes {new}." Button "Change SEO".
- Announced after: "Changed Yoast SEO for {title} on {site}." plus " The site did not keep: ..." when it did not. Nothing different: "Nothing about {title}'s SEO would change." and, where fields cannot be written, " {fields} cannot be written here; Yoast's panel does it."
- Undo: Ctrl+Z: "Put {title}'s SEO back."
- Keyless: "SEO fields are set once per post, behind a preview (rule 9)."
- Code: wordpress_workbench_terms_seo.py, workbench_seo.py, workbench_seo_bulk.py.
- Review notes: seven dialogs for one item, and the indexing list does not start on the current setting.
- Review notes: no running character count while typing the SEO title, though Search Appearance knows the limits.

### Bulk SEO Editor...

- What opens: a list window "Bulk SEO Editor - {site}". Purpose: "Every post and page with its Yoast SEO title and description. Enter changes the selected one where it stands, after a preview; Ctrl+Z in the Workbench undoes it." List "Posts and pages:", each item's title and the length of its SEO title and description; a details area; a button "Change SEO Title and Description...". Enter does the same.
- Editing one: "Edit SEO - {name}", "SEO title:" then "Meta description:", then a preview. Announced "Changed Yoast SEO for {name} on {site}." Locked: "Your role cannot edit {name}, so Yoast keeps its SEO locked."
- No routes: "{site}'s Yoast SEO has no bulk editor routes; it came with Yoast SEO 28." Empty: "Yoast SEO's bulk editor gave no posts or pages on {site}."
- Requirement: wpseo_manage_options (greyed without it).
- Keyless: "A window opened for an SEO pass now and then (rule 9)."
- Review notes: the Bulk SEO Editor is on every SEO item's menu, though it opens the whole site.

### Open in Dashboard (Site SEO row)

- Enter on a Site SEO job row opens "Yoast's own screen for this, in your browser."
- Review notes: half the Site SEO node is pointers to wp-admin. That is honest, but it is the plugin's hand-off.

## Memberships

Paid Memberships Pro shows up in two places. Sites > site > Memberships lists levels, orders, subscriptions, renewals due and discount codes, read through PMPro's Abilities API (WordPress 6.9 and PMPro 3.9 or later). On a person in Users, the context menu has Show Memberships, Check Membership Access, Change Membership Level and Cancel Membership, and the person's Properties sheet gains an Access page. Membership orders are kept apart from WooCommerce's shop orders, and every surface says so. Changes are previewed, with the subscription and gateway that stop named. Nothing here has an undo.

### Where memberships appear in the tree

- Memberships (no list of its own): F1 "Paid Memberships Pro levels, orders, subscriptions and renewals, when its Abilities API is available."
- Membership Levels: name, signups, initial, billing, expires. Detail: "{name}. Signups: ... Initial payment: ... Recurring billing: ... Expires after: ..."
- Orders: code, status, total, gateway, date, member, level. F1 "Paid Memberships Pro order summaries, not WooCommerce shop orders. Card and billing details are never shown."
- Subscriptions and Renewals Due (due now or within thirty days): subscription, status, next payment, billing, gateway, member.
- Discount Codes: code, uses, used, starts, expires, levels. F1 "Paid Memberships Pro discount codes. Look Up a Discount Code reads one by its code; New Discount Code makes one after a preview. The full list is in wp-admin unless the site offers a discount-codes ability."
- Needs My Attention > Membership Orders: pending, in review or failed membership orders on every site.
- Without the abilities: one row, "Paid Memberships Pro abilities are not exposed on this site. They require WordPress 6.9 or later and Paid Memberships Pro 3.9 or later."
- Review notes: the Discount Codes list is usually just a pointer row to wp-admin, so the node promises a list it rarely has.

### Membership row context menu (every pmpro row)

- Order: Read in Full (default), Look Up a Discount Code..., New Discount Code..., Properties....
- F1 (row): "A Paid Memberships Pro level, membership order, subscription or discount code. Alt+Enter reads its details."
- Review notes: the two discount-code commands appear on a level, an order and a subscription row too, where they have nothing to do with the row. A level row has no level command at all.
- Review notes: Properties is a raw read-only sheet of the item's fields.

### Look Up a Discount Code...

- What opens: "Look Up a Discount Code", a "Code:" box.
- Announced after: the code's sentence, "Discount code {code}: {n} uses, used {m} times, starts {date}, expires {date}, for {levels}." Not found: "There is no discount code {code} on {site}."
- Keyless: "A code is looked up when a member asks about it (rule 9)."
- Review notes: the answer is only spoken. There is no window to read it again or copy it.

### New Discount Code...

- How to reach it: Ctrl+N on Discount Codes; the context menu.
- What opens: five dialogs titled "New Discount Code": "Code:", "Level numbers (a comma between):" ("From Memberships > Membership Levels."), "Initial payment with the code:", "How many uses (0 for unlimited):", "Expires (YYYY-MM-DD, or blank for never):".
- Preview: "New Discount Code", "Paid Memberships Pro on {site} gets this discount code.", lines "Code {CODE} on {site}: {uses}, starts {today}, expires {date}." and per level "Level {n} (level {n}): initial payment {amount}, ...". Button "Make the Code".
- Announced after: "Made the discount code {CODE} on {site}." Missing parts: "A discount code needs a code and at least one level, so nothing was made."
- Requirement: manage_options.
- Undo: none.
- Review notes: levels must be typed as numbers learned in wp-admin, though the Membership Levels node lists them. The preview passes no level names, so it says "Level 2 (level 2)", which says the number twice and the name never.
- Review notes: the code is upper-cased silently.

### Show Memberships... (on a person)

- How to reach it: Users > a person > context menu "Show Memberships..." (third row).
- What opens: a report "Paid Memberships Pro - {name}", one level a line, "{level}: {status}, started {date}, ends {date}", or "No current or past memberships were returned." Help mentions payment card details are not included.
- Without PMPro: "{site} exposes neither the Paid Memberships Pro member-memberships ability nor its pmpro/v1 routes."
- Review notes: the dates are the site's raw strings, not friendly dates as elsewhere.
- Review notes: the membership rows (Show, Check Access, Change, Cancel) are on every person's menu on every site, PMPro or not. Not found in code: any hiding or greying of them on a site without PMPro.

### Check Membership Access...

- How to reach it: the person's context menu (fourth row); also Properties > Access page > "Check a Post or Page..." button.
- What opens: "Check Membership Access - {name}", "Post or page (its number, or words from its title):".
- Announced after: "{name} can see {post} on {site}, through {levels}." or "{name} cannot see {post} on {site}. It needs one of these levels: {levels}." Nothing matches: "Nothing on {site} matches {words}." On the Access page, the answer lands in the page's box instead.
- Keyless: "Asked when a member reports a locked page, now and then."
- Review notes: words from a title take the first search result without saying so or offering a choice. A common word can check the wrong page.

### Change Membership Level...

- What opens: "Change Membership Level - {name}", a "New level:" list ("{name} (level {id})") when the site has the levels ability; otherwise a "Level number:" box ("From Memberships > Membership Levels in wp-admin.").
- Preview: "Change Membership Level", "Give {name} {level} on {site}.", lines "{name} gets {level} on {site} now, with no checkout and no payment taken.", what ends ("{old} ends.") and each subscription that stops, or "They have no current membership, so nothing they have ends." and "Cancel Membership takes it away again, after its own preview." Button "Change Level".
- Announced after: "{name} now has {level} on {site}." Same level: "{name} already has {level}. Nothing changed." Not a number: "A level is a number, so nothing changed."
- Undo: none.
- Keyless: "Members change level at checkout; staff do it rarely (rule 9)."
- Review notes: the fallback asks for a number from wp-admin.
- Review notes: no undo for a change that stops a recurring payment; the preview says so only for cancellation.

### Cancel Membership...

- What opens: when the person has more than one current level, "Cancel Membership - {name}", "Level to cancel:".
- Preview: "Cancel Membership", "Cancel {name}'s {level} membership on {site}.", lines "{name} loses {level} on {site} now.", each subscription and gateway asked to stop (or "QUILL found no active recurring subscription for it, so no gateway is asked."), "Nothing is refunded: refunds are made in the gateway or in Memberships > Orders.", "This cannot be undone from QUILL. A cancelled subscription is not restarted; the person would check out again." Button "Cancel Membership".
- Announced after: "Cancelled {name}'s {level} membership on {site}." No membership: "{name} has no current membership on {site}."
- Tier: destructive. Undo: none.
- Keyless: "A cancellation is rare and stops payments: never a bare key."
- Review notes: the dialog's own Cancel button sits next to "Cancel Membership". A listener hears "Cancel Membership, button" and "Cancel, button" side by side, and Escape is the safe one. A button named "End Membership" would avoid the clash.
- Review notes: tier 3, but confirmed by one button, while a refund asks for the amount typed.

### The member's Access page (Properties)

- Alt+Enter on a person, on a site with pmpro/v1, adds a page "Access" with a read-only box "Can this member see it (Paid Memberships Pro)", first saying "Choose Check a Post or Page, then type a post or page's number or words from its title. Paid Memberships Pro says whether this member can see it." The button "Check a Post or Page..." works on read-only sheets too.

## Redirects

Redirects come from the Redirection plugin's redirection/v1 namespace, under Sites > site > Redirects with its 404 Log below. You can add, change, turn on or off, delete and test redirects, and turn a 404 into a redirect. After you change a post's slug, QUILL offers a redirect from the old address. Redirects that Yoast SEO Premium or Rank Math keep are not read; their screens open in wp-admin. No redirect command records an undo.

### Where redirects appear in the tree

- Redirects: columns source, target, code, hits, state ("on" or "off"). Detail: "{source} leads to {target} with a {code} redirect, on; used {n} times, last on {date}." plus " The source is a pattern (regular expression)." F1: "The Redirection plugin's redirects: add with Ctrl+N, change, test, turn off."
- Redirects > 404 Log: columns address, when, from. Detail: "{address} was asked for and not found on {date}, from {referrer}. Redirect This Address makes a redirect from it." F1: "Addresses visitors asked for that were not found; redirect any of them."
- Without the plugin: the node holds one Administration Areas row for Redirects, whose words include "Redirection; Yoast SEO Premium and Rank Math keep redirects in their own screens". Any command says "{site} does not have the Redirection plugin's REST namespace, so QUILL cannot change its redirects. Administration Areas says where they are kept."
- Lists read at most five pages of 200.

### Redirect row context menu

- Order: Read in Full (default), Test an Address..., Add Redirect..., Change Redirect..., Turn On or Off, Delete Redirect..., Open on the Site, Properties....
- 404 row: Read in Full (default), Redirect This Address..., Test an Address..., Properties....
- F1 (rows): redirect "One redirect: from, to, its code and hits. Test an Address follows it."; 404 "An address that was not found. Redirect This Address sends it somewhere."
- Properties: a raw read-only sheet of the plugin's fields.

### Add Redirect...

- How to reach it: Ctrl+N on Redirects; the context menu.
- What opens: three dialogs titled "Add Redirect": "Old address, from this site (such as /old-page/):", "New address it leads to:", then "Kind of redirect:" (301, moved for good; 302, found elsewhere for now; 307, for now; 308, for good). If the site has more than one group, "Group to keep it in:" ("Redirections" first; a turned-off group says "(turned off)").
- Preview: "Redirect Preview", "On {site}: add a redirect.", lines "From: {path}", "To: {target}", "Kind: {code}". Button "Save Redirect".
- Announced after: "Saved on {site}: {from} now leads to {to}." No group: "The Redirection plugin on {site} has no group to keep a redirect in. Add one under Tools, Redirection, Groups, then try again."
- Requirement: manage_options. Undo: none.
- Keyless: "Ctrl+N (New Here) on Redirects reaches it; no chord of its own."
- Code: wordpress_workbench_sweep.py, workbench_redirects.py, workbench_sweep_places.py.
- Review notes: no undo for a new redirect, though deleting what was just made would be safe.
- Review notes: the preview does not warn when the new redirect makes a chain or loop, though Test an Address can work that out from the list already read.

### Change Redirect...

- What opens: the same three dialogs, titled "Change Redirect", filled. The group is kept, or asked when unknown.
- Preview: "Redirect Preview", "On {site}: change this redirect." Button "Save Redirect". Announced as Add.
- Undo: none.

### Turn On or Off

- What opens: a Yes/No question, title "Turn Off" (or "Turn On"), "Turn Off the redirect from {source} on {site}?", buttons "Turn Off" and "Cancel", with Cancel the default.
- Announced after: "The redirect from {source} is off." / "... is on."
- Undo: none.
- Review notes: a reversible on/off with a confirmation but no Ctrl+Z is backwards: every other on/off in the Workbench undoes.

### Delete Redirect...

- What opens: a Yes/No question, "Delete Redirect", "Delete the redirect from {source} to {target} on {site}? The Redirection plugin keeps no Trash, so it is gone for good." Buttons "Delete Redirect" and "Cancel" (default).
- Announced after: "Deleted the redirect from {source} on {site}."
- Undo: none.
- Keyless: "A destructive, rare job: never a bare key (rule 4)."
- Review notes: the row help says "Gone for good, after you confirm by name", and the Administration Areas text says "deleted after a confirmation by name". The code asks a plain Yes/No; nothing is typed. The help is wrong.
- Review notes: QUILL has the redirect's fields, so an undo that makes it again would be easy and would match feeds and tax rates.

### Test an Address...

- What opens: "Test an Address", "Address on this site to follow:", filled with the row's source. Help: "QUILL follows the redirects it read from this site. Nothing is sent."
- Then a report "Test an Address" with, for example, "/a/ leads to /c/: /a/ to /b/ (301) then /b/ to /c/ (301). A chain: one redirect straight to the end is faster. Tested here on the list as read; the plugin's own options, such as case, trailing slashes and query parameters, decide in the end. Open on the Site tries it live." A loop: "{address} goes round in a loop: ... Visitors get an error; change one of these redirects." None: "No redirect read from this site matches {address}." Blank: "Give an address on the site, such as /old-page/."
- Keyless: "Asked when a link is reported broken, now and then (rule 9)."
- Review notes: a clear, useful answer. It uses the list as last read, so a redirect added in wp-admin since is missed until F5.

### Redirect This Address... (404)

- What opens: the Add Redirect dialogs titled "Redirect This Address", with the 404's address filled in.
- Announced after: "Saved on {site}: {from} now leads to {to}."
- Keyless: "Reviewing the 404 log is a monthly job (rule 9)."
- Review notes: the 404 stays in the log after it is redirected; nothing marks it done.

### Add a Redirect after a new slug

- When it opens: after a post's slug is saved on a site with Redirection, and the address changed.
- What opens: a Yes/No question, "Add a Redirect", "{title} moved from {old} to {new}. Add a redirect on {site}, so links to the old address still arrive?", buttons "Add Redirect" and "Cancel".
- Announced after: "Redirect added: {old} now leads to {new}." No group: "No redirect added: the Redirection plugin on {site} has no group to keep one in."
- Review notes: it uses the default group without asking, unlike Add Redirect, and a 301 without offering the kind.

## Multisite

QUILL has no multisite network administration. WordPress's REST API has no network routes, so there is no Network Sites node, no network users or network themes, and no list of a network's subsites. Each subsite is connected and worked on as its own site in the Sites node. Three things touch networks: Promote to Network on a plugin in Across Sites, a Network Admin row in each site's wp-admin Screens list, and the scope matrix's reasons, which explain why each network-wide operation is not offered.

### What there is not

- Not found in code: a node for network sites, wp/v2/sites, any detection that a connected site belongs to a network beyond the plugin-schema check below, or a way to add a subsite.
- The design log (docs/design/wordpress.md, "Multisite network admin") records the choice: "core registers no network-admin routes at all. Sites, network users, network plugins and network themes are wp-admin only. On a subsite, the ordinary routes work per site, and QUILL already treats each subsite as its own connection."
- The scope matrix (workbench_scope_matrix.py) answers every network cell with a reason, such as "WordPress's REST API has no network-wide form of this; each site of a network is changed as its own site.", "Network-enabling a theme has no REST route; use Network Admin > Themes.", "Making a super admin has no REST route; use Network Admin.", "Network settings have no REST route; use Network Admin.", "Application passwords are per site, even on a network."
- Review notes: a person managing a 20-site network must connect each subsite by hand, with its own application password. Nothing says this in the Sites node or in F1.

### Promote to Network...

- How to reach it: Go > Across Sites (Ctrl+0), then Plugins, then a plugin row, context menu "Promote to Network...".
- What it does: for each site that has the plugin, QUILL asks the site's plugin schema (OPTIONS wp/v2/plugins) whether "network-active" is a status. Only a multisite offers it.
- Refusals: on a non-plugin row, "Promote to Network works on a plugin, in Across Sites > Plugins. {reason}", for example "WordPress has no network-wide terms." No network: "{site} is not a multisite network: its plugin schema has no network-active status, so the plugin stays per site." Not allowed: "Promote to Network needs a super admin of {site}'s network."
- Practice crossing: when the practice site and real sites are both in scope, a Yes/No question titled "Promote to Network: the Practice Site and Real Sites Together", with "Change {site} Too" or "Change Them Too", Cancel the default.
- Preview: "Promote to Network", summary "{plugin} runs on every site of each network below, and no single site can deactivate it. WordPress refuses unless you are a super admin." Lines: "{site}: becomes network-active" for each, then "Not changed. {why}" for the others. Button "Promote".
- Announced after: "{plugin}: network-active on {good} of {n} networks." A report "Promote to Network: Each Site" when any failed, "Done. ..." or "Not done. ..." a line.
- Requirement: the row names activate_plugins; the handler also checks it on each site before asking. Undo: none (recorded without one, so Ctrl+Z says it cannot be undone and stops there).
- Keyless: "Done once per plugin on a network, rarely (rule 9)."
- Code: wordpress_workbench_across.py, workbench_across_ops.py, workbench_places.py, workbench_scope_matrix.py.
- Review notes: when no site qualifies, only the first site's reason is spoken; the others are lost.
- Review notes: each connected subsite counts as a network, so two subsites of one network say "network-active on 2 of 2 networks", and WordPress is asked twice.
- Review notes: there is no "Demote" or network-deactivate, and no undo, for a change the summary itself calls one no single site can reverse.
- Review notes: the check activate_plugins is a single-site capability; the real requirement (super admin) is only known when WordPress refuses.

### Network Admin row (wp-admin Screens)

- Where: Sites > site > Overview > wp-admin Screens, a row "Network Admin", address network/, "Only on a multisite network, and only for a Super Admin; REST has no network routes." Enter opens it in the browser.
- Review notes: the row is listed on every site, single sites included (it has no namespace gate), so a single-site owner is offered a screen that does not exist.

### Plugin rows on a subsite

- A plugin that is network-active counts as active (site_admin.py and do_toggle_plugin treat "network-active" as active).
- Review notes: Activate or Deactivate offers "Deactivate" on a network-active plugin and sends status inactive from the subsite. QUILL does not check whether WordPress allows that from a subsite; any refusal is the site's own error, spoken as it comes.

## Review notes, all in one place

The first part ranks the concerns that matter most, merged across every section. The second part lists every review note in the document, section by section, so nothing is lost. None of this was tried live; each line comes from reading code.

### Most important first

#### Safety: things that can change or lose data unexpectedly

1. Workbench Access, Safe Mode and View As Role can be bypassed. The access check (refusal_for) only looks at commands in the selected row's own context menu, so menu-bar and node commands run unchecked under Read Only: Empty Spam, Empty Comment Trash, New Here, Import Posts, Import a Folder, Import WXR, Put Back from a Snapshot, Install on Sites Missing It, Promote to Network, and REST Console writes. Delete and Shift+Delete on a user row (Remove) and on an Application Passwords row (Revoke) also skip the check.
2. Shift+Delete on an Application Passwords row goes through generic Delete Permanently and skips the guard that stops you revoking the password the Workbench itself signs in with.
3. Ctrl+Z is unreliable in two opposite ways. A change recorded with no undo stays on top of Change History, so Ctrl+Z repeats "{summary} cannot be undone." and every older undo becomes unreachable (Delete Permanently, Approve and Schedule, Send Back, Copy to Site, imports, batches, Resend Notifications, Revoke Everywhere). And many writes are not recorded at all (Reply, Merge Into, Convert, Allow This Sender, the Empty commands, New Here, products, orders, coupons, events, redirects, membership changes, form status and settings, Find a Plugin install), so Ctrl+Z right after them silently undoes an older, unrelated change, perhaps on another site.
4. Preview windows default to the action button while message boxes default to Cancel, so Enter proceeds through previews, even at the Destructive tier (Empty Trash's "Delete Permanently", Merge Into).
5. The plugin Properties sheet's Status field can deactivate any plugin with no confirmation, skipping both the Application Passwords lockout guard and the "QUILL relies on" warning that Activate or Deactivate gives.
6. Put Back from a Snapshot restores only title, content and excerpt (name and description for terms); status, slug, terms, featured image and parent are not set back, deleted items return as bare drafts, and a snapshot silently leaves out custom post types, templates, global styles, Navigation menus and form data.
7. Sign Out This Site is irreversible but preselects "Remove {site} from QUILL" with OK as the default, so Enter twice signs out and forgets the site.
8. Send Back with a Note on a published post unpublishes it with no preview and no undo; Approve and Schedule reschedules published posts without the warning Move to Another Day gives.
9. Gravity Spam and Not Spam send the entry as it was when the list loaded, overwriting answers changed since.
10. Replace File asks about deleting the old file after the preview, and after "Delete the old file", Ctrl+Z points every page back at the deleted file.
11. Properties on posts drops plain category and tag names (only "News (12)" or an id works) while the confirmation says they were added.

#### Keys that do not work, or teach the wrong thing

12. Ctrl+Shift+F (Filter Builder) and Ctrl+Alt+Shift+F (Forget a Saved Request) only move to the filter box, and Ctrl+Alt+R (Roles) reloads the list, because the shared frame's key hook (workbench_frame_commands.py) runs before the menu.
13. In QUILL's Insert menu all seven WordPress rows reuse access letters other Insert rows already hold, and three of four View rows do too, so none can be chosen by its letter.
14. Tools > WordPress, Tools > Forms and Edit > WordPress have no access letter in either editor; QUILL Lite menu labels also give no Alt route.
15. Menu letters and layer letters disagree for several rows (Check Before Publishing P against K; Media Library B against M; about eight across Tools and Forms).
16. Four Gravity rows in the Workbench Item menu have no access letter; context-menu rows and "More" have none at all, and context menus show no chords.
17. The layer keeps modifiers held from the prefix ("No WordPress command on Ctrl+Alt+Shift+O."), and its four-second timeout is silent, so a late letter types into the document.
18. Responses shows "(Ctrl+Alt+Shift+Grave, F)" even when WordPress is off and the layer is refused.

#### Dead ends and lost features

19. Fifteen Tools > WordPress rows now always open the Workbench (workbench_door always returns True), making their older windows unreachable; some of those windows did things the Workbench cannot, such as Fonts install and delete, Synced Patterns block editing, and, until Arrange Items arrived on 2026-11-14, rearranging menu items. Docstrings still say "behind its flag".
20. Menu items cannot be seen, renamed, moved or removed inside the Workbench; Arrange Items hands off to the editor's Menus window, which has no previews and no Ctrl+Z.
21. WordPress.com is offered in Connect, then refused with "not available in this build yet".
22. The wp-admin map still says WXR import and export are "Only in wp-admin" though Tools > WXR Files now does both; there is no Tools node in the site tree.
23. Start Here still says the Workbench is "early preview, behind a developer setting" and that the Tools windows still work; both are false.
24. Help and refusal sentences point at commands that moved or never existed ("Menus is in File, WordPress, Running the Site", "choose Trash as the status in Open", "then reconnect").

#### What is heard, and what is not

25. The reason a row is greyed is never heard: menu help goes to a status pane that does not exist, context menus give no reason, and every greyed row says "Not available here." Shift+F1 opens a generic list instead of the provider's real "your role and what each action needs" view.
26. Long operations announce their start but not their end (Load More, Load All, Refresh, filters), and an empty list says nothing.
27. Watches are fire-and-forget: nothing is kept, one refused read silences every Watch on that site, and a round can produce a burst of separate announcements.
28. Names by ear: widget areas, menus and sheets are spoken by id ("Add a Widget to sidebar-1", "12 Properties"); Gravity entries have no number; settings and Gravity values are raw stored values ("left_label (was top_label)", 0 to 6); list values print as Python tuples ("('News',)"); grammar slips such as "1 items" and "a event".
29. Confusing names: "Publish or Update" never updates; "Publish a Document as a Page" and "Publish to Another Site" make drafts; "Site Check" opens Site Health; two different "Coming Up" lists; toggles ("Activate or Deactivate", "Offer to Ask the Site", "Add New Pages Automatically") do not say which way they will go.

#### Structure and consistency

30. The site tree gives every site every plugin's branch whether installed or not (over 100 nodes per site), each selection reads the network, and discovery rebuilds the tree and collapses what you expanded.
31. The Item menu leaves out rows the context menu has (Earlier Versions, Duplicate, Change Role, Remove, Set New Password, Replace File, Edit Picture), breaking the engine's promise that More never hides anything only a right-click can reach.
32. The Properties sheet closes on OK before the save finishes, so a failure or a conflict Cancel loses the edits.
33. Consent is uneven: In Short and Ask the Site send text to an AI without asking while Visual Review asks; Make a Listening Version and Publish a Document as a Page upload without a first confirmation.
34. Shop, event and membership rows mostly name no capability, so they are never greyed and an Editor answers several dialogs before WooCommerce or PMPro refuses; choosers in those dialogs do not start on the current value.
35. QUILL Lite ignores the Form Payments switch, so payment commands run in Lite where QUILL would refuse: Lite ahead of QUILL, which the family rules forbid.
36. Escape outside the filter box goes Back to another node from any pane, so pressing Escape to leave Details jumps the tree.
37. Dozens of editor WordPress commands have no key and no written reason; the rule 8 gate cannot see them because they are not in DEFAULT_KEYMAP.

### Every review note, by section

Each line names the feature it sits under, then the note.

#### Getting connected

- The WordPress feature switch: The catalogue description promises WordPress.com, but WordPress.com sign-in is not available in this build (see Connect a Site). The description is the first thing a person reads when deciding to turn the feature on.
- The WordPress feature switch: The description says "from File > WordPress", but since the 2026-11 placement most commands live in Insert, Format, View, Edit and Tools. A person told to look in File will not find Media Library, Comments or Check Before Publishing there.
- Connect a Site: When the dialog comes back after a failure, the password field is always empty: ConnectSiteDialog never fills it from the previous answer. Any failure (a typo in the address, a slow host, a 500) means retyping or re-fetching the application password. On the browser route this is worse: the fetched password is thrown away and a new one must be minted, leaving an orphan password on the site each time.
- Connect a Site: Tier 2 reads the clipboard the instant the browser opens, before WordPress has even shown the password, so the "offer" is whatever was on the clipboard before. The module docstring says it offers the value "when focus comes back"; the code does not.
- Connect a Site: Tier 2 asks for a username when it is empty and, if cancelled, reopens Connect with an empty password field, so the pasted password is lost.
- Connect a Site: The Problem field's "&Problem:" and the password field's "Application &password:" both claim P whenever the error is shown, so Alt+P cycles between them instead of pressing (a GATE-14 duplicate that only exists on the retry, which is when a person is most likely to need it).
- Connect a Site: WordPress.com is offered as a choice, its help says "you will sign in with your browser", and the browser button's help says "For WordPress.com this is how you sign in"; the result is a dead end sentence after the dialog has already closed. Either hide the choice or keep the dialog open with the explanation in the Problem field.
- Connect a Site: "Approve QUILL in your browser..." is spoken at the moment the browser takes focus, so the screen reader is likely to talk over it. There is no way to cancel the 300-second wait from QUILL, and a listener failure is swallowed silently (the failure callback only cancels the listener).
- Connect a Site: The browser's done page says "You're signed in" before QUILL has verified anything; if verification then fails, the browser and QUILL disagree.
- Connect a Site: A failure on the browser route speaks a sentence and drops you back in the editor, while the same failure on the manual route reopens the dialog with a Problem field. Two behaviours for one dialog.
- Connect a Site: A malformed or state-mismatched reply from WordPress raises inside the success callback; no code here turns that into a spoken sentence (not found in code).
- Connect a Site: Connect and Get Password both beep with no words when the address is empty. A beep is not an explanation; a sentence in the Problem field, or speaking "Type the site's address first", would be.
- Connect a Site: "then reconnect" in the 401 sentence names an action with no command of that name; the way to replace a password is to run Connect a Site again with the same address and username, which nothing tells you.
- Sites: Add... is backwards. If you cancel the Connect dialog, the whole Sites window closes (the action returns CLOSE when the flow returns None). If you complete it, the list refreshes immediately, before the background verification has saved the new site, so the site you just added is not in the list until you close and reopen the window.
- Sites: Verify, Which Password and Remove all go through the site client, which on first use in a session also counts waiting comments and may speak "<site>: N comments waiting." in the middle of a sign-in check (the same is true of Sign Out). Unrelated news arriving with a diagnostic.
- Sites: Remove forgets the password locally but leaves it live on the site; Sign Out This Site (which does revoke it) lives in a different menu (Tools > WordPress > Manage). A person managing sites in this window will not find the safer action here.
- Sites: There is no way to change the address, username or password of an existing site from this window. "Verify" can only tell you it is broken.
- Sites: Sites and Switch Site both change the default site (Make Default, and Switch Site), with different sentences: "<name> is now your default site." versus "Default site: <name>."
- Switch Site: "Switch Site" suggests the document in front moves to another site; it only changes where New and Open start. The help text ("Choose which of your WordPress sites to use") does not say so either.
- Switch Site: It has the everyday key S while the Sites list has Shift+S, yet Switch Site is a subset of the Sites window's Make Default.
- Switch Site: After "Connect a WordPress site first." the Connect dialog opens at once, so the sentence is very likely talked over by the dialog title. After connecting, the original command does not resume. This is true of every command that calls need_site.
- Sign Out This Site: The confirmation is a two-row list with a generic "OK" button. The action is not reversible on the site, so the button should say "Sign Out", as Remove Site's says "Remove".
- Sign Out This Site: "Keep <name> in the list, to connect again later" leaves a site in the list with no password; every later command on it will fail with the 401 sentence. Nothing marks such a site in the Sites list.
- Sign Out This Site: It lives four levels deep under Tools while Connect a Site, Sites and Switch Site are in File > WordPress.
- When no site is connected: Which of the two "not a WordPress document" sentences you hear depends on whether the handler happened to pass its name; Save Draft, Publish, Properties, Open on Site, Copy Address, Trash, Compare, every block command and Image Size use the generic one.
- When no site is connected: "Connect it again with Connect a Site, and the document will find it" is only true when you reconnect with the same address and username and the old id survives; a removed site's id is gone, so the document's site id will not match a fresh connection (sites.py upsert matches by id, and a new connection after Remove gets a new id). Not verified at runtime, but nothing in the connect code looks up an orphaned document's site id.

#### The editor's WordPress commands

- The WordPress keys (the layer): Any modifier still held when the letter is pressed makes a different key. Holding Ctrl+Alt+Shift through from the prefix and pressing O says "No WordPress command on Ctrl+Alt+Shift+O." Holding Shift only turns O into "Shift+O" and S into Sites instead of Switch Site. Since the prefix itself needs Shift, this will happen often; the layer could ignore modifiers held over from the prefix, or the "No WordPress command" sentence could say "release the keys first".
- The WordPress keys (the layer): The timeout is silent. Press the prefix, think for five seconds, press P, and a "p" lands in the document with nothing said. "Left WordPress keys" on timeout, as on Escape, would cost one sentence.
- The WordPress keys (the layer): The menus spell the chord as "(Ctrl+Alt+Shift+Grave, O)" on every row, read aloud in full on every visit to File > WordPress. The QUILL key is displayed as "QUILL Key + S"; the WordPress layer gets no friendly name ("WordPress Key + O" would be shorter and match the spoken "WordPress keys").
- The WordPress keys (the layer): Only 24 of the about 45 editor-side commands have a letter. The per-page navigation commands (Next Block, Previous Block, Where Am I), the most frequent things a writer does in a block document, have none, and nothing records a reason (see "Keyless" below).
- The WordPress keys (the layer): A command failure from the layer goes through _run_command, which reports exceptions with _set_status (status bar), not speech (not verified that the status bar is spoken).
- File > WordPress (the submenu itself): The submenu has 22 rows and four separators plus a submenu; with each label carrying "(Ctrl+Alt+Shift+Grave, X)", arrowing through it is long.
- File > WordPress (the submenu itself): Several access letters are not the word's first letter and do not match the layer key (New Page is P in the menu and G on the layer; Publish is U in the menu and P on the layer; This Post in the Workbench is K in the menu and Shift+H on the layer; Compare is M in the menu and C on the layer; Sites is S in the menu and Shift+S on the layer, while S on the layer is Switch Site whose menu letter is H). The menu.py comment says "A row's own access letter wherever it is free, so the menu teaches the key", but for these rows the menu teaches a different key from the layer.
- New Page: The "Write in" radio box has no access letter, and its label is not "&Write in"; every other field in the dialog has one.
- New Page: The site is chosen inside the dialog, but for posts categories and tags are loaded from the default site before the dialog opens; choosing another site silently drops any categories and tags checked (the code sets them only when the chosen site is the default). Not an issue for pages, but the same dialog is used.
- New Post: Categories and tags are lost without a word if you change the Site choice away from the default (see New Page).
- New Post: Starting a post needs the network; starting a page does not. A writer offline cannot start a post at all, and the sentence they hear is a connection error, not "QUILL needs the site to list categories".
- New Post: A site with hundreds of tags puts hundreds of check boxes in a scrolled group with no filter.
- Open Page or Post: Four to five dialogs to open one post (site, kind, list, autosave, format). The format question comes every time and always starts on HTML; New remembers the last format, Open does not.
- Open Page or Post: The status filter only matches the raw status: rows say "Published" but typing "published" finds nothing; you must type "publish". "Pending review" rows need "pending", "Scheduled" needs "future".
- Open Page or Post: Trash and Restore from this window do not refresh the list; the row still says its old status until you close and reopen.
- Open Page or Post: Opening an item you already have a working copy of opens the local copy without checking the site, so you may edit a stale copy; the sentence tells you to run Compare yourself.
- Open Page or Post: Trashed items are mixed in with live ones in the default list.
- Open Page or Post: "<site> has no <kind>s yet." builds the plural by adding "s" to the type slug, so a custom type such as "tribe_events" is read as "tribe_eventss".
- Open Page or Post: "Opened <title> from <site>." follows a document opening, whose new window title the reader announces anyway; the site name is the only new information.
- Open by Web Address: Using the clipboard without asking is a trap: any web address copied for another reason is used silently, and if it is not on a connected site you are dropped into the Connect dialog for a stranger's site. At minimum the dialog should open with the clipboard address filled in, so the person can see and change it.
- Open by Web Address: Nothing is spoken when the clipboard is used, so the person does not know which address QUILL took.
- Open Local Draft: Silent on success, while Open Page or Post says "Opened <title> from <site>." Inconsistent, though the silent one is the GATE-13-friendlier of the two.
- Open Local Draft: "Drafts" here means every working copy, including copies of published posts; the name suggests only unsent drafts.
- Open Local Draft: No filter on a list that will grow to every item ever opened.
- Save Draft to Site: Choosing "Update the published <kind>" from Save Draft updates the live page with no further confirmation, while Publish or Update asks "Update '<title>' on <site>?". Save Draft is the command people press when they think it is safe.
- Save Draft to Site: The conflict sentence is announced immediately before the conflict dialog opens, so the dialog title is likely to cut it off; the dialog's own prompt does not repeat what happened.
- Save Draft to Site: "Open the site's copy" discards your working copy (it is kept in Previous Versions) without a confirmation.
- Save Draft to Site: The "lines could not be turned into blocks" sentence is spoken and then the send carries on; for Publish it is spoken just before the confirmation dialog, where it will be lost.
- Publish or Update: For a contributor the confirmation says "Publish" and the button says "Publish", but the item is submitted for review (target_status turns publish into pending). The question should say "Submit '<title>' for review on <site>?" when the account cannot publish.
- Publish or Update: Putting the address on the clipboard silently overwrites what the person had copied. Either ask, or say "The address replaced what was on the clipboard."
- Publish or Update: Two sentences in the Add to a Menu flow send people to "File, WordPress, Running the Site", a place that no longer exists; Menus is now Tools > WordPress > Menus.
- Publish or Update: With Cancel as the default, Enter in the confirmation cancels. Safe, but the labels passed to SetYesNoLabels ("Publish", "Update", "Publish Anyway") carry no "&", so the publish button has no access key; the route is Tab to it, then Space. Worth checking with a reader.
- Schedule Publish: The role check happens only at the very end, after the person has typed a date and confirmed twice; a contributor should hear the refusal before the dialog opens (the account is already read for the time zone call's site).
- Schedule Publish: Two confirmations in a row: the dialog's own "Schedule" button, then a "Schedule" message box. The second adds the spoken moment, which is useful, but it could be the dialog's purpose text instead.
- Schedule Publish: The date is a typed field with a format in its label; there is no date picker (deliberate for screen readers, but the label "(year-month-day)" is long to hear on every Tab).
- Open on Site: For a draft, the browser opens an address that needs a WordPress sign-in; Copy Address warns about this ("It needs a WordPress sign-in to open."), Open on Site does not.
- Copy Address: none beyond the generic "not a WordPress document" sentence.
- This Post in the Workbench: When the site is not among the Workbench's sites, the Workbench window has already been opened before the sentence is spoken, so the person lands in a window that does not show what they asked for.
- This Post in the Workbench: Menu letter K, layer key Shift+H: two different things to learn for one command.
- Properties: The outcome sentence always counts categories and tags, so a page says "Kept with your copy: 0 categories, 0 tags." Pages have neither. It also speaks when nothing changed but Apply was pressed.
- Properties: The facts a person most often wants (status, address) are on the last page of the notebook, not the first.
- Properties: A second dialog (Custom Fields) can open straight after OK with no warning; a listener may think Properties reopened.
- Properties: Opening Properties on a post needs the network (categories and tags); offline it fails with a connection sentence and the sheet does not open.
- Custom Fields: A non-number in a number field closes the dialog and discards every other field typed ("Nothing was kept; try again."). It should reopen with the values kept and the problem named.
- Plugin Fields: Custom Fields and Properties keep changes until the next send; Plugin Fields, one row below, sends immediately. Same menu, same kind of data, opposite rule; the OK label "Save to Site" is the only hint.
- Plugin Fields: Event dates and venue are always re-sent and always reported as saved, even when unchanged.
- Plugin Fields: A bad date closes the dialog and loses everything typed.
- Previous Versions: Restore replaces the text but not the title; a version with a different title restores only its body.
- Previous Versions: There is no "compare this version with mine"; the only way to see differences is to read both.
- Previous Versions: The View report is titled just "Version", which says nothing about which one.
- Compare with Site: The comparison is of your text converted to HTML against the site's HTML, so a Markdown document shows block markup lines as differences the writer never typed.
- Compare with Site: "Same" is shown in a report window rather than simply spoken; a one-line answer does not need a dialog.
- Compare with Site: No action from the report (take the site's line, keep mine); it is read-only.
- Move to Trash: "choose Trash as the status in Open" describes a control that does not exist; Open has a find field where you type "trash", and a "Restore from Trash" button.
- Move to Trash: The document stays open in the editor afterwards with its local status set to trash; nothing says what Save Draft or Publish will do next with it.
- Send This Document to WordPress: Two sentences for one action, the first while a new document window opens (likely talked over).
- Send This Document to WordPress: The title is taken from the first heading without showing it; a person cannot correct it before it lands on the site.
- Publish to Another Site: The command is named "Publish" but always creates a draft. "Copy to Another Site" would say what it does.
- Publish to Another Site: With two sites there is no confirmation before content is created on the other site.
- Publish to Another Site: In the Categories and Tags message, "Cancel" does not cancel: it carries on and copies without them. A Cancel button that continues the action breaks a universal expectation; the buttons should be "Create Them" and "Copy Without Them", with a real Cancel.
- Duplicate: In a WordPress document, Duplicate copies the site's copy, not your unsent edits; Publish to Another Site copies your local text. Neighbouring rows, different sources, no word about it.
- Duplicate: With one site, Duplicate in a document creates a draft on the site with no confirmation at all.
- Duplicate: The item list is a plain choice with no filter.
- Send a Folder as Drafts: Every file becomes a post; there is no Post or Page choice, unlike Send This Document.
- Send a Folder as Drafts: Only the first failure is named.
- Download My Writing: "Saving ... QUILL says when it is done." is spoken before the permission check; a refused account then hears a second sentence contradicting the first.
- Download My Writing: The final sentence always ends with a long "Left out:" list, every time, even on a resume that saved nothing new.
- Insert menu rows (overview): Every one of the seven WordPress access letters collides with an existing Insert row in QUILL: "WordPress &Block..." (B) with "Insert Code &Block"; "Pict&ure from the Media Library..." (U) with "Q&uick Insert..."; "Picture from This &Computer..." (C) with "Insert &Citation..."; "Li&nk to a Page on This Site..." (N) with "I&nsert HTML Tag..."; "N&ote on This Block..." (O) with "Insert Em&oji..."; "Make a Pictu&re..." (R) with "Insert Horizontal &Rule"; "WordPress &Icon..." (I) with "L&ist". In a Windows menu a repeated letter cycles the highlight instead of choosing, so none of these rows can be chosen by its letter. menu.py chose these letters for QUILL Lite's menus; nothing checks them against QUILL's.
- WordPress Block: Menu says "WordPress Block", the window says "Insert Block", and the no-blocks sentence elsewhere says "Insert one with Insert Block". Three names for one command.
- WordPress Block: Enter on a row does nothing (no on_enter); you must Tab to Insert. Every other picker in this family (Open, Notes, Fix Link Text) honours Enter.
- WordPress Block: It needs the network even for QUILL's own core blocks; offline, nothing can be inserted.
- Picture from the Media Library: Inserting a picture now opens a whole second window (the Workbench) rather than a dialog; for a screen-reader user that is a heavy context switch for a common task, and you must find your way back.
- Picture from the Media Library: "Use Upload Files" points at a command in Tools > WordPress > More Media without saying where.
- Picture from This Computer: Undoing the insert leaves the picture queued for upload (the pending upload is kept in the working copy and uploaded on the next send if the file exists; _upload_pending replaces the address only if it is in the text but uploads either way).
- Link to a Page on This Site: No filter on what can be hundreds of rows; first-letter navigation in a list box is the only help.
- Link to a Page on This Site: Drafts and scheduled pages cannot be linked to, with no word about why they are missing.
- Note on This Block: The note is sent to the site immediately, while the tie to the block waits for the next send; Undo in the editor takes back the tie but leaves an orphan note on the site.
- Note on This Block: The "protected line" warning is a heavy consequence (the block's words become uneditable in Markdown) for adding a comment; worth surfacing in the menu row or offering to switch to HTML.
- Make a Picture: It is not document-only, so a person can spend AI time making a picture in an ordinary document and only learn at Insert that "This is not a WordPress document...".
- Make a Picture: A made picture uploads the moment you insert it; a picture from this computer waits for the next send. Same menu, two rules.
- WordPress Icon: the refusal names it "Insert Icon"; the menu row says "WordPress Icon".
- Block Settings: needs the network just to read colours; offline, no settings can be changed at all.
- Image Size: replace_text rewrites the whole document; the caret is then put back at the picture with go_to_offset, which is good.
- Mark Language: With nothing selected the whole page is wrapped with no confirmation; forgetting to select is the likely mistake, and the result changes the language of everything. A confirm, or "Nothing is selected: mark the whole page?", would catch it.
- View menu rows: Three of the four access letters collide in QUILL's View menu: "WordPress &Blocks..." (B) with "&Browser Preview..."; "Pre&view Blocks" (V) with "Pre&view Side by Side"; "B&lock Notes..." (L) with "Announce &Lists". Only Play Media Here's M is free (from the rows found in main_frame_menu.py).
- WordPress Blocks: After Move Up or Move Down the list keeps the same row number selected, so the selection stays put while the block moves; pressing Move Up twice swaps the pair back. The Rows type in wordpress_dialogs.py exists for exactly this ("a row moved down follows the row") and is not used here.
- WordPress Blocks: No Enter action; Enter on a row does nothing (Go To is a button).
- WordPress Blocks: Menu "WordPress Blocks", window title "Blocks", and the no-blocks sentence names "Insert Block", which the Insert menu calls "WordPress Block".
- Preview Blocks: the failure count is spoken only after you close the report, when it is no longer useful; it belongs at the top of the report.
- Block Notes: the list is updated optimistically before the site answers; if the reply fails, the list still shows it.
- Play Media Here: "Insert from Media Library" is not the menu's name ("Picture from the Media Library...", which also inserts audio and video despite saying "Picture").
- Edit > WordPress (submenu): The one submenu a writer would visit most while working in a page has no letter (the Edit menu's W is "&Word Prediction..."), and none of its rows has a chord, so moving block by block means Alt+E, arrows, Enter, N for every block. This is the strongest case in the section for a key.
- Edit > WordPress (submenu): The Command Palette now has two commands titled "Next Block" (navigate.next_block and wordpress.next_block) and two titled "Where Am I" (verbosity.where_am_i and wordpress.where_am_i), with no way to tell them apart by name.
- Hear Where a Link Goes: The target sentence is spoken and then repeated as the first line of the confirm that opens at once, so it is said twice, and the spoken copy is the one likely to be cut off.
- Hear Where a Link Goes: A "hear" command that turns into an "insert a link" command when there is no link at the caret is a surprise; the two would be clearer as separate rows.
- Fix Link Text: Each fix rewrites the whole document with replace_text and never puts the caret back, so after closing the window the caret is at the end of the document, far from where you were.
- Fix Link Text: Use All is several Undo steps, not one, unlike every Blocks window change.
- Fix Link Text: There is no way to type your own words for a link from this window; the only choices are the page title or nothing.

#### The editor's WordPress commands

- Open WordPress Workbench...: It is the only row in the submenu with no access letter. Opening it from the menu means arrowing to the top of the submenu or knowing the H layer key.
- Open WordPress Workbench...: The trailing "..." suggests a dialog, but it opens a full peer window.
- Check Before Publishing...: The summary is announced just before a modal opens, so the dialog title announcement may cut it off. The purpose text that repeats it is reachable only with F1.
- Check Before Publishing...: When there are no findings, nothing opens and only the summary is spoken. That is good, but it is the only feedback.
- Check Before Publishing...: Go to It on a conversion-problem row is a guaranteed dead end. Those rows could go to their line number instead.
- Check This Page: The summary is announced right before the modal opens, so it can be cut off.
- Check This Page: A list with zero findings still opens a window with an empty list. Unlike Check Before Publishing, there is no early return when nothing was found.
- Check This Page: The name says "This Page", but from a non-WordPress document it silently checks the site's home page. The chooser does not say so.
- Check the Whole Site...: Access-key collision (GATE-14): the list label "&Problems:" and the "&Pages..." button both claim P in one window, so Alt+P cycles focus instead of pressing. check_access_keys.py cannot see this, because the labels are runtime arguments to the shared ListWindow.
- Check the Whole Site...: Reading every page can take a long time with no progress sentence; only the visitor pass reports progress.
- Check the Whole Site...: Fix in Bulk is two modals in a row, the preview report and then the confirmation. Closing the preview with Escape does not cancel; the confirmation still follows.
- Undo Site Fix...: Only covers Fix in Bulk and Site-wide Find and Replace. Manage > Bulk Edit has its own separate "Undo Bulk Edit", and Style Variations and Site Styles have "Put Back the Previous Look". That is three undo models for site-wide changes.
- Undo Site Fix...: Fixes that were already undone stay in the list. It is not clear from the code whether their spoken rows say so.
- Site-wide Find and Replace...: Grammar: the confirmation always says "matches", so one match reads "Replace 1 matches of ...".
- Site-wide Find and Replace...: It takes three modal steps before any search. A single dialog with Find, Replace with, Match case and Pattern controls would be faster and closer to Word's Replace.
- Site-wide Find and Replace...: Toggling a match does not say the new state, but the row text changes ("Included" or "Skipped" first), which the list re-reads. That is fine.
- Write an Accessibility Statement...: The draft is Markdown or HTML according to the format last chosen in New Page or New Post (self._last_format), not a choice offered here.
- Write an Accessibility Statement...: Leaving the contact empty and pressing OK still makes a statement with an empty contact. No check is made.
- Palette Report: The title has no ellipsis but opens a report. That is inconsistent with the other rows.
- Palette Report: A classic theme silently gives "could not read a colour palette", with no hint that block themes are needed. Design > Style Variations does explain this.
- Palette Report: The same palette data is in Design > Style Variations and in Manage > Previous Looks > Palette Report. That is three doors to one report.
- In Short...: It sends page text to AI with no "this will send N words to {AI}" confirmation. Visual Review asks first; this does not.
- In Short...: The trailing "..." suggests a dialog, but none opens.
- In Short...: It is a content-writing command, not site upkeep. It sits oddly in Tools beside site checks.
- Media Library...: The code comment "the developer flag sends this door to the WordPress Workbench" is stale. There is no flag check.
- Media Library...: Access letter B, but the layer key is M. WordPress key, then B, opens View > WordPress Blocks instead.
- Alt Text Review...: Edit and Mark Decorative speak nothing afterward; only the row text changes. Suggest does announce. That is inconsistent.
- Alt Text Review...: The Alternative Text box is multiline, so Enter adds a new line instead of pressing OK. The user must Tab to OK.
- Alt Text for the Whole Library...: Close saves. That is good for a long session, but Escape (usually "cancel") silently sends pending descriptions to the site.
- Alt Text for the Whole Library...: The save on close announces after the window is gone. That is fine.
- Visual Review...: It should be on DOCUMENT_ONLY (or work on the home page the way Check This Page does). Today it is enabled everywhere and refuses with a sentence that names File > WordPress rather than this command.
- Visual Review...: It is a good model of consent before sending; In Short and Ask the Site should match it.
- More Media > Upload Files...: There is no way to cancel the whole batch from a details dialog. With 20 files, the user must Cancel 20 times.
- More Media > Upload Files...: Enter in the multiline Alt box adds a line instead of pressing Upload.
- More Media > Paste Image: It is an insert-into-this-page command filed under Tools > More Media, while Insert has "Picture from This Computer". Paste Image belongs beside it, or in Edit.
- More Media > Paste Image: It should be on DOCUMENT_ONLY.
- More Media > Paste Image: No "..." even though a dialog opens.
- More Media > Upload a Large File...: It puts the address on the clipboard without being asked, and Upload Files does not. That is inconsistent and overwrites the clipboard.
- More Media > Upload a Large File...: Having both "Upload Files" and "Upload a Large File" makes the user decide what "large" means. The code could choose for them.
- More Media > Make a Smaller Copy...: three modals plus a confirmation for one shrink. A single dialog holding the width and format choices would halve the steps.
- More Media > Edit a Picture on the Site...: one command can chain up to five modals and several announcements. The follow-ups (Use here, Regenerate) could be check boxes in the first confirmation.
- More Media > Site Logo...: Access-key collision (GATE-14): the list label "&Logo and icon:" and the button "From the &Library..." both claim L in one window.
- More Media > Site Logo...: After a replace the list rows are not refreshed (the actions return None), so the window keeps showing the old logo until it is reopened.
- More Media > Site Logo...: The menu title "Site L&ogo" uses O, which is also the submenu's own letter (M&ore). That is harmless but means pressing O twice.
- More Media > Preview and Review...: The refusal sentence is about 60 words, far longer than the one-sentence rule the other commands follow.
- More Media > Preview and Review...: It overlaps with Site Logo > Preview a Width.
- More Media > Captions for Video...: A Cancel after minutes of transcription is silent and loses the work. A "Discard the captions?" confirmation, or keeping a draft, would help.
- More Media > Captions for Video...: It should be on DOCUMENT_ONLY.
- More Media > Make a Listening Version...: the first time, it uploads a file to the site with no confirmation at all; only a remake asks.
- More Media > Name Embeds: It edits the document with no preview or confirmation; the report comes after the fact.
- More Media > Name Embeds: It is a this-page command filed under media upkeep.
- More Media > Publish a Document as a Page...: The name says "Publish", but it uploads the original and opens a draft. The menu name overpromises.
- More Media > Publish a Document as a Page...: In the duplicate prompt, Cancel (and Escape) means "upload a second copy". Cancel starts an action instead of stopping one, which is backwards for a keyboard user.
- More Media > Publish a Document as a Page...: The original file is uploaded to the site with no confirmation.
- Comments...: the legacy comments window under this door is unreachable from the menu, though cmd_comments(status=...) can still be called with another status from elsewhere.
- Menu History...: "1 items back" grammar.
- Menu History...: Menus now opens the Workbench, but Menu History is a separate legacy window beside it, and the Workbench has its own "Earlier Versions". That is two histories reached two ways.
- Menu History...: The classic-menu empty message is about 50 words.
- Site Check: the name "Site Check" sits beside three other "Check" rows but means Site Health. Calling the row "Site Health" would match the node it opens and WordPress's own name.
- Design > Site Styles...: The list rows update to the new value as soon as Yes is pressed, before the save comes back. A failure then leaves the list showing a value the site does not have.
- Design > Site Styles...: It is good that the confirmation says the contrast before anything is saved.
- Plugin Extras > Events Coming Up...: the chooser and window are titled "Coming Up", the same as Your Sites > Coming Up, which is a different list (scheduled posts across sites). By ear the two cannot be told apart.
- Plugin Extras > New Event...: Dates are free text in one fixed format. A wrong guess closes the dialog and loses everything typed. Validation should keep the dialog open.
- Plugin Extras > Shop Orders...: a confirmation before a clipboard copy is unusual, but it is justified by the personal data, and it is clearly worded.
- Manage > Synced Patterns...: the menu says "Synced Patterns", but the node is "Patterns". Whether the Workbench filters it to synced patterns is not in this code.
- Manage > Site Map...: "Site Map" opens a node named "Pages", while Page Order (two rows down) is a separate legacy tree window over the same pages.
- Manage > Template Outline: there is no "..." although a window opens. Indentation by depth is hard to hear in a plain text box; a tree, or "level N" prefixes, would carry the structure.
- Manage > Bulk Edit...: The list rows are not refreshed after Change, so status and author still read the old values.
- Manage > Bulk Edit...: "1 posts" grammar.
- Manage > Bulk Edit...: The Workbench has its own batch editing (Phases 7 to 10), so this window duplicates it.
- Manage > Page Order...: Moves go live on the site with no confirmation and no undo, so a mistaken Alt+I re-parents a page in public menus.
- Manage > Page Order...: Focus returns to the list after a move, but because the rows are rebuilt the selection stays at the old index, not on the page that moved. The row the user hears next may be a different page.
- Manage > Previous Looks...: the window title lacks the site name, unlike its siblings ("Style Variations, {site}").
- Manage > Space Used: no "..." although a report opens. The total is announced and then repeated in the report.
- Manage > AI Abilities...: The menu says "AI Abilities", but the node and the legacy window say "Abilities".
- Manage > AI Abilities...: Ask the Site's refusal tells the user to "Turn them on one by one in Abilities", which now means a Workbench node. This code does not confirm that the Workbench node writes the same per-site choices (ability_choices).
- Manage > Ask the Site...: The question is sent to the AI with no consent step. Only running an ability asks.
- Manage > Ask the Site...: The Question box is multiline, so Enter adds a line and Tab then Enter is needed to ask.
- Manage > Sign Out This Site...: It cannot be undone, and the only step is a two-row chooser whose preselected row is the more destructive one ("Remove"), with OK as the default. Enter twice (menu, then dialog) signs out and removes the site. There is no named confirmation, unlike every other destructive command here.
- Manage > Sign Out This Site...: With one site there is no site chooser, so nothing on screen names the site before the chooser.
- Manage > Sign Out This Site...: It calls self.api(profile) first, so on first use in a session it may announce "{site}: N comments waiting." just before signing out.
- Your Sites > Coming Up...: Bug: Open or Enter on a "Did not answer: ..." row reads items[index] past the end of the list (open_it has no bounds check), which raises an exception instead of speaking.
- Your Sites > Coming Up...: "1 sites did not answer" grammar.
- Your Sites > Coming Up...: When every site fails and nothing is scheduled, no list opens, so the failed sites are named nowhere, unlike What Changed.
- Your Sites > What Changed on My Sites...: The "looked at" mark is set before the user has read the list, so closing it by accident loses the changes.
- Your Sites > What Changed on My Sites...: Enter on a row does nothing (no on_enter), while Enter opens the item in Coming Up. The two sibling windows behave differently.

#### QUILL Lite differences

- Where the rows sit in QUILL Lite: Lite's Tools menu has 30 entries, and the two submenus a WordPress user needs most are the last two, with no letter. That only works if the user knows that Up Arrow wraps to the bottom. No label says so.
- Access letters: what Lite has and QUILL computes: This is the biggest Lite-versus-QUILL gap in this area. In QUILL every keyless Forms and WordPress row says its Alt path aloud. In Lite the same row says nothing, and its parent submenu has no letter to type. The house rule that every enabled item shows a keyboard route is met in QUILL and not in Lite. That is the permitted direction (Lite behind QUILL), but it is a real cost on every visit.
- Access letters: what Lite has and QUILL computes: The layer letters and the menu letters disagree for eight rows. The table comment says "A row's own access letter wherever it is free, so the menu teaches the key", but File > WordPress has New &Page (layer G), P&ublish (layer P), Co&mpare (layer C), Switc&h Site (layer S), &Sites (layer Shift+S) and This Post in the Wor&kbench (layer Shift+H). Tools > WordPress has Check Before &Publishing (layer K) and Media Li&brary (layer M). The menu does not teach the layer key for these. Because the bracketed chord is in the label, you hear both and have to ignore one. This is the same in both editors.
- The WordPress key layer (shared, with three small differences): Responses' label advertises a key that can be dead. If Forms is on and WordPress is off (separate features in QUILL, separate areas in Lite), both editors still show "Responses... (Ctrl+Alt+Shift+Grave, F)". The prefix is refused, though, because the layer belongs to WordPress. A Forms-only user is shown a chord that does nothing and is not told why.
- The WordPress key layer (shared, with three small differences): In Lite, a layer command reached on a document under the Read-Only Guard runs anyway. Every Forms command that rewrites the document (Insert Form Field, Outline moves, Form Rules, Form Properties, Plain Language, Payments Setup) writes through `WriteText` on the control. Whether a read-only native edit control accepts that is not proven here; verify by hand. The menu route behaves the same way, since `_dispatch` also goes through `run_unless_read_only` and finds nothing to refuse.
- The WordPress key layer (shared, with three small differences): The "WordPress keys" announcement is correct under GATE-13, because the prefix changes nothing on screen.
- Document-only dimming: Insert Form Into Page is enabled in every document, but it only works in a WordPress page. It could be dimmed by the WordPress `DOCUMENT_ONLY` test instead of always being enabled, and right now it is the only Tools > Forms row that is enabled in places it cannot work.
- Document-only dimming: A form is recognised only by its file name. An unsaved buffer holding QAF text, or a form saved under another extension, dims every Forms row.
- Command Palette, profiles and feature areas: Lite has no Form Payments gate. `_payment_document` asks the host's editor for `_feature_enabled("core.forms_payments")`. A Lite window has no `_feature_enabled` method, so the check is skipped and Form Payments Setup, Insert Payment Field and Verify Payment Setup always run in Lite whenever Forms is on. In QUILL, with Form Payments off, the same rows stay visible and say "Turn on Form Payments in Features before using this command." This is a divergence, and in the "Lite has it, QUILL may not" direction the house rule forbids.
- Command Palette, profiles and feature areas: In QUILL, those three payment rows stay on the menu and enabled with the feature off. You find out the feature is off only by choosing one.
- Command Palette, profiles and feature areas: Both editors describe Forms as local when it is not. The Lite area description ends "Everything here runs on this computer", and QUILL's feature description says "Runs on this computer". But Publish Form, Insert Form Into Page, Test on Site, Responses, Verify Payment Setup and the three AI rows all reach a site or an AI.
- Command Palette, profiles and feature areas: Lite's Everything profile calls AI help "the one area here that does something outside this computer". WordPress and Forms also reach the network.
- Words that say QUILL inside QUILL Lite: A Lite user hears "QUILL" for the editor they are in. Whether that is acceptable branding, or whether these strings should name the product through the host, is the owner's call.

#### Forms (QAF)

- Forms in the menus, and the one Forms key: With 17 rows in four groups, Tools > Forms is long. The editing commands (Check, Fill In, Properties) are mixed in with payments.
- Forms in the menus, and the one Forms key: Payments has three rows here, and a fourth door through the payment kind in Insert Form Field.
- New Form: The announcement uses "a" before every template name: "a event registration with 4 questions" and "a accessibility feedback with ...". It is also odd for "a blank with 1 question".
- New Form: The dialog's purpose is reachable only through F1. Nothing on screen states it.
- New Form: Cancelling silently is correct here.
- Insert > Form Field: The payment kind is offered in the list even where Form Payments is turned off in QUILL. It then answers with the Features refusal.
- Insert > Form Field: When choices and a library are both left empty on a choice kind, a placeholder "Choice 1" is added without saying so.
- View > Form Outline: Cancelling Rename, Change Id or Change Type speaks "Nothing changed." That is a spoken result for a cancel, where every other Cancel in Forms is silent. This is mild chattiness.
- View > Form Outline: An Alt+Shift+arrow move on a disabled action only beeps (`wx.Bell`). Nothing is spoken.
- Format > Form Rules: Enter or Go to It on a free-standing rule row (the kind stored in the form's rules list) does nothing at all, silently (`go` returns None when the row's kind is "rule"). The list help promises "Press Enter to go to the question it is on."
- Format > Form Rules: The Add Rule dialog's Then default is "show" and its target default is the last question. A rule added with every default is "Show {last question} when {first question} is """. That is valid, but probably not what was meant.
- Tools > Forms > Check This Form: Check Again is a dead end. The window is modal, so you cannot change the form while it is open, and "Check Again after you change it" can never show anything new. When Check Again does empty the list, nothing is spoken.
- Tools > Forms > Fill It In Yourself: Submit does not check the last page's required questions the way Next does. It only lists them at the bottom of the report.
- Tools > Forms > Fill It In Yourself: Next both moves focus (which the screen reader reads) and announces the page heading. Those two can talk over each other. The heading is not otherwise spoken, so the announcement is allowed under GATE-13, but listen for collisions.
- Tools > Forms > Form Properties: Emptying the Title is silently ignored: the old title is kept, with no message.
- Tools > Forms > Form Properties: The read-only box's label "On the site (read only):" has no access key, so the only way to reach the box is Tab.
- Tools > Forms > Form Properties: It says "saved in the document" even when nothing changed.
- Tools > Forms > Form Payments Setup, Insert Payment Field, Verify Payment Setup: Insert Payment Field always adds the field at the end of the last page, whatever the caret position. Insert Form Field places items at the caret.
- Tools > Forms > Form Payments Setup, Insert Payment Field, Verify Payment Setup: The Lite gate bypass is described under QUILL Lite differences.
- Tools > Forms > Publish Form: After the first publish, Publish Form never asks for a site again: the stored link wins (`choose_site` returns the preferred site first). There is no route in the editor to publish the same form to a second site.
- Tools > Forms > Publish Form: Nothing is spoken while QUILL reads the site and then publishes. The task names ("reading {site}", "publishing to {site}") are not announced, so on a slow site there is silence between the button and the result.
- Tools > Forms > Responses (the editor's Responses window): Access-key collision. The list label "&Responses:" and the button "&Read" both claim R in one window. Under GATE-14, Windows cycles between the two instead of pressing, so Alt+R may never press Read. The dialogs are built at runtime, so the static gate may not see it. Verify.
- Tools > Forms > Responses (the editor's Responses window): Refresh Payment Status is the first button in the bar, and is shown for every form, payment or not. The first Tab stop after the list is a payments command most forms never need.
- Tools > Forms > Responses (the editor's Responses window): Delete takes the rows out of the list before the site has answered. If the delete then fails, only the failure sentence is spoken, and the rows stay gone from the window until it is reopened.
- Tools > Forms > Responses (the editor's Responses window): Mark is silent. Whether the reader re-reads the changed row after `set_rows` is not certain. Listen for it.
- Tools > Forms > Responses (the editor's Responses window): From a published form document, Responses always opens that form. To read another form's responses you must first switch to a document that is not a form. Nothing says so.
- Tools > Forms > Responses (the editor's Responses window): This window and the Workbench's Responses do different jobs. The editor has Read, Find, Mark, Export, Summarise and Delete, but no Spam or Not Spam. The Workbench has Spam, Not Spam, Search on the Site and Saved Views, but no Delete and no Export of QAF responses. Someone handling spam and exports has to use both.
- Tools > Forms > Draft a Form, Plain Language, Suggest Autofill Hints: Draft a Form sends as soon as you press OK. Only a spoken sentence comes first, with no confirmation, which is acceptable because only your own description goes. Summarise asks every time, as it should, because it sends people's answers.
- Tools > Forms > Draft a Form, Plain Language, Suggest Autofill Hints: "The draft is in ... Undo takes it out" replaces the whole form, including any rules or properties you wrote. The confirmation says "replace the form in front", which is honest, but it is a large single step.
- Workbench: the Forms node and its rows: Four nodes say "Responses" or "Held as Spam" in two places each. Forms > Responses and Attention > Form Responses are the same thing under two names. Forms > Held as Spam and Attention > Held as Spam share a name and differ in scope (the Attention one also has comments).
- Workbench: the Forms node and its rows: The 300-row and 3-page caps cut the list silently. A busy form shows fewer responses than its count, and nothing says the list is partial.
- Workbench: the Forms node and its rows: The response row's help mentions only Gravity Forms extras. It never says that Ctrl+Shift+S marks spam and Ctrl+Shift+A releases.
- Workbench: Show Its Responses (on a form row): The filter goes by the form's title, not its id. Two forms with the same title, or a title that is part of another title, may share one filtered list. This is plausible from the code; verify how the filter matches.
- Workbench: Show Its Responses (on a form row): It shows only Received responses. Held-as-spam responses to the same form are in a different node, and nothing tells you they exist.
- Workbench: Change Form Status (QAF form row): The preview's summary uses the raw status word ("becomes inactive", "becomes active") while the lines and the result use the friendly phrase ("closed, shown but not taking responses"). Two vocabularies in one preview.
- Workbench: Change Form Status (QAF form row): There is no undo, and no Change History entry. A Ctrl+Z pressed afterwards undoes whatever was recorded before, which may be an earlier spam mark, not this status change. This is plausible from the `_record` and history design; verify.
- Workbench: Form Settings (QAF form row): Settings are shown by their raw keys with underscores turned into spaces (for example "save continue enabled"). They are not friendly labels.
- Workbench: Form Settings (QAF form row): Only one setting can be changed per trip. Changing three means three round trips through the menu.
- Workbench: Saved Views and Search Responses on the Site (QAF form row): Saved Views is offered on one form's row but lists every view on the site. Views of other forms are named "form {id}", because only this form's title is known.
- Workbench: Saved Views and Search Responses on the Site (QAF form row): Search results are a read-only report, not rows. You cannot mark a found response as spam, or open it, from there. It searches Received responses only (`status: active`), so held spam is never found.
- Workbench: Delete Form (QAF form row): Pressing Cancel at the name question also says "The name typed did not match, so nothing was deleted." That reads as an error for a deliberate cancel.
- Workbench: Delete Form (QAF form row): "Export the responses first (Tools > Forms > Responses)" sends a Workbench user to the editor's menu, because the Workbench cannot export QAF responses itself.
- Workbench: Not Spam and Spam (on a response row): "and the site was told" is said even when an older QAF only moved the response and told nobody. `mark_entry` returns the providers it told, and nothing reads that list.
- Workbench: Not Spam and Spam (on a response row): The wording is borrowed from comments. Marking a response spam says "1 item marked as spam", and Not Spam on a response that was not held says "1 item approved". Responses are never "approved".
- Workbench: Not Spam and Spam (on a response row): Item > Unapprove (Ctrl+Shift+U) on a response acts as Not Spam but announces "1 item unapproved on {site}."
- Workbench: Not Spam and Spam (on a response row): Undo reverses every selected response, including any whose change failed. After Not Spam on a response that was already Received, Ctrl+Z marks it as spam. Plausible from `_moderate`; verify.
- Workbench: Not Spam and Spam (on a response row): The permission refusal talks about "Editing posts" when the person is marking a form response. That is accurate to the capability, but confusing.
- Workbench: Not Spam and Spam (on a response row): QAF responses also show Notes... and Resend Notifications... in the context menu (the Gravity rows are shared). Both refuse with "That is a Gravity Forms command. Choose a Gravity Forms form, entry or feed; QUILL Accessible Forms keeps no notes, feeds or notifications." Star or Unstar and Mark Read or Unread do work on QAF responses ("Starred {n} entries on {site}." and similar, with undo). The node help says these four are Gravity Forms only.
- Workbench: the site row's QAF spam commands: Cancelling the Question prompt of Add a question announces "A question needs its words and at least one right answer. Nothing was added." That is a reproach for a deliberate Cancel.
- Workbench: the site row's QAF spam commands: The Spam page's save remembers the revision read when the sheet opened. A second Apply in the same sheet, after a first that succeeded, sends the old revision and is likely to be refused as a conflict caused by your own first save. Plausible from `site_sheet_with_spam`; verify.
- Workbench: the site row's QAF spam commands: `on_save` returns True as soon as the background save starts. The sheet can close before a conflict is reported, and the edits typed into it are lost with it.
- Workbench: the site row's QAF spam commands: These two commands sit on every site row, including sites with no QAF. There they answer "This site has no QUILL Accessible Forms." only after a background read.

#### The WordPress Workbench window

- Opening it: Start Here still says "This is an early preview, behind a developer setting. Your Tools > WordPress windows still work." (workbench_help.py START_HERE). Both sentences are false now: there is no developer setting and the doors always open the Workbench. The first thing a new user reads is wrong.
- Opening it: A door opens on the FIRST site in the store, not the default site and not the site of the open document: current_site() falls back to next(iter(self._profiles)) because frame.current is still None when _start_ref runs. With two sites, Tools > WordPress > Users from a document on site B opens site A's Users.
- Opening it: The window does not remember its place across closes. The frame supports recall_place/remember_place hooks, but the WordPress provider implements neither, so every fresh open starts at Inbox with the tree collapsed. The GitHub Workbench does remember.
- Opening it: Closing the Workbench silently stops a running Practice Site. A person who opened the practice site from here and closes the window to write in the editor loses it without a word.
- Opening it: The workbench_door docstring (wordpress_commands.py) still says it returns False "without the developer flag"; it never does. Harmless to users, misleading to maintainers.
- Layout and panes: Start Here's words live in the Details box, but Ctrl+9 leaves focus on the tree, over an empty list. A first-time user has to press F6 three times (filter, list, details) to read the page they asked for. Ctrl+9 should land in Details, or Start Here should open its text where focus goes.
- Layout and panes: Escape outside the filter box goes Back to the previous node, from any pane, including Details. "Read in Full" (Enter on a comment, plugin, fact and many other rows) moves focus to Details; the natural Escape to return to the list instead navigates the tree to a different node and throws away the list you were reading. Escape in Details should return to the list.
- Layout and panes: Backspace in the tree goes Back. The native tree's type-ahead uses letters, so this is safe, but Backspace as navigation is a browser idiom that surprises in a tree.
- The tree: Every site gets every plugin's branch whether or not the plugin is installed: Shop alone is 16 nodes, Events Calendar 6, Memberships 6, plus SEO, Podcast, Forms' Feeds and Results. That is well over 100 nodes per site, most of which, on a typical site, load only a sentence such as "<site> does not list WooCommerce's wc/v3 routes in its REST index, so it has no shop QUILL can read." For a screen-reader user arrowing through a site this is the single biggest cost in the window. Hide or collapse branches whose namespace is absent from the site's REST index.
- The tree: Every tree selection fires a network load. Arrowing down through a site sends a request per node passed (stale answers are dropped, but the requests still go out). A short delay before loading, or loading only on Enter or a pause, would cut the traffic and the "Loading" churn in the status bar.
- The tree: Discovery rebuilds the whole tree once per connected site shortly after opening. rebuild_tree deletes and re-adds every item, so any branch you expanded in the first seconds collapses again, and the current node is re-selected (the reader may say it again) and its list reloaded. Keep expansion state across rebuilds, or add discovered nodes in place.
- The tree: "Drafts" under Needs My Attention is "Your own drafts, on every site" (NODE_HELP), but the label is just "Drafts", the same word as Posts > Drafts. "My Drafts" would say what it is.
- The tree: "Site Health" and "Held as Spam" each appear twice with different meanings (across sites under Needs My Attention, and per site). The labels do not say which is which; only the position does.
- The tree: Search has no Go key and no menu row; it is reachable only through the tree, and it only works with words typed into the filter box, which is not obvious from the node name.
- The list: Column headers and the Columns dialog disagree on names: the list header is name.replace("_", " ").capitalize() in the frame, the dialog uses column_title, which renames some ("mime_type" is "File type" in the dialog, "Mime type" in the header; "id" is "Number" in the dialog and "Id" in the header). One function should name a column everywhere.
- The list: The Columns dialog's help says "Check each column the list shows, in this order. The first is what your screen reader says first." but the dialog cannot reorder anything; the order is fixed. Either offer Move Up and Move Down or drop "in this order".
- The list: Column choices, groupings and Load More depth are kept in memory only (column_choice, grouping, paging on the provider) and are lost when the window closes.
- The list: Group By counts come from the rows currently loaded and filtered (frame.rows), not from the site, so "Draft (12)" can be the 12 among the first 300, not the site's total. The node label gives no hint.
- The list: Load More, Load All, Refresh and remote filters announce when they START but never when they finish. A blind user hears "Reading every row. A big site takes a while." and then silence, with no signal that the list is ready except polling the Loading status cell. GATE-13 does not forbid saying a background result; "Loaded 1,240 rows." is exactly the kind of thing the reader cannot know.
- The list: The precise sentence cut_words builds ("The first 300 are shown, and the site has more. View > Load More reads 300 more; Load All reads every one.") is computed and stored but never shown or spoken; only the terse ", more on the site" reaches the Items cell.
- The list: "More on the site" is decided by count >= limit, so a site with exactly 300 posts is told there are more.
- The list: An empty list says nothing. "No comments are waiting on Radio." in Details (via the empty_text hook) would answer the first question a listener has.
- The list: Ctrl+A and Ctrl+C do nothing in the list: the frame has select_all and copy verbs, but the WordPress menu binds neither, and a native list view does not select all on Ctrl+A. Select-all-and-act is a common screen-reader workflow (for example Approve all waiting comments).
- The list: After any refresh the landing row is selected alone (focus_row deselects the others), so a multi-selection is lost after every batch action.
- The filter box and filter commands: Ctrl+Shift+F never opens the Filter Builder. The frame's key hook (_on_char_hook: "if event.ControlDown() and event.ShiftDown() and code is F: self.filter.SetFocus()") runs before menu accelerators (the keep_list_key docstring states that order), so the chord only moves to the filter box. The menu shows Ctrl+Shift+F, the filter box help and the Keys node both teach it, and only the menu click works. This is a GitHub-only alias leaking into WordPress.
- The filter box and filter commands: The same hook catches Ctrl+Alt+Shift+F (it checks Control and Shift, not Alt), so Tools > Forget a Saved Request's chord also just moves to the filter box.
- The filter box and filter commands: "Filtering." is said and then nothing: the listener never hears how many rows the site sent back. Say "<n> shown." when the remote answer fills the list.
- The filter box and filter commands: Filter wording is raw: Only Mine adds author:7, so Alt+1 says "filtered to author is 7", and the Filter Builder asks for "Author number" and "Parent number". People do not know their user number. describe() takes attribute labels but the WordPress window never passes any.
- The filter box and filter commands: The Filter Builder offers "after" and "before" for every attribute, including Status and Slug, where they mean nothing, and offers no "contains". Operators should follow the attribute.
- The filter box and filter commands: Only Mine's refusal ("once the site has said who you are") is wrong when the real problem is that you are on Needs My Attention or another non-site node.
- The filter box and filter commands: Edit > Filter... has an ellipsis but opens no dialog; it only moves focus.
- The filter box and filter commands: Filters are cleared without a word when you change nodes. A listener who filters Posts, checks Pages and comes back finds the filter gone. At least the Filter status cell shows "No filter".
- The filter box and filter commands: describe_scope in workbench_filter.py (the "Filtered on this computer, 12 rows loaded" sentence the docstring promises) is not used anywhere in the UI.
- The Properties sheet and Site Properties: WordPress gets the simpler sheet. GitHub's PropertiesSheet has Ctrl+S to apply, Ctrl+Enter for OK from a multi-line box, F5 reload, Ctrl+1 to Ctrl+9 page jumps, Ctrl+Shift+C copy, a "Sheet status" line showing what the last save did, and opens on the last page used. The WordPress sheet has none of these, so the two Workbenches teach different keys for the same window.
- The Properties sheet and Site Properties: OK closes before the save is done. If the save then fails, or a conflict is answered Cancel, the typed changes are gone with no way back. Keep the sheet open until the site answers, or reopen it with the edits on failure.
- The Properties sheet and Site Properties: Apply twice in one sheet will likely raise a false conflict: on_save always passes the modified time read when the sheet opened, so the second Apply finds the site's time changed by your own first Apply and asks "changed on the site after you opened it ... replacing theirs?". (Plausible; depends on the modified time changing between saves.)
- The Properties sheet and Site Properties: Apply updates the sheet as if the save succeeded before the site answers; there is no status line on this sheet to show a failure.
- The Properties sheet and Site Properties: Changing Status to publish on the sheet publishes immediately on OK, with no "Visitors will see them" confirmation, while Item > Publish or Update asks first. The same outcome should not have two confirmation levels.
- The Properties sheet and Site Properties: Status values are raw slugs (publish, future, pending), and Comments and Pingbacks are "open" and "closed". WordPress's own screen says Published, Scheduled, Pending Review, Allow comments. A choice box can show words and send slugs.
- The Properties sheet and Site Properties: The batch confirmation prints list values as Python tuples: "Add categories to ('News', 'Events')" (the f-string formats the tuple from value_of). Format lists as words.
- The Properties sheet and Site Properties: The conflict box offers "Use Mine" and "Cancel"; the module docstring promises "Use Mine or Keep Theirs". "Keep Theirs" (and re-reading their version) is the more useful second choice than a bare Cancel that discards your edits silently.
- The Properties sheet and Site Properties: Escape and Cancel discard edits without asking, even after many changes across pages.
- The Properties sheet and Site Properties: Tab order (Copy as Text, OK, Apply, Cancel) does not match the visual order (OK, Cancel, Apply) because Apply is created before Cancel.
- The Properties sheet and Site Properties: Field labels carry no access keys, so a long General page can only be walked with Tab.
- The Properties sheet and Site Properties: Site Properties is almost all read-only text boxes inside a modal sheet with OK/Cancel semantics; "Close" is right, but a listener must Tab through every read-only box to reach it or press Escape.
- The context menu: The reason a row is greyed is never heard. The menu-bar reason goes into the item's help string, but the frame calls SetStatusBarPane(-1), so menu help is shown nowhere, and screen readers do not read menu help strings. In context menus no reason is set at all. The only place the real sentence appears is when a command is run by key.
- The context menu: The WordPress provider has no reason() hook, so the frame's fallback is used: every greyed row's reason is "Not available here." (workbench_frame_commands.py reason), including in Shift+F1's list (", greyed: Not available here."). The good refusal sentences exist in refusal_for but are not wired to reason().
- The context menu: Context menu rows show no keys and have no access letters, and "More" has none either. The help strings carry the keys ("Delete.", "Ctrl+Shift+P.") but, as above, are never displayed. A listener learns no chords from the context menu.
- The context menu: On a post, Copy Link and Delete Permanently sit inside More, behind Visual Review and Restore from Trash. Restore from Trash is shown on top even for a post that is not in the Trash (it then says "Nothing selected is in the Trash."). The top six should be the ones that apply to the row's state.
- The context menu: "Empty Trash..." (a whole-site, permanent action) is offered on a single post's context menu, under More. A row menu should hold only actions on the row; this one belongs on the node.
- The context menu: On a user, "Cancel Membership..." (DESTRUCTIVE) is on top while "Send Password Reset" is buried in More.
- The context menu: Greying only reflects permission, never applicability: a comment command on a post row is enabled and then says "Choose a comment or a form entry." when run (see the Item menu below).
- The context menu: Merge Into and Convert are DESTRUCTIVE and confirmed, but record nothing in Change History at all, while Delete Permanently records an entry marked cannot be undone. Change History is therefore not "every change made here".
- History and undo: A change that cannot be undone blocks every earlier undo. next_undo() always returns the newest change, and undo() never removes one without an inverse. After one Delete Permanently, Import, REST Console write or Plain-Language Batch, every Ctrl+Z repeats "<summary> This cannot be undone." and the Trash you did five minutes earlier can no longer be undone from here. Ctrl+Z should skip (and say it skipped) entries with no inverse, or Change History should let you undo a chosen entry.
- History and undo: Change History is read only: you cannot pick an entry to undo, and entries have no times (Change.when is never set).
- History and undo: The undo message for summaries like the batch ("move all drafts by Sam to pending on Radio This cannot be undone.") reads as one run-on sentence; the summary needs its own full stop.
- History and undo: Ctrl+Z in the tree is silently ignored; a short "Ctrl+Z works in the list, or use Edit > Undo." would be better than nothing.
- History and undo: A failed undo leaves the change on top, so pressing Ctrl+Z again retries; that is reasonable, but the failure text is the raw error.
- The status bar: The Waiting cell's count is filled only when Needs My Attention > Comments Waiting has been loaded in this window; before that the cell is absent, and it goes stale until that node is loaded again. It reads like a live count and is not.
- The status bar: "1 comments waiting": the plural is fixed.
- The status bar: The Role cell's Enter opens the provider's role-aware report ("You are <Role> on <site>. ... <Action>: yes" or the refusal), which is what Shift+F1 promises but does not open (see Help). Two different What Can I Do Here windows exist.
- The status bar: The Filter cell is always present with "No filter", so F6 into the bar always lands on Site, Your role, Items, Filter, Loading before anything useful changes; fine, but the Items cell already says the count, so most visits read five cells to learn one fact.
- The status bar: A site name containing "&" becomes an access-key mnemonic in the cell's button label (SetLabel with the raw name). Minor, but it can swallow the character.
- F1, Shift+F1 and Help for This View: Shift+F1 opens the wrong window. "what_can_i_do" is a frame verb, so the frame's generic list runs and the provider's do_what_can_i_do (which starts "You are <Role> on <site>. Workbench access on <site> is <Access>." and gives the real refusal for each action) is unreachable from Shift+F1 and from the menu. The menu row's help says "What your role allows." and the Keys node says "Shift+F1: What your role lets you do here."; neither is what opens. The role-aware report is reachable only from the Your role status cell.
- F1, Shift+F1 and Help for This View: In the frame's list, every greyed row says "greyed: Not available here." (no reason hook), and "About this action" shows only the help, never the reason. So the window that exists to say why you cannot do something never says why.
- F1, Shift+F1 and Help for This View: The list is a plain list box; "greyed" rows are not disabled items, just text, and Enter on them only beeps.
- F1, Shift+F1 and Help for This View: F1 has no purpose sentence (no help_purpose hook) and no "open the guide" button: guide routes are registered only for GitHub windows (guide_opener.py), so the WordPress Workbench's F1 cannot open a user guide.
- F1, Shift+F1 and Help for This View: Alt+F1 (What Is This?), Ctrl+F1 (guide chapter), Ctrl+Shift+F1 (Search Help), Alt+Shift+F1 (Keys) and F9 (repeat last result) exist in the shared frame but are not on the WordPress menu, so they are not bound. The Keys node lists only 18 keys and is called "Every key the Workbench answers to" in its help; it omits Ctrl+9, Ctrl+N, F5, the Go row beyond Ctrl+1 and Ctrl+2, and the whole Site and Tools menus.
- F1, Shift+F1 and Help for This View: The Keys node teaches Ctrl+Shift+F for the Filter Builder, which does not work (see The filter box).
- F1, Shift+F1 and Help for This View: The Help menu has one row. Start Here (Ctrl+9) is on the Go menu, and What Can I Do Here? is on the Site menu; a listener looking for help in Help finds neither.
- Workbench Access, View As Role, and Roles: Workbench Access, Safe Mode and View As Role are enforced only for commands that appear in the selected row's action table (refusal_for returns "" for any command not in that table, and for no row). Menu-bar-only commands do not check access: Site > Empty Spam and Empty Comment Trash (permanent deletes), Edit > Import Posts and Import a Folder of Documents, Tools > WXR Files > Import WXR as Drafts, Site > Put Back from a Snapshot, Tools > REST Console (POST, PUT, PATCH and DELETE go straight through after its own preview), and New Here. So "Read Only: look, never change" and View As Role's "Nothing can be changed until you stop" are not true, and Safe Mode ("the Workbench only reads") can still delete every spam comment. This is the most serious finding in the window.
- Workbench Access, View As Role, and Roles: Ctrl+Alt+R does not open Roles: the frame's key hook treats any Ctrl+R without Shift, Alt included, as Reload ("event.ControlDown() and not event.ShiftDown() and code is R"), and it runs before the menu accelerator. Only the menu and the context menu reach it.
- Workbench Access, View As Role, and Roles: When you are not inside a site (for example on Needs My Attention), all three silently act on the first connected site; only the Workbench Access prompt names it.
- Workbench Access, View As Role, and Roles: View As Role always preselects "Myself, as I am", not the role you are currently viewing as.
- Workbench Access, View As Role, and Roles: View As Role is per window and forgotten on close; Workbench Access is per site and persistent. The status bar shows both, but nothing tells you that one survives and the other does not.
- Menu bar: File: New Here's menu help, "A new user or password, where you are.", is out of date: it also makes posts, pages, custom items, categories, tags, terms, menus, redirects, discount codes, shop and event items and forms.
- Menu bar: File: File has no Close Window-style "Open the Editor" or Export; that is fine, but Export List and the imports live in Edit, where a Windows user would look under File.
- Menu bar: Edit: No Cut, Copy, Paste or Select All rows: Ctrl+C and Ctrl+A do nothing in the list (see The list), and the familiar Edit menu shape is missing.
- Menu bar: Edit: Only Mine is a toggle but is not a check item, so the menu does not say whether it is on.
- Menu bar: View: "Load All" says "Read every row the site has." but stops at 10,000 (ALL_PAGES 100 pages of 100).
- Menu bar: View: Back's help mentions Backspace but not Escape, which also goes Back and is the more surprising of the two.
- Menu bar: Go: Every Go key leaves focus on the tree, not the list. After Ctrl+Shift+4 (Comments) you still need F6 twice to reach the comments. A Go key is a "take me to the things" key; landing in the list (or making that an option) would save two presses every time.
- Menu bar: Go: The Go row's digits are not in the order of the tree: Ctrl+1 Needs My Attention, Ctrl+2 Current Site, Ctrl+3 Calendar, Ctrl+5 Watches, Ctrl+6 Practice Site, Ctrl+9 Start Here, Ctrl+0 Across Sites, with 4 and 8 empty. The menu lists them Start Here first but Start Here is Ctrl+9. Hard to learn by ear.
- Menu bar: Go: "Appearance" lands on Themes, and "Needs My Attention" lands on Inbox, not on the folder the label names; the Where Am I words will differ from the menu word.
- Menu bar: Go: Across Sites lands on a folder with an empty list; Ctrl+0 then Right Arrow is always needed.
- Menu bar: Go: Practice Site appears as Go > Practice Site (Ctrl+6) and Tools > Practice Site... (Ctrl+Alt+P), two rows with the same name doing different things (a node versus a start/stop dialog).
- Menu bar: Go: Parent Node at the top silently does nothing.
- Menu bar: Item: The four Gravity entry rows cannot be reached by letter. Free letters remain (H, J, K, Q, X, Z), so they could have them.
- Menu bar: Item: The Item menu has 23 top-level rows plus a 10-row submenu, for every row kind at once. Greying is by permission only, so on a post, Approve, Spam, Reply, Merge Into, Convert, Entry Notes, Star and the rest are all enabled and each says a refusal sentence when chosen ("Choose a comment or a form entry.", "Merge Into works on a category, tag or term."). A listener walks past 15 irrelevant rows to find Publish. Grey by row kind too, or build the Item menu from the selected row's action table (which is what the actions.py docstring says the Item menu is: "the same rows, in the same order").
- Menu bar: Item: Greying is computed only when a menu opens (EVT_MENU_OPEN), never on selection change. On Windows a disabled menu item's accelerator does not fire, so a chord greyed the last time you opened the menu (for example while access was Read Only) likely stays dead, silently, until you open that menu again. (Plausible; verify on Windows.)
- Menu bar: Item: Delete Permanently's help says "after you confirm by name", which suggests typing the name; the dialog only lists names and asks Yes or No. Say "after you confirm" or really ask for the name.
- Menu bar: Item: Delete and Shift+Delete do nothing, silently, in the tree and Details (keep_list_key swallows them); in the filter box they edit text, which is right.
- Menu bar: Site: "Empty Spam" takes M and "Empty Comment Trash" takes E, so the two siblings that start with the same word do not share a letter pattern; acceptable, but E for "Empty" belonging to the second row is a trap for the first.
- Menu bar: Site: Empty Spam and Empty Comment Trash run under Read Only, Safe Mode and View As Role (see Workbench Access).
- Menu bar: Site: What Can I Do Here? belongs in Help.
- Menu bar: Tools: Workbench Options holds only Watches. The name promises the window's options (columns, landing node, Go-key focus, announcements) and delivers one checklist; "Watches..." would be honest, or the options should grow.
- Menu bar: Window: The menu could also list the editor's other open windows; with one row it is a long way to one command that already has a key.
- Menu bar: Help: Start Here, What Can I Do Here?, How WordPress Thinks, Words and Keys are all help and none is here.
- New Here: A new post or page is made on the site and then left there: it is not opened in the editor, the new row is not selected, and the person must find it in the list. "Made the post X on Radio as a draft." followed by opening it in the editor (or at least selecting the row) is the expected flow.
- New Here: A category asks for its parent by number. The site has the category list; a choice would do.
- New Here: A chain of one-field dialogs, each with the same title, is slow and gives no sense of how many steps remain.
- New Here: Not in Change History, so Ctrl+Z cannot undo an accidental Ctrl+N.
- Open on the Site, Preview, Copy Link: With nothing selected, or on Needs My Attention, Open on the Site and Copy Link fall back to the FIRST connected site's address and say only "Copied." A listener cannot tell they copied a home page rather than the row. Say what was copied ("Copied the address of Hello World.") or refuse without a row.
- Open on the Site, Preview, Copy Link: Shift+Enter and Ctrl+Enter are window accelerators, so they also fire from the filter box, where a listener pressing Shift+Enter by habit opens a browser instead of running the filter.
- Open on the Site, Preview, Copy Link: Preview of a draft needs a signed-in browser; nothing says so if the browser is not signed in to wp-admin.
- Export List: The left-out sentence is spoken in full on every export. It is honest but long; the hidden-columns part is news, the rest is the same every time and could be in the help.
- Export List: When the list stopped at its 300-row limit, the export silently writes 300 rows; the generic "not loaded yet" phrase does not say that this export is short. Say "300 of more than 300; Load All first for every row."
- Export List: The file is written on the UI thread; a 10,000-row Excel export will freeze the window briefly.
- Import Posts from a Spreadsheet: Importing from the Media or Comments node makes posts, without saying that it chose posts; the preview's first words should say "posts" or "pages" explicitly and let you switch.
- Import Posts from a Spreadsheet: The Open dialog offers no "All files" choice (the helper choose_spreadsheet in wordpress_workbench_dialogs.py, which says "Spreadsheets saved as CSV", is a different, unused-here dialog).
- Import Posts from a Spreadsheet: The import could easily be undone (move the new drafts to the Trash) but is not.
- Import a Folder of Documents: The chord Ctrl+Alt+Shift+I is a four-key chord for an action used a few times a year; rule 9 would say a letter is enough.
- Import a Folder of Documents: Same Undo and access gaps as the spreadsheet import.
- Workbench Options: Every check box starts with "Watch:", so a listener hears "Watch" eight times; the group could be labelled "Watches" and the boxes left plain.
- Workbench Options: The fifteen-minute interval (watch_minutes) is stored but not offered.
- Workbench Options: The module docstring names quill.core.wordpress.workbench_flag.workbench_window_enabled, a flag the doors no longer read.
- REST Console: The console ignores Workbench Access, Safe Mode and View As Role: a DELETE goes through under Read Only after only its own preview.
- REST Console: do_rest_console calls self.ensure(...) on the UI thread before the dialog opens, which may block on two network reads for a site not yet read.
- REST Console: "answered." is said even when the site answered with a WordPress error object in a 200 body; the listener has to open the tree to learn it failed.
- REST Console: The docstring calls the copy button "Copy Answer"; it is "Copy JSON". The help on Save Request warns "Do not type a password into the parameters of one you keep." which is the right warning but the saved file is not encrypted; a stronger guard (refuse to save a parameter named password) would be safer.
- Run a Saved Request, the Saved Requests submenu, Forget a Saved Request: Ctrl+Alt+Shift+F does not reach Forget: the frame's Ctrl+Shift+F hook catches it and moves to the filter box.
- Run a Saved Request, the Saved Requests submenu, Forget a Saved Request: run_saved also calls ensure on the UI thread.
- Run a Saved Request, the Saved Requests submenu, Forget a Saved Request: A saved request for a site that is gone silently runs against a different site (the current one). For a saved write, that is a risk; say which site it will use, or refuse.
- Run a Saved Request, the Saved Requests submenu, Forget a Saved Request: Only nine show in the submenu with no "More..." row; the tenth is reachable only through Run a Saved Request.
- Plain-Language Batch: The help says "press Change" but the button is OK (ask_checks uses the default OK label). Name the button Change, as the other previews do.
- Plain-Language Batch: The checklist is the only preview: it lists items but not the change itself per item (for example "Draft becomes Pending"); the phrase is only in the F1 help. Put the change sentence above the list.
- Plain-Language Batch: A batch over many items cannot be undone, although every item's before-state was read.
- Read Site as Document: The row has no ellipsis although it opens a dialog first.
- Read Site as Document: Nothing is said while a large site is read; a long silence follows the choice.
- Your Profile: A four-key chord for an occasional command; most people change their profile a few times ever.

#### Posts and pages

- The tree nodes and what the list shows: the six status children under Pages use the Posts columns and are not tree-ordered, so Pages > Drafts loses the Level column the Pages node has. Moving from Pages to Pages > Drafts silently changes the column set.
- The tree nodes and what the list shows: the extra column titled "Comments" shows the item's comment_status ("open" or "closed"), not a count. A listener will expect a number. Calling it "Comments allowed" would fix that.
- The tree nodes and what the list shows: dates in the list and details pane are made from modified_gmt and date_gmt by friendly_date, which the code documents as "UTC as given". Nothing in the cell says UTC, so a site in another time zone hears times that look local and are not.
- The item row's context menu, as it is actually laid out: "More" is appended with no access key, and the context menu labels carry no chord text. The chords live only in each row's help string, which goes to the status bar and is not normally spoken. So the context menu never teaches a listener that Delete Permanently is Shift+Delete or Approve and Schedule is Ctrl+Shift+D.
- The item row's context menu, as it is actually laid out: actions.py promises that "the same rows, in the same order, are the Item menu, so More never hides anything that only a right-click could reach". The WordPress Item menu breaks that promise. Open in Editor, Visual Review, Earlier Versions, Duplicate as Draft, Counts by Status, Empty Trash and Open in wp-admin are only on the context menu, and the Item menu's order differs from the context menu's.
- The item row's context menu, as it is actually laid out: Delete Permanently, a tier 3 command, sits first under More, directly above the harmless Copy Link. One arrow press separates a copy from a permanent delete. The confirmation stops it, but its placement is still careless.
- The item row's context menu, as it is actually laid out: a greyed row gives no reason when you arrow onto it. The reason is reachable through Shift+F1, but nothing in the menu points there.
- Open in Editor: an Author pressing Enter on someone else's page hears a refusal and nothing else. Offering to open it read only, or pointing at Preview on the Site (Ctrl+Enter), would turn the dead end into a choice.
- Preview on the Site: a draft's preview link only works for someone signed in to WordPress in that browser. Open in wp-admin says "You must be signed in to wp-admin in your browser" and Visual Review explains the same limit, but Preview says nothing, so the first time someone previews a draft they meet a login page with no warning.
- Preview on the Site: Open on the Site (Shift+Enter, File > Open on the Site, Alt+F, S) is the published address. It is not on the item context menu at all, though it is on the Site row's.
- Visual Review...: the row is enabled on drafts, pending and scheduled items, where it can only refuse. It is one of the six top rows, so most of the time it is the wrong thing to offer there. It should be greyed, or say before it starts, when the row's status is not "publish".
- Publish or Update...: the label promises "or Update", but published items are filtered out before anything happens, so on a published post the only result is "Nothing selected is waiting to be published." Either drop "or Update" or make it update.
- Publish or Update...: there are two ways to publish now. This one uses a message box whose default is Cancel and records an undo. Approve and Schedule with an empty time uses a preview list whose default is Publish and records no undo (see below). The same act has two dialogs, two default buttons and two answers to Ctrl+Z.
- Publish or Update...: the help says "after a preview", but this is a message box, not the Workbench's preview window.
- Publish or Update...: when every item fails, an undo is still recorded, and Ctrl+Z says "Put 0 items back as they were."
- Approve and Schedule...: it does not look at status. It will "approve" a post that is already published and reschedule it into the future, which takes it off the site until then. Move to Another Day warns about exactly that ("Published items moved to a future time are scheduled again, and are off the site until then.") and this command does not.
- Approve and Schedule...: the items are sent one at a time in a single loop with no per-item outcome. If the third of five fails, the error is said, the first two are already changed, the rest are not, and nothing says which. Publish, Trash and moderation all report each item.
- Approve and Schedule...: a typing mistake in the time throws away what was typed. The error is spoken after the dialog has closed, and the person must press Ctrl+Shift+D and type it all again.
- Approve and Schedule...: "{n} published." and "Publish {n} on {site} now." say a bare number with no noun ("1 published."), unlike Publish's "Published 1 item on {site}."
- Send Back with a Note...: critical. It does not check status. On a published post it sets the post to draft, so the post disappears from the site, with no preview, no warning and no undo. The module's own docstring says "every change is previewed", and this one is not.
- Send Back with a Note...: an empty note cancels silently. A listener who pressed OK by accident on an empty box hears nothing and cannot tell whether anything was sent.
- Send Back with a Note...: "Sent back 1 as drafts" reads oddly for one item.
- Assign a Reviewer...: the fallback list is who=authors, which includes Contributors and Authors who cannot publish others' posts. The list's own help still says "who may edit and publish others' posts", so the fallback can offer people the help says are not there.
- Assign a Reviewer...: a typed name is not checked against anyone on the site; a misspelt reviewer is accepted and recorded.
- Assign a Reviewer...: the closing sentence is about forty words and is said every time. A short "Asked {reviewer} to review {n}. No email is sent." would carry the same fact; the Review Watch explanation belongs in F1.
- Move to Another Day...: the old date of every item is known before the move, so this is one of the easiest changes to undo, and it is not undoable.
- Move to Another Day...: with several items selected, the box shows only the first one's date and every item gets the same new moment. The preview does not show each item's old date, so a listener cannot hear what is being lost.
- Copy Link: when a row has no link, the provider falls back to the site's own address, and the outcome is still just "Copied." A listener pasting expects the post and gets the home page.
- Copy to Site...: "Replace" overwrites an existing item on the target site, and nothing can put it back. The preview line "Replace post About." is the only warning, and it is phrased like the harmless "Make" lines. A replace deserves its own sentence in the summary saying it cannot be undone.
- Show Its Comments: the count is spoken after focus has already moved to the list, so it competes with the screen reader reading the first focused row. One or the other gets cut off. Saying the count first, or putting it in the status bar, avoids the collision.
- Earlier Versions... (in progress): the date in the summary and the announcement is made by stripping "Saved " and cutting at the first comma. friendly_date writes "3 November 2026, 4:12 PM", so the time is cut off. Two versions saved the same day sound identical in the summary and in the closing sentence.
- Earlier Versions... (in progress): in the list, OK means "compare", not "restore". That is a reasonable two-step design, but it is the reverse of Their Application Passwords, where OK in a list means "revoke". The same list dialog means different things in different places.
- Earlier Versions... (in progress): only the title and content are restored. WordPress's own restore also brings back the excerpt; the preview does not say the excerpt is left alone.
- Duplicate as Draft: after the copy is made the list refreshes, and nothing in the handler moves the selection to the copy. Unless the refresh happens to land there, the next Enter opens the original rather than the copy someone presumably wanted to edit. Offering "Open the copy in the editor?" would close the loop.
- Counts by Status: a refused view is silently dropped, so "Private" may simply be missing from the sentence with no hint why. "Private: not shown to you" would be honest.
- Empty Trash...: critical. The preview window makes its action button the default, so Enter in this dialog permanently deletes the whole Trash. Delete Permanently on one item uses a message box whose default is Cancel. The most destructive command in this section is the easiest one to confirm by accident. Every tier 3 preview should default to Cancel.
- Empty Trash...: offered on any item row, even a published post in Posts > Published, where it empties the Trash of that whole kind rather than doing anything to the selected row. Its place on the row menu suggests it acts on the row.
- Open in wp-admin: a hand-off to wp-admin. The sentence is honest but long, and it is said every time. The REST explanation could live in F1, leaving "Opening wp-admin's editor. Sign in there if asked."
- Move to Trash: "Ctrl+Z puts them back." is said for a single item too.
- Restore from Trash: two restores behave differently. Ctrl+Z after Trash puts a published post back as published. Restore from Trash on the same post brings it back as a draft, which is WordPress's own rule. A listener who trashed a post yesterday and restores it today finds it is no longer on the site, and the closing sentence's "as drafts or waiting" is easy to miss.
- Restore from Trash: it is one of the six top rows on every item, including published posts where it can only say "Nothing selected is in the Trash." It is most useful in the Trash node, where it is the only row that matters.
- Delete Permanently...: "after you confirm by name" suggests typing the name, which some products require for a permanent delete. It is a Yes/No box that lists the names. The help should say "after a confirmation that names it".
- Delete Permanently...: it works on items that are not in the Trash, skipping WordPress's safety net. wp-admin offers Delete Permanently only from the Trash view.
- New Here (Ctrl+N), on Posts, Pages and content types: the File menu's help, "A new user or password, where you are.", is stale. New Here now makes posts, pages, terms, menus and more.
- New Here (Ctrl+N), on Posts, Pages and content types: in Posts > Pending or Posts > Scheduled the new item is still a draft, so it does not appear in the list you are standing in. Nothing says where it went, and focus does not move to it. Offering to open the new draft in the editor would finish the job.
- New Here (Ctrl+N), on Posts, Pages and content types: Read Only access, Safe Mode and View As Role ("Nothing can be changed until you stop") do not stop Ctrl+N here.
- Properties (Alt+Enter), one item: the Status, Comments, Pingbacks and Format choices are WordPress's raw slugs ("publish", "future", "open"). The list column says "Published" and "Scheduled" for the same values. A listener meets two vocabularies for one field.
- Properties (Alt+Enter), one item: Published is typed as "2026-11-09T14:00", while Approve and Schedule and Move to Another Day take "2026-11-20 9:00 AM". Three ways to set a date, two formats.
- Properties on several items at once: critical. Add categories, Remove categories, Add tags and Remove tags only understand "News (12)" or "12". A plain name such as "News" is silently dropped (the code calls term_ids with no name table and ignores what it cannot match). The confirmation still says "Add categories to News", the save reports success, and nothing was filed. The one-item sheet refuses an unknown name out loud; the batch sheet should resolve or refuse names the same way.
- Properties on several items at once: on one item Author is a choice of names; on several it is "Author number", a text box wanting a number. The same field asks two different things.
- Ctrl+Z and Change History, as they behave across these sections: critical. When the newest entry has no undo, Ctrl+Z says "{summary} This cannot be undone." and leaves that entry on top. It never moves past it, so every older change that could be undone becomes unreachable for the rest of the session. One Delete Permanently, Send Back or Move to Another Day locks out the undo of everything before it. Skipping past an entry that cannot be undone, and saying so, would keep the rest reachable.
- Ctrl+Z and Change History, as they behave across these sections: critical, the opposite problem. Reply, Merge Into, Convert, Allow This Sender, New Here and the two Empty commands are not recorded. Pressing Ctrl+Z straight after a Reply does not touch the reply; it undoes whatever came before it (an Approve, a role change) and says so in words that do not mention the reply. A listener expects Ctrl+Z to undo the last thing they did.
- Ctrl+Z and Change History, as they behave across these sections: when an undo itself fails (a conflict), the error is said and the entry stays on top, so the next Ctrl+Z tries the same failing undo again.
- Ctrl+Z and Change History, as they behave across these sections: the summary is reused as the start of the refusal, so the listener hears, for example, "Published on {site}. This cannot be undone.", a sentence about what was done followed by one about what cannot be. "Cannot undo: published on {site}." would put the answer first.

#### Media

- The media row's context menu: Insert into the Document is the second row on every media row, and it works only in picking mode. Outside picking mode it is enabled and can only explain itself. It should be hidden, or greyed, unless the Workbench was opened by Insert > Picture from the Media Library.
- The media row's context menu: Edit Picture, Regenerate Sizes and Download are offered on audio, video and documents too. Edit Picture and Regenerate Sizes refuse with "Edit Picture works on a picture in the Media Library." and "Regenerate Sizes works on a picture in the Media Library." Greying them on non-pictures would spare a round trip.
- The media row's context menu: the Item menu has none of the media commands except Copy to Site and Delete Permanently, and its Delete row still reads "Move to Trash" on a media row.
- View or Play: Enter, the most-pressed key, leaves QUILL. Arrowing through the library and pressing Enter to hear what a file is takes the listener into a browser tab every time. Read in Full (the details pane), or an in-app play for audio, would be a gentler default, with View or Play second.
- Insert into the Document: picking mode changes what Enter does, and nothing on the window says so after the first announcement. A listener who arrows away to the tree and back has no cue that Enter now inserts instead of opening a browser. Saying "Picking" in the status bar or the window title would keep the mode audible.
- Replace File... (just built): critical. If you chose "Delete the old file permanently", Ctrl+Z still puts every item back, pointing them at the old file, which no longer exists. The undo turns a working site into one full of broken images and links. Either refuse the undo after a delete, or refuse the delete when an undo is wanted, and say so in the old-file choice.
- Replace File... (just built): the two decisions with the largest consequences, deleting the old file and adding a redirect, are asked after the preview, so the preview the listener approved did not include them. Asking them first, and showing them as lines in the preview, would make the preview true.
- Replace File... (just built): when Enable Media Replace is not active, the "How:" list has a single row. It is a dialog with one choice, and Enter just accepts it. Saying the fact in the preview's summary would remove a step.
- Replace File... (just built): the help text says "every page, post and featured image" and the dialog says "every post, page, pattern and featured image". Small, but a listener checking whether patterns are covered hears two answers.
- Replace File... (just built): the closing sentence after a repoint can run past sixty words. Splitting it into the outcome now and the rest in a report window would be easier to follow.
- Edit Picture...: the preview's line "Sent to wp/v2/media/{id}/edit" is a REST route, not words. It is jargon in a dialog that otherwise speaks plainly.
- Edit Picture...: the edit is undoable in practice (delete the copy), and the closing sentence even says how, but Ctrl+Z will not do it and instead blocks everything older.
- Edit Picture...: a crop typing mistake closes the dialog and loses the four numbers.
- Attach to a Post or Page...: a number skips the search and is not checked. "Attach {title} to number 99 on {site}?" is asked even if post 99 does not exist, and the name in the confirmation is "number 99", not a title.
- Detach: the confirmation names the post by number only ("from post 412"). The listener cannot tell what they are detaching it from.
- Download...: the closing sentence reads out the whole path, which can be long. "Saved {file name}." is enough, since the person just chose the folder.
- Download...: the 2026-11-13 audit table says a file over 512 MB "opens in the browser". The code does not do that. download_file raises a too-big error and that error is what is said.
- Delete Permanently... (media), and the Delete key: the confirmation does not say where the file is used. By Name > Media Usage and Housekeeping already know, and the Housekeeping node "shows usage before Move to Trash". The plain Delete Permanently on a Media row can remove a picture that twenty pages show, with no warning.
- Delete Permanently... (media), and the Delete key: the role sentence says "Changing media" for a permanent delete, which undersells it.
- Properties (Alt+Enter), one file: the row's own F1 says "Alt+Enter edits its alt text", but alt text is on the second tab. Alt+Enter lands on Title, and the listener must press Ctrl+Tab to reach Alt text. For a library whose main accessibility job is alt text, Alt Text and Caption should be the first page, or Alt text the first field.
- Properties (Alt+Enter), one file: "Uploaded by" reads author_name, which the media route does not send and values_for does not fill. It is very likely always empty.
- Properties (Alt+Enter), one file: "Attached to number" is a bare number field. Attach to a Post or Page finds posts by words; the sheet does not.
- Properties on several files: setting one Alt text on many different pictures is rarely right, and nothing warns that every selected picture will get the same description.
- New Here on Media: wp-admin's Media screen has Add New. Uploading from the Workbench is not offered here; the sentence lists everything except what the listener is looking at.

#### Categories and tags

- The tree nodes and what the list shows: Categories and Tags have no Go key, while Posts to Site Health each have one. A listener reaches them by the tree.
- Show Its Posts: it always lands in Posts. For a plugin taxonomy that belongs to a custom content type (an Events category, say), the Posts list is filtered to nothing, or refuses the filter. It should open the content type the taxonomy is on.
- Show Its Posts: when the filter goes to the site, the first thing said is "Filtering.", and the count of what was found is not announced when it arrives.
- Merge Into...: the preview's lines are a route word and a number ("posts 123", "posts 98"), not titles. A listener hears a column of numbers and cannot check what moves.
- Merge Into...: the "Into:" list holds only the rows already loaded, by name only. Two categories called "News" under different parents sound identical, and a term past the first 300 is not offered.
- Merge Into...: the tier 3 preview defaults to Merge, so Enter merges and deletes.
- Convert to Category or Tag...: Convert does the same kind of change as Merge (move every post, delete the term) but previews less. It gives no count, no list and no "cannot be undone" warning; Merge gives all three. They should share one preview.
- Convert to Category or Tag...: on a partial failure the new term has already been made and some posts already moved, yet the sentence says only that the old term "was kept". The site is left with both terms and the posts split between them, and the listener is not told.
- Convert to Category or Tag...: converting a category with child categories or a parent says nothing about the hierarchy, which a tag cannot hold.
- Delete Permanently... (terms), and the Delete key: the confirmation does not say how many posts lose the term, though the Count column already knows. "News is on 34 posts" belongs in that sentence.
- New Here (Ctrl+N), on Categories, Tags and plugin taxonomies: three separate modal dialogs, one after another, each with its own title read out, where one small form would do. Escape on the second throws away the first.
- New Here (Ctrl+N), on Categories, Tags and plugin taxonomies: the parent is asked by number only. Anything that is not a number is silently ignored and the category is made at the top level.
- Properties (Alt+Enter), a term: Parent number is shown on tags too, with help that says "Categories only." A field that cannot apply should not be there.

#### Comments

- Approve, or Not Spam: "Not spam: 1 item on {site}, and the site was told." does not say the comment is now waiting, not published. A listener who pressed Approve on a spam comment reasonably believes it is now visible. It needs a second Ctrl+Shift+A, and nothing says so. Either approve it, or say "back in Waiting; Ctrl+Shift+A again approves it".
- Approve, or Not Spam: the noun is "item", not "comment", in every moderation sentence ("1 item approved"). It is shared with form entries, but in the Comments list it is the wrong word.
- Approve, or Not Spam: a mixed selection of spam and held comments gets the plain "approved" sentence, although the spam ones went back to Waiting instead.
- Not Spam, and Allow This Sender: the name promises an allow list that does not exist. The command is "Approve" plus an explanation of WordPress's own rule, and on a site that holds every comment the closing sentence admits the sender is not allowed at all. "Approve and Explain" would be honest; or it should be greyed on such sites.
- Not Spam, and Allow This Sender: reading the discussion settings needs manage_options. For an Editor the read fails, the empty settings fall back to the first sentence, and an Editor is told the sender's next comments get through whether or not that is true on this site.
- Not Spam, and Allow This Sender: unlike Approve, it is not recorded, so the two moderation commands next to each other have different undo stories.
- Unapprove: the sentence says "unapproved" while the list and status cell say "Waiting". "Back to Waiting" would match what the listener then hears in the list.
- Reply...: a reply is public the moment OK is pressed, and nothing can take it back from here. A multi-line box where Enter does not submit is safe, but there is no preview and no undo for a public post. At least record it, with Ctrl+Z moving the reply to the Trash.
- Reply...: needing moderate_comments means an Author cannot reply to comments on their own posts from the Workbench, although WordPress lets them.
- Reply...: Approve and Reply (wp-admin's one action) is two commands here: Ctrl+Shift+A, then Ctrl+Shift+M. The audit table says so, but nothing in the Reply dialog notes that replying to a waiting comment leaves it waiting.
- Move to Trash, Restore from Trash, Delete Permanently (comments): the Restore row's help says "Out of the Trash, as a draft.", which is wrong for a comment; comments come back Waiting.
- Move to Trash, Restore from Trash, Delete Permanently (comments): Move to Trash, the action Delete performs and the F1 for the node names, is under More on the comment menu, while Read in Full takes the top.
- Empty Spam...: critical. Empty Spam is not a row action, so the Workbench's access check never sees it. Read Only access, Safe Mode, and View As Role, whose own sentence says "Nothing can be changed until you stop", all let Ctrl+Alt+E permanently delete every spam comment after one Yes.
- Empty Spam...: "Delete all 1 comments held as spam" for a single comment; Empty Comment Trash gets the singular right.
- Empty Spam...: an Editor without the right role hears the confirmation, says yes, and then hears "Deleted 0 spam comments on {site}. 37 could not be deleted." with no reason. A refusal before the question would be kinder.
- Empty Comment Trash...: the same critical access gap as Empty Spam.
- Empty Comment Trash...: the two Empty commands sit on the Site menu with access letters M and E, next to each other, and both are destructive. Empty Trash for posts is on the row menu instead. Three "empty" commands live in two places.
- Comment Counts: "1 are yours" for one comment.
- Comment Counts: the sentence is long and fixed in order. "4 waiting" is what a moderator wants first, and it is first, which is good; "which is waiting and approved together" is an explanation that belongs in F1 after the first hearing.
- Properties (Alt+Enter), a comment: the Status choice offers "hold", WordPress's internal word, where the list says "Waiting".
- Properties (Alt+Enter), a comment: the sheet's title is built from the row's title, which for a comment is "Comment by {author} on {post}", so the reader hears "Comment by Ann on Hello World Properties - Community Radio". It is long and runs two names together.

#### People

- The tree nodes and what the list shows: F1 on Users says "Site > Roles explains each role", but the Site menu's row is "Roles and What They May Do" (Ctrl+Alt+R).
- The user row's context menu: the three Paid Memberships Pro rows are offered and enabled on every site, including sites without the plugin, and they hold three of the six top places. Remove, Set New Password and Send Password Reset, which every WordPress site has, are pushed under More. Membership rows should appear only where Paid Memberships Pro answers, or go last.
- The user row's context menu: "Invite from a Spreadsheet" adds new people to the site; it is not about the selected person, yet it sits on the person's row.
- Show Their Posts: only Posts. Their pages and content-type items are not shown, and nothing says so.
- Change Role...: one person gets a preview window that lists what they gain and lose, and Enter confirms. Several people get a message box with no gains or losses, and Enter cancels. The bigger change gets the smaller preview and the opposite default.
- Change Role...: a person with a role the site defines itself (a shop manager, say) opens the list on Subscriber, because only the five default roles are offered. One Enter and one more Enter in the preview demotes them. Custom roles should be listed, or the list should start on nothing.
- Change Role...: the role can also be changed on the Properties sheet's Role page. The same guards apply there, but no gains-and-losses preview does.
- Their Application Passwords...: in a list whose purpose is reading, OK means "revoke". Cancel is the only way to just read. A listener who presses Enter to choose a password to hear about gets a revoke question.
- Their Application Passwords...: the row is tier 0 (reading), but it leads to a permanent revoke. Read Only Workbench access, Safe Mode and View As Role therefore do not stop the revoke.
- Sign Out Everywhere...: a hand-off to wp-admin with a trailing ellipsis in the label, though no dialog follows.
- Send Password Reset: the label says it sends a reset; it opens a web page. It has a chord, unlike the other hand-offs, so a listener pressing Ctrl+Shift+W in a hurry leaves QUILL.
- Send Password Reset: two other texts promise more than it does. The Add a Person note says "Send Password Reset on their row opens wp-admin" (correct), but the Invite note says "Send Password Reset on their row sends them the link to choose their own" (not true).
- Send Password Reset: the refusal sentence "Doing this (edit users)" is the fallback for a capability missing from the plain-words table. edit_users needs an entry, such as "Changing other people's accounts".
- Set New Password...: a password the check rejects closes the box first. A listener who typed their own password hears the problem and must start again from the menu, with the generated one back in the box. The check should keep the box open.
- Set New Password...: the help says "previewed", but it is a confirmation message box. The password is never shown again in it.
- Set New Password...: being recorded with no undo, it blocks Ctrl+Z for everything done before it in the session.
- Remove...: critical. Delete and Shift+Delete on a user row run Move to Trash and Delete Permanently, which hand over to Remove. The Workbench checks a command against the row's own menu rows, and the user row has no Trash or Delete Permanently row, so neither the tier 3 access check nor the delete_users check runs. With Read Only access, Safe Mode or View As Role, Delete on a person still opens Remove, and Yes still removes them.
- Remove...: the "Give their posts to" list includes Subscribers, who cannot edit what they are given. wp-admin offers everyone too, but a hint ("Subscriber") beside each name would help.
- Remove...: the one-person confirmation does not name the site, unlike the several-people one.
- Properties (Alt+Enter), a person: Language wants a code such as en_US typed by hand. wp-admin offers a list of installed languages.
- New Here (Ctrl+N) in Users: Add a Person: the most important fact, that no email goes and the person cannot sign in until someone sends a reset, is in the help of the second tab and in the confirmation. It is not visible on the first tab, where the listener fills everything in.
- New Here (Ctrl+N) in Users: Add a Person: an account just added is easy to remove, but Ctrl+Z will not, and its entry blocks every earlier undo.
- Application Passwords: New Here (Ctrl+N): Copy All copies the name and the instruction too, not just the secret. A listener pasting it into another app's password field pastes three lines. A "Copy Password" button that copies only the secret would fix it.
- Application Passwords: Revoke...: critical. Shift+Delete on an application password row runs the generic Delete Permanently, which has no case for application passwords. It asks "Delete 1 item from {site} permanently? This cannot be undone: {name}." and then deletes the password's route. It skips the guard above, so Shift+Delete on the row marked "QUILL on this computer signs in with it" revokes the password the Workbench is using and locks it out mid-session.
- Application Passwords: Revoke...: Delete reaches Revoke without the tier 3 access check, for the same reason as Remove on a person: the row has no Trash row for the check to find.

#### Menus

- The Menus and Navigation node: The items column is always empty: load_menus fills `"items": ""` for every row. A listener hears a column header with nothing under it on every row.
- The Menus and Navigation node: The locations column shows WordPress's location slugs exactly as `wp/v2/menus` sends them (for example `primary`), not the theme's names for them ("Primary Menu"). Not translated anywhere I could find.
- The Menus and Navigation node: The list reads `wp/v2/menus`, which is classic menus only. A block theme's Navigation menus (`wp_navigation` posts) do not appear in this node at all. The only trace of them is the Default Navigation Menu command, which names one by number.
- The Menus and Navigation node: There is no way to see a menu's items in the Workbench itself: no child node per menu, no items in the detail, nothing in Properties. The only way is Arrange Items, which leaves the Workbench for another window.
- The Menus and Navigation node: Rename an item, move it up, down, in or out, and remove it: not in the Workbench's own rows. The editor's Menus window (wordpress_menu_commands.py) has Rename, Move Up, Move Down, Move In, Move Out, Remove, Check Menu and Locations; `cmd_menus` returns early through `workbench_door("wordpress.menus")` (and `open_from_door` always returns True), so from the editor's Tools menu that window is gone, and it is now reached only through Arrange Items or the editor's add-this-page-to-a-menu path.
- The Menus and Navigation node: No Go key for Menus, although it is one of the places people visit most in wp-admin after Posts and Pages.
- Read in Full (menu row, default): The default action of a menu reads one short sentence that the list row already said. For a menu, Enter is the one key people press expecting to go inside; here it goes to a pane that cannot show the items.
- Add Menu Item...: Up to six dialogs in a row for one item (kind, search, pick, under, position, preview). Each is correct, but there is no single "Add Menu Item" dialog where the kind, the item and the place can be reviewed together and changed before the preview. A wrong choice at step five means Cancel and start again.
- Add Menu Item...: View All reads at most 100 items (`LIMIT = 100`, one page) and never says it stopped. On a site with 300 pages, page 101 onward is silently missing from View All; only Search finds it.
- Add Menu Item...: Search results that share a title (two pages both called "Contact") are indistinguishable in the list: rows are titles only, with no parent, date or address.
- Add Menu Item...: Custom Links sits in the middle of the kinds list (after the post types, before Categories). wp-admin's panel order is the reason, but in a list box a listener has to arrow past every custom post type to find it.
- Add Menu Item...: The "Where" step is skipped entirely for an empty menu and the position step for an empty level, which is good, but the preview then says `Where: at the top level, first, 1 of 1.` with no hint that the Under question was skipped.
- Add Menu Item...: Ctrl+N with a menu selected bypasses the context menu's permission check: `run` checks `new_here` (which needs nothing), then calls `do_add_menu_item` directly. An Editor walks all six dialogs and only fails when the site refuses the write. Not tested on a live site; read from wordpress_workbench_lists.py and wordpress_workbench_window.py.
- Add New Pages Automatically...: The summary is built from the check box label lowercased, so it reads "Turn On automatically add new top-level pages to this menu for Main on Radio?", which is ungrammatical spoken English. Something like "Turn on adding new top-level pages to Main?" would read better.
- Add New Pages Automatically...: The command is a toggle with no indication of the current state in its label. You learn the state only from the preview's Now line. That is acceptable because the preview always comes first, but the context-menu label could say "Turn On..." or "Turn Off...".
- Add New Pages Automatically...: Two routes to one setting: this command (previewed, re-read before and after) and the Properties check box (a sheet save: conflict check, no preview, undone by Ctrl+Z as `Put {menu number} back as it was.`). Same result, two different confirmation styles.
- Arrange Items...: It restores the missing jobs, but as a different window with different rules: no previews, no Ctrl+Z, its own Add buttons that duplicate Add Menu Item with fewer choices (end only). A person learns two ways to add to a menu that behave differently.
- Arrange Items...: The label says "Arrange" but the window also renames, removes, adds and sets locations; "Edit Items..." or "Open in the Menus Window..." would set the right expectation.
- Arrange Items...: When the window closes, the Workbench list is not known to refresh (not verified).
- Earlier Versions... (menu): It only brings back removed items, and puts them at the end of the menu at the top level, not where they were. A restored submenu comes back flattened. The preview does say "at its end", but not "at the top level".
- Earlier Versions... (menu): It cannot undo a rename or a move, only a removal, although the label "Earlier Versions" suggests a full restore.
- Earlier Versions... (menu): History starts only the first time QUILL reads the menu, and only on this computer. The first use always says there are no versions, which teaches the user the command does nothing.
- Earlier Versions... (menu): If the version lost nothing the brought-back count can never be zero here, but between the preview and the write another person could restore items, and the announcement would then say "Brought back 0 items" (the work re-checks what is missing). Minor.
- Default Navigation Menu...: It sits on a classic menu's row but answers a question about block Navigation menus, which this node does not list. A person on a classic theme gets a question that does not apply to them.
- Default Navigation Menu...: The answer speaks the menu's number (`Navigation menu 1234`), which means nothing to a listener and cannot be used anywhere in the Workbench.
- Default Navigation Menu...: The tier is Read, but it can create a menu on the site. The confirmation is honest about that; the history is not (no entry, no undo).
- Copy to Site... (menu): "Copied 3 from Radio to Studio." is missing its noun.
- Copy to Site... (menu): For a menu, the copy replaces the target menu's links (workbench_site_copy.py says "its links there are replaced"). That is a destructive change on the target with no undo; check that the preview says it plainly.
- Properties (menu): The sheet title, the saved sentence and the undo sentence all name the menu by its number, not its name: WbRow.title looks for a title, name, what, plugin, theme, setting, form or site cell, and a menu row's name is in a `menu` cell, so the title falls back to the row key (the menu id). The menu commands work around it with their own `_named()`, the sheet does not.
- Properties (menu): This is the only place to rename a menu, and Shown in is read only: choosing which theme location shows a menu is only in the Menus window's Locations... (through Arrange Items).
- Properties (menu): Shown in lists location slugs, as in the list.
- New Here on Menus (Ctrl+N): A new menu is made with no preview and no undo, unlike every other write in this node. Worse, because it is not in Change History, Ctrl+Z right after it silently undoes the previous, unrelated change.
- New Here on Menus (Ctrl+N): File > New Here's own help still says "A new user or password, where you are.", which is out of date in every node.
- New Here on Menus (Ctrl+N): Delete a menu: not found in the Workbench.

#### Widgets

- The Widgets and Sidebars node: The id-for-name problem above is the first thing to fix: every widget sentence names an area the way only a theme developer would.
- The Widgets and Sidebars node: The detail says `{n} widgets.` and nothing about what they are. To hear the widgets you must run Preview Widgets, which opens a report.
- The Widgets and Sidebars node: "1 widgets" is said for an area with one widget (no singular form in load_sidebars).
- The Widgets and Sidebars node: On a block theme this node is normally empty or shows only WordPress's inactive area; nothing says "your theme uses the Site Editor instead; see Templates and Template Parts".
- Add a Widget...: The help says Block "holds any block, as text", but Add makes only a paragraph block from plain words (`paragraph_block(text)`). You cannot add a heading, a list or a Latest Posts block from here; only Change edits a block widget's markup.
- Add a Widget...: The widget is always added at the end of the area. There is no position choice, unlike Add Menu Item.
- Add a Widget...: "Visitors see:" is WordPress's rendering turned into words, which is the right idea; for a widget that renders nothing until configured, "(nothing yet)" is clear.
- Change a Widget...: A legacy widget whose form has no fields returns no answers, and the command then stops without a word (`if not data: return`). The person hears nothing and does not know why.
- Change a Widget...: Unchanged block markup also stops silently, while Edit Block Markup for templates says `{title} is unchanged, so nothing was sent.` Inconsistent.
- Move a Widget...: The only widget write with no preview. Moving a widget changes every page that shows either area, the same reach Add's preview warns about.
- Move a Widget...: The undo puts it back at the end of the original area, not in its old position.
- Move a Widget...: Moving within an area (reordering) is not offered.
- Remove a Widget...: Good: honest about where it goes and how to undo it.
- Remove a Widget...: The confirmation is a message box, while Add and Change use the preview window; a listener meets two confirmation styles for one family of commands.
- Preview Widgets: The keyless reason calls it "Read Widgets"; the menu calls it "Preview Widgets". The written reason names a command that does not exist.
- Preview Widgets: This is the only way to hear the widgets at all; it would serve better as the area's default (Enter) than Read in Full.
- Properties (widget area): Labels are WordPress's developer descriptions (for example the route's description of before_widget HTML), not words a site owner uses. Not verified on a live site which fields end up editable.
- wp-admin for This Place (Widgets and Sidebars): It tells you the Workbench does all of it, then opens wp-admin anyway. When the map says `workbench`, the sentence could ask first or explain what wp-admin adds (drag-and-drop, the Customizer's live preview).

#### Appearance and the Site Editor

- The Appearance folder and its Go key: F1 for Appearance does not mention Global Styles, Template Parts or Additional CSS, which are three of its eight children.
- The Appearance folder and its Go key: Go > Appearance landing on Themes means the key never shows you the folder; the help "Themes, templates, patterns." suggests otherwise. For an Editor (who cannot list themes) Ctrl+Shift+7 lands on a node that only says they lack the role.
- The Themes node: The refusal says "Changing the theme" when the person only tried to look. An Editor cannot even read which theme is active from the Workbench, although that is harmless information (At a Glance does name the theme).
- Properties (theme): No "Requires WordPress", "Requires PHP", "Tested up to", screenshot description or tags, all of which `wp/v2/themes` sends; a person choosing between themes has only the description.
- The Global Styles node: F1 promises spacing; the node lists colours and font sizes only. Font families, spacing, element styles (links, headings, buttons) and block styles are not listed.
- The Global Styles node: The contrast column is good and rare. It measures against the page background and text colour only; a colour used as a button background against white text is not judged.
- Change... (global style): F1 says "Change... previews the new value", but this is a plain message box, not the preview window every other Site Editor write uses, and Cancel is its default button. Inconsistent with Edit Additional CSS and Edit Block Markup.
- Change... (global style): The module's own comment says "Enter on a Global Styles row changes that colour or font size"; Enter actually reads (Read in Full is the default).
- Change... (global style): Colours are typed as hex or rgb. Named colours, and choosing from the theme's own palette, are not offered. A listener has no way to hear a colour except as a code plus a nearest-colour name.
- Change... (global style): The confirmation repeats the old and new values and then a contrast sentence that repeats the new value again; long for a message box.
- Properties (global style): Alt+Enter cannot change the value although Properties is where values change in most lists, and nothing on the sheet points to Change....
- The Templates and Template Parts nodes: New Template is only on a row's context menu. On an empty Templates list (a classic theme, or a fresh one) there is no row, so there is no way to make the first template; Ctrl+N (New Here) on Templates says `New Here makes posts, pages, custom items, categories, tags, terms, menus, people and application passwords. Choose one of those nodes first.`
- The Templates and Template Parts nodes: A template part's area (header, footer, general) is not a column, though it is what tells parts apart.
- Edit Block Markup...: Editing a whole template as raw block comments in a plain text box is honest and complete, but heavy: a header part is often hundreds of lines of nested comments. The editor's own block tools are not offered here (no "Open in Editor" for a template).
- Edit Block Markup...: The conflict message says "read it again and make the change there" but does not offer to reload; your edit is lost.
- Earlier Versions... (template): A template still from the theme always says it has no earlier versions, without saying why (only customized copies have revisions).
- Earlier Versions... (template): Rows are dates only; no author, no size of change.
- Reset to the Theme's Version...: The row's help says "Confirmed by name", but the confirmation is the ordinary preview with a Reset or Delete button; nothing is typed.
- New Template...: For a template part the help still says it starts from the template WordPress would use, but the code never looks one up for a part: it always starts empty.
- New Template...: A part is made with no area (header, footer), so it lands in General; not offered.
- New Template...: The preview title capitalises only the first word: "New Template part".
- Open in the Site Editor: Fine as a hand-off. The Site Editor is one of the least accessible screens in wp-admin, so its help could say what it is for ("to lay it out by sight") as the row help does.
- Properties (template): Field labels are developer descriptions (for example the schema's sentence describing the slug), and a 60-character cut can end mid-word.
- Properties (template): Not verified whether the content field is editable here; if it is, it is a second route to change a template that skips Edit Block Markup's line-by-line preview.
- The Additional CSS node: The column header "reach" holds a line count on a block theme. A listener hears "reach, 12 lines of Additional CSS".
- The Additional CSS node: On a classic theme, Enter announces only ` Opening Appearance > Customize > Additional CSS on {site} in your browser.`: the row's raw data has no `why`, so the reason sentence before "Opening" is empty.
- The Additional CSS node: On a classic theme, Go to Its Place in the Workbench selects Additional CSS, the node you are already in.
- Edit Additional CSS...: Good brace and markup checks before the preview, said in one sentence.
- Edit Additional CSS...: "Kept in Previous Looks" points at a feature the Workbench does not have; Previous Looks is only in the editor (Tools > WordPress > Manage > Previous Looks...).
- Edit Additional CSS...: A failed check throws the typed text away; the person has to retype the whole edit.
- The Patterns node: `wp/v2/blocks` returns unsynced patterns too, but every row says "a synced pattern" (not verified on a live site whether unsynced ones are filtered).
- The Patterns node: No way to edit a pattern's blocks, rename it, make one or delete one from its row. The editor's old Synced Patterns window had Edit (a "Blocks:" text box and a "Save Synced Pattern" confirmation), but its door now opens this node instead. Regression unless the schema sheet covers it (not verified).
- The Patterns node: Pattern categories: not found.
- The Patterns node: Row help "A synced pattern." is the shortest F1 in the Workbench and says nothing about what can be done.
- The Fonts node: Install a font and delete a font: not found in the Workbench. The editor's old Fonts window (wordpress_design_commands.py) offers both (`Install {name}`, `Delete {name}`), but its door now opens this read-only list. Regression.
- The Fonts node: No font faces (weights and styles) are listed; the Properties sheet shows the raw family settings.
- Style variations and Previous Looks: Three Workbench help strings say "kept in Previous Looks", but there is no Previous Looks node or command in the Workbench. Either add the node (Appearance > Previous Looks, listing global-styles revisions) or say "in the editor's Tools > WordPress > Manage > Previous Looks".
- Style variations and Previous Looks: Switching a block theme's style variation, one of the most common appearance jobs, has no place in the Appearance branch.
- wp-admin for This Place (Appearance nodes): Template Parts finds nothing, while Templates finds the Site Editor: the lookup falls back from `template_parts` to `template`, which is not a node key.
- wp-admin for This Place (Appearance nodes): Customize is mapped to Themes, not to the Appearance folder, so on a classic theme the Customizer is two levels away from where people expect it.

#### Plugins and themes

- The Plugins node: Every row's detail ends with "Updates and automatic updates are in wp-admin: Open in Dashboard." The same sentence on every one of forty plugins is exactly the chattiness GATE-13 warns about; say it once in the node's F1 or the status bar.
- The Plugins node: Delete a plugin: not found as a row action, although `wp/v2/plugins` can delete (the map's Plugins row says "Activate, deactivate, install and delete are in Plugins").
- The Plugins node: The refusal for an Editor talks about turning plugins on and off when they only opened the list.
- Activate or Deactivate: The label "Activate or Deactivate" does not say which it will do for this row. A listener must read the status column first or wait for the message box. Label it from the row's status ("Deactivate..." on an active plugin), and add the ellipsis since it asks.
- Activate or Deactivate: The plugin's Properties sheet has an editable Status choice (active, inactive). Saving it goes through the generic sheet save, which has no preview and never calls `deactivate_refusal` or `deactivate_warning`. So Alt+Enter, Status, inactive, OK can turn off the Application Passwords plugin that the context menu refuses to touch, locking the Workbench out. Read from wordpress_workbench_sheets.py and workbench_sheets.py; not tried live. This is the most serious finding in this section.
- Activate or Deactivate: "{plugin} put back." does not say which state it went back to.
- Activate or Deactivate: Network-active plugins on a multisite: deactivating sends `inactive` from a single site's route; not verified what WordPress does.
- Check on WordPress.org...: The row command checks every plugin on the site, not the row it was chosen on; the label reads as if it is about this plugin.
- Check on WordPress.org...: Consent is asked once per window per kind of question (plugins, themes, updates, languages): four separate "Ask WordPress.org" boxes for one source. Reasonable for privacy, but the person may agree four times in one session and is never told the agreement lasts only until the window closes.
- Find a Plugin on WordPress.org...: The consent question comes after you have typed the search, so declining wastes the typing; Check on WordPress.org asks first.
- Find a Plugin on WordPress.org...: The install is not in Change History. Ctrl+Z right after it undoes the change before it, silently. Either record it with an undo (delete the inactive plugin) or record it as "cannot be undone".
- Find a Plugin on WordPress.org...: After installing, the plugin is inactive and the next step (Activate) is not offered; the person must find the new row and use Activate or Deactivate.
- Find a Plugin on WordPress.org...: "installed on 1 of 1 sites" is the multi-site sentence reused for one site.
- Find a Plugin on WordPress.org...: The refusal sentence reads "Doing this (install plugins)", the only place a raw capability name is spoken.
- Find a Plugin on WordPress.org...: The command needs a plugin row to be selected; on a site with no plugins listed there is no row, so no way to find the first plugin.
- Open in Dashboard (plugin): The row help shared with themes says "for a theme, activating and installing", on a plugin row.
- Open in Dashboard (plugin): It opens the whole Plugins screen, not this plugin; the person has to find the plugin again in wp-admin's table.
- Open in Dashboard (plugin): After an update waiting is found, the detail says "Dashboard > Updates runs it", but Open in Dashboard on a plugin row goes to Plugins, not Dashboard > Updates.
- Check for Updates on WordPress.org... ("update waiting"): This is the cheapest real win wp_missing.md asked for, and it is here. But it checks one site per run. On Needs My Attention > Updates, which gathers every site, you must run it once per site (choosing a row of each), and the marks last only until the window closes. There is no "check every site" and no Watch that uses it.
- Check for Updates on WordPress.org... ("update waiting"): The Watch "Plugin updates available" (workbench_watches.py) still looks only for an update field the site itself sends, which core WordPress never sends, so the Watch stays silent even after this check finds updates.
- Check for Updates on WordPress.org... ("update waiting"): A plugin WordPress.org has closed is marked `Unknown: not on WordPress.org` (latest_plugins returns None for a closed plugin). A closed plugin is a security warning, not an unknown; Check on WordPress.org says "closed", this check hides it.
- Check for Updates on WordPress.org... ("update waiting"): Each row's detail keeps the earlier sentence too, so an Updates row can say "REST does not say whether an update waits." and then "so an update waits." in one detail.
- Check for Updates on WordPress.org... ("update waiting"): The command is on every plugin row, but it checks all of the site's plugins and themes and WordPress; the label suggests it is about the row.
- Check for Updates on WordPress.org... ("update waiting"): Up to 100 theme lookups, one request a theme; plugins one request each. On a site with many plugins this is slow, with no progress said beyond the background task name.
- Properties (plugin): See Activate or Deactivate: the Status choice skips the lockout refusal, the QUILL-relies-on warning and the confirmation.
- Properties (plugin): No "update waiting", WordPress.org facts, "Needs PHP" or "Network only" on the sheet, though the row's detail and `wp/v2/plugins` carry them.
- Theme rows: Activate...: The label has an ellipsis but opens no dialog; it opens the browser.
- Theme rows: Activate...: The spoken reason starts with "it cannot activate" immediately after you asked to activate, which sounds like a failure. Lead with the hand-off: "Activating happens in wp-admin; opening Appearance > Themes ...".
- Theme rows: Activate...: Nothing comes back: the Workbench does not notice the switch until a later read, when (up to five minutes later, on the next request) it announces `{site} changed since QUILL last looked: the theme is now {stylesheet and version}...` out of context.
- Theme rows: Find a Theme on WordPress.org...: Prefilling the search with the theme you already have makes the first search find that theme. An empty box would be the better start.
- Theme rows: Find a Theme on WordPress.org...: The search, the consent and the list all happen in QUILL, then the job is finished in wp-admin's theme browser, which is visual and searches again. The hand-off is honest but it is a dead end for a screen-reader user who wanted QUILL to install it.
- Theme rows: Find a Theme on WordPress.org...: No requirement is checked, although installing a theme needs `install_themes`.
- Theme rows: Open in Dashboard and Check for Updates: Activate... and Open in Dashboard open the same screen with the same sentence (Activate adds `?theme=`); two rows, one job.
- Theme rows: Open in Dashboard and Check for Updates: Delete a theme, update a theme, theme auto-updates: wp-admin only, said in the row; no Workbench path.
- wp-admin map rows for plugins: The WooCommerce Settings row now says Store Settings changes settings, which fixes the stale line wp_missing.md flagged.
- wp-admin map rows for plugins: Only seven plugins are mapped. Every other installed plugin's settings screen (a cache plugin, a security plugin, an SEO plugin other than Yoast) is not reachable through wp-admin for This Place on Plugins. A plugin row has no "Open Its Settings" action. Not found in code.
- wp-admin map rows for plugins: "wp-admin for This Place" is on the tree's node menu, under More, fourth of four. On the Plugins list you must move to the tree, open its context menu, open More, and find it. It is not on the plugin row's own menu.
- wp-admin map rows for plugins: "All of it in the Workbench" for Add New Plugin is generous: wp-admin's screen also uploads a plugin zip, which the Workbench cannot.

#### Settings

- The Settings node: The explanations are excellent and should be the model for other lists.
- The Settings node: The refusal says "Changing" to someone who only opened the list. An Editor cannot even read the site's time zone or date format here.
- The Settings node: Missing from the list because REST does not carry them (said only in the wp-admin map rows): who may register, the default role, the WordPress and site addresses, permalinks, search engine visibility, the privacy policy page, media sizes, discussion's moderation settings.
- The Settings node: The Site icon reads `picture {number}`; the picture's title is not looked up, unlike the front and posts pages.
- Read in Full (setting, default): Row help says "Alt+Enter changes it", which is right, but Enter is what people press to change a value in a list; a setting's Enter could open the change directly.
- Properties: Change a Setting: The Value box holds the raw stored value, not the friendly one the list shows: `posts` or `page` for Front page shows, a page number for Front page and Posts page, `0` to `6` for First day of the week, `open` or `closed`, an empty string for the standard post format, and the raw on/off for emoticons. The list knows the words (CHOICES) but the sheet offers no choice list, no page picker and no check box. A listener has to know WordPress's internal values to change most of these.
- Properties: Change a Setting: The value is sent as typed text, without converting it to a number or a true/false (workbench_edit.py puts the string straight into the body). Whether WordPress accepts "6" for start_of_week or "false" for use_smilies was not checked live.
- Properties: Change a Setting: The preview shows raw values too: "Front page (page_on_front): 12 becomes 34" tells a listener nothing about which pages those are.
- Properties: Change a Setting: The site-address and default-role guards can never fire from this list, because neither setting is in SETTINGS_FIELDS. Harmless, but the protection is in code nobody reaches here.
- Properties: Change a Setting: One setting per sheet: there is no batch sheet for settings, so changing title and tagline is two round trips.
- Language Pack Status...: It is on one site's setting rows but reports on every connected site. The label and placement suggest this site.
- Language Pack Status...: Installing a missing pack is wp-admin only (`WordPress's REST API cannot install or update a language pack.`), but the report has no "open Settings > General" action.
- wp-admin for This Place (Settings): Settings > Media and Settings > Discussion are mapped to Media and Comments, so they do not appear here, where a person who knows wp-admin's Settings menu looks for them.
- wp-admin for This Place (Settings): The reason sentences are long, and every one is spoken before the browser opens.

#### Tools

- Where wp-admin's Tools screens land: The Import and Export rows are stale. The Workbench's own Tools menu now has WXR Files > Export Site as WXR... and Import WXR as Drafts... (engineering log, 2026-11-14), yet the map still says "The WXR export is not in REST; Download My Writing, in the editor, saves posts." and marks both "Only in wp-admin". A person following the map is sent to the browser for something QUILL now does.
- Where wp-admin's Tools screens land: Tools > Available Tools maps to More from This Site, a list of REST namespaces; nothing there relates to the categories and tags converter. The Workbench does have Convert to Category or Tag... (Ctrl+Shift+K) on a term row, which the map does not mention.
- Where wp-admin's Tools screens land: With no Tools node, a person who knows wp-admin ("Tools > Site Health") has to know that Site Health is directly under the site, and that privacy is under Privacy Requests. The wp-admin Screens list is the only bridge, and it is under Overview, not where Tools would be.
- The wp-admin Screens node: A row's spoken detail is long: name, raw path, reach, reason, place, instruction. The path (`wp-admin/options-general.php`) is the least useful part for a listener and comes second.
- The wp-admin Screens node: There is no filter by reach, so finding "what can I only do in wp-admin" means Filter Builder or Show Only on the reach cell.
- Open in Dashboard (wp-admin Screens row, default): For a screen marked "All of it in the Workbench", Enter still leaves for the browser, after saying the Workbench does it all. The default for those rows could be Go to Its Place.
- Go to Its Place in the Workbench: Nothing is announced on success beyond what the tree says on focus, which is right by GATE-13.
- Go to Its Place in the Workbench: The failure sentence names the row by its internal key (for example `plugin_install has no place ...`): a wp-admin Screens row has no title-like cell, so its title falls back to its key.
- Properties (wp-admin Screens row): Not useful: everything here is already in the detail, and Node is an internal name. The engine requires Properties last on every menu, so it cannot be removed, but it could show the screen, path, reach and reason with proper labels.
- wp-admin for This Place...: Buried: fourth of four under More, on the tree's menu only. A row's own menu never has it. For the job it exists for (the thing REST cannot do here), it should be one level up.
- wp-admin for This Place...: The keyless reason says "only for what REST cannot do", but it also opens screens the map marks "All of it in the Workbench" (Menus, Widgets, Posts), with no question first.
- wp-admin for This Place...: "Empty Trash..." and "Counts by Status" sit beside it on every node's menu, including Menus, Settings and Site Health, where they mean nothing.
- Open This wp-admin Screen (privacy): Honest and complete for what REST allows. It is a pure hand-off: the node lists two fixed rows, not the requests, so it cannot tell you whether any request is waiting, which is the one thing a site owner needs from it (a legal deadline applies to these).
- Open This wp-admin Screen (privacy): When a plugin route exists the rows become plain problem rows (Read in Full and Properties only) that name the route, with no way to open or act on the requests.
- Go There (administration area): The browser case speaks the whole address (`Opened {full address} in your browser.`, the row's link, which for most areas ends in `wp-admin/plugins.php?plugin_status=active`). Every other hand-off says the screen's name.
- Go There (administration area): For Backups, Security, Caching and most others the "screen" is the Plugins list filtered to active, not the plugin's own screen, so Go There lands on a generic list.
- Go There (administration area): This list is the closest thing to a Tools node, and it is good orientation, but it is a flat list of 20-odd areas with long boundary sentences read in full.
- Import and export: Fix the map rows so wp-admin for This Place on Posts and the wp-admin Screens list point at WXR Files instead of sending people to wp-admin.
- Run... (ability row, default): The menu cannot show in advance whether a given ability will change the site; the tier is only decided when it runs, so a Read Only window hears the refusal after choosing Run.
- Run... (ability row, default): The cancel path is silent, unlike most Workbench previews.
- Offer to Ask the Site (ability row): Before this row existed (added 2026-11-14, coordinator report), the AI Abilities door sent people to the Workbench, where nothing could turn an ability on, so Ask the Site's refusal "Turn them on one by one in Abilities" was a dead end. It is now reachable, but only from the context menu.
- Offer to Ask the Site (ability row): The label is a toggle that does not say its current state; the list has no column showing which abilities are offered. A person must remember, or run it and listen to the outcome to find out (which flips it).
- Offer to Ask the Site (ability row): Consider "Offered to Ask the Site" as a column, or the label changing to "Stop Offering to Ask the Site" when on.

#### Site Health and maintenance

- The Site Health node: The test column is the first sentence of the line and the says column is the whole line, so every row reads its first sentence twice.
- The Site Health node: Good rows say "A problem a check found." on F1, even for `HTTPS: the site's address uses HTTPS.`
- The Site Health node: Every test runs each time the node loads (each test is its own request; the loopback test waits on the site), with no cache; opening Site Health is slow on a slow host. Not measured.
- The Site Health node: "Search engine visibility: WordPress does not share this over its API" contradicts Search and Upkeep, which does judge it (from the sitemap) and says where its answer comes from. Two answers to one question in one tree.
- The Site Health node: Nothing to do on a problem row: no "Open in Dashboard" to the test's own screen, no "how to fix" link, although WordPress's test answers carry an actions link. The only hand-off is through the node's wp-admin for This Place (Tools > Site Health > Status, marked "All of it in the Workbench").
- Read in Full and Properties (Site Health row): Test and Problem hold the same text; Says repeats it. Five fields, two facts.
- Information (Site Health > Information): Open in Dashboard on that row opens the browser silently: it runs the generic open-on-site command, which speaks nothing, while Open in Dashboard on a plugin or theme row says its reason first. (The reason is in the row's detail, already heard.)
- Information (Site Health > Information): The directory sizes are the Workbench's only "space used" view; the editor's Tools > WordPress > Manage > Space Used is separate. WordPress computes these sizes on request, so this node can be the slowest in the tree; nothing warns.
- Security (Site Health > Security): Clear and careful. The name "Security" promises more than one check; the Administration Areas row for security plugins is where the rest is said, and nothing here links to it.
- Needs My Attention > Site Health: It runs every site's full Site Health (every test on every site) to keep a few rows; on several sites this is slow.
- Needs My Attention > Site Health: "Worst first" holds within a site; across sites the gathered rows are not re-sorted by status (not verified on a live run).
- Needs My Attention > Updates: This is the least "needs my attention" list in Needs My Attention: it lists every plugin and theme on every site, waiting or not. Even after Check for Updates, the up-to-date rows stay. It should list only what waits (after the check) or be renamed Versions.
- Needs My Attention > Updates: Check for Updates runs per site, so with five sites the person runs it five times from rows of each site; the marks are lost when the window closes.
- Needs My Attention > Updates: Open Dashboard Updates in the Browser opens silently (the generic open-on-site command), while the detail already said it.
- Needs My Attention > Updates: The Properties sheet for a plugin or theme row is the raw REST payload (fields labelled from their keys, for example "Plugin uri", "Requires php", "Textdomain"); for the WordPress row, the four cells.
- Open Dashboard Updates in the Browser (Updates row, default): Updates are the one maintenance job a site owner must do, and here it is a pure hand-off to wp-admin's Updates screen, which is a long form of check boxes. Said honestly in every row; still a dead end.
- The Search and Upkeep node: Strong: every row says how it knows. The certificate warning inside 30 days is the kind of thing a site owner never sees until it is too late.
- The Search and Upkeep node: A missed schedule's detail says `Approve and Schedule on its row in Posts or Pages publishes it now.`, but that command is not on the upkeep row; you have to find the post again elsewhere.
- Open Where It Is Checked: On rows without their own link, "Open Where It Is Checked" opening the home page is a silent wrong answer.
- Open Where It Is Checked: Same command id as "Open on the Site" (Shift+Enter) elsewhere, under another label; Shift+Enter does the same here, which is not said.
- Move to Trash... (audit finding): Ctrl+Z does not undo it, although the item is only in the Trash and every other Trash move in the Workbench is undoable. Ctrl+Z here undoes the change before it.
- Move to Trash... (audit finding): Good that usage is shown in the preview itself, not only on request.
- Add Redirect..., Redirect This Address... and Change Redirect...: None of the three prompts has an access key (no `&` in "Old address...", "New address it leads to:", "Kind of redirect:", "Group to keep it in:"), unlike every other Workbench dialog.
- Add Redirect..., Redirect This Address... and Change Redirect...: A redirect write is not in Change History: Ctrl+Z after saving undoes something else.
- Add Redirect..., Redirect This Address... and Change Redirect...: "Kind: 301" in the preview drops the words the list used ("moved for good").
- Turn On or Off and Delete Redirect...: Delete Redirect's row help says "Gone for good, after you confirm by name", but it is an ordinary Yes/No box; nothing is typed, unlike Delete Permanently elsewhere.
- Turn On or Off and Delete Redirect...: "Turn On or Off" does not say which it will do.
- Test an Address...: Useful and safe. The help's "Nothing is sent" is true of the test; the first run does read every redirect from the site.
- Space used: wordpress.md marks Space Used in Site Check "in progress"; in the Workbench it is a set of Information rows, readable only by an administrator.

#### Snapshots and moving sites

- Take a Snapshot: Review note: the completion sentence is very long to hear. It reads out a full Windows path with a profile id, then the whole left-out list. A screen-reader user gets a 30-plus-word path read character-ish, and no way to act on it. Offer "Open the Snapshot Folder" or a report instead.
- Take a Snapshot: Review note: custom post types are not taken. Only `wp/v2/posts` and `wp/v2/pages` are read, so Events, Products, Podcast episodes and the rest are left out. So are templates, template parts, global styles, block-theme Navigation menus (`wp_navigation`) and form-plugin data. None of these appears in the left-out list, which names only "people, passwords, plugins, themes, revisions and comments". The person is told a snapshot is complete when it is not.
- Take a Snapshot: Review note: the menu help says "Everything but media, saved here." That is wrong both ways: media records are always saved, and much more than media is left out (see the note above).
- Take a Snapshot: Review note: "1 patterns", "1 media" and the like: the count words are never made singular.
- Take a Snapshot: Review note: there is no way to list, open, rename or delete snapshots from the Workbench. They pile up, with media files possibly large, in the data folder.
- Take a Snapshot: Review note: Ctrl+Alt+S (take a snapshot) is one modifier away from Ctrl+Alt+Shift+S (Put Back, which writes to the site) and from Ctrl+Shift+S (mark as Spam). Put Back is protected by a picker and a preview, so the risk is a startled moment rather than data loss. On keyboards where Ctrl+Alt is AltGr, these chords may also collide with typing in the filter box.
- Put Back from a Snapshot: Review note (critical): Put Back writes to the site with no Workbench Access, Safe Mode or View As Role check. A person who set a site to Read Only, or who is in Safe Mode, can still overwrite posts and pages from this menu.
- Put Back from a Snapshot: Review note (critical): it puts back far less than "set back to it" promises. For posts, pages and patterns only the title, content and excerpt are compared and sent; for terms, only the name and description. Status, slug, date, author, categories, tags, featured image, parent and menu order are never compared or restored. A post unpublished since the snapshot stays unpublished, and the preview does not say so.
- Put Back from a Snapshot: Review note (critical): an item deleted since the snapshot is "made again as a draft, at a new address" with only title, content and excerpt. Its categories, tags, featured image and parent are lost. A deleted category made again gets a new id, and no post is re-filed under it.
- Put Back from a Snapshot: Review note: items moved to the Trash since the snapshot are probably treated as deleted, because WordPress's `status=any` leaves out trashed items. Put Back then makes a duplicate draft while the original still sits in the Trash. A Restore from Trash would have been the right move. Worth checking on the live site.
- Put Back from a Snapshot: Review note: the chooser shows only a timestamp. There are no counts, no "with media files", no "taken on the practice site", and no way to read what a snapshot holds before choosing it.
- Put Back from a Snapshot: Review note: it is all or nothing. The preview is a read-only list, with no check boxes to put back only some items, unlike Split in By Name, which uses check boxes.
- Put Back from a Snapshot: Review note: the preview's default button is "Put Back", so Enter in the list sends the change. The confirmation dialogs elsewhere (crossing, Reset, Check Every Link) default to Cancel. Two different safety habits sit in the same window.
- Put Back from a Snapshot: Review note: the plan reads every post and page of the site (up to 1000 pages of 100) with no progress or count. A big site sits silent for a long time.
- Copy to Site: Review note: the success sentence says "new items are drafts there", even when every line was a Replace. A replaced published page goes live at once, and the spoken outcome hides that. Say how many were replaced live.
- Copy to Site: Review note: the permission check uses only the first selected row's kind. A mixed selection (a post plus a menu) is checked against post rights only.
- Copy to Site: Review note: "Connect a second site first: File > WordPress > Connect a Site." The Workbench's own File menu has no WordPress submenu. The path exists only in the editor, and unlike `_site_now`'s sentence this one does not say "in the editor".
- Copy to Site: Review note: there is no undo, and this is a write to another site. Ctrl+Z also cannot reach any earlier undoable change while this entry is newest, because `do_undo` only looks at the newest entry (see the Needs My Attention section's note on the undo stack).
- Copy to Site: Review note: the module docstring says custom terms travel; COPY_LEFT_OUT says "taxonomies other than categories and tags" do not. The preview is the one the person hears, so it is probably right, but the two disagree.
- Copy to Site: Review note: "Left out:" lines are mixed into the same "Each change" list as the actions, so arrowing through the plan reads things that will not happen as if they were steps.
- Compare Sites: Review note: status words are WordPress's raw values ("publish here, future there"), not the plain words used elsewhere ("published", "scheduled").
- Compare Sites: Review note: custom post types are not compared, and the omissions line does not name them.
- Compare Sites: Review note: it is a dead end. Nothing in the report leads to Copy to Site or Make Them the Same for a line, so acting on a difference means finding the item again by hand.
- Compare Sites: Review note: the report is one flat list with no per-kind headings or counts at the top. On a big pair of sites the person must arrow through every line to learn the scale.
- Export Site as WXR: Review note: the counts are spoken with WordPress post-type slugs and never go plural: "12 post, 40 attachment, 2 wp_block". Use the plain names ("posts", "files", "synced patterns").
- Export Site as WXR: Review note: the outcome is spoken and then the report opens with the same sentence. The dialog's arrival cuts the speech off, and the person hears it twice. Speak nothing, or open nothing (GATE-13).
- Export Site as WXR: Review note: one bad date ends the whole export, and From and To are not checked against each other, so From after To gives an empty file. Ask again on the same field instead.
- Export Site as WXR: Review note: the Save dialog suggests no file name (such as "{site} {date}.xml"), so the person types one every time.
- Export Site as WXR: Review note: an Everything export writes commenters' emails and IP addresses (`wp:comment_author_email`, `wp:comment_author_IP`) and authors' emails to a plain file. That matches WordPress, but neither the chooser nor the report says the file holds personal data.
- Export Site as WXR: Review note: no Practice Site crossing guard. That is correct for the export itself, but see Import below.
- Import WXR as Drafts: Review note (critical): the import skips Workbench Access, Safe Mode and View As Role, as Put Back does. It can make hundreds of drafts, terms and uploads on a site marked Read Only.
- Import WXR as Drafts: Review note: the order of questions is backwards. The person presses "Import as Drafts" and is then asked about files, and Cancel there throws away the yes they just gave. Ask about files before the preview, and show the choice in the preview.
- Import WXR as Drafts: Review note: the spoken result always ends "Ctrl+Z moves the drafts to the Trash", even when nothing was made. In that case no undo is recorded, and Ctrl+Z says "... This cannot be undone." The two sentences contradict each other.
- Import WXR as Drafts: Review note: no Practice Site guard. A WXR exported from the Practice Site can be imported into a real site with no crossing question, which is the very path the guard exists to stop.
- Import WXR as Drafts: Review note: undo leaves the new terms and uploaded files behind. It says so, but the person must then clean up by hand across two lists.

#### By Name

- The By Name node and its children: Review note: F5 does not re-read. The scan is kept for five minutes (`_SCAN_SECONDS = 300`), and `refresh` does not clear it; only a By Name change does. After editing on the site, F5 shows the old answer, silently.
- The By Name node and its children: Review note: the scan reads at most 10 pages of 100 (1000 posts and 1000 pages, and the same for terms, media and people), and a cap is never said. On a bigger site, Rename Everywhere and Replace Everywhere change "everywhere" except the items past 1000, and the preview looks complete. The unread note covers refusals, not truncation.
- The By Name node and its children: Review note: the By Name node's F1 lists "terms, fields, authors, media, links, blocks" and leaves out patterns, forms and template parts, which are three of its nine children.
- The By Name node and its children: Review note: only posts and pages are scanned (`wp/v2/posts`, `wp/v2/pages`). Custom types that use a term, field or link are not counted, so a Rename can leave them behind. Check Every Link, by contrast, includes custom types.
- The value row's context menu: Review note (critical for discoverability): Check Every Link, the only command built for Links rows, is buried under More. Meanwhile Rename, Split, Merge and Reassign, which all refuse on a Links row, sit on top. On every other kind, Check Every Link sits under More and refuses. The menu does not adapt to the kind it is on.
- The value row's context menu: Review note: refused actions are enabled rather than disabled or hidden, so a screen-reader user tries each one to learn which work. The scope matrix already knows (`by_name_support`). Use it in `supports` so they read "unavailable", or leave them out.
- Where It Is Used (Enter): it is a read-only text report, not a list, so there is no way to open one of those posts from it. Compare the Broken Links window, which has "Open in Editor".
- Rename Everywhere: the preview's title keeps the menu's ellipsis ("Rename Everywhere..."). Every other preview in the window has a plain title. It is read as the dialog title on every open.
- Split: Review note: pressing OK with nothing checked does nothing and says nothing (`if not picked: return None`). Say "Nothing checked, so nothing moves."
- Split: Review note: the check-box group has no access key. It is the only control, so that is minor.
- Merge Into: Review note: tier mismatch. This row is Tier WRITE (`merge_value`), while Merge Into on a term row is Tier DESTRUCTIVE (workbench_actions.py), for the same irreversible term deletion. Under Organize access both are refused, but the tiers should agree, and DESTRUCTIVE elsewhere means confirm by name.
- Merge Into: Review note: the chooser lists every other term with no post counts, so the person cannot tell "News (300 posts)" from "news (1 post)". The By Name row itself shows the counts.
- Replace Everywhere: the media chooser lists bare file names from the library ("IMG_2041.jpg"), with no title or alt text. For a screen-reader user choosing a replacement picture by file name alone is guesswork.
- Find Items Missing This Field: like Where It Is Used, it is a dead-end text report with no Open.
- Check Every Link: Review note (critical for discoverability): see the menu note above. The command is under More, and only one of nine By Name kinds can use it. A Links node command, or a node context-menu row, would be easier to find than a row command that ignores its row.
- Check Every Link: Review note: the label never changes. While a check runs, the same "Check Every Link..." row, with its ellipsis promising a dialog, silently means Stop. Show "Stop Checking Links" while one runs.
- Check Every Link: Review note: one check at a time across all sites, and choosing it on another site's Links row stops the running check instead of starting one. The person hears "Stopping the link check..." when they meant "check this site".
- Check Every Link: Review note: skipped types are silent. A custom type the account cannot read is dropped with no line, so "All 300 links ... work" can be said for a partial read. By Name's unread rows exist for exactly this.
- Check Every Link: Review note: the result is spoken and then the Broken Links window opens with the same sentence as its purpose. The window title interrupts the speech (GATE-13, said twice).
- Check Every Link: Review note: "Open in Editor" opens only the first item that holds the link. A link on 22 pages needs 22 trips, with no way to choose which holder; the details pane lists them but they cannot be opened. Replace Everywhere is the bulk fix and is not offered from this window.
- Check Every Link: Review note: the check runs on the window's two-worker pool, which list loading also uses. A run that takes minutes takes one worker, and with any other long job (a Practice Site start, a big Put Back plan) no node in the window loads until one finishes. See the Practice Site note.
- Check Every Link: Review note: it competes with Needs My Attention > Broken Links (a sample of the first 40 links). The two are not linked: the Broken Links node does not offer "check everything", and this command's results do not feed that node.

#### Across Sites

- The Across Sites node: Review note: Ctrl+0 lands on an empty container. The person hears the node and an empty list, and must know to press Right Arrow. Ctrl+1 (Needs My Attention) avoids this by landing on Inbox, a child. Ctrl+0 could land on Tags and Categories, or the container could list its children as rows.
- The Across Sites node: Review note: a row's detail is one long run-on sentence of variants, missing sites and, for plugins and themes, the same REST disclaimer on every row. Arrowing down a 40-plugin list repeats the disclaimer 40 times if the details pane is read. Put the disclaimer in the node's help once.
- The Across Sites node: Review note: the Plugins variant is "version {v}, {status}", which mixes two facts into one variant. See Make Them the Same.
- Across row context menu: Review note (critical): across rows carry no site (`WbRow("across", "", ...)`), so the window's `refusal_for` returns nothing for every across action. Each handler must check access itself:
- Across row context menu: Make Them the Same and Revoke Everywhere check per site.
- Across row context menu: Install on Sites Missing It checks nothing.
- Across row context menu: Promote to Network checks only `activate_plugins`, not Workbench Access.
- Across row context menu: Under Read Only access, Safe Mode or View As Role, those last two still write.
- Across row context menu: Review note: Revoke Everywhere is irreversible ("a revoked password cannot be restored") but is Tier WRITE, the same tier as Make Them the Same. It should be DESTRUCTIVE, like Delete Permanently, with a confirmation by name.
- Across row context menu: Review note: five of seven actions refuse on most kinds. Hide the rows a kind cannot use; the scope matrix already says which.
- Make Them the Same: Review note (critical): for plugins, the variant includes the version, but the edit sends only `{"status": ...}`. Choose "version 2.3, active" when another site has "version 2.1, active": the plan says "changes from version 2.1, active to version 2.3, active", the request changes nothing, and the outcome says "2 of 2 sites changed to version 2.3, active". That is a false success. Either compare plugin status only, or say plainly that versions are not changed and point to Open in Dashboard.
- Make Them the Same: Review note: Make Them the Same on Settings can push values such as `siteurl`, `home` or `admin_email` from one site to the others. Those are in `wp/v2/settings`. The preview lists them, but nothing warns that some settings are site-identity values that must never be the same.
- Make Them the Same: Review note: the winner chooser shows only variant words, not which sites hold each variant or how many. The person must read the row's Properties first to know which is the majority.
- Revoke Everywhere: Review note: the Ctrl+Z sentence is doubled: "It cannot be undone. This cannot be undone." `do_undo` appends its own "This cannot be undone." to a summary that already says it.
- Revoke Everywhere: Review note: a destructive, irreversible action whose preview defaults to "Revoke" on Enter. Every other irreversible action in the window (Delete Permanently, Reset) asks with Cancel as the default.
- Compare Global Styles: Review note: it compares every site's styles in effect, not the selected theme's. The row the person chose makes no difference beyond being a theme row.
- Compare Global Styles: Review note: spoken, and then a report with the same sentence opens (GATE-13).
- Install on Sites Missing It: Review note (critical): installs plugins with no Workbench Access, Safe Mode or View As Role check, and no `install_plugins` check.
- Install on Sites Missing It: Review note: plugin installs are not recorded in Change History, so they do not appear in Edit > Change History either. Every other site change in this section is recorded.
- Install on Sites Missing It: Review note: declining WordPress.org consent still goes straight to an install preview, which installs from WordPress.org anyway. Saying no to "ask WordPress.org" and then pressing Install sends the request to the site, which itself asks WordPress.org. The consent wording should make clear what "no" covers.
- Open in Dashboard: one site at a time. "Open it on every site missing it" is what Install already does for themes, but Open in Dashboard has no "all" choice.
- Properties on an across row (Alt+Enter): the sheet's only purpose is reading; it adds no actions. Fine, but the row's detail already holds the same text.
- Site Sets: Review note: the person types a set name blind. Existing sets are never listed, so changing "Client sites" means remembering its exact spelling, and a typo silently makes a second set. Start with a chooser of existing sets plus "New Set...".
- Site Sets: Review note: there is no rename. A set is deleted only by unchecking every site, which is not discoverable from the first dialog.
- Site Sets: Review note: members are stored by display name. Renaming a site, or a Practice Site picking up " (practice)", drops it from every set with no word said.
- Across Sites Scope: Review note (critical for trust): the scope is invisible and short-lived.
- Across Sites Scope: It is not in Where Am I (Alt+1), not in the status bar, and not in the node help.
- Across Sites Scope: It is kept only on the provider object (`self.scope`), so closing the window returns it to every site.
- Across Sites Scope: The chooser always starts on "Every site", whatever the current scope.
- Across Sites Scope: A person who set "Client sites" yesterday and presses Make Them the Same today is changing every site.
- Across Sites Scope: Review note: the scope covers Across Sites, the Fleet and Compare Global Styles only. The Calendar, Needs My Attention, Watches and Copy to Site's site list ignore it. The help names "Across Sites and the Fleet", which is accurate but easy to miss.
- Across Sites Scope: Review note: if the chosen set is removed, the scope silently becomes every site (`members is None`).
- Calendar: Review note: days run oldest first, so the list opens on two weeks ago. Today and the coming week, the part people plan with, are in the middle. Start at today, or select today's row.
- Calendar: Review note: the day words have no year, so late December and early January read the same pattern with no year cue.
- Calendar: Review note: each status and type is capped at 300 (`max_pages=3`), and no row says so.
- Calendar: Review note: rebuilding the tree after each Calendar load (`wx.CallAfter(self._days_changed)`) may make the screen reader re-announce the tree or move its virtual position. Worth a JAWS and NVDA check.
- Fleet: it is read only and that is said ("The Fleet only reads; it changes nothing."). It is a good summary view, but nothing links a "critical" health state to Needs My Attention > Site Health.

#### Needs My Attention and Watches

- Needs My Attention and Inbox: Review note: Inbox's F1 says "Everything below Needs My Attention". It actually holds four of the twelve: waiting comments, pending review, spam and form responses. Scheduled, drafts, updates, health, accessibility, broken links and membership orders are not in it.
- Needs My Attention and Inbox: Review note: a stopped Practice Site stays connected. Every Needs My Attention node then starts with "Could not ask Practice Site" every time QUILL starts (the site stops when QUILL closes). Mark a practice site as stopped rather than failed, or leave it out of the account-level lists while it is not running.
- Needs My Attention and Inbox: Review note: "Could not ask {site}" rows have kind "fact", so their F1 says "A fact about the site. Enter reads it in the details pane." That is accurate enough, but it would help to say what to do (check the connection, or Site Properties).
- Needs My Attention and Inbox: Review note: Broken Links here is a sample (first 40 unique links, said in its row). Its F1 does not mention Check Every Link under By Name > Links, the full version.
- Watches node: Review note: the rows read "on" and "off" but cannot be changed where they are. Space or Enter on "New comments waiting off" does nothing useful. Let Enter (or a context-menu row) turn a Watch on or off, or open Workbench Options with that Watch focused.
- Watches node: Review note: the row F1 ("A fact about the site") is wrong for a Watch row, which is about the account.
- Watches node: Review note: nothing the Watches said is kept. There is no "what changed" list on this node, so a sentence missed while away from the computer is gone. The node shows when the last round ran, but not what it found.
- Workbench Options (choosing Watches): Review note: the consent is only in F1. Checking a box starts network requests to every site, but the visible label says only "Watch: New comments waiting", and the screen reader reads the help only if F1 is pressed.
- Workbench Options (choosing Watches): Review note: the interval is not a choice. `watch_minutes` (minimum 15) exists in the options file and is shown on the Watches node, but no dialog sets it.
- Workbench Options (choosing Watches): Review note: "Workbench options saved." does not say what is now on. Saying "3 Watches on: comments, form responses, site down." would confirm the change without a trip to the Watches node.
- Workbench Options (choosing Watches): Review note: the window is titled "Workbench Options" but holds only Watches. Site Sets, which share the same file, live in another dialog.
- Workbench Options (choosing Watches): Review note: the help says "while the editor is open"; the Watches node says "while QUILL is open". Watches run from the editor's timer, in QUILL and in QUILL Lite, whether or not the Workbench is open. One wording, please.
- What Watches announce, and when: Review note (critical): one failed read silences every other Watch on that site. `_site_round` runs the comments check first, and any `WordPressApiError` (for example an Author account refused on held comments) is caught around the whole site (`except WordPressApiError: continue`). Form responses, updates, health and reviews on that site are then never said, every round, and nothing tells the person.
- What Watches announce, and when: Review note: "Plugin updates available" depends on an `update` or `new_version` field in `wp/v2/plugins`. Core WordPress does not send it (the Fleet's own docstring says core REST "does not report waiting updates"). On most sites this Watch will never speak, and its label promises otherwise.
- What Watches announce, and when: Review note: a round can produce a burst. Eight kinds times several sites, each sentence a separate announce, arrive at once and may interrupt each other or whatever the person is reading in the editor. Combine a round into one sentence ("3 changes: ...") with the details on the Watches node.
- What Watches announce, and when: Review note: "A new form response on {site}." is said whatever the count. Ten new responses sound like one. Watches only track the newest id, so the count is not known; say "New form responses".
- What Watches announce, and when: Review note: comments waiting are read one page of 100 (`max_pages=1`). On a site with a large backlog, new comments past the first 100 are not counted.
- What Watches announce, and when: Review note: the Practice Site stops whenever QUILL closes. With "A site not answering" on, the next session can say "Practice Site is not answering..." and later "Practice Site answers again." for something the person never meant to watch.
- What Watches announce, and when: Review note: ISO week codes ("2026-W46") are spoken as is in the form-spam sentence. "the week of 9 November" would be friendlier.
- What Watches announce, and when: Review note: Watches ignore Across Sites Scope and Site Sets; every connected site is asked.

#### Practice Site

- Practice Site node: Review note: the node reports but cannot act. Its "What to do" row says "Tools > Practice Site starts it." Enter on that row, or a node context-menu row, should simply open the Practice Site dialog.
- Practice Site node: Review note: the first three rows are file paths, which are long to hear and matter only when something is missing. "Ready" or the missing piece would be enough, with paths in Properties.
- Start the Practice Site: Review note (critical): a start of up to five minutes is silent. No "Starting; this can take three minutes the first time" is said at the start, and nothing is said during it. The person cannot tell a slow start from a hung one. Say the expected wait up front, and give a status-bar cell like Check Every Link's.
- Start the Practice Site: Review note: the start holds one of the window's two background workers for up to five minutes. With a link check running, no node can load until one finishes (see Check Every Link).
- Start the Practice Site: Review note: "Connect it in a moment." means opening the dialog again and choosing Connect. Starting and connecting are two trips for what is always wanted together. Connect when the start finishes, or offer "Start and Connect".
- Connect It as Practice Site: Review note: Connect stays on the menu after connecting. Choosing it again says "already connected", which is fine, but the dialog could say "Connected" in the choice instead.
- Connect It as Practice Site: Review note: the site always shows under Sites as "(practice)" (practice_label), which is the right protection; every preview and history line carries it.
- Stop the Practice Site: Review note: "practice site" is lower case here and in Reset's sentence, but "Practice Site" in the menu, the dialog title, Start's sentence and the node. A small thing, but braille shows it.
- Stop the Practice Site: Review note: Stop runs on the UI thread (`stop_process` is called directly, not through `background`). On Windows this may run taskkill and wait, which freezes the window briefly with no announcement.
- Stop the Practice Site: Review note: the profile stays connected after Stop, so every account-level node (Needs My Attention, Calendar) lists "Could not ask Practice Site" until it is started again or forgotten.
- Reset the Practice Site: Review note: Reset is unreachable when a piece is missing. The dialog does not open at all if the tool, Node or core files are absent, so a person cannot clear an old practice site's data and its stored password on a build that no longer has the tool. Reset needs only the folder.
- Reset the Practice Site: Review note: a snapshot of the Practice Site survives a Reset (snapshots are keyed by the profile id, which Reset forgets). Those snapshots can no longer be reached from Put Back, because Put Back looks under the current profile's id. They are orphaned on disk.
- The practice crossing question (used by other commands): Review note: WXR is a gap in the guard. Export from the Practice Site, then Import WXR as Drafts into a real site, carries practice work across with no question.
- The practice crossing question (used by other commands): Review note: the question comes before the command's own preview, so the person agrees to "send it" before seeing what "it" is. That order is deliberate in the code ("every cross-site write calls this before its own preview"). A sentence in the preview ("This comes from the Practice Site") would keep the reminder in view at the moment of the real decision.
- The practice crossing question (used by other commands): Review note: on the Cancel default, Enter cancels. That is the right default for this question, and it is the opposite of every preview's default, so the same Enter key means "go ahead" one dialog later.
- Undo across this section (Ctrl+Z, Edit > Undo WordPress Change): Review note (critical): a non-undoable entry blocks the whole stack. After any of the commands above, Ctrl+Z can no longer reach the undoable change made just before it (a Trash, a Rename Everywhere). The person hears "... This cannot be undone." and may conclude the earlier change cannot be undone either. Skip past non-undoable entries, or say "The newest change cannot be undone; Change History lists the earlier ones."
- Undo across this section (Ctrl+Z, Edit > Undo WordPress Change): Review note: summaries that already say "It cannot be undone." get " This cannot be undone." added (Revoke Everywhere).

#### Gravity Forms

- Where Gravity Forms appears in the tree: a response row's title is "{form title} entry", so every response to one form has the same name. "Added a note to Contact entry on Example Site" never says which entry. The entry number is in the Properties sheet but not in any spoken outcome.
- Where Gravity Forms appears in the tree: the list shows no column that tells two responses apart (no submitter name or email). Only the details pane carries the first three answers.
- Context menus on Gravity Forms rows (order as shown): New Gravity Form is under More on every form row, but it acts on the site, not on the form you are on. On the form menu it is the only row that ignores the selection.
- Context menus on Gravity Forms rows (order as shown): the form row's F1 sentence says "Enter lists responses; the context menu shows its feeds and results, tests it, and changes a field type." It does not mention Edit Form, New Gravity Form or the two Copy commands.
- The Item menu for Gravity Forms: the four chord rows have no access letter, so walking Item by letter cannot reach them. Every other Item row has one.
- The Item menu for Gravity Forms: Ctrl+Alt+F for Star and Ctrl+Alt+I for Resend are hard to guess. The help says "Star it to come back to. Ctrl+Alt+F." and gives no hint why F (flag) or I.
- The Item menu for Gravity Forms: the labels differ between the two menus: "Notes..." on the context menu and "Entry Notes..." on Item; "Star or Unstar" against "Star or Unstar Entry"; "Copy as a Gravity Form..." against "Copy QAF Form as a Gravity Form...". A listener who learns one name hears another.
- Permissions (applies to every Gravity Forms command): "You are Editor on" has no article. The core permission sentence elsewhere says "You are an Editor on". Two styles of the same message sit side by side in one window.
- Permissions (applies to every Gravity Forms command): Change a Field Type checks gravityforms_create_form, but Edit Form, which can change every field, checks gravityforms_edit_forms. Someone who may edit forms but not create them can rebuild a whole form in the editor, yet is refused the smaller job.
- Permissions (applies to every Gravity Forms command): Not Spam and Spam on a response check the WordPress capability edit_posts (requirement "forms"). They do not check a Gravity Forms permission, unlike every other Gravity entry command.
- Read in Full (response, feed, result): the details pane names answers by field number ("3: Jane"), not by question label. Properties does better (labels from the form). The pane is what a listener hears first.
- Not Spam (response): "and the site was told" is true for QAF, which reports to its spam providers. For Gravity Forms only the status changes; no spam service hears about it. The sentence overclaims.
- Not Spam (response): on a response that is not spam, the outcome says "approved", a comment word that means nothing for a form entry.
- Not Spam (response): set_entry_spam sends row.raw, the entry as it was when the list loaded. It does not read the entry again first, unlike Star, Read and answers. An answer changed in wp-admin since the list loaded is overwritten with the old copy. This is a silent data-loss risk.
- Not Spam (response): Unapprove (Ctrl+Shift+U, on the Item menu) on a response also sets it not spam, while its label says "Back to waiting".
- Spam (response): the same stale-copy risk as Not Spam. The help "Hold it as spam." is the only explanation; nothing says whether Gravity Forms then hides it from the Responses node (it moves to Held as Spam after the refresh).
- Notes... (response): the notes are shown in a dialog built for change previews. The list is labelled "Each change:" and its help says "One line for each thing the change creates, replaces or skips". Both are wrong for reading notes, and the listener hears them every time.
- Notes... (response): Enter in the notes list presses the default button "Add a Note...". A person reading notes with Enter in mind ends up in the Add a Note box.
- Notes... (response): long notes are one list row each; a listbox truncates nothing, but there is no way to read one note in a text box or copy it, except the read-only report version for people who cannot add.
- Star or Unstar (response): the list has no Starred column, so after the refresh nothing tells a listener which rows are starred except Properties.
- Mark Read or Unread (response): "Marked read 3 entries" reads oddly; "Marked 3 entries read" would be natural English. No Read column either.
- Resend Notifications... (response): because it is recorded with no undo, Ctrl+Z straight after says "{that sentence} cannot be undone." (history.py), with a doubled full stop ("Admin Notification. cannot be undone."). It also blocks Ctrl+Z for every change before it, since the history never steps past an un-undoable change.
- Resend Notifications... (response): unchecking every box and pressing OK returns an empty list. The code treats that as Cancel and says nothing.
- Properties on a response, and editing its answers: a choice answer (drop-down, radio, check box part) is a plain text box. Nothing offers the form's choices, so a typo stores a value the form never allowed. The same goes for dates and numbers: no check before sending.
- Properties on a response, and editing its answers: a check-box field's parts each become a field ("Toppings, Cheese"), and the value is the choice value, not "checked". An empty part means unchecked, which a listener must guess.
- Properties on a response, and editing its answers: fields locked by edit_posts give a WordPress-role reason, then the save gives a Gravity Forms reason. A person can be told two different things for the same edit.
- Properties on a response, and editing its answers: the undo sends without the date_updated check, so Ctrl+Z after someone else's later edit overwrites it.
- Properties on a response, and editing its answers: the sheet's title is "{form} entry Properties", with no entry number. The number is only inside General.
- Properties on a feed or a result: this is a raw dump. Meta is JSON text, and the key names are Gravity Forms' own. Nothing here is editable, although Rename and Activate exist on the menu.
- Properties on a form: the sheet title comes from the row's title, which for a form row is its plugin cell, so the title is "Gravity Forms Properties - {site}", not the form's name. (The commands work around this with a replace; the sheet does not.)
- Properties on a form: the generic sheet is not where a form is edited (Edit Form is), but nothing on it says so.
- Show Its Feeds (form): filtering by title means two forms with the same title share their feeds in the view.
- Show Its Results (form): a form with no quiz, poll or survey field adds no rows (load_results skips it), so the filtered list is empty and nothing from the Gravity Forms code says the form has nothing to count.
- Test This Form... (form): the edit box uses Gravity Forms' input names (input_3_3), not question labels. A listener cannot tell which line is which question until the preview, which shows labels. This is the biggest usability gap in Test This Form.
- Test This Form... (form): on a live site the warning is one line in a list. It is not a separate confirmation, and the default button still submits. Feeds such as Stripe or Mailchimp fire for real.
- Change a Field Type... (form): the type names here ("Single line text", "Drop-down list") differ from the form editor's ("Single Line Text", "Drop Down"). One product, two vocabularies.
- Change a Field Type... (form): "Cannot carry over" lists raw Gravity Forms keys ("enableChoiceValue", "randomize") that mean nothing to a listener.
- Change a Field Type... (form): the help for the editor's Type box points here to change a type ("Change a Field Type on the form changes it later"), but only 7 of the editor's 18 types convert. A Phone or Date field never appears in the Field list, with no sentence saying why.
- Edit Form... (form): Cancel (or Escape) in the editor throws away every edit with no "Discard changes?" question. After the Check Before Saving loop it is easy to lose a session's work with one Escape.
- Edit Form... (form): Remove Field takes effect at once in the editor with no confirmation. The preview catches it before anything is sent, but there is no in-editor undo.
- Edit Form... (form): the save preview says label placement as its code: "Label placement: left_label (was top_label)."
- Edit Form... (form): "Fields move:" speaks the entire field order, not what moved. On a 30-field form one move is a very long line.
- Edit Form... (form): the Choices syntax ("text = value", leading asterisk) is power-user markup typed into a text box, with the rules only in F1 help.
- Edit Form... (form): only the default confirmation and the Admin Notification are editable; others are kept untouched, and the editor never says that more exist.
- New Gravity Form... (site, from a Forms row or node): Ctrl+N on Forms always means a Gravity form. On a QAF-only site it says "Gravity Forms is not on {site}: ..." instead of making a QAF form or saying how to make one.
- New Gravity Form... (site, from a Forms row or node): "Entries were not touched." after making a brand-new form is noise.
- New Gravity Form... (site, from a Forms row or node): Ctrl+N on Forms > Responses, Feeds or Results is not mapped and gives the generic New Here sentence.
- Copy as a QUILL Accessible Form... (Gravity form): every other "make" command in this area undoes with Ctrl+Z; this one tells the person to go and delete the draft themselves.
- Copy as a Gravity Form... (QAF form): the new Gravity form goes straight to the site with no accessibility check, while Edit Form and New Gravity Form both run Check Before Saving.
- Delete Permanently... (feed): the Item menu help for Delete Permanently says "Gone for good, after you confirm by name." A feed is confirmed with a button, not by name, and Ctrl+Z brings it back, so the same row says two contradictory things.
- Delete Permanently... (feed): feed row F1 says "Shift+Delete deletes it", which is the only place the key is taught for feeds.
- Filter Builder on Responses (Gravity): on a site with both QAF and Gravity Forms, Filter Builder on Responses always opens the Gravity Forms builder (gravity_filter_builder returns True whenever the site has Gravity Forms), so QAF responses cannot be filtered by their questions there.
- Filter Builder on Responses (Gravity): five or six dialogs in a row to build one condition, each titled only "Filter Builder", so the title never tells a listener which step they are on.

#### Shop

- Where the Shop appears in the tree: the Shop node sits under the site even on a site without WooCommerce; opening it is how you learn there is none.
- Where the Shop appears in the tree: nothing gates a shop row by capability (needs is "" for products, orders, coupons, settings). An Editor sees every row enabled, fills in five dialogs, previews, and only then hears WooCommerce's refusal.
- Properties on shop rows (all kinds): this is not tailored. A product can have dozens of WooCommerce fields, in WooCommerce's order. The "Edit Product..." command and the sheet are two different ways to change a product, with different checks.
- Products: context menu: Enter leaves QUILL for the browser. On every other row type, Enter stays in QUILL. A listener pressing Enter to read a product is sent to the browser.
- Products: context menu: Move to Trash is under More, though Delete runs it.
- Edit Product...: the Status list does not start on the product's current status (no initial), so OK on a published product makes it published only by luck of order. If the first row is chosen by accident, a draft becomes published. The preview catches it, but only if the person reads it.
- Edit Product...: five modal dialogs for one change is slow. One sheet with five fields would be quicker to review and to correct.
- Edit a Variation...: Edit a Variation has an undo and a conflict check; Edit Product, its sibling, has neither.
- New Product...: New Product is on every product's menu, though it ignores the product.
- Move to Trash... (product): a Trash that can only be emptied or restored in wp-admin is a dead end. Reviews, by contrast, restore with Ctrl+Z.
- Shop orders: context menu: Enter opens wp-admin in the browser. Reading the order, which is what most visits are for, is the second row.
- Change Status... (order): a customer email is sent and there is no undo. That is correct, but the outcome sentence does not say the email went.
- Notes... (order): notes are listed in a single-line choice list; Enter on a note closes the dialog with nothing done. The two "Add" rows sit after every note, so on a busy order they are a long arrow away (End reaches them).
- Notes... (order): the Gravity Forms notes and the shop notes are two different dialogs for the same idea.
- Refund... (order): the strongest confirmation in the Workbench, and well worded. The only gap: the "How" list starts on the gateway, so OK on autopilot moves money.
- Customers: editing a billing address is one dialog per address line, about ten in a row, and Cancel on the eighth loses the first seven.
- Coupons: on Edit Coupon the Discount list does not start on the coupon's current kind, so a percent coupon edited for its date becomes a cart discount unless the person moves back to the first row.
- Store Settings: Change Setting...: the choice list does not start on the current value, so a listener cannot hear what is set without leaving the dialog.
- Product Reviews: the shop's best-behaved area, with selection, outcomes, undo and conflict checks. It shows what the product, order and coupon commands are missing.
- Shipping Zones, Tax Rates, Tax Classes, Attributes, Brands, Webhooks: the Delete command for zones, attributes and brands is labelled "Delete..." while the help on the Item menu says Delete Permanently is "confirm by name". Here it is a preview button, which is fine, but three words for the same idea (Delete, Delete Permanently, Remove) appear in one product.
- Shipping Zones, Tax Rates, Tax Classes, Attributes, Brands, Webhooks: removing a shipping method sends at once after the preview and records no undo.

#### Events

- Events: context menu: as with products, Enter goes to the browser.
- New Event...: there is no way to choose an organizer or categories at creation; categories need a second command.
- New Event...: typing "YYYY-MM-DD HH:MM" by hand is error-prone; no date picker or "tomorrow at 7" understanding.
- Edit Event...: the help and the PLUGIN_ACTION_ROWS text both promise "title, start, end, time zone, venue and cost", but Edit Event never asks for the venue; it keeps the old one. A wrong promise.
- Edit Event...: "All day:" starting on "No" means an all-day event edited for its cost becomes timed unless the person changes it back.
- Events Between Dates...: a report rather than a filtered list, so you cannot act on what you find.
- Categories and Tags... (event): names typed must match existing terms; there is no list to choose from, though QUILL has just read them.
- Venues and Organizers: eight dialogs to make a venue, and a blank answer on an edit clears that field, which the preview shows but which is easy to do by Enter-Enter-Enter.

#### SEO

- Where SEO appears in the tree: the node is called "SEO" but is Yoast-only. A Rank Math or All in One SEO site hears only the error.
- Edit SEO...: seven dialogs for one item, and the indexing list does not start on the current setting.
- Edit SEO...: no running character count while typing the SEO title, though Search Appearance knows the limits.
- Bulk SEO Editor...: the Bulk SEO Editor is on every SEO item's menu, though it opens the whole site.
- Open in Dashboard (Site SEO row): half the Site SEO node is pointers to wp-admin. That is honest, but it is the plugin's hand-off.

#### Memberships

- Where memberships appear in the tree: the Discount Codes list is usually just a pointer row to wp-admin, so the node promises a list it rarely has.
- Membership row context menu (every pmpro row): the two discount-code commands appear on a level, an order and a subscription row too, where they have nothing to do with the row. A level row has no level command at all.
- Membership row context menu (every pmpro row): Properties is a raw read-only sheet of the item's fields.
- Look Up a Discount Code...: the answer is only spoken. There is no window to read it again or copy it.
- New Discount Code...: levels must be typed as numbers learned in wp-admin, though the Membership Levels node lists them. The preview passes no level names, so it says "Level 2 (level 2)", which says the number twice and the name never.
- New Discount Code...: the code is upper-cased silently.
- Show Memberships... (on a person): the dates are the site's raw strings, not friendly dates as elsewhere.
- Show Memberships... (on a person): the membership rows (Show, Check Access, Change, Cancel) are on every person's menu on every site, PMPro or not. Not found in code: any hiding or greying of them on a site without PMPro.
- Check Membership Access...: words from a title take the first search result without saying so or offering a choice. A common word can check the wrong page.
- Change Membership Level...: the fallback asks for a number from wp-admin.
- Change Membership Level...: no undo for a change that stops a recurring payment; the preview says so only for cancellation.
- Cancel Membership...: the dialog's own Cancel button sits next to "Cancel Membership". A listener hears "Cancel Membership, button" and "Cancel, button" side by side, and Escape is the safe one. A button named "End Membership" would avoid the clash.
- Cancel Membership...: tier 3, but confirmed by one button, while a refund asks for the amount typed.

#### Redirects

- Add Redirect...: no undo for a new redirect, though deleting what was just made would be safe.
- Add Redirect...: the preview does not warn when the new redirect makes a chain or loop, though Test an Address can work that out from the list already read.
- Turn On or Off: a reversible on/off with a confirmation but no Ctrl+Z is backwards: every other on/off in the Workbench undoes.
- Delete Redirect...: the row help says "Gone for good, after you confirm by name", and the Administration Areas text says "deleted after a confirmation by name". The code asks a plain Yes/No; nothing is typed. The help is wrong.
- Delete Redirect...: QUILL has the redirect's fields, so an undo that makes it again would be easy and would match feeds and tax rates.
- Test an Address...: a clear, useful answer. It uses the list as last read, so a redirect added in wp-admin since is missed until F5.
- Redirect This Address... (404): the 404 stays in the log after it is redirected; nothing marks it done.
- Add a Redirect after a new slug: it uses the default group without asking, unlike Add Redirect, and a 301 without offering the kind.

#### Multisite

- What there is not: a person managing a 20-site network must connect each subsite by hand, with its own application password. Nothing says this in the Sites node or in F1.
- Promote to Network...: when no site qualifies, only the first site's reason is spoken; the others are lost.
- Promote to Network...: each connected subsite counts as a network, so two subsites of one network say "network-active on 2 of 2 networks", and WordPress is asked twice.
- Promote to Network...: there is no "Demote" or network-deactivate, and no undo, for a change the summary itself calls one no single site can reverse.
- Promote to Network...: the check activate_plugins is a single-site capability; the real requirement (super admin) is only known when WordPress refuses.
- Network Admin row (wp-admin Screens): the row is listed on every site, single sites included (it has no namespace gate), so a single-site owner is offered a screen that does not exist.
- Plugin rows on a subsite: Activate or Deactivate offers "Deactivate" on a network-active plugin and sends status inactive from the subsite. QUILL does not check whether WordPress allows that from a subsite; any refusal is the site's own error, spoken as it comes.
