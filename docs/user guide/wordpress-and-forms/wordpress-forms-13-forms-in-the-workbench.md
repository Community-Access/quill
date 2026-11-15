# Chapter 13: Forms in the Workbench, and Gravity Forms

## What this chapter covers

Once a form is live, the work moves to the site: reading responses, keeping
spam out, changing a form's settings, and sometimes building forms in a
plugin other than QUILL Accessible Forms. The Workbench does all of that, for
QUILL Accessible Forms and for Gravity Forms.

In this chapter you will look after your forms and their responses in the
Workbench, tune QUILL Accessible Forms' spam checks, and build and change a
Gravity Forms form in QUILL. Then you will work with Gravity Forms' feeds,
results, notes and test entries, and copy a form from one plugin to the other.

By the end you can run every form on your site without opening wp-admin.

## Where forms live in the Workbench

Each site's **Forms** lists its forms, from every form plugin QUILL reads.
Under it:

- **Responses**: what people sent;
- **Held as Spam**: responses the site doubted;
- **Feeds** and **Results**, on a site with Gravity Forms.

**Needs My Attention > Form Responses** gathers new responses from every
site, and **Needs My Attention > Held as Spam** the doubtful ones, beside the
doubtful comments.

On a form, Enter, or **Show Its Responses**, lists its responses.

## QUILL Accessible Forms

### Looking after a form

On a QUILL Accessible Forms form:

- **Change Form Status...** makes it open and taking responses, closed
  (shown but not taking responses), or a draft that visitors do not see.
- **Form Settings...** reads the form's settings, such as its button text,
  checks, scheduling and entry limits, and changes one at a time, after a
  preview.
- **Saved Views** lists the views saved for its responses.
- **Search Responses on the Site...** finds responses by words, searched on
  the site.
- **Copy as a Gravity Form...** makes the same form in Gravity Forms, if the
  site has it. The preview names anything that cannot carry over.
- **Copy to Site...** copies it to another of your sites.
- **Delete Form...** first says how many responses it has, then asks you to
  type the form's name.

### Responses

On a response:

- **Read in Full**, or Enter, reads every answer in the details pane.
- **Item > Star or Unstar Entry** (`Ctrl+Alt+F`) stars it to come back to.
- **Item > Mark Entry Read or Unread** (`Ctrl+Alt+U`) marks it.
- **Spam** (`Ctrl+Shift+S`) and **Not Spam** (`Ctrl+Shift+A`) move it out of
  or into the responses. They go through QUILL Accessible Forms' own spam
  checks, so the site learns from them, and a held response's emails are sent
  once you release it. A held response's row gives the plugin's reason for
  holding it.

Several at once works too, with how each one went.

### Keeping spam out

QUILL Accessible Forms has spam checks of its own. You change them in the
Workbench.

1. Select the site, or anything on it.
2. Choose **Site > Site Properties...** (`Alt+Shift+Enter`) and go to the
   **Spam** page.
3. Change what you need:
   - each spam check, checked or unchecked;
   - the limits and thresholds, as whole numbers;
   - **Use WordPress's disallowed words** and **Use WordPress's moderation
     words**, which hold a form whose answers contain a word from those lists
     in Settings, Discussion;
   - **Ask a question**: when a visitor is asked a question before the form is
     sent, and which kinds of question;
   - the Send Anyway setting. Whoever takes Send Anyway is never turned away:
     their form is held for you to look at;
   - **New OOPSpam key**: type a new key to replace the saved one, or leave it
     empty to keep it. The box is hidden as you type. QUILL never shows,
     speaks or keeps the saved key, and only says whether one is saved.
     **Remove the saved OOPSpam key** takes it away when you save.
4. Press OK. QUILL reads the settings again first, sends only what you
   changed, then reads them back and says what the site now holds.

The page also shows this week's numbers. You need the site's Manage Options
capability, or the plugin's own Manage Settings. A site still running the
plugin under its old name, BITS Accessible Forms, shows its settings here to
read, and they are changed in wp-admin until the plugin is updated.

**Your own questions.** **Form Spam Questions...**, on the site's context
menu, lists the questions of the site's own that the plugin asks. Add one, or
change or remove one, after a preview.

**Week by week.** **Form Spam by Week**, on the same menu, lists each week,
newest first: the questions asked, answered, answered wrongly, and let
through with Send Anyway. The Watch for form spam questions says each new
week's numbers without being asked (Chapter 8).

## Gravity Forms

Gravity Forms is a paid plugin many sites already use. On a site that has it,
with its REST API turned on, the Workbench lists its forms and responses
beside everything else, and you can build its forms in QUILL.

The Gravity Forms commands without a key of their own are also in **Item >
Gravity Forms**.

### Building a form

1. In the Workbench, go to the site's **Forms**.
2. Press Ctrl+N, or choose **New Gravity Form...** on the context menu. To
   change a form that is there already, choose **Edit Form...** on it.
3. The form window opens. Fill in the **Title**, **Description**, **Button
   text** and **Label placement**. Top aligned reads best on a phone and
   zoomed in.
4. **Confirmation message** is what people read after sending the form.
   **Notification to** and **Notification subject** are for the email the
   site's administrator gets. If the form sends people to a page instead, or
   routes its email by an answer, those boxes are dimmed, and Gravity Forms
   keeps them as they are.
