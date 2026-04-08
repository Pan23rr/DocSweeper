# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.


from __future__ import annotations

from typing import Any, Dict

from openenv.core.client_types import StepResult
from openenv.core.env_client import EnvClient

from models import DocAction, DocObservation, DocState


class DocSweeperEnv(EnvClient[DocAction, DocObservation, DocState]):

    def _step_payload(self, action: DocAction) -> Dict[str, Any]:
        """

        Args:
            action: DocAction instance with tool parameters.
        """
        return {
            "tool_name": action.tool_name,
            "path": action.path,
            "old_str": action.old_str,
            "new_str": action.new_str,
            "search_query": action.search_query,
        }

    def _parse_result(self, payload: Dict[str, Any]) -> StepResult[DocObservation]:
        """
        Args:
            payload: JSON response from server.

        """
        obs_data = payload.get("observation", {})

        observation = DocObservation(
            active_file=obs_data.get("active_file", ""),
            file_content=obs_data.get("file_content", ""),
            directory_tree=obs_data.get("directory_tree", {}),
            issues_detected=obs_data.get("issues_detected", []),
            terminal_feedback=obs_data.get("terminal_feedback", ""),
            done=obs_data.get("done", False),
            reward=obs_data.get("reward", 0.0),
        )

        return StepResult(
            observation=observation,
            reward=observation.reward,
            done=observation.done,
        )

    def _parse_state(self, payload: Dict[str, Any]) -> DocState:
        """
        Args:
            payload: JSON response from /state endpoint.

        """
        return DocState(
            episode_id=payload.get("episode_id", ""),
            step_count=payload.get("step_count", 0),
            vfs=payload.get("vfs", {}),
            active_file=payload.get("active_file", ""),
        )