# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "requests",
#     "tqdm",
# ]
# ///

import json
import subprocess
from datetime import datetime, timedelta
import os
import sys

def main():
    config_path = "config.json"
    
    with open(config_path, "r") as f:
        config = json.load(f)
        
    now = datetime.now()
    start_date = now - timedelta(days=2)
    
    # Update search parameters
    config["search_parameters"]["datasetId"] = "3RIMG_L1B_STD"
    config["search_parameters"]["startTime"] = start_date.strftime("%Y-%m-%d")
    config["search_parameters"]["endTime"] = now.strftime("%Y-%m-%d")
    
    # Enable automatic download
    config["download_settings"]["skip_user_input"] = True
    
    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)
        
    print(f"Updated config.json to download 3RIMG_L1B_STD from {config['search_parameters']['startTime']} to {config['search_parameters']['endTime']}.")
    print(f"Download location: {config['download_settings']['download_path']}")
    
    # Run the mdapi.py script in a robust restart loop
    while True:
        print("Running mdapi.py...")
        result = subprocess.run([sys.executable, "-u", "mdapi.py"])
        
        if result.returncode == 0:
            print("\nAll downloads completed successfully!")
            break
        else:
            print(f"\n[!] mdapi.py exited with code {result.returncode}. Restarting the download immediately...")
            
if __name__ == "__main__":
    main()
