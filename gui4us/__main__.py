import argparse

import gui4us
from gui4us.logging import get_logger
from gui4us.view.app import Application


LOGGER = get_logger(__name__)


def main():
    app: Application = None
    try:
        parser = argparse.ArgumentParser(
            description=f"GUI4us {gui4us.__version__}")
        parser.add_argument(
            "--host", dest="host",
            help="Host address on which the application should run.",
            default="localhost",
            required=False)
        parser.add_argument(
            "--port", dest="port",
            help="The port the server will listen on",
            type=int,
            default=7777,
            required=False)
        parser.add_argument(
            "--cfg", dest="cfg",
            help="Environment to run.",
            required=False,
            default=None
        )
        args = parser.parse_args()
        app = Application(
            host=args.host,
            port=args.port,
            cfg_path=args.cfg
        )
        if args.cfg is not None:
            app.create_env(cfg_path=args.cfg)
        app.run()

    except Exception as e:
        LOGGER.exception(e)
    finally:
        if app is not None:
            app.close()
        LOGGER.info("gui4us closed.")


if __name__ == "__main__":
    main()
