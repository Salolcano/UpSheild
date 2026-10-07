"""Offline stand-in for genlayer.types, used only by the repository tests."""
u256 = int


class Address:
    def __init__(self, value):
        self.as_hex = str(value)

    def __eq__(self, other):
        return isinstance(other, Address) and self.as_hex == other.as_hex

    def __hash__(self):
        return hash(self.as_hex)


__all__ = ["u256", "Address"]
