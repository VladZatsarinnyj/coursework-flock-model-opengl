"""Поиск соседей: для каждой рыбы — номера рыб, которые ближе заданного радиуса.

Сейчас здесь полный перебор пар. Позже (КТ7) сюда добавится поиск
по пространственной сетке, и их скорость можно будет сравнить.
"""


def find_neighbors_naive(positions, radius):
    """Полный перебор всех пар: O(N²) проверок расстояния.

    positions — список точек (x, y, z), radius — радиус соседства.
    Возвращает список списков: neighbors[i] — номера соседей рыбы i.

    Соседство симметрично: если j — сосед i, то и i — сосед j. Поэтому каждая
    пара (i, j) проверяется один раз, при j > i: это вдвое меньше проверок,
    чем N·(N − 1), но порядок роста остаётся квадратичным.
    """
    count = len(positions)
    radius_squared = radius * radius  # сравниваем квадраты, чтобы не вычислять корень
    neighbors = [[] for _ in range(count)]
    for i in range(count):
        xi, yi, zi = positions[i]
        for j in range(i + 1, count):
            xj, yj, zj = positions[j]
            dx, dy, dz = xi - xj, yi - yj, zi - zj
            if dx * dx + dy * dy + dz * dz < radius_squared:
                neighbors[i].append(j)
                neighbors[j].append(i)
    return neighbors
