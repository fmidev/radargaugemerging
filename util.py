"""Miscellaneous utility functions."""


def read_radar_locations(config):
    """Read radar locations from configuration file."""
    out = {}
    for radar in config.keys():
        out[radar] = tuple([float(v) for v in config[radar].split(",")])

    return out
