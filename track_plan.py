import os
import glob
from dataclasses import dataclass
import random

from constants import GRASS_MAX_Y_FRAC, GRASS_MIN_Y_FRAC, HORSE_SHADOW_MAX_Y_FRAC, HORSE_SHADOW_MIN_Y_FRAC


@dataclass
class TrackEvent:
    kind: str  # 'grass' | 'barrier' | 'flag'
    distance: float
    y_frac: float  # 0..1 within path ground band


class TrackPlan:
    def __init__(self, sky_background_path, events, total_distance):
        self.sky_background_path = sky_background_path  # str | None
        # events must be sorted by distance
        self.events = events
        self.total_distance = total_distance

    @staticmethod
    def generate(total_distance: float,
                 min_grass_spacing: float,
                 max_grass_spacing: float,
                 min_barrier_spacing: float,
                 max_barrier_spacing: float):
        bg_path = TrackPlan._load_sky_background()

        events = []

        # Grass events
        d = 0.0
        while d < total_distance:
            d += random.uniform(min_grass_spacing, max_grass_spacing)
            if d >= total_distance:
                break
            y_frac = random.uniform(GRASS_MIN_Y_FRAC, GRASS_MAX_Y_FRAC)
            while y_frac > HORSE_SHADOW_MIN_Y_FRAC and y_frac < HORSE_SHADOW_MAX_Y_FRAC:
                y_frac = random.uniform(GRASS_MIN_Y_FRAC, GRASS_MAX_Y_FRAC)
            events.append(TrackEvent('grass', d, y_frac))

        # Barrier events
        d = 0.0
        while d < total_distance:
            d += random.uniform(min_barrier_spacing, max_barrier_spacing)
            if d >= total_distance:
                break
            events.append(TrackEvent('barrier', d, None))

        events.append(TrackEvent('flag', total_distance, None))

        # Sort events by distance
        events.sort(key=lambda e: e.distance)
        return TrackPlan(bg_path, events, total_distance)

    def _load_sky_background():
        """Загружает случайное изображение неба из assets/backgrounds."""
        try:
            folder = os.path.join('assets', 'backgrounds')
            candidates = sorted(glob.glob(os.path.join(folder, '*.png')))
            if not candidates:
                return None
            path = random.choice(candidates)
            return path
        except Exception as e:
            print(f"Error loading sky background: {e}")
            return None