5. Tab to **Fields**, the questions in order. Insert, or **Add Field...**,
   adds one after the one you are on. Enter, or **Edit Field...**, changes
   one. **Move Up** and **Move Down** move it. Delete, or **Remove Field**,
   takes it out.
6. Press **Review and Save...**.

**A field** has a **Type**, such as text, paragraph, email, phone, number,
drop-down, radio buttons, check boxes, date, time, website, name, address,
consent, HTML, section or page break. Then its **Label**, **Description**,
whether it is **Required**, a **Placeholder**, a **Default value**, an
**Admin label** for the entries list, and a **CSS class**. For a question
with choices, **Choices** takes one choice a line. To store a different
value, write the text, a space, an equals sign, a space, then the value.
Start a line with an asterisk to have that choice chosen at first.

**Condition...** sets when the field shows: show or hide it **When** an
earlier **Field** is, or is not, a **Value**.

**Checks before saving.** Before anything is sent, QUILL checks the form, the
same way it checks its own forms. It finds questions with no label, or only a
placeholder, a required mark that is only an asterisk, empty choices, page
breaks and sections that leave a page empty, two questions that sound alike,
and conditions that name a missing or later field. Cancel takes you back to
the form window, at the first one.

**Saving.** The preview lists every change. When you change a form, QUILL
reads it again first, and if somebody changed it on the site meanwhile,
nothing is sent. After saving it reads the form back and tells you of any
difference. Ctrl+Z puts the previous form back. A new form goes to Gravity
Forms' Trash instead.

Responses are never read or changed by any of this, and every preview says
so.

Fields QUILL does not edit, and conditions with more than one rule, are kept
exactly as they were.

### Changing one field's type

**Change a Field Type...**, on a Gravity Forms form, turns one common field
into another: text, paragraph, email, number, drop-down, radio buttons and
check boxes. QUILL reads the whole form, previews the change, checks nobody
changed the form meanwhile, sends it, and reads it back to make sure only that
field changed. Address and list fields are never offered. It needs Full
Workbench access, and Gravity Forms' permission to make forms, which an
administrator has.

### Responses

On a Gravity Forms response:

- **Item > Entry Notes...** (`Ctrl+Alt+N`) reads the entry's notes, and adds
  one.
- **Item > Star or Unstar Entry** (`Ctrl+Alt+F`) and **Item > Mark Entry Read
  or Unread** (`Ctrl+Alt+U`) do what they say, and Ctrl+Z undoes them.
- **Item > Resend Notifications...** (`Ctrl+Alt+I`) works out who each of the
  entry's emails goes to, lets you choose which to send, previews the
  recipients, then sends.
- **Spam** and **Not Spam** work as for any response.

The response's Properties has **Answers** and **Notes** pages to read, and
saves Starred and Read.

**Filtering responses.** On Responses, the **Filter Builder**
(`Ctrl+Shift+F`) offers the chosen form's own fields, and the values each
allows. The filter is sent to the site, so it searches every response, not
only the ones loaded. With a second condition, it asks whether a response must
match all of them, or any. The status bar says the site's own count, such as
"12 of the 40 responses that match are shown".

### Feeds and results

- **Feeds** lists every form's add-on feeds, such as Mailchimp, Stripe or
  Zapier, with the form, the add-on and whether each is on. **Activate or
  Deactivate...** and **Rename...** preview first. **Delete Permanently...**
  previews too, and Ctrl+Z makes the feed again. On a form, **Show Its
  Feeds** lists only that form's.
- **Results** shows quiz, poll and survey results: a row for each answer with
  its count and share, and each question as one sentence. On a form, **Show
  Its Results** opens it.

### Trying a form

**Test This Form...**, on a form, lets you fill in test values. The site
checks them first, and names any field it refuses. If the site is live, the
preview says so, and that a practice site would be better. Ctrl+Z moves the
test entry to the Trash.

### Moving forms

- **Copy to Site...** (`Ctrl+Shift+Y`) copies the whole form to another of your
  sites, as a new form, or replacing one with the same title. Responses are
  never read or sent.
- **Copy as a QUILL Accessible Form...** makes the same form in QUILL
  Accessible Forms. **Copy as a Gravity Form...**, on a QUILL Accessible Forms
  form, does the reverse. Each preview names what cannot carry over, such as
  CSS classes, admin labels, conditions with several rules, and kinds of field
  the other plugin lacks.
- **Copy Old Entries into QAF...**, on a Gravity Forms form, brings that
  form's entries across too, once you have made its QUILL Accessible Forms
  copy. Choose the QUILL Accessible Forms form they go into, usually the one
  with the same title. The preview lists each entry with its date and how
  many answers it carries, and names what stays behind: uploaded files,
  payment details, and any field the new form has no question for. Only
  active entries are copied; spam and trashed ones stay in Gravity Forms, and
  the Gravity Forms entries themselves are never changed. Ctrl+Z moves the
  copies to QUILL Accessible Forms' Trash.

  The plugin on your site has to be able to take entries for this to work.
  If yours cannot yet, QUILL tells you so in one sentence and nothing is
  made; update QUILL Accessible Forms and try again.

## Where to next

- Previous: [Chapter 12: Forms on your site, on the web and on paper](wordpress-forms-12-forms-on-the-web-and-paper.html)
- Next: [Chapter 14: QUILL Lite](wordpress-forms-14-quill-lite.html)
- [Contents](wordpress-forms-guide.html)
