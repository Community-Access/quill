from quilllite.rtf_safety import scan_rtf_safety


def test_plain_rtf_is_safe():
    report = scan_rtf_safety(r"{\rtf1\ansi Hello\par}")
    assert report.safe and report.sanitized_rtf == r"{\rtf1\ansi Hello\par}"


def test_embedded_object_is_stripped():
    rtf = r"{\rtf1\ansi Before {\object\objemb{\*\objdata 0102}} After\par}"
    report = scan_rtf_safety(rtf)
    assert not report.safe
    assert "embedded OLE object" in report.blocked
    assert "objdata" not in report.sanitized_rtf
    assert "Before" in report.sanitized_rtf and "After" in report.sanitized_rtf


def test_binary_and_remote_are_flagged():
    report = scan_rtf_safety(r"{\rtf1 \bin12 xx {\field{\*\fldinst INCLUDEPICTURE x}}}")
    assert "binary data" in report.warnings
    assert "remote content references" in report.warnings
    assert r"\bin0" in report.sanitized_rtf


def test_escaped_braces_survive():
    rtf = r"{\rtf1 a\{b\}c\\d}"
    assert scan_rtf_safety(rtf).sanitized_rtf == rtf
