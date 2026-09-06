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

def create_video(fps=5):
    download_path = get_download_path()
    print(f"Looking for HDF5 files in {download_path}")
    
    search_pattern = os.path.join(download_path, "**", "*.h5")
    h5_files = glob.glob(search_pattern, recursive=True)
    
    if not h5_files:
        print("No HDF5 files found!")
        return

    from datetime import datetime
    
    def get_file_time(filepath):
        # Extract the date and time from filenames like: 3RIMG_06SEP2026_0945_L1B_STD_V01R00.h5
        basename = os.path.basename(filepath)
        parts = basename.split("_")
        if len(parts) >= 3:
            date_time_str = parts[1] + "_" + parts[2]
            try:
                return datetime.strptime(date_time_str, "%d%b%Y_%H%M")
            except ValueError:
                pass
        # Fallback to file creation time if parsing fails
        return datetime.fromtimestamp(os.path.getctime(filepath))

    h5_files.sort(key=get_file_time)
    print(f"Found {len(h5_files)} HDF5 files. Sorted chronologically.")
    
    output_filename = "swir_timelapse.mp4"
    writer = imageio.get_writer(output_filename, fps=fps)
    print(f"Generating video {output_filename} at {fps} FPS...")
    
    for file_path in tqdm(h5_files):
        try:
            with h5py.File(file_path, 'r') as f:
                if 'IMG_SWIR' not in f:
                    print(f"No IMG_SWIR dataset found in {os.path.basename(file_path)}")
                    continue
                
                # Read specifically the Banten volcano region (approx 6°S, 105°E)
                # Instead of downsampling the full disk, we crop the specific area at 1:1 resolution
                # to maximize the visible detail of the volcano.
                # SWIR indices for Banten region: y ~ 6168 to 6432, x ~ 8724 to 8952
                # We add some padding for a nice 600x600 context window
                data = f['IMG_SWIR'][0, 6000:6600, 8500:9100]
                
                data_f = data.astype(np.float32)
                
                valid_data = data_f[(data_f > 0) & (data_f < np.percentile(data_f, 99.9))]
                if len(valid_data) == 0:
                    continue
                
                vmin = np.percentile(valid_data, 1)
                vmax = np.percentile(valid_data, 99)
                
                data_norm = np.clip((data_f - vmin) / (vmax - vmin), 0, 1)
                img_8bit = (data_norm * 255).astype(np.uint8)
                
                plt.imsave("temp_frame.png", img_8bit, cmap='gray')
                frame = imageio.v3.imread("temp_frame.png")
                writer.append_data(frame)
        except Exception as e:
            print(f"Error processing {os.path.basename(file_path)}: {e}")
            
    writer.close()
    if os.path.exists("temp_frame.png"):
        os.remove("temp_frame.png")
    print("Video generation complete!")

if __name__ == "__main__":
    create_video(fps=5)
