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


class ControlPanel:
    """Окно «Управление».

    Dear ImGui работает в «немедленном режиме»: окно описывается заново в каждом
    кадре, а каждый виджет сразу возвращает новое значение параметра.
    """

    def __init__(self, gpu_name):
        self.gpu_name = gpu_name

    def draw(self, settings, camera, fps_counter):
        imgui.set_next_window_pos(imgui.ImVec2(12, 12), imgui.Cond_.first_use_ever.value)
        # always_auto_resize: размер окна подстраивается под содержимое.
        imgui.begin("Управление", None, imgui.WindowFlags_.always_auto_resize.value)

        imgui.separator_text("Производительность")
        imgui.text(f"FPS: {fps_counter.fps:.1f}")
        imgui.text(f"Время кадра: {fps_counter.frame_time_ms:.2f} мс")
        imgui.text(f"Видеокарта: {self.gpu_name}")

        imgui.separator_text("Отображение")
        # Ползунок возвращает пару: (изменилось ли значение, новое значение).
        changed, value = imgui.slider_float("Непрозрачность стёкол", settings.wall_alpha,
                                            config.WALL_ALPHA_MIN, config.WALL_ALPHA_MAX, "%.2f")
        if changed:
            settings.set_wall_alpha(value)
        _, settings.show_edges = imgui.checkbox("Рёбра аквариума", settings.show_edges)
        _, settings.vsync = imgui.checkbox("Вертикальная синхронизация", settings.vsync)

        imgui.separator_text("Камера")
        imgui.text(f"Азимут: {camera.yaw_deg:.0f}°, возвышение: {camera.pitch_deg:.0f}°")
        imgui.text(f"Расстояние: {camera.distance:.1f}")
        if imgui.button("Сбросить камеру"):
            camera.reset()
        imgui.text_disabled("ЛКМ + движение — вращение, колесо — приближение")

        imgui.end()
