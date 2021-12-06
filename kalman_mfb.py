"""This module implements the Kalman filter-based radar-gauge bias correction
method described in:

S. Chumchean, A. Seed and A. Sharma, Correcting of real-time radar rainfall
bias using a Kalman filtering approach, Journal of Hydrology 317, 123-137,
2006.

The method is applied to the logarithmic radar-gauge mean field bias

    beta = 1 / n * sum_{i=1}^n log10(G/R)

where the summation is done over all radar-gauge pairs in the domain."""

from numpy import linalg as la
import numpy as np


class KalmanFilterMFB:
    """The Kalman filter model described in Chumchean et al., Fig. 1. The
    filter models the mean field bias beta and its variance denoted by P."""

    def __init__(self, rho_beta=0.72, sigma_beta=0.068, sigma_Y=0.25):
        """Initialize the model.

        Parameters
        ----------
        rho_beta : float

        sigma_beta : float
            Stationary variance of the process describing the mean field bias.
        sigma_Y : float
            Standard deviation of the rain rauge observation noise (mm).

        Notes
        -----
        The default values for rho_beta and sigma_beta are taken from
        Chumchean et al."""
        self.__beta = 0.0
        self.__P = _sigma_w_2(rho_beta, sigma_beta)
        self.__rho_beta = rho_beta
        self.__sigma_beta = sigma_beta
        self.__sigma_Y = sigma_Y

    def predict(self):
        """Compute the predicted state (beta_minus, P_minus) for the next time step."""
        beta_minus = self.__rho_beta * self.__beta
        P_minus = (
            self.__rho_beta ** 2 * self.__P
            + (1.0 - self.__rho_beta ** 2) * self.__sigma_beta ** 2
        )

        return beta_minus, P_minus

    def update(self, beta_minus, P_minus, Y):
        """Update the Kalman filter by using the predicted state
        (beta_minus, P_minus) and the most recent observed value of the mean
        field bias, denoted by Y. If Y is set to None (i.e. no observation
        available), skip the update step."""
        if Y is not None:
            sigma_M = self.__sigma_Y ** 2 - self.__sigma_beta ** 2
            K = _kalman_gain(P_minus, sigma_M)
            self.__beta = beta_minus + K * (Y - beta_minus)
            self.__P = (1 - K) * P_minus
        else:
            self.__beta = beta_minus
            self.__P = (1.0 - self.__rho_beta ** 2) * self.__sigma_beta ** 2

    @property
    def beta(self):
        """The current estimate for the mean field bias denoted by beta."""
        return self.__beta

    @property
    def P(self):
        """The current estimate for variance of the mean field bias denoted by P."""
        return self.__P


# the Kalman gain defined by equation (9)
def _kalman_gain(P_minus, sigma_M):
    return P_minus * 1.0 / (P_minus + sigma_M ** 2)


# the stationary process variance defined by equation (3)
def _sigma_w_2(rho_beta, sigma_beta):
    return (1.0 - rho_beta ** 2) * sigma_beta ** 2
