"""Стая рыб по модели Boids (C. Reynolds, 1987). Не использует OpenGL."""

import math
import random
from dataclasses import dataclass

from aquarium import config
from aquarium.mathutils import add, clamp_length, dot, length, scale, sub
from aquarium.neighbors import find_neighbors_naive


def _clamp(value, value_range):
    low, high = value_range
    return max(low, min(high, float(value)))


@dataclass
class FlockParams:
    """Параметры модели, которые пользователь меняет в панели."""

    separation_weight: float = 1.5  # разделение: не сближаться с соседями
    alignment_weight: float = 1.5   # выравнивание: плыть как соседи
    cohesion_weight: float = 0.8    # сплочённость: держаться центра соседей
    neighbor_radius: float = 3.0    # кого рыба считает соседями
    max_speed: float = 4.0          # единиц сцены в секунду

    def clamp(self):
        """Приводит все параметры к допустимым диапазонам из config."""
        self.separation_weight = _clamp(self.separation_weight, config.SEPARATION_WEIGHT_RANGE)
        self.alignment_weight = _clamp(self.alignment_weight, config.ALIGNMENT_WEIGHT_RANGE)
        self.cohesion_weight = _clamp(self.cohesion_weight, config.COHESION_WEIGHT_RANGE)
        self.neighbor_radius = _clamp(self.neighbor_radius, config.NEIGHBOR_RADIUS_RANGE)
        self.max_speed = _clamp(self.max_speed, config.MAX_SPEED_RANGE)


@dataclass
class Fish:
    position: tuple  # (x, y, z)
    velocity: tuple  # (vx, vy, vz), единиц в секунду


