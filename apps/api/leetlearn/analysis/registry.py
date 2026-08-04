"""Language dispatch.

Python uses the stdlib `ast` (most precise). Every other language routes to
tree-sitter. If tree-sitter isn't installed the caller still gets a valid
`CodeSignals` with an honest error, and card-based hints keep working.
"""

from __future__ import annotations

from .python_analyzer import analyze_python
from .signals import CodeSignals
from .treesitter_analyzer import analyze_with_treesitter, available as _ts_available

_PYTHON = {"python", "python3", "py"}

# language id (as LeetCode labels them) -> tree-sitter key
_TS_LANGS = {
    "cpp": "cpp", "c++": "cpp", "c": "cpp",
    "java": "java",
    "javascript": "javascript", "js": "javascript",
    "typescript": "javascript", "ts": "javascript",
    "go": "go", "golang": "go",
}


def supported_languages() -> list[str]:
    langs = sorted(_PYTHON)
    if _ts_available():
        langs += sorted(set(_TS_LANGS))
    return langs


def analyze(language: str, code: str) -> CodeSignals:
    lang = (language or "").strip().lower()

    if lang in _PYTHON:
        return analyze_python(code)

    if lang in _TS_LANGS:
        if not _ts_available():
            return CodeSignals(
                language=lang,
                parsed=False,
                error=f"'{lang}' needs tree-sitter (pip install tree-sitter tree-sitter-{_TS_LANGS[lang]}); "
                "hints and card content still work",
            )
        return analyze_with_treesitter(_TS_LANGS[lang], code)

    return CodeSignals(
        language=lang or "unknown",
        parsed=False,
        error=f"unsupported language: {language!r} (supported: {', '.join(supported_languages())})",
    )
