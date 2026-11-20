"""Приложение: окно, контекст OpenGL, интерфейс и главный цикл."""

import ctypes
import math
import time

# imgui_bundle импортируется раньше glfw. В imgui_bundle есть своя копия библиотеки
# GLFW, с которой работает интерфейс, и при импорте он указывает пакету glfw на неё.
# Если импортировать glfw первым, в программе окажутся две разные копии GLFW.
from imgui_bundle import imgui
import glfw
import moderngl

from aquarium import __version__, config
from aquarium.camera import FollowCamera, OrbitCamera
from aquarium.flock import Flock, FlockParams
from aquarium.picking import mouse_ray, pick_fish
from aquarium.renderer import SceneRenderer
from aquarium.scene import Scene
from aquarium.ui import ControlPanel, load_cyrillic_font


class FpsCounter:
    """Раз в полсекунды обновляет FPS, среднее время кадра, среднее время шага симуляции
    и скорость симуляции."""

    UPDATE_INTERVAL = 0.5  # секунды

    def __init__(self):
        self.fps = 0.0
        self.frame_time_ms = 0.0
        self.step_time_ms = 0.0
        self.simulation_speed = 1.0  # доля реального времени: 1.0 — стая успевает, 0.5 — вдвое медленнее
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
            # Сколько модельного времени прожито за прошедшее реальное время.
            # Чуть больше 1 бывает только из-за границы окна усреднения, поэтому
            # значение ограничено единицей. На паузе скорость равна 0.
            self.simulation_speed = min(1.0, self._steps * config.SIM_DT / self._elapsed)
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
        self.scene = Scene()
        self.camera = OrbitCamera()            # внешняя камера
        self.follow_camera = FollowCamera()    # внутренняя камера — за выбранной рыбой
        self.active_camera = self.camera       # через какую камеру рисуется кадр
        self.press_position = None             # где была нажата левая кнопка мыши
        self.keys_down = set()                 # какие горячие клавиши были нажаты в прошлом кадре
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

        title = f"{config.WINDOW_TITLE} — версия {__version__}"
        self.window = glfw.create_window(config.WINDOW_WIDTH, config.WINDOW_HEIGHT, title, None, None)
        if not self.window:
            raise RuntimeError("Не удалось создать окно с OpenGL 3.3. Обновите драйвер видеокарты.")

        # Контекст OpenGL — состояние, которому принадлежат все буферы и шейдеры.
        # Он становится текущим, и moderngl подключается к нему.
        glfw.make_context_current(self.window)
        glfw.swap_interval(1)  # вертикальная синхронизация включена
        self.ctx = moderngl.create_context(require=330)

    def _init_imgui(self):
        imgui.create_context()
        # Клавиатурная навигация по панели выключена: иначе панель в фокусе забирает пробел, H, R себе.
        imgui.get_io().config_flags &= ~imgui.ConfigFlags_.nav_enable_keyboard.value
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
            self._handle_keyboard()
            if self.settings.show_panel:
                self.panel.draw(self.settings, self.simulation, self.flock, self.scene, self.camera,
                                self.fps_counter)

            if self.settings.vsync != applied_vsync:
                glfw.swap_interval(1 if self.settings.vsync else 0)
                applied_vsync = self.settings.vsync

            # 3. Симуляция стаи.
            self._update_simulation(frame_time)

            # 4. Выбранная рыба и камера. Рыб могло стать меньше — тогда выбор снимается.
            self.settings.select_fish(self.settings.selected_fish, len(self.flock.fish))
            self.active_camera = self._choose_camera(min(frame_time, config.MAX_FRAME_TIME))

            # 5. Сцена, затем интерфейс поверх неё.
            width, height = glfw.get_framebuffer_size(self.window)
            self.renderer.render(self.active_camera, width, height, self.settings, self.simulation,
                                 self.flock, self.scene)
            imgui.render()
            imgui.backends.opengl3_render_draw_data(imgui.get_draw_data())

            # 6. Показ кадра. Рисование шло в невидимый задний буфер,
            #    теперь буферы меняются местами (двойная буферизация).
            glfw.swap_buffers(self.window)

    def _update_simulation(self, frame_time):
        """Продвигает стаю с постоянным шагом SIM_DT.

        Время кадров накапливается, и симуляция делает столько шагов ровно по SIM_DT,
        сколько уместилось. Поэтому поведение стаи не зависит от FPS: при 30 и при
        144 кадрах в секунду рыбы проплывают одинаковый путь по одинаковым правилам.

        Если компьютер не успевает (один шаг дольше SIM_TIME_BUDGET), остаток
        накопленного времени отбрасывается: стая движется медленнее реального
        времени, но кадры идут часто и интерфейс отвечает. Без этого каждый кадр
        требовал бы всё больше шагов, и программа «застыла» бы.
        """
        if self.simulation.paused:
            self.time_accumulator = 0.0
            return

        self.time_accumulator += min(frame_time, config.MAX_FRAME_TIME)
        frame_started = time.perf_counter()
        while self.time_accumulator >= config.SIM_DT:
            step_started = time.perf_counter()
            food_present = self.simulation.food_enabled and self.scene.food_available()
            food = self.scene.food_position() if food_present else None
            self.flock.step(config.SIM_DT, self.scene.rocks, self.simulation.avoid_rocks, food)
            if self.simulation.food_enabled:
                self.scene.update_food(config.SIM_DT, [fish.position for fish in self.flock.fish])
            self.scene.step(config.SIM_DT)
            step_finished = time.perf_counter()
            self.fps_counter.add_simulation_step(step_finished - step_started)
            self.time_accumulator -= config.SIM_DT
            if step_finished - frame_started > config.SIM_TIME_BUDGET:
                self.time_accumulator = 0.0
                break

    def _handle_mouse(self):
        """Мышь: щелчок выбирает рыбу, перетаскивание и колесо управляют внешней камерой.

        Состояние мыши берётся из ImGui: он уже получает события GLFW и знает,
        находится ли курсор над его окном (want_capture_mouse). Тогда движение
        ползунка в панели не вращает камеру.

        Щелчок и перетаскивание начинаются одинаково — с нажатия левой кнопки.
        Если между нажатием и отпусканием курсор сдвинулся не больше CLICK_MAX_DRAG
        пикселей, это щелчок, иначе — вращение камеры.
        """
        io = imgui.get_io()
        if io.want_capture_mouse:
            self.press_position = None
            return

        if imgui.is_mouse_clicked(0):  # 0 — левая кнопка
            self.press_position = (io.mouse_pos.x, io.mouse_pos.y)
        if imgui.is_mouse_released(0) and self.press_position is not None:
            moved = math.hypot(io.mouse_pos.x - self.press_position[0], io.mouse_pos.y - self.press_position[1])
            if moved <= config.CLICK_MAX_DRAG:
                self._select_fish_at(io.mouse_pos.x, io.mouse_pos.y, io.display_size.x, io.display_size.y)
            self.press_position = None

        if self.active_camera is self.camera:  # мышью управляется только внешняя камера
            if imgui.is_mouse_down(0):
                self.camera.rotate(-io.mouse_delta.x * config.MOUSE_ROTATION_SPEED,
                                   io.mouse_delta.y * config.MOUSE_ROTATION_SPEED)
            if io.mouse_wheel != 0:
                self.camera.zoom(config.MOUSE_ZOOM_STEP ** io.mouse_wheel)

    def _key_pressed(self, key):
        """True только в том кадре, когда клавишу нажали, а не всё время, пока её держат.

        GLFW сообщает лишь, нажата ли клавиша сейчас. Нажатие — это переход
        «в прошлом кадре отпущена → сейчас нажата», поэтому состояние запоминается.
        """
        down = glfw.get_key(self.window, key) == glfw.PRESS
        was_down = key in self.keys_down
        if down:
            self.keys_down.add(key)
        else:
            self.keys_down.discard(key)
        return down and not was_down

    def _handle_keyboard(self):
        """Горячие клавиши для демонстрации: пробел, Esc, H, C, R."""
        pressed = {key: self._key_pressed(key)
                   for key in (glfw.KEY_SPACE, glfw.KEY_ESCAPE, glfw.KEY_H, glfw.KEY_C, glfw.KEY_R)}
        if imgui.get_io().want_text_input:
            return  # идёт ввод числа в поле панели (Ctrl + щелчок) — клавиши для него
        if pressed[glfw.KEY_SPACE]:
            self.simulation.paused = not self.simulation.paused
        if pressed[glfw.KEY_ESCAPE]:
            self.settings.select_fish(None, len(self.flock.fish))
        if pressed[glfw.KEY_H]:
            self.settings.show_panel = not self.settings.show_panel
        if pressed[glfw.KEY_C]:
            self.settings.follow_camera = not self.settings.follow_camera
        if pressed[glfw.KEY_R]:
            self.camera.reset()

    def _select_fish_at(self, x, y, width, height):
        """Выбирает рыбу под курсором; щелчок по пустому месту снимает выбор."""
        if width <= 0 or height <= 0:
            return
        origin, direction = mouse_ray(self.active_camera, x, y, width, height)
        self.settings.select_fish(pick_fish(origin, direction, self.flock.fish), len(self.flock.fish))

    def _choose_camera(self, dt):
        """Камера за рыбой работает, только если она включена и рыба выбрана."""
        selected = self.settings.selected_fish
        if self.settings.follow_camera and selected is not None:
            self.follow_camera.update(selected, self.flock.fish[selected], dt)
            return self.follow_camera
        self.follow_camera.fish_index = None  # при следующем включении камера сразу встанет за рыбой
        return self.camera

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
