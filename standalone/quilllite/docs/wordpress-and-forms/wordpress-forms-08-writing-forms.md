# Chapter 8: Writing a form

## What this chapter covers

This chapter is about making a form: a contact form, an event sign-up, a
membership renewal, a survey or a feedback page. It explains why QUILL
writes forms as text, what the QAF form language looks like, how to start a
form from a template, add questions, rearrange them, write rules that show
and hide questions, set the form's properties, check it for problems, and
fill it in yourself with your screen reader before anyone else sees it.
Everything in this chapter happens on your own computer, needs no site, and
works in Safe Mode. Chapter 9 covers putting the form on the web and on
paper.

## Why forms are text here

Making a form usually means dragging boxes around a web page, which is one
of the hardest things on the web to do with a screen reader. But a form is
really structured text: a title, some pages and sections, the questions,
their choices, and a few rules. QUILL is good at text, so that is how you
write one.

You write the form as a short plain text document in the **QAF form
language**, the language of the QUILL Accessible Forms plugin for WordPress.
You check it, and then you fill it in yourself, with your screen reader,
before anyone else sees it. When it is right, you can publish it to your
site, save it as a web page, or print it.

**Turning it on.** Forms is on in every QUILL feature profile except
Essential, and in QUILL Lite's Recommended, Everything and Developer
profiles. If you do not see **File > New Form...**, switch Forms on in
**Profiles and Features...** in QUILL, or check it in **Tools > Customize
Features** in QUILL Lite.

## Where everything is

| Menu | What is there |
|---|---|
| File | New Form, beside the other New commands |
| Insert | Form Field |
| View | Form Outline |
| Format | Form Rules |
| Tools > Forms | Check, Fill It In Yourself, Properties, publishing, saving and AI |

Apart from New Form and Responses, these commands are dimmed unless a form
is open. If you reach one another way, such as from the Command Palette,
QUILL tells you why, for example "Check This Form works in a form document,
a .qaf file. Start one with New Form in the File menu, or open one."

None of the Forms commands has a shortcut key. Every sensible key is already
taken by something you use more often, and you will not write forms every
day. Use the menus, or press Ctrl+Shift+P, type "form", and pick the command
from the list.

## Form files

A form is an ordinary text file whose name ends in `.qaf`. Ctrl+S saves it
like any other document, File > Open opens it, and you can read it in any
text editor. A form saved by an earlier build with the `.bfl` ending still
opens and works the same.

Most commands rewrite only the question they change, and the rest of your
form stays exactly as you wrote it, spacing and all. Moving a question can
rewrite the whole form in the standard layout. Ctrl+Z takes either back.

## Starting a form

1. Choose **File > New Form...**. The New Form window opens on **Title**.
2. Type the form's title, the name your visitors will see.
3. Tab to **Template** and choose one. There are seven, each a few questions
   you can change:
   - **Blank:** one question to start from.
   - **Contact form:** name, email address and a message.
   - **Event registration:** name, email, how many are coming, and access
     arrangements, asked only when needed.
   - **Membership renewal:** contact details, membership level, and how they
     would like the newsletter.
   - **Survey:** a rating, a yes or no, and room to say more.
   - **Accessibility feedback:** where the problem was, what happened, what
     they use, and whether to reply.
   - **Volunteer sign-up:** contact details, the days they can help, and
     what they would like to do.
4. Press **Next**. The ordinary Save As window opens, with a file name made
   from your title. Choose a folder and press Save.

You hear, for example, "Saved Ask us anything.qaf, a contact form with 3
questions." The new form opens straight away, ready to change.

## What a form looks like

Here is the Event registration template, as QUILL writes it:

```
bfl 1
form "Spring fair"

text #name "Your name"
  @required
  @autocomplete "name"
email #email "Email address"
  @required
  @description "We send your confirmation here."
  @autocomplete "email"
number #guests "How many people are coming, including you?"
  @required
  @description "A number from 1 to 10."
  @default 1
  @min 1
  @max 10
radio #access "Do you need any access arrangements?"
  + No
  + Yes
textarea #access_details "Tell us what you need"
  @when #access is "yes"
```

Read it a line at a time:

- **The first line,** `bfl 1`, says which version of the form language this
  is. Leave it alone.
- **`form`** gives the form's title.
- **Each question** starts on a line of its own: the kind of question, its
  id (the word after the `#`), and its label in quotes. The id is the name
  rules use for the question; visitors never see it.
- **The indented lines** under a question are its settings, starting with
  `@`, and its choices, starting with `+`.
- **`@when`** is a rule: Tell us what you need only appears when somebody
  answers Yes.

You never have to type any of this. The commands below write it for you.
But it is ordinary text, so Find, spelling, copy and paste all work on it,
and if you would rather type a question yourself, you can.

## The form language in more detail

### Pages and sections

A long form is easier in pages. A `page` line starts one, optionally with a
title, and everything indented under it belongs to it. A `section` groups
questions under a heading, with its own id and label:

```
page
  section #about "About you"
    text #name "Your name"
      @required
  select #country "Country"
    @library "countries"

page "Your session"
  radio #size "T-shirt size"
    + Small
    + Large
```

