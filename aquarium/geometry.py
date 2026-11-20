"""Геометрия сцены: списки вершин для загрузки в видеопамять.

Каждая функция возвращает плоский список чисел. Треугольники идут подряд:
каждые 3 вершины образуют один треугольник, каждые 2 — один отрезок (для рёбер).

Вершина освещаемой поверхности — 6 чисел: позиция (x, y, z) и нормаль (nx, ny, nz).
Нормаль — единичный вектор, перпендикулярный поверхности; по ней считается освещение.
"""

import math
import random

from aquarium import config
from aquarium.mathutils import add, cross, dot, normalize, scale, sub


def _face(name, low, high):
    """Нормаль и 4 угла грани параллелепипеда.

    Углы перечислены против часовой стрелки, если смотреть на грань снаружи.
    По этому порядку обхода OpenGL определяет лицевую сторону треугольника.
    """
    x0, y0, z0 = low
    x1, y1, z1 = high
    faces = {
        "right":  ((1, 0, 0),  [(x1, y0, z1), (x1, y0, z0), (x1, y1, z0), (x1, y1, z1)]),
        "left":   ((-1, 0, 0), [(x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)]),
        "top":    ((0, 1, 0),  [(x0, y1, z1), (x1, y1, z1), (x1, y1, z0), (x0, y1, z0)]),
        "front":  ((0, 0, 1),  [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]),
        "back":   ((0, 0, -1), [(x1, y0, z0), (x0, y0, z0), (x0, y1, z0), (x1, y1, z0)]),
    }
    return faces[name]


def _quad(normal, corners):
    """Четырёхугольник как два треугольника: (0, 1, 2) и (0, 2, 3)."""
    vertices = []
    for index in (0, 1, 2, 0, 2, 3):
        vertices.extend(corners[index])
        vertices.extend(normal)
    return vertices


def box_walls(low, high):
    """Стенки и крышка аквариума (5 граней, без дна): 5 × 2 треугольника × 3 вершины = 30 вершин.

    Нормали направлены наружу. У каждой грани свои вершины: угол коробки
    принадлежит трём граням с разными нормалями, поэтому вершины не общие.
    """
    vertices = []
    for name in ("right", "left", "top", "front", "back"):
        normal, corners = _face(name, low, high)
        vertices.extend(_quad(normal, corners))
    return vertices


def floor(low, high):
    """Прямоугольник дна в плоскости y = low.y, лицевой стороной вверх."""
    x0, y0, z0 = low
    x1, _, z1 = high
    corners = [(x0, y0, z1), (x1, y0, z1), (x1, y0, z0), (x0, y0, z0)]
    return _quad((0, 1, 0), corners)


def box_edges(low, high):
    """12 рёбер параллелепипеда: 24 вершины (x, y, z), каждые две — отрезок."""
    x0, y0, z0 = low
    x1, y1, z1 = high
    corners = [
        (x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1),
        (x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1),
    ]
    edges = [
        (0, 1), (1, 2), (2, 3), (3, 0),
        (4, 5), (5, 6), (6, 7), (7, 4),
        (0, 4), (1, 5), (2, 6), (3, 7),
    ]
    vertices = []
    for start, end in edges:
        vertices.extend(corners[start])
        vertices.extend(corners[end])
    return vertices


def _triangle(a, b, c):
    """Треугольник с нормалью, вычисленной по порядку вершин: n = normalize((b − a) × (c − a)).

    При обходе a → b → c против часовой стрелки нормаль смотрит на наблюдателя.
    """
    normal = normalize(cross(sub(b, a), sub(c, a)))
    vertices = []
    for point in (a, b, c):
        vertices.extend(point)
        vertices.extend(normal)
    return vertices


def fish(fish_length):
    """Упрощённая модель рыбы: ромбовидное тело (8 треугольников) и хвост (1 треугольник).

    Рыба смотрит вдоль оси +X, спина — вдоль +Y, правый бок — вдоль +Z.
    Повернуть рыбу по направлению движения — задача вершинного шейдера fish.vert.
    """
    k = fish_length / 1.35
    nose = (0.60 * k, 0.0, 0.0)
    back = (-0.40 * k, 0.0, 0.0)
    top = (0.05 * k, 0.20 * k, 0.0)
    bottom = (0.05 * k, -0.18 * k, 0.0)
    right = (0.05 * k, 0.0, 0.12 * k)
    left = (0.05 * k, 0.0, -0.12 * k)
    tail_root = (-0.35 * k, 0.0, 0.0)
    tail_top = (-0.75 * k, 0.22 * k, 0.0)
    tail_bottom = (-0.75 * k, -0.22 * k, 0.0)

    vertices = []
    ring = [top, right, bottom, left, top]
    for current, following in zip(ring, ring[1:]):
        vertices.extend(_triangle(nose, current, following))
        vertices.extend(_triangle(back, following, current))
    vertices.extend(_triangle(tail_root, tail_top, tail_bottom))
    return vertices


