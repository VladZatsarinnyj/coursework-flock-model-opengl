"""Векторы и матрицы для трёхмерной графики, без сторонних библиотек.

Вектор — кортеж из трёх чисел (x, y, z).
Матрица 4×4 — список из четырёх строк, элемент m[строка][столбец], как в учебнике.
"""

import math


# --- Векторы ---

def add(a, b):
    """Сумма векторов a + b."""
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def sub(a, b):
    """Разность векторов a − b."""
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def scale(v, k):
    """Умножение вектора на число."""
    return (v[0] * k, v[1] * k, v[2] * k)


def dot(a, b):
    """Скалярное произведение: a·b = |a|·|b|·cos(угла между ними)."""
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b):
    """Векторное произведение: вектор, перпендикулярный и a, и b."""
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def length(v):
    return math.sqrt(dot(v, v))


def normalize(v):
    """Вектор того же направления, но длины 1."""
    n = length(v)
    if n < 1e-9:
        raise ValueError("Нельзя нормировать вектор нулевой длины")
    return (v[0] / n, v[1] / n, v[2] / n)


def clamp_length(v, max_length):
    """Укорачивает вектор до max_length, если он длиннее; направление сохраняется."""
    n = length(v)
    if n > max_length:
        return scale(v, max_length / n)
    return v


# --- Матрицы ---

def perspective(fov_y_deg, aspect, near, far):
    """Матрица перспективной проекции.

    Переводит координаты камеры (камера в начале координат, смотрит вдоль −Z)
    в координаты отсечения. Последняя строка записывает в w расстояние до точки (−z).
    После деления на w дальние объекты становятся меньше, а видимая область
    превращается в куб [−1; 1]³ (нормализованные координаты устройства, NDC).
    """
    f = 1.0 / math.tan(math.radians(fov_y_deg) / 2.0)
    return [
        [f / aspect, 0.0, 0.0, 0.0],
        [0.0, f, 0.0, 0.0],
        [0.0, 0.0, (far + near) / (near - far), 2.0 * far * near / (near - far)],
        [0.0, 0.0, -1.0, 0.0],
    ]


def look_at(eye, target, up):
    """Матрица вида: переводит мировые координаты в координаты камеры.

    Базис камеры:
        forward = normalize(target − eye)   — куда смотрит камера
        right   = normalize(forward × up)   — вправо от камеры
        true_up = right × forward           — вверх от камеры

    Строки матрицы — оси камеры, последний столбец — сдвиг, переносящий
    камеру в начало координат. В OpenGL камера смотрит вдоль −Z, поэтому
    третья строка равна −forward.
    """
    forward = normalize(sub(target, eye))
    right = normalize(cross(forward, up))
    true_up = cross(right, forward)
    return [
        [right[0], right[1], right[2], -dot(right, eye)],
        [true_up[0], true_up[1], true_up[2], -dot(true_up, eye)],
        [-forward[0], -forward[1], -forward[2], dot(forward, eye)],
        [0.0, 0.0, 0.0, 1.0],
    ]


def to_opengl(matrix):
    """16 чисел матрицы в порядке, который ожидает OpenGL.

    OpenGL читает матрицу по столбцам (column-major): сначала первый столбец,
    затем второй и т. д. Наша матрица записана по строкам, поэтому числа
    перебираются «столбец за столбцом».
    """
    return tuple(matrix[row][col] for col in range(4) for row in range(4))
