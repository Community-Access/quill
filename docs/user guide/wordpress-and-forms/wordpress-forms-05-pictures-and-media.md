# Chapter 5: Pictures and the Media Library

## What this chapter covers

Pictures, sound and video make a page, and they are where most
accessibility problems hide. This chapter covers all of it.

You will put a picture in a page with good alternative text, work with the
Media Library in the Workbench, replace a file that pages already use,
upload, make a picture smaller, edit it on the site, make a new picture with
AI, and change the site logo. Then you will hear what a sighted visitor sees,
make captions, transcripts and listening versions, and tidy the library. It
ends with posting from QUILL's other apps.

By the end every picture on your page will say what it shows, and you will
know where every file in your library is used.

## Putting a picture in a page

There are two ways in, both in the Insert menu:

- **Insert > Picture from the Media Library...** puts in something already
  on your site. It opens the WordPress Workbench on your site's Media. Move
  to the file you want and press Enter. The editor comes back to the front
  with the picture window open, and the picture goes in at your caret.
  Picking ends after one picture, or when you close the Workbench. A file
  from a different site than your page's is refused, and you are told why.
- **Insert > Picture from This Computer...** uses a file of yours. It goes
  into the page straight away, marked as not uploaded yet, and is uploaded
  the next time you choose Save Draft to Site or Publish. Its address is
  swapped in then.

Either way the picture window opens, and that is where you say everything
about it:

- **Alternative text:** what the picture tells someone who cannot see it.
- **Decorative:** check this for a divider, a border or a texture, so screen
  readers skip it.
- **Caption:** visible text under the picture, for names or a photo credit.
- **Display width:** how wide it shows. The proportions are always kept.
- **File size:** which of the sizes WordPress made of the picture to use,
  such as "Medium, 300 wide", when the picture is already in the library.
- **Use as featured image:** the picture that stands for the whole page in
  lists and when the page is shared.
- **Link to:** where the picture links to, if anywhere.

Press **Insert**. You hear "Picture inserted:" and its alternative text.

Sound and video from the library go in as players, and documents, such as a
PDF, go in as a link.

## Writing good alternative text

Alternative text is read instead of the picture. A few habits make it good:

- Say what the picture is for, in a sentence or two. "Volunteers sorting
  donations at the spring fair" says more than "people at tables".
- If the picture shows words, such as a poster or a sign, read them out.
- Leave out "image of" or "picture of". A screen reader already says it is a
  picture, and Check Before Publishing flags it.
- Never use the file name. `IMG_2041.jpg` tells nobody anything, and QUILL
  flags that too.
- If the picture adds nothing a visitor needs, such as a decorative
  flourish, check Decorative and write nothing.
- For a chart or a diagram, keep the alternative text short and put the
  detail in a paragraph after the picture.

## Asking AI for help with pictures

Two buttons in the picture window use the AI you chose in Choose Your AI, the same way Ask About an Image
does. QUILL tells you what it sends before it sends anything.

- **Suggest Alternative Text** sends the picture and the text around it, and
  puts the suggestion in the Alternative text field for you to read and
  change. Nothing is saved until you choose OK or Insert. If the AI thinks
  the picture is decorative, QUILL says so instead of inventing words. For a
  chart it may also write a fuller description, and QUILL offers to add it
  as a paragraph after the picture.
- **Describe Image** gives you a longer description, just for you, in a
  window you can read and copy.

If AI is switched off, or you are in Safe Mode, QUILL says so and sends
nothing.

## The Media Library

**Tools > WordPress > Media Library...** (the WordPress key, then M) opens
the Workbench at your site's **Media**. Chapter 2 explains how the Workbench
moves. Each row is one file, with its title, its type, its alternative text
and when it was uploaded, newest first. Type in the filter box and press
Enter to search the library.

Under Media are smaller lists: **Pictures**, **Audio**, **Video**,
**Documents**, **Unattached** (files no page claims), **Without Alt Text**,
and **Housekeeping**, described at the end of this chapter.

On a file:

- **Enter**, or **View or Play**, opens the file in your browser.
- **Properties** (`Alt+Enter`) changes its title, alternative text, caption
  and description on the site. Select several files to change them all at
  once.
- **Edit > Copy Link** (`Ctrl+Shift+C`) puts its address on the clipboard.

The rest are on the context menu (the Applications key, or Shift+F10):

- **Insert into the Document** puts it at the caret of your page.
- **Replace File...** puts a new file in its place. The next section shows
  how.
