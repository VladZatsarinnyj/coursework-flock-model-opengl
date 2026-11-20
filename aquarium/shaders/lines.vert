#version 330 core

uniform mat4 u_view;
uniform mat4 u_projection;

in vec3 in_position;
in vec3 in_color;

out vec3 v_color;

void main() {
    v_color = in_color;
    gl_Position = u_projection * u_view * vec4(in_position, 1.0);
}
