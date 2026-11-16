#version 330 core

// Фрагментный шейдер: освещение по закону Ламберта плюс фоновая подсветка.
// Выполняется для каждого фрагмента (кандидата в пиксель) треугольника.

uniform vec3 u_color;            // цвет поверхности
uniform float u_alpha;           // непрозрачность: 1 — непрозрачная поверхность
uniform vec3 u_light_direction;  // единичный вектор от поверхности к источнику света

in vec3 v_normal;

out vec4 f_color;

const float AMBIENT = 0.35;  // фоновый свет, чтобы теневые стороны не были чёрными

void main() {
    vec3 normal = normalize(v_normal);

    // Стенки видны и снаружи, и изнутри. Если камера видит обратную сторону
    // треугольника, нормаль разворачивается к камере.
    if (!gl_FrontFacing) {
        normal = -normal;
    }

    // Закон Ламберта: яркость пропорциональна косинусу угла между нормалью
    // и направлением на свет. Отрицательные значения (свет сзади) обнуляются.
    float diffuse = max(dot(normal, u_light_direction), 0.0);
    vec3 color = u_color * (AMBIENT + (1.0 - AMBIENT) * diffuse);

    f_color = vec4(color, u_alpha);
}
