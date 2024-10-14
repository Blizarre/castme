from contextlib import contextmanager, redirect_stdout
from dataclasses import dataclass
from enum import Enum
from io import BytesIO
from queue import Empty, Queue
from threading import Thread
from typing import Any, BinaryIO, Generator, List

import requests as r

# Feeling bad about it, but pygame always display a welcome
# message which is completely out of place on a CLI music player.
with redirect_stdout(None):
    from pygame import event, NOEVENT
    from pygame.locals import USEREVENT
    from pygame.display import init as display_init
    from pygame.mixer import music
    from pygame.mixer import init as mixer_init

from castme.config import Config
from castme.messages import debug as msg_debug
from castme.player import Backend, NoSongsToPlayException
from castme.song import Song

STOP_EVENT = USEREVENT + 1


def get_song(song: Song) -> BinaryIO:
    response = r.get(song.url, timeout=10)
    response.raise_for_status()
    return BytesIO(response.content)


def debug(msg):
    msg_debug("local", msg)


@dataclass
class Message:
    class Type(Enum):
        VOLUME_SET = 1
        VOLUME_DELTA = 2
        PLAY_PAUSE = 3
        FORCE_PLAY = 4
        STOP = 5
        EXIT = 6
        PLAY = 7

    @staticmethod
    def playpause():
        return Message(Message.Type.PLAY_PAUSE, None)

    @staticmethod
    def stop():
        return Message(Message.Type.STOP, None)

    @staticmethod
    def exit():
        return Message(Message.Type.EXIT, None)

    @staticmethod
    def force_play():
        return Message(Message.Type.FORCE_PLAY, None)

    type: Type
    # This is ugly but it will do for now. Poor man's tagged union
    payload: Any


class State(Enum):
    PLAYING = 1
    PAUSED = 2
    STOPPED = 3


def play_next(songs: List[Song]) -> bool:
    if songs:
        debug(f"Playing {songs[0].title}")
        music.load(get_song(songs[0]))
        music.play()
        return True
    return False


def pygame_loop(queue: Queue[Message], songs: List[Song]):  # noqa: PLR0912
    """Pygame is not thread-safe. All the api calls needs to be done on the
    same thread, expecially the event management code."""
    mixer_init()
    display_init()
    music.set_endevent(STOP_EVENT)

    state = State.STOPPED

    while True:
        try:
            message = queue.get(timeout=0.1)
            debug(f"loop - Received message {message}")
            match message.type:
                case Message.Type.VOLUME_SET:
                    music.set_volume(message.payload)
                case Message.Type.VOLUME_DELTA:
                    music.set_volume(music.get_volume() + message.payload)
                case Message.Type.STOP:
                    state = State.STOPPED
                    music.stop()
                case Message.Type.PLAY_PAUSE:
                    if state == State.STOPPED:
                        if play_next(songs):
                            state = State.PLAYING
                    elif state == State.PAUSED:
                        music.unpause()
                        state = State.PLAYING
                    elif state == State.PLAYING:
                        music.pause()
                        state = State.PAUSED
                case Message.Type.FORCE_PLAY:
                    if play_next(songs):
                        state = State.PLAYING
                case Message.Type.EXIT:
                    return
        except Empty:
            pass

        if (pygame_event := event.poll()).type != NOEVENT:
            debug(f"Event: {pygame_event}")
            if pygame_event.type == STOP_EVENT:
                if state == State.PLAYING:
                    # The channel have stopped _and_ we are now playing the queued song. It is time
                    # to move on to the next song
                    if songs:
                        songs.pop(0)

                    if songs and play_next(songs):
                        debug("Channel was not busy, played the next song")
                        state = State.PLAYING
                    else:
                        debug("Channel was not busy, nothing to play")
                        state = State.STOPPED


class LocalBackendImpl(Backend):
    def __init__(self, songs: List[Song]):
        self.songs = songs
        self.queue: Queue[Message] = Queue()
        self.pygame_thread = Thread(
            target=pygame_loop,
            args=(
                self.queue,
                self.songs,
            ),
        )
        self.pygame_thread.start()

    def close(self):
        self.queue.put(Message.exit())
        self.pygame_thread.join()

    def playpause(self):
        self.queue.put(Message.playpause())

    def force_play(self):
        if not self.songs:
            raise NoSongsToPlayException()
        self.queue.put(Message.force_play())

    def volume_set(self, value: float):
        self.queue.put(Message(Message.Type.VOLUME_SET, value))

    def volume_delta(self, value: float):
        self.queue.put(Message(Message.Type.VOLUME_DELTA, value))

    def stop(self):
        self.queue.put(Message.stop())


@contextmanager
def backend(_config: Config, songs: List[Song]) -> Generator[Backend, None, None]:
    local = LocalBackendImpl(songs)
    try:
        yield local
    finally:
        local.close()
