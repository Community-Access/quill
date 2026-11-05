"""The last three Forms lessons: filling it in, paper and braille, the site.

Split from :mod:`quill.core.tutorials.forms_lessons` to stay under the module
size cap; that module has the example form and the first four lessons, and
assembles all seven.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.tutorials.forms_lessons import FORM_TITLE
from quill.core.tutorials.model import Step, Tutorial

__all__ = ["later_forms_lessons"]


def later_forms_lessons(
    command: Callable[[str], str],
    *,
    track: str,
    surfaces: tuple[str, ...],
    app: str,
) -> tuple[Tutorial, ...]:
    """Lessons five to seven, with the same arguments as the first four."""
    return (
        Tutorial(
            slug="forms-fill-in",
            title="Fill It In Yourself",
            track=track,
            minutes=5,
            surfaces=surfaces,
            summary=(
                "Open your form as a real window and fill it in with your screen "
                "reader, the way a visitor will, before anybody else sees it."
            ),
            steps=(
                Step(
                    title="Open the form as a visitor meets it",
                    body=(
                        "In the Tools menu, open Forms and choose Fill It In Yourself. "
                        f"{app} builds a real window from the same text, with ordinary "
                        "edit boxes, buttons and lists, so you meet what a visitor meets."
                    ),
                    command=command("fill_in"),
                    hear=f"Fill It In Yourself: {FORM_TITLE}, and the first question.",
                ),
                Step(
                    title="Tab through the questions",
                    body=(
                        "Press Tab to move from question to question. Listen for each "
                        "label, and for the word required on the ones that must be "
                        "answered. Type a name and an email address as you go."
                    ),
                    hear="Your name (required), edit. Then Email address (required), edit.",
                    note=(
                        "If a question is hard to understand by ear here, it will be "
                        "hard on the website too. That is the point of this window."
                    ),
                ),
                Step(
                    title="Watch the rule work",
                    body=(
                        "Tab to the Best way to reply group and arrow to Phone. Your "
                        "rule runs as you answer, and you are told about the question it "
                        "brings in, because nothing else would say so."
                    ),
                    hear='"Phone number appears."',
                ),
                Step(
                    title="Change your mind",
                    body=(
                        "Arrow back to Email. The phone number question goes away again, "
                        "exactly as it will for a visitor who chooses Email on the site."
                    ),
                    hear='"Phone number is hidden."',
                ),
                Step(
                    title="Submit, which sends nothing",
                    body=(
                        "Press Submit. Nothing is sent anywhere. Instead, a window shows "
                        "what would have been sent, one question and its answer to a "
                        "line, and anything that still needs an answer."
                    ),
                    hear=(
                        'What Would Be Sent: "Nothing was sent. This is what the form '
                        'would send:", then each question and your answer.'
                    ),
                    note=(
                        "On a form with more than one page, Next first checks this page "
                        "and names any required question still empty, then puts you on it."
                    ),
                ),
                Step(
                    title="Close it",
                    body=(
                        "Press Escape to close What Would Be Sent, and Escape again to "
                        "close the form. Nothing you typed is kept, so you can try it as "
                        "many times as you like."
                    ),
                    hear="Your form document again, where you left it.",
                ),
            ),
            closing=(
                "You have filled in your own form the way your visitors will. Next, "
                "make a copy for people who would rather have it on paper or in braille."
            ),
            then=("forms-paper-and-braille",),
        ),
        Tutorial(
            slug="forms-paper-and-braille",
            title="Save it as large print or braille-ready text",
            track=track,
            minutes=4,
            surfaces=surfaces,
            summary=(
                "Make a large-print copy and a braille-ready copy of your form, from "
                "the same text, without a website."
            ),
            steps=(
                Step(
                    title="Know why there are other copies",
                    body=(
                        "Not everybody fills in a form on a website. Some people want "
                        "it on paper in large print, and some want it in braille. Every "
                        "copy comes from the same form, so it always asks the same "
                        "questions."
                    ),
                    hear="Nothing yet. This step is the reason for the next two.",
                    note=(
                        "These work without a site and even in Safe Mode. If the form "
                        "has a problem it cannot be read past, you are told to run "
                        "Check This Form first, and nothing is saved."
                    ),
                ),
                Step(
                    title="Save a large-print copy",
                    body=(
                        "In the Tools menu, open Forms and choose Save As Large Print. "
                        "The ordinary Save As window opens with a name ending in large "
                        "print. Choose a folder and press Save."
                    ),
                    command=command("save_large_print"),
                    hear=(
                        f'"Saved {FORM_TITLE} large print.docx, a large-print Word '
                        "document, 18 point and up, with 5 questions, lines to write on "
                        'and boxes to check."'
                    ),
                ),
                Step(
                    title="Save a braille-ready copy",
                    body=(
                        "Choose Save As Braille-Ready Text, in Tools, Forms. It writes "
                        "one question to a block, with the choices lettered a, b, c, 40 "
                        "cells to a line, ready to emboss or read on a display."
                    ),
                    command=command("save_braille"),
                    hear=(
                        f'"Saved {FORM_TITLE}.txt, braille-ready text with 5 questions, '
                        'one a block."'
                    ),
                    note=(
                        "With the braille pack installed, you are first asked whether "
                        "to save it as it is or as a braille file in UEB contracted "
                        "braille."
                    ),
                ),
                Step(
                    title="Read the braille copy back",
                    body=(
                        "Open the .txt file you just saved, as you open any document. "
                        "Arrow through it to hear one question to a block, so you know "
                        "what the person reading it will find."
                    ),
                    hear=(
                        "The form's title, then each question, numbered, with its choices lettered."
                    ),
                    note=(
                        "Save As Web Page and Save As Word Document, beside these in "
                        "Tools, Forms, make the other two copies the same way."
                    ),
                ),
            ),
            closing=(
                "One form, and a copy for whoever needs one. The last lesson puts the "
                "form on your website."
            ),
            then=("forms-publish-and-responses",),
        ),
        Tutorial(
            slug="forms-publish-and-responses",
            title="Publish it and read the responses",
            track=track,
            minutes=7,
            surfaces=surfaces,
            summary=(
                "Publish your form to a WordPress site running QUILL Accessible Forms, "
                "put it on a page, try it there, and read what people send."
            ),
            steps=(
                Step(
                    title="Know what the site needs",
                    body=(
                        "Publishing needs a WordPress site you have connected, with the "
                        "QUILL Accessible Forms plugin installed and switched on. The "
                        "WordPress lessons show how to connect a site."
                    ),
                    hear="Nothing yet. This step is what the rest need.",
                    note=(
                        "Without the plugin you hear that the command needs QUILL "
                        "Accessible Forms on the site, and to install and activate it "
                        "there. Publishing and Responses are off in Safe Mode."
                    ),
                ),
                Step(
                    title="Publish the form",
                    body=(
                        f"With {FORM_TITLE} in front, open Forms in the Tools menu and "
                        "choose Publish Form. With more than one site, you choose which "
                        "one first."
                    ),
                    command=command("publish"),
                    hear="Publish Form, and Publish as, on Live.",
                ),
                Step(
                    title="Choose live or draft, then say yes",
                    body=(
                        "Live means people can fill it in wherever it is placed. Draft "
                        "puts it on the site where nobody can use it yet. Press Enter on "
                        "Live, and then on Publish when the question asks."
                    ),
                    hear=(
                        f'"Published {FORM_TITLE} on" your site, its form number, '
                        '"live. Insert Form Into Page puts it on a page."'
                    ),
                    note=(
                        "Publishing again later updates the same form. If somebody "
                        "changed it on the site since, you are asked first, and the "
                        "site's copy is kept on this computer."
                    ),
                ),
                Step(
                    title="Put it on a page",
                    body=(
                        "Open a page with Open Page or Post, in File, WordPress, and put "
                        "the cursor where the form goes. Choose Insert Form Into Page in "
                        "Tools, Forms, pick your form, then Publish or Update the page."
                    ),
                    command=command("insert_into_page"),
                    hear=(
                        f'"Inserted the {FORM_TITLE} form", and that it shows on the '
                        "page once the page is sent."
                    ),
                ),
                Step(
                    title="Try it on the site",
                    body=(
                        "Back in your form, choose Test on Site, in Tools, Forms. It "
                        "opens the page that shows your form in your web browser, so you "
                        "can fill it in for real and send yourself a response."
                    ),
                    command=command("test_on_site"),
                    hear='"Opened" the page\'s name "on" your site, "where the form is."',
                ),
                Step(
                    title="Read what people sent",
                    body=(
                        "Choose Responses, in Tools, Forms. With your published form in "
                        "front it goes straight to that form's responses, newest first. "
                        "Press Enter on one to read it, a question and its answer a line."
                    ),
                    command=command("responses"),
                    hear=(
                        f"Responses to {FORM_TITLE}, and each response: its number, when "
                        "it was sent, and who sent it."
                    ),
                    note=(
                        "Responses are people's personal details. They are read only "
                        "while this window is open and saved only where you choose, with "
                        "Export to CSV or Export to Word."
                    ),
                ),
            ),
            closing=(
                "Your form is live, and you can hear every answer it brings in. The "
                "first time you use a site in a session, you are also told how many "
                "new responses are waiting."
            ),
        ),
    )
