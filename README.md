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

# Add zoom in effect (from 100% to 80% field of view)
rawtherapee-timelapse /path/to/images --zoom-level 100-80

# Complex example: 6K output with exponential zoom out anchored at top
rawtherapee-timelapse /path/to/images --output 6k --zoom-level 80-100 --zoom-anchor top --zoom-easing exponential
```

## Zoom Effects

The zoom feature creates Ken Burns effects by adjusting the field of view:

### Understanding Field of View

- **100%** = Full field of view (showing the entire image)
- **80%** = 80% field of view (cropped by 20%, zoomed in)
- **70%** = 70% field of view (cropped by 30%, more zoomed in)

### Zoom Direction

- **Zoom IN**: Start at higher percentage, end at lower (e.g., 100-70)
- **Zoom OUT**: Start at lower percentage, end at higher (e.g., 80-100)

### Examples

```bash
# Zoom in: Start showing full image (100%), end showing 70% (zoomed in)
rawtherapee-timelapse /path/to/images --zoom-level 100-70

# Zoom out: Start showing 80% of image (zoomed), end showing full image
rawtherapee-timelapse /path/to/images --zoom-level 80-100

# Dramatic zoom in from full view to half field of view
rawtherapee-timelapse /path/to/images --zoom-level 100-50

# Start zoomed in at 75%, return to full view
rawtherapee-timelapse /path/to/images --zoom-level 75-100
```

### Zoom Options

- `--zoom-level`: Field of view range (e.g., "100-70" or "80-100")
- `--zoom-anchor`: Where to anchor the zoom
  - `center`: Zoom from/to center (default)
  - `top`: Keep top fixed while zooming
  - `bottom`: Keep bottom fixed while zooming
- `--zoom-easing`: Speed curve for the zoom
  - `linear`: Constant speed (default)
  - `ease-in`: Start slow, speed up
  - `ease-out`: Start fast, slow down
  - `ease-in-out`: Slow at both ends
  - `exponential`: Accelerating effect

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