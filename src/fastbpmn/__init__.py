"""Top-level package for yio-minions."""

__author__ = """Daniel Hofstetter"""
__email__ = "dh@yio.at"
__version__ = "2.0.6"

from .minion import YioMinion
from .process import Process
from .task import TaskHandler
from .task_group import TaskGroup

# Later we will include all types and definitions here that are really required to implement external tasks
# to keep the interface probably as simple as possible.
__all__ = ["YioMinion", "Process", "TaskGroup", "TaskHandler"]
