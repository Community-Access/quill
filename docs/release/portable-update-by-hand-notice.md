# Portable copies: please update by hand this time

*A notice for the website and the release notes. Draft, 2026-10-17: not yet
published or sent.*

## Who this is for

You need this only if you use a **portable copy**, the one you unzipped
instead of installing, of either of these:

- **QUILL Lite 1.1.2**
- **QUILL 0.9**, any 0.9 version

If you installed with a Setup program, you are not affected: update the usual
way. Quill Radio 3.0.4 and earlier are not affected either; they have always
been updated by hand.

Not sure which version you have? Open **Help > About** in the program.

## What is wrong

In those portable copies, the **Install and restart now** button in **Check
for Updates** can delete your settings, recovered work and everything else in
the copy's `data` folder. The fault is in the updater that came with your old
copy, so the new version cannot fix it for you. Files deleted this way do not
go to the Recycle Bin.

The new versions carry a fixed updater, so this is the last time you need to
do it by hand.

## What to do

Do not choose **Install and restart now** in that copy. If it offers an
update, choose Close. Then:

1. **Close the program.** Close QUILL Lite or QUILL completely.
2. **Back up your data folder.** Open the folder you unzipped it into. Next to
   `QuillLite.exe` (or `quill.exe`) is a folder called `data`. Copy it, not
   move it, to somewhere safe, such as your Documents folder or another
   drive. This is your settings, keys and recovered work.
3. **Download the new portable zip** from the QUILL download page. For QUILL
   Lite it is the file whose name starts `QuillLite-Portable`.
4. **Unzip it next to the old one**, into a new folder, for example
   `QuillLite-new`. Do not unzip it on top of the old folder.
5. **Copy your data back.** Open your backed-up `data` folder, select
   everything in it (Ctrl+A) and copy it (Ctrl+C). Then open the `data` folder
   inside the new folder and paste (Ctrl+V). If Windows asks about files with
   the same name, choose **Replace the files in the destination**, so your own
   files win.
6. **Start the new copy** from the new folder. Check **Help > About** shows
   the new version, and that your settings and recent documents are there.
7. **Tidy up when you are sure.** Delete the old folder. Keep your backup
   for a week or two in case you missed something.

If you carry the copy on a USB stick, do all of this on the stick, so the new
folder and its `data` folder stay together.

## If your data is already gone

If you have already used **Install and restart now** and your settings are
missing, the files cannot be brought back by QUILL. Look for a backup you made
of the folder, or your computer's own backup or File History. We are sorry.
Please tell us, so we know how many people this reached.

## Why it happened

Every portable zip carries a `data` folder: it is what tells the program to
keep everything inside the copy. The old updater swapped the new files in by
mirroring the new folder over the old one, and the mirror treated the files
you had in `data` as extra and removed them. The updater that does the swap is
the one in your old copy, which is why the fix only helps from the next update
on.
