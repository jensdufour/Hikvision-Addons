import ctypes
import socket

import pytest


@pytest.fixture(autouse=True)
def forbid_hardware(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Offline tests must not open sockets or load the vendor SDK")
    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)
    monkeypatch.setattr(socket.socket, "sendto", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(ctypes.cdll, "LoadLibrary", blocked)