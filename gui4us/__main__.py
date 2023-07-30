import argparse

import sys

import gui4us
from gui4us.logging import get_logger
from gui4us.app import Application


LOGGER = get_logger(__name__)


def main():
    app: Application = None
    try:
        parser = argparse.ArgumentParser(
            description=f"GUI4us {gui4us.__version__}")
        parser.add_argument(
            "--port", dest="port",
            help="The port the server will listen on",
            default="7777",
            required=False)
        args = parser.parse_args()
        app = Application(
            port=args.port,
        )
        app.run()

    except Exception as e:
        LOGGER.exception(e)
    finally:
        if app is not None:
            app.close()
        LOGGER.info("gui4us closed.")


if __name__ == "__main__":
    main()
