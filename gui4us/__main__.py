import sys
import argparse

import gui4us
from gui4us.logging import get_logger

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
        parser.add_argument(
            "--view", dest="view", default="qt", choices=("qt", "web"),
            help="View to start: 'qt' (default, PyQt window) or 'web' (browser).")
        parser.add_argument(
            "--host", dest="host", default="127.0.0.1",
            help="Web view only: address to bind to.")
        parser.add_argument(
            "--port", dest="port", type=int, default=7777,
            help="Web view only: port to listen on.")
        parser.add_argument(
            "--max-fps", dest="max_fps", type=float, default=30.0,
            help="Web view only: upper bound on the displayed frame rate.")
        # Read configuration.
        args = parser.parse_args()
        cfg_path = args.cfg

        if args.view == "web":
            # The web view owns its environment controller (it is created by create_session).
            from gui4us.view.web.server import start_view_app as start_web_view
            sys.exit(start_web_view(
                cfg_path=cfg_path, host=args.host, port=args.port, max_fps=args.max_fps))

        # Qt view (default). Imported here so that the web view does not require PyQt.
        import matplotlib
        matplotlib.use("QtAgg")
        from gui4us.controller import EnvController
        from gui4us.view import start_view_app

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
