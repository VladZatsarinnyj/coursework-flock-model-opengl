#version 330 core

uniform float u_alpha;
uniform vec3 u_light_direction;

in vec3 v_normal;
in vec3 v_color;

out vec4 f_color;

const float AMBIENT = 0.35;

void main() {
    vec3 normal = normalize(v_normal);

    if (!gl_FrontFacing) {
        normal = -normal;
    }

    float diffuse = max(dot(normal, u_light_direction), 0.0);
    vec3 color = v_color * (AMBIENT + (1.0 - AMBIENT) * diffuse);

    f_color = vec4(color, u_alpha);
}
