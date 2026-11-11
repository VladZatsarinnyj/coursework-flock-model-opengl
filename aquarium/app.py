"""Приложение: окно, контекст OpenGL, интерфейс и главный цикл."""

import ctypes
import time

# imgui_bundle импортируется раньше glfw. В imgui_bundle есть своя копия библиотеки
# GLFW, с которой работает интерфейс, и при импорте он указывает пакету glfw на неё.
# Если импортировать glfw первым, в программе окажутся две разные копии GLFW.
from imgui_bundle import imgui
import glfw
import moderngl

from aquarium import config
from aquarium.camera import OrbitCamera
from aquarium.flock import Flock, FlockParams
from aquarium.renderer import SceneRenderer
from aquarium.ui import ControlPanel, load_cyrillic_font


class FpsCounter:
    """Раз в полсекунды обновляет FPS, среднее время кадра и среднее время шага симуляции."""

    UPDATE_INTERVAL = 0.5  # секунды

    def __init__(self):
        self.fps = 0.0
        self.frame_time_ms = 0.0
        self.step_time_ms = 0.0
        self._frames = 0
        self._elapsed = 0.0
        self._steps = 0
        self._steps_duration = 0.0

    def add_simulation_step(self, duration):
        self._steps += 1
        self._steps_duration += duration

    def add_frame(self, frame_time):
        self._frames += 1
        self._elapsed += frame_time
        if self._elapsed >= self.UPDATE_INTERVAL:
            # FPS = число кадров / затраченное время. Это то же, что 1 / среднее время кадра.
            self.fps = self._frames / self._elapsed
            self.frame_time_ms = 1000.0 * self._elapsed / self._frames
            if self._steps > 0:
                self.step_time_ms = 1000.0 * self._steps_duration / self._steps
            self._frames = 0
            self._elapsed = 0.0
            self._steps = 0
            self._steps_duration = 0.0


