from typing import List

from pychromecast import Chromecast, get_listed_chromecasts
from pychromecast.controllers.media import (
    MediaController,
    MediaStatus,
    MediaStatusListener,
)

from castme.song import Song


class ChromecastNotFoundException(BaseException):
    def __init__(self, keyword):
        self.keyword = keyword

    def __str__(self):
        return f"Chromecast named {self.keyword} not found"


class MyChromecastListener(MediaStatusListener):
    def __init__(self, songs: List[Song], media_controller: MediaController):
        self.songs = songs
        self.media_controller = media_controller

    def new_media_status(self, status: MediaStatus):
        if status.player_is_idle and status.idle_reason == "FINISHED":
            if self.songs:
                play_on_chromecast(self.songs.pop(0), self.media_controller)

    def load_media_failed(self, item: int, error_code: int):
        """Called when load media failed."""
        print("BOOH", item, error_code)


def find_chromecast(label) -> Chromecast:
    chromecasts, _ = get_listed_chromecasts(friendly_names=[label])
    if not chromecasts:
        raise ChromecastNotFoundException(label)

    return chromecasts[0]


def play_on_chromecast(song: Song, controller: MediaController):
    print("Playing song", song)
    metadata = dict(
        # 3 is the magic number for MusicTrackMediaMetadata
        metadataType=3,
        albumName=song.album_name,
        title=song.title,
        artist=song.artist,
    )
    controller.play_media(
        song.url,
        content_type=song.content_type,
        title=song.title,
        media_info=metadata,
        thumb=song.album_art,
    )
