#version 330 core

// Фрагментный шейдер вспомогательных линий: цвет из вершинного шейдера.

in vec3 v_color;

out vec4 f_color;

void main() {
    f_color = vec4(v_color, 1.0);
}
