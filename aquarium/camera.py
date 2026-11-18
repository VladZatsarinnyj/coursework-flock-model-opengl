"""Камеры: внешняя (вращается вокруг аквариума) и внутренняя (следует за выбранной рыбой)."""

import math

from aquarium import config
from aquarium.mathutils import add, length, look_at, normalize, perspective, scale

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


class FollowCamera:
    """Внутренняя камера: следует за выбранной рыбой, позади и чуть выше неё.

        eye    = p − d·BEHIND + up·HEIGHT
        target = p + d·LOOK_AHEAD

    где p — положение рыбы, d — сглаженное направление её движения. Без сглаживания
    камера дёргалась бы при каждом повороте рыбы. Сглаживание экспоненциальное:
        d ← normalize(d + (v/|v| − d)·k),  k = 1 − e^(−FOLLOW_SMOOTHING·Δt)
    Доля k зависит от Δt так, что результат не зависит от FPS.

    Наклон d ограничен FOLLOW_MAX_PITCH_DEG: если рыба плывёт почти вертикально,
    направление взгляда совпало бы с вектором «вверх», и look_at не смогла бы
    построить базис камеры (та же причина, что у внешней камеры).
    """

    def __init__(self):
        self.direction = (1.0, 0.0, 0.0)
        self.fish_position = (0.0, 0.0, 0.0)
        self.fish_index = None  # за какой рыбой камера следила в прошлом кадре

    def update(self, fish_index, fish, dt):
        speed = length(fish.velocity)
        heading = scale(fish.velocity, 1.0 / speed) if speed > 1e-9 else self.direction
        if fish_index != self.fish_index:
            self.direction = heading  # выбрана другая рыба: сразу смотреть по её курсу
            self.fish_index = fish_index
        else:
            k = 1.0 - math.exp(-config.FOLLOW_SMOOTHING * dt)
            blended = add(self.direction, scale(add(heading, scale(self.direction, -1.0)), k))
            self.direction = blended if length(blended) > 1e-9 else heading
        self.direction = self._limit_pitch(normalize(self.direction))
        self.fish_position = fish.position

    @staticmethod
    def _limit_pitch(direction):
        horizontal = math.hypot(direction[0], direction[2])
        if horizontal < 1e-6:
            return (1.0, 0.0, 0.0)  # строго вертикально: горизонтальное направление не определено
        max_pitch = math.radians(config.FOLLOW_MAX_PITCH_DEG)
        pitch = max(-max_pitch, min(max_pitch, math.atan2(direction[1], horizontal)))
        return (direction[0] / horizontal * math.cos(pitch),
                math.sin(pitch),
                direction[2] / horizontal * math.cos(pitch))

    def eye_position(self):
        behind = scale(self.direction, -config.FOLLOW_DISTANCE_BEHIND)
        return add(add(self.fish_position, behind), (0.0, config.FOLLOW_HEIGHT, 0.0))

    def view_matrix(self):
        target = add(self.fish_position, scale(self.direction, config.FOLLOW_LOOK_AHEAD))
        return look_at(self.eye_position(), target, WORLD_UP)

    def projection_matrix(self, aspect):
        return perspective(config.CAMERA_FOV_DEG, aspect, config.CAMERA_NEAR, config.CAMERA_FAR)
