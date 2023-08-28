import importlib
import sys
import os
import pathlib
import socket
from contextlib import closing
import webbrowser


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
    if not os.path.exists(cfg_dirname):
        raise ValueError(f"Directory does not exists: {cfg_dirname}.")
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


def get_gui4us_location() -> str:
    """
    Returns location to the gui4us module location.
    """
    return pathlib.Path(__file__).parent.__str__()


def get_free_port_for_address(address: str):
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind((address, 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


def open_browser(url):
    webbrowser.open_new(url)
