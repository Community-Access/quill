# Appendix A: Every WordPress feature QUILL uses

## What this appendix covers

QUILL talks to your site through WordPress's own REST API, which a site
offers as a set of routes: one for posts, one for the Media Library, and so
on. This appendix lists every group of routes QUILL uses, what it uses it
for, where you reach that in QUILL and QUILL Lite, its WordPress key if it
has one, and what happens on a site that does not offer it. It is for the
curious, and for site administrators deciding what a security plugin may
safely hide.

## How to read it

- **Where** is the same in QUILL and QUILL Lite: both editors build their
  menus from one table. The Command Palette (Ctrl+Shift+P) reaches every row
  in both.
- **Key** is the letter after Ctrl+Alt+Shift+Grave (Chapter 12). A dash
  means the command is reached from its menu or the Command Palette.
- **When the site lacks it.** QUILL reads each site's list of routes once a
  session, before it offers anything. A command whose route is missing stays
  in the menu, because your other sites may have it, but when you choose it
  on that site it says why in one sentence and sends nothing. The rows about
  the page in front of you are also dimmed whenever no WordPress page is
  open; that is about the document, not the site.

## Writing and the site's content

| Feature and routes | Where | Key | When the site lacks it |
|---|---|---|---|
| Pages and posts: `posts`, `pages` | File > WordPress: New, Open, Save Draft to Site, Publish or Update, Properties, Move to Trash, Send and Copy | G, N, O, D, P, R, T | "Community Radio does not offer its pages and posts to QUILL." A security plugin is hiding them. |
| The site's own kinds: `types` | File > WordPress > Open Page or Post (Events and the like beside Posts and Pages) | O | Open offers only Posts and Pages, and says nothing. |
| Versions and autosaves: `revisions`, `autosaves` | File > WordPress > Previous Versions; the unsaved-version question in Open; autosave every two minutes | V | Previous Versions lists only what QUILL kept on your computer. |
| Scheduling (part of `posts` and `pages`) | File > WordPress > Schedule Publish | E | As for pages and posts. |
| Categories and tags: `categories`, `tags` | Properties; New Post; Tools > WordPress > Categories and Tags; Bulk Edit | R | The pickers are empty; the window says the role or site cannot. |
| Custom fields (the registered fields of `posts` and `pages`) | File > WordPress > Custom Fields; Properties | - | "Community Radio has no custom fields for a post." |
| Comments and block notes: `comments` | Tools > WordPress > Comments; View > Block Notes; Insert > Note on This Block | - | Block Notes needs WordPress 6.9 or later, and says the site does not offer notes. |
| Find and replace across the site (part of `posts` and `pages`) | Tools > WordPress > Site-wide Find and Replace | - | As for pages and posts. |
| Many changes at once: `batch/v1` | Fix in Bulk, Undo Site Fix, Merge Into, Bulk Edit, Do with Marked, Site-wide Find and Replace | - | "Community Radio does not offer this. It may be turned off, or the site may need a newer WordPress." Nothing is changed. Batches arrived in WordPress 5.6. |

## Blocks and patterns

| Feature and routes | Where | Key | When the site lacks it |
|---|---|---|---|
| Block types: `block-types` | Insert > WordPress Block; Format > WordPress > Block Settings | - | The list leaves out whatever the site would not list, and keeps QUILL's own everyday blocks. |
| Previews: `block-renderer` | View > Preview Blocks | - | The report says how many blocks the site could not show, and why. |
| The site's patterns: `block-patterns/patterns` | Insert > WordPress Block | - | The list leaves the site's patterns out, and says nothing. |
| Synced patterns: `blocks`, `wp_pattern_category` | Insert > WordPress Block; Tools > WordPress > Manage > Synced Patterns | - | The window lists none, and skips the category question. |
| WordPress.org patterns: `pattern-directory/patterns` | Insert > WordPress Block > WordPress.org Patterns | - | The button is not offered. |
| Icons: `icons`, `icon-collections` | Insert > WordPress Icon | - | "Community Radio has no icon library. Icons arrived in WordPress 7.0." |
| Where a link goes: `wp-block-editor/v1/url-details` | Edit > WordPress > Hear Where a Link Goes, Fix Link Text; Dead Links in Check This Page | - | "Community Radio cannot read where a link goes. That needs WordPress 5.9 or later." Check This Page carries on without dead links. |
| Naming embeds: `oembed/1.0/proxy` | Tools > WordPress > More Media > Name Embeds | - | The report says the site could not describe the embed. |

## Pictures and media

| Feature and routes | Where | Key | When the site lacks it |
|---|---|---|---|
| The Media Library: `media` | Tools > WordPress > Media Library; Insert > Picture from the Media Library; More Media uploads; Alt Text for the Whole Library; Captions, Transcript, Listening Version, Publish a Document as a Page | M, U | "Community Radio does not offer its Media Library to QUILL." |
| Editing a picture: `media/{id}/edit` | Tools > WordPress > More Media > Edit a Picture on the Site | - | "Community Radio offers no edits QUILL can make to" the picture. |
| Uploads in pieces: `media/{id}/sideload`, `finalize` | Tools > WordPress > More Media > Upload a Large File | - | "Community Radio cannot take an upload in pieces. Upload Files sends it in one go instead." |
| Remaking sizes: `media/{id}/post-process` | Tools > WordPress > More Media > Regenerate Sizes | - | "Community Radio cannot remake a picture's sizes. That needs WordPress 6.9 or later." |
| Logo and icon: `settings` | Tools > WordPress > More Media > Site Logo | - | Says the theme does not use the standard site logo. |

