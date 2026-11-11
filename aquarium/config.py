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
MAX_SIM_STEPS_PER_FRAME = 5  # защита от лавинного отставания на медленном компьютере
MAX_FRAME_TIME = 0.25        # кадр дольше этого (например, перетаскивание окна) не догоняется
RANDOM_SEED = 42             # одинаковое начальное состояние стаи при каждом запуске

# --- Стая ---
FISH_COUNT_DEFAULT = 80
FISH_COUNT_MIN = 10
FISH_COUNT_MAX = 300
FISH_LENGTH = 1.2            # длина модели рыбы
FISH_MIN_SPEED = 1.5         # рыба не останавливается полностью
FISH_MAX_ACCELERATION = 8.0  # ограничение суммарной силы правил
WALL_MARGIN = 2.5            # с какого расстояния до стенки рыба начинает разворачиваться
WALL_FORCE = 12.0            # сила разворота у самой стенки
WALL_PADDING = 0.6           # минимальный зазор между центром рыбы и стеклом

# Допустимые значения параметров стаи: используются и ползунками, и проверкой в FlockParams.
SEPARATION_WEIGHT_RANGE = (0.0, 5.0)
ALIGNMENT_WEIGHT_RANGE = (0.0, 5.0)
COHESION_WEIGHT_RANGE = (0.0, 5.0)
NEIGHBOR_RADIUS_RANGE = (0.5, 8.0)
MAX_SPEED_RANGE = (2.0, 10.0)

# Окраска рыб: рыба с номером i получает цвет FISH_COLORS[i % len(FISH_COLORS)].
FISH_COLORS = [
    (1.00, 0.55, 0.15),  # оранжевый
    (1.00, 0.75, 0.20),  # золотистый
    (0.95, 0.40, 0.30),  # коралловый
    (1.00, 0.85, 0.55),  # светло-жёлтый
]

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
    """Управление симуляцией из панели. В КТ4 сюда добавятся режим движения и корм."""

    paused: bool = False
