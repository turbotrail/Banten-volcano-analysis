# Banten Volcano Analysis

This repository contains an automated Python pipeline for downloading and visualizing live geostationary satellite data (INSAT-3DR) to monitor volcanic activity in the Banten region (Sunda Strait, Indonesia). 

By leveraging the `3RIMG_L1B_STD` dataset, this tool processes massive multi-spectral HDF5 satellite imagery, performing dynamic spatial downsampling to efficiently extract high-resolution regions of interest (like Anak Krakatau) without overwhelming system memory.

## Features

- **Automated Data Retrieval**: Fetches the latest 48 hours of satellite imagery via the MOSDAC API.
- **Robust Error Handling**: Auto-restarts on token expiration (HTTP 429) and network drops. Includes a cleanup script to automatically detect and purge corrupted or truncated HDF5 files.
- **Multi-Spectral Visualization**: Renders timelapse videos from different sensor channels (Visible, Shortwave IR, Mid-Infrared, Thermal IR).
- **Synchronized Grid Mode**: Generates a 2x2 comparison grid of four different sensor channels over time.
- **In-Memory Processing**: Uses OpenCV (`cv2`) for blazing-fast, direct-to-video array rendering (eliminating slow disk-based intermediate image creation).

---

## 🛠️ Installation & Setup

This project uses `uv` for lightning-fast dependency management. The scripts are configured with inline dependency metadata, meaning `uv` will automatically install what it needs when you run them.

1. Ensure you have [`uv`](https://github.com/astral-sh/uv) installed.
2. Clone the repository.

---

## 📥 Data Downloading

### 1. Configuration
Open `mdapi/config.json` and configure your credentials and target download location.
Ensure you have a valid MOSDAC account configured in `user_credentials`.

```json
{
    "user_credentials": {
        "username/email": "your_email@example.com",
        "password": "your_password"
    },
    "download_settings": {
        "download_path": "/Volumes/Expansion/banten_volcano"
    }
}
```

### 2. Fetching the Data
Run the auto-downloader. This script automatically checks the last 48 hours, updates the config, and executes the downloader in an infinite restart loop to guarantee success despite rate limits or connection drops.

```bash
uv run mdapi/download_latest.py
```

### 3. Cleaning Corrupted Files
If the download was interrupted and resulted in truncated files, run the cleanup script. It will scan for broken HDF5 files and delete them so they can be re-downloaded cleanly.

```bash
uv run cleanup_bad_files.py
```

*(You can simply run the auto-downloader again after cleaning up to fetch the missing files).*

---

## 🎥 Visualization

The visualization engine is heavily configurable via `visualize_config.json`. You can define custom geographic bounding boxes (1km coordinate scales) and output resolutions.

### Basic Visualization
Run the visualizer targeting a specific sensor channel (e.g. `IMG_MIR`) and region (e.g. `banten`):

```bash
uv run visualize_swir.py --channel IMG_MIR --region banten
```

Available Channels:
- `IMG_VIS`: Visible Light
- `IMG_SWIR`: Shortwave Infrared
- `IMG_MIR`: Mid-Infrared (Best for night-time thermal hotspot tracking)
- `IMG_TIR1` / `IMG_TIR2`: Thermal Infrared (Best for tracking ash plumes)

### Full Earth Disk
If you want to render the entire globe, use the `full_disk` region. The script mathematically downsamples the 11,000x11,000 arrays into memory-safe sizes automatically!

```bash
uv run visualize_swir.py --channel IMG_VIS --region full_disk
```

### Grid Mode (Multi-Spectral Comparison)
To observe multiple channels simultaneously, you can generate a synchronized 2x2 grid. 

```bash
uv run visualize_swir.py --region banten --grid
```

*Note: You can configure which 4 channels are displayed in the grid by editing the `grid_settings` block in `visualize_config.json`.*

---

## 🌋 Monitoring Note

When observing volcanic thermal signatures over long periods:
- **Daytime**: `IMG_VIS` and `IMG_SWIR` are excellent for spotting structural changes and smoke.
- **Nighttime**: Because they rely on reflected sunlight, VIS and SWIR go completely dark at night. You must switch to `IMG_MIR` or `IMG_TIR1` to track the thermal glow of lava flows or ash plumes seamlessly through the night!
