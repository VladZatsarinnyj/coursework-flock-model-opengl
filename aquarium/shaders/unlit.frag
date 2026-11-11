#version 330 core

// Фрагментный шейдер с постоянным цветом.

uniform vec3 u_color;
uniform float u_alpha;

out vec4 f_color;

void main() {
    f_color = vec4(u_color, u_alpha);
}
