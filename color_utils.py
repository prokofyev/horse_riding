import pygame
import numpy as np
from collections import deque

def adjust_hue_saturation(surface, color_range, hue_shift=0, saturation_scale=1.0, 
                               value_scale=1.0, h_tolerance=10, s_tolerance=0.2, v_tolerance=0.2, 
                               connectivity=8):
    """
    Модифицирует тон и насыщенность для области пикселей со схожими HSV компонентами
    
    Args:
        surface: pygame.Surface
        color_range: ((r_min, g_min, b_min), (r_max, g_max, b_max)) - диапазон для начальных пикселей
        hue_shift: сдвиг тона в градусах
        saturation_scale: множитель насыщенности
        value_scale: множитель яркости
        h_tolerance: допустимая разница Hue (в градусах 0-180)
        s_tolerance: допустимая разница Saturation (0-1)
        v_tolerance: допустимая разница Value (0-1)
        connectivity: 4 или 8-связность
    """
    # Создаем копию массива пикселей
    pixel_array = pygame.surfarray.pixels3d(surface).copy()
    has_alpha = surface.get_bytesize() == 4
    
    if has_alpha:
        alpha_array = pygame.surfarray.pixels_alpha(surface).copy()
    
    # Находим все пиксели в начальном диапазоне color_range (в RGB)
    start_pixels_mask = find_pixels_in_color_range(pixel_array, color_range, has_alpha, alpha_array)
    
    if not np.any(start_pixels_mask):
        # print("Не найдено пикселей в начальном диапазоне цветов")
        return surface
    
    # Вычисляем средние HSV компоненты начальных пикселей
    start_pixels = pixel_array[start_pixels_mask]
    start_pixels_float = start_pixels.astype(np.float32) / 255.0
    start_hsv = rgb_to_hsv_vectorized(start_pixels_float)
    
    avg_hue = np.mean(start_hsv[:, 0])
    avg_saturation = np.mean(start_hsv[:, 1])
    avg_value = np.mean(start_hsv[:, 2])
    
    # print(f"Средние HSV начальных пикселей:")
    # print(f"  Hue: {avg_hue:.1f}°")
    # print(f"  Saturation: {avg_saturation:.3f}")
    # print(f"  Value: {avg_value:.3f}")
    
    # Выращиваем область по схожести всех трех HSV компонент
    region_mask = grow_region_by_hsv(
        pixel_array, start_pixels_mask, avg_hue, avg_saturation, avg_value,
        h_tolerance, s_tolerance, v_tolerance, has_alpha, alpha_array, connectivity
    )
    
    # Если нашли область для обработки
    if np.any(region_mask):
        region_size = np.sum(region_mask)
        start_pixels_count = np.sum(start_pixels_mask)
        added_pixels_count = region_size - start_pixels_count
        
        # print(f"Начальных пикселей: {start_pixels_count}")
        # print(f"Добавленных пикселей: {added_pixels_count}")
        # print(f"Всего обработано: {region_size} пикселей")
        
        # Конвертируем в float для вычислений
        pixel_array_float = pixel_array.astype(np.float32) / 255.0
        
        # Получаем пиксели из найденной области
        region_pixels = pixel_array_float[region_mask]
        
        # Конвертируем в HSV и применяем модификации
        hsv_pixels = rgb_to_hsv_vectorized(region_pixels)
        hsv_pixels[:, 0] = (hsv_pixels[:, 0] + hue_shift) % 360
        hsv_pixels[:, 1] = np.clip(hsv_pixels[:, 1] * saturation_scale, 0, 1)
        hsv_pixels[:, 2] = np.clip(hsv_pixels[:, 2] * value_scale, 0, 1)
        
        # Конвертируем обратно в RGB
        rgb_modified = hsv_to_rgb_vectorized(hsv_pixels)
        
        # Обновляем только пиксели в найденной области
        pixel_array_float[region_mask] = rgb_modified
        pixel_array[:,:,:] = (pixel_array_float * 255).astype(np.uint8)
    else:
        # print("Не удалось найти область для обработки")
        pass
    
    # Создаем новую поверхность
    new_surface = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    pygame.surfarray.blit_array(new_surface, pixel_array)
    
    # Восстанавливаем альфа-канал
    if has_alpha:
        pygame.surfarray.pixels_alpha(new_surface)[:] = alpha_array
    
    return new_surface

