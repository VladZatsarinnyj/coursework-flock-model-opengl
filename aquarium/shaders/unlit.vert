#version 330 core

// Вершинный шейдер без освещения: для линий и вспомогательной графики.

uniform mat4 u_view;
uniform mat4 u_projection;

in vec3 in_position;

void main() {
    gl_Position = u_projection * u_view * vec4(in_position, 1.0);
}
