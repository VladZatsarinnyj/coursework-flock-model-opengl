"""Отрисовка сцены: шейдеры, буферы вершин и порядок проходов."""

from array import array
from pathlib import Path

import moderngl

from aquarium import config, geometry
from aquarium.mathutils import add, length, normalize, scale, to_opengl

SHADER_DIR = Path(__file__).parent / "shaders"

FLOOR_OFFSET = 0.02

LIT_LAYOUT = ("3f 3f", ("in_position", "in_normal"))


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
        self.mode = mode
        self.vbo = ctx.buffer(array("f", vertices).tobytes())
        self.vao = ctx.vertex_array(program, [(self.vbo, layout, *attributes)])

    def render(self):
        self.vao.render(self.mode)

    def release(self):
        self.vao.release()
        self.vbo.release()


class InstancedMesh:
    """Одна модель, нарисованная много раз за один вызов отрисовки (инстансинг).

    Буфер модели хранит вершины одного объекта (рыбы, сегмента водоросли, пузырька).
    Буфер экземпляров хранит данные каждого объекта. Суффикс "/i" в формате означает:
    брать новое значение не для каждой вершины, а для каждого экземпляра. Видеокарта
    рисует модель count раз, и в каждом повторе шейдер получает данные очередного объекта.

    Без инстансинга понадобилось бы по вызову отрисовки на каждый объект,
    а каждый вызов из Python заметно дороже, чем расчёт на видеокарте.
    """

    def __init__(self, ctx, program, vertices, instance_layout, instance_attributes, max_instances):
        self.program = program
        self.floats_per_instance = sum(int(part[:-1]) for part in instance_layout.split())
        self.max_instances = max_instances
        self.vbo = ctx.buffer(array("f", vertices).tobytes())
        self.instances = ctx.buffer(reserve=max_instances * self.floats_per_instance * 4)
        self.vao = ctx.vertex_array(program, [
            (self.vbo, LIT_LAYOUT[0], *LIT_LAYOUT[1]),
            (self.instances, instance_layout + "/i", *instance_attributes),
        ])
        self.count = 0

    def update(self, instance_data):
        """Записывает в видеопамять данные экземпляров для текущего кадра."""
        count = len(instance_data) // self.floats_per_instance
        if count > self.max_instances:
            raise ValueError(f"Экземпляров {count}, а буфер рассчитан на {self.max_instances}")
        if count > 0:
            self.instances.write(array("f", instance_data).tobytes())
        self.count = count

    def render(self):
        if self.count > 0:
            self.vao.render(moderngl.TRIANGLES, instances=self.count)

    def release(self):
        self.vao.release()
        self.instances.release()
        self.vbo.release()


class DynamicLines:
    """Отрезки, которые меняются каждый кадр: сфера соседства, векторы скорости и сил.

    Буфер выделяется один раз под максимальное число вершин, а в каждом кадре
    в него записываются новые данные. У вершины 6 чисел: положение и цвет.
    """

    def __init__(self, ctx, program, max_vertices):
        self.max_vertices = max_vertices
        self.buffer = ctx.buffer(reserve=max_vertices * 6 * 4)
        self.vao = ctx.vertex_array(program, [(self.buffer, "3f 3f", "in_position", "in_color")])
        self.count = 0

    def update(self, segments):
        """segments — список (начало, конец, цвет)."""
        data = []
        for start, end, color in segments:
            data.extend(start)
            data.extend(color)
            data.extend(end)
            data.extend(color)
        count = len(data) // 6
        if count > self.max_vertices:
            raise ValueError(f"Вершин линий {count}, а буфер рассчитан на {self.max_vertices}")
        if count > 0:
            self.buffer.write(array("f", data).tobytes())
        self.count = count

    def render(self):
        if self.count > 0:
            self.vao.render(moderngl.LINES, vertices=self.count)

    def release(self):
        self.vao.release()
        self.buffer.release()