def grow_region_by_hsv(pixel_array, start_pixels_mask, target_hue, target_saturation, target_value,
                      h_tolerance, s_tolerance, v_tolerance, has_alpha, alpha_array=None, connectivity=8):
    """
    Выращивает область по схожести всех трех HSV компонент
    """
    height, width = pixel_array.shape[:2]
    
    # Маска для отслеживания посещенных пикселей
    visited = np.zeros((height, width), dtype=bool)
    region_mask = np.zeros((height, width), dtype=bool)
    
    # Начальные пиксели уже добавлены в регион
    region_mask[start_pixels_mask] = True
    visited[start_pixels_mask] = True
    
    # Направления
    if connectivity == 4:
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]
    else:  # 8-связность
        directions = [(0, 1), (1, 1), (1, 0), (1, -1), 
                     (0, -1), (-1, -1), (-1, 0), (-1, 1)]
    
    # Очередь для BFS - добавляем все начальные пиксели
    queue = deque()
    start_y, start_x = np.where(start_pixels_mask)
    for x, y in zip(start_x, start_y):
        queue.append((x, y))
    
    # Предварительно конвертируем весь массив в HSV для производительности
    pixel_array_float = pixel_array.astype(np.float32) / 255.0
    hsv_array = rgb_to_hsv_vectorized(pixel_array_float.reshape(-1, 3))
    hsv_array = hsv_array.reshape(height, width, 3)
    
    added_pixels = 0
    
    while queue:
        x, y = queue.popleft()
        
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            
            # Проверка границ и посещения
            if 0 <= nx < width and 0 <= ny < height and not visited[ny, nx]:
                # Проверка прозрачности
                if has_alpha and alpha_array[ny, nx] == 0:
                    visited[ny, nx] = True
                    continue
                
                current_hue = hsv_array[ny, nx, 0]
                current_saturation = hsv_array[ny, nx, 1]
                current_value = hsv_array[ny, nx, 2]
                
                # Проверяем схожесть всех трех компонент
                if hsv_similarity(current_hue, current_saturation, current_value,
                                target_hue, target_saturation, target_value,
                                h_tolerance, s_tolerance, v_tolerance):
                    visited[ny, nx] = True
                    region_mask[ny, nx] = True
                    queue.append((nx, ny))
                    added_pixels += 1
                else:
                    visited[ny, nx] = True
    
    # print(f"Добавлено {added_pixels} пикселей по схожести HSV")
    return region_mask

def hsv_similarity(h1, s1, v1, h2, s2, v2, h_tol, s_tol, v_tol):
    """
    Проверяет схожесть всех трех HSV компонент
    """
    # Проверяем Hue (с учетом циклической природы)
    h_diff = abs(h1 - h2)
    h_similar = min(h_diff, 360 - h_diff) <= h_tol
    
    # Проверяем Saturation и Value (линейные)
    s_similar = abs(s1 - s2) <= s_tol
    v_similar = abs(v1 - v2) <= v_tol
    
    return h_similar and s_similar and v_similar

def find_pixels_in_color_range(pixel_array, color_range, has_alpha, alpha_array=None):
    """Находит все пиксели в диапазоне color_range (RGB)"""
    low, high = color_range
    low = np.array(low)
    high = np.array(high)
    
    color_mask = np.all((pixel_array >= low) & (pixel_array <= high), axis=2)
    
    if has_alpha:
        color_mask = color_mask & (alpha_array > 0)
    
    return color_mask

def rgb_to_hsv_vectorized(rgb):
    """Векторизованная конвертация RGB в HSV"""
    r, g, b = rgb[:, 0], rgb[:, 1], rgb[:, 2]
    
    max_val = np.maximum(np.maximum(r, g), b)
    min_val = np.minimum(np.minimum(r, g), b)
    delta = max_val - min_val
    
    h = np.zeros_like(r)
    mask = delta != 0
    r_mask = mask & (max_val == r)
    g_mask = mask & (max_val == g)
    b_mask = mask & (max_val == b)
    
    h[r_mask] = 60 * (((g[r_mask] - b[r_mask]) / delta[r_mask]) % 6)
    h[g_mask] = 60 * (((b[g_mask] - r[g_mask]) / delta[g_mask]) + 2)
    h[b_mask] = 60 * (((r[b_mask] - g[b_mask]) / delta[b_mask]) + 4)
    
    s = np.zeros_like(r)
    s[mask] = delta[mask] / max_val[mask]
    
    v = max_val
    
    return np.column_stack([h, s, v])

def hsv_to_rgb_vectorized(hsv):
    """Векторизованная конвертация HSV в RGB"""
    h, s, v = hsv[:, 0], hsv[:, 1], hsv[:, 2]
    
    c = v * s
    x = c * (1 - np.abs((h / 60) % 2 - 1))
    m = v - c
    
    rgb = np.zeros_like(hsv)
    
    mask0 = (0 <= h) & (h < 60)
    mask1 = (60 <= h) & (h < 120)
    mask2 = (120 <= h) & (h < 180)
    mask3 = (180 <= h) & (h < 240)
    mask4 = (240 <= h) & (h < 300)
    mask5 = (300 <= h) & (h < 360)
    
    rgb[mask0, :] = np.column_stack([c[mask0], x[mask0], np.zeros(np.sum(mask0))])
    rgb[mask1, :] = np.column_stack([x[mask1], c[mask1], np.zeros(np.sum(mask1))])
    rgb[mask2, :] = np.column_stack([np.zeros(np.sum(mask2)), c[mask2], x[mask2]])
    rgb[mask3, :] = np.column_stack([np.zeros(np.sum(mask3)), x[mask3], c[mask3]])
    rgb[mask4, :] = np.column_stack([x[mask4], np.zeros(np.sum(mask4)), c[mask4]])
    rgb[mask5, :] = np.column_stack([c[mask5], np.zeros(np.sum(mask5)), x[mask5]])
    
    rgb += m[:, np.newaxis]
    return np.clip(rgb, 0, 1)