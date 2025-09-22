"""
Simple Timelapse PP3 Interpolator with Zoom Effects
"""

import configparser
import copy
import shutil
from datetime import datetime
from pathlib import Path
from typing import Tuple

import click


class CaseSensitiveConfigParser(configparser.RawConfigParser):
    """ConfigParser that preserves case for keys"""

    def optionxform(self, optionstr):
        return optionstr


class SimpleInterpolator:
    """PP3 interpolator with zoom and aspect ratio effects"""

    # Validation ranges
    TEMP_RANGE = (2000, 10000)
    GREEN_RANGE = (0.1, 2.0)
    COMP_RANGE = (-5.0, 5.0)

    # Common video resolutions
    RESOLUTIONS = {
        "1080p": (1920, 1080),
        "2k": (2048, 1152),
        "4k": (3840, 2160),
        "5k": (5120, 2880),
        "6k": (6144, 3456),
        "8k": (7680, 4320),
    }

    def __init__(
        self,
        directory: Path,
        dry_run: bool = False,
        backup: bool = True,
        aspect_drift: str = "center",
        zoom_level: str = "100-100",
        zoom_anchor: str = "center",
        zoom_easing: str = "linear",
        output: str = "4k",
    ):
        self.directory = directory
        self.dry_run = dry_run
        self.backup = backup
        self.aspect_drift = aspect_drift
        self.zoom_anchor = zoom_anchor
        self.zoom_easing = zoom_easing

        # Parse output resolution
        if output in self.RESOLUTIONS:
            self.output_width, self.output_height = self.RESOLUTIONS[output]
        else:
            click.echo(f"Error: Unknown resolution '{output}', using 4K")
            self.output_width, self.output_height = self.RESOLUTIONS["4k"]

        # Parse zoom level range
        parts = zoom_level.split("-")
        if len(parts) == 2:
            self.zoom_start = float(parts[0]) / 100.0
            self.zoom_end = float(parts[1]) / 100.0
        else:
            # Single value means no zoom
            self.zoom_start = self.zoom_end = float(parts[0]) / 100.0

    def get_image_dimensions(
        self, config: configparser.RawConfigParser
    ) -> Tuple[int, int]:
        """Extract original image dimensions from PP3 file"""
        try:
            # First, check if we have stored original dimensions
            if hasattr(self, "_original_width") and hasattr(self, "_original_height"):
                return self._original_width, self._original_height

            # If crop is disabled, W and H are the full image dimensions
            crop_enabled = (
                config.get("Crop", "Enabled", fallback="false").lower() == "true"
            )
            width = config.getint("Crop", "W")
            height = config.getint("Crop", "H")

            if not crop_enabled:
                # Store original dimensions for future use
                self._original_width = width
                self._original_height = height
                return width, height

            # If crop is enabled, we need to estimate the original dimensions
            # For now, use common Nikon Z6 dimensions
            click.echo(
                "Warning: Crop is enabled in keyframe, using default dimensions. "
                "For best results, disable crop in the first keyframe."
            )
            self._original_width = 6056
            self._original_height = 4032
            return 6056, 4032
        except:
            # Default to common Nikon Z6 dimensions if not found
            click.echo(
                "Warning: Could not read image dimensions from PP3, using defaults"
            )
            self._original_width = 6056
            self._original_height = 4032
            return 6056, 4032

    def apply_easing(self, t: float, easing: str) -> float:
        """Apply easing function to progress value"""
        if easing == "linear":
            return t
        elif easing == "ease-in":
            # Quadratic ease-in (slow start)
            return t * t
        elif easing == "ease-out":
            # Quadratic ease-out (slow end)
            return 1 - (1 - t) * (1 - t)
        elif easing == "ease-in-out":
            return self.ease_cubic(t)
        elif easing == "exponential":
            # Exponential ease-in-out
            if t <= 0:
                return 0.0
            elif t >= 1:
                return 1.0
            elif t < 0.5:
                return 0.5 * (2 ** (20 * t - 10))
            else:
                return 1 - 0.5 * (2 ** (-20 * t + 10))
        else:
            return t

    def calculate_zoom_factor(self, progress: float) -> float:
        """Calculate zoom factor based on progress and settings"""
        # No zoom if start and end are the same
        if self.zoom_start == self.zoom_end:
            return 1.0

        # Apply easing to progress
        eased_progress = self.apply_easing(progress, self.zoom_easing)

        # Interpolate between start and end field of view percentage
        current_fov = (
            self.zoom_start + (self.zoom_end - self.zoom_start) * eased_progress
        )

        # Return the field of view as a factor (1.0 = 100% = full view, 0.7 = 70% = zoomed in)
        return current_fov

    def calculate_16_9_crop(
        self, width: int, height: int, drift_mode: str, progress: float = 0.0
    ) -> Tuple[int, int, int, int]:
        """Calculate 16:9 crop from any aspect ratio image.

        Args:
            width: Original image width
            height: Original image height
            drift_mode: How to position the crop ('center', 'top', 'bottom', 'top-to-bottom', 'bottom-to-top')
            progress: Progress through the sequence (0.0 to 1.0) for animated drift

        Returns:
            Tuple of (x, y, crop_width, crop_height) for the 16:9 crop
        """
        # Calculate 16:9 dimensions
        target_height = int(width * 9 / 16)

        # If image is already wider than 16:9, crop width instead
        if height < target_height:
            crop_width = int(height * 16 / 9)
            crop_height = height
        else:
            crop_width = width
            crop_height = target_height

        # Horizontal position is always centered
        crop_x = (width - crop_width) // 2

        # Calculate vertical position based on drift mode
        available_drift = height - crop_height

        if drift_mode == "center":
            crop_y = available_drift // 2
        elif drift_mode == "top":
            crop_y = 0
        elif drift_mode == "bottom":
            crop_y = available_drift
        elif drift_mode == "top-to-bottom":
            # Start at top, drift to bottom over time
            crop_y = int(available_drift * progress)
        elif drift_mode == "bottom-to-top":
            # Start at bottom, drift to top over time
            crop_y = int(available_drift * (1 - progress))
        else:
            crop_y = available_drift // 2

        return crop_x, crop_y, crop_width, crop_height

    def apply_zoom_to_crop(
        self,
        crop_x: int,
        crop_y: int,
        crop_width: int,
        crop_height: int,
        original_width: int,
        original_height: int,
        fov_factor: float,
        anchor: str,
    ) -> Tuple[int, int, int, int]:
        """Apply zoom effect to an existing crop.

        Args:
            crop_x, crop_y, crop_width, crop_height: Current crop parameters
            original_width, original_height: Original image dimensions
            fov_factor: Field of view factor (1.0 = 100%, 0.8 = 80%)
            anchor: Zoom anchor point ('center', 'top', 'bottom')

        Returns:
            Tuple of (x, y, width, height) for the zoomed crop
        """
        # Calculate new crop size based on FOV
        new_crop_width = int(crop_width * fov_factor)
        new_crop_height = int(crop_height * fov_factor)

        # Calculate position based on anchor
        if anchor == "top":
            new_crop_x = crop_x + (crop_width - new_crop_width) // 2
            new_crop_y = crop_y
        elif anchor == "bottom":
            new_crop_x = crop_x + (crop_width - new_crop_width) // 2
            new_crop_y = crop_y + (crop_height - new_crop_height)
        else:  # center
            new_crop_x = crop_x + (crop_width - new_crop_width) // 2
            new_crop_y = crop_y + (crop_height - new_crop_height) // 2

        # Ensure crop stays within image bounds
        new_crop_x = max(0, min(original_width - new_crop_width, new_crop_x))
        new_crop_y = max(0, min(original_height - new_crop_height, new_crop_y))

        return new_crop_x, new_crop_y, new_crop_width, new_crop_height

    def calculate_aspect_crop(
        self, original_width: int, original_height: int, progress: float
    ) -> Tuple[int, int, int, int]:
        """Calculate crop parameters for 16:9 aspect ratio with drift and zoom"""

        # Stage 1: Calculate 16:9 crop with aspect drift
        crop_x, crop_y, crop_width, crop_height = self.calculate_16_9_crop(
            original_width, original_height, self.aspect_drift, progress
        )

        # Stage 2: Apply zoom effect if needed
        if self.zoom_start != self.zoom_end:
            fov_factor = self.calculate_zoom_factor(progress)
            # When zooming, zoom anchor takes precedence over aspect drift for positioning
            anchor = self.zoom_anchor if self.zoom_anchor != "center" else "center"
            crop_x, crop_y, crop_width, crop_height = self.apply_zoom_to_crop(
                crop_x,
                crop_y,
                crop_width,
                crop_height,
                original_width,
                original_height,
                fov_factor,
                anchor,
            )

        return crop_x, crop_y, crop_width, crop_height

    def parse_pp3(
        self, path: Path
    ) -> Tuple[configparser.RawConfigParser, float, float, float]:
        """Parse PP3 file and validate values"""
        config = CaseSensitiveConfigParser()
        config.read(path, encoding="utf-8")

        try:
            temp = config.getint("White Balance", "Temperature")
        except (configparser.NoSectionError, configparser.NoOptionError):
            temp = 5500  # Default temperature

        try:
            green = config.getfloat("White Balance", "Green")
        except (configparser.NoSectionError, configparser.NoOptionError):
            green = 1.0  # Default green

        try:
            comp = config.getfloat("Exposure", "Compensation")
        except (configparser.NoSectionError, configparser.NoOptionError):
            comp = 0.0  # Default compensation

        # Validate
        if not self.TEMP_RANGE[0] <= temp <= self.TEMP_RANGE[1]:
            click.echo(f"Warning: {path.name}: Temperature {temp}K outside range")
        if not self.GREEN_RANGE[0] <= green <= self.GREEN_RANGE[1]:
            click.echo(f"Warning: {path.name}: Green {green} outside range")
        if not self.COMP_RANGE[0] <= comp <= self.COMP_RANGE[1]:
            click.echo(f"Warning: {path.name}: Compensation {comp} outside range")

        return config, temp, green, comp

    def ease_cubic(self, t: float) -> float:
        """Smooth cubic ease-in-out: 3t² - 2t³"""
        return 3 * t * t - 2 * t * t * t

    def clamp(self, val: float, min_val: float, max_val: float) -> float:
        """Clamp value to range"""
        return max(min_val, min(max_val, val))

    def backup_pp3_files(self) -> None:
        """Backup existing PP3 files"""
        if self.dry_run or not self.backup:
            return

        pp3_files = list(self.directory.glob("*.pp3"))
        if not pp3_files:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.directory / f"rawtherapee-timelapse_{timestamp}"
        backup_dir.mkdir(exist_ok=True)

        click.echo(f"Backing up {len(pp3_files)} PP3 files to {backup_dir.name}/")
        for pp3 in pp3_files:
            shutil.copy2(pp3, backup_dir / pp3.name)

    def write_pp3(
        self,
        config: configparser.RawConfigParser,
        temp: float,
        green: float,
        comp: float,
        path: Path,
        frame_index: int,
        total_frames: int,
    ) -> configparser.RawConfigParser:
        """Write PP3 file with interpolated values and crop settings"""

        new_config = copy.deepcopy(config)

        # Set white balance and exposure
        new_config.set("White Balance", "Temperature", str(int(temp)))
        new_config.set("White Balance", "Green", f"{green:.3f}")
        new_config.set("Exposure", "Compensation", f"{comp:.3f}")

        # Calculate and set crop parameters
        progress = frame_index / (total_frames - 1) if total_frames > 1 else 0
        width, height = self.get_image_dimensions(config)
        crop_x, crop_y, crop_w, crop_h = self.calculate_aspect_crop(
            width, height, progress
        )

        # Update Crop section
        if not new_config.has_section("Crop"):
            new_config.add_section("Crop")

        new_config.set("Crop", "Enabled", "true")
        new_config.set("Crop", "X", str(crop_x))
        new_config.set("Crop", "Y", str(crop_y))
        new_config.set("Crop", "W", str(crop_w))
        new_config.set("Crop", "H", str(crop_h))
        new_config.set("Crop", "FixedRatio", "true")
        new_config.set("Crop", "Ratio", "16:9")
        new_config.set("Crop", "Orientation", "As Image")
        new_config.set("Crop", "Guide", "Frame")

        # Update Resize section for output resolution
        if not new_config.has_section("Resize"):
            new_config.add_section("Resize")

        new_config.set("Resize", "Enabled", "true")
        new_config.set("Resize", "Scale", "1")
        new_config.set("Resize", "AppliesTo", "Cropped area")
        new_config.set("Resize", "Method", "Lanczos")
        new_config.set("Resize", "DataSpecified", "3")
        new_config.set("Resize", "Width", str(self.output_width))
        new_config.set("Resize", "Height", str(self.output_height))
        new_config.set(
            "Resize", "LongEdge", str(max(self.output_width, self.output_height))
        )
        new_config.set(
            "Resize", "ShortEdge", str(min(self.output_width, self.output_height))
        )

        if self.dry_run:
            if self.zoom_start != self.zoom_end:
                fov_factor = self.calculate_zoom_factor(progress)
                fov_percentage = int(fov_factor * 100)
                zoom_info = f" FOV={fov_percentage}%"
            else:
                zoom_info = ""
            click.echo(
                f"  [DRY] {path.name}: T={int(temp)} G={green:.3f} C={comp:+.2f} "
                f"Crop=[{crop_x},{crop_y},{crop_w}x{crop_h}]{zoom_info}"
            )
        else:
            with open(path, "w", encoding="utf-8") as f:
                new_config.write(f)

        return new_config

    def process(self) -> None:
        """Main processing"""
        # Get files
        nef_files = sorted(self.directory.glob("*.NEF"))
        pp3_files = sorted(self.directory.glob("*.NEF.pp3"))

        if not nef_files:
            click.echo("Error: No NEF files found")
            return
        if not pp3_files:
            click.echo("Error: No PP3 keyframes found")
            return

        click.echo(f"Found {len(nef_files)} NEF files, {len(pp3_files)} keyframes")
        click.echo(f"Output resolution: {self.output_width}x{self.output_height}")
        click.echo(f"Aspect drift mode: {self.aspect_drift}")
        if self.zoom_start != self.zoom_end:
            zoom_info = f"{int(self.zoom_start * 100)}-{int(self.zoom_end * 100)}%"
            click.echo(
                f"Zoom: {zoom_info}, anchor: {self.zoom_anchor}, easing: {self.zoom_easing}"
            )

        # Backup
        self.backup_pp3_files()

        # Load keyframes
        keyframes = []
        nef_to_idx = {f.name: i for i, f in enumerate(nef_files)}

        for pp3 in pp3_files:
            nef_name = pp3.name[:-4]  # Remove .pp3
            if nef_name in nef_to_idx:
                try:
                    cfg, t, g, c = self.parse_pp3(pp3)
                    # Apply crop to keyframe PP3 files
                    frame_idx = nef_to_idx[nef_name]
                    progress = (
                        frame_idx / (len(nef_files) - 1) if len(nef_files) > 1 else 0
                    )
                    updated_cfg = self.write_pp3(
                        cfg, t, g, c, pp3, frame_idx, len(nef_files)
                    )
                    keyframes.append(
                        {
                            "idx": frame_idx,
                            "cfg": updated_cfg,
                            "temp": t,
                            "green": g,
                            "comp": c,
                        }
                    )
                except Exception as e:
                    click.echo(f"Error parsing {pp3.name}: {e}")

        if not keyframes:
            click.echo("Error: No valid keyframes")
            return

        keyframes.sort(key=lambda k: k["idx"])

        # Get image dimensions from first keyframe
        first_width, first_height = self.get_image_dimensions(keyframes[0]["cfg"])
        click.echo(f"Image dimensions: {first_width}x{first_height}")

        # Calculate 16:9 crop info
        target_height = int(first_width * 9 / 16)
        height_loss = first_height - target_height
        click.echo(
            f"16:9 crop: {first_width}x{target_height} (losing {height_loss}px height)"
        )

        click.echo("\nKeyframes:")
        for kf in keyframes:
            click.echo(
                f"   Frame {kf['idx']:4d}: T={kf['temp']} G={kf['green']:.3f} C={kf['comp']:+.2f}"
            )

        # Process each frame
        created = 0
        total_frames = len(nef_files)
        click.echo(
            f"\n{'Processing...' if not self.dry_run else 'Dry run processing...'}"
        )

        for i, nef in enumerate(nef_files):
            pp3_path = nef.parent / f"{nef.name}.pp3"

            # Skip existing
            if pp3_path.exists():
                continue

            # Find surrounding keyframes
            prev_kf = next((kf for kf in reversed(keyframes) if kf["idx"] <= i), None)
            next_kf = next((kf for kf in keyframes if kf["idx"] >= i), None)

            if prev_kf and next_kf and prev_kf != next_kf:
                # Interpolate between keyframes
                span = next_kf["idx"] - prev_kf["idx"]
                pos = (i - prev_kf["idx"]) / span

                # Apply easing
                pos = self.ease_cubic(pos)

                # Interpolate values
                temp = prev_kf["temp"] + (next_kf["temp"] - prev_kf["temp"]) * pos
                green = prev_kf["green"] + (next_kf["green"] - prev_kf["green"]) * pos
                comp = prev_kf["comp"] + (next_kf["comp"] - prev_kf["comp"]) * pos
                cfg = prev_kf["cfg"]
            elif prev_kf:
                # After last keyframe
                temp, green, comp, cfg = (
                    prev_kf["temp"],
                    prev_kf["green"],
                    prev_kf["comp"],
                    prev_kf["cfg"],
                )
            elif next_kf:
                # Before first keyframe
                temp, green, comp, cfg = (
                    next_kf["temp"],
                    next_kf["green"],
                    next_kf["comp"],
                    next_kf["cfg"],
                )
            else:
                continue

            # Clamp values
            temp = self.clamp(temp, *self.TEMP_RANGE)
            green = self.clamp(green, *self.GREEN_RANGE)
            comp = self.clamp(comp, *self.COMP_RANGE)

            # Write file with crop settings
            self.write_pp3(cfg, temp, green, comp, pp3_path, i, total_frames)
            created += 1

            if created % 100 == 0 and not self.dry_run:
                click.echo(f"   Progress: {created} files...")

        click.echo(f"\nDone! Created {created} PP3 files with 16:9 crop")
        if self.dry_run:
            click.echo("   (This was a dry run - no files created)")


