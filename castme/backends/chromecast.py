from contextlib import contextmanager
from typing import Generator, List

from pychromecast import Chromecast, get_listed_chromecasts  # type: ignore
from pychromecast.controllers.media import (  # type: ignore
    MediaController,
    MediaStatus,
    MediaStatusListener,
)

from castme.config import Config
from castme.messages import debug as msg_debug
from castme.messages import error
from castme.player import Backend, NoSongsToPlayException
from castme.song import Song


def debug(msg):
    msg_debug("chromecast", msg)


class ChromecastBackend(Backend):
    def __init__(self, config: Config, songs: List[Song]):
        self.chromecast_friendly_name = config.chromecast_friendly_name
        self.songs = songs
        self.chromecast = find_chromecast(self.chromecast_friendly_name)
        self.mediacontroller = self.chromecast.media_controller
        self.chromecast.wait()
        self.mediacontroller.register_status_listener(
            MyChromecastListener(songs, self.mediacontroller)
        )

    def force_play(self):
        debug("Force play")
        if self.songs:
            play_on_chromecast(self.songs[0], self.mediacontroller)
        else:
            raise NoSongsToPlayException()

    def playpause(self):
        debug("playpause")
        if self.mediacontroller.status.player_is_paused:
            self.mediacontroller.play()
        elif self.mediacontroller.status.player_is_idle:
            self.force_play()
        elif self.mediacontroller.status.player_is_playing:
            self.mediacontroller.pause()

    def volume_set(self, value):
        debug(f"volume set {value}")
        self.chromecast.set_volume(value)

    def volume_delta(self, value):
        debug(f"volume delta {value}")
        if value > 0:
            self.chromecast.volume_up(value)
        else:
            self.chromecast.volume_down(-value)

    def stop(self):
        debug("stop")
        self.mediacontroller.stop()

    def close(self):
        debug("close")
        self.stop()


class ChromecastNotFoundException(Exception):
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
                self.songs.pop(0)
            if self.songs:
                play_on_chromecast(self.songs[0], self.media_controller)

    def load_media_failed(self, item: int, error_code: int):
        """Called when load media failed."""
        error(f"Error loading media, error code: {error_code}")


def find_chromecast(label) -> Chromecast:
    chromecasts, _ = get_listed_chromecasts(friendly_names=[label])
    if not chromecasts:
        raise ChromecastNotFoundException(label)

    return chromecasts[0]


def play_on_chromecast(song: Song, controller: MediaController):
    metadata = dict(
        # 3 is the magic number for MusicTrackMediaMetadata
        # see https://developers.google.com/cast/docs/media/messages
        metadataType=3,
        albumName=song.album_name,
        title=song.title,
        artist=song.artist,
    )
    debug(f"Playing {song.title} @ {song.url}")
    controller.play_media(
        song.url,
        content_type=song.content_type,
        title=song.title,
        media_info=metadata,
        thumb=song.album_art,
    )


@contextmanager
def backend(config: Config, songs: List[Song]) -> Generator[Backend, None, None]:
    chromecast = ChromecastBackend(config, songs)
    try:
        yield chromecast
    finally:
        chromecast.close()
