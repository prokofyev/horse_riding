import pygame

from pygame_animation import AnimationManager


class Flag(pygame.sprite.Sprite):
    def __init__(self, position):
        super().__init__()
        # Анимация флага
        self.animation = AnimationManager.load_animation('assets/flag', fps=12, loop=True)
        # Позиционируем по нижнему левому углу, чтобы стоял на земле
        first_frame = self.animation.get_current_frame()
        self.image = first_frame
        self.rect = self.image.get_rect(bottomleft=position)
        self.pos_x = float(self.rect.x)
        # Запускаем анимацию
        self.animation.play()

    def update(self, dt):
        self.animation.update(dt)
        self.image = self.animation.get_current_frame()


