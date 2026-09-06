# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "h5py",
# ]
# ///

import os
import glob
import h5py
import json

def get_download_path():
    try:
        with open("mdapi/config.json", "r") as f:
            config = json.load(f)
            return config["download_settings"]["download_path"]
    except Exception as e:
        print("Error reading config.json:", e)
        return "."

def cleanup():
    download_path = get_download_path()
    print(f"Scanning for corrupted HDF5 files in {download_path}...")
    
    search_pattern = os.path.join(download_path, "**", "*.h5")
    h5_files = glob.glob(search_pattern, recursive=True)
    
    deleted_count = 0
    for file_path in h5_files:
        is_bad = False
        try:
            # Try to open the file and read the root keys. 
            # This will trigger an error if the file is corrupted, truncated, or bad.
            with h5py.File(file_path, 'r') as f:
                keys = list(f.keys())
        except Exception as e:
            print(f"Found corrupted file: {os.path.basename(file_path)} (Error: {e})")
            is_bad = True
            
        if is_bad:
            try:
                os.remove(file_path)
                print(f" -> Successfully deleted: {os.path.basename(file_path)}")
                deleted_count += 1
            except OSError as e:
                print(f" -> Failed to delete {os.path.basename(file_path)}: {e}")

    print(f"\nCleanup complete. Deleted {deleted_count} corrupted files.")
    print("You can now safely re-run 'uv run download_latest.py' to re-download the missing data.")

if __name__ == "__main__":
    cleanup()