- **Edit Picture...** turns, flips or crops a picture, to a shape or by
  numbers in percent, after a preview that says the result in words.
  WordPress keeps the original and makes the edit a new picture.
- **Regenerate Sizes** remakes a picture's smaller copies, so the theme shows
  it right everywhere.
- **Attach to a Post or Page...** finds a post or page by words or number and
  makes it the file's parent, which some galleries and themes use. **Detach**
  takes it off again. Ctrl+Z undoes either.
- **Download...** saves the file on this computer, where you choose.
- **Copy to Site...** copies it to another of your sites.
- **Counts by Status** says how many files of each kind the library holds.
- **Open in wp-admin** opens the file's own screen in your browser, for the
  few things only wp-admin does, such as scaling the original.
- **Delete Permanently...** deletes the file from the site.

**Deleting a file cannot be undone.** WordPress has no Trash for media. QUILL
names the file and asks you to confirm, and says it cannot be undone. If a
page still uses it, the picture goes missing from that page. Use
**Download...** first if you want a copy, and By Name > Media Usage (Chapter
9) to see where a file is used.

## Replacing a file

You have a new menu PDF, or a better photo, and pages already use the old
one. Replace File puts the new file in the old one's place, so you do not
have to find every page yourself.

1. In the Workbench, go to **Media** and arrow to the file you are
   replacing.
2. Press the Applications key and choose **Replace File...**.
3. Choose the new file on your computer. It can be up to 64 MB, of any type
   the Media Library takes.

QUILL then asks the site what it can do. What happens next depends on the
answer.

### When the site can replace a file in place

Some media plugins let a file be swapped over the REST API. When your site
has one, the file keeps its address, and every page that uses it simply
shows the new one.

The preview says what is there now and what is coming, such as the old and
new file's name, size and type, and that the address stays the same. It also
says that QUILL cannot put the old file back. Press **Replace File**.

QUILL then reads the file back from the site. You hear "Replaced. The address
is the same", with the address. For a picture, its sizes are remade too. If
the site gave the file a new address after all, QUILL says so, and warns that
links to the old address may break.

### When it cannot

WordPress itself has no way to swap a file in place. On most sites QUILL
offers a choice, under **How**:

- **Upload it as a new file and point every use at it (the address
  changes).** This works on every site.
- **Open Enable Media Replace in wp-admin (the address stays the same).**
  This is offered only when the Enable Media Replace plugin is active on the
  site.

**Opening Enable Media Replace.** QUILL opens the file's edit screen in your
browser, where the plugin's Replace Media box is. You need to be signed in to
wp-admin there. Replace the file in the browser, then come back and press F5.

**Uploading and pointing every use at it.**

1. QUILL finds every post, page, synced pattern, featured image and custom
   field that uses the old file.
2. The preview lists the old and new file, and then every item that will be
   changed. It also names anything it found but cannot change, such as a
   field that holds the file's number instead of its address. Press
   **Upload and Repoint**.
3. QUILL asks about **The Old File**:
   - **Keep the old file in the library**, the safe choice;
   - **Delete the old file permanently once every use is moved (cannot be
     undone)**. It is deleted only if every use really was moved.
4. If your site has the Redirection plugin, QUILL asks whether to **Add a
   Redirect** from the old address to the new one. Say yes if other websites,
   emails or search engines link to the old file. Without a redirect, those
   links stop working.

At the end you hear one sentence, such as "The file's address changes; QUILL
updated 4 places that used it. A redirect now sends the old address to the
new one. The old file is still in the library."

Changed your mind? Ctrl+Z points every item back at the old file. The new
file stays in the library, and you can delete it if you like.

## Listening and watching

**View > Play Media Here** plays the sound or video block the caret is in,
inside a page. It opens a small player and starts at once. It streams the
file from your site and saves nothing on your computer.

- The keys are the same as QUILL's own player and Quill Media Player: Play
  and Pause, Stop, Rewind, Forward, Where Am I, Speed, Volume and Mute.
- **Go to Position...** jumps to a time you type, such as `0:01:30`.
- **Captions** speaks the caption on screen at the moment, when the video
  has a captions file on your site.
- **Open in Quill Media Player** hands the file over, for bookmarks and
  resume. Playback here pauses.
- **Open in Browser** opens the file's address in your browser.
- **Close**, or Escape, stops playback and closes the window.

Video shows its picture where the playback engine can. If it cannot, the
window says so once and points you to Open in Browser.

