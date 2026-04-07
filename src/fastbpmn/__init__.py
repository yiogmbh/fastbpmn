"""Top-level package for yio-minions."""

import importlib.metadata
from .fastbpmn import FastBPMN
from .process import Process
from .task import TaskHandler
from .task_group import TaskGroup

__version__ = importlib.metadata.version("fastbpmn")
__author__ = """yio gmbh"""
__email__ = "hello@yio.at"

# Later we will include all types and definitions here that are really required to implement external tasks
# to keep the interface probably as simple as possible.
__all__ = ["FastBPMN", "Process", "TaskGroup", "TaskHandler"]
