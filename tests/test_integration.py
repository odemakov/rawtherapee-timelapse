import shutil
import tempfile
from pathlib import Path


from rawtherapee_timelapse.cli import SimpleInterpolator


class TestIntegration:
    """Integration tests for the full workflow"""

    def setup_method(self):
        """Create temp directory and test files"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_dir = Path(self.temp_dir) / "test_images"
        self.test_dir.mkdir()

    def teardown_method(self):
        """Clean up temp directory"""
        shutil.rmtree(self.temp_dir)

    def create_test_files(self, num_images=10):
        """Create test NEF and PP3 files"""
        # Create NEF files (just empty files for testing)
        nef_files = []
        for i in range(num_images):
            nef_file = self.test_dir / f"DSC_{i:04d}.NEF"
            nef_file.touch()
            nef_files.append(nef_file)

        return nef_files

    def create_keyframe_pp3(self, nef_file: Path, temp=5500, green=1.0, comp=0.0):
        """Create a PP3 file for a keyframe"""
        pp3_file = nef_file.with_suffix(".NEF.pp3")
        content = f"""[Version]
AppVersion=5.8
Version=342

[White Balance]
Setting=Custom
Temperature={int(temp)}
Green={green}

[Exposure]
Compensation={comp}

[Crop]
Enabled=false
X=0
Y=0
W=6056
H=4032
"""
        pp3_file.write_text(content)
        return pp3_file

    def test_simple_interpolation(self):
        """Test basic interpolation between two keyframes"""
        # Create test files
        nef_files = self.create_test_files(5)

        # Create keyframes at start and end
        self.create_keyframe_pp3(nef_files[0], temp=5000, green=0.8, comp=-1.0)
        self.create_keyframe_pp3(nef_files[4], temp=7000, green=1.2, comp=1.0)

        # Run interpolation
        interpolator = SimpleInterpolator(
            directory=self.test_dir,
            dry_run=False,
            backup=False,
        )
        interpolator.process()

        # Check that PP3 files were created for all images
        for nef_file in nef_files:
            pp3_file = nef_file.with_suffix(".NEF.pp3")
            assert pp3_file.exists()

        # Verify interpolated values for middle frame
        import configparser

        middle_pp3 = nef_files[2].with_suffix(".NEF.pp3")
        config = configparser.ConfigParser()
        config.read(middle_pp3)

        # Should be halfway between keyframe values
        assert int(config.get("White Balance", "Temperature")) == 6000
        assert float(config.get("White Balance", "Green")) == 1.0
        assert float(config.get("Exposure", "Compensation")) == 0.0

    def test_zoom_and_drift_integration(self):
        """Test integration of zoom and aspect drift"""
        # Create test files
        nef_files = self.create_test_files(5)
        self.create_keyframe_pp3(nef_files[0])

        # Run with zoom and drift
        interpolator = SimpleInterpolator(
            directory=self.test_dir,
            dry_run=False,
            backup=False,
            zoom_level="100-80",  # Zoom in
            aspect_drift="bottom-to-top",
            output="1080p",
        )
        interpolator.process()

        # Check first and last frames
        import configparser

        # First frame (100% FOV, bottom drift)
        first_pp3 = nef_files[0].with_suffix(".NEF.pp3")
        config = configparser.ConfigParser()
        config.read(first_pp3)
        assert config.get("Crop", "Enabled") == "true"
        crop_y_first = int(config.get("Crop", "Y"))

        # Last frame (80% FOV, top drift)
        last_pp3 = nef_files[4].with_suffix(".NEF.pp3")
        config = configparser.ConfigParser()
        config.read(last_pp3)
        crop_y_last = int(config.get("Crop", "Y"))
        crop_w_last = int(config.get("Crop", "W"))
        crop_h_last = int(config.get("Crop", "H"))

        # Verify drift (Y should decrease)
        assert crop_y_last < crop_y_first

        # Verify zoom (crop dimensions should be smaller)
        assert crop_w_last < 6056
        assert crop_h_last < 3406

        # Verify output resolution
        assert int(config.get("Resize", "Width")) == 1920
        assert int(config.get("Resize", "Height")) == 1080

    def test_multiple_keyframes(self):
        """Test interpolation with multiple keyframes"""
        # Create test files
        nef_files = self.create_test_files(10)

        # Create keyframes at start, middle, and end
        self.create_keyframe_pp3(nef_files[0], temp=5000, green=0.8, comp=-1.0)
        self.create_keyframe_pp3(nef_files[4], temp=6500, green=1.0, comp=0.5)
        self.create_keyframe_pp3(nef_files[9], temp=7000, green=1.2, comp=1.0)

        # Run interpolation
        interpolator = SimpleInterpolator(
            directory=self.test_dir,
            dry_run=False,
            backup=False,
        )
        interpolator.process()

        # Check frame 2 (between first and second keyframe)
        import configparser

        pp3_2 = nef_files[2].with_suffix(".NEF.pp3")
        config = configparser.ConfigParser()
        config.read(pp3_2)

        temp = int(config.get("White Balance", "Temperature"))
        assert 5000 < temp < 6500  # Should be between first two keyframes

    def test_dry_run(self):
        """Test that dry run doesn't create files"""
        # Create test files
        nef_files = self.create_test_files(3)
        self.create_keyframe_pp3(nef_files[0])

        # Run in dry-run mode
        interpolator = SimpleInterpolator(
            directory=self.test_dir,
            dry_run=True,
        )
        interpolator.process()

        # Check that no new PP3 files were created
        pp3_count = len(list(self.test_dir.glob("*.pp3")))
        assert pp3_count == 1  # Only the keyframe

    def test_backup_creation(self):
        """Test that backups are created when overwriting"""
        # Create test files
        nef_files = self.create_test_files(2)

        # Create existing PP3 for all files
        for nef in nef_files:
            self.create_keyframe_pp3(nef, temp=5000)

        # Run with backup enabled
        interpolator = SimpleInterpolator(
            directory=self.test_dir,
            dry_run=False,
            backup=True,
        )
        interpolator.process()

        # Check that backup was created
        backup_dirs = list(self.test_dir.glob("rawtherapee-timelapse_*"))
        assert len(backup_dirs) == 1

        # Check that PP3 files were backed up in the directory
        backup_dir = backup_dirs[0]
        backup_files = list(backup_dir.glob("*.pp3"))
        assert len(backup_files) == 2

    def test_no_keyframes_error(self):
        """Test that process fails gracefully with no keyframes"""
        # Create only NEF files, no PP3
        self.create_test_files(5)

        interpolator = SimpleInterpolator(
            directory=self.test_dir,
            dry_run=False,
        )

        # Should handle gracefully
        interpolator.process()  # Should print error message

    def test_single_keyframe(self):
        """Test with only one keyframe (all frames get same values)"""
        # Create test files
        nef_files = self.create_test_files(5)

        # Create only one keyframe
        self.create_keyframe_pp3(nef_files[2], temp=6000, green=1.1, comp=0.5)

        # Run interpolation
        interpolator = SimpleInterpolator(
            directory=self.test_dir,
            dry_run=False,
            backup=False,
        )
        interpolator.process()

        # All frames should have the same values
        import configparser

        for nef in nef_files:
            pp3 = nef.with_suffix(".NEF.pp3")
            config = configparser.ConfigParser()
            config.read(pp3)

            assert int(config.get("White Balance", "Temperature")) == 6000
            assert float(config.get("White Balance", "Green")) == 1.1
            assert float(config.get("Exposure", "Compensation")) == 0.5

    def test_different_output_resolutions(self):
        """Test different output resolution settings"""
        resolutions = {
            "1080p": (1920, 1080),
            "2k": (2048, 1152),
            "4k": (3840, 2160),
            "5k": (5120, 2880),
            "6k": (6144, 3456),
            "8k": (7680, 4320),
        }

        for res_name, (width, height) in resolutions.items():
            # Create test files
            nef_files = self.create_test_files(1)
            self.create_keyframe_pp3(nef_files[0])

            # Run with specific resolution
            interpolator = SimpleInterpolator(
                directory=self.test_dir,
                dry_run=False,
                backup=False,
                output=res_name,
            )
            interpolator.process()

            # Check output resolution
            import configparser

            pp3 = nef_files[0].with_suffix(".NEF.pp3")
            config = configparser.ConfigParser()
            config.read(pp3)

            assert int(config.get("Resize", "Width")) == width
            assert int(config.get("Resize", "Height")) == height

            # Clean up for next iteration
            pp3.unlink()

    def test_easing_functions(self):
        """Test that different easing functions produce different results"""
        easing_types = ["linear", "ease-in", "ease-out", "ease-in-out", "exponential"]
        results = {}

        for easing in easing_types:
            # Create test files
            nef_files = self.create_test_files(3)
            self.create_keyframe_pp3(nef_files[0], temp=5000)
            self.create_keyframe_pp3(nef_files[2], temp=7000)

            # Run with specific easing
            interpolator = SimpleInterpolator(
                directory=self.test_dir,
                dry_run=False,
                backup=False,
                zoom_level="100-80",
                zoom_easing=easing,
            )
            interpolator.process()

            # Get middle frame crop
            import configparser

            pp3 = nef_files[1].with_suffix(".NEF.pp3")
            config = configparser.ConfigParser()
            config.read(pp3)
            crop_w = int(config.get("Crop", "W"))
            results[easing] = crop_w

            # Clean up
            for nef in nef_files:
                nef.unlink()
                pp3_file = nef.with_suffix(".NEF.pp3")
                if pp3_file.exists():
                    pp3_file.unlink()

        # Different easings should produce different results for middle frame
        # (except maybe some edge cases)
        unique_values = set(results.values())
        assert len(unique_values) >= 3  # At least 3 different values