class Flock:
    """Стая: список рыб и один шаг расчёта их движения."""

    def __init__(self, params):
        self.params = params
        self.random = random.Random(config.RANDOM_SEED)
        self.fish = []
        self.neighbors = []  # neighbors[i] — номера соседей рыбы i на последнем шаге
        # Область, в которой может находиться центр рыбы: аквариум минус зазор до стекла.
        self.low = add(config.AQUARIUM_MIN, (config.WALL_PADDING,) * 3)
        self.high = sub(config.AQUARIUM_MAX, (config.WALL_PADDING,) * 3)
        self.set_count(config.FISH_COUNT_DEFAULT)

    # --- Состав стаи ---

    def _random_fish(self):
        position = tuple(self.random.uniform(self.low[k], self.high[k]) for k in range(3))
        # Направление из двух углов: азимут yaw и небольшой наклон pitch.
        yaw = self.random.uniform(0.0, 2.0 * math.pi)
        pitch = self.random.uniform(-0.3, 0.3)  # почти горизонтально, как у настоящих рыб
        speed = 0.5 * (config.FISH_MIN_SPEED + self.params.max_speed)
        direction = (math.cos(pitch) * math.cos(yaw), math.sin(pitch), math.cos(pitch) * math.sin(yaw))
        return Fish(position, scale(direction, speed))

    def set_count(self, count):
        """Добавляет случайных рыб или убирает лишних с конца списка."""
        count = int(_clamp(count, (config.FISH_COUNT_MIN, config.FISH_COUNT_MAX)))
        while len(self.fish) < count:
            self.fish.append(self._random_fish())
        del self.fish[count:]
        self.neighbors = [[] for _ in self.fish]

    def respawn(self):
        """Раскладывает всех рыб заново в случайные места."""
        self.fish = [self._random_fish() for _ in self.fish]

    # --- Шаг симуляции ---

    def step(self, dt):
        """Продвигает стаю на время dt.

        Шаг выполняется в две фазы. Сначала по положению стаи на текущий момент
        вычисляются ускорения ВСЕХ рыб, затем все рыбы перемещаются. Если бы рыбы
        перемещались сразу по одной, вторая рыба видела бы уже сдвинутую первую,
        и результат зависел бы от порядка рыб в списке.
        """
        positions = [fish.position for fish in self.fish]
        self.neighbors = find_neighbors_naive(positions, self.params.neighbor_radius)

        accelerations = [self._acceleration(i) for i in range(len(self.fish))]

        for fish, acceleration in zip(self.fish, accelerations):
            # Полунеявный метод Эйлера: сначала скорость, затем положение по новой скорости.
            velocity = add(fish.velocity, scale(acceleration, dt))
            fish.velocity = self._limit_speed(velocity)
            fish.position = add(fish.position, scale(fish.velocity, dt))
            self._keep_inside(fish)

    def _acceleration(self, i):
        """Сумма сил, действующих на рыбу i (ускорение, единиц/с²).

        Для соседей j рыбы i (их n штук):
            разделение  s = Σ (pᵢ − pⱼ) / |pᵢ − pⱼ|²  — от каждого соседа, сильнее вблизи
            выравнивание a = (Σ vⱼ) / n − vᵢ           — к средней скорости соседей
            сплочённость c = (Σ pⱼ) / n − pᵢ           — к центру соседей
            F = w_s·s + w_a·a + w_c·c + сила стенок,   |F| ≤ FISH_MAX_ACCELERATION
        """
        fish = self.fish[i]
        params = self.params
        total = self._wall_force(fish.position)

        neighbor_ids = self.neighbors[i]
        if neighbor_ids:
            separation = (0.0, 0.0, 0.0)
            velocity_sum = (0.0, 0.0, 0.0)
            position_sum = (0.0, 0.0, 0.0)
            for j in neighbor_ids:
                other = self.fish[j]
                away = sub(fish.position, other.position)
                distance_squared = dot(away, away)
                if distance_squared > 1e-9:  # две рыбы в одной точке: направление не определено
                    separation = add(separation, scale(away, 1.0 / distance_squared))
                velocity_sum = add(velocity_sum, other.velocity)
                position_sum = add(position_sum, other.position)

            n = len(neighbor_ids)
            alignment = sub(scale(velocity_sum, 1.0 / n), fish.velocity)
            cohesion = sub(scale(position_sum, 1.0 / n), fish.position)

            total = add(total, scale(separation, params.separation_weight))
            total = add(total, scale(alignment, params.alignment_weight))
            total = add(total, scale(cohesion, params.cohesion_weight))

        return clamp_length(total, config.FISH_MAX_ACCELERATION)

    def _wall_force(self, position):
        """Мягкий разворот у стенок.

        Пока рыба дальше WALL_MARGIN от стенки, сила равна нулю. Ближе — сила
        направлена от стенки и растёт линейно: у самой границы она равна WALL_FORCE.
        """
        force = [0.0, 0.0, 0.0]
        for axis in range(3):
            near_low = self.low[axis] + config.WALL_MARGIN - position[axis]
            near_high = position[axis] - (self.high[axis] - config.WALL_MARGIN)
            if near_low > 0:
                force[axis] += config.WALL_FORCE * near_low / config.WALL_MARGIN
            if near_high > 0:
                force[axis] -= config.WALL_FORCE * near_high / config.WALL_MARGIN
        return tuple(force)

    def _limit_speed(self, velocity):
        """Держит скорость в пределах [FISH_MIN_SPEED; max_speed], сохраняя направление."""
        speed = length(velocity)
        if speed < 1e-9:
            return (config.FISH_MIN_SPEED, 0.0, 0.0)  # нулевая скорость: направление не определено
        if speed > self.params.max_speed:
            return scale(velocity, self.params.max_speed / speed)
        if speed < config.FISH_MIN_SPEED:
            return scale(velocity, config.FISH_MIN_SPEED / speed)
        return velocity

    def _keep_inside(self, fish):
        """Жёсткая граница на случай, если мягкой силы не хватило.

        Рыба возвращается на границу, а скорость вдоль этой оси направляется внутрь.
        """
        position = list(fish.position)
        velocity = list(fish.velocity)
        for axis in range(3):
            if position[axis] < self.low[axis]:
                position[axis] = self.low[axis]
                velocity[axis] = abs(velocity[axis])
            elif position[axis] > self.high[axis]:
                position[axis] = self.high[axis]
                velocity[axis] = -abs(velocity[axis])
        fish.position = tuple(position)
        fish.velocity = tuple(velocity)

    # --- Показатели стаи (для панели и исследования) ---

    def average_neighbor_count(self):
        if not self.fish:
            return 0.0
        return sum(len(ids) for ids in self.neighbors) / len(self.fish)

    def polarization(self):
        """Согласованность направлений: Φ = |Σ vᵢ/|vᵢ|| / N.

        Φ = 1, если все рыбы плывут в одну сторону; около 0 — если направления случайны.
        """
        total = (0.0, 0.0, 0.0)
        for fish in self.fish:
            speed = length(fish.velocity)
            if speed > 1e-9:
                total = add(total, scale(fish.velocity, 1.0 / speed))
        return length(total) / len(self.fish) if self.fish else 0.0
