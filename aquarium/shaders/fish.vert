#version 330 core

uniform mat4 u_view;
uniform mat4 u_projection;
uniform float u_time;
uniform float u_fish_length;

in vec3 in_position;
in vec3 in_normal;

in vec3 in_fish_position;
in vec3 in_fish_velocity;
in vec3 in_fish_color;

out vec3 v_normal;
out vec3 v_color;

void main() {
    vec3 local = in_position;
    float tail = max(0.0, -local.x - 0.2 * u_fish_length);
    float speed = length(in_fish_velocity);
    local.z += 0.5 * tail * sin(u_time * (4.0 + 2.0 * speed) + float(gl_InstanceID));

    vec3 forward = normalize(in_fish_velocity);
    vec3 world_up = abs(forward.y) > 0.99 ? vec3(1.0, 0.0, 0.0) : vec3(0.0, 1.0, 0.0);
    vec3 right = normalize(cross(forward, world_up));
    vec3 up = cross(right, forward);
    mat3 rotation = mat3(forward, up, right);

    vec3 world_position = in_fish_position + rotation * local;
    v_normal = rotation * in_normal;
    v_color = in_fish_color;
    gl_Position = u_projection * u_view * vec4(world_position, 1.0);
}
