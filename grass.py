import os
import glob
import random
import pygame


class Grass(pygame.sprite.Sprite):
    def __init__(self, position):
        super().__init__()
        
        image_path = self._choose_random_grass_image()
        self.image = self._load_image_with_alpha(image_path)
        self.rect = self.image.get_rect(topleft=position)

    def _choose_random_grass_image(self):
        folder = os.path.join('assets', 'grass')
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
                print(f"Error loading grass image {image_path}: {e}")
        # Fallback: tiny transparent placeholder with a small green dot
        placeholder = pygame.Surface((16, 16), pygame.SRCALPHA)
        pygame.draw.circle(placeholder, (34, 139, 34), (8, 8), 5)
        return placeholder


