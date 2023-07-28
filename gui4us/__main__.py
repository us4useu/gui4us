import argparse

import sys

import gui4us
from gui4us.logging import get_logger
from gui4us.app import Application


LOGGER = get_logger(__name__)


def main():
    # Read input parameters.
    env = None
    try:
        parser = argparse.ArgumentParser(
            description=f"GUI4us {gui4us.__version__}")
        parser.add_argument(
            "--cfg", dest="cfg",
            help="Path to the initial env configuration files.",
            required=True)

        args = parser.parse_args()
        cfg_path = args.cfg

        sys.exit(result)
    except Exception as e:
        LOGGER.exception(e)
    finally:
        if env is not None:
            env.close()
        LOGGER.info("gui4us closed.")


if __name__ == "__main__":
    main()
