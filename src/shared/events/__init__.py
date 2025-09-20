"""
Shared event components for the YABOT system.

This module contains event correlation services and utilities for
cross-module event management and ordering.
"""

from .correlation import EventCorrelationService, create_correlation_service, CorrelationSequence, EventStatus

__all__ = [
    "EventCorrelationService",
    "create_correlation_service",
    "CorrelationSequence",
    "EventStatus"
]