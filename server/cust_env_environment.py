# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import uuid
from typing import Dict, List

from openenv.core.env_server import Environment
from models import DocAction, DocObservation, DocState

class DocSweeperEnvironment(Environment):

    def __init__(
        self,
        task: str = "version_bump",
        max_steps: int = 20,
    ):
        super().__init__(rubric=None)
        self._task = task
        self._max_steps = max_steps
        self._state: DocState | None = None
        self._terminal_feedback = ""
        
        self._baseline_denominators = {}
        self.reset()

    def reset(self, **kwargs):
        episode_id = str(uuid.uuid4())
        self._terminal_feedback = "Environment reset."
        
        if self._task == "version_bump":
            initial_vfs = {
                "/docs/setup.md": "Welcome to our tool v1.0.0. To install v1.0.0, run the script.",
                "/docs/api.md": "API Reference for v1.0.0.",
                "/docs/troubleshoot.md": "If v1.00 fails, check logs."
            }
            self._baseline_denominators["total_files"] = 3
            
        elif self._task == "config_migration":
            initial_vfs = {
                "/docs/docker-compose.yml": "version: '2'\nservices:\n  web:\n    links:\n      - db",
                "/docs/readme.md": "Use the docker-compose to start."
            }
            self._baseline_denominators["total_files"] = 1 # Only one compose file matters
            
        elif self._task == "broken_links": 
            initial_vfs = {
                "/docs/index.md": "Please read [Setup](../old-docs/setup.md) before continuing.",
                "/docs/installation.md": "# Installation\nSee [API](../old-docs/api.md) for details.",
                "/docs/advanced.md": "Advanced config in [Setup](../old-docs/setup.md)."
            }
            self._baseline_denominators["total_links"] = 3
        else:
            initial_vfs = {"/docs/empty.md": "Unknown task."}

        self._state = DocState(
            episode_id=episode_id,
            step_count=0,
            vfs=initial_vfs,
            active_file=""
        )

        return self._make_observation(reward=0.0, done=False)

    def step(self, action: DocAction):
        if self._state is None:
            raise RuntimeError("Environment not initialized. Call reset() first.")

        self._state.step_count += 1
        done = False
        self._terminal_feedback = ""
        
        old_score = self._calculate_state_score()
        
        step_penalty = 0.0

        if action.tool_name == "done":
            done = True
            self._terminal_feedback = "Task submitted. Evaluating final state."
            
        elif action.tool_name == "open":
            if action.path in self._state.vfs:
                self._state.active_file = action.path
                self._terminal_feedback = f"Opened {action.path}"
            else:
                self._terminal_feedback = f"Error: File '{action.path}' not found."
                step_penalty -= 0.05 
                
        elif action.tool_name == "grep":
            if action.search_query:
                results = [p for p, c in self._state.vfs.items() if action.search_query in c]
                self._terminal_feedback = f"Found '{action.search_query}' in: {', '.join(results) or 'No files'}"
            else:
                self._terminal_feedback = "Error: search_query required for grep."
                step_penalty -= 0.05
                
        elif action.tool_name == "edit":
            step_penalty += self._handle_edit(action)
            
        else:
            self._terminal_feedback = f"Error: Unknown tool {action.tool_name}."
            step_penalty -= 0.05

        if self._state.step_count >= self._max_steps and not done:
            done = True
            self._terminal_feedback = "Max steps reached. Forced termination."

        new_score = self._calculate_state_score()
        
        delta_reward = (new_score - old_score)
        total_step_reward = delta_reward + step_penalty
            
        return self._make_observation(reward=total_step_reward, done=done)

    def _handle_edit(self, action: DocAction) -> float:
        """Executes the edit and returns a penalty if it fails."""
        if not self._state.active_file:
            self._terminal_feedback = "Error: No file is currently open."
            return -0.05
            
        if not action.old_str:
            self._terminal_feedback = "Error: 'old_str' is missing or empty."
            return -0.05

        content = self._state.vfs[self._state.active_file]
        
        if action.old_str in ["```yaml", "# Title"] and not action.new_str:
            self._terminal_feedback = "Error: Destructive action prevented."
            return -0.05
            
        if action.old_str in content:
            safe_new_str = action.new_str if action.new_str is not None else ""
            self._state.vfs[self._state.active_file] = content.replace(action.old_str, safe_new_str)
            self._terminal_feedback = "Edit successful."
            return 0.0 
        else:
            self._terminal_feedback = f"Error: old_str '{action.old_str}' not found in file."
            return -0.05

    def _calculate_state_score(self) -> float:
        """
        Calculates the absolute progress of the environment [0.0 to 1.0].
        This is called every step to calculate the delta reward.
        """
        vfs_items = self._state.vfs.items()
        
        if self._task == "version_bump":
            correct_files = 0
            for path, content in vfs_items:
                if "v2.0.0" in content and not ("v1.0.0" in content or "v1.00" in content):
                    correct_files += 1
            
            return min(1.0, correct_files / self._baseline_denominators["total_files"])

        elif self._task == "config_migration":
            compose_files = [content for path, content in vfs_items if "docker-compose" in path]
            total_score = 0.0
            
            for content in compose_files:
                if "version: '3.8'" in content or 'version: "3.8"' in content:
                    total_score += 0.5
                if "networks:" in content and "links:" not in content:
                    total_score += 0.5
                    
            return min(1.0, total_score / self._baseline_denominators["total_files"])

        elif self._task == "broken_links":
            good_link_count = 0
            for path, content in vfs_items:
                good_link_count += content.count("./new-docs/")
                
            return min(1.0, good_link_count / self._baseline_denominators["total_links"])

        return 0.0

    def _get_linter_issues(self) -> List[str]:
        if not self._state.active_file:
            return []
        issues = []
        content = self._state.vfs.get(self._state.active_file, "")
        
        if self._task == "version_bump" and ("v1.0.0" in content or "v1.00" in content):
            issues.append("LINTER WARNING: Deprecated version string found.")
        elif self._task == "broken_links" and "../old-docs/" in content:
            issues.append("LINTER WARNING: Broken relative link detected.")
        elif self._task == "config_migration" and "links:" in content:
            issues.append("LINTER WARNING: Docker 'links' is deprecated. Use 'networks'.")
            
        return issues

    def _make_observation(self, reward: float = 0.0, done: bool = False):
        files_list = list(self._state.vfs.keys())
        return DocObservation(
            active_file=self._state.active_file,
            file_content=self._state.vfs.get(self._state.active_file, ""),
            directory_tree={"/docs": files_list},
            issues_detected=self._get_linter_issues(),
            terminal_feedback=self._terminal_feedback,
            reward=reward,
            done=done,
        )

    @property
    def state(self):
        return self._state