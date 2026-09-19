from app.review.diff_analyzer import parse_diff

SAMPLE_DIFF = (
    "diff --git a/app/foo.py b/app/foo.py\n"
    "index e69de29..4b825dc 100644\n"
    "--- a/app/foo.py\n"
    "+++ b/app/foo.py\n"
    "@@ -1,3 +1,4 @@\n"
    " def foo():\n"
    "-    return 1\n"
    "+    return 2\n"
    "+    # new comment\n"
    " \n"
)


def test_parse_diff_tracks_changed_files():
    parsed = parse_diff(SAMPLE_DIFF)
    assert parsed.changed_files() == ["app/foo.py"]


def test_parse_diff_commentable_lines_include_added_and_context_lines():
    parsed = parse_diff(SAMPLE_DIFF)
    assert parsed.is_commentable("app/foo.py", 1)  # context line
    assert parsed.is_commentable("app/foo.py", 2)  # added line
    assert parsed.is_commentable("app/foo.py", 3)  # added line
    assert parsed.is_commentable("app/foo.py", 4)  # trailing context line


def test_parse_diff_rejects_lines_outside_diff():
    parsed = parse_diff(SAMPLE_DIFF)
    assert not parsed.is_commentable("app/foo.py", 100)
    assert not parsed.is_commentable("other/file.py", 1)


def test_parse_diff_handles_deleted_file():
    diff_text = (
        "diff --git a/old.py b/old.py\n"
        "deleted file mode 100644\n"
        "index e69de29..0000000\n"
        "--- a/old.py\n"
        "+++ /dev/null\n"
        "@@ -1,1 +0,0 @@\n"
        "-print('gone')\n"
    )
    parsed = parse_diff(diff_text)
    assert parsed.files["old.py"].is_deleted is True
    assert not parsed.is_commentable("old.py", 1)


def test_parse_diff_empty_string_returns_no_files():
    parsed = parse_diff("")
    assert parsed.changed_files() == []
