import numpy as np

def scale_values(
    values: np.ndarray,
    a: float,
    b: float
) -> np.ndarray:
    """Scale values from [0, 1] to [a, b] range

    Parameters
    ----------
    values : np.ndarray
        arrays of values to be scaled. The values should be in the range [0, 1]
    a : float
        lower bound of the range to scale to
    b : float
        upper bound of the range to scale to

    Returns
    -------
    np.ndarray
        scaled values in the range [a, b]
    """

    return a + (b - a) * values