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
from castme.messages import debug_mode_enabled, enable_debug_mode, error, message
from castme.player import Backend, NoSongsToPlayException
from castme.song import Song
from castme.subsonic import AlbumNotFoundException, SubSonic


class InvalidBackend(Exception):
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
    def __init__(
        self,
        subsonic: SubSonic,
        targets: Dict[str, Backend],
        default_backend: str,
        songs: List[Song],
    ):
        super().__init__()
        self.min_column_width = 50
        self.subsonic = subsonic
        self.songs = songs
        self.targets = targets
        if default_backend not in targets:
            raise InvalidBackend(default_backend)

        self.current_target = targets[default_backend]
        message(f"Currently playing on {default_backend}")
        self.update_prompt(default_backend)

    def update_prompt(self, label: str):
        self.prompt = f"[{label}] >> "

    def do_rewind(self, _list: str):
        self.current_target.rewind()

    def do_list(self, _line: str):
        """List all the albums available (alias: l)"""
        term_cols, term_rows = get_terminal_size()
        albums = self.subsonic.get_all_albums()
        number_of_columns = term_cols // self.min_column_width or 1
        # We can get some extra chars by dispatching the remainder characters to
        # each column
        column_width = (
            self.min_column_width
            + (term_cols % self.min_column_width) // number_of_columns
        )
        text_width_fmt = str(column_width - 2)  # 2 chars of padding
        # We want to truncate the string to the text width
        format_string_album = "{:" + text_width_fmt + "." + text_width_fmt + "}"

        while albums:
            lines_printed = 1
            # We print line by line
            while albums and lines_printed < term_rows:
                displayed_albums = albums[:number_of_columns]
                albums = albums[number_of_columns:]
                # This line concatenate N format string and then format the result with N album names
                message(
                    "".join(([format_string_album] * len(displayed_albums))).format(
                        *displayed_albums
                    )
                )
                lines_printed += 1

            if albums:
                input(" .... Press <Enter> to continue ....")

    def emptyline(self):
        pass

    def do_switch(self, line):
        """Switch to another backend. Without argument list the available
        backends. (alias: s)"""
        if not line:
            message(f"Available targets: {', '.join(self.targets.keys())}")
            return

        if line in self.targets:
            self.current_target.stop()
            self.current_target = self.targets[line]
            if self.songs:
                self.current_target.force_play()

            self.update_prompt(line)
        else:
            error(f"Could not find target {line}")

    def do_clear(self, _line: str):
        """Clear the queue and stop the music (alias: c)"""
        self.songs.clear()
        self.current_target.stop()

    def do_queue(self, line: str):
        """Queue an album. The argument to that command will be matched against all
        albums on the device and the best matching one will be played (alias: q).
        """
        if not line:
            for idx, s in enumerate(self.songs):
                message(f"{1 + idx:2} {s}")
            return
        try:
            start_empty = len(self.songs) == 0
            name, songs = self.subsonic.get_songs_for_album(line)
            message(f"Queueing {name}")
            self.songs.extend(songs)
            if start_empty:
                self.current_target.force_play()
        except AlbumNotFoundException as e:
            error(str(e))

    def do_playpause(self, _line: str):
        """play/pause the song (alias: pp)"""
        self.current_target.playpause()

    def do_next(self, _line: str):
        """Skip to the next song (alias: n)"""
        if self.songs:
            self.songs.pop(0)
        try:
            self.current_target.force_play()
        except NoSongsToPlayException:
            error("No songs in the queue")

    def do_volume(self, line: str):
        """Set or change the volume. Valid values are between 0 and 100 (alias: v)
        +VALUE: Increase the volume by VALUE
        -VALUE: Decrease the volume by VALUE
        VALUE: Set the volume to VALUE
        """
        try:
            value = float(line) / 100.0
        except ValueError:
            error("Error converting the value into a number")
            return

        if line.startswith("+") or line.startswith("-"):
            self.current_target.volume_delta(value)
        else:
            self.current_target.volume_set(value)

    def do_quit(self, _line: str):
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
            "r": "rewind",
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
    parser.add_argument("--debug", action="store_true", help="print debugging messages")
    parser.add_argument("backend", nargs="?")
    args = parser.parse_args()
    config_path = args.config

    if args.debug:
        enable_debug_mode()

    if args.version:
        message(f"Version: {castme_version()}")
        return

    try:
        if args.init:
            config_path = os.path.expanduser(args.config or "~/.config/castme.toml")
            if os.path.exists(config_path):
                error(
                    f"The configuration file {config_path} already exist, bailing out..."
                )
                sys_exit(1)
            shutil.copy(
                Path(os.path.dirname(__file__), "assets/castme.toml.template"),
                config_path,
            )
            message(
                f"Configuration initialized in {config_path}, please edit it before starting castme again"
            )
            sys_exit(0)

        config = Config.load(config_path)
        subsonic = SubSonic(
            SUBSONIC_APP_ID, config.user, config.password, config.subsonic_server
        )

        songs_queue: List[Song] = []

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
    except Exception as e:
        if debug_mode_enabled():
            raise
        else:
            error(str(e))
            sys_exit(1)


if __name__ == "__main__":
    main()
