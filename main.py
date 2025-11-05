import pygame
import time

from horse import Horse
from path import Path
from controls import Controls
from constants import FPS, GRASS_COLOR, HORSE_OFFSET


class Game:
    def __init__(self):
        pygame.init()
        # Получаем размеры экрана для полноэкранного режима
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        self.screen_width = self.screen.get_width()
        self.screen_height = self.screen.get_height()
        self.clock = pygame.time.Clock()
        
        # Разделяем экран горизонтально пополам
        mid_y = self.screen_height // 2
        
        # Создаем объекты управления для лошадей
        self.controls1 = Controls(
            left=pygame.K_LEFT,
            right=pygame.K_RIGHT,
            jump=pygame.K_UP
        )
        self.controls2 = Controls(
            left=pygame.K_a,
            right=pygame.K_d,
            jump=pygame.K_w
        )
        
        self._winner_path = None
        self._winner_time = None
        def get_winner():
            return self._winner_path
        def set_winner(path):
            if self._winner_path is None:
                self._winner_path = path
                self._winner_time = time.time()
        
        # Верхняя дорожка и лошадь
        horse = Horse((100, mid_y // 2 - HORSE_OFFSET))
        self.path1 = Path(horse, top_y=0, bottom_y=mid_y, screen_width=self.screen_width, controls=self.controls1, 
            get_winner=get_winner, set_winner=set_winner)
        
        # Нижняя дорожка и лошадь
        horse = Horse((100, mid_y + mid_y // 2 - HORSE_OFFSET))
        self.path2 = Path(horse, top_y=mid_y, bottom_y=self.screen_height, screen_width=self.screen_width, controls=self.controls2, 
            get_winner=get_winner, set_winner=set_winner)

        # Для передачи delta time
        self.dt = 0
        
        # Стартовый обратный отсчет
        self.countdown_active = False
        self.countdown_start_time = None
        self._start_countdown()
    
    def run(self):
        running = True
        while running:
            # Расчет delta time
            self.dt = self.clock.tick(FPS) / 1000.0  # в секундах
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    # Выход из полноэкранного режима по ESC
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    # Передаем события в Path для обработки
                    self.path1.handle_event(event)
                    self.path2.handle_event(event)
            
            # Во время обратного отсчета не обновляем физику/анимацию дорожек
            if not self.countdown_active:
                # Обновление с передачей delta time
                self.path1.update(self.dt)
                self.path2.update(self.dt)
            
            # Отрисовка (фон рисуют сами Path: небо и почву)
            self.screen.fill((0, 0, 0))
            # Рисуем обе дорожки
            self.path1.draw(self.screen)
            self.path2.draw(self.screen)
            
            # Рисуем разделительную линию между дорожками
            mid_y = self.screen_height // 2
            pygame.draw.line(self.screen, (100, 100, 100), (0, mid_y), (self.screen_width, mid_y), 3)
            
            # Рисуем оверлей обратного отсчета, если активен
            if self.countdown_active:
                self._draw_countdown_overlay()
            pygame.display.flip()

            # Автоматический рестарт через 10 секунд после победы
            if self._winner_path is not None and self._winner_time is not None:
                if time.time() - self._winner_time >= 10.0:
                    self._reset_game()

            # Проверяем завершение обратного отсчета
            if self.countdown_active and self.countdown_start_time is not None:
                elapsed = time.time() - self.countdown_start_time
                if elapsed >= 4.0:
                    # 3,2,1,СТАРТ по 1с каждый
                    self.countdown_active = False

    def _reset_game(self):
        # Сбрасываем победителя
        self._winner_path = None
        self._winner_time = None
        
        # Пересоздаем дорожки и лошадей
        mid_y = self.screen_height // 2
        horse = Horse((100, mid_y // 2 - HORSE_OFFSET))
        self.path1 = Path(horse, top_y=0, bottom_y=mid_y, screen_width=self.screen_width, controls=self.controls1, 
            get_winner=lambda: self._winner_path, set_winner=lambda p: self._set_winner(p))
        horse = Horse((100, mid_y + mid_y // 2 - HORSE_OFFSET))
        self.path2 = Path(horse, top_y=mid_y, bottom_y=self.screen_height, screen_width=self.screen_width, controls=self.controls2, 
            get_winner=lambda: self._winner_path, set_winner=lambda p: self._set_winner(p))
        
        # Новый обратный отсчет
        self._start_countdown()

    def _set_winner(self, path):
        if self._winner_path is None:
            self._winner_path = path
            self._winner_time = time.time()

    def _start_countdown(self):
        self.countdown_active = True
        self.countdown_start_time = time.time()

    def _draw_countdown_overlay(self):
        elapsed = time.time() - self.countdown_start_time if self.countdown_start_time else 0
        # 0-1: '3', 1-2: '2', 2-3: '1', 3-4: 'СТАРТ'
        if elapsed < 1.0:
            text = "3"
        elif elapsed < 2.0:
            text = "2"
        elif elapsed < 3.0:
            text = "1"
        elif elapsed < 4.0:
            text = "СТАРТ"
        else:
            text = ""
        
        if text:
            # Полупрозрачный черный фон на весь экран
            overlay = pygame.Surface((self.screen_width, self.screen_height))
            overlay.set_alpha(180)
            overlay.fill((0, 0, 0))
            self.screen.blit(overlay, (0, 0))
            
            # Большой шрифт, центр экрана
            base_size = int(min(self.screen_width, self.screen_height) * (0.4 if text != 'СТАРТ' else 0.25))
            font = pygame.font.SysFont(None, base_size)
            text_surface = font.render(text, True, (255, 255, 255))
            shadow_surface = font.render(text, True, (0, 0, 0))
            rect = text_surface.get_rect(center=(self.screen_width // 2, self.screen_height // 2))
            shadow_rect = shadow_surface.get_rect(center=(self.screen_width // 2 + 6, self.screen_height // 2 + 6))
            self.screen.blit(shadow_surface, shadow_rect)
            self.screen.blit(text_surface, rect)

if __name__ == "__main__":
    game = Game()
    game.run()