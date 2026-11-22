"""Typed errors. Every message says what happened and what to do."""

from __future__ import annotations


class RagDoctorError(Exception):
    """The base of every error ragdoctor raises on purpose."""
