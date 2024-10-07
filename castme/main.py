import argparse
import cmd
from typing import List

from pychromecast import Chromecast, get_listed_chromecasts
from pychromecast.controllers.media import (
    MediaController,
    MediaStatus,
    MediaStatusListener,
)

from castme.config import Config
from castme.song import Song
from castme.subsonic import AlbumNotFoundException, SubSonic

SUBSONIC_APP_ID = "castme"


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


class CastMeCli(cmd.Cmd):
    prompt = ">> "  # Change the prompt text
    intro = "CastMe"

    def __init__(self, subsonic: SubSonic, chromecast: Chromecast, songs: List[Song]):
        super().__init__()
        self.subsonic = subsonic
        self.songs = songs
        self.chromecast = chromecast
        self.mediacontroller = chromecast.media_controller

    def do_queue(self, _line):
        """Print the play queue"""
        for idx, s in enumerate(self.songs):
            print(f"{idx:2} {s}")

    def do_list(self, _line):
        """List all the albums available"""
        for album in self.subsonic.get_all_albums():
            print(album)

    def default(self, line: str):
        print("Unknown command", line)

    def do_play(self, line: str):
        """play an album. The argument to that command will be matched against all
        albums on the device and the best matching one will be played/"""
        self.songs.clear()
        try:
            self.songs.extend(self.subsonic.get_songs_for_album(line))
            play_on_chromecast(self.songs.pop(0), self.mediacontroller)
        except AlbumNotFoundException as e:
            print(e)

    def do_playpause(self, _line):
        """play/pause the song"""
        if self.mediacontroller.is_paused:
            self.mediacontroller.play()
        else:
            self.mediacontroller.pause()

    def do_next(self, _line):
        """Skip to the next song"""
        play_on_chromecast(self.songs.pop(0), self.mediacontroller)

    def do_volume(self, line: str):
        """Set or change the volume. Valid values are between 0 and 100.
        +VALUE: Increase the volume by VALUE
        -VALUE: Decrease the volume by VALUE
        VALUE: Set the volume to VALUE
        """
        value = float(line) / 100.0
        if line.startswith("+"):
            self.chromecast.volume_up(value)
        elif line.startswith("-"):
            self.chromecast.volume_down(-value)
        else:
            self.chromecast.set_volume(value)

    def do_quit(self, _line):
        return True


def main():
    parser = argparse.ArgumentParser("CastMe")
    parser.add_argument("--config")
    args = parser.parse_args()
    config_path = args.config
    songs = []

    config = Config.load(config_path)
    subsonic = SubSonic(
        SUBSONIC_APP_ID, config.user, config.password, config.subsonic_server
    )

    print("Finding chromecast")
    cast = find_chromecast(config.chromecast_friendly_name)

    print("Waiting for cast to be ready")
    cast.wait()
    print("Chromecast ready")

    mc: MediaController = cast.media_controller
    mc.register_status_listener(MyChromecastListener(songs, mc))

    cli = CastMeCli(subsonic, cast, songs)
    cli.cmdloop()
