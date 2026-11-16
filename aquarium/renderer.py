"""Отрисовка сцены: шейдеры, буферы вершин и порядок проходов."""

from array import array
from pathlib import Path

import moderngl

from aquarium import config, geometry
from aquarium.mathutils import normalize, to_opengl

SHADER_DIR = Path(__file__).parent / "shaders"

# Дно опущено на 0.02 ниже нижних рёбер. Если дно и рёбра лежат в одной плоскости,
# их глубины совпадают, тест глубины проходит то одно, то другое, и рёбра мерцают
# (это явление называют z-fighting).
FLOOR_OFFSET = 0.02

# Данные одной рыбы в буфере экземпляров: положение (3), скорость (3), цвет (3).
FLOATS_PER_FISH = 9


def load_program(ctx, vertex_name, fragment_name):
    """Компилирует шейдерную программу из файлов <vertex_name>.vert и <fragment_name>.frag."""
    vertex_source = (SHADER_DIR / f"{vertex_name}.vert").read_text(encoding="utf-8")
    fragment_source = (SHADER_DIR / f"{fragment_name}.frag").read_text(encoding="utf-8")
    return ctx.program(vertex_shader=vertex_source, fragment_shader=fragment_source)


class Mesh:
    """Геометрия в видеопамяти.

    VBO (vertex buffer object) — массив вершин в памяти видеокарты.
    VAO (vertex array object)  — описание этого массива: какие числа вершины
                                 относятся к какому входу (in) вершинного шейдера.
    """

    def __init__(self, ctx, program, vertices, layout, attributes, mode):
        self.program = program
        self.mode = mode  # moderngl.TRIANGLES или moderngl.LINES
        # array("f", ...) упаковывает числа Python в 4-байтовые float, как ожидает видеокарта.
        self.vbo = ctx.buffer(array("f", vertices).tobytes())
        # layout "3f 3f" — у вершины 3 числа позиции и 3 числа нормали.
        self.vao = ctx.vertex_array(program, [(self.vbo, layout, *attributes)])

    def render(self):
        self.vao.render(self.mode)

    def release(self):
        self.vao.release()
        self.vbo.release()


class InstancedMesh:
    """Одна модель, нарисованная много раз за один вызов отрисовки (инстансинг).

    Буфер модели хранит вершины одной рыбы. Буфер экземпляров хранит данные
    каждой рыбы. Суффикс "/i" в формате означает: брать новое значение
    не для каждой вершины, а для каждого экземпляра. Видеокарта рисует модель
    count раз, и в каждом повторе шейдер получает данные очередной рыбы.

    Без инстансинга понадобилось бы 300 вызовов отрисовки на 300 рыб,
    а каждый вызов из Python заметно дороже, чем расчёт на видеокарте.
    """

    def __init__(self, ctx, program, vertices, instance_attributes, max_instances):
        self.program = program
        self.vbo = ctx.buffer(array("f", vertices).tobytes())
        # Буфер экземпляров выделяется сразу под максимальное число рыб (4 байта на число).
        self.instances = ctx.buffer(reserve=max_instances * FLOATS_PER_FISH * 4)
        self.vao = ctx.vertex_array(program, [
            (self.vbo, "3f 3f", "in_position", "in_normal"),
            (self.instances, "3f 3f 3f/i", *instance_attributes),
        ])
        self.count = 0

    def update(self, instance_data, count):
        """Записывает в видеопамять данные экземпляров для текущего кадра."""
        self.instances.write(array("f", instance_data).tobytes())
        self.count = count

    def render(self):
        if self.count > 0:
            self.vao.render(moderngl.TRIANGLES, instances=self.count)

    def release(self):
        self.vao.release()
        self.instances.release()
        self.vbo.release()


