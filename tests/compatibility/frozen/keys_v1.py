class E:
    """Frozen snapshot of E API (v1) for compatibility testing."""

    def __new__(cls, id_=None):
        """id_: int | str | list[int] | tuple[int, ...] | None"""
        return None

    @property
    def high(self):
        return 0

    @property
    def high_mid(self):
        return 0

    @property
    def low_mid(self):
        return 0

    @property
    def low(self):
        return 0

    def to_hdf5(self):
        return None
