import numpy as np

def scale_values(values, lower_bnd , upper_bnd) -> np.ndarray: 
    """
    Scales an array of values from 0 to 1 to be within the range of lower_bnd and upper_bnd.

    Parameters
    ----------
    values : np.ndarray
        The array of values to be scaled.
    lower_bnd : float
        The lower bound of the range to scale the values to.
    upper_bnd : float
    
    """
    return a + (b - a) * values