## The site's look

| Feature and routes | Where | Key | When the site lacks it |
|---|---|---|---|
| Colours and sizes: `global-styles/{id}` | Format > WordPress > Block Settings; Tools > WordPress > Palette Report; Design > Site Styles | - | Says the theme sets no colours or font sizes, or is not a block theme. |
| Style variations: `global-styles/themes/{theme}/variations` | Tools > WordPress > Design > Style Variations | - | "The theme on Community Radio has no style variations." |
| Earlier looks: `global-styles/{id}/revisions` | Tools > WordPress > Manage > Previous Looks | - | "Community Radio keeps no history of its site styles. That needs a block theme and WordPress 6.3 or later." |
| Themes: `themes` | Tools > WordPress > Manage > Themes | - | The role sentence, if your role cannot see them. |
| Fonts: `font-collections`, `font-families`, `font-faces` | Tools > WordPress > Manage > Fonts | - | "Community Radio has no font library. It needs WordPress 6.5 or newer and a block theme." |
| Templates: `templates`, `template-parts` | Tools > WordPress > Manage > Template Outline | - | "Community Radio uses a classic theme, so it has no block templates." |
| A copy of the design: `wp-block-editor/v1/export` | Tools > WordPress > Manage > Download a Copy of the Site's Design | - | "Community Radio cannot export its design. Only a block theme on WordPress 5.9 or later can." |

## Menus and widgets

| Feature and routes | Where | Key | When the site lacks it |
|---|---|---|---|
| Menus: `menus`, `menu-items`, `menu-locations`, `navigation` | Tools > WordPress > Menus; the "Add it to a menu?" question; Site Map | - | "Community Radio does not offer its menus to QUILL." |
| Menu history: `navigation` revisions | Tools > WordPress > Menu History | - | "Community Radio keeps no history of its Navigation blocks." Classic menus use the versions QUILL keeps on your computer. |
| Widgets: `sidebars`, `widgets` | Tools > WordPress > Manage > Widgets | - | Says the site has no widget areas, and points to Template Outline. |

## Running the site

| Feature and routes | Where | Key | When the site lacks it |
|---|---|---|---|
| Settings: `settings` | Tools > WordPress > Site Settings | - | "Only an administrator on Community Radio can change site settings." |
| Health: `wp-site-health/v1/tests` | Tools > WordPress > Site Check | - | Each test the site could not run is one line, such as "the site could not run this test"; for a role that cannot run them, "Health checks: only an administrator can run them." |
| Space used: `wp-site-health/v1/directory-sizes` | Tools > WordPress > Manage > Space Used | - | "Community Radio does not say how much space it uses. That needs WordPress 5.6 or later." |
| People: `users`, `users/me` | Tools > WordPress > Manage > Users and My Profile; your role on every window | - | The role sentence; your own profile is still yours. |
| Application passwords: `users/{id}/application-passwords`, `introspect` | Sites > Which Password; Manage > Application Passwords; Sign Out This Site | - | "Community Radio did not say which application password QUILL is using." |
| Plugins: `plugins` | Tools > WordPress > Manage > Plugins | - | "Your account on Community Radio is an Editor, which cannot manage plugins.", or, where a security plugin hides the route, "Community Radio does not offer this." |
| Abilities: `wp-abilities/v1` | Tools > WordPress > Manage > AI Abilities, Ask the Site | - | "Community Radio offers no abilities for AI. That needs WordPress 6.9 or later, and a site or plugin that describes some." |

## Plugins QUILL recognises

These are not part of WordPress itself. Each is offered only when the
plugin's own routes are on the site, and Site Check names it.

| Feature and routes | Where | Key | When the site lacks it |
|---|---|---|---|
| QUILL Accessible Forms: `qaf/v1` (or the older `baf/v1`) | Tools > Forms: Publish Form, Insert Form Into Page, Test on Site, Responses | - | "Publish Form needs QUILL Accessible Forms on Community Radio, and the site does not offer it." |
| The Events Calendar: `tribe/events/v1` | Plugin Extras > Events Coming Up, New Event; Plugin Fields | - | Plugin Fields says the plugins add no fields. |
| WooCommerce: `wc/v3` | Plugin Extras > Shop Orders; Plugin Fields | - | As above. |
| Yoast SEO and Rank Math (their registered fields) | Plugin Fields; Properties | - | As above. |

## Across all your sites

Coming Up and What Changed on My Sites (Tools > WordPress > Your Sites) read
the routes above from every connected site. A site that does not answer is
listed as "Did not answer:" and its name, and the rest carry on.

## Where to next

- Previous: [Chapter 13: Every window, field and button](wordpress-forms-13-window-reference.html)
- [Contents](wordpress-forms-guide.html)
