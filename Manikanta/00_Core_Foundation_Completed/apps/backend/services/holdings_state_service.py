"""
Holdings State Service - State machine for holdings lifecycle

This module defines and validates state transitions for holdings.
"""

from typing import Dict, Optional
from enum import Enum


class HoldingStatus(str, Enum):
    """Valid holding statuses"""
    OPEN = "OPEN"
    PARTIALLY_SOLD = "PARTIALLY_SOLD"
    SOLD = "SOLD"
    CANCELLED = "CANCELLED"


class HoldingSource(str, Enum):
    """Valid holding sources"""
    MANUAL_BUY = "MANUAL_BUY"
    ARBITRAGE_SIMULATION = "ARBITRAGE_SIMULATION"
    TRANSFER = "TRANSFER"


# Valid state transitions
VALID_TRANSITIONS = {
    HoldingStatus.OPEN: [HoldingStatus.PARTIALLY_SOLD, HoldingStatus.SOLD, HoldingStatus.CANCELLED],
    HoldingStatus.PARTIALLY_SOLD: [HoldingStatus.SOLD],
    HoldingStatus.SOLD: [],  # Terminal state - no transitions allowed
    HoldingStatus.CANCELLED: []  # Terminal state - no transitions allowed
}


def can_transition(from_status: str, to_status: str) -> bool:
    """
    Check if a state transition is valid.
    
    Args:
        from_status: Current status
        to_status: Desired status
        
    Returns:
        bool: True if transition is valid, False otherwise
    """
    try:
        from_enum = HoldingStatus(from_status)
        to_enum = HoldingStatus(to_status)
    except ValueError:
        return False
    
    return to_enum in VALID_TRANSITIONS.get(from_enum, [])


def validate_transition(from_status: str, to_status: str) -> None:
    """
    Validate a state transition and raise an exception if invalid.
    
    Args:
        from_status: Current status
        to_status: Desired status
        
    Raises:
        ValueError: If transition is invalid
    """
    if not can_transition(from_status, to_status):
        raise ValueError(
            f"Invalid state transition from {from_status} to {to_status}. "
            f"Valid transitions from {from_status}: {VALID_TRANSITIONS.get(HoldingStatus(from_status), [])}"
        )


def get_valid_transitions(current_status: str) -> list:
    """
    Get list of valid transitions from current status.
    
    Args:
        current_status: Current holding status
        
    Returns:
        list: List of valid status values that can be transitioned to
    """
    try:
        current_enum = HoldingStatus(current_status)
        return [status.value for status in VALID_TRANSITIONS.get(current_enum, [])]
    except ValueError:
        return []


def is_terminal_status(status: str) -> bool:
    """
    Check if a status is terminal (no further transitions allowed).
    
    Args:
        status: Status to check
        
    Returns:
        bool: True if status is terminal, False otherwise
    """
    try:
        status_enum = HoldingStatus(status)
        return len(VALID_TRANSITIONS.get(status_enum, [])) == 0
    except ValueError:
        return False

