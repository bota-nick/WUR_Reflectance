import spectral
import numpy as np
import os
import matplotlib.pyplot as plt
import pandas as pd
from glob import glob
import cv2

def OpenFimg(p):
  with open(p, "rb") as f:
    data = f.read()
    header = np.frombuffer(data[:8], dtype=np.int32)
    #print("Header:", header[0], header[1])
    # Extract the rest of the data as 32-bit floats
    # (Make sure that the remaining byte count is a multiple of 4)
    floats = np.frombuffer(data[8:], dtype=np.float32)
    #print("Floats:", floats)
    image = np.reshape(floats, newshape=(header[1], header[0])) #Image size in pixels
    return image.copy()
    
def Whiteref_Calibration(image_folder, white_ref_path):
  """
  Calibrate all images in image_folder using the column mean of white_ref.
  Save corrected images with the same name in a subfolder 'Corrected_ENVIs'.
  """

  # Load white reference image and compute column mean
  white_ref_img = spectral.envi.open(white_ref_path)
  white_ref = white_ref_img.load().astype(np.float32)
  white_col_mean = np.mean(white_ref, axis=0)  # shape: (n_cols,)
  zeroplus = 1e-10

  corrected_dir = os.path.join(image_folder, 'Corrected_ENVIs')
  os.makedirs(corrected_dir, exist_ok=True)

  # Find all ENVIS images in the folder
  image_paths = glob(os.path.join(image_folder, '*.hdr'))
  for idx, img_path in enumerate(image_paths, 1):
    envi_img = spectral.envi.open(img_path)
    img = envi_img.load().astype(np.float32)
    meta = envi_img.metadata

    # Divide each column by the white reference column mean
    corrected = img / (white_col_mean + zeroplus)

    # Save with same name in Corrected_ENVIs
    out_hdr = os.path.join(corrected_dir, os.path.basename(img_path))
    spectral.envi.save_image(out_hdr, corrected, dtype=np.float32, force=True, metadata=meta)

    # Rename the .img file to .raw
    img_file = os.path.splitext(out_hdr)[0] + '.img'
    raw_file = os.path.splitext(out_hdr)[0]  + '.raw'
    if os.path.exists(img_file):
      os.rename(img_file, raw_file)
    print(f"Corrected {idx} of {len(image_paths)} images. Saved to {corrected_dir}")

def InspectDummFile(path):
  with open(path, "rb") as f:
    data = f.read()
    # Try reading as int32
    ints = np.frombuffer(data, dtype=np.int32)
    print("First 10 int32 values:", ints[:10])
    print("Total int32 values:", len(ints))
    return ints
  def plant_mask(image_path, threshold=1.5):
    """
    Create a plant mask for the spectral using a water band index:
    - A: mean of bands with wavelength 120-130 (1200 nm - 1223 nm)
    - B: mean of bands with wavelength 210-220 (1423 nm -1448 nm)
    - Mask: (A/B) >= threshold
    Saves the mask as a PNG in a 'plant_masks' subfolder under the image's base folder.
    """
    img = spectral.envi.open(image_path)
    data = img.load().astype(np.float32)

    # Do the math to create the mask
    A = np.mean(data[..., 119:131], axis=-1)
    B = np.mean(data[..., 209:231], axis=-1)
    index = A / (B + 1e-10)
    mask = (index >= threshold).astype(np.uint8) * 255

    # Prepare output path
    base_folder = os.path.dirname(image_path)
    mask_folder = os.path.join(base_folder, 'plant_masks')
    os.makedirs(mask_folder, exist_ok=True)
    mask_filename = os.path.splitext(os.path.basename(image_path))[0] + '_mask.png'
    mask_path = os.path.join(mask_folder, mask_filename)
    cv2.imwrite(mask_path, mask)
    print(f"Saved plant mask to {mask_path}")


