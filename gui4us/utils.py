import importlib
import sys
import os


class CfgRegister:

    def __init__(self):
        self.cfgs = set()

    def add(self, path):
        if path not in self.cfgs:
            self.cfgs.add(path)
            sys.path.insert(0, path)

    def remove(self, path):
        sys.path.remove(path)
        self.cfgs.remove(path)


_CFG_REGISTER = CfgRegister()


def load_cfg(path, id):
    """
    NOTE: this function is not thread-safe.
    """
    module_name = f"gui4us_cfg_{id}"
    cfg_dirname = os.path.dirname(os.path.abspath(path))
    try:
        spec = importlib.util.spec_from_file_location(module_name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        _CFG_REGISTER.add(cfg_dirname)
        spec.loader.exec_module(module)
        return module
    except:
        _CFG_REGISTER.remove(cfg_dirname)
        raise


def unload_cfg(path):
    _CFG_REGISTER.remove(path)
