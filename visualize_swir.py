# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "h5py",
#     "matplotlib",
#     "imageio[ffmpeg]",
#     "numpy",
#     "tqdm",
# ]
# ///

import os
import glob
import h5py
import numpy as np
import matplotlib.pyplot as plt
import imageio
from tqdm import tqdm
import json

def get_download_path():
    try:
        with open("mdapi/config.json", "r") as f:
            config = json.load(f)
            return config["download_settings"]["download_path"]
    except Exception as e:
        print("Error reading config.json:", e)
        return "."

def find_swir_dataset(f):
    """Recursively find a dataset whose name contains SWIR."""
    swir_path = None
    def visitor(name, node):
        nonlocal swir_path
        if isinstance(node, h5py.Dataset) and "SWIR" in name.upper():
            swir_path = name
    f.visititems(visitor)
    return swir_path

def create_video(fps=5):
    download_path = get_download_path()
    print(f"Looking for HDF5 files in {download_path}")
    
    # 3RIMG files usually start with 3RIMG_ or similar and have .h5 extension
    search_pattern = os.path.join(download_path, "**", "*.h5")
    h5_files = glob.glob(search_pattern, recursive=True)
    
    if not h5_files:
        print("No HDF5 files found!")
        return

    # Sort files by name to maintain chronological order
    h5_files.sort()
    
    print(f"Found {len(h5_files)} HDF5 files.")
    
    output_filename = "swir_timelapse.mp4"
    writer = imageio.get_writer(output_filename, fps=fps)
    
    print(f"Generating video {output_filename} at {fps} FPS...")
    
    for file_path in tqdm(h5_files):
        try:
            with h5py.File(file_path, 'r') as f:
                swir_ds_name = find_swir_dataset(f)
                if not swir_ds_name:
                    print(f"No SWIR dataset found in {os.path.basename(file_path)}")
                    continue
                
                data = f[swir_ds_name][:]
                
                # Handle fill values or invalid data (often 1023 or 0 in raw satellite data)
                # Convert to float for processing
                data_f = data.astype(np.float32)
                
                # Simple normalization (ignoring outliers)
                valid_data = data_f[(data_f > 0) & (data_f < np.percentile(data_f, 99.9))]
                if len(valid_data) == 0:
                    continue
                
                vmin = np.percentile(valid_data, 1)
                vmax = np.percentile(valid_data, 99)
                
                data_norm = np.clip((data_f - vmin) / (vmax - vmin), 0, 1)
                
                # Convert to 8-bit image
                img_8bit = (data_norm * 255).astype(np.uint8)
                
                # Apply a colormap (gray is often best for SWIR)
                plt.imsave("temp_frame.png", img_8bit, cmap='gray')
                
                # Read back to append to video
                frame = imageio.v3.imread("temp_frame.png")
                writer.append_data(frame)
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            
    writer.close()
    if os.path.exists("temp_frame.png"):
        os.remove("temp_frame.png")
    print("Video generation complete!")

if __name__ == "__main__":
    create_video(fps=5)
