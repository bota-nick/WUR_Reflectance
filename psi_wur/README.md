# PSI_WUR_PreProcessing.py Functions

This README describes the main functions in the `PSI_WUR_PreProcessing.py` script

## Functions

### 1. `OpenFimg(p)`
Reads a OpenFimg image file from the Fluorocam and returns the image as a NumPy array.
- **Parameters:**
  - `p`: Path to the Fluorocam file.
- **Returns:**
  - 2D NumPy array representing the image.

### 2. `Whiteref_Calibration(image_folder, white_ref_path)`
Calibrates all ENVI images in a folder using a pre-defined white reference image. Make sure that the white_ref_path points to the CalibFrame that is in the same folder as the images and corresponds to the White image. Note, this takes ENVIs (raw/hdrs) you need to convert the BIL files first
- **Parameters:**
  - `image_folder`: Directory containing ENVI images (`.hdr` files).
  - `white_ref_path`: Path to the white reference ENVI image.
- **Process:**
  - Loads the white reference and computes the column mean.
  - Divides each image by the white reference column mean.
  - Saves corrected images in a `Corrected_ENVIs` subfolder.
  - Renames output `.img` files to `.raw`.
  - Prints progress for each image.

### 3. `InspectDummFile(path)`
Reads a DUMM file from Fluorocam and prints the first 10 values corresponding to the Fm and FV images.
- **Parameters:**
  - `path`: Path to the DUMM file file.
- **Returns:**
  - NumPy array of int32 values.

### 4. `plant_mask(image_path, threshold=1.5)`
Creates a plant mask for a spectral image using a water band index. 1.5 is what I found works well for segmenting the leaves from the background but you can adjust the threshold if needed. NOTE this takes ENVI files (raw/hdr) you need to convert the BILs first.
- **Parameters:**
  - `image_path`: Path to the ENVI image.
  - `threshold`: Threshold for the water band index (default: 1.5).
- **Process:**
  - Computes a water band index to segment plant material from the image.
  - Creates a binary mask where the index exceeds the threshold.
  - Saves the mask as a PNG in a `plant_masks` subfolder.

### 5. `Bil2ENVI(path, output_path)`
Converts a BIL format file to ENVI format. I use this because the BIL format is not widely used in agriculture. ENVIs using (raw/hdr) is the standard at WUR. This should be run first on any exports from the PSI system. 
- **Parameters:**
  - `path`: Path to the input BIL file (expects a corresponding `.hdr` file).
  - `output_path`: Path for the output ENVI file.
- **Process:**
  - Reads header for image dimensions, bands, and layout.
  - Loads binary data and reshapes according to layout (BIL, BIP, BSQ).
  - Saves the data in ENVI format with metadata.
  - Renames output `.img` files to `.raw`.

---

For more details, see the function docstrings and comments in the script.
