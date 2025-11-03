import os
import glob
import random
import pygame


class Barrier(pygame.sprite.Sprite):
    def __init__(self, position):
        super().__init__()
        image_path = self._choose_random_image()
        self.image = self._load_image_with_alpha(image_path)
        self.rect = self.image.get_rect(bottomleft=position)

    def _choose_random_image(self):
        folder = os.path.join('assets', 'barrier')
        candidates = sorted(glob.glob(os.path.join(folder, '*.png')))
        if not candidates:
            return None
        return random.choice(candidates)

    def _load_image_with_alpha(self, image_path):
        if image_path and os.path.exists(image_path):
            try:
                image = pygame.image.load(image_path)
                return image.convert_alpha()
            except pygame.error as e:
                print(f"Error loading barrier image {image_path}: {e}")
        # Fallback simple placeholder
        placeholder = pygame.Surface((32, 32), pygame.SRCALPHA)
        pygame.draw.rect(placeholder, (200, 60, 60), placeholder.get_rect(), 2)
        return placeholder


