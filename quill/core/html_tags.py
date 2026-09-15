"""The HTML vocabulary: what the tag picker offers, and what it calls each thing.

Split out of :mod:`quill.core.tagging` when that module passed its GATE-11 cap,
and the seam is the honest one rather than a convenient line number: this file
is **pure data** -- a list of elements, the ones that take no closing tag, and
the words people search for them by -- while ``tagging`` holds the functions
that turn a choice into text. The two grow for entirely different reasons. A new
element is a row here; a new *kind* of insertion is a branch there.

**The list is meant to be complete.** A searchable picker has no cost to being
so: searching 111 elements is no harder than searching 46, and every element
left out is a dead end somebody has to leave the app to resolve. The forty-six
that shipped before this file existed left out ``<dl>``, ``<dt>`` and ``<dd>`` --
which the editor *announces* as the caret moves through them -- along with
``<figure>``, ``<figcaption>``, the parts that make a table readable, ``<abbr>``,
and ``<br>`` and ``<hr>``, which :data:`VOID_HTML_TAGS` already knew how to
write and no row could reach.

**The aliases are the other half of complete.** A tag is looked for by what it
does far more often than by its name, and the two rarely coincide: nobody types
``dl`` when what they want is a glossary, or ``abbr`` when what they want is an
acronym. Every entry in :data:`HTML_SEARCH_ALIASES` is a phrase somebody
actually reaches for.

Re-exported from :mod:`quill.core.tagging`, so every existing import is
unchanged.
"""

from __future__ import annotations

__all__ = ["HTML_SEARCH_ALIASES", "HTML_TAG_CHOICES", "VOID_HTML_TAGS"]


#: Elements that take no closing tag, so an insertion writes ``<br />`` rather
#: than ``<br></br>``. The complete HTML living-standard set, not a sample: a
#: tag wrongly closed here is invalid markup somebody has to find by eye, which
#: is exactly the review this editor's users cannot do for themselves.
VOID_HTML_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "source",
    "track",
    "wbr",
}

#: Every element a person editing an HTML document might reasonably reach for,
#: grouped by what it is for rather than alphabetically -- the order is what a
#: reader hears when the search box is empty.
#:
#: **A searchable list should be complete.** Searching ninety is no harder than
#: searching forty, and a tag that is missing is a dead end somebody has to
#: leave the app to resolve. The earlier forty left out `<dl>`, `<dt>` and
#: `<dd>` -- which this editor *announces* as you arrow through them -- along
#: with `<figure>`/`<figcaption>`, the accessible-table parts (`<caption>`,
#: `<thead>`, `<tbody>`, `<th scope>`), `<abbr>`, and `<br>` and `<hr>`, which
#: were already handled as void elements and simply could not be chosen.
HTML_TAG_CHOICES = [
    # Sectioning and structure
    "div",
    "span",
    "p",
    "section",
    "article",
    "aside",
    "header",
    "footer",
    "nav",
    "main",
    "hgroup",
    "address",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "br",
    # Lists, all three kinds
    "ul",
    "ol",
    "li",
    "dl",
    "dt",
    "dd",
    # Tables, including the parts that make one readable
    "table",
    "caption",
    "thead",
    "tbody",
    "tfoot",
    "colgroup",
    "col",
    "tr",
    "th",
    "td",
    # Links, media and figures
    "a",
    "img",
    "figure",
    "figcaption",
    "picture",
    "source",
    "video",
    "audio",
    "track",
    "iframe",
    "embed",
    "object",
    "map",
    "area",
    "canvas",
    "svg",
    # Text-level semantics
    "strong",
    "em",
    "b",
    "i",
    "u",
    "s",
    "mark",
    "small",
    "sub",
    "sup",
    "del",
    "ins",
    "abbr",
    "cite",
    "q",
    "blockquote",
    "dfn",
    "time",
    "data",
    "kbd",
    "samp",
    "var",
    "code",
    "pre",
    "bdi",
    "bdo",
    "ruby",
    "rt",
    "rp",
    "wbr",
    # Forms
    "form",
    "label",
    "input",
    "textarea",
    "select",
    "option",
    "optgroup",
    "datalist",
    "button",
    "fieldset",
    "legend",
    "output",
    "progress",
    "meter",
    # Interactive and scripting
    "details",
    "summary",
    "dialog",
    "template",
    "slot",
    "script",
    "noscript",
    "style",
    # A whole page
    "html",
    "head",
    "title",
    "base",
    "link",
    "meta",
    "body",
]

