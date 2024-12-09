"""Exceptions for promptantic."""

from __future__ import annotations


class PromptanticError(Exception):
    """Base exception for promptantic."""


class ValidationError(PromptanticError):
    """Raised when validation fails."""


class TypeHandlerError(PromptanticError):
    """Raised when a type handler fails."""


class NoHandlerError(TypeHandlerError):
    """Raised when no handler is found for a type."""