### The settings you will use most

- `@required`: the visitor must answer it.
- `@description "..."`: help text, read with the question. Say what is
  expected, such as "A number from 1 to 10".
- `@placeholder "..."`: an example shown inside an empty box. It is never a
  label: a placeholder disappears as soon as someone types.
- `@autocomplete "..."`: an autofill hint, so the visitor's browser can fill
  in their name, email, phone or address. The usual hints are `name`,
  `email`, `tel` and `street-address`.
- `@default ...`: the answer the question starts with.
- `@min` and `@max`: the smallest and largest number. `@minlength` and
  `@maxlength` do the same for the length of text.
- `@library "..."`: take the choices from a ready-made choice library, such
  as `countries`, instead of listing them.
- `@when ...`: show the question only when the condition is true.
- `@calculate ...`: work the answer out from other answers.

### Choices

Each choice is a `+` line. QUILL stores a choice by a value made from its
words, in small letters with hyphens, so "Large print" is stored as
`large-print`. A rule can name either the words or the value, in any
capitals.

### Conditions and calculations

Conditions and calculations use one small expression language. A question
is named by its id with a `#`:

- comparing: `#type is "business"`, `#type is not "business"`,
  `#age > 17`, `#age is at least 18`;
- empty or not: `#phone is empty`, `#consent is filled`;
- words: `#email contains "@"`;
- a list: `#country is one of ["uk", "ie"]`;
- dates: `#date is before today()`, `#date is within 7 days of today()`;
- joining: `and`, `or` and `not`, as in `#age > 17 and #consent is filled`;
- arithmetic, for `@calculate`: `#tickets * 5`, or
  `round(#total * 1.2, 2)`.

QUILL reads every rule back as a sentence, such as "Age is greater than 17
and Consent is filled in", or "Tickets times 5", so you can check it means
what you meant.

## Adding a question

Put the cursor on the question you want the new one to follow, then choose
**Insert > Form Field...**.

1. The Kind of question list opens. Each row says what a visitor meets, such
   as "Choose one: Choose one from a group of buttons". **Section** and
   **Page break** are at the top. Type a word such as "date" in **Search**
   and press Enter to narrow the list, then press Enter on a row.
2. A short window asks only what that kind of question needs:
   - **Label:** the question, as visitors will hear it;
   - **Id (optional):** leave it empty and QUILL makes one from the label;
   - **Required:** check it if visitors must answer;
   - **Help text:** a sentence read with the question, saying what is
     expected;
   - for a question with choices, **Choices, one per line**, or a **Choice
     library**, a ready-made list such as countries or time zones;
   - for a page break, an optional **Page title**.
3. Press Insert. The question goes in after the one your cursor was on, and
   your cursor moves to it. You hear, for example, "Inserted Best way to
   reply, choose one."

A page break starts a new page at your cursor: everything after it moves to
the new page.

### The kinds of question

- **Text:** one line of text, such as a name; several lines, such as a
  message; a number; an email address; a phone number; a web address; an
  amount of money; a password; a hidden value visitors never see.
- **Choosing:** one from a drop-down list; several from a list; one from a
  group of buttons; check as many as apply; one check box to agree to
  something; one on-or-off switch.
- **Scales:** a score out of five; how likely they are to recommend you,
  from 0 to 10; how much they agree with each statement; a grid of the same
  choices for several questions; putting choices in order; a quiz question
  with a right answer.
- **Dates and times:** a date; a time; both; a first and last date.
- **People and places:** a name in parts; a postal address in parts.
- **Other:** a file they send; a signature; a number worked out from other
  answers; a group of questions they can fill in more than once; and text
  shown on the form that is not a question.

Payment fields, and the fields some sites use to make posts or register
users, are left to the site. If a form you open has one, QUILL keeps it
exactly as it is, as a protected line.

## The form outline

**View > Form Outline...** lists every page, section and question in order.
Each row reads like a sentence, for example "Email address, email field,
required, page 1". The list starts with a count, such as "Page 1, 3
questions".

- **Go to It**, or Enter, puts the cursor on that question in the document.
- **Move Up** and **Move Down** move it, as do Alt+Shift+Up and
  Alt+Shift+Down. Moving past the top or bottom of a page takes it on to the
  next page.
- **Move In** puts it into the section just above it, as does
  Alt+Shift+Right. **Move Out** takes it out of its section, as does
  Alt+Shift+Left.
- **Rename...** changes what the question says.
- **Change Id...** changes its id, and every rule that mentions it changes
  too.
- **Change Type...** makes it a different kind of question. Its label, help
  and rules stay.
- **Duplicate** puts a copy straight after it.
- **Remove...** takes it out, after asking you first.

Every change is one step that Ctrl+Z in the document takes back.

## Rules

**Format > Form Rules...** lists every rule in the form as a sentence, such
as "Show Tell us what you need when Do you need any access arrangements? is
Yes." Calculations are there too: "Cost is Tickets times 5."

To add one, press **Add Rule...** and make three choices:

