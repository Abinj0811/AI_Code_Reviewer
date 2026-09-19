"""Parsing of unified diffs into structured, per-file data.

Used for two things:
1. Giving the LLM a per-file view of what changed.
2. Determining which (file, line) pairs are valid targets for a GitHub
   line comment — GitHub rejects comments on lines that are not part of
   the diff.
"""

import re
from dataclasses import dataclass, field

_DIFF_GIT_RE = re.compile(r"^diff --git a/(.*?) b/(.*?)$")
_HUNK_HEADER_RE = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")


@dataclass
class FileDiff:
    """The diff contents for a single file, plus its commentable lines."""

    path: str
    hunk_text: str = ""
    commentable_lines: set[int] = field(default_factory=set)
    is_deleted: bool = False


@dataclass
class ParsedDiff:
    files: dict[str, FileDiff] = field(default_factory=dict)

    def is_commentable(self, path: str, line: int) -> bool:
        file_diff = self.files.get(path)
        return bool(file_diff and line in file_diff.commentable_lines)

    def changed_files(self) -> list[str]:
        return list(self.files.keys())


def parse_diff(diff_text: str) -> ParsedDiff:
    """Parse a unified diff (as returned by the GitHub diff API) into a
    ParsedDiff describing each changed file's hunks and commentable
    (new-file) line numbers.
    """
    parsed = ParsedDiff()
    current: FileDiff | None = None
    new_line_no = 0

    for raw_line in diff_text.splitlines():
        git_match = _DIFF_GIT_RE.match(raw_line)
        if git_match:
            path = git_match.group(2)
            current = FileDiff(path=path)
            parsed.files[path] = current
            continue

        if current is None:
            continue

        if raw_line.startswith("+++ "):
            if raw_line.strip() == "+++ /dev/null":
                current.is_deleted = True
            current.hunk_text += raw_line + "\n"
            continue

        hunk_match = _HUNK_HEADER_RE.match(raw_line)
        if hunk_match:
            new_line_no = int(hunk_match.group(2))
            current.hunk_text += raw_line + "\n"
            continue

        if raw_line.startswith("+") and not raw_line.startswith("+++"):
            current.hunk_text += raw_line + "\n"
            current.commentable_lines.add(new_line_no)
            new_line_no += 1
        elif raw_line.startswith("-") and not raw_line.startswith("---"):
            current.hunk_text += raw_line + "\n"
            # Removed lines don't exist in the new file; no line increment.
        else:
            # Context line or other metadata (e.g. "\ No newline at end of file").
            current.hunk_text += raw_line + "\n"
            if raw_line.startswith(" "):
                current.commentable_lines.add(new_line_no)
                new_line_no += 1

    return parsed
