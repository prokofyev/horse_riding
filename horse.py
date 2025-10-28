import pygame
import random
import time
from pygame_animation import Animation, AnimationManager
from constants import IDLE_RANDOM_MIN_INTERVAL, IDLE_RANDOM_MAX_INTERVAL


class Horse(pygame.sprite.Sprite):
    def __init__(self, position):
        super().__init__()
        
        # Загрузка анимаций через AnimationManager
        self.animations = {
            'idle': AnimationManager.load_animation('assets/horse/idle', fps=8, loop=True),
            'idle2': AnimationManager.load_animation('assets/horse/idle2', fps=8, loop=False),
            'idle3': AnimationManager.load_animation('assets/horse/idle3', fps=8, loop=False),
            'start_moving': AnimationManager.load_animation('assets/horse/start_moving', fps=8, loop=False),
            'stop_moving': AnimationManager.load_animation('assets/horse/stop_moving', fps=8, loop=False),
            'walk': AnimationManager.load_animation('assets/horse/walk', fps=10, loop=True),
            'trot': AnimationManager.load_animation('assets/horse/trot', fps=12, loop=True),
            'gallop': AnimationManager.load_animation('assets/horse/gallop', fps=20, loop=True),
            'barrier': AnimationManager.load_animation('assets/horse/barrier', fps=20, loop=False),
        }
        
        self.current_animation = 'idle'
        self.image = self.animations[self.current_animation].get_current_frame()
        self.rect = self.image.get_rect(topleft=position)
        
        # Переменные для случайной смены idle анимации
        self.idle_start_time = time.time()
        self.next_idle_change_time = self._get_next_idle_change_time()
        
        # Очередь для последующего переключения анимации
        self.queued_animation = None
        
        # Автоматический запуск анимации
        self.animations[self.current_animation].play()
    
    def update(self, dt):
        # Обновляем текущую анимацию (dt - delta time)
        self.animations[self.current_animation].update(dt)
        self.image = self.animations[self.current_animation].get_current_frame()
        
        # Если играется переходная анимация, проверяем завершение и выполняем запланированное переключение
        if self.animations[self.current_animation].is_finished:
            if self.queued_animation:
                next_anim = self.queued_animation
                self.queued_animation = None
                self.set_animation(next_anim)
            else:
                self.set_animation('idle')
        
        # Проверяем случайную смену idle анимации
        self._check_idle_random_change()
    
    def set_animation(self, animation_name):
        if animation_name in self.animations and animation_name != self.current_animation:
            # Останавливаем текущую анимацию
            self.animations[self.current_animation].stop()
            
            # Переключаем на новую
            self.current_animation = animation_name
            self.animations[self.current_animation].reset()
            self.animations[self.current_animation].play()
            
            # Если переключаемся на idle, сбрасываем таймер случайной смены
            if animation_name == 'idle':
                self.idle_start_time = time.time()
                self.next_idle_change_time = self._get_next_idle_change_time()
    
    def _get_next_idle_change_time(self):
        """Генерирует случайное время для следующей смены idle анимации"""
        return random.uniform(IDLE_RANDOM_MIN_INTERVAL, IDLE_RANDOM_MAX_INTERVAL)
    
    def _check_idle_random_change(self):
        """Проверяет, нужно ли сменить idle анимацию на idle2 или idle3"""
        if self.current_animation == 'idle':
            current_time = time.time()
            elapsed_time = current_time - self.idle_start_time
            
            if elapsed_time >= self.next_idle_change_time:
                # Случайно выбираем между idle2 и idle3
                random_animation = random.choice(['idle2', 'idle3'])
                self.set_animation(random_animation)
                
                # Сбрасываем таймер для следующей смены
                self.idle_start_time = current_time
                self.next_idle_change_time = self._get_next_idle_change_time()
        
        # Если текущая анимация idle2 или idle3 закончилась, возвращаемся к idle
        elif self.current_animation in ['idle2', 'idle3']:
            if self.animations[self.current_animation].is_finished:
                self.set_animation('idle')

    def accelerate(self):
        if self.current_animation in ['idle', 'idle2', 'idle3']:
            self.queued_animation = 'walk'
            self.set_animation('start_moving')
        elif self.current_animation in ['walk']:
            self.set_animation('trot')  
        elif self.current_animation in ['trot']:
            self.set_animation('gallop')

    def decelerate(self):
        if self.current_animation in ['walk']:
            self.queued_animation = 'idle'
            self.set_animation('stop_moving')
        elif self.current_animation in ['trot']:
            self.set_animation('walk')
        elif self.current_animation in ['gallop']:
            self.set_animation('trot')

    def barrier(self):
        if self.current_animation in ['gallop', 'trot', 'walk']:
            self.queued_animation = self.current_animation
            self.set_animation('barrier')