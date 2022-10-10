import traceback
import logging
import sys
import traceback
import multiprocessing as mp

import gui4us
from gui4us.controller import MainController
from gui4us.view import start_view

logging_file_handler = logging.FileHandler(filename="gui4us.log")
logging_handlers = [logging_file_handler]
logging.basicConfig(level=logging.INFO, handlers=logging_handlers)

if __name__ == "__main__":
    mp.set_start_method("spawn")
    # Read input parameters.
    controller = None
    result = None
    try:
        controller = MainController()
        result = start_view(f"gui4us {gui4us.__version__}", controller)
    except Exception as e:
        print(traceback.format_exc())
        print(e)
    finally:
        if controller is not None:
            controller.close()
    sys.exit(result)
