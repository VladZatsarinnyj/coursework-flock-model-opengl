"""Внешняя камера, вращающаяся вокруг аквариума."""

import math

from aquarium import config
from aquarium.mathutils import look_at, perspective

WORLD_UP = (0.0, 1.0, 0.0)


class OrbitCamera:
    """Камера на сфере вокруг точки target.

    Положение задаётся сферическими координатами: азимутом yaw (поворот вокруг
    оси Y), углом возвышения pitch и расстоянием distance:

        x = target.x + distance · cos(pitch) · sin(yaw)
        y = target.y + distance · sin(pitch)
        z = target.z + distance · cos(pitch) · cos(yaw)

    Угол pitch ограничен ±85°: при 90° камера смотрела бы строго вниз,
    направление взгляда совпало бы с вектором «вверх», и look_at не смогла бы
    построить базис камеры (векторное произведение стало бы нулевым).
    """

    MIN_PITCH_DEG = -85.0
    MAX_PITCH_DEG = 85.0

    def __init__(self, target=config.AQUARIUM_CENTER):
        self.target = target
        self.reset()

    def reset(self):
        """Возвращает камеру в начальное положение."""
        self.yaw_deg = config.CAMERA_START_YAW_DEG
        self.pitch_deg = config.CAMERA_START_PITCH_DEG
        self.distance = config.CAMERA_START_DISTANCE

    def rotate(self, delta_yaw_deg, delta_pitch_deg):
        self.yaw_deg = (self.yaw_deg + delta_yaw_deg) % 360.0
        self.pitch_deg = max(self.MIN_PITCH_DEG, min(self.MAX_PITCH_DEG, self.pitch_deg + delta_pitch_deg))

    def zoom(self, factor):
        """Умножает расстояние на factor: меньше 1 — приближение, больше 1 — отдаление."""
        self.distance = max(config.CAMERA_MIN_DISTANCE,
                            min(config.CAMERA_MAX_DISTANCE, self.distance * factor))

    def eye_position(self):
        yaw = math.radians(self.yaw_deg)
        pitch = math.radians(self.pitch_deg)
        return (
            self.target[0] + self.distance * math.cos(pitch) * math.sin(yaw),
            self.target[1] + self.distance * math.sin(pitch),
            self.target[2] + self.distance * math.cos(pitch) * math.cos(yaw),
        )

    def view_matrix(self):
        return look_at(self.eye_position(), self.target, WORLD_UP)

    def projection_matrix(self, aspect):
        return perspective(config.CAMERA_FOV_DEG, aspect, config.CAMERA_NEAR, config.CAMERA_FAR)
