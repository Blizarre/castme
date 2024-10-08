from abc import abstractmethod


class NoSongsToPlayException(BaseException):
    pass


class Backend:
    @abstractmethod
    def play_next(self):
        pass

    @abstractmethod
    def playpause(self):
        pass

    @abstractmethod
    def volume_set(self, value: float):
        """Set volume, between 0 and 1.0"""

    @abstractmethod
    def volume_delta(self, value):
        pass

    @abstractmethod
    def stop(self):
        pass
