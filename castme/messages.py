from termcolor import cprint

_DEBUG = False


def enable_debug_mode():
    global _DEBUG  # noqa: PLW0603
    _DEBUG = True


def debug_mode_enabled() -> bool:
    return _DEBUG


def debug(msg: str):
    if _DEBUG:
        cprint(msg, "light_blue")


def message(msg: str):
    print(msg)


def error(msg: str):
    cprint(msg, "red", attrs=["bold"])
