import pygame

from constants import HORSE_SHADOW_MAX_Y_FRAC, HORSE_SHADOW_MIN_Y_FRAC, SKY_COLOR, GRASS_COLOR, SKY_PROPORTION
from grass import Grass
from barrier import Barrier
from flag import Flag
from track_plan import TrackPlan


class Path:
    def __init__(self, horse, top_y, bottom_y, screen_width, controls, race_controller, plan: TrackPlan):
        self.horse = horse
        self.screen_width = screen_width
        self.controls = controls
        self.race_controller = race_controller
        self.plan = plan
        self.next_event_idx = 0
        self.grass_sprites = pygame.sprite.Group()
        self.barrier_sprites = pygame.sprite.Group()
        self.flag_sprites = pygame.sprite.Group()
        self.path_distance = plan.total_distance   
        self.traveled_distance = 0
        self.is_winner = False

        # Границы области для этой дорожки
        self.top_y = top_y
        self.bottom_y = bottom_y
        
        # Отступы за пределы экрана для спауна/очистки
        self.offscreen_margin = 64

        self.sky_bg = pygame.image.load(self.plan.sky_background_path).convert()
        self._sky_bg_scaled = None

    def update(self, dt):
        speed = self.horse.get_speed()

        direction = -1 if self.horse.facing_right else 1
        base_dx = direction * speed * dt

        self.traveled_distance -= base_dx # движение направо с минусом
        # Держим прогресс в пределах дистанции
        if self.path_distance > 0:
            if self.traveled_distance < 0:
                self.traveled_distance = 0
            elif self.traveled_distance > self.path_distance:
                self.traveled_distance = self.path_distance

        sky_height = int((self.bottom_y - self.top_y) * SKY_PROPORTION)
        ground_y = self.top_y + sky_height

        horse_y = self.top_y + int((self.bottom_y - self.top_y) * HORSE_SHADOW_MAX_Y_FRAC)

        # Двигаем флаг с учетом перспективы (ниже = быстрее)
        for sprite in list(self.flag_sprites):
            sprite.update(dt)

            perspective_factor = (sprite.rect.bottom - ground_y) / (horse_y - ground_y)
            
            dxf = base_dx * perspective_factor
            sprite.pos_x += dxf
            sprite.rect.x = round(sprite.pos_x)
            
            if sprite.rect.right < -self.offscreen_margin or sprite.rect.left > self.screen_width + self.offscreen_margin:
                self.flag_sprites.remove(sprite)

        # Двигаем траву с учетом перспективы (ниже = быстрее)
        for sprite in list(self.grass_sprites):
            perspective_factor = (sprite.rect.bottom - ground_y) / (horse_y - ground_y)
            
            dxf = base_dx * perspective_factor
            sprite.pos_x += dxf
            sprite.rect.x = round(sprite.pos_x)
            
            if sprite.rect.right < -self.offscreen_margin or sprite.rect.left > self.screen_width + self.offscreen_margin:
                self.grass_sprites.remove(sprite)

        for sprite in list(self.barrier_sprites):
            perspective_factor = (sprite.rect.bottom - ground_y) / (horse_y - ground_y)
                
            dxf = base_dx * perspective_factor
            sprite.pos_x += dxf
            sprite.rect.x = round(sprite.pos_x)
            
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

        # Спавним события из плана 
        while self.next_event_idx < len(self.plan.events) and self.traveled_distance >= self.plan.events[self.next_event_idx].distance:
            ev = self.plan.events[self.next_event_idx]
            if ev.kind == 'grass':
                self._spawn_grass_from_frac(ev.y_frac)
            elif ev.kind == 'barrier':
                self._spawn_barrier()
            elif ev.kind == 'flag':
                self._spawn_flag()
            self.next_event_idx += 1

        # Проверка прохождения флага (победа)
        if not self.is_winner and self.race_controller.get_winner() is None:
            for flag in list(self.flag_sprites):
                if self.horse.passed_flag(flag):
                    self.race_controller.declare_winner(self)
                    self.is_winner = True
                    break

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
        sky_height = int((self.bottom_y - self.top_y) * SKY_PROPORTION)

        if sky_height > 0:
            self._draw_sky(surface, sky_height)

        ground_y = self.top_y + sky_height
        ground_height = self.bottom_y - ground_y
        if ground_height > 0:
            pygame.draw.rect(surface, GRASS_COLOR, (0, ground_y, self.screen_width, ground_height))

        self.grass_sprites.draw(surface)
        self.flag_sprites.draw(surface)
        self.horse.draw(surface)
        self.barrier_sprites.draw(surface)

        self._draw_progress_bar(surface)

        if self.is_winner:
            self._draw_win_message(surface)

    def _draw_sky(self, surface, sky_height):
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
        else:
            pygame.draw.rect(surface, SKY_COLOR, (0, self.top_y, self.screen_width, sky_height))

    def _draw_progress_bar(self, surface):
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

    def _draw_win_message(self, surface):
        font = pygame.font.SysFont(None, 250)
        text_surface = font.render("ПОБЕДА", True, (255, 255, 255))
        shadow_surface = font.render("ПОБЕДА", True, (0, 0, 0))
        center_x = self.screen_width // 2
        center_y = (self.top_y + self.bottom_y) // 2
        text_rect = text_surface.get_rect(center=(center_x, center_y))
        shadow_rect = shadow_surface.get_rect(center=(center_x + 2, center_y + 2))
        surface.blit(shadow_surface, shadow_rect)
        surface.blit(text_surface, text_rect)

    def _ensure_sky_scaled(self, sky_height):
        """Готовит масштабированную версию неба под фиксированную высоту sky_height,
        сохраняя соотношение сторон; ширина может быть больше экрана и будет обрезана при отрисовке."""
        if self.sky_bg is None:
            self._sky_bg_scaled = None
            return
        # Масштабируем по высоте, сохраняя аспект
        src_w = self.sky_bg.get_width()
        src_h = self.sky_bg.get_height()

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

    def _spawn_grass_from_frac(self, y_frac: float):
        y = int(self.top_y + y_frac * (self.bottom_y - self.top_y))
        x = self.screen_width + self.offscreen_margin if self.horse.facing_right else -self.offscreen_margin
        self.grass_sprites.add(Grass((x, y)))

    def _spawn_barrier(self):
        y = int(self.top_y + HORSE_SHADOW_MAX_Y_FRAC * (self.bottom_y - self.top_y))
        x = self.screen_width + self.offscreen_margin if self.horse.facing_right else -self.offscreen_margin
        self.barrier_sprites.add(Barrier((x, y)))

    def _spawn_flag(self):
        y = int(self.top_y + HORSE_SHADOW_MIN_Y_FRAC * (self.bottom_y - self.top_y))
        x = self.screen_width + self.offscreen_margin if self.horse.facing_right else -self.offscreen_margin
        self.flag_sprites.add(Flag((x, y)))

