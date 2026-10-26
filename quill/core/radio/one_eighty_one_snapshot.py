"""181.FM's station list as it stood on 2026-10-25 (generated, not hand-edited).

The fallback :mod:`quill.core.radio.one_eighty_one` uses when the live list
cannot be read and no cached copy exists: the network never browses empty.
Regenerate from a live parse when 181.FM changes its line-up.
"""

from __future__ import annotations

#: ``(genre, ((station, mount), ...))`` in the publisher's order.
SNAPSHOT: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    (
        "Oldies",
        (
            ("Classic Hits 181", "181-greatoldies"),
            ("Good Time Oldies", "181-goodtime"),
            ("Mellow Gold", "181-mellow"),
            ("Soul", "181-soul"),
            ("Beatles", "181-beatles"),
            ("Super 70s", "181-70s"),
        ),
    ),
    (
        "80's Decade",
        (
            ("Awesome 80's", "181-awesome80s"),
            ("Lite 80's", "181-lite80s"),
            ("80's Country", "181-80scountry"),
            ("80's Lite RnB", "181-80sliternb"),
            ("80's RnB", "181-80srnb"),
            ("80's Hairband", "181-hairband"),
        ),
    ),
    (
        "90's Decade",
        (
            ("Lite 90's", "181-lite90s"),
            ("90's Lite RnB", "181-90sliternb"),
            ("90's Alternative", "181-90salt"),
            ("90's RnB", "181-90srnb"),
            ("Star 90's", "181-star90s"),
            ("90's Country", "181-90scountry"),
            ("90's Dance", "181-90sdance"),
        ),
    ),
    (
        "Pop",
        (
            ("Power 181 (Top 40)", "181-power"),
            ("Power 181 [E]", "181-powerexplicit"),
            ("The Office", "181-office"),
            ("The Mix", "181-themix"),
            ("The Point", "181-thepoint"),
            ("Old School HipHop/RnB", "181-oldschool"),
            ("Smooth AC", "181-smoothac"),
            ("UK top 40", "181-uktop40"),
            ("The Heart (Love Songs)", "181-heart"),
            ("The Vibe of Vegas", "181-vibe"),
        ),
    ),
    (
        "Rock",
        (
            ("The Buzz (Alt. Rock)", "181-buzz"),
            ("Classic Buzz (Alt)", "181-classicbuzz"),
            ("The Eagle (Classic)", "181-eagle"),
            ("Rock 181", "181-rock"),
            ("Rock 40 (Rock & Roll)", "181-rock40"),
            ("80's Hairband", "181-hairband"),
            ("Yacht Rock", "181-yachtrock"),
            ("Chloe @181.FM", "181-chloe"),
            ("The Point", "181-thepoint"),
            ("The Rock! (Hard Rock)", "181-hardrock"),
        ),
    ),
    (
        "Country",
        (
            ("Kickin' Country", "181-kickincountry"),
            ("Real Country", "181-realcountry"),
            ("Highway 181", "181-highway"),
            ("80's Country", "181-80scountry"),
            ("90's Country", "181-90scountry"),
            ("Front Porch (Bluegrass)", "181-frontporch"),
        ),
    ),
    (
        "Urban",
        (
            ("The Beat (HipHop/R&B)", "181-beat"),
            ("Classic R&B", "181-classicrnb"),
            ("The Box (Urban)", "181-thebox"),
            ("True R&B", "181-rnb"),
            ("Soul", "181-soul"),
            ("Party 181", "181-party"),
            ("Jammin 181", "181-jammin"),
            ("80's RnB", "181-80srnb"),
            ("80's Lite RnB", "181-80sliternb"),
            ("Old School HipHop/RnB", "181-oldschool"),
        ),
    ),
    (
        "Dance",
        (
            ("Energy 98", "181-energy98"),
            ("Classic Energy", "181-classicenergy"),
            ("Chilled Out", "181-chilled"),
            ("Energy 93", "181-energy93"),
            ("Studio 181", "181-ball"),
            ("The Vibe of Vegas", "181-vibe"),
            ("90's Dance", "181-90sdance"),
            ("Techno Club", "181-technoclub"),
        ),
    ),
    (
        "Easy Listening",
        (
            ("True Blues", "181-blues"),
            ("Jazz Mix", "181-jazzmix"),
            ("The Breeze", "181-breeze"),
            ("Classical Guitar", "181-classicalguitar"),
            ("Classical Jazz", "181-classicaljazz"),
            ("Vocal Jazz", "181-vocals"),
            ("BeBop Jazz", "181-bebop"),
            ("Fusion Jazz", "181-fusionjazz"),
            ("Trance Jazz", "181-trancejazz"),
            ("Classical Music", "181-classical"),
            ("Acid Jazz", "181-acidjazz"),
        ),
    ),
    (
        "Comedy",
        (("Comedy", "181-comedy"),),
    ),
    (
        "Christmas",
        (
            ("Christmas Kountry", "181-xkkountry"),
            ("Christmas Classics", "181-xtraditional"),
            ("Christmas Oldies", "181-xoldies"),
            ("Christmas Country", "181-xcountry"),
            ("Christmas Power", "181-xpower"),
            ("Christmas Highway", "181-xhighway"),
            ("Christmas Soundtracks", "181-xsoundtrax"),
            ("Christmas R&B", "181-xtrue"),
            ("Christmas Rock", "181-xrock"),
            ("Christmas Mix", "181-xmix"),
            ("Christmas Fun", "181-xfun"),
            ("Christmas Kids", "181-xkids"),
            ("Christmas Blender", "181-xblender"),
            ("Christmas Standards", "181-xstandards"),
            ("Christmas Spirit", "181-xspirit"),
            ("Christmas Smooth Jazz", "181-xsmooth"),
            ("Christmas Gospel", "181-xgospel"),
            ("Christmas Swing", "181-xswing"),
        ),
    ),
)
