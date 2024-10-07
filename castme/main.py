import argparse
import cmd
from shutil import get_terminal_size
from typing import List

from pychromecast import Chromecast
from pychromecast.controllers.media import MediaController

from castme.chromecast import MyChromecastListener, find_chromecast, play_on_chromecast
from castme.config import Config
from castme.song import Song
from castme.subsonic import AlbumNotFoundException, SubSonic

from importlib.metadata import PackageNotFoundError, version


def castme_version():
    try:
        return version("castme")
    except PackageNotFoundError:
        return "unknown"


SUBSONIC_APP_ID = "castme"


class CastMeCli(cmd.Cmd):
    prompt = ">> "  # Change the prompt text

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
        cols, _lines = get_terminal_size()
        print(cols)
        self.columnize(self.subsonic.get_all_albums(), displaywidth=cols)

    def emptyline(self):
        pass

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
        """Exit the application"""
        self.chromecast.quit_app()
        self.chromecast.disconnect()
        return True

    def do_EOF(self, line: str):
        return self.do_quit(line)


def main():
    parser = argparse.ArgumentParser("CastMe")
    parser.add_argument("--config", help="Set the configuration file to use")
    parser.add_argument("--version", action="store_true", help="Print version and exit")
    args = parser.parse_args()
    config_path = args.config

    if args.version:
        print("Version: ", castme_version())
        return

    config = Config.load(config_path)
    subsonic = SubSonic(
        SUBSONIC_APP_ID, config.user, config.password, config.subsonic_server
    )

    songs = []

    print("looking for chromecast", config.chromecast_friendly_name)
    cast = find_chromecast(config.chromecast_friendly_name)
    cast.wait()
    print("Chromecast ready")

    mc: MediaController = cast.media_controller
    mc.register_status_listener(MyChromecastListener(songs, mc))

    cli = CastMeCli(subsonic, cast, songs)
    cli.cmdloop()


if __name__ == "__main__":
    main()
