from abc import abstractmethod


class NoSongsToPlayException(Exception):
    pass


class Backend:
    @abstractmethod
    def force_play(self):
        """Force playing the first song in the queue"""

    @abstractmethod
    def rewind(self):
        """Rewind the current song"""

    @abstractmethod
    def playpause(self):
        """Play or pause the music"""

    @abstractmethod
    def volume_set(self, value: float):
        """Set volume, between 0 and 1.0"""

    @abstractmethod
    def volume_delta(self, value: float):
        """add value to the volume, between 0 and 1.0"""

    @abstractmethod
    def stop(self):
        """Stop the music, regardless of its current status"""
