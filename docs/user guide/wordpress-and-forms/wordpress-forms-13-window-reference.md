# Chapter 13: WordPress Workbench reference

## What this chapter covers

The WordPress Workbench is the shared management window for QUILL and QUILL
Lite. It brings connected sites, their content and the actions available to
your account into one keyboard-first workspace. This chapter is the current
reference for site management; the former separate management-window reference
is retired.

The earlier chapters explain common tasks. Use this chapter to find a node,
understand its list and actions, or see how the supported form and membership
integrations behave.

## Open the Workbench

In QUILL or QUILL Lite, choose **Tools > WordPress > Open WordPress
Workbench...**. Other WordPress management doors open the Workbench at the
matching node. Writing and editing a post still happens in the editor.

Connect a site from **File > WordPress > Connect a Site...**. The Workbench
reads the site's own REST API and permissions. Every confirmation names the
site it will affect.

## Move around

The Workbench has a tree, a filter, a list, a details pane and a status bar.
The tree names each place; the list shows its rows; the details pane explains
the selected row. F6 and Shift+F6 move between panes. F1 describes the place
or row under focus.

The top of the tree includes **Start Here**, **Needs My Attention**, **Inbox**,
**Comments Waiting**, **Pending Review**, **Scheduled**, **Drafts**, **Held as
Spam**, **Form Responses**, **Sites**, **Calendar**, **Across Sites** and
**Practice Site**. Each site has its own branch for posts, pages, media,
comments, people, categories, appearance, settings, forms, memberships and
other content the site exposes.

Use Right Arrow to open a branch and Left Arrow to close it. Enter runs the
selected row's main action. Alt+Enter opens its Properties. Context menus and
the **Item** menu contain the other actions for that row. If an action is dim,
Shift+F1 says what permission or prerequisite is missing.

The filter narrows the current list. Ctrl+E moves to it; Ctrl+Shift+F opens
the Filter Builder; F5 refreshes. View > Load More and Load All read longer
lists. View > Columns chooses which supported details appear in a list.

The status bar says which site and role are active, how many rows are shown,
what filter is in effect, whether a list is loading, and how much Workbench
access the site has. Enter on a status cell opens its related action.

## Access and confirmations

**Read Only** allows reading. **Organize** adds undoable organization and
moderation actions. **Full** allows site changes. Safe Mode and **View As
Role...** limit the Workbench to reading. WordPress still checks the connected
account's actual capabilities before it accepts an action.

A preview names the site and shows what will change before a write. Actions
that delete or replace data need a stronger confirmation. Change History and
Undo WordPress Change are in the **Edit** menu when the inverse operation is
available.

Default WordPress roles are Subscriber, Contributor, Author, Editor and
Administrator. Sites can define additional roles. **Site > Roles and What
They May Do** explains the roles the site reports.

## Supported plugin integrations

Plugin-specific support in this implementation is limited to QAF, Gravity
Forms and Paid Memberships Pro.

| Plugin | Workbench support |
| --- | --- |
| QUILL Accessible Forms (QAF) | List forms and responses, review spam status, and open a QAF form in the editor's Form Outline. Change an existing field's control type there; QUILL previews which properties and choices carry over. |
| Gravity Forms | List forms and responses, review spam status, and convert common text, paragraph, email, number, drop-down, radio and checkbox fields. QUILL reads the full form, previews the field conversion, then sends the complete form through Gravity Forms REST v2 after confirmation. The connected account needs the site's `gravityforms_create_form` capability. |
| Paid Memberships Pro | Read Membership Levels, Orders, Subscriptions and Renewals Due. On a site's Users list, **Show Memberships...** reads one person's current and past levels. Change and Cancel abilities are listed under **Abilities** and require a preview; the site checks permission when they run. |

Paid Memberships Pro's Abilities integration requires WordPress 6.9 or later
and Paid Memberships Pro 3.9 or later. Cancelling a membership may also cancel
that member's recurring subscription at the payment gateway. The Workbench
shows this consequence before the action runs.

The general REST and Abilities views can describe other APIs a site exposes.
They do not add a first-class workflow for another plugin.

## Practice Site

**Tools > Practice Site...** starts a local WordPress Playground site when
the build includes the pinned Playground CLI. The starter site has a welcome
page, a published sample post, a draft and a QUILL application password. It
runs on this computer and is reset by **Reset Practice Site...**. If the
Playground CLI is not staged in the build, the Workbench explains how to make
it available.

## Useful keys

| Key | Action |
| --- | --- |
| F1 | Help for the current place or row |
| F5 | Refresh the current list |
| F6 / Shift+F6 | Next or previous pane |
| Alt+Enter | Properties for the selected row |
| Ctrl+E | Move to the filter |
| Ctrl+Shift+F | Filter Builder |
| Ctrl+Shift+H | Change History |
| Ctrl+N | New Here |
| Ctrl+Shift+O | Workbench Options |
| Alt+F4 | Close the Workbench |

For writing and checking forms, continue with [Chapter 8: Writing forms](wordpress-forms-08-writing-forms.html),
[Chapter 9: Forms on the web and paper](wordpress-forms-09-forms-on-the-web-and-paper.html),
and [Chapter 12: Every WordPress and Forms key](wordpress-forms-12-keys.html).

## Where to next

- Previous: [Chapter 12: Every WordPress and Forms key](wordpress-forms-12-keys.html)
- Next: [Appendix A: Every WordPress feature QUILL uses](wordpress-forms-appendix-a-features.html)
- [Contents](wordpress-forms-guide.html)
