import pygame
import os
import glob


class Animation:
    def __init__(self, frames, fps=8, loop=True):
        self.frames = frames
        self.fps = fps
        self.loop = loop
        self.current_frame = 0
        self.frame_time = 0
        self.frame_duration = 1.0 / fps
        self.is_playing = False
        self.is_finished = False
    
    def play(self):
        self.is_playing = True
        self.is_finished = False
    
    def stop(self):
        self.is_playing = False
    
    def reset(self):
        self.current_frame = 0
        self.frame_time = 0
        self.is_finished = False
    
    def update(self, dt):
        if not self.is_playing:
            return
        
        self.frame_time += dt
        
        if self.frame_time >= self.frame_duration:
            self.frame_time = 0
            self.current_frame += 1
            
            if self.current_frame >= len(self.frames):
                if self.loop:
                    self.current_frame = 0
                else:
                    self.current_frame = len(self.frames) - 1
                    self.is_finished = True
                    self.is_playing = False
    
    def get_current_frame(self):
        if not self.frames:
            return None
        return self.frames[self.current_frame]


class AnimationManager:
    @staticmethod
    def load_animation(folder_path, fps=8, loop=True):
        """Load animation frames from a folder"""
        frames = []
        
        # Get all PNG files in the folder
        pattern = os.path.join(folder_path, "*.png")
        image_files = sorted(glob.glob(pattern))
        
        for image_file in image_files:
            try:
                image = pygame.image.load(image_file)
                # Convert to display format for better performance
                image = image.convert_alpha()
                frames.append(image)
            except pygame.error as e:
                print(f"Error loading image {image_file}: {e}")
        
        if not frames:
            print(f"Warning: No frames found in {folder_path}")
            # Create a placeholder surface
            placeholder = pygame.Surface((32, 32), pygame.SRCALPHA)
            pygame.draw.rect(placeholder, (255, 0, 0), (0, 0, 32, 32))
            frames = [placeholder]
        
        return Animation(frames, fps, loop)
