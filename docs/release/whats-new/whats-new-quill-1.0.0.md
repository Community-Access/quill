# What's new in QUILL 1.0

QUILL 1.0 is the first general release. These are the newest parts; the full release notes cover everything else.

## Writing

- **Document Statistics, pressed twice.** `Ctrl+Shift+G` gives the counts; press it twice quickly for paragraphs, sentences, long sentences, reading time and the reading grade. It counts the selection when there is one.

## WordPress

### Stripe and PayPal form setup

- Tools > Forms adds Insert Payment Field, Form Payments Setup and Verify
  Payment Setup. Stripe is the default; PayPal is also available. New settings
  use test mode, with confirmation before saving live mode.
- Paid-form publication checks plugin readiness and matching mode. Test on
  Site refuses published live-payment forms. Responses show and export payment
  metadata, with a confirmed Refresh Payment Status action.
- Checkout requires QAF payment contract version 1 on WordPress. Provider
  credentials and money movement stay on the site; no plugin deployment or
  live acceptance is implied by this desktop update.

- **File > WordPress** writes, opens and publishes your sites' pages and posts. Connect a Site fetches the password with your browser and keeps it in Windows Credential Manager.
- **Ctrl+S saves on this computer only.** Save Draft to Site and Publish or Update are separate, Publish checks the page first, and nothing someone else changed is overwritten.
- **Blocks, made plain:** Insert > WordPress Block, and Next Block, Previous Block and Where Am I in Edit > WordPress. A block QUILL does not know goes back untouched.
- **Tools > WordPress** has the Media Library, Check This Page with axe-core, Check the Whole Site with safe fixes in bulk, comments, menus, users and settings.
- **Keys:** Ctrl+Alt+Shift+Grave, then O to open, P to publish, D for a draft, M for the Media Library. The menus show every letter.
- File > Publish is gone; your saved connections come across by themselves.

## Forms

- **File > New Form** writes an accessible form as a short `.qaf` text document, in the language of the QUILL Accessible Forms plugin (formerly BITS Accessible Forms).
- **Tools > Forms > Fill It In Yourself** lets you tab through your own form as a visitor would, before anyone else sees it.
- Check This Form, rules read as sentences in Format > Form Rules, and saving as a web page, Word, large print or braille-ready text. Publish and Responses work with sites running the plugin.

## AI and code

- **Choose Your AI (Ctrl+4)** lists QUILL's free AI, your ChatGPT plan, GitHub Copilot, Codex and your own key. **Which AI Am I Using (Ctrl+8)** says where your words go.
- **Do a Document Task (Ctrl+3)** gives Copilot or Codex a job with several steps, and asks before each change.
- **Project tasks,** in the Developer profile: open a folder of code, press Ctrl+3, and review every change and every command before it happens. Undo Last Agent Turn puts everything back.

## Writing

- **Ctrl+Enter** inserts a page break, as in Word. Word documents keep their page breaks now.
- **The Command Palette (Ctrl+Shift+P)** finds every menu item, recent files and open documents included.
- **Tables** you can read cell by cell, and Insert Table (Ctrl+Alt+T). **Find in Open Documents** (Ctrl+Shift+F10).

## More

**Help > What's New** (Alt+H, W) opens the full changelog. QUILL Lite has all of this too, in the same places. The full release notes: https://www.quillforall.org/docs/release1.0.0.html. The WordPress and Forms guide: https://www.quillforall.org/docs/wordpress-forms-guide.html. Stuck? Help > Get Help from Support (Ctrl+Alt+F2).
