# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Doc Sweeper Environment for OpenEnv.

This module provides an environment where an agent navigates a virtual file system
to fix outdated documentation, broken links, and deprecated configurations.
"""

import uuid
from typing import Dict, List

from openenv.core.env_server import Environment

from models import DocAction, DocObservation, DocState


class DocSweeperEnvironment(Environment):
    """
    Doc Sweeper environment implementing the OpenEnv interface.

    Simulates a Virtual File System (VFS) of markdown and config files. The agent
    must find and replace deprecated patterns without destructive behavior.
    """

    def __init__(
        self,
        task: str = "version_bump",
        max_steps: int = 30,
    ):
        """
        Initialize the Doc Sweeper environment.

        Args:
            task: Task to run - "version_bump", "config_migration", or "broken_links".
            max_steps: Maximum allowed actions before forced termination.
        """
        super().__init__(rubric=None)
        self._task = task
        self._max_steps = max_steps
        self._state: DocState | None = None
        self._terminal_feedback = ""
        self.reset()

    def reset(self, **kwargs):
        """
        Initialize a new task episode.

        Returns:
            Initial observation of the virtual file system.
        """
        episode_id = str(uuid.uuid4())
        self._terminal_feedback = "Environment reset."
        
        initial_vfs = {}
        if self._task == "version_bump":
            initial_vfs = {
                "/docs/setup.md": "Welcome to our tool v1.0.0. To install v1.0.0, run the script.",
                "/docs/api.md": "API Reference for v1.0.0.",
                "/docs/troubleshoot.md": "If v1.00 fails, check logs."
            }
        elif self._task == "config_migration":
            initial_vfs = {
                "/docs/docker-compose.yml": "version: '2'\nservices:\n  web:\n    links:\n      - db",
                "/docs/readme.md": "Use the docker-compose to start."
            }
        else: 
            initial_vfs = {
                "/docs/index.md": "Please read [Setup](setup.md) before continuing.",
                "/docs/installation.md": "# Installation\nSteps go here.",
                "/docs/advanced.md": "Advanced config in [Setup](setup.md)."
            }

        self._state = DocState(
            episode_id=episode_id,
            step_count=0,
            vfs=initial_vfs,
            active_file=""
        )

        return self._make_observation(reward=0.0, done=False)

    def step(self, action: DocAction):
        """
        Execute an action and return the resulting state.

        Args:
            action: The tool action to execute (open, edit, grep, done).

        Returns:
            Observation with reward and done flag.
        """
        if self._state is None:
            raise RuntimeError("Environment not initialized. Call reset() first.")

        self._state.step_count += 1
        reward = 0.0
        done = False
        self._terminal_feedback = ""
        
        # Action Routing
        if action.tool_name == "done":
            done = True
            reward += self._evaluate_final_grade()
            self._terminal_feedback = "Task submitted for final grading."
            
        elif action.tool_name == "open":
            if action.path in self._state.vfs:
                self._state.active_file = action.path
                self._terminal_feedback = f"Opened {action.path}"
            else:
                self._terminal_feedback = f"Error: File {action.path} not found."
                reward -= 0.1
                
        elif action.tool_name == "grep":
            if action.search_query:
                results = [p for p, c in self._state.vfs.items() if action.search_query in c]
                self._terminal_feedback = f"Found '{action.search_query}' in: {', '.join(results) or 'No files'}"
                if self._task == "broken_links":
                    reward += 0.1
            else:
                self._terminal_feedback = "Error: search_query required for grep."
                
        elif action.tool_name == "edit":
            reward += self._handle_edit(action)
            
        else:
            self._terminal_feedback = f"Error: Unknown tool {action.tool_name}."
            reward -= 0.1

        # Check timeout
        if self._state.step_count >= self._max_steps:
            done = True
            self._terminal_feedback = "Max steps reached."
            
        return self._make_observation(reward=reward, done=done)

    def _handle_edit(self, action: DocAction) -> float:
        if not self._state.active_file:
            self._terminal_feedback = "Error: No file is currently open."
            return -0.1
            
        content = self._state.vfs[self._state.active_file]
        
        if action.old_str in ["```yaml", "# Title"] and not action.new_str:
            self._terminal_feedback = "Error: Destructive action prevented."
            return -1.0
            
        if action.old_str and action.old_str in content:
            self._state.vfs[self._state.active_file] = content.replace(action.old_str, action.new_str or "")
            self._terminal_feedback = "Edit successful."
            return 0.1
        else:
            self._terminal_feedback = f"Error: old_str '{action.old_str}' not found in file."
            return -0.1

    def _evaluate_final_grade(self) -> float:
        # Simplified deterministic grader for example purposes
        text = "".join(self._state.vfs.values())
        if self._task == "version_bump":
            target_count = text.count("v2.0.0")
            penalty = text.count("v1.0.0") + text.count("v1.00")
            return max(0.0, (target_count / 4.0) - (penalty * 0.5))
        return 0.5

    def _get_linter_issues(self) -> List[str]:
        if not self._state.active_file:
            return []
        issues = []
        content = self._state.vfs.get(self._state.active_file, "")
        if self._task == "version_bump" and "v1.0.0" in content:
            issues.append("Deprecated version 'v1.0.0' found.")
        return issues

    def _make_observation(self, reward: float = 0.0, done: bool = False):
        return DocObservation(
            active_file=self._state.active_file,
            file_content=self._state.vfs.get(self._state.active_file, ""),
            directory_tree={"/docs": list(self._state.vfs.keys())},
            issues_detected=self._get_linter_issues(),
            terminal_feedback=self._terminal_feedback,
            reward=reward,
            done=done,
        )

    @property
    def state(self):
        """Return the current episode state."""
        return self._state