import random
import pygame

from constants import SCREEN_WIDTH, SCREEN_HEIGHT
from grass import Grass


class Path:
    def __init__(self, horse):
        self.horse = horse
        self.grass_sprites = pygame.sprite.Group()
        self.spawn_timer = 0.0
        self.next_spawn = 0.0
        self._schedule_next_spawn(0)

        # Вертикальная полоса для травы (у земли)
        self.min_y = int(SCREEN_HEIGHT * 0.65)
        self.max_y = int(SCREEN_HEIGHT * 0.9)

        # Отступы за пределы экрана для спауна/очистки
        self.offscreen_margin = 64

    def update(self, dt):
        speed = self._get_background_speed()
        if speed != 0:
            direction = -1 if self.horse.facing_right else 1
            dx = int(direction * speed * dt)
        else:
            dx = 0

        # Двигаем траву
        for sprite in list(self.grass_sprites):
            sprite.rect.x += dx
            if sprite.rect.right < -self.offscreen_margin or sprite.rect.left > SCREEN_WIDTH + self.offscreen_margin:
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
            x = SCREEN_WIDTH + self.offscreen_margin
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
            return 40
        # idle и прочее — фон не движется
        return 0


