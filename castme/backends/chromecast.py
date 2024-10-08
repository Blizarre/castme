from typing import List

from pychromecast import Chromecast, get_listed_chromecasts
from pychromecast.controllers.media import (
    MediaController,
    MediaStatus,
    MediaStatusListener,
)

from castme.config import Config
from castme.player import Backend, NoSongsToPlayException
from castme.song import Song


class ChromecastBackend(Backend):
    def __init__(self, config: Config, songs: List[Song]):
        self.chromecast = find_chromecast(config.chromecast_friendly_name)
        self.songs = songs
        self.mediacontroller = self.chromecast.media_controller
        self.chromecast.wait()
        self.mediacontroller.register_status_listener(
            MyChromecastListener(songs, self.mediacontroller)
        )

    def play_next(self):
        if self.songs:
            play_on_chromecast(self.songs.pop(0), self.mediacontroller)
        else:
            raise NoSongsToPlayException()

    def playpause(self):
        if self.mediacontroller.status.player_is_playing:
            self.mediacontroller.pause()
        else:
            self.mediacontroller.play()

    def volume_set(self, value):
        self.chromecast.set_volume(value)

    def volume_delta(self, value):
        if value > 0:
            self.chromecast.volume_up(value)
        else:
            self.chromecast.volume_down(-value)

    def stop(self):
        self.chromecast.quit_app()


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
        # see https://developers.google.com/cast/docs/media/messages
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
