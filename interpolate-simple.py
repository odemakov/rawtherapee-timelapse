#!/usr/bin/env python3
"""
Simple Timelapse PP3 Interpolator with Zoom Effects
"""

import configparser
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

    def __init__(
        self,
        directory: Path,
        dry_run: bool = False,
        backup: bool = True,
        aspect_drift: str = "center",
    ):
        self.directory = directory
        self.dry_run = dry_run
        self.backup = backup
        self.aspect_drift = aspect_drift

    def get_image_dimensions(
        self, config: configparser.RawConfigParser
    ) -> Tuple[int, int]:
        """Extract image dimensions from PP3 Crop section"""
        try:
            # Get dimensions from Crop section
            width = config.getint("Crop", "W")
            height = config.getint("Crop", "H")
            return width, height
        except:
            # Default to common Nikon Z6 dimensions if not found
            click.echo(
                "Warning: Could not read image dimensions from PP3, using defaults"
            )
            return 6056, 4032

    def calculate_aspect_crop(
        self, original_width: int, original_height: int, progress: float
    ) -> Tuple[int, int, int, int]:
        """Calculate crop parameters for 16:9 aspect ratio with drift"""

        # Calculate 16:9 dimensions maintaining full width
        target_height = int(original_width * 9 / 16)

        # If original is already wider than 16:9, crop width instead
        if original_height < target_height:
            target_width = int(original_height * 16 / 9)
            target_height = original_height
            crop_x = (original_width - target_width) // 2
            crop_y = 0
            return crop_x, crop_y, target_width, target_height

        # Calculate vertical crop needed
        height_to_crop = original_height - target_height

        # Calculate Y offset based on aspect_drift
        if self.aspect_drift == "center":
            y_offset = height_to_crop // 2
        elif self.aspect_drift == "top":
            y_offset = 0
        elif self.aspect_drift == "bottom":
            y_offset = height_to_crop
        elif self.aspect_drift == "top-to-bottom":
            y_offset = int(height_to_crop * progress)
        elif self.aspect_drift == "bottom-to-top":
            y_offset = int(height_to_crop * (1 - progress))
        else:
            y_offset = height_to_crop // 2  # Default to center

        return 0, y_offset, original_width, target_height

    def parse_pp3(
        self, path: Path
    ) -> Tuple[configparser.RawConfigParser, float, float, float]:
        """Parse PP3 file and validate values"""
        config = CaseSensitiveConfigParser()
        config.read(path, encoding="utf-8")

        temp = config.getint("White Balance", "Temperature")
        green = config.getfloat("White Balance", "Green")
        comp = config.getfloat("Exposure", "Compensation")

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
        backup_dir = self.directory / f"pp3_backup_{timestamp}"
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
    ) -> None:
        """Write PP3 file with interpolated values and crop settings"""
        if self.dry_run:
            progress = frame_index / (total_frames - 1) if total_frames > 1 else 0
            width, height = self.get_image_dimensions(config)
            x, y, w, h = self.calculate_aspect_crop(width, height, progress)
            click.echo(
                f"  [DRY] {path.name}: T={int(temp)} G={green:.3f} C={comp:+.2f} "
                f"Crop=[{x},{y},{w}x{h}]"
            )
            return

        import copy

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

        with open(path, "w", encoding="utf-8") as f:
            new_config.write(f)

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
        click.echo(f"Aspect drift mode: {self.aspect_drift}")

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
                    self.write_pp3(cfg, t, g, c, pp3, frame_idx, len(nef_files))
                    keyframes.append(
                        {
                            "idx": frame_idx,
                            "cfg": cfg,
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
    default=".",
    required=False,
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
def main(directory: Path, dry_run: bool, backup: bool, aspect_drift: str):
    """
    Interpolate RawTherapee PP3 settings for timelapse sequences with zoom effects.

    This tool creates smooth transitions between keyframe PP3 files by interpolating
    Temperature, Green/Tint, and Exposure values. It also crops images to 16:9 aspect
    ratio for 4K video output.

    Aspect drift modes:

    \b
    - center:         Always crop equally from top and bottom
    - top:            Keep top, crop bottom only
    - bottom:         Keep bottom, crop top only
    - top-to-bottom:  Start at top, drift to bottom
    - bottom-to-top:  Start at bottom, drift to top

    Examples:

        # Preview with center crop
        python interpolate_simple.py --dry-run

        # Create dramatic sunrise effect
        python interpolate_simple.py --aspect-drift bottom-to-top

        # Process specific directory
        python interpolate_simple.py /path/to/images --aspect-drift top-to-bottom
    """
    interpolator = SimpleInterpolator(directory, dry_run, backup, aspect_drift)
    interpolator.process()


if __name__ == "__main__":
    main()
