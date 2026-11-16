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


def load_program(ctx, name):
    """Компилирует шейдерную программу из файлов <name>.vert и <name>.frag."""
    vertex_source = (SHADER_DIR / f"{name}.vert").read_text(encoding="utf-8")
    fragment_source = (SHADER_DIR / f"{name}.frag").read_text(encoding="utf-8")
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


class SceneRenderer:
    """Рисует кадр в фиксированном порядке.

    1. Непрозрачные объекты с записью глубины: дно (позже — рыбы, камни, водоросли).
    2. Дальние стенки: полупрозрачные, без записи глубины.
    3. (позже) Прозрачные объекты внутри аквариума — пузырьки.
    4. Ближние стенки.
    5. Рёбра аквариума.

    Полупрозрачная поверхность смешивается с тем, что уже нарисовано за ней,
    поэтому она рисуется после непрозрачных объектов и от дальних к ближним.
    """

    def __init__(self, ctx):
        self.ctx = ctx
        self.lit = load_program(ctx, "lit")
        self.unlit = load_program(ctx, "unlit")

        low, high = config.AQUARIUM_MIN, config.AQUARIUM_MAX
        floor_low = (low[0], low[1] - FLOOR_OFFSET, low[2])
        lit_layout = ("3f 3f", ("in_position", "in_normal"))
        self.floor = Mesh(ctx, self.lit, geometry.floor(floor_low, high), *lit_layout, moderngl.TRIANGLES)
        self.walls = Mesh(ctx, self.lit, geometry.box_walls(low, high), *lit_layout, moderngl.TRIANGLES)
        self.edges = Mesh(ctx, self.unlit, geometry.box_edges(low, high), "3f", ("in_position",), moderngl.LINES)

        self.light_direction = normalize(config.LIGHT_DIRECTION)

    def render(self, camera, width, height, settings):
        if width == 0 or height == 0:
            return  # окно свёрнуто: рисовать некуда

        ctx = self.ctx
        ctx.viewport = (0, 0, width, height)
        ctx.clear(*config.BACKGROUND_COLOR, 1.0)  # очищает буфер цвета и буфер глубины

        # Матрицы вида и проекции одинаковы для всех объектов кадра.
        view = to_opengl(camera.view_matrix())
        projection = to_opengl(camera.projection_matrix(width / height))
        for program in (self.lit, self.unlit):
            program["u_view"].value = view
            program["u_projection"].value = projection
        self.lit["u_light_direction"].value = self.light_direction

        # Проход 1: непрозрачное дно. Каждый проход явно включает нужные режимы,
        # потому что ImGui в конце прошлого кадра мог их изменить.
        ctx.enable_only(moderngl.DEPTH_TEST)
        self._draw(self.floor, config.SAND_COLOR, 1.0)

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

    @staticmethod
    def _draw(mesh, color, alpha):
        mesh.program["u_color"].value = color
        mesh.program["u_alpha"].value = alpha
        mesh.render()

    def release(self):
        """Освобождает видеопамять. Вызывается до уничтожения контекста OpenGL."""
        for mesh in (self.floor, self.walls, self.edges):
            mesh.release()
        self.lit.release()
        self.unlit.release()
