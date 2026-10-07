"""Offline stand-in for the GenLayer SDK, used only by the repository tests.

It lets the real contracts/upshield.py run in plain Python with a controllable
transaction clock, sender, attached value, mocked web pages and a mocked model.
It does not simulate consensus. Live behaviour is covered by `npm run e2e`.
"""
from types import SimpleNamespace

from . import types  # noqa: F401  (makes `from genlayer.types import *` work)
from .types import Address

transfers = []  # (recipient_hex, amount) for every emit_transfer
web_pages = {}  # url substring -> page body
llm = None  # callable(prompt) -> str
llm_calls = []  # every prompt sent to the model
message = SimpleNamespace(sender_address=Address("0x0"), value=0)
message_raw = {"datetime": "2026-01-01T00:00:00.000000Z"}


class UserError(Exception):
    pass


class TreeMap(dict):
    def __class_getitem__(cls, item):
        return cls


class Contract:
    def __new__(cls, *args, **kwargs):
        obj = super().__new__(cls)
        for klass in cls.__mro__:
            for name, ann in getattr(klass, "__annotations__", {}).items():
                if ann is TreeMap:
                    setattr(obj, name, TreeMap())
        return obj


def _ident(fn):
    return fn


class _Write:
    def __call__(self, fn):
        return fn

    payable = staticmethod(_ident)


public = SimpleNamespace(view=_ident, write=_Write())
contract = SimpleNamespace(Contract=Contract)
storage = SimpleNamespace(TreeMap=TreeMap)
vm = SimpleNamespace(UserError=UserError)


def _contract_interface(cls):
    class Wrapper:
        def __init__(self, address):
            self.address = address

        def emit_transfer(self, value):
            transfers.append((self.address.as_hex, int(value)))

    return Wrapper


evm = SimpleNamespace(contract_interface=_contract_interface)


def _render(url, mode="text"):
    for key, body in web_pages.items():
        if key in url:
            return body
    raise AssertionError("unmocked web request: " + url)


def _exec_prompt(task):
    llm_calls.append(task)
    return llm(task)


nondet = SimpleNamespace(web=SimpleNamespace(render=_render), exec_prompt=_exec_prompt)
eq_principle = SimpleNamespace(
    prompt_comparative=lambda fn, criteria: fn(),
    strict_eq=lambda fn: fn(),
)
