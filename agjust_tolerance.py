import pygame
import numpy as np
import os
from collections import deque

from color_utils import adjust_hue_saturation

# Инициализация Pygame
pygame.init()

# Константы
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
FPS = 60
FONT_SIZE = 24

# Цвета
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (100, 100, 100)
LIGHT_GRAY = (200, 200, 200)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

# Создание окна
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("HSV Color Adjustment Tool")
clock = pygame.time.Clock()

image_path = "assets/horse/barrier/frame_0058.png"

# Параметры HSV
default_params = {
    'h_tolerance': 15,
    's_tolerance': 0.24,
    'v_tolerance': 0.26,
    'hue_shift': 30,
    'saturation_scale': 1.0,
    'value_scale': 1.0
}

params = default_params.copy()

color_range = [(191, 70, 18), (223, 122, 66)]

# Загрузка шрифта
try:
    font = pygame.font.Font(None, FONT_SIZE)
    small_font = pygame.font.Font(None, FONT_SIZE - 4)
except:
    font = pygame.font.SysFont('Arial', FONT_SIZE)
    small_font = pygame.font.SysFont('Arial', FONT_SIZE - 4)

# Загрузка изображения
def load_image():
    if not os.path.exists(image_path):
        # Создаем тестовое изображение если файл не найден
        print(f"Файл {image_path} не найден. Создаю тестовое изображение...")
        test_surface = pygame.Surface((200, 200), pygame.SRCALPHA)
        # Рисуем разноцветные круги
        colors = [(255, 0, 0, 255), (200, 50, 50, 255), (150, 0, 0, 255),
                 (0, 255, 0, 255), (50, 200, 50, 255), (0, 150, 0, 255)]
        for i, color in enumerate(colors):
            pygame.draw.circle(test_surface, color, (100, 100), 80 - i * 12)
        return test_surface
    else:
        return pygame.image.load(image_path).convert_alpha()

original_surface = load_image()
modified_surface = original_surface.copy()

# Активный параметр для регулировки
active_param = None

# Функция для обновления модифицированного изображения
def update_modified_image():
    global modified_surface
    modified_surface = adjust_hue_saturation(
        original_surface,
        color_range=color_range,
        hue_shift=params['hue_shift'],
        saturation_scale=params['saturation_scale'],
        value_scale=params['value_scale'],
        h_tolerance=params['h_tolerance'],
        s_tolerance=params['s_tolerance'],
        v_tolerance=params['v_tolerance']
    )

# Функция для отрисовки интерфейса
def draw_interface():
    # Очистка экрана
    screen.fill(GRAY)
    
    # Размеры для изображений
    img_width = original_surface.get_width()
    img_height = original_surface.get_height()
    padding = 20
    
    # Позиции для изображений
    original_pos = (padding, padding)
    modified_pos = (SCREEN_WIDTH // 2 + padding, padding)
    
    # Отрисовка изображений
    screen.blit(original_surface, original_pos)
    screen.blit(modified_surface, modified_pos)
    
    # Подписи
    original_text = font.render("Оригинал", True, WHITE)
    modified_text = font.render("Модифицированный", True, WHITE)
    screen.blit(original_text, (original_pos[0], original_pos[1] + img_height + 10))
    screen.blit(modified_text, (modified_pos[0], modified_pos[1] + img_height + 10))
    
    # Отображение параметров
    params_y = img_height + 150
    param_names = {
        'h_tolerance': f"Hue Tolerance: {params['h_tolerance']}°",
        's_tolerance': f"Sat Tolerance: {params['s_tolerance']:.2f}",
        'v_tolerance': f"Val Tolerance: {params['v_tolerance']:.2f}",
        'hue_shift': f"Hue Shift: {params['hue_shift']}°",
        'saturation_scale': f"Sat Scale: {params['saturation_scale']:.2f}",
        'value_scale': f"Val Scale: {params['value_scale']:.2f}"
    }
    
    for i, (key, text) in enumerate(param_names.items()):
        color = RED if active_param == key else WHITE
        param_text = font.render(text, True, color)
        screen.blit(param_text, (padding, params_y + i * 30))
    
    # Инструкции
    instructions = [
        "Управление:",
        "Кликните на параметр для выбора",
        "Стрелки Вверх/Вниз - регулировка",
        "R - сброс параметров",
    ]
    
    for i, instruction in enumerate(instructions):
        instr_text = small_font.render(instruction, True, LIGHT_GRAY)
        screen.blit(instr_text, (SCREEN_WIDTH - 300, 20 + i * 25))

# Обработка кликов по параметрам
def handle_param_click(mouse_pos):
    global active_param
    params_y = original_surface.get_height() + 150
    param_keys = list(params.keys())
    
    for i, key in enumerate(param_keys):
        param_rect = pygame.Rect(20, params_y + i * 30, 300, 25)
        if param_rect.collidepoint(mouse_pos):
            active_param = key
            return True
    return False

# Регулировка параметра
def adjust_param(direction):
    if active_param is None:
        return
    
    step_small = 1 if active_param in ['h_tolerance', 'hue_shift'] else 0.01
    step_large = 5 if active_param in ['h_tolerance', 'hue_shift'] else 0.05
    
    step = step_small if not pygame.key.get_mods() & pygame.KMOD_SHIFT else step_large
    
    params[active_param] += direction * step
    
    # Ограничения значений
    if active_param in ['h_tolerance', 'hue_shift']:
        params[active_param] = max(0, min(180, params[active_param]))
    elif active_param in ['s_tolerance', 'v_tolerance']:
        params[active_param] = max(0, min(1, params[active_param]))
    elif active_param in ['saturation_scale', 'value_scale']:
        params[active_param] = max(0, min(5, params[active_param]))
    
    update_modified_image()

# Сброс параметров
def reset_params():
    global params
    params = default_params.copy()
    update_modified_image()

# Основной цикл
running = True
update_modified_image()  # Первоначальное обновление

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Левая кнопка мыши
                handle_param_click(event.pos)
        
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                adjust_param(1)
            elif event.key == pygame.K_DOWN:
                adjust_param(-1)
            elif event.key == pygame.K_r:
                reset_params()
            elif event.key == pygame.K_ESCAPE:
                running = False
    
    # Отрисовка
    draw_interface()
    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()