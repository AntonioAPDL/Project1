import numpy as np

# Patch for numpy deprecation
if not hasattr(np, 'bool'):
    np.bool = bool

