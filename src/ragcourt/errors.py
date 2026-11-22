"""Typed errors. Every message says what happened and what to do."""

from __future__ import annotations


class RagCourtError(Exception):
    """The base of every error ragcourt raises on purpose."""
