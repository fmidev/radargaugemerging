"""Utilities for matching precipitation fields with gauge measurements."""

import numpy as np

def find_nearest_pixel(x, y, R, x1, y1, x2, y2, yorigin="upper"):
  """For a given set of locations, find the nearest pixel values in the given 
  precipitation field.
  
  Parameters
  ----------
  x : scalar or array_like
    The x-coordinate(s) of the location(s).
  y : scalar or array_like
    The y-coordinate(s) of the location(s).
  R : array_like
    Two-dimensional array containing the precipitation field.
  x1 : float
    X-coordinate of the lower-left corner of R (in the same coordinate system as x).
  y1 : float
    Y-coordinate of the lower-left corner of R (in the same coordinate system as y).
  x2 : float
    X-coordinate of the upper-right corner of R (in the same coordinate system as x).
  y2 : float
    Y-coordinate of the upper-right corner of R (in the same coordinate system as y).
  yorigin : str
    The available options are "upper" and "lower". If set to "upper", the origin 
    of the y-axis of the data raster is assumed to be at the upper border, and 
    at the lower border otherwise.
  
  Returns
  -------
  out : scalar or array
    Values of the pixels that are nearest to the given x- and y-coordinates.
  """
  scalar_input = True if np.isscalar(x) and np.isscalar(y) else False
  
  if not scalar_input and len(x) != len(y):
    raise ValueError("x and y must have the same shape")

  x = np.array([x]) if scalar_input else np.array(x)
  y = np.array([y]) if scalar_input else np.array(y)

  xi = (x - x1) / (x2 - x1) * (R.shape[1] - 1) + 0.5
  if yorigin == "upper":
    yi = (y2 - y) / (y2 - y1) * (R.shape[0] - 1) + 0.5
  else:
    yi = (y - y1) / (y2 - y1) * (R.shape[0] - 1) + 0.5

  r = R[yi.round().astype(int), xi.round().astype(int)]

  if scalar_input:
    return r[0]
  else:
    return r
