"""Все настройки программы в одном месте."""

from dataclasses import dataclass

# --- Окно ---
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 800
WINDOW_TITLE = "Аквариум со стаей"
MSAA_SAMPLES = 4  # сглаживание краёв: число выборок на пиксель

# --- Аквариум ---
# Мировая система координат: ось Y направлена вверх, дно лежит в плоскости y = 0,
# центр дна совпадает с началом координат.
AQUARIUM_WIDTH = 24.0   # размер по оси X
AQUARIUM_HEIGHT = 12.0  # размер по оси Y
AQUARIUM_DEPTH = 14.0   # размер по оси Z
AQUARIUM_MIN = (-AQUARIUM_WIDTH / 2, 0.0, -AQUARIUM_DEPTH / 2)
AQUARIUM_MAX = (AQUARIUM_WIDTH / 2, AQUARIUM_HEIGHT, AQUARIUM_DEPTH / 2)
AQUARIUM_CENTER = (0.0, AQUARIUM_HEIGHT / 2, 0.0)

# --- Цвета (R, G, B), каждая компонента от 0 до 1 ---
BACKGROUND_COLOR = (0.02, 0.06, 0.10)
SAND_COLOR = (0.76, 0.68, 0.50)
GLASS_COLOR = (0.60, 0.85, 0.95)
EDGE_COLOR = (0.80, 0.95, 1.00)

# Направление НА источник света (сверху и немного сбоку).
LIGHT_DIRECTION = (0.35, 1.0, 0.25)

# --- Камера ---
CAMERA_FOV_DEG = 50.0      # вертикальный угол обзора
CAMERA_NEAR = 0.1          # ближняя плоскость отсечения
CAMERA_FAR = 300.0         # дальняя плоскость отсечения
CAMERA_START_YAW_DEG = 35.0
CAMERA_START_PITCH_DEG = 25.0
CAMERA_START_DISTANCE = 38.0
CAMERA_MIN_DISTANCE = 2.0
CAMERA_MAX_DISTANCE = 150.0
MOUSE_ROTATION_SPEED = 0.3  # градусов поворота на пиксель движения мыши
MOUSE_ZOOM_STEP = 0.9       # во сколько раз меняется расстояние за щелчок колеса

# --- Симуляция ---
# Стая рассчитывается с постоянным шагом времени, независимо от FPS (см. App.run).
SIM_DT = 1.0 / 60.0          # шаг симуляции, секунды
SIM_TIME_BUDGET = 0.010      # не больше 10 мс реального времени на симуляцию за кадр
MAX_FRAME_TIME = 0.25        # кадр дольше этого (например, перетаскивание окна) не догоняется
RANDOM_SEED = 42             # одинаковое начальное состояние стаи при каждом запуске

# --- Стая ---
FISH_COUNT_DEFAULT = 80
FISH_COUNT_MIN = 10
FISH_COUNT_MAX = 300
FISH_LENGTH = 1.2            # длина модели рыбы
FISH_MIN_SPEED = 1.5         # рыба не останавливается полностью
FISH_MAX_ACCELERATION = 8.0  # ограничение суммарной силы трёх правил стаи
# Личное пространство: ближе этого расстояния тела рыб пересекались бы.
# Сила столкновения действует всегда и не зависит от весов правил (как и непроницаемость стёкол).
FISH_PERSONAL_SPACE = 1.0
COLLISION_FORCE = 100.0      # сила отталкивания при полном совпадении положений
WALL_MARGIN = 2.5            # с какого расстояния до стенки рыба начинает разворачиваться
FLOOR_MARGIN = 1.5           # то же для дна: полоса уже, рыбы плавают и среди камней
WALL_FORCE = 12.0            # сила разворота у самой стенки
WALL_PADDING = 0.6           # минимальный зазор между центром рыбы и стеклом

# Допустимые значения параметров стаи: используются и ползунками, и проверкой в FlockParams.
SEPARATION_WEIGHT_RANGE = (0.0, 5.0)
ALIGNMENT_WEIGHT_RANGE = (0.0, 5.0)
COHESION_WEIGHT_RANGE = (0.0, 5.0)
# Радиус соседства не меньше FISH_PERSONAL_SPACE: столкновения ищутся среди соседей.
NEIGHBOR_RADIUS_RANGE = (1.0, 8.0)
MAX_SPEED_RANGE = (2.0, 10.0)
FOOD_WEIGHT_RANGE = (0.0, 5.0)

# Окраска рыб: рыба с номером i получает цвет FISH_COLORS[i % len(FISH_COLORS)].
FISH_COLORS = [
    (1.00, 0.55, 0.15),  # оранжевый
    (1.00, 0.75, 0.20),  # золотистый
    (0.95, 0.40, 0.30),  # коралловый
    (1.00, 0.85, 0.55),  # светло-жёлтый
]

# --- Сцена ---
# Объекты размещаются случайно, но воспроизводимо: свой генератор со своим начальным числом.
SCENE_RANDOM_SEED = RANDOM_SEED + 1
PLACEMENT_ATTEMPTS = 200     # сколько случайных мест пробовать для одного объекта

