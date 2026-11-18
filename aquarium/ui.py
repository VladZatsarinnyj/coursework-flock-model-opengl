"""Интерфейс: шрифт с кириллицей и панель «Управление»."""

from pathlib import Path

import imgui_bundle
from imgui_bundle import imgui

from aquarium import config
from aquarium.mathutils import length

# Встроенный шрифт ImGui содержит только латиницу, поэтому загружается
# первый найденный шрифт с кириллицей.
FONT_CANDIDATES = [
    Path(imgui_bundle.__file__).parent / "assets" / "fonts" / "Roboto" / "Roboto-Regular.ttf",
    Path("C:/Windows/Fonts/segoeui.ttf"),
    Path("C:/Windows/Fonts/arial.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
]

PANEL_WIDTH = 480


def load_cyrillic_font():
    for path in FONT_CANDIDATES:
        if path.is_file():
            imgui.get_io().fonts.add_font_from_file_ttf(str(path), config.FONT_SIZE)
            return
    print("Шрифт с кириллицей не найден: русские подписи будут отображаться знаками «?»")


def _slider(label, value, value_range, value_format="%.2f"):
    """Ползунок для дробного параметра; возвращает текущее значение.

    imgui.slider_float возвращает пару (изменилось ли значение, новое значение).
    Через Ctrl + щелчок можно ввести число вне диапазона, поэтому после ползунков
    вызывается проверка в модели (FlockParams.clamp, ViewSettings.set_wall_alpha).
    """
    _, value = imgui.slider_float(label, value, value_range[0], value_range[1], value_format)
    return value


def _section(title, default_open):
    """Сворачиваемый раздел панели; возвращает True, если раздел развёрнут."""
    flags = imgui.TreeNodeFlags_.default_open.value if default_open else 0
    return imgui.collapsing_header(title, flags)


def _color_label(color, text):
    imgui.text_colored(imgui.ImVec4(color[0], color[1], color[2], 1.0), text)


class ControlPanel:
    """Окно «Управление».

    Dear ImGui работает в «немедленном режиме»: окно описывается заново в каждом
    кадре, а каждый виджет сразу возвращает новое значение параметра.
    Разделы сворачиваются, а если всё не помещается по высоте, появляется прокрутка.
    """

    def __init__(self, gpu_name):
        self.gpu_name = gpu_name

    def draw(self, view, simulation, flock, scene, camera, fps_counter):
        io = imgui.get_io()
        first_use = imgui.Cond_.first_use_ever.value
        imgui.set_next_window_pos(imgui.ImVec2(12, 12), first_use)
        imgui.set_next_window_size(imgui.ImVec2(PANEL_WIDTH, max(300.0, io.display_size.y - 24)), first_use)
        # Текст после ### не показывается, а служит постоянным именем окна: заголовок
        # с FPS меняется каждый кадр, а положение и размер окна при этом сохраняются.
        imgui.begin(f"Управление — {fps_counter.fps:.0f} FPS###control_panel", None, 0)
        if _section("Производительность", False):
            self._draw_performance(fps_counter)
        if _section("Стая", True):
            self._draw_flock(simulation, flock)
        if _section("Режимы движения", True):
            self._draw_modes(simulation, flock, scene)
        if _section("Выбранная рыба", True):
            self._draw_selection(view, flock)
        if _section("Сцена", False):
            self._draw_scene(scene)
        if _section("Отображение", False):
            self._draw_view(view)
        if _section("Внешняя камера", False):
            self._draw_camera(camera)
        imgui.end()

    def _draw_performance(self, fps_counter):
        imgui.text(f"FPS: {fps_counter.fps:.1f}")
        imgui.text(f"Время кадра: {fps_counter.frame_time_ms:.2f} мс")
        imgui.text(f"Шаг симуляции: {fps_counter.step_time_ms:.2f} мс")
        imgui.text(f"Скорость симуляции: {100 * fps_counter.simulation_speed:.0f} %")
        imgui.text(f"Видеокарта: {self.gpu_name}")

    @staticmethod
    def _draw_flock(simulation, flock):
        changed, count = imgui.slider_int("Число рыб", len(flock.fish),
                                          config.FISH_COUNT_MIN, config.FISH_COUNT_MAX)
        if changed:
            flock.set_count(count)

        params = flock.params
        params.separation_weight = _slider("Разделение", params.separation_weight,
                                           config.SEPARATION_WEIGHT_RANGE)
        params.alignment_weight = _slider("Выравнивание", params.alignment_weight,
                                          config.ALIGNMENT_WEIGHT_RANGE)
        params.cohesion_weight = _slider("Сплочённость", params.cohesion_weight,
                                         config.COHESION_WEIGHT_RANGE)
        params.neighbor_radius = _slider("Радиус соседства", params.neighbor_radius,
                                         config.NEIGHBOR_RADIUS_RANGE, "%.1f")
        params.max_speed = _slider("Макс. скорость", params.max_speed,
                                   config.MAX_SPEED_RANGE, "%.1f")
        params.clamp()

        _, simulation.paused = imgui.checkbox("Пауза", simulation.paused)
        imgui.same_line()
        if imgui.button("Перемешать стаю"):
            flock.respawn()

        imgui.text(f"Среднее число соседей: {flock.average_neighbor_count():.1f}")
        imgui.text(f"Согласованность движения Φ: {flock.polarization():.2f}")

    @staticmethod
    def _draw_modes(simulation, flock, scene):
        # Режимы — независимые добавки к модели Boids, поэтому это флажки, а не выбор одного из трёх.
        # При смене режима счётчики сбрасываются: каждое число должно относиться к одному режиму.
        changed_avoid, simulation.avoid_rocks = imgui.checkbox("Обход камней", simulation.avoid_rocks)
        imgui.same_line()
        changed_food, simulation.food_enabled = imgui.checkbox("Корм", simulation.food_enabled)
        params = flock.params
        params.food_weight = _slider("Притяжение к корму", params.food_weight, config.FOOD_WEIGHT_RANGE)
        params.clamp()
        imgui.text(f"Режим: {simulation.mode_name()}")
        imgui.text(f"Касаний камней в минуту: {flock.contacts_per_minute():.1f}")
        if simulation.food_enabled:
            imgui.text(f"Съедено порций: {scene.portions_eaten()}")
            imgui.text(f"Среднее время поиска корма: {scene.average_search_time():.1f} с")
        if imgui.button("Сбросить счётчики") or changed_avoid or changed_food:
            flock.reset_contact_stats()
            scene.reset_food_stats()

    @staticmethod
    def _draw_selection(view, flock):
        count = len(flock.fish)
        current = -1 if view.selected_fish is None else view.selected_fish
        changed, index = imgui.slider_int("Номер рыбы", current, -1, count - 1)
        if changed:
            view.select_fish(index, count)  # −1 снимает выбор
        imgui.text_disabled("Щелчок по рыбе — выбрать, по пустому месту — снять выбор")

        if view.selected_fish is None:
            imgui.text("Рыба не выбрана")
        else:
            fish = flock.fish[view.selected_fish]
            neighbor_count = len(flock.neighbors[view.selected_fish])
            imgui.text(f"Соседей в радиусе {flock.params.neighbor_radius:.1f}: {neighbor_count}")
            imgui.text(f"Скорость: {length(fish.velocity):.2f}")
            _, view.show_neighbor_sphere = imgui.checkbox("Сфера соседства", view.show_neighbor_sphere)
            imgui.same_line()
            _, view.show_force_vectors = imgui.checkbox("Векторы сил", view.show_force_vectors)
            if view.show_force_vectors:
                # Легенда в две колонки: цвет стрелки — название слагаемого.
                names = list(config.FORCE_COLORS)
                for k, name in enumerate(names):
                    if k % 2 == 1:
                        imgui.same_line(PANEL_WIDTH / 2)
                    _color_label(config.FORCE_COLORS[name], f"— {name}")
                _color_label(config.VELOCITY_COLOR, "— скорость")

        # Камера за рыбой включается только при выбранной рыбе.
        if imgui.radio_button("Внешняя камера", not view.follow_camera):
            view.follow_camera = False
        imgui.same_line()
        if imgui.radio_button("Камера за рыбой", view.follow_camera):
            view.follow_camera = True
        if view.follow_camera and view.selected_fish is None:
            imgui.text_disabled("Выберите рыбу, чтобы камера встала за ней")
        _, view.show_all_velocities = imgui.checkbox("Векторы скорости всех рыб", view.show_all_velocities)

    @staticmethod
    def _draw_scene(scene):
        # Если для камня не нашлось свободного места, камней станет меньше,
        # чем выбрано, и ползунок покажет фактическое число.
        changed, count = imgui.slider_int("Камни", len(scene.rocks), *config.ROCK_COUNT_RANGE)
        if changed:
            scene.set_rock_count(count)
        changed, count = imgui.slider_int("Водоросли", len(scene.seaweed), *config.SEAWEED_COUNT_RANGE)
        if changed:
            scene.set_seaweed_count(count)
        changed, count = imgui.slider_int("Пузырьки", len(scene.bubbles), *config.BUBBLE_COUNT_RANGE)
        if changed:
            scene.set_bubble_count(count)
        scene.set_sway_strength(_slider("Колебание водорослей", scene.sway_strength,
                                        config.SWAY_STRENGTH_RANGE))
        if imgui.button("Новая расстановка"):
            scene.shuffle()

    @staticmethod
    def _draw_view(view):
        view.set_wall_alpha(_slider("Непрозрачность стёкол", view.wall_alpha,
                                    (config.WALL_ALPHA_MIN, config.WALL_ALPHA_MAX)))
        _, view.show_edges = imgui.checkbox("Рёбра аквариума", view.show_edges)
        _, view.vsync = imgui.checkbox("Вертикальная синхронизация", view.vsync)

    @staticmethod
    def _draw_camera(camera):
        imgui.text(f"Азимут: {camera.yaw_deg:.0f}°, возвышение: {camera.pitch_deg:.0f}°")
        imgui.text(f"Расстояние: {camera.distance:.1f}")
        if imgui.button("Сбросить камеру"):
            camera.reset()
        imgui.text_disabled("ЛКМ + движение — вращение, колесо — приближение")
