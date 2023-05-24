import h5py
import hiisi
import numpy as np
import gzip
import math
import json
import logging
import sys
import argparse
import datetime


def read_config(config_file):
    """Read parameters from config file.

    Keyword arguments:
    config_file -- json file containing input parameters

    Return:
    coef -- dictionary containing coefficients
    input_conf -- dictionary containing input parameters
    output_conf -- dictionary containing output parameters

    """

    with open(config_file, "r") as jsonfile:
        data = json.load(jsonfile)

    coef = data["coef"]
    input_conf = data["input_composite"]
    radargauge_conf = data["radargauge_file"]
    output_conf = data["output_composite"]

    return coef, input_conf, radargauge_conf, output_conf


def read_hdf5(image_h5_file):
    """Read image array from ODIM hdf5 file.

    Keyword arguments:
    image_h5_file -- ODIM hdf5 file containing DBZH or RATE array

    Return:
    image_array -- numpy array containing DBZH or RATE array
    quantity -- array quantity, either 'DBZH' or 'RATE'
    timestamp -- timestamp of image_array
    mask_nodata -- masked array where image_array has nodata value
    gain -- gain of image_array
    offset -- offset of image_array

    """

    # Read RATE or DBZH from hdf5 file
    logging.info(f"Extracting data from {image_h5_file} file")
    comp = hiisi.OdimCOMP(image_h5_file, "r")
    # Read RATE array if found in dataset
    test = comp.select_dataset("DBZH")
    if test is not None:
        image_array = comp.dataset
        quantity = "DBZH"
    else:
        # Look for RATE array
        test = comp.select_dataset("RATE")
        if test is not None:
            image_array = comp.dataset
            quantity = "RATE"
        else:
            # Look for SNOWPROB array
            test = comp.select_dataset("SNOWPROB")
            if test is not None:
                image_array = comp.dataset
                quantity = "SNOWPROB"
            else:
                # Look for ACCR array
                test = comp.select_dataset("ACRR")
                if test is not None:
                    image_array = comp.dataset
                    quantity = "ACRR"
                else:
                    logging.error(
                        f"DBZH, RATE, SNOWPROB or ACRR array not found in the file {image_h5_file}!"
                    )
                    sys.exit(1)

    # Read nodata and undetect values from metadata for masking
    gen = comp.attr_gen("nodata")
    pair = gen.__next__()
    nodata = pair.value
    gen = comp.attr_gen("undetect")
    pair = gen.__next__()
    undetect = pair.value

    # Read gain and offset values from metadata
    gen = comp.attr_gen("gain")
    pair = gen.__next__()
    gain = pair.value
    gen = comp.attr_gen("offset")
    pair = gen.__next__()
    offset = pair.value

    # Read timestamp from metadata
    gen = comp.attr_gen("date")
    pair = gen.__next__()
    date = pair.value
    gen = comp.attr_gen("time")
    pair = gen.__next__()
    time = pair.value

    timestamp = date + time

    return image_array, quantity, timestamp, gain, offset, int(nodata), int(undetect)


def convert_dtype(accumulated_image, output_conf, nodata_mask, undetect_mask):
    """Change output data dtype (e.g. to 16 bit unsigned integer) and rescale data if needed

    Keyword arguments:
    accumulated_image --
    output_conf --
    nodata_mask --
    undetect_mask --

    Return:
    scaled_image_new_dtype --

    """
    scaled_image = (accumulated_image - output_conf["offset"]) / output_conf["gain"]
    scaled_image[nodata_mask] = output_conf["nodata"]
    scaled_image[undetect_mask] = output_conf["undetect"]
    scaled_image_new_dtype = scaled_image.astype(output_conf["dtype"])

    return scaled_image_new_dtype


def dBZtoRR(dbz, coef):                                                                           
    """Convert dBZ to rain rate (frontal/convective rain).                                                                                
     
    Keyword arguments:
    dbz -- Array of dBZ values
    coef -- dictionary containing Z(R) A and B coefficients                                                                                                                  

    Return:
    rr -- rain rate
    """

    zr_a = coef["zr_a"]
    zr_b = coef["zr_b"]
    
    # Convert dBZ to rain rate RR
    rr = 10 ** (dbz / (10 * zr_b) + (-math.log10(zr_a) / zr_b))
    
    return rr


def RRtodBZ(rr, coef):
    """Convert rain rate to dBZ.

    Keyword arguments:
    rr -- rain rate
    coef -- dictionary containing Z(R) A and B coefficients zr_a, zr_b

    Return:
    dbz -- Array of dBZ values

    """
    
    zr_a = coef["zr_a"]
    zr_b = coef["zr_b"]

    # Convert RR to dBZ
    dbz = 10 * zr_b * math.log10(rr) + math.log10(zr_a)

    return rr       


def overwrite_dataset_hdf5(infile, outfile):
    """ Overwrite modified dataset in hdf5 file and write everything to new file.
    
    Keyword arguments:
    infile -- input filename
    outfile -- output filename

    """

    f1 = h5py.File(infile, 'r+')     # open the file
    
    data = f1['meas/frame1/data']       # load the data
    data[...] = X1                      # assign new values to data
    f1.close()                          # close the file
   
    

def run(timestamp, config):

    config_file = f"/config/{config}/multiply_composite_with_calculated_factor.json"
    coef, input_conf, radargauge_conf, output_conf = read_config(config_file)

    # Current timestamp in datetime
    formatted_timestamp = datetime.datetime.strptime(timestamp, "%Y%m%d%H%M")
    
    # Read dbzh composite hdf5
    if input_conf["dir_contains_date"]:
        input_file = f"{input_conf['path'].format(year=timestamp[0:4], month=timestamp[4:6], day=timestamp[6:8])}/{input_conf['filename'].format(timestamp=timestamp, config=config)}"
    else:
        input_file = f"{input_conf['path']}/{input_conf['filename'].format(timestamp=timestamp, config=config)}"

    image_array, quantity, file_timestamp, gain, offset, nodata, undetect = read_hdf5(input_file)
    
    nodata_mask = image_array == nodata
    undetect_mask = image_array == undetect
    
    # Convert image arrays dBZ -> rate
    first_image_array = dbzh_to_rate.dBZtoRATE_lut(
        np.int_(first_image_array), lut_rr, lut_sr, snowprob
    )
    second_image_array = dbzh_to_rate.dBZtoRATE_lut(
        np.int_(second_image_array), lut_rr, lut_sr, snowprob
    )


    # Multiply rain values with radargauge factor


    # Convert image arrays back to dBZ
    
    # Change nodata and undetect to zero and np.nan before interpolation
    first_image_array[nodata_mask_first] = np.nan
    first_image_array[undetect_mask_first] = 0
    


def main():
    run(options.timestamp, options.config)


if __name__ == "__main__":
    # Parse commandline arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--timestamp", type=str, default="202201170700", help="Input timestamp"
    )
    parser.add_argument(
        "--config", type=str, default="ravake_composite", help="Config file to use."
    )

    options = parser.parse_args()
    main()
