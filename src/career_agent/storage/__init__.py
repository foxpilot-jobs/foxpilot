"""Durable local storage."""

from .sqlite import JobStore

__all__ = ["JobStore"]
