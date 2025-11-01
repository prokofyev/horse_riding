import pygame

from horse import Horse
from path import Path
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
        
        # Верхняя дорожка и лошадь
        horse = Horse((100, mid_y // 2 - HORSE_OFFSET))
        self.path1 = Path(horse, top_y=0, bottom_y=mid_y, screen_width=self.screen_width)
        
        # Нижняя дорожка и лошадь
        horse = Horse((100, mid_y + mid_y // 2 - HORSE_OFFSET))
        self.path2 = Path(horse, top_y=mid_y, bottom_y=self.screen_height, screen_width=self.screen_width)

        # Для передачи delta time
        self.dt = 0
    
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
                    # Управление первой лошадью (стрелки)
                    if event.key == pygame.K_RIGHT:
                        if self.path1.horse.facing_right:
                            self.path1.horse.accelerate()
                        else:
                            self.path1.horse.decelerate()
                    if event.key == pygame.K_LEFT:
                        if self.path1.horse.facing_right:
                            self.path1.horse.decelerate()
                        else:
                            self.path1.horse.accelerate()
                    if event.key == pygame.K_UP:
                        self.path1.horse.barrier()
                    
                    # Управление второй лошадью (WASD)
                    if event.key == pygame.K_d:
                        if self.path2.horse.facing_right:
                            self.path2.horse.accelerate()
                        else:
                            self.path2.horse.decelerate()
                    if event.key == pygame.K_a:
                        if self.path2.horse.facing_right:
                            self.path2.horse.decelerate()
                        else:
                            self.path2.horse.accelerate()
                    if event.key == pygame.K_w:
                        self.path2.horse.barrier()
            
            # Обработка непрерывного ввода
            # keys = pygame.key.get_pressed()
            # if keys[pygame.K_RIGHT]:
            #     self.horse.set_animation('start')
            
            # Обновление с передачей delta time
            self.path1.update(self.dt)
            self.path2.update(self.dt)
            
            # Отрисовка
            self.screen.fill(GRASS_COLOR)
            # Рисуем обе дорожки
            self.path1.draw(self.screen)
            self.path2.draw(self.screen)
            
            # Рисуем разделительную линию между дорожками
            mid_y = self.screen_height // 2
            pygame.draw.line(self.screen, (100, 100, 100), (0, mid_y), (self.screen_width, mid_y), 3)
            
            pygame.display.flip()

if __name__ == "__main__":
    game = Game()
    game.run()