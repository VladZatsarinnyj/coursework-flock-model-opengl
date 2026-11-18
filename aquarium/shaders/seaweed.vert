#version 330 core

// Вершинный шейдер сегмента водоросли.
// Модель сегмента одна на все водоросли (инстансинг); каждый экземпляр —
// это один сегмент: откуда и куда он идёт, его ширина и цвет.

uniform mat4 u_view;
uniform mat4 u_projection;

// Модель сегмента: крест из двух пластин, x и z от −0.5 до 0.5, y от 0 до 1.
in vec3 in_position;
in vec3 in_normal;

// Данные экземпляра (сегмента), вычисленные в scene.py.
in vec3 in_start;         // начало сегмента — конец предыдущего
in vec3 in_end;           // конец сегмента
in float in_width_start;  // ширина в начале
in float in_width_end;    // ширина в конце (к верхушке водоросль сужается)
in vec3 in_color;

out vec3 v_normal;
out vec3 v_color;

void main() {
    // Ось сегмента — его «верх». Два перпендикуляра к ней строятся так же,
    // как базис камеры в look_at и базис рыбы в fish.vert.
    vec3 axis = in_end - in_start;
    float segment_length = length(axis);
    vec3 up = axis / segment_length;
    vec3 helper = abs(up.z) > 0.99 ? vec3(1.0, 0.0, 0.0) : vec3(0.0, 0.0, 1.0);
    vec3 right = normalize(cross(up, helper));
    vec3 side = cross(right, up);

    // Ширина плавно меняется вдоль сегмента: y = 0 — начало, y = 1 — конец.
    float width = mix(in_width_start, in_width_end, in_position.y);

    vec3 world_position = in_start
        + right * (in_position.x * width)
        + up * (in_position.y * segment_length)
        + side * (in_position.z * width);

    // Нормали пластин перпендикулярны оси y, поэтому растяжение вдоль оси
    // и одинаковое масштабирование по x и z их направление не меняют.
    v_normal = mat3(right, up, side) * in_normal;
    v_color = in_color;
    gl_Position = u_projection * u_view * vec4(world_position, 1.0);
}
