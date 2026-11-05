# Chapter 4: Pictures and the Media Library

## What this chapter covers

This chapter covers everything to do with pictures, sound and video:
putting a picture in a page with good alternative text, the Media Library
window, listening to and watching your site's files without downloading
them, uploading, making a picture smaller, changing how big it shows,
editing it on the site, making a new picture with AI, the site logo, and
hearing what a sighted visitor sees. It ends with captions, transcripts,
listening versions of your pages, and posting from QUILL's other apps.

## Putting a picture in a page

There are two ways in, both in the Insert menu:

- **Insert > Picture from the Media Library...** puts in something already
  on your site.
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
  flourish, check Decorative rather than writing something.
- For a chart or a diagram, keep the alternative text short and put the
  detail in a paragraph after the picture.

## Asking AI for help with pictures

Two buttons in the picture window, and the same two in the Media Library,
use the AI you chose in Choose Your AI, the same way Ask About an Image
does. QUILL tells you what it sends before it sends anything.

- **Suggest Alternative Text** sends the picture and the text around it, and
  puts the suggestion in the Alternative text field for you to read and
  change. Nothing is saved until you choose OK or Insert. If the AI thinks
  the picture is decorative, QUILL says so instead of inventing words. For a
  chart it may also write a fuller description, and QUILL offers to add it
  as a paragraph after the picture.
- **Describe Image** gives you a longer description, for you rather than for
  visitors, in a window you can read and copy.

If AI is switched off, or you are in Safe Mode, QUILL says so and sends
nothing.

## The Media Library window

**Tools > WordPress > Media Library...** lists every file on your site,
newest first. Each row gives the title, the type, the size, the alternative
text and when it was uploaded. Type in **Find** and press Enter to narrow
the list by title, file name or alternative text.

The details under the list say more about the file you are on, including
where it is used. On a site with 500 files or fewer, QUILL works this out
while the window is open and tells you when it is ready. On a bigger site,
press **Used In** to search for the one you are on.

The buttons:

- **Insert...** puts the file at the caret. A picture opens the picture
  window first.
- **Play...** plays a sound or video file (see the next section).
- **Used In** says which pages and posts link to the file.
- **Attach to This Page or Post** makes the open page the file's parent on
  the site, which some galleries and themes use.
- **Set as Featured Image** makes the picture the open page's featured
  image.
- **Suggest Alternative Text...** and **Describe Image...**, as above.
- **Edit Alternative Text...** changes the library's own alternative text
  on the site. You hear "Alternative text saved on Community Radio."
- **Copy Address** puts the file's web address on the clipboard.
- **Remove from Library...** deletes the file from the site.

**Enter** on a row plays a sound or video file and inserts anything else.

**Removing a file is the one thing that cannot be undone on the site.**
WordPress has no Trash for media. So before removing a file, QUILL tells you
how many pages use it, and saves a copy in your Documents folder, under
"Removed from WordPress". You hear where the copy went.

## Listening and watching

**Play** in the Media Library opens a small player and starts the file at
once. It streams the file from your site and saves nothing on your computer.

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

Play on a picture says "That file is not audio or video."

**View > Play Media Here** does the same for the sound or video block the
caret is in, inside a page.

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
- **Upload a Large File...** sends a long recording or video up in pieces,
  so a slow connection or a strict host does not lose the whole upload. You
  hear how far it has got.

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
everywhere.

## Alternative text for a whole page, or the whole site

- **Tools > WordPress > Alt Text Review...** lists every picture in the page
  you have open, with its alternative text. It points out the ones with
  none, the ones that are just a file name, the very long ones and the ones
  that start "image of". You can edit each one, mark it decorative, ask your
  AI for a suggestion, or go straight to it.
- **Tools > WordPress > Alt Text for the Whole Library...** steps through
  every picture on the site that has no alternative text, with Suggest, and
  saves your answers in batches.

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

- Previous: [Chapter 3: Blocks made plain](wordpress-forms-03-blocks.html)
- Next: [Chapter 5: Comments, categories, tags and menus](wordpress-forms-05-comments-categories-menus.html)
- [Contents](wordpress-forms-guide.html)
