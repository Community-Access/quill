# Chapter 9: Forms on your site, on the web and on paper

## What this chapter covers

A form you have written and checked can go four ways: onto your WordPress
site through the QUILL Accessible Forms plugin, onto any website as a page
of its own, onto paper in ordinary or large print, and into braille. This
chapter covers each one, then reading the responses people send, bringing
forms in from other form builders, and the optional AI help for forms. It
ends with what is kept private and what Safe Mode turns off.

## QUILL Accessible Forms

WordPress has no forms of its own. Something on the site has to show the
form to visitors, check and store their answers, send the emails and keep
spam out, and QUILL runs on your computer, so it cannot do that for your
visitors. That job belongs to a plugin: **QUILL Accessible Forms**, made by
the same people as QUILL, free and MIT-licensed. It used to be called BITS
Accessible Forms.

The plugin reads the same form language QUILL writes, so a form you publish
from QUILL is exactly the form you checked and filled in yourself. It also
has its own accessible builder screens, if someone on your team prefers to
work in the dashboard.

To use it, install QUILL Accessible Forms on your site in the usual way, or
ask your site's administrator to. Site Check (Chapter 7) names it when it is
there. A site that still runs it under its old name, BITS Accessible Forms,
works too.

Forms are published only to QUILL Accessible Forms. If your site does not
have it, Save As Web Page, below, still puts your form on the web.

## Publishing a form

1. Open the form, and check it with **Tools > Forms > Check This Form...**.
   Publish will not send a form QUILL cannot read properly, such as one with
   a rule that makes no sense: it says, for example, "Publish Form stopped:
   this form has 2 problems to fix first." Check This Form lists them.
2. Choose **Tools > Forms > Publish Form...**.
3. If you have more than one site, choose the site that has QUILL Accessible
   Forms.
4. The first time, QUILL asks **Publish as**: **Live**, so people can fill
   it in wherever it is placed, or a **draft**, which waits until you make it
   live, here or in the plugin.
5. QUILL asks you to confirm, naming the form and the site.

You hear, for example, "Published Ask us anything on Community Radio, form
12, live. Insert Form Into Page puts it on a page."

**Publishing again** updates the same form on the site; the question then
says Update. If someone changed the form on the site since you last
published, QUILL says so before it replaces it, and keeps the site's copy on
your computer first. It keeps the last ten copies of each form.

If the site does not have the plugin, you hear, for example, "Publish Form
needs QUILL Accessible Forms on Community Radio, and the site does not offer
it."

## Putting the form on a page

A published form shows wherever you place it.

1. Open the page from **File > WordPress > Open Page or Post...**.
2. Put the cursor where the form goes.
3. Choose **Tools > Forms > Insert Form Into Page...**.
4. QUILL lists the site's forms, each with how many responses it has had.
   The one you published last from this computer is selected. Press Enter.

QUILL inserts the plugin's form block in an HTML page, or its shortcode in a
Markdown page. You hear "Inserted the Ask us anything form", and that it
shows on the page once the page is sent. Then Save Draft to Site or Publish
the page as usual.

## Test on Site

**Tools > Forms > Test on Site** opens the page that shows your form, in
your web browser, so you can fill it in there with your screen reader, the
way a visitor will. You hear "Opened Contact on Community Radio, where the
form is." If no page shows the form yet, QUILL opens the form in QUILL
Accessible Forms on the site instead, and reminds you that Insert Form Into
Page puts it on a page.

## Reading the responses

**Tools > Forms > Responses...** lists what people sent, newest first, such
as "Response 41, 3 November, 2:10 PM, Jane Smith, Event registration". With
a published form open, it goes straight to that form's responses. Otherwise
QUILL asks which site, then which form, each with how many responses it has
had.

The buttons:

- **Read**, or Enter: one response, a question and its answer on each line,
  in a window you can read and copy.
- **View...:** the list; or grouped under a heading for each day; or grouped
  for each place the responses gave.
- **Find...:** shows only responses containing some words. Leave it empty to
  show every response again.
- **Mark:** marks or unmarks the response you are on, to delete several.
- **Export to CSV...:** saves the responses shown as a CSV file, where you
  choose.
- **Open as Table...:** does the same and opens the file afterwards, as a
  table you can walk cell by cell.
- **Export to Word...:** saves the response you are on, or all of those
  shown, as a Word document.
- **Summarise...:** asks your AI for a summary (see below).
- **Delete...:** deletes the marked responses, or the one you are on, after
  telling you how many. They go to the Trash in QUILL Accessible Forms, not
  away for good.
