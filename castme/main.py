import argparse
import difflib
import random
import string
import time
import urllib.parse
from hashlib import md5
from typing import Any, Dict, List, Tuple

import requests
from attr import dataclass
from pychromecast import Chromecast, get_listed_chromecasts
from pychromecast.controllers.media import (
    MediaController,
    MediaStatus,
    MediaStatusListener,
)


class AlbumNotFoundException(BaseException):
    def __init__(self, keyword):
        self.keyword = keyword

    def __str__(self):
        return f"Album not found with keyword: {self.keyword}"


class ChromecastNotFoundException(BaseException):
    def __init__(self, keyword):
        self.keyword = keyword

    def __str__(self):
        return f"Chromecast named {self.keyword} not found"


@dataclass
class Song:
    title: str
    album_name: str
    artist: str
    url: str
    content_type: str
    album_art: str


class MyChromecastListener(MediaStatusListener):
    def __init__(self, songs: List[Song], media_controller: MediaController):
        self.songs = songs
        self.media_controller = media_controller

    def new_media_status(self, status: MediaStatus):
        print(f"{len(self.songs)} left")
        if status.player_is_idle and status.idle_reason == "FINISHED":
            play_on_chromecast(self.songs.pop(0), self.media_controller)

    def load_media_failed(self, item: int, error_code: int):
        """Called when load media failed."""
        print("BOOH", item, error_code)


def find_chromecast() -> Chromecast:
    friendly_chromecast_label = "Living Room TV"
    chromecasts, _ = get_listed_chromecasts(friendly_names=[friendly_chromecast_label])
    if not chromecasts:
        raise ChromecastNotFoundException(friendly_chromecast_label)

    return chromecasts[0]


def make_sonic_url(verb: str, **kwargs) -> Tuple[str, Dict[str, Any]]:
    user = "admin"
    pwd = "admin"
    version = "1.16.1"
    app_id = "castme"
    salt = "".join(random.choices(string.ascii_letters + string.digits, k=10))
    token = md5((pwd + salt).encode()).hexdigest()
    parameters = kwargs | {
        "u": user,
        "t": token,
        "v": version,
        "c": app_id,
        "f": "json",
        "s": salt,
    }

    return f"https://m.l.marache.net/rest/{verb}", parameters


def call_sonic(verb: str, **kwargs):
    url, parameters = make_sonic_url(verb, **kwargs)
    req = requests.get(url, params=parameters, timeout=20)
    req.raise_for_status()
    return req.json()


def get_songs_for_album(album_name: str) -> List[Song]:
    output = call_sonic("getAlbumList", type="alphabeticalByName", size=500)[
        "subsonic-response"
    ]
    albums = output["albumList"]["album"]
    _songs = []
    names = [a["album"] for a in albums]
    closest = difflib.get_close_matches(album_name, [a["album"] for a in albums], 1)
    if not closest:
        print(
            f"Couldn't find your album, FYI, all the available albums:\n{",   ".join(names)}"
        )
        raise AlbumNotFoundException(album_name)
    print(f"Closest match for {album_name} is {closest[0]}")
    for album in albums:
        if album["album"] == closest[0]:
            cover_url, cover_params = make_sonic_url(
                "getCoverArt", id=album["coverArt"]
            )
            theid = album["id"]
            data = call_sonic("getAlbum", id=theid)["subsonic-response"]["album"][
                "song"
            ]
            for s in data:
                strurl, params = make_sonic_url("stream", id=s["id"])
                _songs.append(
                    Song(
                        s["title"],
                        s["album"],
                        s["artist"],
                        strurl + "?" + urllib.parse.urlencode(params),
                        s["contentType"],
                        cover_url + "?" + urllib.parse.urlencode(cover_params),
                    )
                )
    return _songs


def play_on_chromecast(song: Song, controller: MediaController):
    print("Playing", song)
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


def main():
    parser = argparse.ArgumentParser("CastMe")
    parser.add_argument("album")
    args = parser.parse_args()
    candidate_album_name = args.album

    songs = get_songs_for_album(candidate_album_name)
    print(f"{len(songs)} to play")

    print("Finding chromecast")
    cast = find_chromecast()

    print("Waiting for cast to be ready")
    cast.wait()
    print("Chromecast ready")

    mc: MediaController = cast.media_controller
    mc.register_status_listener(MyChromecastListener(songs, mc))

    # Kick-start the player
    play_on_chromecast(songs.pop(0), mc)

    print("Waiting for chromecast")
    mc.block_until_active()
    print("Active, ready to rock)")

    while True:
        time.sleep(1)
