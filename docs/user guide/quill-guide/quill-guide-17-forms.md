# Chapter 17: Forms

## Payments and donations

Tools > Forms > Insert Payment Field adds a fixed amount, a `#field_id`
amount reference, or a donation with optional bounds. Form Payments Setup
chooses Stripe and/or PayPal, currency, capture mode and test mode. New settings
start in test mode; all edits remain local until Publish Form.

Configure provider sandbox credentials and webhooks in WordPress, then use
Verify Payment Setup. Publishing requires a QAF plugin implementing payment
contract version 1, ready selected providers/webhooks and matching payment mode.
Test on Site checks the published form and refuses live-payment checkout.
Responses show payment metadata; Refresh Payment Status rereads the site after
confirmation. CSV and Word exports include the metadata. Actual charging,
manual capture and refunds stay on the site or in the provider dashboard.

For the complete sandbox-first workflow, read the payment section in
[Forms on the web and paper](../wordpress-and-forms/wordpress-forms-09-forms-on-the-web-and-paper.html).

## Writing a form

A form is a contact form, an event sign-up, a membership renewal, a survey or
a feedback page. Making one usually means dragging boxes around a web page,
which is one of the hardest things on the web to do with a screen reader. But
a form is really just structured text: a title, some questions, their
choices, and a few rules. QUILL is good at text, so that is how you write one
here. You check it, and then you fill it in yourself, with your screen
reader, before anyone else sees it.

**Turning it on.** Forms is on in every feature profile except Essential. If you do not
see **File > New Form...**, choose another profile, or switch on Forms
by itself, in **Profiles and Features...**.

This chapter is the short version. The form language, rules, Form Properties,
putting a form on your site, paper and braille copies, responses and AI help
are all in the [WordPress and Forms manual](../wordpress-and-forms/wordpress-forms-guide.html), which QUILL and QUILL
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
day. Use the menus, or press `Ctrl+Shift+P`, type "form", and pick the
command from the list.

---

- Previous: [Chapter 16: WordPress](quill-guide-16-wordpress.html)
- Next: [A last word](quill-guide-a-last-word.html)
- [Contents](../userguide.html)
