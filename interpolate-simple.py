#!/usr/bin/env python3
"""
Simple Timelapse PP3 Interpolator - No external dependencies
"""

import argparse
import configparser
import copy
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Tuple


class CaseSensitiveConfigParser(configparser.RawConfigParser):
    """ConfigParser that preserves case for keys"""

    def optionxform(self, optionstr):
        return optionstr


class SimpleInterpolator:
    """Lightweight PP3 interpolator without scipy dependency"""

    # Validation ranges
    TEMP_RANGE = (2000, 10000)
    GREEN_RANGE = (0.1, 2.0)
    COMP_RANGE = (-5.0, 5.0)

    def __init__(self, directory: Path, dry_run: bool = False, backup: bool = True):
        self.directory = directory
        self.dry_run = dry_run
        self.backup = backup

    def parse_pp3(
        self, path: Path
    ) -> Tuple[configparser.ConfigParser, float, float, float]:
        """Parse PP3 file and validate values"""
        config = CaseSensitiveConfigParser()
        config.read(path, encoding="utf-8")

        temp = config.getint("White Balance", "Temperature")
        green = config.getfloat("White Balance", "Green")
        comp = config.getfloat("Exposure", "Compensation")

        # Validate
        if not self.TEMP_RANGE[0] <= temp <= self.TEMP_RANGE[1]:
            print(f"⚠️  {path.name}: Temperature {temp}K outside range")
        if not self.GREEN_RANGE[0] <= green <= self.GREEN_RANGE[1]:
            print(f"⚠️  {path.name}: Green {green} outside range")
        if not self.COMP_RANGE[0] <= comp <= self.COMP_RANGE[1]:
            print(f"⚠️  {path.name}: Compensation {comp} outside range")

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

        print(f"📁 Backing up {len(pp3_files)} PP3 files to {backup_dir.name}/")
        for pp3 in pp3_files:
            shutil.copy2(pp3, backup_dir / pp3.name)

    def write_pp3(
        self,
        config: CaseSensitiveConfigParser,
        temp: float,
        green: float,
        comp: float,
        path: Path,
    ) -> None:
        """Write PP3 file with interpolated values"""
        if self.dry_run:
            print(f"  [DRY] {path.name}: T={int(temp)} G={green:.3f} C={comp:+.2f}")
            return

        new_config = copy.deepcopy(config)
        new_config.set("White Balance", "Temperature", str(int(temp)))
        new_config.set("White Balance", "Green", f"{green:.3f}")
        new_config.set("Exposure", "Compensation", f"{comp:.3f}")

        with open(path, "w", encoding="utf-8") as f:
            new_config.write(f)

    def process(self) -> None:
        """Main processing"""
        # Get files
        nef_files = sorted(self.directory.glob("*.NEF"))
        pp3_files = sorted(self.directory.glob("*.NEF.pp3"))

        if not nef_files:
            print("❌ No NEF files found")
            return
        if not pp3_files:
            print("❌ No PP3 keyframes found")
            return

        print(f"📸 Found {len(nef_files)} NEF files, {len(pp3_files)} keyframes")

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
                    keyframes.append(
                        {
                            "idx": nef_to_idx[nef_name],
                            "cfg": cfg,
                            "temp": t,
                            "green": g,
                            "comp": c,
                        }
                    )
                except Exception as e:
                    print(f"❌ Error parsing {pp3.name}: {e}")

        if not keyframes:
            print("❌ No valid keyframes")
            return

        keyframes.sort(key=lambda k: k["idx"])
        print("\n🔑 Keyframes:")
        for kf in keyframes:
            print(
                f"   Frame {kf['idx']:4d}: T={kf['temp']} G={kf['green']:.3f} C={kf['comp']:+.2f}"
            )

        # Process each frame
        created = 0
        print(f"\n{'🔄' if not self.dry_run else '👁️ '} Processing...")

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

            # Write file
            self.write_pp3(cfg, temp, green, comp, pp3_path)
            created += 1

            if created % 100 == 0 and not self.dry_run:
                print(f"   Progress: {created} files...")

        print(f"\n✅ Done! Created {created} PP3 files")
        if self.dry_run:
            print("   (This was a dry run - no files created)")


def main():
    parser = argparse.ArgumentParser(
        description="Simple PP3 interpolator for timelapses",
        epilog="Example: %(prog)s /path/to/timelapse --dry-run",
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Directory with NEF files (default: current)",
    )
    parser.add_argument(
        "-d", "--dry-run", action="store_true", help="Preview without creating files"
    )
    parser.add_argument(
        "-n",
        "--no-backup",
        dest="backup",
        action="store_false",
        help="Skip backup of existing PP3 files",
    )

    args = parser.parse_args()

    directory = Path(args.directory)
    if not directory.is_dir():
        print(f"❌ Error: {directory} is not a directory")
        sys.exit(1)

    interpolator = SimpleInterpolator(directory, args.dry_run, args.backup)
    interpolator.process()


if __name__ == "__main__":
    main()
