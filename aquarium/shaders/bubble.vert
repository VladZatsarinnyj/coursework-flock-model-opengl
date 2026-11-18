#version 330 core

// Вершинный шейдер маленьких сфер: пузырьков и хлопьев корма.
// Единичная сфера переносится в центр сферы и растягивается до её радиуса.
// Все сферы одного вида рисуются одним вызовом (инстансинг).

uniform mat4 u_view;
uniform mat4 u_projection;
uniform vec3 u_color;

in vec3 in_position;  // точка единичной сферы
in vec3 in_normal;

in vec3 in_center;    // данные экземпляра: центр пузырька
in float in_radius;   // и его радиус

out vec3 v_normal;
out vec3 v_color;

void main() {
    // Равномерное масштабирование не меняет направление нормалей.
    v_normal = in_normal;
    v_color = u_color;
    gl_Position = u_projection * u_view * vec4(in_center + in_position * in_radius, 1.0);
}
