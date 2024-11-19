from typing import Any
import numpy.typing as npt
import numpy as np


strings = list[str] | set[str] | tuple[str, ...]
floatlist = npt.NDArray[np.floating[Any]]
boollist = npt.NDArray[np.bool_]
rules = set[tuple[tuple[str, ...], str]]