# OpenFimg, Whiteref_Calibration, InspectDummFile, Bil2ENVI
def Bil2ENVI(path,output_path):

  #also read the header file as well to get dimensions, it will have the same name but .hdr extension
  hdr_path = os.path.splitext(path)[0] + '.hdr'
  if os.path.exists(hdr_path):
    with open(hdr_path, 'r') as hdr:
      lines = hdr.readlines()
      wavelengths = []
      reading_wavelengths = False
      for line in lines:
        if 'NCOLS' in line:
          cols = int(line.split()[-1])
        elif 'samples = ' in line:
          cols = int(line.split()[-1])
        elif 'NROWS' in line:
          rows = int(line.split()[-1])
        elif 'lines = ' in line:
          rows = int(line.split()[-1])
        elif 'NBANDS' in line:
          bands = int(line.split()[-1])
        elif 'bands = ' in line:
          bands = int(line.split()[-1])
        elif 'NBITS' in line:
          bits = int(line.split()[-1])
        elif 'data type = ' in line:
          datatype = int(line.split()[-1])
          if datatype == 4:
            bits = 32
          elif datatype == 2:
            bits = 16
        elif 'LAYOUT' in line:
          layout = line.split()[-1]
        elif 'interleave = ' in line:
          layout = line.split()[-1]
        elif 'WAVELENGTH' in line:
          reading_wavelengths = True
          continue
        elif 'WAVELENGTH END' in line:
          reading_wavelengths = False
          continue
        if reading_wavelengths:
          try:
            wavelengths.append(float(line.strip()))
          except ValueError:
            pass
        elif 'wavelength' in line.lower() and '=' in line and '{' in line and '}' in line:
          try:
            wl_str = line.split('=',1)[1]
            wl_str = wl_str.strip().lstrip('{').rstrip('}').replace('{','').replace('}','')
            wavelengths += [float(w.strip()) for w in wl_str.split(',') if w.strip()]
          except Exception:
            pass
  else:
    # If no header file, assume default dimensions (example: 512x512)
    rows = 512
    cols = 512
    bands = 100
    bits = 32  # Assuming float32
  

    # Read the binary file using bits to determine dtype
  if bits == 32:
    dtype = np.float32  
  elif bits == 16:
    dtype = np.uint16
  else:
    raise ValueError("Unsupported bit depth: {}".format(bits))
  
  # Switch to the .bil data file (same name, .bil extension)
  data_path = os.path.splitext(path)[0] + '.bil'
  # Load the binary data using np.fromfile for all layouts
  if layout == 'BIL':
    data = np.fromfile(data_path, dtype=dtype).reshape((rows, bands, cols)).transpose(0, 2, 1)
  elif layout == 'bil':
    data = np.fromfile(data_path, dtype=dtype).reshape((rows, bands, cols)).transpose(0, 2, 1)
  elif layout == 'BIP':
    data = np.fromfile(data_path, dtype=dtype).reshape((rows, cols, bands))
  elif layout == 'bip':
    data = np.fromfile(data_path, dtype=dtype).reshape((rows, cols, bands))
  else:  # Default to BSQ
    data = np.fromfile(data_path, dtype=dtype).reshape((bands, rows, cols)).transpose(1, 2, 0)
  
  #Create a new metadata dictionary for ENVI
  meta = {
    'description': 'Converted from BIL format',
    'samples': cols,
    'lines': rows,
    'bands': bands,
    'data type': 4 if bits == 32 else 2,  # ENVI data type codes
    'interleave': layout.lower(),
    'byte order': 0,
    'wavelength': wavelengths if 'wavelengths' in locals() else []
  }

  #now we resave the data in ENVI format with the same name as the input file but with .envi extension

  envi_path = os.path.splitext(output_path)[0] + '.hdr'
  # Save result as .hdr/.raw pair
  spectral.envi.save_image(envi_path, data, dtype=np.float32, force=True, metadata=meta)

        # Rename the .img file to .raw
  img_file = os.path.splitext(output_path)[0] + '.img'
  raw_file = os.path.splitext(output_path)[0]  + '.raw'
  if os.path.exists(img_file):
    os.rename(img_file, raw_file)
  #print(f"Converted complete and saved for {envi_path}.")


    # --- Test Bil2ENVI with user input ---
# if __name__ == "__main__":

#   input_root = "W:\\PROJECTS\\Phenotyping4Profit\\Data\\Bremia_2025\\G8 experiment NPEC\\FinalData_upload\\Spectral_images\\2025-03-5"
#   output_root = "W:\\PROJECTS\\Phenotyping4Profit\\Data\\Bremia_2025\\G8 experiment NPEC\\FinalData_upload\\Corrected_Spectral_images\\2025-03-5"
#   # for dirpath, dirnames, filenames in os.walk(input_root):
#   #   for filename in filenames:
#   #     if filename.lower().endswith('.hdr'):
#   #       hdr_path = os.path.join(dirpath, filename)
#   #       # Compute relative path and output path
#   #       rel_path = os.path.relpath(hdr_path, input_root)
#   #       out_dir = os.path.join(output_root, os.path.dirname(rel_path))
#   #       os.makedirs(out_dir, exist_ok=True)
#   #       out_path = os.path.join(out_dir, os.path.splitext(os.path.basename(hdr_path))[0] + '.hdr')
#   #       if os.path.exists(out_path):
#   #         print(f"Skipping   {os.path.splitext(filename)[0]} (already exists)")
#   #         continue
#   #       print(f"Converting {os.path.splitext(filename)[0]}")
#   #       Bil2ENVI(hdr_path, out_path)
#   Whiteref_Calibration(input_root, 'W:\\PROJECTS\\Phenotyping4Profit\\Data\\Bremia_2025\\G8 experiment NPEC\\FinalData_upload\\Spectral_images\\2025-03-6\\2025-03-06--14-20-19_round-0_cam-2_calibFrame.hdr')

