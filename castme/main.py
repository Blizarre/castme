import argparse
import cmd
from typing import List

from pychromecast import Chromecast
from pychromecast.controllers.media import MediaController

from castme.chromecast import MyChromecastListener, find_chromecast, play_on_chromecast
from castme.config import Config
from castme.song import Song
from castme.subsonic import AlbumNotFoundException, SubSonic

SUBSONIC_APP_ID = "castme"


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
            print(f"{1 + idx:2} {s}")

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
