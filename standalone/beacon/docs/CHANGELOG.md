# QuillBeacon changelog

## Unreleased

- **AI in the Assist menu, when you want it.** The three local helpers stay
  first and still call no AI service. After them: Ask (Ctrl+6) about the
  selected beacon or your search results, Which AI Am I Using (Ctrl+8),
  Choose Your AI (Ctrl+4), and Describe a Saved Picture (Ctrl+F5), which reads
  the words in a beacon's picture on your computer first, sends the picture
  once, and offers the description as a note. QuillBeacon signs in on its own,
  as QUILL Beacon. A line at the bottom of the results pane says which AI is in
  use. Nothing runs on a timer, and Safe Mode turns it all off.
- **Organize What I Saved** (Ctrl+3, Assist menu): an AI task that searches
  your library, reads beacons, uses the local Suggest Tags, and tags beacons or
  moves them into collections. Every change is shown as text and waits for
  Apply, and Ctrl+Z undoes it. Needs GitHub Copilot or Codex.

## 0.1.0

- **Shared-runtime licensing.** Installed editions use the QuillVille Runtime,
  which currently carries PyMuPDF 1.28.2 under AGPL-3.0 through the shared
  GLOW dependency; Beacon does not itself expose GLOW. Release-specific source
  and legal review are required before the next public release. Portable
  contents must be checked separately. See Licences and Notices and the
  PyMuPDF distribution review.
