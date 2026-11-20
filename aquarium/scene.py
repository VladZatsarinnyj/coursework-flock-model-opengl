"""Объекты сцены: камни, водоросли, пузырьки, корм. Не использует OpenGL."""

import math
import random
from dataclasses import dataclass

from aquarium import config
from aquarium.mathutils import add, scale, sub


@dataclass
class Rock:
    center: tuple
    radius: float
    color: tuple
    shape_seed: int


@dataclass
class Seaweed:
    base: tuple
    segment_count: int
    segment_length: float
    sway_direction: tuple
    phase: float
    color: tuple


@dataclass
class Bubble:
    base_x: float
    base_z: float
    y: float
    speed: float
    radius: float
    phase: float


def _clamp_count(value, value_range):
    return int(max(value_range[0], min(value_range[1], int(value))))


def horizontal_distance(a, b):
    """Расстояние между точками в плане (по осям X и Z, без учёта высоты)."""
    return math.hypot(a[0] - b[0], a[2] - b[2])


class Scene:
    """Камни, водоросли, пузырьки и корм; время сцены и анимация."""

    def __init__(self):
        self.random = random.Random(config.SCENE_RANDOM_SEED)
        self.time = 0.0
        self.sway_strength = config.SWAY_STRENGTH_DEFAULT
        self.rocks = []
        self.seaweed = []
        self.bubbles = []
        self.rocks_version = 0
        self.set_rock_count(config.ROCK_COUNT_DEFAULT)
        self.set_seaweed_count(config.SEAWEED_COUNT_DEFAULT)
        self.set_bubble_count(config.BUBBLE_COUNT_DEFAULT)
        self.food_offsets = [self._random_offset(config.FOOD_CLUSTER_RADIUS) for _ in range(config.FOOD_FLAKES)]
        self.food_eaten = [False] * config.FOOD_FLAKES
        self.food_time_offset = 0.0
        self.food_respawn_timer = 0.0
        self.portion_age = 0.0
        self.search_times = []

    def _random_floor_point(self, margin):
        """Случайная точка на дне, не ближе margin к стёклам."""
        low, high = config.AQUARIUM_MIN, config.AQUARIUM_MAX
        x = self.random.uniform(low[0] + margin, high[0] - margin)
        z = self.random.uniform(low[2] + margin, high[2] - margin)
        return (x, 0.0, z)

    def _find_free_point(self, margin, is_free):
        """Метод проб: берём случайные точки, пока не найдём подходящую.

        is_free — функция, которая для точки отвечает True или False.
        Если за PLACEMENT_ATTEMPTS попыток места не нашлось, возвращается None.
        """
        for _ in range(config.PLACEMENT_ATTEMPTS):
            point = self._random_floor_point(margin)
            if is_free(point):
                return point
        return None

    def _clear_of_rocks(self, point, clearance):
        """True, если точка в плане дальше clearance от края каждого камня."""
        return all(horizontal_distance(point, rock.center) >= rock.radius + clearance
                   for rock in self.rocks)

    def set_rock_count(self, count):
        """Добавляет камни в свободные места или убирает лишние с конца списка."""
        count = _clamp_count(count, config.ROCK_COUNT_RANGE)
        del self.rocks[count:]
        while len(self.rocks) < count:
            rock = self._new_rock()
            if rock is None:
                break
            self.rocks.append(rock)
        self.rocks_version += 1
        self._move_plants_out_of_rocks()
        self._move_bubbles_out_of_rocks()

    def _new_rock(self):
        """Камень случайного размера в свободном месте дна.

        Если для камня такого размера места не нашлось, пробуется камень меньше
        (на ROCK_SHRINK_STEP), вплоть до минимального радиуса. Без этого при
        15 камнях на дне иногда помещалось только 11–14.
        """
        min_radius = config.ROCK_RADIUS_RANGE[0]
        radius = self.random.uniform(*config.ROCK_RADIUS_RANGE)
        while True:
            point = self._find_free_point(radius + config.ROCK_WALL_MARGIN,
                                          lambda p: self._clear_of_rocks(p, radius + config.ROCK_GAP))
            if point is not None:
                break
            if radius <= min_radius:
                return None
            radius = max(min_radius, radius - config.ROCK_SHRINK_STEP)
        center = (point[0], config.ROCK_CENTER_HEIGHT * radius, point[2])
        return Rock(center, radius, self.random.choice(config.ROCK_COLORS),
                    self.random.randrange(1_000_000))

    def set_seaweed_count(self, count):
        count = _clamp_count(count, config.SEAWEED_COUNT_RANGE)
        del self.seaweed[count:]
        while len(self.seaweed) < count:
            plant = self._new_plant()
            if plant is None:
                break
            self.seaweed.append(plant)

    def _plant_fits(self, point):
        far_from_rocks = self._clear_of_rocks(point, 0.3)
        far_from_plants = all(horizontal_distance(point, plant.base) >= config.SEAWEED_SPACING
                              for plant in self.seaweed)
        return far_from_rocks and far_from_plants

    def _new_plant(self):
        point = self._find_free_point(config.SEAWEED_WALL_MARGIN, self._plant_fits)
        if point is None:
            return None
        segment_count = self.random.randint(*config.SEAWEED_SEGMENTS_RANGE)
        height = self.random.uniform(*config.SEAWEED_HEIGHT_RANGE)
        yaw = self.random.uniform(0.0, 2.0 * math.pi)
        return Seaweed(
            base=point,
            segment_count=segment_count,
            segment_length=height / segment_count,
            sway_direction=(math.cos(yaw), 0.0, math.sin(yaw)),
            phase=self.random.uniform(0.0, 2.0 * math.pi),
            color=self.random.choice(config.SEAWEED_COLORS),
        )

    def _move_plants_out_of_rocks(self):
        """Водоросли, на которые «лёг» новый камень, переносятся в свободное место."""
        for i, plant in enumerate(self.seaweed):
            if not self._clear_of_rocks(plant.base, 0.3):
                replacement = self._new_plant()
                if replacement is not None:
                    self.seaweed[i] = replacement
        self.seaweed = [plant for plant in self.seaweed if self._clear_of_rocks(plant.base, 0.3)]

    def set_sway_strength(self, value):
        self.sway_strength = max(config.SWAY_STRENGTH_RANGE[0],
                                 min(config.SWAY_STRENGTH_RANGE[1], float(value)))

    def seaweed_segments(self):
        """Положения всех сегментов всех водорослей в текущий момент времени.

        Водоросль — кинематическая цепь: каждый сегмент начинается в конце
        предыдущего и повёрнут относительно него на небольшой угол

            θₖ(t) = s · A · sin(ω·t + φ − k·δ),

        где s — сила колебаний, A — амплитуда для одного сегмента, φ — фаза
        водоросли, δ — сдвиг фазы между соседними сегментами. Наклон сегмента k
        от вертикали равен сумме углов всех сегментов ниже: αₖ = θ₀ + θ₁ + … + θₖ.
        Поэтому верхушка отклоняется сильнее основания, а сдвиг δ создаёт волну,
        бегущую от основания вверх.

        Возвращает список (начало, конец, ширина_в_начале, ширина_в_конце, цвет).
        """
        segments = []
        for plant in self.seaweed:
            start = plant.base
            angle = 0.0
            n = plant.segment_count
            for k in range(n):
                angle += self.sway_strength * config.SEAWEED_SEGMENT_ANGLE * math.sin(
                    config.SEAWEED_SWAY_FREQUENCY * self.time + plant.phase - config.SEAWEED_WAVE_LAG * k)
                direction = add(scale(plant.sway_direction, math.sin(angle)), (0.0, math.cos(angle), 0.0))
                end = add(start, scale(direction, plant.segment_length))
                width_start = self._seaweed_width(k / n)
                width_end = self._seaweed_width((k + 1) / n)
                segments.append((start, end, width_start, width_end, plant.color))
                start = end
        return segments

    @staticmethod
    def _seaweed_width(t):
        """Ширина водоросли на доле высоты t ∈ [0; 1]: линейно сужается к верхушке."""
        return config.SEAWEED_BASE_WIDTH + (config.SEAWEED_TIP_WIDTH - config.SEAWEED_BASE_WIDTH) * t

    def set_bubble_count(self, count):
        count = _clamp_count(count, config.BUBBLE_COUNT_RANGE)
        del self.bubbles[count:]
        while len(self.bubbles) < count:
            self.bubbles.append(self._new_bubble(self.random.uniform(0.0, config.AQUARIUM_HEIGHT)))

    def _new_bubble(self, y):
        radius = self.random.uniform(*config.BUBBLE_RADIUS_RANGE)

        def fits(point):
            return self._clear_of_rocks(point, radius)

        point = self._find_free_point(0.3, fits) or self._random_floor_point(0.3)
        return Bubble(point[0], point[2], y, self.random.uniform(*config.BUBBLE_SPEED_RANGE),
                      radius, self.random.uniform(0.0, 2.0 * math.pi))

    def _move_bubbles_out_of_rocks(self):
        for i, bubble in enumerate(self.bubbles):
            if not self._clear_of_rocks((bubble.base_x, 0.0, bubble.base_z), bubble.radius):
                self.bubbles[i] = self._new_bubble(bubble.y)

    def bubble_instances(self):
        """Положение и радиус каждого пузырька с учётом покачивания по окружности."""
        instances = []
        for bubble in self.bubbles:
            angle = config.BUBBLE_WOBBLE_FREQUENCY * self.time + bubble.phase
            position = (bubble.base_x + config.BUBBLE_WOBBLE * math.sin(angle),
                        bubble.y,
                        bubble.base_z + config.BUBBLE_WOBBLE * math.cos(angle))
            instances.append((position, bubble.radius))
        return instances

    def _random_offset(self, radius):
        """Случайная точка внутри шара радиуса radius (метод проб внутри куба)."""
        while True:
            offset = tuple(self.random.uniform(-radius, radius) for _ in range(3))
            if offset[0] ** 2 + offset[1] ** 2 + offset[2] ** 2 <= radius * radius:
                return offset

    def food_position(self):
        """Центр корма в текущий момент: фигура Лиссажу.

        По каждой оси — своя синусоида со своей частотой:
            x = cx + Ax·sin(ωx·t),  y = cy + Ay·sin(ωy·t),  z = cz + Az·cos(ωz·t)
        Частоты не кратны друг другу, поэтому траектория долго не повторяется
        и корм обходит почти весь верхний объём аквариума.
        """
        center, amplitude, frequency = config.FOOD_CENTER, config.FOOD_AMPLITUDE, config.FOOD_FREQUENCY
        t = self.time + self.food_time_offset
        return (center[0] + amplitude[0] * math.sin(frequency[0] * t),
                center[1] + amplitude[1] * math.sin(frequency[1] * t),
                center[2] + amplitude[2] * math.cos(frequency[2] * t))

    def _flake_positions(self):
        """Положения всех хлопьев порции: смещения вращаются вокруг вертикали, облачко «кружится»."""
        center = self.food_position()
        angle = config.FOOD_SPIN * self.time
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        return [add(center, (x * cos_a - z * sin_a, y, x * sin_a + z * cos_a)) for x, y, z in self.food_offsets]

    def food_flakes(self):
        """Несъеденные хлопья для отрисовки: (центр, радиус)."""
        return [(position, config.FOOD_FLAKE_RADIUS)
                for position, eaten in zip(self._flake_positions(), self.food_eaten) if not eaten]

    def food_available(self):
        """True, пока в аквариуме есть порция корма (а не пауза после съедания)."""
        return self.food_respawn_timer <= 0.0

    def update_food(self, dt, fish_positions):
        """Кормление; вызывается на каждом шаге симуляции, пока корм включён.

        Рыба, центр которой ближе FOOD_EAT_RADIUS к хлопью, съедает его; за один шаг
        рыба съедает не больше одного хлопья. Когда съедены все хлопья, порция исчезает,
        а через FOOD_RESPAWN_DELAY секунд новая появляется дальше по траектории —
        в другом месте аквариума, и стая плывёт туда.
        """
        if not self.food_available():
            self.food_respawn_timer -= dt
            if self.food_available():
                self._new_food_portion()
            return

        self.portion_age += dt
        flakes = self._flake_positions()
        eat_radius_squared = config.FOOD_EAT_RADIUS * config.FOOD_EAT_RADIUS
        for fish_position in fish_positions:
            for k, flake in enumerate(flakes):
                if self.food_eaten[k]:
                    continue
                offset = sub(flake, fish_position)
                if offset[0] ** 2 + offset[1] ** 2 + offset[2] ** 2 < eat_radius_squared:
                    self.food_eaten[k] = True
                    break

        if all(self.food_eaten):
            self.search_times.append(self.portion_age)
            self.food_respawn_timer = config.FOOD_RESPAWN_DELAY

    def _new_food_portion(self):
        """Новая порция: перенос вперёд по траектории на случайное время."""
        self.food_time_offset += self.random.uniform(*config.FOOD_JUMP_RANGE)
        self.food_eaten = [False] * config.FOOD_FLAKES
        self.portion_age = 0.0

    def portions_eaten(self):
        return len(self.search_times)

    def average_search_time(self):
        """Среднее время от появления порции до её полного съедания, секунды."""
        if not self.search_times:
            return 0.0
        return sum(self.search_times) / len(self.search_times)

    def reset_food_stats(self):
        self.search_times = []

    def step(self, dt):
        """Продвигает время сцены и поднимает пузырьки.

        Пузырёк, достигший поверхности, рождается заново на дне в новом месте.
        Так число пузырьков постоянно, а новые объекты не создаются бесконечно.
        """
        self.time += dt
        for i, bubble in enumerate(self.bubbles):
            bubble.y += bubble.speed * dt
            if bubble.y + bubble.radius >= config.AQUARIUM_HEIGHT:
                self.bubbles[i] = self._new_bubble(0.0)

    def shuffle(self):
        """Новая расстановка: камни и водоросли в новых случайных местах."""
        rock_count, plant_count = len(self.rocks), len(self.seaweed)
        self.rocks.clear()
        self.seaweed.clear()
        self.set_rock_count(rock_count)
        self.set_seaweed_count(plant_count)
