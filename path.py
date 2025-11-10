import pygame

from constants import HORSE_OFFSET_X, HORSE_SHADOW_MAX_Y_FRAC, HORSE_SHADOW_MIN_Y_FRAC, HORSE_Y_FRAC, OFFSCREEN_MARGIN, SKY_COLOR, GRASS_COLOR, SKY_PROPORTION
from grass import Grass
from barrier import Barrier
from flag import Flag
from horse import Horse
from track_plan import TrackPlan


class Path:
    def __init__(self, top_y, bottom_y, screen_width, controls, race_controller, plan: TrackPlan):
        self.horse = Horse((HORSE_OFFSET_X, top_y + int(HORSE_Y_FRAC * (bottom_y - top_y))))
        self.screen_width = screen_width
        self.controls = controls
        self.race_controller = race_controller
        self.plan = plan
        # Словарь для хранения спрайтов по TrackEvent
        self._sprites_by_event = {}  # TrackEvent -> sprite
        self.grass_sprites = pygame.sprite.Group()
        self.barrier_sprites = pygame.sprite.Group()
        self.flag_sprites = pygame.sprite.Group()
        self.path_distance = plan.total_distance   
        self.traveled_distance = 0
        self.is_winner = False

        # Границы области для этой дорожки
        self.top_y = top_y
        self.bottom_y = bottom_y
        
        # Коэффициент для преобразования distance в пиксели экрана
        # Определяет, сколько единиц distance видно на экране
        self._view_distance_range = self.screen_width  # Примерно сколько единиц distance видно на экране
        self._pixels_per_distance = self.screen_width / self._view_distance_range if self._view_distance_range > 0 else 1.0

        self.sky_bg = pygame.image.load(self.plan.sky_background_path).convert()
        self._sky_bg_scaled = None

    def update(self, dt):
        speed = self.horse.get_speed()

        direction = -1 if self.horse.facing_right else 1
        base_dx = direction * speed * dt

        # Движение вправо увеличивает traveled_distance
        # traveled_distance -= base_dx означает:
        # если base_dx < 0 (движение вправо), то traveled_distance увеличивается
        # если base_dx > 0 (движение влево), то traveled_distance уменьшается
        self.traveled_distance -= base_dx

        sky_height = int((self.bottom_y - self.top_y) * SKY_PROPORTION)
        ground_y = self.top_y + sky_height
        horse_y = self.top_y + int((self.bottom_y - self.top_y) * HORSE_SHADOW_MAX_Y_FRAC)

        # Вычисляем видимые границы трассы и обновляем спрайты
        self._update_visible_sprites(ground_y, horse_y, dt)

        # Проверка коллизий с барьерами
        if self.horse.current_animation in ['trot', 'gallop'] or \
                self.horse.current_animation in ['barrier'] and self.horse.is_near_ground():
            collided = False
            for barrier in self.barrier_sprites:
                if self.horse.collide_barrier(barrier):
                    collided = True
            if collided:
                self.horse.make_fall()

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
            bar_margin_x = 0
            bar_margin_y = 0
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

    def _calculate_view_bounds(self):
        """Вычисляет видимые границы трассы на основе текущей позиции"""
        # traveled_distance увеличивается при движении вправо
        # Видимая область: события в диапазоне [traveled_distance - margin, traveled_distance + margin]
        # margin зависит от ширины экрана и коэффициента преобразования
        left_bound = self.traveled_distance - 2.5 * self._view_distance_range
        right_bound = self.traveled_distance + 2.5 * self._view_distance_range
                
        return left_bound, right_bound

    def _distance_to_screen_x(self, distance: float, y_pos: float, ground_y: float, horse_y: float):
        """Преобразует distance на трассе в позицию X на экране с учетом перспективы"""
        # Разница между distance события и текущей позицией
        distance_diff = distance - self.traveled_distance
        
        # Вычисляем фактор перспективы на основе Y позиции
        # Объекты ниже (ближе к земле) двигаются быстрее
        perspective_factor = (y_pos - ground_y) / (horse_y - ground_y)
        
        # Преобразуем distance_diff в пиксели с учетом перспективы
        # Если distance > traveled_distance, объект впереди (справа на экране)
        # Если distance < traveled_distance, объект позади (слева на экране)
        pixels_diff = distance_diff * self._pixels_per_distance * perspective_factor
        
        # Позиция на экране: лошадь в HORSE_OFFSET_X
        screen_x = HORSE_OFFSET_X + pixels_diff
        
        return screen_x

    def _update_visible_sprites(self, ground_y: float, horse_y: float, dt: float):
        """Обновляет спрайты на основе видимых границ трассы"""
        # Вычисляем видимые границы
        left_bound, right_bound = self._calculate_view_bounds()
        
        # Находим события, которые должны быть видны
        visible_events = set()
        for event in self.plan.events:
            if left_bound <= event.distance <= right_bound:
                visible_events.add(event)
                
                # Создаем или обновляем спрайт для видимого события
                if event not in self._sprites_by_event:
                    self._create_sprite_for_event(event, ground_y, horse_y)
                else:
                    self._update_sprite_position(event, ground_y, horse_y, dt)
        
        # Удаляем спрайты для невидимых событий
        events_to_remove = []
        for event, sprite in self._sprites_by_event.items():
            if event not in visible_events:
                events_to_remove.append(event)
        
        for event in events_to_remove:
            self._remove_sprite_for_event(event)

    def _create_sprite_for_event(self, event, ground_y: float, horse_y: float):
        """Создает спрайт для события"""
        if event.kind == 'grass':
            y = int(self.top_y + event.y_frac * (self.bottom_y - self.top_y))
            x = self._distance_to_screen_x(event.distance, y, ground_y, horse_y)
            sprite = Grass((x, y))
            self._sprites_by_event[event] = sprite
            self.grass_sprites.add(sprite)
        elif event.kind == 'barrier':
            y = int(self.top_y + HORSE_SHADOW_MAX_Y_FRAC * (self.bottom_y - self.top_y))
            x = self._distance_to_screen_x(event.distance, y, ground_y, horse_y)
            sprite = Barrier((x, y))
            self._sprites_by_event[event] = sprite
            self.barrier_sprites.add(sprite)
        elif event.kind == 'flag':
            y = int(self.top_y + HORSE_SHADOW_MIN_Y_FRAC * (self.bottom_y - self.top_y))
            x = self._distance_to_screen_x(event.distance, y, ground_y, horse_y)
            sprite = Flag((x, y))
            self._sprites_by_event[event] = sprite
            self.flag_sprites.add(sprite)

    def _update_sprite_position(self, event, ground_y: float, horse_y: float, dt: float):
        """Обновляет позицию спрайта на основе distance события"""
        sprite = self._sprites_by_event[event]
        
        # Обновляем анимацию для флагов
        if event.kind == 'flag':
            sprite.update(dt)
        
        # Вычисляем новую позицию
        if event.kind == 'grass':
            y = int(self.top_y + event.y_frac * (self.bottom_y - self.top_y))
        elif event.kind == 'barrier':
            y = int(self.top_y + HORSE_SHADOW_MAX_Y_FRAC * (self.bottom_y - self.top_y))
        else:  # flag
            y = int(self.top_y + HORSE_SHADOW_MIN_Y_FRAC * (self.bottom_y - self.top_y))
        
        x = self._distance_to_screen_x(event.distance, y, ground_y, horse_y)
        sprite.rect.x = round(x)
        sprite.rect.bottom = y

    def _remove_sprite_for_event(self, event):
        """Удаляет спрайт для события"""
        sprite = self._sprites_by_event.pop(event)
        if event.kind == 'grass':
            self.grass_sprites.remove(sprite)
        elif event.kind == 'barrier':
            self.barrier_sprites.remove(sprite)
        elif event.kind == 'flag':
            self.flag_sprites.remove(sprite)

