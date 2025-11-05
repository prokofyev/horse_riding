import random
import os
import glob
import pygame

from constants import HORSE_MARGIN_LEFT, HORSE_MARGIN_RIGHT, MAX_SPAWN_DISTANCE, MIN_SPAWN_DISTANCE, BARRIER_MIN_SPAWN_DISTANCE, BARRIER_MAX_SPAWN_DISTANCE, SKY_COLOR, GRASS_COLOR
from grass import Grass
from barrier import Barrier
from flag import Flag


class Path:
    def __init__(self, horse, top_y, bottom_y, screen_width, controls, get_winner, set_winner):
        self.horse = horse
        self.screen_width = screen_width
        self.controls = controls
        self.get_winner = get_winner
        self.set_winner = set_winner
        self.grass_sprites = pygame.sprite.Group()
        self.barrier_sprites = pygame.sprite.Group()
        self.spawn_distance = 0.0
        self.barrier_spawn_distance = 0.0
        self._schedule_next_spawn()
        self._schedule_next_barrier_spawn()
        self.path_distance = 50000
        self.traveled_distance = 0
        self.flag_spawned = False
        self.is_winner = False

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
        self.sky_max_y = int(top_y + area_height * 0.5)

        # Отступы за пределы экрана для спауна/очистки
        self.offscreen_margin = 64

        # Фоновое изображение неба
        self.sky_bg = self._load_sky_background()
        self._sky_bg_scaled = None

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
        if self.barrier_spawn_distance >= self.next_barrier_spawn_distance and not self.flag_spawned:
            self.barrier_spawn_distance = 0.0
            self._spawn_barrier()
            self._schedule_next_barrier_spawn()

        # Проверка прохождения флага (победа)
        if not self.is_winner and self.get_winner() is None:
            for obj in list(self.grass_sprites):
                if isinstance(obj, Flag):
                    # Условие: лошадь проехала мимо флага
                    if self.horse.rect.right >= obj.rect.left:
                        self.set_winner(self)
                        self.is_winner = True
                        break

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
        # Небо (изображение из assets/backgrounds) или цветовой бэкап
        sky_height = self.sky_max_y - self.top_y
        if sky_height > 0:
            if self.sky_bg is not None:
                self._ensure_sky_scaled(sky_height)
                if self._sky_bg_scaled:
                    tile_w = self._sky_bg_scaled.get_width()
                    if tile_w >= self.screen_width:
                        # Если изображение шире экрана — обрезаем по ширине
                        src_rect = pygame.Rect(0, 0, self.screen_width, sky_height)
                        surface.blit(self._sky_bg_scaled, (0, self.top_y), src_rect)
                    else:
                        # Если уже — повторяем по горизонтали, чередуя с отражением
                        x = 0
                        use_flip = False
                        while x < self.screen_width:
                            tile_surface = self._sky_bg_scaled_flipped if use_flip and self._sky_bg_scaled_flipped else self._sky_bg_scaled
                            remaining = self.screen_width - x
                            draw_w = tile_surface.get_width()
                            if draw_w > remaining:
                                src_rect = pygame.Rect(0, 0, remaining, sky_height)
                                surface.blit(tile_surface, (x, self.top_y), src_rect)
                                break
                            else:
                                surface.blit(tile_surface, (x, self.top_y))
                            x += draw_w
                            use_flip = not use_flip
            else:
                pygame.draw.rect(surface, SKY_COLOR, (0, self.top_y, self.screen_width, sky_height))

        # Почва/трава как фон области от границы неба до низа дорожки
        ground_y = self.sky_max_y
        ground_h = max(0, self.bottom_y - ground_y)
        if ground_h > 0:
            pygame.draw.rect(surface, GRASS_COLOR, (0, ground_y, self.screen_width, ground_h))

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

        # Сообщение ПОБЕДА по центру дорожки
        if self.is_winner:
            font = pygame.font.SysFont(None, 250)
            text_surface = font.render("ПОБЕДА", True, (255, 255, 255))
            shadow_surface = font.render("ПОБЕДА", True, (0, 0, 0))
            center_x = self.screen_width // 2
            center_y = (self.top_y + self.bottom_y) // 2
            text_rect = text_surface.get_rect(center=(center_x, center_y))
            shadow_rect = shadow_surface.get_rect(center=(center_x + 2, center_y + 2))
            surface.blit(shadow_surface, shadow_rect)
            surface.blit(text_surface, text_rect)

    def _load_sky_background(self):
        """Загружает случайное изображение неба из assets/backgrounds."""
        try:
            folder = os.path.join('assets', 'backgrounds')
            candidates = sorted(glob.glob(os.path.join(folder, '*.png')))
            if not candidates:
                return None
            path = random.choice(candidates)
            img = pygame.image.load(path).convert()
            return img
        except Exception as e:
            print(f"Error loading sky background: {e}")
            return None

    def _ensure_sky_scaled(self, sky_height):
        """Готовит масштабированную версию неба под фиксированную высоту sky_height,
        сохраняя соотношение сторон; ширина может быть больше экрана и будет обрезана при отрисовке."""
        if self.sky_bg is None:
            self._sky_bg_scaled = None
            return
        # Масштабируем по высоте, сохраняя аспект
        src_w = self.sky_bg.get_width()
        src_h = self.sky_bg.get_height()
        if src_h <= 0:
            self._sky_bg_scaled = None
            return
        target_h = sky_height
        target_w = int(src_w * (target_h / float(src_h)))
        # Если уже есть нужного размера — не пересоздаём
        if (self._sky_bg_scaled is None or
            self._sky_bg_scaled.get_height() != target_h or
            self._sky_bg_scaled.get_width() != target_w):
            try:
                self._sky_bg_scaled = pygame.transform.smoothscale(self.sky_bg, (target_w, target_h))
            except Exception:
                self._sky_bg_scaled = pygame.transform.scale(self.sky_bg, (target_w, target_h))
            # Подготовим отраженную версию для чередования
            try:
                self._sky_bg_scaled_flipped = pygame.transform.flip(self._sky_bg_scaled, True, False)
            except Exception:
                self._sky_bg_scaled_flipped = None

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

    


