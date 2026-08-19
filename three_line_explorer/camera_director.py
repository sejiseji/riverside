from __future__ import annotations

from dataclasses import dataclass

from three_line_explorer.config import CameraShotId, INITIAL_CAMERA
from three_line_explorer.stage import ALL_CAMERA_SHOTS, CameraRule


@dataclass(slots=True)
class CameraDirector:
    stage_default_shot: CameraShotId = INITIAL_CAMERA
    last_manual_shot: CameraShotId = INITIAL_CAMERA
    effective_shot: CameraShotId = INITIAL_CAMERA

    def resolve(
        self,
        rule: CameraRule,
        manual_request: CameraShotId | None,
        current_camera_shot: CameraShotId,
    ) -> CameraShotId:
        allowed = rule.allowed_shots or ALL_CAMERA_SHOTS

        if rule.forced_shot is not None:
            self.effective_shot = rule.forced_shot
            return rule.forced_shot

        if manual_request is not None and rule.manual_enabled and manual_request in allowed:
            self.last_manual_shot = manual_request

        if self.last_manual_shot in allowed:
            self.effective_shot = self.last_manual_shot
            return self.effective_shot

        if self.effective_shot in allowed:
            return self.effective_shot

        if allowed:
            self.effective_shot = nearest_allowed_shot(current_camera_shot, allowed)
            return self.effective_shot

        self.effective_shot = self.stage_default_shot
        return self.effective_shot


def nearest_allowed_shot(
    current: CameraShotId,
    allowed: frozenset[CameraShotId],
) -> CameraShotId:
    if not allowed:
        return INITIAL_CAMERA
    return min(allowed, key=lambda shot_id: (abs(int(shot_id) - int(current)), int(shot_id)))
