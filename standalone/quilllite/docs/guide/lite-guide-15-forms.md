# Chapter 15: Forms

## Payments and donations

QUILL Lite uses the same payment commands as QUILL. Tools > Forms > Insert
Payment Field adds a fixed amount, `#field_id` reference or bounded donation.
Form Payments Setup chooses Stripe and/or PayPal, currency and capture mode.
New settings start in test mode. Setup changes only the local form.

Configure sandbox credentials and webhooks in WordPress, then use Verify
Payment Setup. Publishing requires a QAF plugin implementing payment contract
version 1, ready selected providers/webhooks and matching test/live mode.
Test on Site checks the published form and refuses live-payment checkout.
Responses include payment metadata in Read, CSV and Word exports; Refresh
Payment Status confirms the site before rereading entries. QUILL Lite stores
no provider credentials and never captures or refunds payments.

Follow the full payment walkthrough in
[Forms on the web and paper](../wordpress-and-forms/wordpress-forms-09-forms-on-the-web-and-paper.html).

## Writing a form

A form is a contact form, an event sign-up, a membership renewal, a survey or
a feedback page. Making one usually means dragging boxes around a web page,
which is one of the hardest things on the web to do with a screen reader. But
a form is really just structured text: a title, some questions, their
choices, and a few rules. QUILL Lite is good at text, so that is how you write one
here. You check it, and then you fill it in yourself, with your screen
reader, before anyone else sees it.

**Turning it on.** Forms is on in the Recommended and Everything profiles, and off in
WordPad and Notepad. If you do not see **File > New Form...**, check
Forms in **Tools > Customize Features**.

This chapter is the short version. The form language, rules, Form Properties,
putting a form on your site, paper and braille copies, responses and AI help
are all in the [WordPress and Forms manual](https://community-access.github.io/quill/docs/wordpress-forms-guide.html), which QUILL and QUILL
Lite share.

## Where everything is

| Menu | What is there |
|---|---|
| **File** | New Form, beside the other New commands |
| **Insert** | Form Field |
| **View** | Form Outline |
| **Format** | Form Rules |
| **Tools > Forms** | Check This Form, Fill It In Yourself, Form Properties, Responses |

To start, choose **File > New Form...**, give the form a title, pick a
template, and save it. Apart from New Form and Responses, the Forms commands
are dimmed until a form is open.

## Keys

None of the Forms commands has a shortcut key. Every useful key is already
taken by something you use more often, and you will not write forms every
day. Use the menus, or press **Ctrl+Shift+P**, type "form", and pick the
command from the list.

---

- Previous: [Chapter 14: WordPress](lite-guide-14-wordpress.html)
- Next: [Licences and notices](lite-guide-licences-and-notices.html)
- [Contents](../userguide.html)
