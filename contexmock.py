import sys
from multiprocessing import Queue


class MockStdin:
    """
    Class for redirecting stdin with context manager

    Puts input in multiprocessing.Queue,
    so it could be retrieved from another process
    """

    def __init__(self):
        self.queue_input = Queue()
        self.real_stdin = sys.stdin

    def readline(self):
        return self.queue_input.get()

    def write_input(self, s):
        self.queue_input.put(s)

    def __enter__(self):
        sys.stdin = self

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        sys.stdin = self.real_stdin

    def __getstate__(self):
        self_dict = self.__dict__.copy()
        if "real_stdin" in self_dict:
            self_dict.pop("real_stdin")
        return self_dict


class MockStdout:
    """
    Class for redirecting stdout with context manager

    Puts output in multiprocessing.Queue,
    so it could be retrieved from another process
    """

    def __init__(self):
        self.queue_output = Queue()
        self.real_stdout = sys.stdout

    def write(self, s):
        self.queue_output.put(s)

    def read_output(self):
        return self.queue_output.get()

    def __enter__(self):
        sys.stdout = self

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        sys.stdout = self.real_stdout

    def __getstate__(self):
        self_dict = self.__dict__.copy()
        if "real_stdout" in self_dict:
            self_dict.pop("real_stdout")
        return self_dict
