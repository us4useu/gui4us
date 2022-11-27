import importlib
import sys
import argparse
import pathlib
import os
import arrus
import traceback

import logging

import gui4us
from gui4us.common import EventQueue
from gui4us.view import View, start_view
from gui4us.model.ultrasound import Env
from gui4us.controller import Controller


logging_file_handler = logging.FileHandler(filename="gui4us.log")
# logging_stderr_handler = logging.StreamHandler(sys.stderr)
logging_handlers = [logging_file_handler]# , logging_stderr_handler]
logging.basicConfig(level=logging.INFO, handlers=logging_handlers)


def load_cfg(path):
    module_name = "gui4us_cfg"
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    # Read input parameters.
    try:
        parser = argparse.ArgumentParser(description="GUI4us.")
        parser.add_argument("--cfg", dest="cfg",
                        help="Path to the initial configuration file",
                        required=True)
        args = parser.parse_args()
        cfg_path = args.cfg
        cfg = load_cfg(cfg_path)

        print("Creating model")
        model = Env(cfg.environment)
        print("Creating controller")
        controller = Controller(model)
        print("Creating View")
        result = start_view(f"gui4us {gui4us.__version__}",
                        cfg.view_cfg, controller)
        print(f"view returned with {result}")
        sys.exit(result)
    except Exception as e:
        print(traceback.format_exc())
        print(e)
    finally:
        pass


