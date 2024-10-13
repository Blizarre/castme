from abc import abstractmethod


class NoSongsToPlayException(Exception):
    pass


class Backend:
    @abstractmethod
    def force_play(self):
        pass

    @abstractmethod
    def playpause(self):
        pass

    @abstractmethod
    def volume_set(self, value: float):
        """Set volume, between 0 and 1.0"""

    @abstractmethod
    def volume_delta(self, value: float):
        """add value to the volume, between 0 and 1.0"""

    @abstractmethod
    def stop(self):
        pass