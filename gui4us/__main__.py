import matplotlib
matplotlib.use("QtAgg")
import sys
import argparse

import sys

import gui4us
from gui4us.controller import AppController, EnvController
from gui4us.logging import get_logger
from gui4us.model.app import App

from gui4us.view import View, start_view_app

LOGGER = get_logger(__name__)

def main():
    # Read input parameters.
    env = None
    try:
        parser = argparse.ArgumentParser(
            description=f"GUI4us {gui4us.__version__}")
        parser.add_argument(
            "--cfg", dest="cfg",
            help="Path to the env configuration file.",
            required=True)
        # Read configuration.
        args = parser.parse_args()
        cfg_path = args.cfg

        # Start application (MVC).
        env = EnvController("main", cfg_path)
        result = start_view_app(
            title=f"gui4us {gui4us.__version__}",
            cfg_path=cfg_path,
            env=env
        )
        sys.exit(result)
    except Exception as e:
        LOGGER.exception(e)
    finally:
        if env is not None:
            env.close()
        LOGGER.info("gui4us closed.")


if __name__ == "__main__":
    main()
