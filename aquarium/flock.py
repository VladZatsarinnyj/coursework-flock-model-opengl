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
    food_weight: float = 1.5        # притяжение к корму (действует, если корм включён)

    def clamp(self):
        """Приводит все параметры к допустимым диапазонам из config."""
        self.separation_weight = _clamp(self.separation_weight, config.SEPARATION_WEIGHT_RANGE)
        self.alignment_weight = _clamp(self.alignment_weight, config.ALIGNMENT_WEIGHT_RANGE)
        self.cohesion_weight = _clamp(self.cohesion_weight, config.COHESION_WEIGHT_RANGE)
        self.neighbor_radius = _clamp(self.neighbor_radius, config.NEIGHBOR_RADIUS_RANGE)
        self.max_speed = _clamp(self.max_speed, config.MAX_SPEED_RANGE)
        self.food_weight = _clamp(self.food_weight, config.FOOD_WEIGHT_RANGE)


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
        # Счётчик касаний камней — показатель для сравнения режимов движения.
        self.rock_contacts = 0
        self.contact_time = 0.0     # модельное время, за которое накоплен счётчик, секунды
        self._touching = set()      # номера рыб, касавшихся камня на прошлом шаге
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
        self._touching = set()

    def respawn(self):
        """Раскладывает всех рыб заново в случайные места."""
        self.fish = [self._random_fish() for _ in self.fish]
        self._touching = set()

    # --- Шаг симуляции ---

    def step(self, dt, rocks=(), avoid_rocks=False, food=None):
        """Продвигает стаю на время dt.

        rocks       — камни сцены (scene.Rock); непроницаемы в любом режиме;
        avoid_rocks — режим «обход препятствий»: заранее отворачивать от камней;
        food        — положение корма или None, если корм выключен.

        Шаг выполняется в две фазы. Сначала по положению стаи на текущий момент
        вычисляются ускорения ВСЕХ рыб, затем все рыбы перемещаются. Если бы рыбы
        перемещались сразу по одной, вторая рыба видела бы уже сдвинутую первую,
        и результат зависел бы от порядка рыб в списке.
        """
        positions = [fish.position for fish in self.fish]
        self.neighbors = find_neighbors_naive(positions, self.params.neighbor_radius)

        accelerations = [self._acceleration(i, rocks, avoid_rocks, food) for i in range(len(self.fish))]

        touching = set()
        for i, (fish, acceleration) in enumerate(zip(self.fish, accelerations)):
            # Полунеявный метод Эйлера: сначала скорость, затем положение по новой скорости.
            velocity = add(fish.velocity, scale(acceleration, dt))
            fish.velocity = self._limit_speed(velocity)
            fish.position = add(fish.position, scale(fish.velocity, dt))
            if self._keep_out_of_rocks(fish, rocks):
                touching.add(i)
            self._keep_inside(fish)  # последней, чтобы рыба гарантированно осталась в аквариуме

        # Касание считается один раз — в момент, когда рыба впервые упёрлась в камень,
        # а не на каждом шаге, пока она скользит по его поверхности.
        self.rock_contacts += len(touching - self._touching)
        self._touching = touching
        self.contact_time += dt

    def force_components(self, i, rocks, avoid_rocks, food):
        """Слагаемые ускорения рыбы i: для расчёта движения и для показа векторами.

        Поведение — три правила стаи для соседей j рыбы i (их n штук) и корм:
            разделение  s = Σ (pᵢ − pⱼ) / |pᵢ − pⱼ|²  — от каждого соседа, сильнее вблизи
            выравнивание a = (Σ vⱼ) / n − vᵢ           — к средней скорости соседей
            сплочённость c = (Σ pⱼ) / n − pᵢ           — к центру соседей
            корм         f — см. _seek

        Ограничения — стенки, столкновения, обход камней — не зависят от весов.

        Возвращает два списка пар (название, вектор): правила (уже умноженные на веса)
        и ограничения. Как они складываются, описано в _acceleration.
        """
        fish = self.fish[i]
        params = self.params
        separation = (0.0, 0.0, 0.0)
        alignment = (0.0, 0.0, 0.0)
        cohesion = (0.0, 0.0, 0.0)
        collision = (0.0, 0.0, 0.0)

        neighbor_ids = self.neighbors[i]
        if neighbor_ids:
            velocity_sum = (0.0, 0.0, 0.0)
            position_sum = (0.0, 0.0, 0.0)
            for j in neighbor_ids:
                other = self.fish[j]
                away = sub(fish.position, other.position)
                distance_squared = dot(away, away)
                # Две рыбы точно в одной точке: направление не определено. Сила
                # столкновения не даёт им сблизиться, поэтому на практике это не случается.
                if distance_squared > 1e-9:
                    separation = add(separation, scale(away, 1.0 / distance_squared))
                    collision = add(collision, self._collision_force(away, math.sqrt(distance_squared)))
                velocity_sum = add(velocity_sum, other.velocity)
                position_sum = add(position_sum, other.position)

            n = len(neighbor_ids)
            alignment = sub(scale(velocity_sum, 1.0 / n), fish.velocity)
            cohesion = sub(scale(position_sum, 1.0 / n), fish.position)

        rules = [
            ("разделение", scale(separation, params.separation_weight)),
            ("выравнивание", scale(alignment, params.alignment_weight)),
            ("сплочённость", scale(cohesion, params.cohesion_weight)),
        ]
        if food is not None:
            rules.append(("корм", scale(self._seek(fish, food), params.food_weight)))

        constraints = [
            ("стенки", self._wall_force(fish.position)),
            ("столкновения", collision),
        ]
        if avoid_rocks:
            constraints.append(("обход камней", self._avoidance_force(fish, rocks)))
        return rules, constraints

    def _acceleration(self, i, rocks, avoid_rocks, food):
        """Ускорение рыбы i, единиц/с²:

            F = clamp(Σ правил, FISH_MAX_ACCELERATION) + Σ ограничений

        Правила ограничиваются по длине, ограничения — нет. Если бы ограничения
        урезались вместе с правилами, при большой сплочённости урезание уменьшило бы
        все слагаемые пропорционально: отталкивание не помешало бы рыбам слиться
        в точку, а обход не успел бы отвернуть рыбу от камня.
        """
        rules, constraints = self.force_components(i, rocks, avoid_rocks, food)
        total = (0.0, 0.0, 0.0)
        for _, vector in rules:
            total = add(total, vector)
        total = clamp_length(total, config.FISH_MAX_ACCELERATION)
        for _, vector in constraints:
            total = add(total, vector)
        return total

    def _seek(self, fish, target):
        """Стремление к цели (поведение seek, Reynolds, 1999).

        Желаемая скорость направлена на цель и равна максимальной; сила —
        разница между желаемой и текущей скоростью:
            desired = (target − p) / |target − p| · v_max,   f = desired − v
        Так рыба не просто получает толчок к корму, а поворачивает свою скорость к нему.
        """
        to_target = sub(target, fish.position)
        distance = length(to_target)
        if distance < 1e-9:
            return (0.0, 0.0, 0.0)
        desired = scale(to_target, self.params.max_speed / distance)
        return sub(desired, fish.velocity)

    @staticmethod
    def _avoidance_force(fish, rocks):
        """Упреждающий обход камней (obstacle avoidance, Reynolds, 1999).

        Рыба смотрит вперёд вдоль направления движения f = v/|v|. Для каждого камня
        с центром c и радиусом безопасности R' = R + зазор + запас:
            t = (c − p)·f        — проекция: насколько впереди лежит ближайшая к центру точка луча;
            q = p + t·f          — эта точка луча;
            |q − c|              — расстояние от центра камня до луча.
        Если камень впереди (t > 0), не дальше AVOID_LOOKAHEAD от рыбы и |q − c| < R',
        луч задевает камень. Из таких камней берётся ближайший (меньшее t).

        Сила направлена от центра камня к точке q — поперёк курса — и растёт по мере
        приближения:  F = F_обх · (1 − s / L) · (q − c)/|q − c|,  s = max(0, t − R').
        Если камень точно по курсу (q ≈ c), рыба отворачивает вверх: камни лежат на дне.
        """
        speed = length(fish.velocity)
        if speed < 1e-9:
            return (0.0, 0.0, 0.0)
        forward = scale(fish.velocity, 1.0 / speed)

        nearest = None  # (t, R', q − c) ближайшего камня на пути
        for rock in rocks:
            safe_radius = rock.radius + config.FISH_ROCK_PADDING + config.AVOID_CLEARANCE
            t = dot(sub(rock.center, fish.position), forward)
            if t <= 0.0 or t - safe_radius > config.AVOID_LOOKAHEAD:
                continue  # камень позади или слишком далеко
            closest = add(fish.position, scale(forward, t))
            offset = sub(closest, rock.center)
            if dot(offset, offset) >= safe_radius * safe_radius:
                continue  # луч проходит мимо камня
            if nearest is None or t < nearest[0]:
                nearest = (t, safe_radius, offset)

        if nearest is None:
            return (0.0, 0.0, 0.0)
        t, safe_radius, offset = nearest
        direction = (0.0, 1.0, 0.0) if length(offset) < 1e-6 else scale(offset, 1.0 / length(offset))
        distance_to_surface = max(0.0, t - safe_radius)
        return scale(direction, config.AVOID_FORCE * (1.0 - distance_to_surface / config.AVOID_LOOKAHEAD))

    @staticmethod
    def _collision_force(away, distance):
        """Отталкивание соседа, оказавшегося ближе личного пространства d₀.

        Сила направлена от соседа и растёт линейно, когда расстояние d уменьшается:
            F = COLLISION_FORCE · (d₀ − d) / d₀ · (pᵢ − pⱼ) / d,  при d < d₀
        Это та же схема, что у мягкой силы стенок, только «стенка» — тело соседа.
        """
        overlap = config.FISH_PERSONAL_SPACE - distance
        if overlap <= 0.0:
            return (0.0, 0.0, 0.0)
        strength = config.COLLISION_FORCE * overlap / config.FISH_PERSONAL_SPACE
        return scale(away, strength / distance)

    def _wall_force(self, position):
        """Мягкий разворот у стенок.

        Пока рыба дальше полосы margin от стенки, сила равна нулю. Ближе — сила
        направлена от стенки и растёт линейно: у самой границы она равна WALL_FORCE.
        У дна полоса уже (FLOOR_MARGIN), чем у стёкол и поверхности (WALL_MARGIN):
        рыбы плавают и у дна, среди камней и водорослей.
        """
        force = [0.0, 0.0, 0.0]
        for axis in range(3):
            low_margin = config.FLOOR_MARGIN if axis == 1 else config.WALL_MARGIN
            near_low = self.low[axis] + low_margin - position[axis]
            near_high = position[axis] - (self.high[axis] - config.WALL_MARGIN)
            if near_low > 0:
                force[axis] += config.WALL_FORCE * near_low / low_margin
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

    @staticmethod
    def _keep_out_of_rocks(fish, rocks):
        """Камни непроницаемы: рыба, заплывшая в камень, выталкивается на его поверхность.

        Для физики камень — сфера радиуса r с центром c. Если рыба ближе r + зазор
        к центру, она переносится на эту границу вдоль нормали n = (p − c)/|p − c|,
        а составляющая скорости, направленная в камень (v·n < 0), убирается:
            v ← v − (v·n)·n
        Остаётся скольжение вдоль поверхности камня. Камни внизу, поэтому рыбы,
        плывущие выше всех камней, не проверяются.
        Возвращает True, если рыбу пришлось вытолкнуть (рыба касается камня).
        """
        touched = False
        for rock in rocks:
            min_distance = rock.radius + config.FISH_ROCK_PADDING
            if fish.position[1] > rock.center[1] + min_distance:
                continue  # рыба выше камня
            away = sub(fish.position, rock.center)
            distance_squared = dot(away, away)
            if distance_squared >= min_distance * min_distance or distance_squared < 1e-12:
                continue
            normal = scale(away, 1.0 / math.sqrt(distance_squared))
            fish.position = add(rock.center, scale(normal, min_distance))
            inward = dot(fish.velocity, normal)
            if inward < 0.0:
                fish.velocity = sub(fish.velocity, scale(normal, inward))
            touched = True
        return touched

    # --- Показатели стаи (для панели и исследования) ---

    def reset_contact_stats(self):
        self.rock_contacts = 0
        self.contact_time = 0.0
        self._touching = set()

    def contacts_per_minute(self):
        """Касаний камней в минуту модельного времени с последнего сброса счётчика."""
        if self.contact_time <= 0.0:
            return 0.0
        return 60.0 * self.rock_contacts / self.contact_time

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
