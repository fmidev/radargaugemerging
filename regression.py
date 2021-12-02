"""Methods for fitting regression surfaces."""

import itertools
import numpy as np
import scipy.linalg as la


class Polynomial:
    """D-dimensional polynomial regression model."""

    def __init__(self, X, Y, degree):
        """Fit a d-dimensional polynomial to the given data.

        Parameters
        ----------
        X : array_like
            Coordinates of the data points. Array of shape (n,d), where n is
            the number of data points and d is dimension.
        Y : array_like
            One-dimensional array of length n containing function values at the
            data points.
        degree : int
            Degree of the polynomial.
        """
        P = np.array(X)
        V = _polyvandernd(P, degree)

        self.__C = la.lstsq(V, Y)[0]
        self.__degree = degree
        self.__dim = X.shape[1]

    def __call__(self, X):
        """Evaluate the regression polynomial at the given points.

        Parameters
        ----------
        X : array_like
            Array of shape (n,d) containing n d-dimensional points.

        Returns
        -------
        out : array_like
            N-dimensional array containing the function values at the given
            points.
        """
        if len(X.shape) == 1:
            X = np.reshape(X, (len(X), 1))

        f_X = np.zeros(X.shape[0])
        J = _ndpolydegrees(self.__dim, self.__degree)
        for i in range(X.shape[0]):
            f_X[i] = 0.0
            for k in range(pow(self.__degree + 1, self.__dim)):
                p = 1.0
                for l in range(self.__dim):
                    p *= pow(X[i, l], J[k, l])
                ci = _ndpolycoeffidx(J[k, :], self.__dim, self.__degree)
                f_X[i] += self.__C[ci] * p

        return f_X


def _ndpolycoeffidx(i, m, d):
    j = 0
    for k in range(m):
        j += pow(d + 1, m - (k + 1)) * i[k]

    return j


def _ndpolydegrees(m, d):
    D = np.array(list(itertools.product(*itertools.repeat(range(d + 1), m))))
    mask = np.sum(np.diff(D, axis=1), axis=1) != 0
    D = np.vstack([D, np.fliplr(D[mask, :])])

    return D


def _polyvandernd(X, deg):
    n, m = X.shape

    V = np.ones((n, pow(deg + 1, m)))
    J = _ndpolydegrees(m, deg)
    for i in range(n):
        for l in range(pow(deg + 1, m)):
            j = _ndpolycoeffidx(J[l, :], m, deg)
            for k in range(m):
                V[i, j] *= pow(X[i, k], J[l, k])

    return V
