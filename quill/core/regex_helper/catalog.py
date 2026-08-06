"""The recipe catalog for the Regular Expression Helper.

A browsable library of ready-made patterns, each with a plain-language
explanation and a sample the pattern genuinely matches. The catalog exists
because regular expressions are the least screen-reader-friendly notation in
computing: a sighted user can crib a pattern from a website and eyeball it,
while a blind user hears a stream of punctuation. Every explanation here is a
sentence meant to be heard ("Finds words separated by two or more spaces"),
never symbol-speak, and every sample lets the user run the recipe immediately
and hear real matches before trusting it on their own document.

Capture-and-replace recipes additionally carry a ready replacement template
and a note describing what the replacement does in ordinary words.

Pure data; wx-free, network-free, strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["CATEGORIES", "RECIPES", "RegexRecipe", "recipes_by_category"]


@dataclass(frozen=True)
class RegexRecipe:
    """One ready-made pattern with everything needed to hear, try, and trust it.

    ``explanation`` is one or two spoken-friendly sentences; ``sample`` always
    contains at least one real match so "Try it" produces an immediate,
    audible result. ``replace_template``/``replace_note`` are set on recipes
    meant for capture-and-replace work.
    """

    name: str
    pattern: str
    explanation: str
    sample: str
    category: str
    difficulty: str  # "basic" | "intermediate" | "advanced"
    replace_template: str | None = None
    replace_note: str | None = None


#: Category order as presented to the user: everyday cleanup first, writer
#: tasks in the middle, technical material last.
CATEGORIES: tuple[str, ...] = (
    "Cleanup",
    "Words and phrases",
    "Lines",
    "Numbers",
    "Dates and times",
    "Contact and web",
    "Markdown",
    "HTML and tags",
    "Punctuation and dialogue",
    "Writing and editing",
    "OCR and scan cleanup",
    "Code and identifiers",
    "Capture and replace",
)


RECIPES: tuple[RegexRecipe, ...] = (
    # -- Cleanup --------------------------------------------------------------
    RegexRecipe(
        name="Two or more spaces",
        pattern=r" {2,}",
        explanation=(
            "Finds runs of two or more spaces in a row, the usual leftovers "
            "of manual alignment or double-spacing after periods."
        ),
        sample="This line  has   extra spaces inside it.",
        category="Cleanup",
        difficulty="basic",
        replace_template=" ",
        replace_note="Replaces each run of spaces with a single space.",
    ),
    RegexRecipe(
        name="Trailing spaces at the end",
        pattern=r"[ \t]+$",
        explanation=(
            "Finds invisible spaces or tabs sitting at the end of the text. "
            "They are silent to the ear but show up in diffs and pasted text."
        ),
        sample="This line ends with stray spaces   ",
        category="Cleanup",
        difficulty="basic",
        replace_template="",
        replace_note="Deletes the trailing whitespace outright.",
    ),
    RegexRecipe(
        name="Blank lines between paragraphs",
        pattern=r"\n\s*\n",
        explanation="Finds each blank gap between paragraphs, even when the blank "
        "line holds stray spaces.",
        sample="Paragraph one.\n\nParagraph two.",
        category="Cleanup",
        difficulty="basic",
    ),
    RegexRecipe(
        name="Tab characters",
        pattern=r"\t+",
        explanation="Finds tab characters, alone or in runs, wherever they appear.",
        sample="Column one\tColumn two\tColumn three",
        category="Cleanup",
        difficulty="basic",
    ),
    RegexRecipe(
        name="Space before punctuation",
        pattern=r" +(?=[,.;:!?])",
        explanation=(
            "Finds spaces wrongly placed just before a comma, period, or "
            "other punctuation mark, without touching the mark itself."
        ),
        sample="This sentence has a space before the comma , and the period .",
        category="Cleanup",
        difficulty="intermediate",
        replace_template="",
        replace_note="Removes the stray space; the punctuation stays put.",
    ),
    RegexRecipe(
        name="Three or more blank lines",
        pattern=r"\n{3,}",
        explanation="Finds places where three or more line breaks pile up, leaving big empty gaps.",
        sample="Section one.\n\n\n\nSection two.",
        category="Cleanup",
        difficulty="basic",
        replace_template="\n\n",
        replace_note="Collapses each pile-up to a single blank line.",
    ),
    RegexRecipe(
        name="Non-breaking spaces",
        pattern="\u00a0+",
        explanation=(
            "Finds non-breaking spaces, which paste in from web pages and "
            "word processors and sound identical to normal spaces."
        ),
        sample="Pasted\u00a0text\u00a0keeps its special spaces.",
        category="Cleanup",
        difficulty="intermediate",
        replace_template=" ",
        replace_note="Converts each non-breaking space to an ordinary space.",
    ),
    RegexRecipe(
        name="Indentation at the start",
        pattern=r"^[ \t]+",
        explanation="Finds spaces or tabs at the very start of the text, before the first word.",
        sample="    An indented opening line.",
        category="Cleanup",
        difficulty="basic",
    ),
    RegexRecipe(
        name="Windows line endings",
        pattern=r"\r\n",
        explanation=(
            "Finds Windows-style line endings, a carriage return followed by "
            "a newline, useful before sharing text with other systems."
        ),
        sample="Line one\r\nLine two",
        category="Cleanup",
        difficulty="intermediate",
    ),
    # -- Words and phrases ----------------------------------------------------
    RegexRecipe(
        name="Repeated word",
        pattern=r"\b(\w+) \1\b",
        explanation=(
            "Finds a word accidentally typed twice in a row, like 'the the'. "
            "One of the easiest mistakes to make and the hardest to hear."
        ),
        sample="This is is a common mistake.",
        category="Words and phrases",
        difficulty="intermediate",
        replace_template=r"\1",
        replace_note="Keeps a single copy of the word and removes the duplicate.",
    ),
    RegexRecipe(
        name="The word 'very' on its own",
        pattern=r"\bvery\b",
        explanation="Finds 'very' as a whole word, skipping words that merely "
        "contain it, like 'every'.",
        sample="It was very good, and every reviewer agreed.",
        category="Words and phrases",
        difficulty="basic",
    ),
    RegexRecipe(
        name="Long words",
        pattern=r"\b[A-Za-z]{10,}\b",
        explanation="Finds words of ten letters or more, handy for spotting jargon "
        "or readability problems.",
        sample="An extraordinary achievement by any measure.",
        category="Words and phrases",
        difficulty="basic",
    ),
    RegexRecipe(
        name="Words in all capitals",
        pattern=r"\b[A-Z]{2,}\b",
        explanation="Finds words written entirely in capital letters, such as "
        "acronyms or shouted words.",
        sample="Please reply ASAP about the NASA visit.",
        category="Words and phrases",
        difficulty="basic",
    ),
    RegexRecipe(
        name="Hyphenated words",
        pattern=r"\b\w+(?:-\w+)+\b",
        explanation="Finds hyphenated words like 'well-known', including ones "
        "with several hyphens.",
        sample="A well-known, up-to-date example.",
        category="Words and phrases",
        difficulty="intermediate",
    ),
    RegexRecipe(
        name="Capitalized words",
        pattern=r"\b[A-Z][a-z]+\b",
        explanation="Finds words that start with one capital letter, such as "
        "names and sentence openers.",
        sample="Alice met Bob near London Bridge.",
        category="Words and phrases",
        difficulty="basic",
    ),
    RegexRecipe(
        name="Contractions",
        pattern=r"\b\w+'\w+\b",
        explanation="Finds contractions like don't and it's, useful when a "
        "style guide forbids them.",
        sample="Don't worry, it's nearly finished.",
        category="Words and phrases",
        difficulty="basic",
    ),
    RegexRecipe(
        name="Either spelling of colour",
        pattern=r"\b(?:color|colour)\b",
        explanation="Finds both the American and British spellings of the word in one pass.",
        sample="The colour of the sky, or the color of the sea.",
        category="Words and phrases",
        difficulty="basic",
    ),
    # -- Lines ----------------------------------------------------------------
    RegexRecipe(
        name="Completely empty lines",
        pattern=r"(?m)^$",
        explanation="Finds lines with nothing on them at all. The (?m) at the front makes the "
        "pattern look at each line separately.",
        sample="First line\n\nThird line",
        category="Lines",
        difficulty="intermediate",
    ),
    RegexRecipe(
        name="Bulleted list lines",
        pattern=r"(?m)^[-*] ",
        explanation="Finds lines that begin with a dash or asterisk bullet followed by a space.",
        sample="- first item\n- second item\n* third item",
        category="Lines",
        difficulty="basic",
    ),
    RegexRecipe(
        name="Lines ending with a period",
        pattern=r"(?m)\.$",
        explanation="Finds the period at the end of any line, useful for "
        "checking list punctuation.",
        sample="A complete sentence.\nA fragment without one",
        category="Lines",
        difficulty="basic",
    ),
    RegexRecipe(
        name="Lines containing a word",
        pattern=r"(?m)^.*\berror\b.*$",
        explanation="Finds every whole line that mentions the word 'error' anywhere on "
        "it. Swap in your own word.",
        sample="all good\nan error occurred here\nall good again",
        category="Lines",
        difficulty="intermediate",
    ),
    RegexRecipe(
        name="Numbered list lines",
        pattern=r"(?m)^\d+\. ",
        explanation="Finds lines that start with a number, a period, and a space, "
        "like a numbered list.",
        sample="1. First step\n2. Second step",
        category="Lines",
        difficulty="basic",
    ),
    RegexRecipe(
        name="Lines longer than eighty characters",
        pattern=r"(?m)^.{81,}$",
        explanation="Finds lines longer than eighty characters, a common wrapping "
        "limit for code and email.",
        sample=(
            "short line\n"
            "This single line runs on and on and on and on and on and on and on "
            "and on and on well past the eighty character mark."
        ),
        category="Lines",
        difficulty="intermediate",
    ),
    RegexRecipe(
        name="Comment lines",
        pattern=r"(?m)^#.*$",
        explanation="Finds whole lines that start with a hash sign, the comment "
        "style of many file formats.",
        sample="# a comment line\nregular text",
        category="Lines",
        difficulty="basic",
    ),
    RegexRecipe(
        name="Very short lines",
        pattern=r"(?m)^.{1,4}$",
        explanation="Finds lines of four characters or fewer, often stray "
        "fragments left by editing.",
        sample="Hi\nHello there, this line is long enough.",
        category="Lines",
        difficulty="basic",
    ),
    # -- Numbers --------------------------------------------------------------
    RegexRecipe(
        name="Whole numbers",
        pattern=r"\d+",
        explanation="Finds any run of digits: 7, 42, 2026, and so on.",
        sample="There are 42 items across 3 shelves.",
        category="Numbers",
        difficulty="basic",
    ),
    RegexRecipe(
        name="Decimal numbers",
        pattern=r"\d+\.\d+",
        explanation="Finds numbers with a decimal point, like 3.14 or 99.9.",
        sample="Pi is about 3.14, and the score was 99.5.",
        category="Numbers",
        difficulty="basic",
    ),
    RegexRecipe(
        name="Numbers with thousands separators",
        pattern=r"\b\d{1,3}(?:,\d{3})+\b",
        explanation="Finds large numbers written with commas every three digits, like 1,234,567.",
        sample="The city has 1,234,567 residents.",
        category="Numbers",
        difficulty="intermediate",
    ),
    RegexRecipe(
        name="Dollar amounts",
        pattern=r"\$\d+(?:\.\d{2})?",
        explanation="Finds dollar amounts like $5 or $19.99, with or without cents.",
        sample="It costs $19.99 today, down from $25.",
        category="Numbers",
        difficulty="basic",
    ),
    RegexRecipe(
        name="Percentages",
        pattern=r"\d+(?:\.\d+)?%",
        explanation="Finds percentages, whole or decimal, like 40% or 12.5%.",
        sample="Growth of 12.5% beat the 10% target.",
        category="Numbers",
        difficulty="basic",
    ),
    RegexRecipe(
        name="Negative numbers",
        pattern=r"-\d+(?:\.\d+)?",
        explanation="Finds numbers with a leading minus sign, like -40 or -3.5.",
        sample="The low was -40 degrees, a drop of -12.5 overnight.",
        category="Numbers",
        difficulty="basic",
    ),
    RegexRecipe(
        name="Numbers from 0 to 255",
        pattern=r"\b(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\b",
        explanation=(
            "Finds only numbers in the range 0 through 255, the range of one "
            "byte, rejecting anything larger."
        ),
        sample="Values 255 and 17 fit; 300 does not.",
        category="Numbers",
        difficulty="advanced",
    ),
    RegexRecipe(
        name="Roman numerals",
        pattern=r"\b[IVXLCDM]+\b",
        explanation="Finds runs of Roman-numeral letters, like the XIV in a chapter heading.",
        sample="Chapter XIV begins after part II.",
        category="Numbers",
        difficulty="intermediate",
    ),
    RegexRecipe(
        name="Ordinal numbers",
        pattern=r"\b\d+(?:st|nd|rd|th)\b",
        explanation="Finds ordinals written with digits, like 1st, 2nd, 3rd, and 4th.",
        sample="The 3rd of May, then the 21st.",
        category="Numbers",
        difficulty="basic",
    ),
    # -- Dates and times ------------------------------------------------------
    RegexRecipe(
        name="ISO dates",
        pattern=r"\b\d{4}-\d{2}-\d{2}\b",
        explanation="Finds dates in year-month-day form with hyphens, like 2026-08-05.",
        sample="The report is due on 2026-08-05.",
        category="Dates and times",
        difficulty="basic",
    ),
    RegexRecipe(
        name="Slash-style dates",
        pattern=r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
        explanation="Finds dates written with slashes, like 7/4/2026 or 12/25/26.",
        sample="Filed on 7/4/2026 and updated 12/25/26.",
        category="Dates and times",
        difficulty="basic",
    ),
    RegexRecipe(
        name="Month-name dates",
        pattern=(
            r"\b(?:January|February|March|April|May|June|July|August"
            r"|September|October|November|December) \d{1,2}, \d{4}\b"
        ),
        explanation="Finds fully written dates like August 5, 2026.",
        sample="On August 5, 2026 the update ships.",
        category="Dates and times",
        difficulty="intermediate",
    ),
    RegexRecipe(
        name="Twelve-hour times",
        pattern=r"\b\d{1,2}:\d{2} ?(?:AM|PM|am|pm)\b",
        explanation="Finds clock times with AM or PM, like 9:30 AM or 11:15pm.",
        sample="Meet at 9:30 AM sharp, not 2:45 pm.",
        category="Dates and times",
        difficulty="basic",
    ),
    RegexRecipe(
        name="Twenty-four-hour times",
        pattern=r"\b(?:[01]\d|2[0-3]):[0-5]\d\b",
        explanation="Finds 24-hour clock times from 00:00 through 23:59, like 18:45.",
        sample="Departure at 18:45, arrival at 06:10.",
        category="Dates and times",
        difficulty="intermediate",
    ),
    RegexRecipe(
        name="Four-digit years",
        pattern=r"\b(?:19|20)\d{2}\b",
        explanation="Finds four-digit years from the 1900s and 2000s.",
        sample="Founded in 1999 and rebuilt in 2026.",
        category="Dates and times",
        difficulty="basic",
    ),
    RegexRecipe(
        name="Weekday names",
        pattern=r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b",
        explanation="Finds any full weekday name.",
        sample="See you on Friday, or Monday at the latest.",
        category="Dates and times",
        difficulty="basic",
    ),
    RegexRecipe(
        name="Durations like 2h 45m",
        pattern=r"\b\d+h(?: ?\d+m)?\b",
        explanation="Finds shorthand durations written with h for hours and m for "
        "minutes, like 2h 45m.",
        sample="The flight takes 2h 45m, the drive 5h.",
        category="Dates and times",
        difficulty="intermediate",
    ),
    # -- Contact and web ------------------------------------------------------
    RegexRecipe(
        name="Email addresses",
        pattern=r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        explanation="Finds email addresses, like name@example.com.",
        sample="Write to jeff@example.com or team@quill.org soon.",
        category="Contact and web",
        difficulty="intermediate",
    ),
    RegexRecipe(
        name="Web addresses",
        pattern=r"https?://[^\s<>\"]+",
        explanation="Finds web addresses that start with http or https.",
        sample="Visit https://example.com/docs for details.",
        category="Contact and web",
        difficulty="basic",
    ),
    RegexRecipe(
        name="Bare domain names",
        pattern=r"\b[a-z0-9-]+\.(?:com|org|net|edu|gov|io)\b",
        explanation="Finds plain domain names without the http part, like example.org.",
        sample="Search example.org before checking quill.io.",
        category="Contact and web",
        difficulty="intermediate",
    ),
    RegexRecipe(
        name="US phone numbers",
        pattern=r"\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}",
        explanation="Finds ten-digit US phone numbers in common formats, with or "
        "without parentheses.",
        sample="Call (555) 123-4567 or 555.987.6543 today.",
        category="Contact and web",
        difficulty="intermediate",
    ),
    RegexRecipe(
        name="ZIP codes",
        pattern=r"\b\d{5}(?:-\d{4})?\b",
        explanation="Finds five-digit US ZIP codes, with or without the four-digit extension.",
        sample="Mail it to 90210 or 20500-0003.",
        category="Contact and web",
        difficulty="basic",
    ),
    RegexRecipe(
        name="IP addresses",
        pattern=r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        explanation="Finds numeric internet addresses of four dot-separated "
        "parts, like 192.168.1.10.",
        sample="The server at 192.168.1.10 answered first.",
        category="Contact and web",
        difficulty="intermediate",
    ),
    RegexRecipe(
        name="Social media handles",
        pattern=r"@\w+",
        explanation="Finds at-sign handles like @quill_app. Note it will also flag "
        "the tail of email addresses.",
        sample="Follow @quill_app for release news.",
        category="Contact and web",
        difficulty="basic",
    ),
    RegexRecipe(
        name="Hashtags",
        pattern=r"#\w+",
        explanation="Finds social-media hashtags such as #accessibility.",
        sample="Tagged #accessibility and #writing today.",
        category="Contact and web",
        difficulty="basic",
    ),
    # -- Markdown -------------------------------------------------------------
    RegexRecipe(
        name="Markdown headings",
        pattern=r"(?m)^#{1,6} .+$",
        explanation="Finds Markdown heading lines, which start with one to six "
        "hash signs and a space.",
        sample="# Title\nSome text\n## Section",
        category="Markdown",
        difficulty="basic",
    ),
    RegexRecipe(
        name="Bold text",
        pattern=r"\*\*[^*]+\*\*",
        explanation="Finds text wrapped in double asterisks, which Markdown renders as bold.",
        sample="This point is **important** to remember.",
        category="Markdown",
        difficulty="basic",
    ),
    RegexRecipe(
        name="Italic text",
        pattern=r"(?<!\*)\*[^*\n]+\*(?!\*)",
        explanation=(
            "Finds text wrapped in single asterisks, Markdown italics, while "
            "carefully skipping the double asterisks used for bold."
        ),
        sample="An *emphasized* word stands out.",
        category="Markdown",
        difficulty="advanced",
    ),
    RegexRecipe(
        name="Markdown links",
        pattern=r"\[[^\]]+\]\([^)]+\)",
        explanation="Finds Markdown links: text in square brackets followed by an "
        "address in parentheses.",
        sample="See [the guide](https://example.com) for setup.",
        category="Markdown",
        difficulty="intermediate",
    ),
    RegexRecipe(
        name="Markdown images",
        pattern=r"!\[[^\]]*\]\([^)]+\)",
        explanation="Finds Markdown images, which look like links with an "
        "exclamation mark in front.",
        sample="![a sunset photo](sunset.png)",
        category="Markdown",
        difficulty="intermediate",
    ),
    RegexRecipe(
        name="Inline code",
        pattern=r"`[^`\n]+`",
        explanation="Finds text wrapped in single backticks, Markdown's inline code style.",
        sample="Run `pytest -q` before you push.",
        category="Markdown",
        difficulty="basic",
    ),
    RegexRecipe(
        name="Fenced code blocks",
        pattern=r"(?s)```.*?```",
        explanation=(
            "Finds whole fenced code blocks, from one triple-backtick fence "
            "to the next, across multiple lines."
        ),
        sample="Text before.\n```\nprint('hello')\n```\nText after.",
        category="Markdown",
        difficulty="advanced",
    ),
    RegexRecipe(
        name="Blockquote lines",
        pattern=r"(?m)^> .+$",
        explanation="Finds Markdown quotation lines, which begin with a "
        "greater-than sign and a space.",
        sample="> A quoted line of wisdom.\nRegular text.",
        category="Markdown",
        difficulty="basic",
    ),
    RegexRecipe(
        name="Task list items",
        pattern=r"(?m)^[-*] \[[ xX]\] ",
        explanation="Finds Markdown task-list items, checked or unchecked, like '- [x] done'.",
        sample="- [x] Write the draft\n- [ ] Edit the draft",
        category="Markdown",
        difficulty="intermediate",
    ),
    # -- HTML and tags --------------------------------------------------------
    RegexRecipe(
        name="Any HTML tag",
        pattern=r"</?[A-Za-z][^>]*>",
        explanation="Finds any HTML tag, opening or closing, like <p> or </div>.",
        sample="<p>Hello there</p>",
        category="HTML and tags",
        difficulty="basic",
        replace_template="",
        replace_note="Strips the tags and leaves the text between them.",
    ),
    RegexRecipe(
        name="Opening tags only",
        pattern=r"<[A-Za-z][^/>]*>",
        explanation=(
            'Finds opening HTML tags such as <p> or <div class="note">, skipping closing tags.'
        ),
        sample='<div class="note">text</div>',
        category="HTML and tags",
        difficulty="intermediate",
    ),
    RegexRecipe(
        name="Closing tags only",
        pattern=r"</[A-Za-z][^>]*>",
        explanation="Finds closing HTML tags such as </em> or </div>.",
        sample="<em>word</em>",
        category="HTML and tags",
        difficulty="basic",
    ),
    RegexRecipe(
        name="HTML comments",
        pattern=r"(?s)<!--.*?-->",
        explanation="Finds HTML comments, including ones that span several lines.",
        sample="Before <!-- a hidden\nnote --> after.",
        category="HTML and tags",
        difficulty="intermediate",
    ),
    RegexRecipe(
        name="Links with an address",
        pattern=r"<a\s[^>]*href=\"[^\"]*\"[^>]*>",
        explanation="Finds anchor tags that carry an href address in double quotes.",
        sample='<a href="https://example.com">a link</a>',
        category="HTML and tags",
        difficulty="advanced",
    ),
    RegexRecipe(
        name="Character entities",
        pattern=r"&[a-zA-Z]+;|&#\d+;",
        explanation="Finds HTML character entities, both named like &amp; and "
        "numeric like &#8212;.",
        sample="Fish &amp; chips &#8212; delicious.",
        category="HTML and tags",
        difficulty="intermediate",
    ),
    RegexRecipe(
        name="Line break tags",
        pattern=r"<br\s*/?>",
        explanation="Finds break tags in any of their spellings: <br>, <br/>, or <br />.",
        sample="Line one<br/>Line two<br />Line three",
        category="HTML and tags",
        difficulty="basic",
    ),
    RegexRecipe(
        name="Empty elements",
        pattern=r"<(\w+)[^>]*>\s*</\1>",
        explanation="Finds elements with nothing between their opening and closing "
        "tags, like an empty paragraph.",
        sample="<p></p> and <div>  </div> are empty.",
        category="HTML and tags",
        difficulty="advanced",
        replace_template="",
        replace_note="Deletes the empty element entirely.",
    ),
    # -- Punctuation and dialogue ---------------------------------------------
    RegexRecipe(
        name="Straight-quoted dialogue",
        pattern=r"\"[^\"\n]+\"",
        explanation="Finds text wrapped in straight double quotation marks on one line.",
        sample='She said "hello there" and smiled.',
        category="Punctuation and dialogue",
        difficulty="basic",
    ),
    RegexRecipe(
        name="Curly-quoted dialogue",
        pattern="\u201c[^\u201d\n]+\u201d",
        explanation="Finds text wrapped in curly typographic quotation marks, the "
        "kind word processors insert.",
        sample="\u201cCome in,\u201d she said.",
        category="Punctuation and dialogue",
        difficulty="intermediate",
    ),
    RegexRecipe(
        name="Em dashes",
        pattern="\u2014",
        explanation="Finds em dashes, the long dash used for interruptions and asides.",
        sample="Wait\u2014stop right there.",
        category="Punctuation and dialogue",
        difficulty="basic",
    ),
    RegexRecipe(
        name="Double hyphens",
        pattern=r"--",
        explanation="Finds double hyphens, often a stand-in where an em dash belongs.",
        sample="It was -- oddly enough -- very quiet.",
        category="Punctuation and dialogue",
        difficulty="basic",
        replace_template="\u2014",
        replace_note="Converts each double hyphen into a true em dash.",
    ),
    RegexRecipe(
        name="Ellipses",
        pattern="\\.{3}|\u2026",
        explanation="Finds ellipses, whether typed as three periods or as the "
        "single ellipsis character.",
        sample="Well... maybe\u2026 or maybe not.",
        category="Punctuation and dialogue",
        difficulty="intermediate",
    ),
    RegexRecipe(
        name="Repeated exclamation marks",
        pattern=r"!{2,}",
        explanation="Finds two or more exclamation marks in a row.",
        sample="Stop!! Right now!!!",
        category="Punctuation and dialogue",
        difficulty="basic",
        replace_template="!",
        replace_note="Calms each run down to a single exclamation mark.",
    ),
    RegexRecipe(
        name="Missing space after a comma",
        pattern=r",(?=\S)",
        explanation="Finds commas jammed against the next word with no space after them.",
        sample="One,two and three,four need spaces.",
        category="Punctuation and dialogue",
        difficulty="intermediate",
        replace_template=", ",
        replace_note="Adds the missing space after the comma.",
    ),
    RegexRecipe(
        name="Mixed question and exclamation",
        pattern=r"[?!]{2,}",
        explanation="Finds stacked end punctuation like ?! or !!, common in informal drafts.",
        sample="Really?! You finished already!!",
        category="Punctuation and dialogue",
        difficulty="basic",
    ),
    # -- Writing and editing --------------------------------------------------
    RegexRecipe(
        name="Simple passive voice",
        pattern=r"\b(?:was|were) \w+ed\b",
        explanation=(
            "Finds simple passive constructions like 'was thrown' or 'were "
            "counted'. Not every hit is passive, but each is worth a listen."
        ),
        sample="The ball was thrown far; the votes were counted.",
        category="Writing and editing",
        difficulty="intermediate",
    ),
    RegexRecipe(
        name="Filler words",
        pattern=r"\b(?:very|really|quite|rather|just|somewhat)\b",
        explanation="Finds common filler words that usually weaken a sentence.",
        sample="It was really quite good, just a bit slow.",
        category="Writing and editing",
        difficulty="basic",
    ),
    RegexRecipe(
        name="Sentences starting with And or But",
        pattern=r"(?:^|(?<=[.!?] ))(?:And|But)\b",
        explanation="Finds sentences that open with And or But, whether at the start of "
        "the text or after a sentence end.",
        sample="But then it changed. And nobody noticed.",
        category="Writing and editing",
        difficulty="advanced",
    ),
    RegexRecipe(
        name="Very long sentences",
        pattern=r"[A-Z][^.!?]{200,}[.!?]",
        explanation="Finds sentences that run past two hundred characters without a break, "
        "prime candidates for splitting.",
        sample=(
            "Short one. This enormous sentence keeps going and going and going "
            "and going and going and going and going and going and going and "
            "going and going and going and going and going and going and going "
            "and going without ever quite stopping for breath until now."
        ),
        category="Writing and editing",
        difficulty="advanced",
    ),
    RegexRecipe(
        name="Adverbs ending in -ly",
        pattern=r"\b\w+ly\b",
        explanation="Finds words ending in -ly, mostly adverbs. Some hits like "
        "'family' are innocent bystanders.",
        sample="She spoke softly and moved slowly.",
        category="Writing and editing",
        difficulty="basic",
    ),
    RegexRecipe(
        name="Tired opening phrases",
        pattern=r"\b(?:In conclusion|At the end of the day|Needless to say)\b",
        explanation="Finds a few well-worn opening phrases that editors love to cut.",
        sample="In conclusion, the plan worked.",
        category="Writing and editing",
        difficulty="basic",
    ),
    RegexRecipe(
        name="First-person pronouns",
        pattern=r"\b(?:I|me|my|mine)\b",
        explanation="Finds first-person pronouns, handy when a document should stay impersonal.",
        sample="My draft needs work, I think.",
        category="Writing and editing",
        difficulty="basic",
    ),
    RegexRecipe(
        name="Leftover writing notes",
        pattern=r"\b(?:TODO|FIXME|TK)\b",
        explanation="Finds the placeholder notes writers leave for themselves: TODO, "
        "FIXME, and the journalist's TK.",
        sample="Add the citation here TODO before submitting.",
        category="Writing and editing",
        difficulty="basic",
    ),
    # -- OCR and scan cleanup -------------------------------------------------
    RegexRecipe(
        name="Words split across lines",
        pattern=r"(\w+)-\n(\w+)",
        explanation=(
            "Finds words that a scanned page split with a hyphen at the end "
            "of a line, like 'docu-' at one line end and 'ment' on the next."
        ),
        sample="The docu-\nment continues on the next line.",
        category="OCR and scan cleanup",
        difficulty="intermediate",
        replace_template=r"\1\2",
        replace_note="Joins the two halves back into one word and drops the hyphen and line break.",
    ),
    RegexRecipe(
        name="Stray page numbers",
        pattern=r"(?m)^\s*\d{1,4}\s*$",
        explanation="Finds lines that contain nothing but a number, usually page "
        "numbers swept in by the scanner.",
        sample="end of a page\n42\nstart of the next page",
        category="OCR and scan cleanup",
        difficulty="intermediate",
    ),
    RegexRecipe(
        name="Letter l posing as digit one",
        pattern=r"\bl\d+\b",
        explanation="Finds a lowercase letter L stuck to the front of digits, a classic "
        "scan misreading of the digit one.",
        sample="Invoice l23 was attached.",
        category="OCR and scan cleanup",
        difficulty="advanced",
    ),
    RegexRecipe(
        name="Digit zero inside a word",
        pattern=r"(?<=[A-Za-z])0(?=[A-Za-z])",
        explanation="Finds the digit zero sandwiched between letters, where a "
        "scanner mistook the letter O.",
        sample="The w0rd looks broken.",
        category="OCR and scan cleanup",
        difficulty="advanced",
        replace_template="o",
        replace_note="Replaces the stray zero with the letter o.",
    ),
    RegexRecipe(
        name="Orphaned single letters",
        pattern=r"\b[b-hj-z]\b",
        explanation=(
            "Finds single letters standing alone that are not the words 'a' "
            "or 'I', usually debris from a broken word."
        ),
        sample="The c at sat on the mat.",
        category="OCR and scan cleanup",
        difficulty="advanced",
    ),
    RegexRecipe(
        name="Speckled punctuation",
        pattern=r"[.,]{2,}",
        explanation="Finds runs of periods and commas mixed together, the residue "
        "of dust specks on a scan.",
        sample="End of the line,,. next sentence.",
        category="OCR and scan cleanup",
        difficulty="basic",
    ),
    RegexRecipe(
        name="Missing space after a period",
        pattern=r"\.(?=[A-Z])",
        explanation="Finds a period jammed straight against the next sentence's capital letter.",
        sample="It ended.Then it began again.",
        category="OCR and scan cleanup",
        difficulty="intermediate",
        replace_template=". ",
        replace_note="Adds the missing space after the period.",
    ),
    RegexRecipe(
        name="Broken paragraphs",
        pattern=r"(?<=\w)\n(?=\w)",
        explanation=(
            "Finds single line breaks in the middle of running text, where a "
            "scan hard-wrapped a paragraph into short lines."
        ),
        sample="the first half of a sentence\nand its second half",
        category="OCR and scan cleanup",
        difficulty="advanced",
        replace_template=" ",
        replace_note="Rejoins the wrapped lines into flowing text with a space.",
    ),
    # -- Code and identifiers -------------------------------------------------
    RegexRecipe(
        name="CamelCase names",
        pattern=r"\b[a-z]+(?:[A-Z][a-z0-9]*)+\b",
        explanation="Finds camel-case identifiers like getUserName, which start "
        "lowercase with capitalized humps.",
        sample="Call getUserName and maxRetryCount here.",
        category="Code and identifiers",
        difficulty="intermediate",
    ),
    RegexRecipe(
        name="snake_case names",
        pattern=r"\b[a-z]+(?:_[a-z0-9]+)+\b",
        explanation="Finds snake-case identifiers like max_text_chars, lowercase "
        "words joined by underscores.",
        sample="Use max_text_chars and line_count instead.",
        category="Code and identifiers",
        difficulty="intermediate",
    ),
    RegexRecipe(
        name="Hexadecimal numbers",
        pattern=r"\b0x[0-9A-Fa-f]+\b",
        explanation="Finds hexadecimal numbers written with the 0x prefix, like 0xFF00.",
        sample="Mask 0xFF00 was applied to 0x1a2b.",
        category="Code and identifiers",
        difficulty="basic",
    ),
    RegexRecipe(
        name="Hex color codes",
        pattern=r"#(?:[0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})\b",
        explanation="Finds web color codes like #1a2b3c or the short #fff form.",
        sample="Background #1a2b3c with accent #fff.",
        category="Code and identifiers",
        difficulty="intermediate",
    ),
    RegexRecipe(
        name="UUIDs",
        pattern=r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
        explanation="Finds standard UUIDs: five hyphen-separated groups of hexadecimal digits.",
        sample="Session ca1007ed-4c5c-4811-913a-f41cde689295 expired.",
        category="Code and identifiers",
        difficulty="advanced",
    ),
    RegexRecipe(
        name="Version numbers",
        pattern=r"\b\d+\.\d+\.\d+\b",
        explanation="Finds three-part version numbers like 1.0.0 or 2.14.3.",
        sample="Upgrade from 0.9.0 to 1.0.0 now.",
        category="Code and identifiers",
        difficulty="basic",
    ),
    RegexRecipe(
        name="Python function definitions",
        pattern=r"(?m)^\s*def \w+\(",
        explanation="Finds lines where a Python function is defined, even when "
        "indented inside a class.",
        sample="def main():\n    pass",
        category="Code and identifiers",
        difficulty="basic",
    ),
    RegexRecipe(
        name="Quoted string literals",
        pattern=r"'[^'\n]*'|\"[^\"\n]*\"",
        explanation="Finds string literals wrapped in single or double quotes on one line.",
        sample="name = 'quill' and title = \"editor\"",
        category="Code and identifiers",
        difficulty="intermediate",
    ),
    RegexRecipe(
        name="Windows file paths",
        pattern=r"[A-Za-z]:\\(?:[^\\\s]+\\)*[^\\\s]+",
        explanation=(
            "Finds Windows file paths that start with a drive letter, like S:\\QUILL\\readme.md."
        ),
        sample="Open S:\\QUILL\\readme.md before the meeting.",
        category="Code and identifiers",
        difficulty="advanced",
    ),
    # -- Capture and replace --------------------------------------------------
    RegexRecipe(
        name="Swap first and last names",
        pattern=r"\b([A-Z][a-z]+) ([A-Z][a-z]+)\b",
        explanation="Captures two capitalized words, a first and last name, so "
        "they can be reordered.",
        sample="Ada Lovelace wrote the first program.",
        category="Capture and replace",
        difficulty="intermediate",
        replace_template=r"\2, \1",
        replace_note="Rewrites 'Ada Lovelace' as 'Lovelace, Ada' for sorting.",
    ),
    RegexRecipe(
        name="ISO date to US date",
        pattern=r"\b(\d{4})-(\d{2})-(\d{2})\b",
        explanation="Captures the year, month, and day of an ISO date so they can be rearranged.",
        sample="The deadline is 2026-08-05, firm.",
        category="Capture and replace",
        difficulty="intermediate",
        replace_template=r"\2/\3/\1",
        replace_note="Turns 2026-08-05 into 08/05/2026, month first.",
    ),
    RegexRecipe(
        name="Colour to color",
        pattern=r"\b([Cc])olour\b",
        explanation="Captures the first letter of 'colour' so the American spelling "
        "keeps the original capitalization.",
        sample="A Colour swatch and a colour wheel.",
        category="Capture and replace",
        difficulty="intermediate",
        replace_template=r"\1olor",
        replace_note="Changes colour to color, and Colour to Color, preserving the capital.",
    ),
    RegexRecipe(
        name="Markdown link to plain text",
        pattern=r"\[([^\]]+)\]\([^)]+\)",
        explanation="Captures the visible text of a Markdown link so the address can be dropped.",
        sample="Read [the full guide](https://example.com/guide) first.",
        category="Capture and replace",
        difficulty="intermediate",
        replace_template=r"\1",
        replace_note="Keeps just the link text and removes the address.",
    ),
    RegexRecipe(
        name="Double hyphen to em dash",
        pattern=r"(\w) ?-- ?(\w)",
        explanation="Captures the letters on either side of a double hyphen so it "
        "can become a proper em dash.",
        sample="It was -- against all odds -- finished.",
        category="Capture and replace",
        difficulty="advanced",
        replace_template="\\1\u2014\\2",
        replace_note="Replaces the double hyphen and any spaces around it with an em dash.",
    ),
    RegexRecipe(
        name="Rejoin words split across lines",
        pattern=r"(\w+)-\n[ \t]*(\w+)",
        explanation="Captures both halves of a word hyphenated at a line break "
        "so they can be joined.",
        sample="A hyphen-\nated word from a scan.",
        category="Capture and replace",
        difficulty="advanced",
        replace_template=r"\1\2",
        replace_note="Glues the halves back together and removes the hyphen and break.",
    ),
    RegexRecipe(
        name="Last-comma-first to first-last",
        pattern=r"\b([A-Z][a-z]+), ([A-Z][a-z]+)\b",
        explanation="Captures a 'Lastname, Firstname' pair so it can read naturally.",
        sample="Lovelace, Ada wrote it first.",
        category="Capture and replace",
        difficulty="intermediate",
        replace_template=r"\2 \1",
        replace_note="Rewrites 'Lovelace, Ada' as 'Ada Lovelace'.",
    ),
    RegexRecipe(
        name="Add a thousands comma",
        pattern=r"\b(\d)(\d{3})\b",
        explanation="Captures a four-digit number in two pieces so a comma can slide between them.",
        sample="About 5000 people attended.",
        category="Capture and replace",
        difficulty="intermediate",
        replace_template=r"\1,\2",
        replace_note="Turns 5000 into 5,000. Four-digit numbers only; run again for longer ones.",
    ),
    RegexRecipe(
        name="Quote every line",
        pattern=r"(?m)^(.+)$",
        explanation="Captures each whole line so it can be wrapped in quotation marks.",
        sample="alpha\nbeta\ngamma",
        category="Capture and replace",
        difficulty="basic",
        replace_template=r'"\1"',
        replace_note="Wraps each line in double quotation marks.",
    ),
)


def recipes_by_category() -> dict[str, tuple[RegexRecipe, ...]]:
    """Group the catalog by category, preserving both category and recipe order.

    The UI presents a tree of category headings; a stable, spoken-friendly
    order means the library sounds the same on every visit, which is how a
    screen-reader user builds a mental map of it.
    """
    grouped: dict[str, list[RegexRecipe]] = {name: [] for name in CATEGORIES}
    for recipe in RECIPES:
        grouped[recipe.category].append(recipe)
    return {name: tuple(items) for name, items in grouped.items()}
