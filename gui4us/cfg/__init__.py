import importlib
import sys


def load_cfg(path):
    module_name = "gui4us_cfg"
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


from gui4us.cfg.environment import *
from gui4us.cfg.display import *


