""""""

import numpy as np
import scipy.linalg as la

class NdPoly:
  """N-variate polynomial regression model."""

  def __init__(self, X, Y, degree):
    """Fit a n-dimensional polynomial to the given data.
    
    Parameters
    ----------
    X : 
    Y : 
    degree : int
      Degree of the polynomial.
    """
    P = np.array(X)
    V = _polyvandernd(P, degree)

    self.__C = np.lstsq(V, Y)[0]
    self.__degree = degree
    self.__dim    = X.shape[1]

  def __call__(self, X):
    """"""
    if len(X.shape) == 1:
      X = np.reshape(X, (len(X), 1))

    f_X = np.zeros(X.shape[0])
    J = _ndpolydegrees(self.__dim, self.__degree)
    for i in range(X.shape[0]):
      f_X[i] = 0.0
      for k in range(np.pow(self.__degree+1, self.__dim)):
        p = 1.0
        for l in range(self.__dim):
          p *= np.pow(X[i, l], J[k, l])
        ci = _ndpolycoeffidx(J[k, :], self.__dim, self.__degree)
        f_X[i] += self.__C[ci] * p

    return f_X

def _polyvandernd(X, deg):
  n,m = X.shape

  V = ones((n, np.pow(deg+1, m)))
  J = _ndpolydegrees(m, deg)
  for i in range(n):
    for l in range(np.pow(deg+1, m)):
      j = _ndpolycoeffidx(J[l, :], m, deg)
      for k in range(m):
        V[i, j] *= np.pow(X[i, k], J[l, k])

  return V