#: What people actually type when they are looking for each element.
HTML_SEARCH_ALIASES: dict[str, tuple[str, ...]] = {
    "h1": ("heading 1", "heading one", "level 1", "h one"),
    "h2": ("heading 2", "heading two", "level 2", "h two"),
    "h3": ("heading 3", "heading three", "level 3", "h three"),
    "h4": ("heading 4", "heading four", "level 4", "h four"),
    "h5": ("heading 5", "heading five", "level 5", "h five"),
    "h6": ("heading 6", "heading six", "level 6", "h six"),
    "input": ("text", "textbox", "field", "radio", "checkbox", "email", "password"),
    "button": ("click", "submit", "reset", "action"),
    "select": ("dropdown", "combo", "pick"),
    "option": ("choice", "item", "dropdown"),
    "textarea": ("multiline", "text area", "notes"),
    "label": ("caption", "form", "field"),
    "form": ("fields", "controls", "submit"),
    "fieldset": ("group", "form"),
    "legend": ("group title", "form"),
    "datalist": ("autocomplete", "suggestions"),
    "optgroup": ("option group", "group"),
    "output": ("result", "computed"),
    "progress": ("meter", "completion"),
    "meter": ("gauge", "level"),
    "details": ("collapsible", "accordion"),
    "summary": ("collapsible", "accordion", "title"),
    # A tag is looked for by what it does far more often than by its name, and
    # the two rarely coincide: nobody types "dl" when what they want is a
    # glossary. These are the words people actually reach for.
    "dl": ("definition list", "glossary", "terms"),
    "dt": ("term", "definition list", "glossary"),
    "dd": ("definition", "description", "glossary"),
    "figure": ("image with caption", "picture", "illustration"),
    "figcaption": ("caption", "image caption", "figure"),
    "caption": ("table caption", "table title"),
    "thead": ("table header", "header row"),
    "tbody": ("table body", "rows"),
    "tfoot": ("table footer", "totals"),
    "colgroup": ("columns", "table"),
    "col": ("column", "table"),
    "th": ("header cell", "table heading", "scope"),
    "td": ("cell", "table"),
    "tr": ("row", "table"),
    "abbr": ("abbreviation", "acronym", "initialism"),
    "a": ("link", "hyperlink", "anchor", "href"),
    "img": ("image", "picture", "alt text", "photo"),
    "ul": ("bullet list", "unordered", "bullets"),
    "ol": ("numbered list", "ordered", "steps"),
    "li": ("list item", "bullet", "row"),
    "blockquote": ("quote", "quotation", "citation"),
    "q": ("inline quote", "quotation"),
    "cite": ("citation", "source", "title of work"),
    "mark": ("highlight", "highlighted", "marker"),
    "del": ("strikethrough", "deleted", "removed"),
    "ins": ("inserted", "added", "underline"),
    "s": ("strikethrough", "struck out", "no longer accurate"),
    "u": ("underline",),
    "b": ("bold", "presentational"),
    "i": ("italic", "presentational"),
    "strong": ("bold", "important", "emphasis"),
    "em": ("italic", "emphasis", "stress"),
    "small": ("fine print", "small print", "aside"),
    "sub": ("subscript", "below"),
    "sup": ("superscript", "above", "footnote marker"),
    "kbd": ("keyboard", "key", "shortcut"),
    "samp": ("sample output", "program output"),
    "var": ("variable", "placeholder"),
    "dfn": ("defining instance", "definition", "term"),
    "time": ("date", "datetime", "timestamp"),
    "data": ("machine readable", "value"),
    "code": ("code", "snippet", "monospace"),
    "pre": ("preformatted", "code block", "monospace"),
    "hr": ("horizontal rule", "divider", "separator", "thematic break"),
    "br": ("line break", "newline", "hard return"),
    "wbr": ("word break", "line break opportunity"),
    "aside": ("sidebar", "callout", "tangent"),
    "header": ("banner", "masthead", "top"),
    "footer": ("bottom", "colophon"),
    "nav": ("navigation", "menu", "links"),
    "main": ("main content", "landmark"),
    "hgroup": ("heading group", "subtitle"),
    "address": ("contact", "author"),
    "section": ("landmark", "region"),
    "article": ("post", "entry", "landmark"),
    "video": ("movie", "media", "captions", "mp4"),
    "audio": ("sound", "media", "mp3", "podcast"),
    "track": ("captions", "subtitles", "vtt", "audio description"),
    "picture": ("responsive image", "art direction"),
    "iframe": ("embed", "frame", "youtube"),
    "canvas": ("drawing", "graphics"),
    "svg": ("vector", "icon", "graphic"),
    "dialog": ("modal", "popup", "dialogue"),
    "template": ("inert", "clone"),
    "slot": ("web component", "shadow dom"),
    "script": ("javascript", "js", "code"),
    "noscript": ("no javascript", "fallback"),
    "style": ("css", "stylesheet"),
    "html": ("page", "document", "lang"),
    "head": ("page", "metadata"),
    "body": ("page", "content"),
    "title": ("page title", "tab title"),
    "meta": ("metadata", "charset", "viewport", "description"),
    "link": ("stylesheet", "favicon", "rel"),
    "base": ("base url",),
    "bdi": ("bidirectional", "isolate", "rtl"),
    "bdo": ("bidirectional", "override", "rtl", "direction"),
    "ruby": ("annotation", "furigana", "pronunciation"),
    "rt": ("ruby text", "annotation"),
    "rp": ("ruby parenthesis", "fallback"),
    "object": ("embed", "plugin"),
    "embed": ("plugin", "external"),
    "map": ("image map", "areas"),
    "area": ("image map", "hotspot"),
    "span": ("inline", "wrapper", "no meaning"),
    "div": ("block", "wrapper", "container", "no meaning"),
}
