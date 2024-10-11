import argparse
import cmd
import os
import shutil
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from shutil import get_terminal_size
from sys import exit as sys_exit
from typing import Dict, List

from castme.backends.chromecast import backend as chromecast_backend
from castme.backends.local import backend as local_backend
from castme.config import Config
from castme.player import Backend, NoSongsToPlayException
from castme.song import Song
from castme.subsonic import AlbumNotFoundException, SubSonic


class InvalidBackend(BaseException):
    def __init__(self, invalid_backend_name: str):
        self.invalid_name = invalid_backend_name

    def __str__(self):
        return f"Invalid backend name {self.invalid_name}"


def castme_version():
    try:
        return version("castme")
    except PackageNotFoundError:
        return "unknown"


SUBSONIC_APP_ID = "castme"


class CastMeCli(cmd.Cmd):
    prompt = ">> "  # Change the prompt text

    def __init__(
        self,
        subsonic: SubSonic,
        targets: Dict[str, Backend],
        default_backend: str,
        songs: List[Song],
    ):
        super().__init__()
        self.subsonic = subsonic
        self.songs = songs
        self.targets = targets
        if default_backend not in targets:
            raise InvalidBackend(default_backend)

        self.current_target = targets[default_backend]
        print("Currently playing on", default_backend)

    def do_list(self, _line):
        """List all the albums available (alias: l)"""
        cols, _lines = get_terminal_size()
        print(cols)
        self.columnize(self.subsonic.get_all_albums(), displaywidth=cols)

    def emptyline(self):
        pass

    def do_switch(self, line):
        """Switch to another backend. Without argument list the available
        backends. (alias: s)"""
        if not line:
            print(f"Available targets: {", ".join(self.targets.keys())}")
            return

        self.current_target.stop()
        if line in self.targets:
            self.current_target = self.targets[line]
            if self.songs:
                self.current_target.force_play()

            print(f"Switch done to {line}")
        else:
            print(f"Could not find target {line}")

    def do_clear(self, line: str):
        """Clear the queue and stop the music (alias: c)"""
        self.songs.clear()
        self.current_target.stop()

    def do_queue(self, line: str):
        """Queue an album. The argument to that command will be matched against all
        albums on the device and the best matching one will be played (alias: q).
        """
        if not line:
            for idx, s in enumerate(self.songs):
                print(f"{1 + idx:2} {s}")
            return
        try:
            name, songs = self.subsonic.get_songs_for_album(line)
            print("Queueing", name)
            self.songs.extend(songs)
        except AlbumNotFoundException as e:
            print(e)

    def do_playpause(self, _line):
        """play/pause the song (alias: pp)"""
        self.current_target.playpause()

    def do_next(self, _line):
        """Skip to the next song (alias: n)"""
        if self.songs:
            self.songs.pop(0)
        try:
            self.current_target.force_play()
        except NoSongsToPlayException:
            print("No songs in the queue")

    def do_volume(self, line: str):
        """Set or change the volume. Valid values are between 0 and 100 (alias: v)
        +VALUE: Increase the volume by VALUE
        -VALUE: Decrease the volume by VALUE
        VALUE: Set the volume to VALUE
        """
        try:
            value = float(line) / 100.0
        except ValueError:
            print("Error converting the value into a number")
            return

        if line.startswith("+") or line.startswith("-"):
            self.current_target.volume_delta(value)
        else:
            self.current_target.volume_set(value)

    def do_quit(self, _line):
        """Exit the application (alias: x or Ctrl-D)"""
        self.current_target.stop()
        return True

    def precmd(self, line: str) -> str:
        potential_alias = line.split(" ")[0]
        aliases = {
            "pp": "playpause",
            "l": "list",
            "n": "next",
            "q": "queue",
            "v": "volume",
            "c": "clear",
            "x": "quit",
            "s": "switch",
            "EOF": "quit",  # Set by Cmd itself on Ctrl-C
        }
        if potential_alias in aliases:
            return line.replace(potential_alias, aliases[potential_alias], 1)
        else:
            return line


def main():
    parser = argparse.ArgumentParser("CastMe")
    parser.add_argument("--config", help="Set the configuration file to use")
    parser.add_argument(
        "--init",
        help="create an empty configuration file in ~/.config . You can override its location with --config",
        action="store_true",
    )
    parser.add_argument("--version", action="store_true", help="Print version and exit")
    parser.add_argument("backend", nargs="?")
    args = parser.parse_args()
    config_path = args.config

    if args.version:
        print("Version: ", castme_version())
        return

    if args.init:
        config_path = os.path.expanduser(args.config or "~/.config/castme.toml")
        if os.path.exists(config_path):
            print(f"The configuration file {config_path} already exist, bailing out...")
            sys_exit(1)
        shutil.copy(
            Path(os.path.dirname(__file__), "assets/castme.toml.template"), config_path
        )
        print(
            f"Configuration initialized in {config_path}, please edit it before starting castme again"
        )
        sys_exit(0)

    config = Config.load(config_path)
    subsonic = SubSonic(
        SUBSONIC_APP_ID, config.user, config.password, config.subsonic_server
    )

    songs_queue = []

    with (
        chromecast_backend(config, songs_queue) as chromecast,
        local_backend(config, songs_queue) as local,
    ):

        cli = CastMeCli(
            subsonic,
            {"chromecast": chromecast, "local": local},
            args.backend or config.default_backend,
            songs_queue,
        )
        cli.cmdloop()


if __name__ == "__main__":
    main()
