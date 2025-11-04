import random
import pygame

from constants import HORSE_MARGIN_LEFT, HORSE_MARGIN_RIGHT, MAX_SPAWN_DISTANCE, MIN_SPAWN_DISTANCE, BARRIER_MIN_SPAWN_DISTANCE, BARRIER_MAX_SPAWN_DISTANCE
from grass import Grass
from barrier import Barrier
from flag import Flag


class Path:
    def __init__(self, horse, top_y, bottom_y, screen_width, controls):
        self.horse = horse
        self.screen_width = screen_width
        self.controls = controls
        self.grass_sprites = pygame.sprite.Group()
        self.barrier_sprites = pygame.sprite.Group()
        self.spawn_distance = 0.0
        self.barrier_spawn_distance = 0.0
        self._schedule_next_spawn()
        self._schedule_next_barrier_spawn()
        self.path_distance = 100
        self.traveled_distance = 0
        self.flag_spawned = False

        # Границы области для этой дорожки
        self.top_y = top_y
        self.bottom_y = bottom_y
        
        # Вертикальная полоса для травы (у земли в пределах области)
        area_height = bottom_y - top_y

        self.min_y = int(top_y + area_height * 0.65)
        self.max_y = int(top_y + area_height * 0.99)

        self.horse_shadow_min_y = int(top_y + area_height * 0.78)
        self.horse_shadow_max_y = int(top_y + area_height * 0.9)

        self.barrier_max_y = int(top_y + area_height * 0.9)

        # Отступы за пределы экрана для спауна/очистки
        self.offscreen_margin = 64

    def update(self, dt):
        speed = self.horse.get_speed()
        if speed != 0:
            direction = -1 if self.horse.facing_right else 1
            base_dx = direction * speed * dt
        else:
            base_dx = 0

        self.traveled_distance -= base_dx # движение направо с минусом
        # Держим прогресс в пределах дистанции
        if self.path_distance > 0:
            if self.traveled_distance < 0:
                self.traveled_distance = 0
            elif self.traveled_distance > self.path_distance:
                self.traveled_distance = self.path_distance

        # Двигаем траву с учетом перспективы (ниже = быстрее)
        for sprite in list(self.grass_sprites):
            # Обновляем анимацию объектов, если есть
            if hasattr(sprite, 'update'):
                try:
                    sprite.update(dt)
                except TypeError:
                    pass
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

        for sprite in list(self.barrier_sprites):
            y_range = self.max_y - self.min_y
            if y_range > 0:
                perspective_factor = (sprite.rect.bottom - self.min_y) / y_range
                perspective_multiplier = perspective_factor + 1.0
            else:
                perspective_multiplier = 1.0
                
            dx = int(base_dx * perspective_multiplier)
            sprite.rect.x += dx
            if sprite.rect.right < -self.offscreen_margin or sprite.rect.left > self.screen_width + self.offscreen_margin:
                self.barrier_sprites.remove(sprite)

        if self.horse.current_animation in ['trot', 'gallop'] or \
                self.horse.current_animation in ['barrier'] and self.horse.is_near_ground():
            collided = False
            for barrier in self.barrier_sprites:
                if self.horse.collide_barrier(barrier):
                    collided = True
            if collided:
                self.horse.make_fall()

        # Спавним новую траву
        self.spawn_distance += abs(base_dx)
        if self.spawn_distance >= self.next_spawn_distance:
            self.spawn_distance = 0.0
            self._spawn_grass()
            self._schedule_next_spawn()

        # Спавним новый барьер (реже)
        self.barrier_spawn_distance += abs(base_dx)
        if self.barrier_spawn_distance >= self.next_barrier_spawn_distance:
            self.barrier_spawn_distance = 0.0
            self._spawn_barrier()
            self._schedule_next_barrier_spawn()

        if self.traveled_distance >= self.path_distance:
            self._spawn_flag()

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
        self.barrier_sprites.draw(surface)

        # Прогресс-бар расстояния (для верхней дорожки — внизу области)
        if self.path_distance > 0:
            bar_margin_x = 20
            bar_margin_y = 10
            bar_height = 10
            bar_width = max(10, self.screen_width - bar_margin_x * 2)
            bar_x = bar_margin_x
            # По умолчанию сверху области дорожки
            bar_y = self.top_y + bar_margin_y
            # Если это верхняя дорожка (начинается от самого верха экрана), рисуем полосу внизу ее области
            if self.top_y == 0:
                bar_y = self.bottom_y - bar_margin_y - bar_height

            # Фон и рамка
            pygame.draw.rect(surface, (40, 40, 40), (bar_x, bar_y, bar_width, bar_height))
            pygame.draw.rect(surface, (200, 200, 200), (bar_x, bar_y, bar_width, bar_height), 1)

            # Заполнение
            ratio = self.traveled_distance / float(self.path_distance)
            ratio = max(0.0, min(1.0, ratio))
            fill_w = int(bar_width * ratio)
            if fill_w > 0:
                pygame.draw.rect(surface, (80, 200, 80), (bar_x, bar_y, fill_w, bar_height))

        # pygame.draw.line(surface, (100, 100, 100), (0, self.min_y), (self.screen_width, self.min_y), 1)
        # pygame.draw.line(surface, (100, 100, 100), (0, self.max_y), (self.screen_width, self.max_y), 1)

        # pygame.draw.line(surface, (0, 100, 100), (0, self.horse_shadow_min_y), (self.screen_width, self.horse_shadow_min_y), 1)
        # pygame.draw.line(surface, (0, 100, 100), (0, self.horse_shadow_max_y), (self.screen_width, self.horse_shadow_max_y), 1)

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

    def _spawn_barrier(self):
        y = self.barrier_max_y
        if self.horse.facing_right:
            x = self.screen_width + self.offscreen_margin
        else:
            x = -self.offscreen_margin
        barrier = Barrier((x, y))
        self.barrier_sprites.add(barrier)

    def _spawn_flag(self):
        if self.flag_spawned:
            return 

        y = self.horse_shadow_min_y
        if self.horse.facing_right:
            x = self.screen_width + self.offscreen_margin
        else:
            x = -self.offscreen_margin
        flag = Flag((x, y))
        self.grass_sprites.add(flag)
        self.flag_spawned = True

    def _schedule_next_spawn(self):
        self.next_spawn_distance = random.uniform(MIN_SPAWN_DISTANCE, MAX_SPAWN_DISTANCE)

    def _schedule_next_barrier_spawn(self):
        self.next_barrier_spawn_distance = random.uniform(BARRIER_MIN_SPAWN_DISTANCE, BARRIER_MAX_SPAWN_DISTANCE)

    