- **Say New Count:** turns on or off the spoken count of new responses.

**The new response count.** The first time you use a site in a session,
QUILL says how many new responses each form has, for example "Community
Radio: 4 new responses to Event registration." The plugin has no "unread"
mark, so "new" means new since you last opened Responses in QUILL.

**Responses are people's personal details.** QUILL reads them only while
the Responses window is open, keeps them in memory, never writes them to a
log, and saves them only where you choose.

## Save As Web Page

**Tools > Forms > Save As Web Page...** makes a web page of its own with the
form in it, every question properly labelled, to upload anywhere. QUILL asks
**Send answers to**: the https web address the form should send its answers
to, such as a form service your organisation already uses. Leave it empty
for a form to print or read, which sends nothing.

This is the way to put a form on a site without QUILL Accessible Forms. Such
a form has no Responses window in QUILL; its answers go wherever you sent
them.

## Paper, large print and braille

Every form can be saved three more ways, without a site, even in Safe Mode:

- **Save As Word Document...:** a printable form. Each question is a
  heading, with lines to write on and boxes to check.
- **Save As Large Print...:** the same Word form at 18 point and up. You
  hear, for example, "Saved Ask us anything large print.docx, a large-print
  Word document, 18 point and up, with 5 questions, lines to write on and
  boxes to check."
- **Save As Braille-Ready Text...:** one question per block, choices
  lettered a, b, c, 40 cells to a line. QUILL asks **Save as**: text you can
  emboss or read on a display as it is, or, with the braille pack installed,
  a BRF file translated to UEB contracted braille by QUILL's own braille
  translator.

All of these come from the same form, so the paper version always asks what
the web version asks. Change the form, save again, and they all agree.

## Bringing forms in from other builders

Forms made in other WordPress form plugins are brought in on the site, by
QUILL Accessible Forms' own Import and Export screen, which reads forms from
Gravity Forms, WPForms, Contact Form 7, Ninja Forms and Google Forms, and
lists anything it could not bring across in an import report rather than
dropping it silently. The same screen can export a form back to those
builders.

QUILL does not publish to those other plugins, only to QUILL Accessible
Forms.

## AI help with forms

If you have chosen an AI in Choose Your AI, four commands can help. Each one
tells you what it sends before it sends it, and nothing changes until you
have read the proposal and said yes. Undo takes it all out in one step.

- **Tools > Forms > Draft a Form...:** describe the form in a sentence or
  two, such as who fills it in and what you need to know. Only that
  description is sent. The AI writes it as a form, which you read in full,
  and QUILL then asks whether to use it: in place of the form in front, or
  saved as a new form.
- **Tools > Forms > Plain Language...:** sends your questions' labels and
  help text, never anybody's answers. You get simpler wording, each beside
  what is there now, to accept or decline as one step.
- **Tools > Forms > Suggest Autofill Hints...:** for questions such as name,
  email, phone and address that have no autofill hint, and for questions
  with a format rule but no help. It sends their labels and kinds only.
- **Summarise...**, a button in Responses: this sends people's answers, so
  QUILL asks every time. It says how many responses would go, and that they
  may include names and email addresses. The summary opens in a window to
  read; check it against the responses before you rely on it.

## Privacy and Safe Mode

- Payment details and website passwords never pass through QUILL. Payment
  fields, CAPTCHA keys and the like stay on your website.
- Nothing is sent without a deliberate Publish Form, Insert Form Into Page,
  Test on Site, Responses or AI command.
- In Safe Mode, Publish Form, Insert Form Into Page, Test on Site, Responses
  and the four AI commands each say they are off: "Publish Form is off in
  Safe Mode, because it would reach your site or an AI." Writing, checking,
  Fill It In Yourself and the four Save As commands still work.

## A walk-through: from your computer to your site

1. Check the form, then **Tools > Forms > Publish Form...**. Choose Live.
   Confirm. You hear the form's number on the site.
2. **File > WordPress > Open Page or Post...**, and open your Contact page.
3. Put the cursor after the first paragraph, and **Tools > Forms > Insert
   Form Into Page...**. Choose the form.
4. **File > WordPress > Publish or Update...**.
5. Open the form again, and **Tools > Forms > Test on Site**. Fill it in once
   in your browser.
6. **Tools > Forms > Responses...**. Your test response is at the top. Read
   it, then Mark it and Delete it.

## Where to next

- Previous: [Chapter 8: Writing a form](wordpress-forms-08-writing-forms.html)
- Next: [Chapter 10: QUILL Lite](wordpress-forms-10-quill-lite.html)
- [Contents](wordpress-forms-guide.html)