def sphere(rings, segments, point_at):
    """UV-сфера: rings поясов по широте и segments долей по долготе, как на глобусе.

    Для каждого узла сетки вычисляется единичное направление из центра:
        direction = (sin θ · cos φ, cos θ, sin θ · sin φ),  θ ∈ [0; π], φ ∈ [0; 2π)
    point_at(direction) возвращает, где поставить вершину. Для пузырька это сама точка
    единичной сферы, для камня — точка с неровностями (см. rock).

    Соседние узлы двух поясов образуют четырёхугольник из двух треугольников.
    На полюсах все узлы пояса совпадают, и там остаётся по одному треугольнику.
    Нормали — по граням (_triangle), поэтому поверхность выглядит гранёной.
    """
    grid = []
    for i in range(rings + 1):
        theta = math.pi * i / rings
        row = []
        for j in range(segments):
            phi = 2.0 * math.pi * j / segments
            direction = (math.sin(theta) * math.cos(phi), math.cos(theta), math.sin(theta) * math.sin(phi))
            row.append(point_at(direction))
        grid.append(row)

    vertices = []
    for i in range(rings):
        for j in range(segments):
            j_next = (j + 1) % segments
            a, b = grid[i][j], grid[i][j_next]
            c, d = grid[i + 1][j], grid[i + 1][j_next]
            if i != 0:
                vertices.extend(_triangle(a, b, d))
            if i != rings - 1:
                vertices.extend(_triangle(a, d, c))
    return vertices


def unit_sphere():
    """Низкополигональная сфера радиуса 1 для пузырьков (размер задаёт шейдер)."""
    return sphere(6, 8, lambda direction: direction)


def rock(center, radius, seed):
    """Неровный камень в мировых координатах.

    Радиус в направлении d меняется плавно — как сумма трёх синусоид вдоль
    случайных осей:
        r(d) = radius · (1 + Σ a · sin(fₖ · (d·axisₖ) + phaseₖ))
    Оси, частоты и фазы берутся из генератора с начальным числом seed, поэтому
    один и тот же камень всегда имеет одну и ту же форму. Часть камня ниже дна
    «срезается»: такие вершины поднимаются на уровень дна.
    """
    rng = random.Random(seed)
    bumps = []
    for _ in range(3):
        axis = normalize((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 1)))
        bumps.append((axis, rng.uniform(2.0, 4.0), rng.uniform(0.0, 2.0 * math.pi)))

    def point_at(direction):
        factor = 1.0 + sum(config.ROCK_ROUGHNESS * math.sin(frequency * dot(direction, axis) + phase)
                           for axis, frequency, phase in bumps)
        x, y, z = add(center, scale(direction, radius * factor))
        return (x, max(y, 0.0), z)

    return sphere(7, 10, point_at)


def seaweed_segment():
    """Модель одного сегмента водоросли: две перпендикулярные пластины («крест» сверху).

    Ширина 1 (x и z от −0.5 до 0.5), высота 1 (y от 0 до 1). Реальные длину,
    ширину и наклон задаёт шейдер seaweed.vert. Одна плоская пластина при взгляде
    с ребра исчезала бы, крест виден с любой стороны. Пластины видны с обеих
    сторон: нормаль разворачивает фрагментный шейдер (gl_FrontFacing).
    """
    plate_a = _quad((0, 0, 1), [(-0.5, 0, 0), (0.5, 0, 0), (0.5, 1, 0), (-0.5, 1, 0)])
    plate_b = _quad((1, 0, 0), [(0, 0, 0.5), (0, 0, -0.5), (0, 1, -0.5), (0, 1, 0.5)])
    return plate_a + plate_b


def circle_points(center, radius, axis_u, axis_v, segments):
    """Точки окружности в плоскости, натянутой на единичные векторы axis_u и axis_v:
        p(φ) = center + radius·(cos φ·u + sin φ·v),  φ = 2π·k / segments
    Последняя точка совпадает с первой, чтобы окружность была замкнутой.
    """
    points = []
    for k in range(segments + 1):
        angle = 2.0 * math.pi * k / segments
        offset = add(scale(axis_u, math.cos(angle)), scale(axis_v, math.sin(angle)))
        points.append(add(center, scale(offset, radius)))
    return points


def sphere_outline(center, radius, segments):
    """Каркас сферы — три взаимно перпендикулярные окружности (как гироскоп).

    Возвращает список отрезков (начало, конец) для отрисовки линиями.
    """
    x, y, z = (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)
    segments_list = []
    for axis_u, axis_v in ((x, y), (y, z), (z, x)):
        points = circle_points(center, radius, axis_u, axis_v, segments)
        segments_list.extend(zip(points, points[1:]))
    return segments_list