# Камни: для физики каждый камень — сфера; её нижняя часть скрыта под песком.
ROCK_COUNT_DEFAULT = 10
ROCK_COUNT_RANGE = (0, 15)
ROCK_RADIUS_RANGE = (0.7, 1.6)
ROCK_CENTER_HEIGHT = 0.3     # центр сферы на 0.3 радиуса выше дна: камень высотой 1.3 радиуса
ROCK_GAP = 0.5               # минимальный просвет между камнями
ROCK_WALL_MARGIN = 1.2       # просвет до стекла: рыба должна проплывать между камнем и стеклом
FISH_ROCK_PADDING = 0.4      # минимальный зазор между центром рыбы и поверхностью камня
ROCK_ROUGHNESS = 0.07        # амплитуда неровностей формы камня (доля радиуса)
ROCK_COLORS = [
    (0.45, 0.43, 0.40),  # серый
    (0.52, 0.47, 0.40),  # серо-коричневый
    (0.38, 0.38, 0.40),  # тёмно-серый
]

# Водоросли: цепочка сегментов, каждый поворачивается относительно предыдущего.
SEAWEED_COUNT_DEFAULT = 20
SEAWEED_COUNT_RANGE = (0, 30)
SEAWEED_SEGMENTS_RANGE = (8, 12)
SEAWEED_HEIGHT_RANGE = (3.0, 7.0)
SEAWEED_BASE_WIDTH = 0.35
SEAWEED_TIP_WIDTH = 0.08
SEAWEED_WALL_MARGIN = 3.2      # при силе 2 верхушка отклоняется до ~3.1: не должна пройти сквозь стекло
SEAWEED_SPACING = 0.6          # минимальное расстояние между основаниями водорослей
SEAWEED_SEGMENT_ANGLE = 0.08   # амплитуда поворота одного сегмента при силе 1, радианы
SEAWEED_SWAY_FREQUENCY = 1.2   # угловая частота колебаний ω, рад/с
SEAWEED_WAVE_LAG = 0.45        # сдвиг фазы между соседними сегментами: волна бежит вверх
SWAY_STRENGTH_DEFAULT = 1.0
SWAY_STRENGTH_RANGE = (0.0, 2.0)
SEAWEED_COLORS = [
    (0.20, 0.55, 0.25),
    (0.25, 0.65, 0.30),
    (0.35, 0.60, 0.20),
]

# Пузырьки: поднимаются от дна к поверхности, у поверхности рождаются заново на дне.
BUBBLE_COUNT_DEFAULT = 200
BUBBLE_COUNT_RANGE = (0, 400)
BUBBLE_RADIUS_RANGE = (0.05, 0.13)
BUBBLE_SPEED_RANGE = (1.0, 2.2)  # единиц в секунду
BUBBLE_WOBBLE = 0.08             # амплитуда покачивания из стороны в сторону
BUBBLE_WOBBLE_FREQUENCY = 3.0    # рад/с
BUBBLE_COLOR = (0.85, 0.95, 1.00)
BUBBLE_ALPHA = 0.35

# --- Режимы движения ---
# Обход препятствий: рыба смотрит вперёд по курсу и заранее отворачивает от камня.
AVOID_LOOKAHEAD = 3.0   # на сколько вперёд рыба «видит» камни
AVOID_CLEARANCE = 0.5   # дополнительный запас к радиусу камня при обходе
AVOID_FORCE = 15.0      # сила поворота, когда камень вплотную

# Корм движется по фигуре Лиссажу: по каждой оси — своя синусоида.
FOOD_CENTER = (0.0, 7.0, 0.0)
FOOD_AMPLITUDE = (8.0, 2.0, 4.0)    # размах движения по X, Y, Z
FOOD_FREQUENCY = (0.25, 0.37, 0.5)  # угловые частоты по X, Y, Z, рад/с
FOOD_FLAKES = 10                    # корм — облачко хлопьев вокруг центра
FOOD_CLUSTER_RADIUS = 0.6
FOOD_EAT_RADIUS = 0.5               # рыба съедает хлопье, если её центр ближе этого расстояния
FOOD_RESPAWN_DELAY = 1.5            # через сколько секунд после съедания появляется новая порция
FOOD_JUMP_RANGE = (10.0, 30.0)      # на сколько секунд «вперёд по траектории» переносится новая порция
FOOD_FLAKE_RADIUS = 0.08
FOOD_SPIN = 1.5                     # скорость вращения облачка, рад/с
FOOD_COLOR = (0.80, 0.45, 0.20)

# --- Интерфейс ---
FONT_SIZE = 17.0
WALL_ALPHA_MIN = 0.0
WALL_ALPHA_MAX = 0.6


@dataclass
class ViewSettings:
    """Параметры отображения, которые пользователь меняет в панели управления."""

    wall_alpha: float = 0.15  # непрозрачность стёкол: 0 — невидимы, 1 — непрозрачны
    show_edges: bool = True
    vsync: bool = True        # вертикальная синхронизация

    def set_wall_alpha(self, value):
        """Записывает непрозрачность, ограничивая её допустимым диапазоном."""
        self.wall_alpha = max(WALL_ALPHA_MIN, min(WALL_ALPHA_MAX, float(value)))


@dataclass
class SimulationSettings:
    """Управление симуляцией из панели.

    Режимы движения — это дополнительные силы поверх модели Boids, которые
    включаются независимо и поэтому сочетаются:
        оба выключены      — свободное движение;
        avoid_rocks        — обход препятствий;
        food_enabled       — сбор стаи у движущегося корма.
    """

    paused: bool = False
    avoid_rocks: bool = False
    food_enabled: bool = False

    def mode_name(self):
        if self.food_enabled and self.avoid_rocks:
            return "сбор у корма с обходом камней"
        if self.food_enabled:
            return "сбор у корма"
        if self.avoid_rocks:
            return "обход препятствий"
        return "свободное движение"
