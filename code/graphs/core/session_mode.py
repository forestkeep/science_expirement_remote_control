from enum import Enum

class SessionMode(Enum):
    LIVE = "live"        # эксперимент идёт, данные в потоке
    REVIEW = "review"    # эксперимент остановлен или импортирован