1. **When this question**, and how its answer is compared in **Is**: is, is
   not, is filled in, is empty, contains, is more than, or is less than.
   Type the answer to compare with in **This answer**. You can type the
   choice's words, such as Phone, in any capitals; QUILL matches it to the
   choice.
2. **Then**: show, hide, require, make optional, enable, disable, or skip
   to a page.
3. **To this question or page**: what the rule acts on.

If you know the form language, you can type the whole condition in **Or
write the condition yourself** instead, for example
`#age > 17 and #consent is filled`. QUILL checks that it makes sense before
it writes anything, and tells you what is wrong if it does not.

You hear the new rule as a sentence, such as "Show Phone number when Best
way to reply is Phone.", and an `@when` line appears under the question.

The other buttons: **Edit...** changes a rule's condition (an empty
condition removes it), **Remove...** takes a rule out after asking, and
**Go to It** takes you to the question the rule is on.

## Form Properties

**Tools > Forms > Form Properties...** holds everything about the form that
is not a question:

- **Title:** the form's name;
- **Description:** a sentence or two shown above the questions;
- **Language:** the language the form is written in, as a short code such
  as `en`, `fr` or `pt-BR`;
- **Submit button:** what the send button says;
- **Success message:** what visitors read after sending;
- **Redirect to:** a web address to go to after sending, instead of the
  message;
- **Let visitors save and continue later:** for a long form.

At the bottom, **On the site (read only)** says what the website decides:
whether the CAPTCHA and the spam trap are on, how many email notifications
there are, and the form's number on the site once it is published. You read
these here; you change them on the site. You hear "Form properties saved in
the document." when you press OK.

## Checking a form

**Tools > Forms > Check This Form...** looks for anything that would make
the form hard to fill in, and lists what to fix, most serious first:

- a question with no label, or with only a placeholder for one;
- a group of choices with no question for the group;
- a question marked required only with an asterisk or a word, instead of
  Required;
- a format rule, such as a smallest number, with no help text saying what is
  expected;
- name, email, phone and address questions without an autofill hint, so the
  browser cannot fill them in, for example "Phone number has no autofill
  hint, so the browser cannot fill it in. The hint is tel.";
- a rule that names a question that does not exist, or that can never show
  a required question;
- an empty page, or more than 30 questions on one page;
- the same id used twice;
- a list of more than 15 choices, which would be easier as a choice library.

Anything QUILL could not read is listed first, in the form language's own
words, such as a word it did not expect. Lines that start "On the site
today" are different: they say where the forms plugin on your website
currently reads your form differently from how it is written, so you know
before you publish.

Press Enter or **Go to It** to go to the line. After you fix something,
**Check Again** reads the form afresh. When there is nothing left you hear
"Check This Form found nothing to fix."

## Fill It In Yourself

**Tools > Forms > Fill It In Yourself...** opens your form as a real window,
built from the same text, and you fill it in as a visitor would.

- **Tab** moves from question to question. Each one is an ordinary edit
  box, check box, list or group of radio buttons, so your screen reader says
  its label, its group, and "required" where it is.
- **Rules work as you answer.** When an answer makes a question appear or
  disappear, QUILL tells you, for example "Phone number appears." or "Phone
  number is hidden."
- **Answers that are worked out,** such as a total, update as you type.
- **Next** goes to the next page, but first checks this page: if a required
  question has no answer, QUILL tells you which, and puts you on it. **Back**
  goes back.
- **Language,** at the top, lets you try the form in each language it is
  translated into.
- **Submit** sends nothing. It shows **What Would Be Sent**: "Nothing was
  sent. This is what the form would send:", then each question and its
  answer, anything that still needs an answer, and what the rules worked
  out.
- **Close**, or Escape, leaves without keeping anything.

If a question is hard to understand by ear here, it will be hard for your
visitors too. This is the moment to fix it.

## A walk-through: a contact form with a rule

1. **File > New Form...**, title "Ask us anything", template Contact form,
   Next, Save.
2. Put the cursor on the Your message question. **Insert > Form Field...**,
   search "choose", pick Choose one. Label "Best way to reply", choices
   Email and Phone. Insert.
3. **Insert > Form Field...** again, Phone number, label "Phone number".
   Insert.
4. **Format > Form Rules...**, **Add Rule...**: when Best way to reply, is,
   Phone; then Show; Phone number. You hear "Show Phone number when Best way
   to reply is Phone."
5. **Tools > Forms > Check This Form...** says the phone question has no
   autofill hint. Go to It, and add a line `@autocomplete "tel"` under it.
   Check Again.
6. **Tools > Forms > Fill It In Yourself...**. Tab through. Choose Phone and
   hear "Phone number appears." Submit, and read What Would Be Sent.

The Forms track in **Help > Tutorials** has seven guided lessons that build
this same form.

## Where to next

- Previous: [Chapter 7: Running your site](wordpress-forms-07-running-your-site.html)
- Next: [Chapter 9: Forms on your site, on the web and on paper](wordpress-forms-09-forms-on-the-web-and-paper.html)
- [Contents](wordpress-forms-guide.html)
