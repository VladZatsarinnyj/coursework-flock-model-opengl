#version 330 core

uniform mat4 u_view;
uniform mat4 u_projection;
uniform vec3 u_color;

in vec3 in_position;
in vec3 in_normal;

out vec3 v_normal;
out vec3 v_color;

void main() {
    v_normal = in_normal;
    v_color = u_color;
    gl_Position = u_projection * u_view * vec4(in_position, 1.0);
}
