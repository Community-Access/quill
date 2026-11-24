# QUILL Social changelog

## 0.3.0

- **The demo timeline says it is a demo** (FUX-09, 2026-11-24). While the
  local demo account is your only account, the title ends with "(demo)" and
  launch says "QUILL Social ready. Demo timeline only. Add Account (Ctrl+Shift+A) connects Mastodon or Bluesky.", on the status bar too. It
  was explained only in F1 help.
- **Next and previous unread** (2026-11-23). Item > Next unread (Alt+.) and
  Item > Previous unread (Alt+,) move to the next or previous unread post
  in the view; past the last one you hear "No more unread."
- **Exports say where the file went** (2026-11-23). Feeds > Export OPML...
  ends with how many feeds went to which file in which folder ("Exported 12
  feeds to quill-social-feeds.opml in Downloads."). Item > Send to QUILL says
  "Saved the thread for QUILL in exports." instead of reading the whole path
  aloud, and says so when the file could not be written, where it used to say
  nothing.
- **Scribe for Documents** (2026-11-21). Item > Convert Linked Document with
  Scribe for Documents... (Alt+Shift+F6) converts a document a post links;
  Tools holds Conversions on This Computer and the other Scribe rows, on Alt+Shift+F7 to
  F11.
- **Help > What's New** (Ctrl+Alt+F1) opens this changelog. The family's
  usual key for it, Ctrl+Shift+F1, is the Keyboard Reference here.
- **Shared-runtime licensing.** Installed editions use the QuillVille Runtime,
  which includes PyMuPDF 1.28.2 under AGPL-3.0 through the shared GLOW
  dependency; Social does not itself expose GLOW. Its exact source, and that
  of every other GPL, LGPL or AGPL part, is published with each release.
  Portable editions leave GLOW, and with it PyMuPDF, out. See Licences and
  Notices.
