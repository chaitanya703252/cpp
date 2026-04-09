"""
studygroup-scheduler-nci - Study Group Scheduling Library
Author: Lakshmi Chaitanya
Version: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "Lakshmi Chaitanya"

from .scheduler import SessionScheduler
from .matcher import GroupMatcher
from .validator import InputValidator
from .formatter import ScheduleFormatter

__all__ = [
    "SessionScheduler",
    "GroupMatcher",
    "InputValidator",
    "ScheduleFormatter",
]