class SceneRenderer:
    """Рисует кадр в фиксированном порядке.

    1. Непрозрачные объекты с записью глубины: дно, камни, водоросли, рыбы, корм,
       вспомогательные линии (сфера соседства, векторы).
    2. Дальние стенки: полупрозрачные, без записи глубины.
    3. Пузырьки — полупрозрачные объекты внутри аквариума.
    4. Ближние стенки.
    5. Рёбра аквариума.

    Полупрозрачная поверхность смешивается с тем, что уже нарисовано за ней,
    поэтому она рисуется после непрозрачных объектов и от дальних к ближним.
    """

    def __init__(self, ctx):
        self.ctx = ctx
        self.lit = load_program(ctx, "lit", "lit")
        self.unlit = load_program(ctx, "unlit", "unlit")
        self.fish_program = load_program(ctx, "fish", "lit")
        self.seaweed_program = load_program(ctx, "seaweed", "lit")
        self.sphere_program = load_program(ctx, "bubble", "lit")
        self.lines_program = load_program(ctx, "lines", "lines")
        self.programs = [self.lit, self.unlit, self.fish_program, self.seaweed_program, self.sphere_program,
                         self.lines_program]
        self.lit_programs = [self.lit, self.fish_program, self.seaweed_program, self.sphere_program]

        low, high = config.AQUARIUM_MIN, config.AQUARIUM_MAX
        floor_low = (low[0], low[1] - FLOOR_OFFSET, low[2])
        self.floor = Mesh(ctx, self.lit, geometry.floor(floor_low, high), *LIT_LAYOUT, moderngl.TRIANGLES)
        self.walls = Mesh(ctx, self.lit, geometry.box_walls(low, high), *LIT_LAYOUT, moderngl.TRIANGLES)
        self.edges = Mesh(ctx, self.unlit, geometry.box_edges(low, high), "3f", ("in_position",), moderngl.LINES)

        self.fish = InstancedMesh(
            ctx, self.fish_program, geometry.fish(config.FISH_LENGTH),
            "3f 3f 3f", ("in_fish_position", "in_fish_velocity", "in_fish_color"),
            max_instances=config.FISH_COUNT_MAX,
        )
        self.seaweed = InstancedMesh(
            ctx, self.seaweed_program, geometry.seaweed_segment(),
            "3f 3f 1f 1f 3f", ("in_start", "in_end", "in_width_start", "in_width_end", "in_color"),
            max_instances=config.SEAWEED_COUNT_RANGE[1] * config.SEAWEED_SEGMENTS_RANGE[1],
        )
        self.bubbles = InstancedMesh(
            ctx, self.sphere_program, geometry.unit_sphere(),
            "3f 1f", ("in_center", "in_radius"),
            max_instances=config.BUBBLE_COUNT_RANGE[1],
        )
        self.food = InstancedMesh(
            ctx, self.sphere_program, geometry.unit_sphere(),
            "3f 1f", ("in_center", "in_radius"),
            max_instances=config.FOOD_FLAKES,
        )

        self.helper_lines = DynamicLines(ctx, self.lines_program, config.MAX_LINE_VERTICES)

        self.rock_meshes = []
        self.rocks_version = None

        self.light_direction = normalize(config.LIGHT_DIRECTION)

    def render(self, camera, width, height, view, simulation, flock, scene):
        if width == 0 or height == 0:
            return

        ctx = self.ctx
        ctx.viewport = (0, 0, width, height)
        ctx.clear(*config.BACKGROUND_COLOR, 1.0)

        view_matrix = to_opengl(camera.view_matrix())
        projection_matrix = to_opengl(camera.projection_matrix(width / height))
        for program in self.programs:
            program["u_view"].value = view_matrix
            program["u_projection"].value = projection_matrix
        for program in self.lit_programs:
            program["u_light_direction"].value = self.light_direction
            program["u_alpha"].value = 1.0

        if scene.rocks_version != self.rocks_version:
            self._rebuild_rocks(scene.rocks, scene.rocks_version)

        ctx.enable_only(moderngl.DEPTH_TEST)
        self._draw(self.floor, config.SAND_COLOR, 1.0)
        for mesh, color in self.rock_meshes:
            self._draw(mesh, color, 1.0)
        self._draw_seaweed(scene)
        self._draw_fish(flock, scene.time, view.selected_fish)
        food_present = simulation.food_enabled and scene.food_available()
        if food_present:
            self._draw_spheres(self.food, scene.food_flakes(), config.FOOD_COLOR, 1.0)
        food = scene.food_position() if food_present else None
        self._draw_helper_lines(view, simulation, flock, scene, food)

        ctx.enable_only(moderngl.DEPTH_TEST | moderngl.BLEND | moderngl.CULL_FACE)
        ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        ctx.fbo.depth_mask = False
        ctx.cull_face = "front"
        self._draw(self.walls, config.GLASS_COLOR, view.wall_alpha)
        ctx.cull_face = "back"
        self._draw_spheres(self.bubbles, scene.bubble_instances(), config.BUBBLE_COLOR, config.BUBBLE_ALPHA)
        self._draw(self.walls, config.GLASS_COLOR, view.wall_alpha)
        ctx.fbo.depth_mask = True

        ctx.enable_only(moderngl.DEPTH_TEST)
        if view.show_edges:
            self._draw(self.edges, config.EDGE_COLOR, 1.0)

    def _rebuild_rocks(self, rocks, version):
        """Освобождает старые сетки камней и строит новые по текущему списку камней."""
        for mesh, _ in self.rock_meshes:
            mesh.release()
        self.rock_meshes = []
        for rock in rocks:
            vertices = geometry.rock(rock.center, rock.radius, rock.shape_seed)
            mesh = Mesh(self.ctx, self.lit, vertices, *LIT_LAYOUT, moderngl.TRIANGLES)
            self.rock_meshes.append((mesh, rock.color))
        self.rocks_version = version

    def _draw_seaweed(self, scene):
        data = []
        for start, end, width_start, width_end, color in scene.seaweed_segments():
            data.extend(start)
            data.extend(end)
            data.append(width_start)
            data.append(width_end)
            data.extend(color)
        self.seaweed.update(data)
        self.seaweed.render()

    def _draw_fish(self, flock, time, selected):
        neighbors = set(flock.neighbors[selected]) if selected is not None else set()
        data = []
        for i, fish in enumerate(flock.fish):
            data.extend(fish.position)
            data.extend(fish.velocity)
            if i == selected:
                data.extend(config.SELECTED_FISH_COLOR)
            elif i in neighbors:
                data.extend(config.NEIGHBOR_FISH_COLOR)
            else:
                data.extend(config.FISH_COLORS[i % len(config.FISH_COLORS)])
        self.fish.update(data)

        program = self.fish_program
        program["u_time"].value = time
        program["u_fish_length"].value = config.FISH_LENGTH
        self.fish.render()

    def _draw_helper_lines(self, view, simulation, flock, scene, food):
        """Сфера соседства, векторы скорости и сил — одним вызовом отрисовки."""
        segments = []
        if view.show_all_velocities:
            for fish in flock.fish:
                segments.append(self._arrow(fish.position, fish.velocity, config.VELOCITY_VECTOR_SCALE,
                                            config.VELOCITY_COLOR))
        selected = view.selected_fish
        if selected is not None:
            fish = flock.fish[selected]
            if view.show_neighbor_sphere:
                for start, end in geometry.sphere_outline(fish.position, flock.params.neighbor_radius,
                                                          config.NEIGHBOR_SPHERE_SEGMENTS):
                    segments.append((start, end, config.NEIGHBOR_SPHERE_COLOR))
            if view.show_force_vectors:
                if not view.show_all_velocities:
                    segments.append(self._arrow(fish.position, fish.velocity, config.VELOCITY_VECTOR_SCALE,
                                                config.VELOCITY_COLOR))
                rules, constraints = flock.force_components(selected, scene.rocks, simulation.avoid_rocks, food)
                for name, vector in rules + constraints:
                    if length(vector) > 1e-6:
                        segments.append(self._arrow(fish.position, vector, config.FORCE_VECTOR_SCALE,
                                                    config.FORCE_COLORS[name]))
        self.helper_lines.update(segments)
        self.helper_lines.render()

    @staticmethod
    def _arrow(start, vector, vector_scale, color):
        """Отрезок от start в направлении vector длиной |vector|·vector_scale."""
        return (start, add(start, scale(vector, vector_scale)), color)

    def _draw_spheres(self, mesh, spheres, color, alpha):
        """Рисует набор сфер (центр, радиус) одного цвета: пузырьки или хлопья корма."""
        data = []
        for center, radius in spheres:
            data.extend(center)
            data.append(radius)
        mesh.update(data)
        mesh.program["u_color"].value = color
        mesh.program["u_alpha"].value = alpha
        mesh.render()

    @staticmethod
    def _draw(mesh, color, alpha):
        mesh.program["u_color"].value = color
        mesh.program["u_alpha"].value = alpha
        mesh.render()

    def release(self):
        """Освобождает видеопамять. Вызывается до уничтожения контекста OpenGL."""
        for mesh in (self.floor, self.walls, self.edges, self.fish, self.seaweed, self.bubbles, self.food,
                     self.helper_lines):
            mesh.release()
        for mesh, _ in self.rock_meshes:
            mesh.release()
        for program in self.programs:
            program.release()