class SceneRenderer:
    """Рисует кадр в фиксированном порядке.

    1. Непрозрачные объекты с записью глубины: дно и рыбы (позже — камни, водоросли).
    2. Дальние стенки: полупрозрачные, без записи глубины.
    3. (позже) Прозрачные объекты внутри аквариума — пузырьки.
    4. Ближние стенки.
    5. Рёбра аквариума.

    Полупрозрачная поверхность смешивается с тем, что уже нарисовано за ней,
    поэтому она рисуется после непрозрачных объектов и от дальних к ближним.
    """

    def __init__(self, ctx):
        self.ctx = ctx
        self.lit = load_program(ctx, "lit", "lit")
        self.unlit = load_program(ctx, "unlit", "unlit")
        # Рыбы используют свой вершинный шейдер и общий с дном фрагментный.
        self.fish_program = load_program(ctx, "fish", "lit")

        low, high = config.AQUARIUM_MIN, config.AQUARIUM_MAX
        floor_low = (low[0], low[1] - FLOOR_OFFSET, low[2])
        lit_layout = ("3f 3f", ("in_position", "in_normal"))
        self.floor = Mesh(ctx, self.lit, geometry.floor(floor_low, high), *lit_layout, moderngl.TRIANGLES)
        self.walls = Mesh(ctx, self.lit, geometry.box_walls(low, high), *lit_layout, moderngl.TRIANGLES)
        self.edges = Mesh(ctx, self.unlit, geometry.box_edges(low, high), "3f", ("in_position",), moderngl.LINES)
        self.fish = InstancedMesh(
            ctx, self.fish_program, geometry.fish(config.FISH_LENGTH),
            ("in_fish_position", "in_fish_velocity", "in_fish_color"),
            max_instances=config.FISH_COUNT_MAX,
        )

        self.light_direction = normalize(config.LIGHT_DIRECTION)

    def render(self, camera, width, height, settings, flock, time):
        if width == 0 or height == 0:
            return  # окно свёрнуто: рисовать некуда

        ctx = self.ctx
        ctx.viewport = (0, 0, width, height)
        ctx.clear(*config.BACKGROUND_COLOR, 1.0)  # очищает буфер цвета и буфер глубины

        # Матрицы вида и проекции одинаковы для всех объектов кадра.
        view = to_opengl(camera.view_matrix())
        projection = to_opengl(camera.projection_matrix(width / height))
        for program in (self.lit, self.unlit, self.fish_program):
            program["u_view"].value = view
            program["u_projection"].value = projection
        for program in (self.lit, self.fish_program):
            program["u_light_direction"].value = self.light_direction

        # Проход 1: непрозрачные дно и рыбы. Каждый проход явно включает нужные
        # режимы, потому что ImGui в конце прошлого кадра мог их изменить.
        ctx.enable_only(moderngl.DEPTH_TEST)
        self._draw(self.floor, config.SAND_COLOR, 1.0)
        self._draw_fish(flock, time)

        # Проходы 2–4: стёкла. Смешивание: цвет = α·новый + (1 − α)·уже_нарисованный.
        ctx.enable_only(moderngl.DEPTH_TEST | moderngl.BLEND | moderngl.CULL_FACE)
        ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        # Стёкла проверяют глубину, но не записывают её: иначе ближнее стекло
        # закрыло бы всё, что за ним будет нарисовано позже.
        ctx.fbo.depth_mask = False
        # Нормали стенок смотрят наружу, поэтому дальние стенки повёрнуты к камере
        # обратной стороной. Отсекаем лицевые — остаются дальние; затем наоборот.
        ctx.cull_face = "front"
        self._draw(self.walls, config.GLASS_COLOR, settings.wall_alpha)
        ctx.cull_face = "back"
        self._draw(self.walls, config.GLASS_COLOR, settings.wall_alpha)
        # Запись глубины обязательно включается обратно: очистка буфера глубины
        # в начале следующего кадра тоже подчиняется этой маске.
        ctx.fbo.depth_mask = True

        # Проход 5: рёбра.
        ctx.enable_only(moderngl.DEPTH_TEST)
        if settings.show_edges:
            self._draw(self.edges, config.EDGE_COLOR, 1.0)

    def _draw_fish(self, flock, time):
        # Данные всех рыб одним списком: x y z, vx vy vz, r g b для каждой.
        data = []
        for i, fish in enumerate(flock.fish):
            data.extend(fish.position)
            data.extend(fish.velocity)
            data.extend(config.FISH_COLORS[i % len(config.FISH_COLORS)])
        self.fish.update(data, len(flock.fish))

        program = self.fish_program
        program["u_time"].value = time
        program["u_fish_length"].value = config.FISH_LENGTH
        program["u_alpha"].value = 1.0
        self.fish.render()

    @staticmethod
    def _draw(mesh, color, alpha):
        mesh.program["u_color"].value = color
        mesh.program["u_alpha"].value = alpha
        mesh.render()

    def release(self):
        """Освобождает видеопамять. Вызывается до уничтожения контекста OpenGL."""
        for mesh in (self.floor, self.walls, self.edges, self.fish):
            mesh.release()
        for program in (self.lit, self.unlit, self.fish_program):
            program.release()
