import random
import pygame

from grass import Grass


class Path:
    def __init__(self, horse, top_y, bottom_y, screen_width):
        self.horse = horse
        self.screen_width = screen_width
        self.grass_sprites = pygame.sprite.Group()
        self.spawn_timer = 0.0
        self.next_spawn = 0.0
        self._schedule_next_spawn(0)

        # Границы области для этой дорожки
        self.top_y = top_y
        self.bottom_y = bottom_y
        
        # Вертикальная полоса для травы (у земли в пределах области)
        area_height = bottom_y - top_y
        # Трава занимает нижние 25-30% области
        self.min_y = int(top_y + area_height * 0.65)
        self.max_y = int(top_y + area_height * 0.9)

        # Отступы за пределы экрана для спауна/очистки
        self.offscreen_margin = 64

    def update(self, dt):
        speed = self._get_background_speed()
        if speed != 0:
            direction = -1 if self.horse.facing_right else 1
            base_dx = direction * speed * dt
        else:
            base_dx = 0

        # Двигаем траву с учетом перспективы (ниже = быстрее)
        for sprite in list(self.grass_sprites):
            # Вычисляем множитель перспективы на основе Y-координаты
            # Трава ниже (ближе к max_y) движется быстрее
            y_range = self.max_y - self.min_y
            if y_range > 0:
                # Нормализуем: 0 (min_y) до 1 (max_y)
                perspective_factor = (sprite.rect.y - self.min_y) / y_range
                # Применяем множитель: от 0.5 (верх) до 1.5 (низ) для усиления эффекта
                perspective_multiplier = 0.5 + perspective_factor
            else:
                perspective_multiplier = 1.0
            
            # Применяем перспективу к скорости
            dx = int(base_dx * perspective_multiplier)
            sprite.rect.x += dx
            
            if sprite.rect.right < -self.offscreen_margin or sprite.rect.left > self.screen_width + self.offscreen_margin:
                self.grass_sprites.remove(sprite)

        # Спавним новую траву в зависимости от скорости
        if speed > 0:
            self.spawn_timer += dt
            if self.spawn_timer >= self.next_spawn:
                self.spawn_timer = 0.0
                self._spawn_grass()
                self._schedule_next_spawn(speed)

        # Обновляем лошадь (анимации и логику)
        self.horse.update(dt)

    def draw(self, surface):
        self.grass_sprites.draw(surface)
        self.horse.draw(surface)

    def _spawn_grass(self):
        y = random.randint(self.min_y, self.max_y)
        if self.horse.facing_right:
            # Двигаемся направо -> фон идет влево: спавним справа
            x = self.screen_width + self.offscreen_margin
        else:
            # Двигаемся налево -> фон идет вправо: спавним слева
            x = -self.offscreen_margin
        grass = Grass((x, y))
        self.grass_sprites.add(grass)

    def _schedule_next_spawn(self, speed):
        # Чем больше скорость, тем чаще спавним
        # Базовый интервал (в секундах)
        if speed <= 0:
            self.next_spawn = 0.5
            return
        # Нормируем: 50..400 px/s -> 0.6..0.15 сек
        t = max(50, min(400, speed))
        base = 0.6 - (t - 50) * (0.45 / 350.0)
        jitter = random.uniform(-0.1, 0.1)
        self.next_spawn = max(0.05, base + jitter)

    def _get_background_speed(self):
        # Пиксели в секунду для сдвига бэкграунда
        anim = self.horse.current_animation
        if anim in ['gallop']:
            return 380
        if anim in ['trot']:
            return 240
        if anim in ['walk']:
            return 200
        if anim in ['start_moving']:
            return 120
        if anim in ['stop_moving']:
            return 80
        # Прыжок/барьер пусть сохраняет текущую видимую скорость
        if anim in ['barrier']:
            return 220
        # Поворот — фон почти стоит
        if anim in ['turn']:
            return 0
        # idle и прочее — фон не движется
        return 0


