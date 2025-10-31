import pygame

from horse import Horse
from path import Path
from constants import SCREEN_WIDTH, SCREEN_HEIGHT, FPS


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        
        # Создание игрока
        self.horse = Horse((100, 100))
        self.path = Path(self.horse)

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
                    if event.key == pygame.K_RIGHT:
                        if self.horse.facing_right:
                            self.horse.accelerate()
                        else:
                            self.horse.decelerate()
                    if event.key == pygame.K_LEFT:
                        if self.horse.facing_right:
                            self.horse.decelerate()
                        else:
                            self.horse.accelerate()
                    if event.key == pygame.K_UP:
                        self.horse.barrier()
            
            # Обработка непрерывного ввода
            # keys = pygame.key.get_pressed()
            # if keys[pygame.K_RIGHT]:
            #     self.horse.set_animation('start')
            
            # Обновление с передачей delta time
            self.path.update(self.dt)
            
            # Отрисовка
            self.screen.fill((149, 178, 98))
            # Сначала рисуем дорожку (траву), затем лошадь
            self.path.draw(self.screen)
            pygame.display.flip()

if __name__ == "__main__":
    game = Game()
    game.run()