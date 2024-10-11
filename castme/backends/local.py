from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from io import BytesIO
from queue import Empty, Queue
from threading import Thread
from typing import Any, BinaryIO, Generator, List

import requests as r
from pygame import event, locals
from pygame.display import init as display_init
from pygame.mixer import Channel, Sound
from pygame.mixer import init as mixer_init

from castme.config import Config
from castme.player import Backend, NoSongsToPlayException
from castme.song import Song

STOP_EVENT = locals.USEREVENT + 1


def get_song(song: Song) -> BinaryIO:
    response = r.get(song.url, timeout=10)
    response.raise_for_status()
    return BytesIO(response.content)


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


def pygame_loop(queue: Queue[Message], songs: List[Song]):  # noqa: PLR0912
    """Pygame is not thread-safe. All the api calls needs to be done on the
    same thread, expecially the event management code."""
    mixer_init()
    display_init()
    channel = Channel(0)
    channel.set_endevent(STOP_EVENT)

    state = State.STOPPED

    while True:
        try:
            message = queue.get(timeout=0.1)
            print("Message", message)
            match message.type:
                case Message.Type.VOLUME_SET:
                    channel.set_volume(message.payload)
                case Message.Type.VOLUME_DELTA:
                    print(channel.get_volume())
                    channel.set_volume(channel.get_volume() + message.payload)
                case Message.Type.STOP:
                    state = State.STOPPED
                    channel.stop()
                case Message.Type.PLAY_PAUSE:
                    if state == State.STOPPED:
                        if songs:
                            print("playing")
                            channel.play(Sound(get_song(songs[0])))
                            state = State.PLAYING
                    elif state == State.PAUSED:
                        print("Unpausing")
                        channel.unpause()
                        state = State.PLAYING
                    elif state == State.PLAYING:
                        print("pausing")
                        channel.pause()
                        state = State.PAUSED
                case Message.Type.FORCE_PLAY:
                    if songs:
                        channel.play(Sound(get_song(songs[0])))
                        state = State.PLAYING
                case Message.Type.EXIT:
                    return
        except Empty:
            pass

        pygame_event = event.wait(100)
        if pygame_event == STOP_EVENT:
            if state == State.PLAYING:
                # The channel have stopped _and_ we are still playing. It is time
                # to move on to the next song
                songs.pop(0)
                if songs:
                    channel.play(Sound(get_song(songs[0])))
                else:
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
