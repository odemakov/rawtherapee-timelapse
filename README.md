# RawTherapee Timelapse

Interpolates RawTherapee PP3 settings between keyframes for smooth timelapse sequences.

## Features

- Interpolates temperature, green/tint, and exposure compensation between keyframe PP3 files
- Automatic 16:9 crop with multiple drift modes (center, top, bottom, animated drift)
- Ken Burns zoom effects (in/out) with customizable anchor points and easing functions
- Multiple output resolutions: 1080p, 2K, 4K, 5K, 6K, 8K
- Dry-run mode for preview
- Automatic backup of existing PP3 files

## Installation

```bash
pip install rawtherapee-timelapse
```

## Usage

1. Edit keyframes in RawTherapee (first frame, last frame, and any others where settings change)
2. Run interpolation:

```bash
# Basic usage - interpolate and crop to 4K
rawtherapee-timelapse /path/to/images

# Preview without creating files
rawtherapee-timelapse /path/to/images --dry-run

# Sunrise effect - drift crop from bottom to top
rawtherapee-timelapse /path/to/images --aspect-drift bottom-to-top

# Add zoom in effect
rawtherapee-timelapse /path/to/images --zoom in --zoom-level 80-100

# Complex example: 6K output with exponential zoom out anchored at top
rawtherapee-timelapse /path/to/images --output 6k --zoom out --zoom-level 70-100 --zoom-anchor top --zoom-easing exponential
```

## Docker Usage (for macOS)

Since `rawtherapee-cli` doesn't work on macOS, use Docker:

```bash
# Using docker compose directly
INPUT_DIR=/path/to/images OUTPUT_DIR=/path/to/output docker compose run rawtherapee-shell

# Using the wrapper script
./run-docker.sh -i /path/to/images -o /path/to/output -s rawtherapee-shell

# Run rawtherapee-cli on all files
./run-docker.sh -i ~/Photos/raw -o ~/Photos/processed -s rawtherapee

# Run timelapse interpolation
./run-docker.sh -i ~/Photos/timelapse -s timelapse
```

## Requirements

- Python 3.8+
- RawTherapee (for editing keyframes)
- NEF files with corresponding PP3 keyframes
- Docker (for macOS users)