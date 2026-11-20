"""Все настройки программы в одном месте."""

from dataclasses import dataclass

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 800
WINDOW_TITLE = "Аквариум со стаей"
MSAA_SAMPLES = 4

AQUARIUM_WIDTH = 24.0
AQUARIUM_HEIGHT = 12.0
AQUARIUM_DEPTH = 14.0
AQUARIUM_MIN = (-AQUARIUM_WIDTH / 2, 0.0, -AQUARIUM_DEPTH / 2)
AQUARIUM_MAX = (AQUARIUM_WIDTH / 2, AQUARIUM_HEIGHT, AQUARIUM_DEPTH / 2)
AQUARIUM_CENTER = (0.0, AQUARIUM_HEIGHT / 2, 0.0)

BACKGROUND_COLOR = (0.02, 0.06, 0.10)
SAND_COLOR = (0.76, 0.68, 0.50)
GLASS_COLOR = (0.60, 0.85, 0.95)
EDGE_COLOR = (0.80, 0.95, 1.00)

LIGHT_DIRECTION = (0.35, 1.0, 0.25)

CAMERA_FOV_DEG = 50.0
CAMERA_NEAR = 0.1
CAMERA_FAR = 300.0
CAMERA_START_YAW_DEG = 35.0
CAMERA_START_PITCH_DEG = 25.0
CAMERA_START_DISTANCE = 38.0
CAMERA_MIN_DISTANCE = 2.0
CAMERA_MAX_DISTANCE = 150.0
MOUSE_ROTATION_SPEED = 0.3
MOUSE_ZOOM_STEP = 0.9

SIM_DT = 1.0 / 60.0
SIM_TIME_BUDGET = 0.010
MAX_FRAME_TIME = 0.25
RANDOM_SEED = 42

FISH_COUNT_DEFAULT = 80
FISH_COUNT_MIN = 10
FISH_COUNT_MAX = 300
FISH_LENGTH = 1.2
FISH_MIN_SPEED = 1.5
FISH_MAX_ACCELERATION = 8.0
FISH_PERSONAL_SPACE = 1.0
COLLISION_FORCE = 100.0
WALL_MARGIN = 2.5
FLOOR_MARGIN = 1.5
WALL_FORCE = 12.0
WALL_PADDING = 0.6

SEPARATION_WEIGHT_RANGE = (0.0, 5.0)
ALIGNMENT_WEIGHT_RANGE = (0.0, 5.0)
COHESION_WEIGHT_RANGE = (0.0, 5.0)
NEIGHBOR_RADIUS_RANGE = (1.0, 8.0)
MAX_SPEED_RANGE = (2.0, 10.0)
FOOD_WEIGHT_RANGE = (0.0, 5.0)

FISH_COLORS = [
    (1.00, 0.55, 0.15),
    (1.00, 0.75, 0.20),
    (0.95, 0.40, 0.30),
    (1.00, 0.85, 0.55),
]

SCENE_RANDOM_SEED = RANDOM_SEED + 1
PLACEMENT_ATTEMPTS = 200

ROCK_COUNT_DEFAULT = 10
ROCK_COUNT_RANGE = (0, 15)
ROCK_RADIUS_RANGE = (0.7, 1.6)
ROCK_CENTER_HEIGHT = 0.3
ROCK_GAP = 0.5
ROCK_SHRINK_STEP = 0.2
ROCK_WALL_MARGIN = 1.2
FISH_ROCK_PADDING = 0.4
ROCK_ROUGHNESS = 0.07
ROCK_COLORS = [
    (0.45, 0.43, 0.40),
    (0.52, 0.47, 0.40),
    (0.38, 0.38, 0.40),
]

SEAWEED_COUNT_DEFAULT = 20
SEAWEED_COUNT_RANGE = (0, 30)
SEAWEED_SEGMENTS_RANGE = (8, 12)
SEAWEED_HEIGHT_RANGE = (3.0, 7.0)
SEAWEED_BASE_WIDTH = 0.35
SEAWEED_TIP_WIDTH = 0.08
SEAWEED_WALL_MARGIN = 3.2
SEAWEED_SPACING = 0.6
SEAWEED_SEGMENT_ANGLE = 0.08
SEAWEED_SWAY_FREQUENCY = 1.2
SEAWEED_WAVE_LAG = 0.45
SWAY_STRENGTH_DEFAULT = 1.0
SWAY_STRENGTH_RANGE = (0.0, 2.0)
SEAWEED_COLORS = [
    (0.20, 0.55, 0.25),
    (0.25, 0.65, 0.30),
    (0.35, 0.60, 0.20),
]

