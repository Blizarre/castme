from termcolor import cprint

_DEBUG = False


def enable_debug_mode():
    global _DEBUG  # noqa: PLW0603
    _DEBUG = True


def debug_mode_enabled() -> bool:
    return _DEBUG


def debug(context: str, msg: str):
    if _DEBUG:
        cprint(f"  [{context}] {msg}", "green")


def message(msg: str):
    print(msg)


def error(msg: str):
    cprint(msg, "red", attrs=["bold"])