In the Workbench, Enter on a sound or video file opens it in your browser.

## Uploading

These are in **Tools > WordPress > More Media**:

- **Upload Files...** sends one or many files at once. For each one QUILL
  asks for a title and caption, and, for a picture, its alternative text
  first. Cancel skips that file and the rest carry on. If the same file is
  already on the site, QUILL asks whether to use the one already there. You
  hear how far along it is, such as "Uploading 2 of 5", and at the end what
  was uploaded and what was not, and why.
- **Upload from Web Address...** fetches a picture, sound, video or document
  from an address starting https, then uploads it to your site. It will not
  fetch an ordinary web page, an address that is not secure, or a file over
  64 MB.
- **Paste Image** takes a picture you have copied, asks for its alternative
  text, uploads it and puts it at the caret.
- **Upload a Large File...** is for a long recording or a video. Before it
  starts, it tells you how big the file is and how much room the site
  already uses, and that it can take a while. Then it asks for the file's
  title, caption and description, and, for a picture, its alternative text.
  If your host refuses a file that big, you hear the site's own reason. An
  upload that is cut off starts again from the beginning next time, because
  WordPress cannot take a file in pieces.

## Making a picture smaller, and changing how big it shows

A photograph straight from a phone can be several megabytes, which is slow
for visitors on a phone connection. Two commands help, and they do
different things:

- **Tools > WordPress > More Media > Make a Smaller Copy...** makes a new,
  smaller file. Choose the largest width and a format: JPEG for
  photographs, WebP for smaller still, PNG for sharp edges such as a logo.
  The copy is made on your computer, QUILL tells you the size before and
  after, and only then asks whether to upload it as a new file. Your
  original stays in the library.
- **Format > WordPress > Image Size...** changes how wide a picture in your
  page shows, without touching the file. Put the caret on the picture and
  choose from the sizes WordPress made of it. Nothing is cropped. Next time,
  **Back to Earlier Size** is at the top of the list, even after you have
  saved and closed the page.

## Editing a picture on the site

**Tools > WordPress > More Media > Edit a Picture on the Site...** turns,
flips or crops a picture (square, 4 by 3, or 16 by 9), where your site
offers it. The result is a new item in the library, so the original is
kept. With AI on, QUILL describes the new picture for you.

**Tools > WordPress > More Media > Regenerate Sizes...** remakes a
picture's smaller copies after an edit, so the theme shows the change
everywhere. After an edit, QUILL offers to do it for you.

In the Workbench, **Edit Picture...** and **Regenerate Sizes** on a file's
context menu do the same jobs, as the Media Library section above says.

## Alternative text for a whole page, or the whole site

- **Tools > WordPress > Alt Text Review...** lists every picture in the page
  you have open, with its alternative text. It points out the ones with
  none, the ones that are just a file name, the very long ones and the ones
  that start "image of". You can edit each one, mark it decorative, ask your
  AI for a suggestion, or go straight to it.
- **Tools > WordPress > Alt Text for the Whole Library...** steps through
  every picture on the site that has no alternative text, with Suggest, and
  saves your answers in batches.
- In the Workbench, **Media > Without Alt Text** lists the same pictures for
  one site, and **Needs My Attention > Accessibility** lists them for every
  site. Alt+Enter on one opens its alternative text and caption.

## Making a picture with AI

**Insert > Make a Picture...** opens the Picture Maker, the same one QUILL
Studio uses.

1. Describe the picture you want: the subject, the style, the colours, and
   anything to avoid. Not sure? **Suggest from Page Content** reads the
   page, or just your selection, and fills in a description for you to
   change.
2. Choose a shape: wide, square or tall.
3. Choose a background: Normal, Solid colour, or Transparent when your
   provider can make one.
4. Press **Make the picture**. QUILL names the provider and model, and asks
   first.

The picture is saved on your computer only, and a description of what was
actually drawn opens straight away, so you know what you got. Every version
is kept. To change one, type only the change, such as "make the sky
darker", and press **Make the change**.

**Insert into Document** opens the usual picture window, and the picture is
uploaded to your Media Library when you press Insert.

A made picture is an illustration, never a screenshot. If you ask for an
app's screen or a dialog, QUILL says so once.

## The site logo and icon

**Tools > WordPress > More Media > Site Logo...** shows your site's logo and
its small site icon: the file, its real size and its alternative text.
Replace either one from the library, from a file, or from the Picture Maker.
QUILL names the site and the new picture and asks before it changes
anything. The old image stays in your Media Library, and **Restore Earlier**
puts back anything QUILL replaced. Changing the logo needs the
Administrator role.

