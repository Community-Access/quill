# Tutorial 2: Own the keyboard

**Goal:** move anywhere in QUILL without the mouse, and set up the keys the
way you like them.

## 1. The QUILL key (prefix commands)

QUILL has more commands than convenient key combinations, so it uses a prefix:
press the **QUILL key** (`Ctrl+Shift+Grave` by default; Grave is the key with
the tilde on it), then one more key.

Try these:

1. QUILL key, then `S`: insert a snippet.
2. QUILL key, then `X`: open the Copy Tray (a twelve-slot clipboard).
3. QUILL key, then `Shift+M`: the remote sites manager.

Press the QUILL key **twice** and Browse Mode locks on: letters and arrows act
as navigation commands until you press `Escape`. It works like your screen
reader's virtual cursor. One press is for just one command (Quick Nav); two
presses keep the mode on.

## 2. Deep navigation

- Jump by heading in Markdown documents; move by section; set and jump to
  named marks (palette > `mark`).
- Bookmarks are per-document and survive restarts, and QUILL reopens every
  saved file at your last cursor position.
- `Ctrl+Tab` cycles document tabs; the tab name is announced on switch.

## 3. The Keymap Editor

**Preferences > Keyboard** opens the editor. Three things to try:

1. **Reverse lookup.** In the search box, type a *shortcut*, such as
   `ctrl+alt+m`, or even `Control + Shift + K`. It does not mind how you spell
   it or what order you type the keys in. QUILL tells you which command owns
   it, or that it is free.
2. **Record Keys.** Select a command, choose Record Keys, press the keys you
   want. Done. If those keys are already in use, QUILL tells you which command
   has them and offers to move them for you. It never takes them without
   asking.
3. **Run Diagnostics.** Checks all your keys for problems: a key given to two
   commands, a key for a command that no longer exists, or a key that does
   nothing. **Heal** fixes what it can in one step.

Export your keymap as a `.kqp` keyboard pack to share it or carry it between
machines.

## 4. Ask, don't wait: status queries

You can ask QUILL about where you are whenever you like. These are all in the
palette: **Where am I?**, **What changed?**, **Speak Status**, and **Describe
Formatting at Cursor** ("Arial, 14 point, centered, bold").

## 5. Exercise

1. Rebind **GLOW Audit Current Document** to a key of your choice.
2. Use reverse lookup to find out what `Ctrl+Shift+Z` does.
3. Enter Browse Mode (QUILL key twice), navigate a long document by heading,
   press `Escape`.
4. Open the Spoken Echo (`Alt+Shift+E`) and review what all of that
   announced.

**Next:** [Rescue a scanned PDF](03-rescue-a-scanned-pdf.md).
