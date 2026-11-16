#version 330 core

// Вершинный шейдер рыбы.
// Модель одной рыбы рисуется сразу для всей стаи за один вызов (инстансинг).
// Вершины модели общие, а положение, скорость и цвет — свои у каждой рыбы.

uniform mat4 u_view;
uniform mat4 u_projection;
uniform float u_time;         // время в секундах, для взмахов хвоста
uniform float u_fish_length;  // длина модели рыбы

// Атрибуты вершины модели: одинаковы для всех рыб.
in vec3 in_position;  // в системе координат рыбы: нос вдоль +X, спина вдоль +Y
in vec3 in_normal;

// Атрибуты экземпляра: свои у каждой рыбы.
in vec3 in_fish_position;
in vec3 in_fish_velocity;
in vec3 in_fish_color;

out vec3 v_normal;
out vec3 v_color;

void main() {
    // 1. Взмахи хвоста: вершины задней части сдвигаются вбок по синусоиде.
    //    Чем дальше вершина от середины тела, тем больше сдвиг. Быстрая рыба
    //    машет чаще. gl_InstanceID — номер рыбы, он сдвигает фазу, чтобы рыбы
    //    не махали хвостами синхронно.
    vec3 local = in_position;
    float tail = max(0.0, -local.x - 0.2 * u_fish_length);
    float speed = length(in_fish_velocity);
    local.z += 0.5 * tail * sin(u_time * (4.0 + 2.0 * speed) + float(gl_InstanceID));

    // 2. Поворот по направлению движения: базис строится так же, как в look_at.
    vec3 forward = normalize(in_fish_velocity);
    // Если рыба плывёт почти вертикально, forward почти параллелен (0, 1, 0)
    // и векторное произведение вырождается; тогда опорой служит ось X.
    vec3 world_up = abs(forward.y) > 0.99 ? vec3(1.0, 0.0, 0.0) : vec3(0.0, 1.0, 0.0);
    vec3 right = normalize(cross(forward, world_up));
    vec3 up = cross(right, forward);
    // Столбцы матрицы показывают, куда переходят оси модели:
    // X (нос) → forward, Y (спина) → up, Z (правый бок) → right.
    mat3 rotation = mat3(forward, up, right);

    // 3. Матрица модели M = перенос · поворот, собранная из данных рыбы.
    vec3 world_position = in_fish_position + rotation * local;
    v_normal = rotation * in_normal;
    v_color = in_fish_color;
    gl_Position = u_projection * u_view * vec4(world_position, 1.0);
}
