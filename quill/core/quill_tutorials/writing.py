"""QUILL, track 2: writing and editing.

Five lessons about the work itself: selecting and moving text without a mouse,
finding and replacing at every level of ambition, structure and formatting,
spelling and words, and the one structure plain caret movement handles badly.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="select-and-move",
        title="Select, mark, and move text",
        track="writing",
        minutes=6,
        surfaces=("QUILL",),
        summary=(
            "Selection that grows by structure rather than by character, marks "
            "you can return to, and a clipboard with twelve slots instead of one."
        ),
        steps=(
            Step(
                title="Grow a selection by meaning",
                body=(
                    "Expand Selection takes the next larger structure -- word, "
                    "then sentence, then paragraph, then block. It is far more "
                    "predictable by ear than holding Shift and counting, and "
                    "Shrink Selection goes back."
                ),
                command="edit.expand_selection",
                hear="What is now selected, and how much of it.",
            ),
            Step(
                title="Select exactly one paragraph or block",
                body=(
                    "Select Paragraph and Select Block take the unit you mean in "
                    "one keystroke. Say Selected reads back what you have, which "
                    "is the check worth making before a destructive edit."
                ),
                command="edit.select_paragraph",
                hear="The paragraph, then its size.",
            ),
            Step(
                title="Drop a mark and come back to it",
                body=(
                    "Set Mark remembers where you are; Exchange Point and Mark "
                    "jumps between the mark and the cursor, which is how you "
                    "select across a long distance without holding anything down. "
                    "Named marks survive for as long as you want them."
                ),
                command="edit.set_mark",
                hear="Mark set -- and, on the exchange, where you landed.",
            ),
            Step(
                title="Use more than one clipboard",
                body=(
                    "The copy tray has twelve slots. Copy to a numbered slot, "
                    "paste from a numbered slot, or open the tray and search it. "
                    "It is the answer to gathering five quotes from one document "
                    "into another without a round trip each time."
                ),
                command="edit.open_copy_tray",
                hear="The tray, with what each slot holds.",
                note=(
                    "Clear All Tray Slots asks first and defaults to No, like "
                    "every destructive question in QUILL."
                ),
            ),
            Step(
                title="Paste something that came from the web",
                body=(
                    "Magic Paste and Paste HTML as Markdown clean up what the "
                    "clipboard actually contains, rather than dropping styled "
                    "soup into your document. Copy With Source does the reverse "
                    "courtesy when you are the one quoting."
                ),
                command="edit.magic_paste",
                hear="What it pasted, and what it cleaned up.",
            ),
            Step(
                title="Tidy lines in place",
                body=(
                    "Quote Lines, Unquote Lines, Reverse Lines, Keep Unique "
                    "Lines, Number Lines and Trim Blank Lines each do one obvious "
                    "thing to the selection. They are the small tools that save "
                    "an hour when a document arrives badly."
                ),
                command="edit.quote_lines",
                hear="How many lines it changed.",
            ),
        ),
        closing=(
            "Selection by structure, marks for distance, twelve clipboards. None "
            "of it needs a mouse and none of it needs you to count characters."
        ),
        then=("find-and-replace",),
    ),
    Tutorial(
        slug="find-and-replace",
        title="Find, replace, and search across files",
        track="writing",
        minutes=6,
        surfaces=("QUILL",),
        summary=(
            "The four levels: find here, find every match, replace with care, and "
            "search or replace across a folder of files."
        ),
        steps=(
            Step(
                title="Find, and find again",
                body=(
                    "Find opens the search; Find Next and Find Previous walk the "
                    "matches. QUILL keeps your search history, so a search you run "
                    "often gets shorter every time."
                ),
                command="edit.find",
                hear="The match, with its line -- or a plain statement that there are none.",
            ),
            Step(
                title="See every match at once",
                body=(
                    "Find All Matches opens a summary rather than making you walk "
                    "the document. It is the right tool when the question is how "
                    "many and where rather than take me to the next one."
                ),
                command="edit.find_all_matches",
                hear="How many matches, and the list of them.",
            ),
            Step(
                title="Choose the kind of search",
                body=(
                    "Plain text, whole word, wildcard, or regular expression. The "
                    "Regex Helper explains the syntax when you need it, which is "
                    "the difference between a powerful search and one you are "
                    "afraid of."
                ),
                hear="The mode you chose, read back.",
            ),
            Step(
                title="Replace deliberately",
                body=(
                    "Replace steps through and asks; Replace All does not. Both "
                    "say how many they changed, and Undo takes the whole "
                    "operation back as one action rather than one edit at a time."
                ),
                command="edit.replace",
                hear="Each replacement, or the count at the end.",
            ),
            Step(
                title="Search a whole folder",
                body=(
                    "Search in Files answers where did I write that when you "
                    "cannot remember which document it was in. Replace in Files is "
                    "its counterpart, and it is worth doing on a copy the first "
                    "time you use it."
                ),
                command="tools.search_in_files",
                hear="The matches, grouped by file.",
            ),
            Step(
                title="Learn the one that is not a search",
                body=(
                    "Go to Anything reaches files, headings and places rather "
                    "than text. When you know the *name* of the thing you want, it "
                    "is faster than any search."
                ),
                command="navigate.go_to_anything",
                hear="Matches grouped by what they are.",
            ),
        ),
        closing=(
            "Find for here, Find All for how many, Search in Files for which "
            "document. The regex helper is there when the pattern gets hard."
        ),
        then=("structure-and-format",),
    ),
    Tutorial(
        slug="structure-and-format",
        title="Structure and formatting",
        track="writing",
        minutes=6,
        surfaces=("QUILL",),
        summary=(
            "Headings, lists, emphasis and sections -- and Describe Formatting, "
            "which tells you what is actually on the text under your cursor."
        ),
        steps=(
            Step(
                title="Make a heading",
                body=(
                    "Heading 1 through Heading 6 set the level directly, and "
                    "Increase and Decrease Heading Level move an existing one. "
                    "Headings are what the outline, Quick Nav and the structure "
                    "keys all navigate by, so they earn their keystroke twice."
                ),
                command="format.heading_2",
                hear="The heading level, and the line it applied to.",
            ),
            Step(
                title="Emphasise something",
                body=(
                    "Bold and Italic do what they say, in the document's own "
                    "language: Markdown gets Markdown, HTML gets tags, rich text "
                    "gets real formatting. Bold means bold -- QUILL speaks your "
                    "document's format rather than imposing one."
                ),
                command="format.bold",
                hear="Bold on, and what it applied to.",
            ),
            Step(
                title="Ask what formatting is here",
                body=(
                    "Describe Formatting says what is actually on the text under "
                    "the cursor. It is the one-shot answer to why does this line "
                    "sound different, and double-pressing it opens the Spoken Echo "
                    "so you can read the answer rather than catch it."
                ),
                command="format.describe_formatting",
                hear="Every attribute on the text, in one pass.",
            ),
            Step(
                title="Make a list, and nest it",
                body=(
                    "Toggle Bullet List and Toggle Numbered List convert the "
                    "selection. On a Markdown list item, Tab and Shift+Tab nest "
                    "and promote the item, and each move is spoken -- so you hear "
                    "the indent even though the caret does not move."
                ),
                command="format.toggle_bullet_list",
                hear="The list applied, then the new depth as you nest.",
            ),
            Step(
                title="Move a whole section",
                body=(
                    "Move Section Up and Move Section Down move a heading and "
                    "everything under it. Reordering a document by its structure "
                    "rather than by cut and paste is the difference between an "
                    "edit and an afternoon."
                ),
                command="format.move_section_up",
                hear="Where the section moved to.",
            ),
            Step(
                title="Insert the awkward things",
                body=(
                    "Insert Link, Insert Table, Insert Snippet, Insert Emoji, "
                    "Insert Special Character and Insert Equation each open a "
                    "small, keyboard-first window rather than expecting you to "
                    "type syntax from memory."
                ),
                command="edit.insert_link",
                hear="The window, with focus in its first field.",
            ),
            Step(
                title="Decide what Tab does",
                body=(
                    "By default Tab indents the line and Shift+Tab outdents. If "
                    "you would rather Tab typed a literal tab character, the Tab "
                    "Mode chord switches it, the status bar shows which mode you "
                    "are in, and Shift+Tab still outdents either way."
                ),
                keys=("Ctrl+Shift+Grave, U",),
                hear="The new mode, and afterwards the depth on every indent.",
            ),
        ),
        closing=(
            "Structure first, emphasis second. Describe Formatting is the key to "
            "keep: it turns a guess into a fact."
        ),
        then=("words-and-spelling",),
    ),
    Tutorial(
        slug="words-and-spelling",
        title="Spelling, words, and the thesaurus",
        track="writing",
        minutes=5,
        surfaces=("QUILL",),
        summary=(
            "Spell check as a list rather than a march, the ranked view for a "
            "long document, word count, and the thesaurus."
        ),
        steps=(
            Step(
                title="Check one word",
                body=(
                    "Spell Check Word at Cursor answers the question you actually "
                    "have -- is this one right -- without starting a pass through "
                    "the whole document."
                ),
                command="tools.spell_check_word_at_cursor",
                hear="The verdict, and suggestions if it is wrong.",
            ),
            Step(
                title="Get the misspellings as a list",
                body=(
                    "The misspelling list is a list you can arrow through and "
                    "jump from, rather than a modal march through the document. "
                    "For a long piece the ranked view puts the ones that occur "
                    "most first, which is usually the same word thirty times."
                ),
                command="tools.misspelling_list",
                hear="How many, then each one with its context.",
            ),
            Step(
                title="Walk them one at a time when you want to",
                body=(
                    "Next Misspelling and Previous Misspelling are the classic "
                    "movement, and they exist alongside the list rather than "
                    "instead of it. Use whichever suits the document."
                ),
                command="tools.next_misspelling",
                hear="The word, and the line it is on.",
            ),
            Step(
                title="Count what you have written",
                body=(
                    "Word Count reports the document or the selection. Document "
                    "Summary is the bigger answer -- what this document is, how "
                    "long, and how it is shaped."
                ),
                command="tools.word_count",
                hear="Words, characters, and the rest.",
            ),
            Step(
                title="Find a better word",
                body=(
                    "The thesaurus works on the word under the cursor and offers "
                    "replacements you can apply straight into the document, rather "
                    "than a list you have to copy out of."
                ),
                command="tools.thesaurus",
                hear="The word, then its alternatives.",
            ),
            Step(
                title="Know what an AI check adds",
                body=(
                    "AI Spell Check and Check Grammar with AI are separate "
                    "commands, and they never apply anything automatically: the "
                    "grammar check lists corrections as original phrase, arrow, "
                    "corrected phrase, and a reason, and you apply what you agree "
                    "with."
                ),
                command="tools.ai_grammar_style",
                hear="Each correction with its reason, and nothing changed yet.",
            ),
        ),
        closing=(
            "The list before the march, the ranked list for a long document, and "
            "an AI pass only when you ask for one."
        ),
        then=("tables-by-ear",),
    ),
    Tutorial(
        slug="tables-by-ear",
        title="Tables, by ear",
        track="writing",
        minutes=4,
        surfaces=("QUILL",),
        summary=(
            "The one structure plain caret movement handles badly, and the six keys that fix it."
        ),
        steps=(
            Step(
                title="Understand the problem",
                body=(
                    "Arrowing along a line in a table tells you the characters and "
                    "never the shape. You can read every word of a row and still "
                    "not know which column you are in, which is why tables get "
                    "their own movement."
                ),
                hear="Nothing: this is why the next six steps exist.",
            ),
            Step(
                title="Move along a row",
                body=(
                    "Next Cell and Previous Cell move one cell along the row, and "
                    "each landing says where you are before it says what is there: "
                    "Row 2 of 6, column 3 of 5: Portland."
                ),
                command="table.next_cell",
                hear="The position, then the contents.",
            ),
            Step(
                title="Move down a column",
                body=(
                    "Cell Below and Cell Above move down and up the column. "
                    "Reading a column is how you compare values, and it is exactly "
                    "what character movement cannot do."
                ),
                command="table.cell_below",
                hear="The new row and column, then the cell.",
            ),
            Step(
                title="Jump to the edges",
                body=(
                    "Row Start and Row End go to the ends of the row; First Cell "
                    "and Last Cell go to the ends of the whole table. Four keys "
                    "for the four questions you actually ask."
                ),
                command="table.row_start",
                hear="The cell you landed on, with its position.",
            ),
            Step(
                title="Hear the difference between an edge and a wall",
                body=(
                    "No more cells at the end of a row, No more rows at the "
                    "bottom of a column, and No more cells, end of table on the "
                    "very last cell. That is the difference between this row stops "
                    "here and the table stops here."
                ),
                hear="One of those three sentences, rather than silence.",
                note=(
                    "An empty cell is announced as blank rather than by silence, "
                    "and the keys are harmless outside a table: QUILL simply says "
                    "Not in a table."
                ),
            ),
            Step(
                title="Know that a Word table behaves the same",
                body=(
                    "A .docx table is brought in as a real table laid out as "
                    "Markdown rows, so the same keys, positions and edges apply to "
                    "a table you opened from Word as to one you typed. A cell "
                    "containing a pipe character stays one cell."
                ),
                hear="The same position announcements, in an imported document.",
            ),
        ),
        closing=(
            "Six keys, and every landing says where you are. Tables stop being "
            "the thing you dread in somebody else's document."
        ),
    ),
)
