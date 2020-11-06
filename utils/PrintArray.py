import numpy as np


class PrintArray:
    def __init__(self, **kwargs):
        self._kwargs = kwargs

    def __repr__(self):
        rpr = (
            "PrintArray("
            + ", ".join([f"{name}={value}" for name, value in self._kwargs.items()])
            + ")"
        )
        return rpr

    def __array_ufunc__(self, ufunc, method, *inputs, **kwargs):
        if ufunc != np.floor_divide:
            return NotImplemented
        a = inputs[0]
        with np.printoptions(**self._kwargs):
            print(a)
