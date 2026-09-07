from quilllite.editor import HEADING_POINT_SIZES, heading_level_for_font


def test_ladder_maps_back():
    for level, size in HEADING_POINT_SIZES.items():
        assert heading_level_for_font(size, True) == level


def test_body_and_unbold_are_not_headings():
    assert heading_level_for_font(11.0, True) is None
    assert heading_level_for_font(20.0, False) is None
    assert heading_level_for_font(15.0, True) is None
