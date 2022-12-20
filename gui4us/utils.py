import importlib
import sys


def load_cfg(path, id):
    module_name = f"gui4us_cfg_{id}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module