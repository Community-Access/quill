"""Seven Forms lessons, the same in QUILL and QUILL Lite.

Both editors reach Forms through one table (``quill/core/forms/menu.py``) and
one set of handlers (``quill/ui/forms_commands.py``), so the lessons are
written once, the way the WordPress lessons are. Each editor passes a function
that turns a Forms row's short name (``"check"``) into its own command id, its
Save command, and its name.

The Forms commands have no keys (rule 9, and the reasons in ``forms/menu.py``),
so no step carries a literal key: each one teaches the menu path, and the
command it names lets the lesson offer Try It.

The example is one small form built up across the lessons: "Ask us anything",
started from the Contact form template, with a choose-one question and a phone
number that appears only when somebody asks to be phoned. Every sentence the
lessons say you will hear is one the commands really say
(``quill/ui/forms_*.py``), worked out from that form.

The wording follows :mod:`quill.core.tutorials.model`: one action a step, the
reason as well as the instruction, what you should hear, and no key promised in
prose.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.tutorials.model import Step, Tutorial

__all__ = ["FORM_FILE", "FORM_TITLE", "forms_lessons"]

#: The form every lesson builds on.
FORM_TITLE = "Ask us anything"
FORM_FILE = "Ask us anything.bfl"


def forms_lessons(
    command: Callable[[str], str],
    *,
    save: str,
    track: str,
    surfaces: tuple[str, ...],
    app: str,
) -> tuple[Tutorial, ...]:
    """The seven lessons: four here, three in :mod:`forms_lessons_more`.

    *command* maps a row's short name in ``forms/menu.py`` (``"rules"``) to
    this editor's command id; *save* is the editor's own Save command; *app* is
    the editor's name as its lessons say it.
    """
    from quill.core.tutorials.forms_lessons_more import later_forms_lessons

    return (
        Tutorial(
            slug="forms-start",
            title="Start a form from a template",
            track=track,
            minutes=5,
            surfaces=surfaces,
            summary=(
                "Start a contact form from a template, save it, and read it through, "
                "first as text and then as an outline of its questions."
            ),
            steps=(
                Step(
                    title="Know what a form is here",
                    body=(
                        "A form in "
                        f"{app} is a short plain text document: a title, some "
                        "questions, their choices and a few rules, written in BITS "
                        "Accessible Forms' form language. You never have to learn the "
                        "language, because the Forms commands write it for you."
                    ),
                    hear="Nothing yet. This step is the idea the rest build on.",
                    note=(
                        "Forms is on in every feature profile except Essential. If "
                        "there is no New Form in the File menu, switch Forms on in "
                        "Profiles and Features."
                    ),
                ),
                Step(
                    title="Open New Form",
                    body=(
                        "In the File menu, choose New Form. It sits with the other New "
                        "commands. Nothing is written anywhere until you have chosen "
                        "where to save it."
                    ),
                    command=command("new_form"),
                    hear="The New Form dialog, on Title.",
                    note=(
                        "No Forms command has a shortcut key, because you will not "
                        "write forms every day. The Command Palette finds every one of "
                        "them: type form."
                    ),
                ),
                Step(
                    title="Give it a title and a template",
                    body=(
                        f"Type {FORM_TITLE} in Title. That is the name your visitors "
                        "will see. Tab to Template and arrow down to Contact form. "
                        "There are seven templates, and each one is a few questions you "
                        "can change."
                    ),
                    hear="Template, and Contact form: Name, email address and a message.",
                ),
                Step(
                    title="Save the new form",
                    body=(
                        "Press Next. The ordinary Save As window opens with a file name "
                        f"made from your title, {FORM_FILE}. Choose a folder you will "
                        "find again and press Save. The new form opens straight away."
                    ),
                    hear=f'"Saved {FORM_FILE}, a contact form with 3 questions."',
                    note=(
                        "A form file ends in .bfl. It is ordinary text, so you can open "
                        "it in any text editor too."
                    ),
                ),
                Step(
                    title="Read it through as text",
                    body=(
                        "Arrow down through the form from the top. Each question starts "
                        "on a line of its own: its kind, its id after a number sign, and "
                        "its label in quotes. The indented lines under it are its "
                        "settings, such as required."
                    ),
                    hear='"text #name", then "Your name" in quotes, then "@required".',
                    note=(
                        "Because it is text, Find, spelling, copy and paste all work "
                        "here, and you can type a question yourself if you would rather."
                    ),
                ),
                Step(
                    title="Hear it as an outline",
                    body=(
                        "In the View menu, choose Form Outline. It lists every page and "
                        "question in order, each one read like a sentence, so you can "
                        "hear the shape of the form without the form language."
                    ),
                    command=command("outline"),
                    hear=(
                        '"Page 1, 3 questions", then "Your name, text field, required, '
                        'with an autofill hint, page 1".'
                    ),
                    note=(
                        "Enter takes you to the selected question in the document. "
                        "Escape closes the outline."
                    ),
                ),
            ),
            closing=(
                "You have a real form, saved on this computer, and you have heard it "
                "two ways. Next, give it a question of your own."
            ),
            then=("forms-add-questions",),
        ),
        Tutorial(
            slug="forms-add-questions",
            title="Add questions",
            track=track,
            minutes=5,
            surfaces=surfaces,
            summary=(
                "Add a choose-one question and a phone number question to your form, "
                "each from a short window that asks only what that kind needs."
            ),
            steps=(
                Step(
                    title="Put the cursor where it goes",
                    body=(
                        "Move to the line that says Your message. A new question goes "
                        "in straight after the one your cursor is on, so this one will "
                        "come last in the form."
                    ),
                    hear='"textarea #message", then "Your message" in quotes.',
                ),
                Step(
                    title="Open Form Field",
                    body=(
                        "In the Insert menu, choose Form Field. A list of every kind of "
                        "question opens, each row saying what a visitor meets. Section "
                        "and Page break are at the top."
                    ),
                    command=command("insert_field"),
                    hear="The Insert Form Field dialog, and the Kind of question list.",
                ),
                Step(
                    title="Find the kind you want",
                    body=(
                        "Tab to Search, type choose, and press Enter to narrow the list. "
                        "Arrow to Choose one and press Enter. A visitor meets it as a "
                        "group of buttons, and picks only one."
                    ),
                    hear="Choose one: Choose one from a group of buttons.",
                ),
                Step(
                    title="Write the question and its choices",
                    body=(
                        "In the next window, type Best way to reply in Label. Tab to "
                        "Choices, one per line, and type Email, press Enter, then type "
                        "Phone. Press Insert."
                    ),
                    hear='"Inserted Best way to reply, choose one."',
                    note=(
                        "Help text is a sentence a screen reader reads with the "
                        "question. Leave Id empty and the id is made from the label."
                    ),
                ),
                Step(
                    title="Add a phone number question",
                    body=(
                        "With the cursor still on Best way to reply, choose Form Field "
                        "again. This time pick Phone number, type Phone number in "
                        "Label, and press Insert. Leave Required unchecked: only some "
                        "people will want a call."
                    ),
                    command=command("insert_field"),
                    hear='"Inserted Phone number, phone number."',
                ),
                Step(
                    title="Save your work",
                    body=(
                        "Save as you always do. A form saves like any other document, "
                        "on this computer, and nothing is sent anywhere. Each insert is "
                        "also one step that Undo takes back."
                    ),
                    command=save,
                    hear="The usual saved message.",
                ),
            ),
            closing=(
                "The form now asks five questions. The phone number is asked of "
                "everybody, which is not quite right. A rule fixes that."
            ),
            then=("forms-rules",),
        ),
        Tutorial(
            slug="forms-rules",
            title="Add a rule and hear it as a sentence",
            track=track,
            minutes=5,
            surfaces=surfaces,
            summary=(
                "Make the phone number appear only for somebody who asked to be phoned, "
                "built from three choices and read back to you as a sentence."
            ),
            steps=(
                Step(
                    title="Open Form Rules",
                    body=(
                        "In the Format menu, choose Form Rules. It lists every rule in "
                        "the form as a sentence. This form has none yet, so the list is "
                        "empty."
                    ),
                    command=command("rules"),
                    hear="The Form Rules window, and the Rules list.",
                ),
                Step(
                    title="Say which question it listens to",
                    body=(
                        "Press Add Rule. In When this question, choose Best way to "
                        "reply. Leave Is on is. In This answer, type Phone, the choice's "
                        "own words; capitals do not matter."
                    ),
                    hear="When this question, and Best way to reply.",
                    note=(
                        "A choice is stored as its words in small letters, with a hyphen "
                        "for each space: Large print is large-print. QUILL turns what you "
                        "type into that, so the rule matches however you write it."
                    ),
                ),
                Step(
                    title="Say what it does",
                    body=(
                        "Tab to Then and leave it on Show. In To this question or page, "
                        "choose Phone number. Read that back to yourself: when Best way "
                        "to reply is Phone, show Phone number."
                    ),
                    hear="To this question or page, and Phone number.",
                    note=(
                        "Then can also hide, require, make optional, enable, disable, "
                        "or skip to a page."
                    ),
                ),
                Step(
                    title="Add it, and hear the sentence",
                    body=(
                        "Press Add Rule. The rule is written into the form for you, and "
                        f"{app} reads it back as the sentence it is, so you can hear "
                        "whether it says what you meant."
                    ),
                    hear='"Show Phone number when Best way to reply is Phone."',
                    note=(
                        "If you know the form language, Or write the condition yourself "
                        "takes a whole condition instead. It is checked before anything "
                        "is written, and you are told what is wrong if it does not read."
                    ),
                ),
                Step(
                    title="Find it in the form",
                    body=(
                        "The new rule is in the Rules list. Press Go to It to close the "
                        "window and land on Phone number. The line under it, starting "
                        "@when, is your rule in the form language."
                    ),
                    hear='"phone #phone", then "Phone number" in quotes.',
                    note=(
                        "Edit changes a rule's condition, and Remove takes one out after "
                        "asking. Undo in the document takes back either."
                    ),
                ),
            ),
            closing=(
                "Rules are the part of a form that is hardest to see on a web page. "
                "Here every one is a sentence you can read. Next, let the form be "
                "checked."
            ),
            then=("forms-check",),
        ),
        Tutorial(
            slug="forms-check",
            title="Check This Form",
            track=track,
            minutes=4,
            surfaces=surfaces,
            summary=(
                "Find what would make the form hard to fill in, go straight to it, fix "
                "it, and check again."
            ),
            steps=(
                Step(
                    title="Run the check",
                    body=(
                        "In the Tools menu, open Forms and choose Check This Form. It "
                        "looks for anything that would make the form hard to fill in, "
                        "such as a question with no label, and lists the most serious "
                        "first."
                    ),
                    command=command("check"),
                    hear=(
                        '"Phone number has no autofill hint, so the browser cannot fill '
                        'it in. The hint is tel."'
                    ),
                    note=(
                        "An autofill hint lets a visitor's browser fill in their own "
                        "phone number, which saves typing and mistakes."
                    ),
                ),
                Step(
                    title="Know the On the site today lines",
                    body=(
                        "Arrow down the Findings list. A line that starts On the site "
                        "today is not a mistake in your form. It says where the forms "
                        "plugin on a website reads your form differently today, so you "
                        "know before you publish."
                    ),
                    hear='Lines starting "On the site today", if there are any.',
                ),
                Step(
                    title="Go to the finding",
                    body=(
                        "Arrow back to the autofill finding and press Go to It. The "
                        "window closes and your cursor is on the Phone number question, "
                        "ready to fix."
                    ),
                    hear='"phone #phone", then "Phone number" in quotes.',
                ),
                Step(
                    title="Fix it",
                    body=(
                        "Go to the end of the last indented line under Phone number and "
                        'press Enter. Type two spaces, then @autocomplete "tel", with '
                        "the quotes. That is the hint the finding asked for."
                    ),
                    hear='Your new line read back: "@autocomplete", then "tel" in quotes.',
                    note=(
                        "Suggest Autofill Hints, in Tools, Forms, asks your chosen AI to "
                        "suggest them all at once. It says what it sends first."
                    ),
                ),
                Step(
                    title="Check again",
                    body=(
                        "Choose Check This Form once more, in Tools, Forms. The autofill "
                        "finding has gone. When there is nothing to fix at all, there is "
                        "no list, just one sentence."
                    ),
                    command=command("check"),
                    hear=(
                        "Only On the site today lines, or, with none of those, "
                        '"Check This Form found nothing to fix."'
                    ),
                ),
            ),
            closing=(
                "Check This Form is worth running every time you change a form, and "
                "always before you publish one. Next, fill it in yourself."
            ),
            then=("forms-fill-in",),
        ),
    ) + later_forms_lessons(command, track=track, surfaces=surfaces, app=app)
