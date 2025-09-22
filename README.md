# RawTherapee Timelapse

A Python tool for creating smooth timelapse sequences by interpolating RawTherapee PP3 settings between keyframes. This tool helps create professional-looking timelapses with smooth transitions in exposure, white balance, and color grading, along with zoom and aspect ratio effects.

## Features

- **Smooth Interpolation**: Interpolates Temperature, Green/Tint, and Exposure Compensation between keyframe PP3 files
- **Automatic 16:9 Crop**: Crops images to 16:9 aspect ratio for video output
- **Zoom Effects**: Add zoom in/out effects with customizable easing functions
- **Aspect Drift**: Control how the 16:9 crop moves through the frame during the timelapse
- **Multiple Output Resolutions**: Support for 1080p, 2K, 4K, 5K, 6K, and 8K output
- **Batch Processing**: Processes entire directories of NEF files
- **Backup System**: Automatically backs up existing PP3 files before processing

## Installation

### Using pip

```bash
pip install rawtherapee-timelapse
```

### From source

```bash
git clone <repository>
cd timelapse
pip install -e .
```

## Usage

### Basic Usage

```bash
# Process current directory with default settings (4K output, center crop)
rawtherapee-timelapse

# Preview what will be created without making changes
rawtherapee-timelapse --dry-run

# Process a specific directory
rawtherapee-timelapse /path/to/images
```

### Zoom Effects

```bash
# Zoom in from 80% to 100% during the timelapse
rawtherapee-timelapse --zoom in --zoom-level 80-100

# Zoom out with exponential easing, anchored at top
rawtherapee-timelapse --zoom out --zoom-level 70-100 --zoom-anchor top --zoom-easing exponential

# Combine zoom with aspect drift for complex motion
rawtherapee-timelapse --zoom in --zoom-level 90-100 --aspect-drift bottom-to-top
```

### Aspect Drift Options

Control how the 16:9 crop moves through the frame:

- `center`: Always crop equally from top and bottom (default)
- `top`: Keep top of frame, crop bottom only
- `bottom`: Keep bottom of frame, crop top only
- `top-to-bottom`: Start at top, drift to bottom during timelapse
- `bottom-to-top`: Start at bottom, drift to top during timelapse

```bash
# Create dramatic sunrise effect by drifting from bottom to top
rawtherapee-timelapse --aspect-drift bottom-to-top

# Keep the horizon stable by using top drift
rawtherapee-timelapse --aspect-drift top
```

### Output Resolutions

All output resolutions maintain 16:9 aspect ratio:

- `1080p`: 1920×1080 (Full HD)
- `2k`: 2048×1152 (2K DCI)
- `4k`: 3840×2160 (4K UHD) - default
- `5k`: 5120×2880 (5K)
- `6k`: 6144×3456 (6K)
- `8k`: 7680×4320 (8K UHD)

```bash
# Export for 1080p video
rawtherapee-timelapse --output 1080p

# Process for 8K output
rawtherapee-timelapse --output 8k
```

### Complete Example

```bash
# Create a sunset timelapse with zoom out effect in 5K resolution
rawtherapee-timelapse \
    --zoom out \
    --zoom-level 70-100 \
    --zoom-anchor center \
    --zoom-easing ease-in-out \
    --aspect-drift top-to-bottom \
    --output 5k
```

## How It Works

1. **Keyframe Detection**: The tool identifies existing PP3 files in your directory as keyframes
2. **Value Extraction**: Extracts Temperature, Green/Tint, and Exposure Compensation from each keyframe
3. **Interpolation**: Creates smooth transitions between keyframes using cubic easing
4. **Crop Calculation**: Applies 16:9 crop with optional drift and zoom effects
5. **Resize Configuration**: Sets up proper dimensions for your chosen output resolution
6. **File Generation**: Creates PP3 files for all frames that don't already have them

## Workflow

1. Import your RAW files (NEF) into RawTherapee
2. Create keyframes by editing a few images throughout your sequence and saving their PP3 files
3. Run `rawtherapee-timelapse` in the directory containing your files
4. Process all images in RawTherapee using the generated PP3 files
5. Export as JPG or TIF for video compilation

## Requirements

- Python 3.12 or higher
- RawTherapee (for processing the images)
- NEF files with at least 2 keyframe PP3 files

## Tips

- Create keyframes at important moments (sunrise/sunset, weather changes, etc.)
- Use zoom effects subtly (5-20% range) for best results
- Test with `--dry-run` first to preview the effects
- The tool preserves existing PP3 settings from keyframes (like lens corrections, noise reduction, etc.)

## License

See LICENSE file for details.