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
import pickle


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
        dataset_path = test
    else:
        # Look for RATE array
        test = comp.select_dataset("RATE")
        if test is not None:
            image_array = comp.dataset
            quantity = "RATE"
            dataset_path = test
        else:
            # Look for SNOWPROB array
            test = comp.select_dataset("SNOWPROB")
            if test is not None:
                image_array = comp.dataset
                quantity = "SNOWPROB"
                dataset_path = test
            else:
                # Look for ACCR array
                test = comp.select_dataset("ACRR")
                if test is not None:
                    image_array = comp.dataset
                    quantity = "ACRR"
                    dataset_path = test
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
    
    return image_array, quantity, timestamp, gain, offset, int(nodata), int(undetect), dataset_path


def convert_dtype(image_array, nodata_mask, undetect_mask, nodata, undetect, gain, offset):
    """Change output data dtype (e.g. to 16 bit unsigned integer) and rescale data if needed

    Keyword arguments:
    image_array -- image array with physical values
    nodata_mask -- nodata mask
    undetect_mask -- undetect mask
    nodata -- input/output data nodata
    undetect -- input/output data undetect
    gain -- input/output data scale
    offset -- input/output data offset

    Return:
    scaled_image_new_dtype -- 

    """

    if nodata == 65535:
        dtype = "uint16"
    elif nodata == 255:
        dtype = "uint8"
        
    scaled_image = (image_array - offset) / gain    
    scaled_image[nodata_mask] = nodata
    scaled_image[undetect_mask] = undetect
    scaled_image_new_dtype = scaled_image.astype(dtype)
    
    return scaled_image_new_dtype


def dBZtoRR(dbz, coef):                                                                           
    """Convert dBZ to rain rate using simple formula.
     
    Keyword arguments:
    dbz -- Array of dBZ values
    coef -- dictionary containing Z(R) A and B coefficients                                                                                                                  

    Return:
    rr -- rain rate
    """

    zr_a = coef["zr_a"]
    zr_b = coef["zr_b"]
    
    # Convert dBZ to rain rate RR
    rr = np.power(10**(dbz/10) / zr_a, 1/zr_b)
    
    return rr


def RRtodBZ(rr, coef):
    """Convert rain rate to dBZ using simple formula.

    Keyword arguments:
    rr -- rain rate
    coef -- dictionary containing Z(R) A and B coefficients zr_a, zr_b

    Return:
    dbz -- Array of dBZ values

    """
    
    zr_a = coef["zr_a"]
    zr_b = coef["zr_b"]

    # Convert RR to dBZ
    dbz = 10 * np.log10(zr_a * np.power(rr, zr_b))
    
    return dbz       


def read_radargauge_factor(radargauge_factor_file):
    """ Read radargauge factor from file

    Keyword arguments:
    radargauge_factor_file -- pickle file containing dictionary of factors

    Return:
    radargauge_factor -- radargauge factor

    """
    pickle_file = open(radargauge_factor_file,"rb")
    data = pickle.load(pickle_file)
    radargauge_factor = data["corr_factor"]
    print("radargauge_factor: ", radargauge_factor)

    return radargauge_factor
    

def overwrite_dataset_hdf5(infile, outfile, datapath, new_dataset):
    """ Overwrite modified dataset in hdf5 file and write everything to new file.
    
    Keyword arguments:
    infile -- input hdf5 filename
    outfile -- output hdf5 filename
    datapath -- dataset path in infile
    new_dataset -- new dataset

    """    
    # Create a copy of the hdf5 file
    with h5py.File(infile, 'r') as f_source:
        with h5py.File(outfile, 'w') as f_dest:
            # Copy all items from source file to destination file
            for name, item in f_source.items():
                f_source.copy(name, f_dest)

            # Copy root-level attributes
            for name, value in f_source.attrs.items():
                f_dest.attrs[name] = value

            # Overwrite the data in the existing dataset
            f_dest[datapath][...] = new_dataset

        
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

    image_array, quantity, file_timestamp, gain, offset, nodata, undetect, dataset_path = read_hdf5(input_file)
    
    # Get nodata and undetect masks and then give
    # value 0 to them
    nodata_mask = image_array == nodata
    undetect_mask = image_array == undetect
    image_array[nodata_mask] = 0
    image_array[undetect_mask] = 0
    
    # Convert to physical values
    image_array_phys = image_array * gain + offset
    
    # Convert image arrays dBZ -> rate
    image_array_rate = dBZtoRR(image_array_phys, coef)
    
    # Multiply rain values with radargauge factor
    radargauge_factor_file = f"{radargauge_conf['path']}/{radargauge_conf['filename'].format(config=config)}"
    radargauge_factor = read_radargauge_factor(radargauge_factor_file)
    image_array_rate = image_array_rate * radargauge_factor

    # Convert image arrays back to dBZ
    image_array_dbz = RRtodBZ(image_array_rate, coef)

    # Convert back to 16bit (or 8bit) unsigned integer values
    image_array_dbz = convert_dtype(image_array_dbz, nodata_mask, undetect_mask, nodata, undetect, gain, offset)
    
    # Write to file
    output_file = f"{output_conf['path'].format(year=timestamp[0:4], month=timestamp[4:6], day=timestamp[6:8])}/{output_conf['filename'].format(timestamp=timestamp, config=config)}"
    overwrite_dataset_hdf5(input_file, output_file, dataset_path, image_array_dbz)

    
def main():
    run(options.timestamp, options.config)


if __name__ == "__main__":
    # Parse commandline arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--timestamp", type=str,
        default="202201170700",
        help="Input timestamp"
    )
    parser.add_argument(
        "--config", type=str,
        default="ravake_composite",
        help="Config file to use."
    )

    options = parser.parse_args()
    main()
