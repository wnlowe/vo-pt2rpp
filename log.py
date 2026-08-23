import logging, functools, time
import traceback

from preferences_manager import Config

class _Log:
    def __init__(self):
        self.app_data = Config.get_value("directories.preferences")
        logging.basicConfig(
            level=logging.INFO,
            format='%(message)s',
            datefmt='[%X]',
            handlers=[
                logging.FileHandler(f"{self.app_data}/app.log", mode="a"),
            ]
        )
        self._logger = logging.getLogger("vo_pt2rpp.app")

    def debug(self, msg, *args, **kwargs):
        self._logger.debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self._logger.info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self._logger.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self._logger.error(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self._logger.critical(msg, *args, **kwargs)

log = _Log()

def log_func(level = "info"):
    def log_level(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            add = ""
            if len(args) > 1:
                add = add + f" args={args[1:]}"
            if len(kwargs) > 0:
                add = add + f", kwargs={kwargs}"
            match level:
                case "info":
                    log.info(f"ENTER {func.__qualname__} {add}")
                case "warning":
                    log.warning(f"ENTER {func.__qualname__} {add}")
                case "error":
                    log.error(f"ENTER {func.__qualname__} {add}")
                case "critical":
                    log.critical(f"ENTER {func.__qualname__} {add}")
                case "debug":
                    log.debug(f"ENTER {func.__qualname__} {add}")
                case "print":
                    print(f"ENTER {func.__qualname__} {add}")
                case _:
                    log.info(f"ENTER {func.__qualname__} {add}") #args={args[1:]}, kwargs={kwargs}

            start = time.monotonic()
            try:
                result = func(*args, **kwargs)
            except BaseException as exc:
                elapsed = time.monotonic() - start
                log.error(
                    f"RAISE {func.__qualname__} after {elapsed:.2f}s: "
                    f"{exc!r}\n{traceback.format_exc()}"
                )
                raise
            else:
                elapsed = time.monotonic() - start
                match level:
                    case "info":
                        log.info(f"EXIT {func.__qualname__} after {elapsed:.2f}s")
                    case "warning":
                        log.warning(f"EXIT {func.__qualname__} after {elapsed:.2f}s")
                    case "error":
                        log.error(f"EXIT {func.__qualname__} after {elapsed:.2f}s")
                    case "critical":
                        log.critical(f"EXIT {func.__qualname__} after {elapsed:.2f}s")
                    case "debug":
                        log.debug(f"EXIT {func.__qualname__} after {elapsed:.2f}s")
                    case "print":
                        print(f"EXIT {func.__qualname__} after {elapsed:.2f}s")
                    case _:
                        log.info(f"EXIT {func.__qualname__} after {elapsed:.2f}s")
                return result
        return wrapper
    return log_level