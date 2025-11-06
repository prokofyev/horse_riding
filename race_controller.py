import time


class RaceController:
    def __init__(self):
        self._winner_path = None
        self._winner_time = None

    def get_winner(self):
        return self._winner_path

    def declare_winner(self, path):
        if self._winner_path is None:
            self._winner_path = path
            self._winner_time = time.time()

    def should_auto_restart(self, seconds: float) -> bool:
        return self._winner_time is not None and (time.time() - self._winner_time) >= seconds


