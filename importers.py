import gzip
from matplotlib.pyplot import imread
import numpy as np

try:
    import pyproj

    PYPROJ_IMPORTED = True
except ImportError:
    PYPROJ_IMPORTED = False


def import_fmi_pgm(filename, gzipped=False, **kwargs):
    """
    Import a 8-bit PGM radar reflectivity composite from the FMI archive.

    Parameters
    ----------
    filename: str
        Name of the file to import.
    gzipped: bool
        If True, the input file is treated as a compressed gzip file.

    {extra_kwargs_doc}

    Returns
    -------
    out: tuple
        A two-element tuple containing the reflectivity composite in dBZ and
        the associated metadata.

    Notes
    -----
    Reading georeferencing metadata is supported only for stereographic
    projection. For other projections, the keys related to georeferencing are
    not set.
    """
    if not PYPROJ_IMPORTED:
        raise ImportError(
            "pyproj package is required to import "
            "FMI's radar reflectivity composite "
            "but it is not installed"
        )

    if gzipped is False:
        precip = imread(filename)
    else:
        precip = imread(gzip.open(filename, "r"))
    pgm_metadata = _import_fmi_pgm_metadata(filename, gzipped=gzipped)
    geodata = _import_fmi_pgm_geodata(pgm_metadata)

    mask = precip == pgm_metadata["missingval"]
    precip = precip.astype(float)
    precip[mask] = np.nan
    precip = (precip - 64.0) / 2.0

    metadata = geodata
    metadata["institution"] = "Finnish Meteorological Institute"
    metadata["accutime"] = 5.0
    metadata["unit"] = "dBZ"
    metadata["transform"] = "dB"
    metadata["zerovalue"] = np.nanmin(precip)
    metadata["threshold"] = _get_threshold_value(precip)
    metadata["zr_a"] = 223.0
    metadata["zr_b"] = 1.53

    return precip, metadata


def _import_fmi_pgm_geodata(metadata):
    geodata = {}

    projdef = ""

    if "type" in metadata.keys() and metadata["type"][0] == "stereographic":
        projdef += "+proj=stere "
        projdef += " +lon_0=" + metadata["centrallongitude"][0] + "E"
        projdef += " +lat_0=" + metadata["centrallatitude"][0] + "N"
        projdef += " +lat_ts=" + metadata["truelatitude"][0]
        # These are hard-coded because the projection definition
        # is missing from the PGM files.
        projdef += " +a=6371288"
        projdef += " +x_0=380886.310"
        projdef += " +y_0=3395677.920"
        projdef += " +no_defs"
        #
        geodata["projection"] = projdef

        ll_lon, ll_lat = [float(v) for v in metadata["bottomleft"]]
        ur_lon, ur_lat = [float(v) for v in metadata["topright"]]

        pr = pyproj.Proj(projdef)
        x1, y1 = pr(ll_lon, ll_lat)
        x2, y2 = pr(ur_lon, ur_lat)

        geodata["x1"] = x1
        geodata["y1"] = y1
        geodata["x2"] = x2
        geodata["y2"] = y2
        geodata["cartesian_unit"] = "m"
        geodata["xpixelsize"] = float(metadata["metersperpixel_x"][0])
        geodata["ypixelsize"] = float(metadata["metersperpixel_y"][0])

        geodata["yorigin"] = "upper"

    return geodata


def _get_threshold_value(precip):
    valid_mask = np.isfinite(precip)
    if valid_mask.any():
        _precip = precip[valid_mask]
        min_precip = _precip.min()
        above_min_mask = _precip > min_precip
        if above_min_mask.any():
            return np.min(_precip[above_min_mask])
        else:
            return min_precip
    else:
        return np.nan


def _import_fmi_pgm_metadata(filename, gzipped=False):
    metadata = {}

    if not gzipped:
        f = open(filename, "rb")
    else:
        f = gzip.open(filename, "rb")

    file_line = f.readline()
    while not file_line.startswith(b"#"):
        file_line = f.readline()
    while file_line.startswith(b"#"):
        x = file_line.decode()
        x = x[1:].strip().split(" ")
        if len(x) >= 2:
            k = x[0]
            v = x[1:]
            metadata[k] = v
        else:
            file_line = f.readline()
            continue
        file_line = f.readline()
    file_line = f.readline().decode()
    metadata["missingval"] = int(file_line)
    f.close()

    return metadata
