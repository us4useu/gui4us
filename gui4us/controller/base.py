from abc import ABC, abstractmethod


class AbstractController:

    @abstractmethod
    def run(self):
        pass

    @abstractmethod
    def close(self):
        pass
