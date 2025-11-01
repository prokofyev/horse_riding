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

        self.min_y = int(top_y + area_height * 0.65)
        self.max_y = int(top_y + area_height * 0.99)

        self.horse_shadow_min_y = int(top_y + area_height * 0.78)
        self.horse_shadow_max_y = int(top_y + area_height * 0.9)

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
                perspective_factor = (sprite.rect.bottom - self.min_y) / y_range
                perspective_multiplier = perspective_factor + 1.0
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

        pygame.draw.line(surface, (100, 100, 100), (0, self.min_y), (self.screen_width, self.min_y), 1)
        pygame.draw.line(surface, (100, 100, 100), (0, self.max_y), (self.screen_width, self.max_y), 1)

        pygame.draw.line(surface, (0, 100, 100), (0, self.horse_shadow_min_y), (self.screen_width, self.horse_shadow_min_y), 1)
        pygame.draw.line(surface, (0, 100, 100), (0, self.horse_shadow_max_y), (self.screen_width, self.horse_shadow_max_y), 1)

    def _spawn_grass(self):
        y = None
        while y is None:
            y = random.randint(self.min_y, self.max_y)
            if y > self.horse_shadow_min_y and y < self.horse_shadow_max_y:
                y = None

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

        MIN_SPAWN_INTERVAL = 0.5
        MAX_SPAWN_INTERVAL = 1.5

        MIN_SPEED = 0
        MAX_SPEED = 400

        t = max(MIN_SPEED, min(MAX_SPEED, speed))
        base = MAX_SPAWN_INTERVAL - (t - MIN_SPEED) * ((MAX_SPAWN_INTERVAL - MIN_SPAWN_INTERVAL) / 
            (MAX_SPEED - MIN_SPEED))

        jitter = random.uniform(-0.1, 0.1)
        self.next_spawn = max(MIN_SPAWN_INTERVAL, base + jitter)

    def _get_background_speed(self):
        # Пиксели в секунду для сдвига бэкграунда
        anim = self.horse.current_animation
        if anim in ['gallop']:
            return 380
        if anim in ['trot']:
            return 260
        if anim in ['walk']:
            return 150
        if anim in ['start_moving']:
            return 120
        if anim in ['stop_moving']:
            return 80
        # Прыжок/барьер пусть сохраняет текущую видимую скорость
        if anim in ['barrier']:
            return 220

        return 0


