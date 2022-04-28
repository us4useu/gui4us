from abc import abstractmethod

EnvId = str
StreamId = str


class Stream:
    """
    Represents a stream of data produced synchronously.
    """

    @abstractmethod
    def new_data(self):
        """
        A signal emitted when new data (observations) arrive.
        :return:
        """
        raise NotImplementedError()


class Metadata:
    pass


class Action:
    pass


class Env:

    @property
    def id(self) -> EnvId:
        return "Env"

    @property
    def actions(self):
        raise {}

    @abstractmethod
    def start(self) -> None:
        raise NotImplementedError()

    @abstractmethod
    def stop(self) -> None:
        raise NotImplementedError()

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError()

    @abstractmethod
    def do(self, action: Action) -> None:
        raise NotImplementedError()

    @abstractmethod
    def get_stream(self, id: StreamId) -> Stream:
        raise NotImplementedError()

    @abstractmethod
    def get_stream_metadata(self, id: StreamId) -> Metadata:
        raise NotImplementedError()