## Hearing what a sighted visitor sees

**Tools > WordPress > Visual Review...** tells you what a sighted visitor
sees on a published page.

1. QUILL opens the public page in Microsoft Edge, or Chrome if Edge is
   missing, hidden in the background, at a desktop width and at a phone
   width.
2. It measures every picture: its size, whether it spills out of the page,
   whether it loaded, and its alternative text.
3. It tells you what it would send to your AI, and sends it only if you say
   yes.

The report starts with anything you should know, such as unpublished
changes not being in it, then the review, then the measurements. Each
finding is labelled as likely a problem, a design choice, or worth checking.
QUILL never downloads a browser.

**Tools > WordPress > More Media > Preview and Review...** does the same
with a change you have not made yet. Choose a picture on the page, or the
site logo, and type a width. QUILL shows that width in its captured copy
only, so nothing on your site changes.

Both work on published pages. A draft can only be opened by someone signed
in to WordPress in a browser, so QUILL explains that instead.

## Captions, transcripts and listening versions

These are in **Tools > WordPress > More Media**. The heavy work happens on
this computer, and nothing reaches your site until you have reviewed it.

**Captions for Video...**

1. Choose a video from the site's Media Library.
2. QUILL makes captions on this computer, with the same transcription it
   uses everywhere else, so the video is never sent anywhere to be
   transcribed.
3. Review Captions opens. Each caption is one line: its time, then its
   words. Correct anything misheard, change "Speaker 1" to a name, and add
   sounds such as [applause].
4. Choose OK. QUILL uploads the captions and connects them to the video in
   your page, so the player's CC button works. If the video is not in the
   page yet, QUILL puts it at the caret with its captions.

**Transcript for Audio...** does the same for a sound file. After you review
the transcript, choose whether it goes under the player folded away as
"Read the transcript", or in full.

**Make a Listening Version...** reads your page aloud with your Read Aloud
voice, saves it as an MP3, uploads it, and puts a player at the top
labelled, for example, "Listen to this post (6 minutes)". Run it again after
you change the page: QUILL tells you the recording is out of date and offers
to make it again, and the new recording replaces the old one.

**Name Embeds** asks your site what every embedded YouTube, Vimeo or podcast
link in the page is, and gives each one without a caption its title, so
nobody meets an unnamed frame. A report says what each one turned out to
be.

**Publish a Document as a Page...** Choose a PDF or Word file. QUILL
converts it on this computer, uploads the original to the Media Library, and
opens the text as a new page draft with a link to the original at the top.
Many people find a page easier to read than a PDF. A scanned PDF is only
read with OCR after you say yes.

Your page changes go to the site only with your next Save Draft to Site or
Publish.

## Tidying the library

**Media > Housekeeping**, in the Workbench, finds files that are not used
anywhere, files uploaded twice, very large files, and sound or video with no
captions or transcript.

1. Arrow to a finding and read it.
2. Choose **Show Where It Is Used** on its context menu. It lists every page
   that uses or links to the file. A file you thought was unused sometimes
   turns out to be the logo.
3. To tidy it away, choose **Move to Trash...**, which shows you where it is
   used again before it asks.

Nothing is deleted for good from Housekeeping. Most sites keep no Trash for
media, and then QUILL says so and leaves the file alone. Delete Permanently
on the file's row in Media does that, after you confirm.

## Posting from QUILL's other apps

Three other apps in the family can send things to your site, through the
same WordPress code and the same saved sites:

- **QUILL Cast** can post an episode you have downloaded, with its player,
  show notes, chapters and transcript: **Episode > Post This Episode to
  WordPress...**.
- **QUILL Studio** can post a finished recording the same way, from its
  **WordPress** menu: **Post an Episode to WordPress...**.
- **Quill Converter** can upload the files it made straight to your Media
  Library: **File > Upload to WordPress...**.

Cast and Studio write a local WordPress draft and open QUILL with it, so you
can read it over before sending. If QUILL cannot start, the draft waits for
you, in QUILL and in QUILL Lite, under **File > WordPress > Open Local
Draft...**.

## Where to next

- Previous: [Chapter 4: Blocks made plain](wordpress-forms-04-blocks.html)
- Next: [Chapter 6: Comments, categories, tags, people and menus](wordpress-forms-06-comments-people-and-menus.html)
- [Contents](wordpress-forms-guide.html)
