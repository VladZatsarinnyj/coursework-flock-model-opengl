"""Интерфейс: шрифт с кириллицей и панель «Управление»."""

from pathlib import Path

import imgui_bundle
from imgui_bundle import imgui

from aquarium import config

# Встроенный шрифт ImGui содержит только латиницу, поэтому загружается
# первый найденный шрифт с кириллицей.
FONT_CANDIDATES = [
    Path(imgui_bundle.__file__).parent / "assets" / "fonts" / "Roboto" / "Roboto-Regular.ttf",
    Path("C:/Windows/Fonts/segoeui.ttf"),
    Path("C:/Windows/Fonts/arial.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
]


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


class ControlPanel:
    """Окно «Управление».

    Dear ImGui работает в «немедленном режиме»: окно описывается заново в каждом
    кадре, а каждый виджет сразу возвращает новое значение параметра.
    """

    def __init__(self, gpu_name):
        self.gpu_name = gpu_name

    def draw(self, view, simulation, flock, camera, fps_counter):
        imgui.set_next_window_pos(imgui.ImVec2(12, 12), imgui.Cond_.first_use_ever.value)
        # always_auto_resize: размер окна подстраивается под содержимое.
        imgui.begin("Управление", None, imgui.WindowFlags_.always_auto_resize.value)
        self._draw_performance(fps_counter)
        self._draw_flock(simulation, flock)
        self._draw_view(view)
        self._draw_camera(camera)
        imgui.end()

    def _draw_performance(self, fps_counter):
        imgui.separator_text("Производительность")
        imgui.text(f"FPS: {fps_counter.fps:.1f}")
        imgui.text(f"Время кадра: {fps_counter.frame_time_ms:.2f} мс")
        imgui.text(f"Шаг симуляции: {fps_counter.step_time_ms:.2f} мс")
        imgui.text(f"Видеокарта: {self.gpu_name}")

    @staticmethod
    def _draw_flock(simulation, flock):
        imgui.separator_text("Стая")
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
    def _draw_view(view):
        imgui.separator_text("Отображение")
        view.set_wall_alpha(_slider("Непрозрачность стёкол", view.wall_alpha,
                                    (config.WALL_ALPHA_MIN, config.WALL_ALPHA_MAX)))
        _, view.show_edges = imgui.checkbox("Рёбра аквариума", view.show_edges)
        _, view.vsync = imgui.checkbox("Вертикальная синхронизация", view.vsync)

    @staticmethod
    def _draw_camera(camera):
        imgui.separator_text("Камера")
        imgui.text(f"Азимут: {camera.yaw_deg:.0f}°, возвышение: {camera.pitch_deg:.0f}°")
        imgui.text(f"Расстояние: {camera.distance:.1f}")
        if imgui.button("Сбросить камеру"):
            camera.reset()
        imgui.text_disabled("ЛКМ + движение — вращение, колесо — приближение")
