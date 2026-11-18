"""Выбор рыбы щелчком мыши: луч из камеры через курсор и его пересечение со сферами рыб.

Не использует OpenGL: всё строится из матрицы вида и угла обзора камеры.
"""

import math

from aquarium import config
from aquarium.mathutils import add, dot, normalize, scale, sub


def mouse_ray(camera, mouse_x, mouse_y, width, height):
    """Луч из глаза камеры через точку экрана (обратное проецирование).

    1. Пиксель → нормализованные координаты устройства (NDC), от −1 до 1:
           x = 2·mx / width − 1,   y = 1 − 2·my / height
       (ось y экрана направлена вниз, а в NDC — вверх).
    2. На расстоянии 1 перед камерой видимая область имеет полувысоту tan(fov/2)
       и полуширину tan(fov/2)·aspect — это обратное к тому, что делает матрица проекции.
    3. Строки матрицы вида — оси камеры в мировых координатах: right, up и −forward.
       Направление луча: normalize(right·x·tan·aspect + up·y·tan + forward).
    Возвращает (начало, единичное направление).
    """
    x_ndc = 2.0 * mouse_x / width - 1.0
    y_ndc = 1.0 - 2.0 * mouse_y / height
    tan_half = math.tan(math.radians(config.CAMERA_FOV_DEG) / 2.0)
    aspect = width / height

    view = camera.view_matrix()
    right = tuple(view[0][:3])
    up = tuple(view[1][:3])
    forward = scale(tuple(view[2][:3]), -1.0)

    direction = add(add(scale(right, x_ndc * tan_half * aspect), scale(up, y_ndc * tan_half)), forward)
    return camera.eye_position(), normalize(direction)


def ray_sphere_distance(origin, direction, center, radius):
    """Расстояние вдоль луча до первой точки пересечения со сферой или None.

    t = (c − o)·d — проекция центра на луч; d² = |c − o|² − t² — квадрат расстояния
    от центра до луча (теорема Пифагора). Если d² > r², луч проходит мимо.
    Иначе точки пересечения — t ± √(r² − d²); берётся ближняя, лежащая впереди.
    """
    to_center = sub(center, origin)
    t = dot(to_center, direction)
    distance_squared = dot(to_center, to_center) - t * t
    if distance_squared > radius * radius:
        return None
    half_chord = math.sqrt(radius * radius - distance_squared)
    if t - half_chord >= 0.0:
        return t - half_chord
    if t + half_chord >= 0.0:
        return 0.0  # камера внутри сферы
    return None  # сфера позади камеры


def pick_fish(origin, direction, fish_list):
    """Номер ближайшей к камере рыбы, в чью сферу попал луч, или None."""
    best_index, best_distance = None, math.inf
    for i, fish in enumerate(fish_list):
        distance = ray_sphere_distance(origin, direction, fish.position, config.FISH_PICK_RADIUS)
        if distance is not None and distance < best_distance:
            best_index, best_distance = i, distance
    return best_index
