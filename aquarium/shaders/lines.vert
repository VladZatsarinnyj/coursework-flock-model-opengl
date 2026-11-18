#version 330 core

// Вершинный шейдер вспомогательных линий: сфера соседства, векторы скорости и сил.
// В отличие от unlit.vert, цвет задаётся у каждой вершины, поэтому все линии
// разных цветов рисуются одним вызовом.

uniform mat4 u_view;
uniform mat4 u_projection;

in vec3 in_position;  // мировые координаты
in vec3 in_color;

out vec3 v_color;

void main() {
    v_color = in_color;
    gl_Position = u_projection * u_view * vec4(in_position, 1.0);
}
