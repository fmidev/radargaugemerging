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
    projection : str
        PROJ-compatible projection definition.
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
    srs.ImportFromProj4(projection)
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