class App:
    def __init__(self):
        # Пока ничего не создано. close() освобождает только то, что успели создать,
        # поэтому её можно вызвать даже при ошибке на середине запуска.
        self.window = None
        self.ctx = None
        self.imgui_ready = False
        self.renderer = None
        try:
            self._create_window()
            self._init_imgui()
            self.renderer = SceneRenderer(self.ctx)
        except Exception:
            self.close()
            raise

        self.settings = config.ViewSettings()
        self.simulation = config.SimulationSettings()
        self.flock = Flock(FlockParams())
        self.camera = OrbitCamera()
        self.panel = ControlPanel(gpu_name=self.ctx.info["GL_RENDERER"])
        self.fps_counter = FpsCounter()
        self.time_accumulator = 0.0  # время, ещё не «прожитое» симуляцией

    def _create_window(self):
        if not glfw.init():
            raise RuntimeError("Не удалось инициализировать GLFW")

        # Запрашиваем контекст OpenGL 3.3 Core Profile — без устаревших функций.
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, glfw.TRUE)  # требуется на macOS
        glfw.window_hint(glfw.SAMPLES, config.MSAA_SAMPLES)

        self.window = glfw.create_window(config.WINDOW_WIDTH, config.WINDOW_HEIGHT,
                                         config.WINDOW_TITLE, None, None)
        if not self.window:
            raise RuntimeError("Не удалось создать окно с OpenGL 3.3. Обновите драйвер видеокарты.")

        # Контекст OpenGL — состояние, которому принадлежат все буферы и шейдеры.
        # Он становится текущим, и moderngl подключается к нему.
        glfw.make_context_current(self.window)
        glfw.swap_interval(1)  # вертикальная синхронизация включена
        self.ctx = moderngl.create_context(require=330)

    def _init_imgui(self):
        imgui.create_context()
        imgui.style_colors_dark()
        # Бэкенд GLFW написан на C++ и принимает адрес окна в памяти.
        # True — бэкенд сам подписывается на события мыши и клавиатуры.
        window_address = ctypes.cast(self.window, ctypes.c_void_p).value
        imgui.backends.glfw_init_for_opengl(window_address, True)
        imgui.backends.opengl3_init("#version 330")
        self.imgui_ready = True
        load_cyrillic_font()

    def run(self):
        applied_vsync = self.settings.vsync
        previous_time = glfw.get_time()

        while not glfw.window_should_close(self.window):
            # 1. События ОС: мышь, клавиатура, изменение размера, закрытие окна.
            glfw.poll_events()

            now = glfw.get_time()
            frame_time = now - previous_time
            previous_time = now
            self.fps_counter.add_frame(frame_time)

            # 2. Новый кадр интерфейса, ввод, панель управления.
            imgui.backends.opengl3_new_frame()
            imgui.backends.glfw_new_frame()
            imgui.new_frame()
            self._handle_mouse()
            self.panel.draw(self.settings, self.simulation, self.flock, self.camera, self.fps_counter)

            if self.settings.vsync != applied_vsync:
                glfw.swap_interval(1 if self.settings.vsync else 0)
                applied_vsync = self.settings.vsync

            # 3. Симуляция стаи.
            self._update_simulation(frame_time)

            # 4. Сцена, затем интерфейс поверх неё.
            width, height = glfw.get_framebuffer_size(self.window)
            self.renderer.render(self.camera, width, height, self.settings, self.flock, now)
            imgui.render()
            imgui.backends.opengl3_render_draw_data(imgui.get_draw_data())

            # 5. Показ кадра. Рисование шло в невидимый задний буфер,
            #    теперь буферы меняются местами (двойная буферизация).
            glfw.swap_buffers(self.window)

    def _update_simulation(self, frame_time):
        """Продвигает стаю с постоянным шагом SIM_DT.

        Время кадров накапливается, и симуляция делает столько шагов ровно по SIM_DT,
        сколько уместилось. Поэтому поведение стаи не зависит от FPS: при 30 и при
        144 кадрах в секунду рыбы проплывают одинаковый путь по одинаковым правилам.

        Если компьютер не успевает, число шагов за кадр ограничено, а лишнее
        накопленное время отбрасывается. Иначе каждый кадр требовал бы всё больше
        шагов и программа «застыла» бы.
        """
        if self.simulation.paused:
            self.time_accumulator = 0.0
            return

        self.time_accumulator += min(frame_time, config.MAX_FRAME_TIME)
        steps = 0
        while self.time_accumulator >= config.SIM_DT and steps < config.MAX_SIM_STEPS_PER_FRAME:
            started = time.perf_counter()
            self.flock.step(config.SIM_DT)
            self.fps_counter.add_simulation_step(time.perf_counter() - started)
            self.time_accumulator -= config.SIM_DT
            steps += 1
        if self.time_accumulator >= config.SIM_DT:
            self.time_accumulator = 0.0

    def _handle_mouse(self):
        """Вращение и приближение камеры мышью.

        Состояние мыши берётся из ImGui: он уже получает события GLFW и знает,
        находится ли курсор над его окном (want_capture_mouse). Тогда движение
        ползунка в панели не вращает камеру.
        """
        io = imgui.get_io()
        if io.want_capture_mouse:
            return
        if imgui.is_mouse_down(0):  # 0 — левая кнопка
            self.camera.rotate(-io.mouse_delta.x * config.MOUSE_ROTATION_SPEED,
                               io.mouse_delta.y * config.MOUSE_ROTATION_SPEED)
        if io.mouse_wheel != 0:
            self.camera.zoom(config.MOUSE_ZOOM_STEP ** io.mouse_wheel)

    def close(self):
        """Освобождает ресурсы в порядке, обратном созданию. Повторный вызов безопасен."""
        if self.renderer is not None:
            self.renderer.release()
            self.renderer = None
        if self.imgui_ready:
            imgui.backends.opengl3_shutdown()
            imgui.backends.glfw_shutdown()
            imgui.destroy_context()
            self.imgui_ready = False
        if self.ctx is not None:
            self.ctx.release()
            self.ctx = None
        if self.window is not None:
            glfw.destroy_window(self.window)
            self.window = None
        glfw.terminate()
