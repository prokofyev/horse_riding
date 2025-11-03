import random
import pygame

from constants import MAX_SPAWN_DISTANCE, MIN_SPAWN_DISTANCE
from grass import Grass


class Path:
    def __init__(self, horse, top_y, bottom_y, screen_width, controls):
        self.horse = horse
        self.screen_width = screen_width
        self.controls = controls
        self.grass_sprites = pygame.sprite.Group()
        self.spawn_distance = 0.0
        self._schedule_next_spawn()

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
        speed = self.horse.get_speed()
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

        # Спавним новую траву
        self.spawn_distance += abs(base_dx)
        if self.spawn_distance >= self.next_spawn_distance:
            self.spawn_distance = 0.0
            self._spawn_grass()
            self._schedule_next_spawn()

        # Обновляем лошадь (анимации и логику)
        self.horse.update(dt)
    
    def handle_event(self, event):
        """Обрабатывает события клавиатуры для управления лошадью"""
        if event.type == pygame.KEYDOWN:
            if event.key == self.controls.right:
                if self.horse.facing_right:
                    self.horse.accelerate()
                else:
                    self.horse.decelerate()
            elif event.key == self.controls.left:
                if self.horse.facing_right:
                    self.horse.decelerate()
                else:
                    self.horse.accelerate()
            elif event.key == self.controls.up:
                self.horse.barrier()

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

    def _schedule_next_spawn(self):
        self.next_spawn_distance = random.uniform(MIN_SPAWN_DISTANCE, MAX_SPAWN_DISTANCE)

    


