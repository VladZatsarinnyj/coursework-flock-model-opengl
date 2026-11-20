"""Ограничения движения рыб: стенки аквариума, тела соседей, камни. Не использует OpenGL.

В отличие от правил стаи, эти силы и поправки не зависят от весов в панели:
рыба не может выплыть из аквариума, пройти сквозь соседа или сквозь камень
ни при каких настройках. Обход камней — тоже здесь: это упреждающая реакция
на те же камни (режим «обход препятствий»).

low и high — углы области, в которой может находиться центр рыбы
(аквариум минус зазор до стекла, см. Flock.__init__).
"""

import math

from aquarium import config
from aquarium.mathutils import add, dot, length, scale, sub


def wall_force(position, low, high):
    """Мягкий разворот у стенок.

    Пока рыба дальше полосы margin от стенки, сила равна нулю. Ближе — сила
    направлена от стенки и растёт линейно: у самой границы она равна WALL_FORCE.
    У дна полоса уже (FLOOR_MARGIN), чем у стёкол и поверхности (WALL_MARGIN):
    рыбы плавают и у дна, среди камней и водорослей.
    """
    force = [0.0, 0.0, 0.0]
    for axis in range(3):
        low_margin = config.FLOOR_MARGIN if axis == 1 else config.WALL_MARGIN
        near_low = low[axis] + low_margin - position[axis]
        near_high = position[axis] - (high[axis] - config.WALL_MARGIN)
        if near_low > 0:
            force[axis] += config.WALL_FORCE * near_low / low_margin
        if near_high > 0:
            force[axis] -= config.WALL_FORCE * near_high / config.WALL_MARGIN
    return tuple(force)


def keep_inside(fish, low, high):
    """Жёсткая граница на случай, если мягкой силы не хватило.

    Рыба возвращается на границу, а скорость вдоль этой оси направляется внутрь.
    """
    position = list(fish.position)
    velocity = list(fish.velocity)
    for axis in range(3):
        if position[axis] < low[axis]:
            position[axis] = low[axis]
            velocity[axis] = abs(velocity[axis])
        elif position[axis] > high[axis]:
            position[axis] = high[axis]
            velocity[axis] = -abs(velocity[axis])
    fish.position = tuple(position)
    fish.velocity = tuple(velocity)


def collision_force(away, distance):
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


def push_out_of_rocks(fish, rocks):
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


def avoidance_force(fish, rocks):
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