@click.command()
@click.argument(
    "directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
)
@click.option("--dry-run", "-d", is_flag=True, help="Preview without creating files")
@click.option(
    "--backup/--no-backup",
    "-b/-B",
    default=True,
    help="Backup existing PP3 files (default: backup)",
)
@click.option(
    "--aspect-drift",
    type=click.Choice(["center", "top", "bottom", "top-to-bottom", "bottom-to-top"]),
    default="center",
    help="How to crop from 3:2 to 16:9 aspect ratio",
)
@click.option(
    "--zoom-level",
    type=str,
    default="100-100",
    help="Field of view percentage range (e.g., '100-70' for zoom in, '80-100' for zoom out). 100 = full view, <100 = cropped/zoomed",
)
@click.option(
    "--zoom-anchor",
    type=click.Choice(["center", "top", "bottom"]),
    default="center",
    help="Anchor point for zoom effect",
)
@click.option(
    "--zoom-easing",
    type=click.Choice(["linear", "ease-in-out", "exponential"]),
    default="linear",
    help="Easing function for zoom effect",
)
@click.option(
    "--output",
    type=click.Choice(["1080p", "2k", "4k", "5k", "6k", "8k"]),
    default="4k",
    help="Output resolution (all maintain 16:9 aspect ratio)",
)
def main(
    directory: Path,
    dry_run: bool,
    backup: bool,
    aspect_drift: str,
    zoom_level: str,
    zoom_anchor: str,
    zoom_easing: str,
    output: str,
):
    """
    Interpolate RawTherapee PP3 settings for timelapse sequences with zoom effects.

    This tool creates smooth transitions between keyframe PP3 files by interpolating
    Temperature, Green/Tint, and Exposure values. It also crops images to 16:9 aspect
    ratio for 4K video output with optional zoom effects.

    Aspect drift modes:

    \b
    - center:         Always crop equally from top and bottom
    - top:            Keep top, crop bottom only
    - bottom:         Keep bottom, crop top only
    - top-to-bottom:  Start at top, drift to bottom
    - bottom-to-top:  Start at bottom, drift to top

    Output resolutions:

    \b
    - 1080p: 1920x1080 (Full HD)
    - 2k:    2048x1152 (2K DCI)
    - 4k:    3840x2160 (4K UHD) - default
    - 5k:    5120x2880 (5K)
    - 6k:    6144x3456 (6K)
    - 8k:    7680x4320 (8K UHD)

    Examples:

        # Preview with center crop at 4K
        python interpolate_simple.py --dry-run

        # Create dramatic sunrise effect in 1080p
        python interpolate_simple.py --aspect-drift bottom-to-top --output 1080p

        # Process for 8K output
        python interpolate_simple.py /path/to/images --output 8k

        # Add zoom in effect from 100% view to 70% view for 5K
        python interpolate_simple.py --zoom-level 100-70 --output 5k

        # Zoom out with exponential easing, anchored at top, 4K output
        python interpolate_simple.py --zoom-level 80-100 --zoom-anchor top --zoom-easing exponential
    """
    interpolator = SimpleInterpolator(
        directory,
        dry_run,
        backup,
        aspect_drift,
        zoom_level,
        zoom_anchor,
        zoom_easing,
        output,
    )
    interpolator.process()


if __name__ == "__main__":
    main()
