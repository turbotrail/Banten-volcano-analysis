# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "h5py",
#     "matplotlib",
#     "imageio[ffmpeg]",
#     "numpy",
#     "tqdm",
#     "opencv-python-headless",
# ]
# ///

import os
import glob
import h5py
import numpy as np
import cv2
import matplotlib.pyplot as plt
from datetime import timedelta, datetime
import imageio
from tqdm import tqdm
import json
import argparse

def get_download_path():
    try:
        with open("mdapi/config.json", "r") as f:
            config = json.load(f)
            return config["download_settings"]["download_path"]
    except Exception as e:
        print("Error reading config.json:", e)
        return "."

def get_file_time(filepath):
    basename = os.path.basename(filepath)
    parts = basename.split("_")
    if len(parts) >= 3:
        date_time_str = parts[1] + "_" + parts[2]
        try:
            return datetime.strptime(date_time_str, "%d%b%Y_%H%M")
        except ValueError:
            pass
    return datetime.fromtimestamp(os.path.getctime(filepath))

def process_channel_data(f, channel, region_cfg):
    """Extracts, normalizes, and resizes a specific channel's data from the HDF5 file."""
    target_w, target_h = region_cfg["target_resolution"]
    
    if channel not in f:
        # Return a black frame if missing (e.g. VIS during night might be black or missing)
        return np.zeros((target_h, target_w, 3), dtype=np.uint8)
        
    ds = f[channel]
    is_4km = ds.shape[1] < 5000
    
    y_min, y_max = region_cfg["y_min_1km"], region_cfg["y_max_1km"]
    x_min, x_max = region_cfg["x_min_1km"], region_cfg["x_max_1km"]
    
    if is_4km:
        y_min, y_max = y_min // 4, y_max // 4
        x_min, x_max = x_min // 4, x_max // 4
    
    crop_h = y_max - y_min
    crop_w = x_max - x_min
    
    stride_y = max(1, crop_h // target_h)
    stride_x = max(1, crop_w // target_w)
    stride = min(stride_y, stride_x)
    
    data = ds[0, y_min:y_max:stride, x_min:x_max:stride]
    data_f = data.astype(np.float32)
    
    valid_data = data_f[(data_f > 0) & (data_f < np.percentile(data_f, 99.9))]
    if len(valid_data) == 0:
        return np.zeros((target_h, target_w, 3), dtype=np.uint8)
    
    vmin = np.percentile(valid_data, 1)
    vmax = np.percentile(valid_data, 99)
    
    data_norm = np.clip((data_f - vmin) / (vmax - vmin), 0, 1)
    img_8bit = (data_norm * 255).astype(np.uint8)
    
    img_8bit = cv2.resize(img_8bit, (target_w, target_h), interpolation=cv2.INTER_NEAREST)
    img_rgb = cv2.cvtColor(img_8bit, cv2.COLOR_GRAY2RGB)
    
    # Add channel label to the top right corner
    label = channel.replace("IMG_", "")
    text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
    cv2.putText(img_rgb, label, (target_w - text_size[0] - 15, 35), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2, cv2.LINE_AA)
                
    return img_rgb

def create_video(fps=5, channel="IMG_SWIR", region="banten", grid=False):
    download_path = get_download_path()
    print(f"Looking for HDF5 files in {download_path}")
    
    config_file = "visualize_config.json"
    if not os.path.exists(config_file):
        print(f"Error: {config_file} not found!")
        return
        
    with open(config_file, "r") as f:
        vis_config = json.load(f)
        
    region_cfg = vis_config["regions"].get(region)
    if not region_cfg:
        print(f"Error: Region '{region}' not defined in {config_file}")
        return
    
    search_pattern = os.path.join(download_path, "**", "*.h5")
    h5_files = glob.glob(search_pattern, recursive=True)
    
    if not h5_files:
        print("No HDF5 files found!")
        return

    h5_files.sort(key=get_file_time)
    print(f"Found {len(h5_files)} HDF5 files. Sorted chronologically.")
    
    if grid:
        grid_channels = vis_config.get("grid_settings", {}).get("channels", ["IMG_VIS", "IMG_SWIR", "IMG_MIR", "IMG_TIR1"])
        if len(grid_channels) != 4:
            print("Error: grid_settings.channels in config must contain exactly 4 channels for a 2x2 grid.")
            return
        output_filename = f"grid_{region}_timelapse.mp4"
        print(f"Generating 2x2 GRID video {output_filename} at {fps} FPS comparing {grid_channels}...")
    else:
        output_filename = f"{channel.lower()}_{region}_timelapse.mp4"
        print(f"Generating single-channel video {output_filename} at {fps} FPS using {channel}...")
        
    writer = imageio.get_writer(output_filename, fps=fps)
    
    for file_path in tqdm(h5_files):
        try:
            with h5py.File(file_path, 'r') as f:
                utc_time = get_file_time(file_path)
                ist_time = utc_time + timedelta(hours=5, minutes=30)
                time_str = ist_time.strftime("%d %b %Y %H:%M IST")
                
                if grid:
                    ch1_img = process_channel_data(f, grid_channels[0], region_cfg)
                    ch2_img = process_channel_data(f, grid_channels[1], region_cfg)
                    ch3_img = process_channel_data(f, grid_channels[2], region_cfg)
                    ch4_img = process_channel_data(f, grid_channels[3], region_cfg)
                    
                    top_row = np.hstack([ch1_img, ch2_img])
                    bot_row = np.hstack([ch3_img, ch4_img])
                    final_img = np.vstack([top_row, bot_row])
                else:
                    if channel not in f:
                        print(f"No {channel} dataset found in {os.path.basename(file_path)}")
                        continue
                    final_img = process_channel_data(f, channel, region_cfg)
                
                # Burn master timestamp string onto frame (Yellow text)
                cv2.putText(final_img, time_str, (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2, cv2.LINE_AA)
                
                writer.append_data(final_img)
        except Exception as e:
            print(f"Error processing {os.path.basename(file_path)}: {e}")
            
    writer.close()
    print("Video generation complete!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a timelapse video from INSAT-3DR HDF5 files.")
    parser.add_argument("--fps", type=int, default=5, help="Frames per second for the output video.")
    parser.add_argument("--channel", type=str, default="IMG_SWIR", 
                        choices=["IMG_SWIR", "IMG_MIR", "IMG_TIR1", "IMG_TIR2", "IMG_VIS"], 
                        help="The sensor channel to visualize (e.g. IMG_MIR for thermal).")
    parser.add_argument("--region", type=str, default="banten",
                        help="The predefined region from visualize_config.json to crop (e.g. 'banten' or 'full_disk').")
    parser.add_argument("--grid", action="store_true", 
                        help="Generate a 2x2 grid comparing 4 channels defined in visualize_config.json.")
    args = parser.parse_args()
    
    create_video(fps=args.fps, channel=args.channel, region=args.region, grid=args.grid)
