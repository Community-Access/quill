"""BFL spellings for model features BAF's language guide does not have yet.

17a.15 point 3: every model feature has a BFL spelling. These are QUILL's
proposals, read by :mod:`bfl_read` and written by :mod:`bfl_write`; BAF's PHP
side adopts them in its own branch. Each is chosen so that BAF's *current*
parser skips it harmlessly instead of misreading it (an unknown modifier, a
comment, or a word it does not know).

``EXTENSIONS`` maps each feature to an example, for Insert Field's help and
for the shared conformance suite.
"""

from __future__ import annotations

EXTENSIONS: dict[str, str] = {
    "version": "// bfl-version 1",
    "condition, full language": 'if #type is "business" or #type is "charity"',
    "condition, one of": 'if #country is one of ("US", "CA")',
    "condition, dates": "if #start is within 7 days",
    "condition on a field": "  @when #age >= 18",
    "condition on a page": 'page "Business details"\n  @when #type is "business"',
    "condition on a section": 'section "Company"\n  @when #type is "business"',
    "calculation": "  @calculate #quantity * #price",
    "smart default, any expression": "  @smart_default today + 7",
    "quiz score for a field": '  @score #capital is "paris"',
    "quiz score for a choice": "  @choice_score paris 1",
    "quiz outcome": 'outcome "You passed"\n  @when quiz.score >= 3',
    "translation": '  @translate fr label "Adresse courriel"',
    "translation of a choice": '  @translate fr choice email "Par courriel"',
    "form settings": '  @submit_label "Sign me up"\n  @success_message "Thank you"',
    "any other setting": '  @setting "width" "\\"half\\""',
    "repeater fields": 'repeater #children "Children" {\n  text #child_name "Name"\n}',
    "new field types": 'toggle #news "Newsletter"\nnps #recommend "Would you recommend us?"',
}
