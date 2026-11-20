#version 330 core

uniform mat4 u_view;
uniform mat4 u_projection;

in vec3 in_position;
in vec3 in_normal;

in vec3 in_start;
in vec3 in_end;
in float in_width_start;
in float in_width_end;
in vec3 in_color;

out vec3 v_normal;
out vec3 v_color;

void main() {
    vec3 axis = in_end - in_start;
    float segment_length = length(axis);
    vec3 up = axis / segment_length;
    vec3 helper = abs(up.z) > 0.99 ? vec3(1.0, 0.0, 0.0) : vec3(0.0, 0.0, 1.0);
    vec3 right = normalize(cross(up, helper));
    vec3 side = cross(right, up);

    float width = mix(in_width_start, in_width_end, in_position.y);

    vec3 world_position = in_start
        + right * (in_position.x * width)
        + up * (in_position.y * segment_length)
        + side * (in_position.z * width);

    v_normal = mat3(right, up, side) * in_normal;
    v_color = in_color;
    gl_Position = u_projection * u_view * vec4(world_position, 1.0);
}
