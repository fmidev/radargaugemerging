"""Methods for writing output files."""

from osgeo import gdal, osr


def export_geotiff(filename, zvalues, projection, bounds):
    """Write a single-band array to a GeoTIFF file.

    Parameters
    ----------
    filename : str
        Output file name.
    zvalues : 2D array_like
        Two-dimensional array (height, width) to write.
    projection : int or str
        EPSG code (e.g., 3067) or PROJ string (e.g., "+proj=utm +zone=35 ...").
    bounds : list or tuple
        (x_min, y_min, x_max, y_max) defining the geographical bounds.
    """
    driver = gdal.GetDriverByName("GTiff")
    ny, nx = zvalues.shape

    dst = driver.Create(
        filename,
        nx,
        ny,
        1,  # Single band
        gdal.GDT_Float32,
        ["COMPRESS=DEFLATE", "PREDICTOR=3"],
    )

    srs = osr.SpatialReference()

    # Handle both EPSG codes and PROJ strings
    if isinstance(projection, int):
        srs.ImportFromEPSG(projection)
    elif isinstance(projection, str):
        if projection.lower().startswith("epsg:"):
            epsg_code = int(projection.split(":")[1])
            srs.ImportFromEPSG(epsg_code)
        else:
            ret = srs.ImportFromProj4(projection)
            if ret != 0:
                raise ValueError(f"Invalid PROJ string: {projection}")
    else:
        raise TypeError("projection must be int, 'EPSG:xxxx', or PROJ string")

    dst.SetProjection(srs.ExportToWkt())

    xmin, ymin, xmax, ymax = bounds
    xres = (xmax - xmin) / nx
    yres = (ymax - ymin) / ny
    geotransform = (xmin, xres, 0, ymax, 0, -yres)
    dst.SetGeoTransform(geotransform)

    band = dst.GetRasterBand(1)
    band.WriteArray(zvalues)
    band.SetNoDataValue(0.0)

    dst.FlushCache()
    dst = None