BUBBLE_COUNT_DEFAULT = 200
BUBBLE_COUNT_RANGE = (0, 400)
BUBBLE_RADIUS_RANGE = (0.05, 0.13)
BUBBLE_SPEED_RANGE = (1.0, 2.2)
BUBBLE_WOBBLE = 0.08
BUBBLE_WOBBLE_FREQUENCY = 3.0
BUBBLE_COLOR = (0.85, 0.95, 1.00)
BUBBLE_ALPHA = 0.35

AVOID_LOOKAHEAD = 3.0
AVOID_CLEARANCE = 0.5
AVOID_FORCE = 15.0

FOOD_CENTER = (0.0, 7.0, 0.0)
FOOD_AMPLITUDE = (8.0, 2.0, 4.0)
FOOD_FREQUENCY = (0.25, 0.37, 0.5)
FOOD_FLAKES = 10
FOOD_CLUSTER_RADIUS = 0.6
FOOD_EAT_RADIUS = 0.5
FOOD_RESPAWN_DELAY = 1.5
FOOD_JUMP_RANGE = (10.0, 30.0)
FOOD_FLAKE_RADIUS = 0.08
FOOD_SPIN = 1.5
FOOD_COLOR = (0.80, 0.45, 0.20)

FISH_PICK_RADIUS = 0.8
CLICK_MAX_DRAG = 4.0
SELECTED_FISH_COLOR = (1.00, 1.00, 1.00)
NEIGHBOR_FISH_COLOR = (0.30, 0.85, 1.00)
NEIGHBOR_SPHERE_COLOR = (0.30, 0.85, 1.00)
NEIGHBOR_SPHERE_SEGMENTS = 64
VELOCITY_COLOR = (1.00, 1.00, 0.60)
VELOCITY_VECTOR_SCALE = 0.5
FORCE_VECTOR_SCALE = 0.3
FORCE_COLORS = {
    "разделение": (1.00, 0.35, 0.35),
    "выравнивание": (0.35, 1.00, 0.35),
    "сплочённость": (0.45, 0.60, 1.00),
    "корм": (1.00, 0.60, 0.20),
    "стенки": (0.80, 0.80, 0.80),
    "столкновения": (1.00, 0.40, 1.00),
    "обход камней": (1.00, 1.00, 0.30),
}
MAX_LINE_VERTICES = 4000

FOLLOW_DISTANCE_BEHIND = 3.0
FOLLOW_HEIGHT = 0.8
FOLLOW_LOOK_AHEAD = 4.0
FOLLOW_SMOOTHING = 3.0
FOLLOW_MAX_PITCH_DEG = 60.0

TASK_COMPOSITIONS = {
    "Минимум по заданию": {"fish": 60, "seaweed": 15, "rocks": 8, "bubbles": 100},
    "Максимум по заданию": {"fish": 120, "seaweed": 25, "rocks": 15, "bubbles": 300},
}

FONT_SIZE = 17.0
WALL_ALPHA_MIN = 0.0
WALL_ALPHA_MAX = 0.6


@dataclass
class ViewSettings:
    """Параметры отображения, которые пользователь меняет в панели управления."""

    wall_alpha: float = 0.15
    show_edges: bool = True
    vsync: bool = True
    selected_fish: int | None = None
    follow_camera: bool = False
    show_neighbor_sphere: bool = True
    show_force_vectors: bool = True
    show_all_velocities: bool = False
    show_panel: bool = True

    def set_wall_alpha(self, value):
        """Записывает непрозрачность, ограничивая её допустимым диапазоном."""
        self.wall_alpha = max(WALL_ALPHA_MIN, min(WALL_ALPHA_MAX, float(value)))

    def select_fish(self, index, fish_count):
        """Выбирает рыбу по номеру. None или номер вне [0; fish_count) снимает выбор."""
        if index is None or not 0 <= index < fish_count:
            self.selected_fish = None
        else:
            self.selected_fish = int(index)


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
