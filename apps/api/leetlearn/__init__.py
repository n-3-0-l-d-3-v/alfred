"""LeetLearn API — a Duolingo-for-LeetCode coding mentor.

The design rule that governs this whole package: the **AC gate**. Before a
passing submission the mentor is Socratic-only and structurally cannot emit
solution code (see `mentor.contracts`). After a passing submission the full
teaching surface opens up. Cost is kept near zero by serving hints from
pre-generated Problem Cards (a DB/file read) instead of live LLM calls.
"""

__version__ = "0.1.0"
