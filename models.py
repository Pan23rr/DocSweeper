# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Data models for Doc Sweeper Environment.

This module defines the Action, Observation, and State types for the documentation
maintenance tasks via the OpenEnv interface.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from openenv.core.env_server import Action, Observation, State
from pydantic import Field


class DocAction(Action):
    """
    Action for Doc Sweeper environment.

    Attributes:
        tool_name: The command to run ('open', 'edit', 'grep', 'done').
        path: File path for opening or editing.
        old_str: Exact match string for safe replacement.
        new_str: Replacement string.
        search_query: String to search via grep.
    """

    tool_name: str = Field(..., description="'open', 'edit', 'grep', or 'done'")
    path: Optional[str] = Field(None, description="File path for open/edit/grep")
    old_str: Optional[str] = Field(None, description="Exact match string for safe replacement")
    new_str: Optional[str] = Field(None, description="Replacement string")
    search_query: Optional[str] = Field(None, description="String to search via grep")


class DocObservation(Observation):
    """
    Observation for Doc Sweeper environment.

    Attributes:
        active_file: Currently opened file path.
        file_content: Full text of the opened file.
        directory_tree: Virtual File System tree representation.
        issues_detected: Linter output for current file.
        terminal_feedback: Result of last action.
        done: Whether the task is complete.
        reward: Reward for the last action.
    """

    active_file: str = ""
    file_content: str = ""
    directory_tree: Dict[str, List[str]] = Field(default_factory=dict)
    issues_detected: List[str] = Field(default_factory=list)
    terminal_feedback: str = "Environment initialized."
    done: bool = False


class DocState(State):
    """
    State for Doc Sweeper environment.

    Attributes:
        episode_id: Unique ID for the current task session.
        step_count: Number of actions taken.
        vfs: The current state of the virtual file system (hidden from direct observation).
        active_file: The file currently open in the editor.
    """

    episode_id: str = ""
    step_count: int = 0
    vfs: Dict[str, str] = Field(default_factory=dict)
    active_file: str = ""