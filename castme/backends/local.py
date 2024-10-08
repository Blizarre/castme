from io import BytesIO
from typing import List

import requests as r
from pygame.mixer import init as mixer_init
from pygame.mixer import music

from castme.player import Backend, NoSongsToPlayException
from castme.song import Song


def play_song(song: Song):
    response = r.get(song.url, timeout=10)
    response.raise_for_status()

    music.load(BytesIO(response.content))
    music.play()


class LocalBackend(Backend):
    def __init__(self, songs: List[Song]):
        mixer_init()
        self.songs = songs

    def play_next(self):
        if self.songs:
            play_song(self.songs.pop(0))
        else:
            raise NoSongsToPlayException()

    def playpause(self):
        if music.get_busy():
            music.pause()
        else:
            music.unpause()

    def volume_set(self, value):
        print("Not supported")

    def volume_delta(self, value):
        print("Not supported")

    def stop(self):
        music.stop()
