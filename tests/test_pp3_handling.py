import configparser
import tempfile
from pathlib import Path

from rawtherapee_timelapse.cli import CaseSensitiveConfigParser, SimpleInterpolator


class TestPP3Handling:
    """Test PP3 file parsing, interpolation, and writing"""

    def setup_method(self):
        """Create a SimpleInterpolator instance and temp directory for testing"""
        self.temp_dir = tempfile.mkdtemp()
        self.interpolator = SimpleInterpolator(
            directory=Path(self.temp_dir), dry_run=True
        )

    def teardown_method(self):
        """Clean up temp directory"""
        import shutil

        shutil.rmtree(self.temp_dir)

    def create_test_pp3(self, path: Path, temp=5500, green=1.0, comp=0.0):
        """Create a test PP3 file with given values"""
        content = f"""[Version]
AppVersion=5.8
Version=342

[Color Management]
InputProfile=(cameraICC)
ToneCurve=standard
ApplyLookTable=true
ApplyBaselineExposureOffset=true
ApplyHueSatMap=true

[Exposure]
Auto=false
Clip=0.02
Compensation={comp}
Brightness=0
Contrast=0
Saturation=0
Black=0
HighlightCompr=0
HighlightComprThreshold=0
ShadowCompr=50
CurveMode=Standard
CurveMode2=Standard

[White Balance]
Setting=Custom
Temperature={int(temp)}
Green={green}
Equal=1
TemperatureBias=0

[Crop]
Enabled=false
X=0
Y=0
W=6056
H=4032
FixedRatio=false
Ratio=3:2
Orientation=As Image
Guide=Frame
"""
        path.write_text(content)

    def test_parse_pp3(self):
        """Test parsing PP3 file values"""
        pp3_path = Path(self.temp_dir) / "test.pp3"
        self.create_test_pp3(pp3_path, temp=7000, green=1.5, comp=0.65)

        config, temp, green, comp = self.interpolator.parse_pp3(pp3_path)

        assert temp == 7000
        assert green == 1.5
        assert comp == 0.65
        assert isinstance(config, CaseSensitiveConfigParser)

    def test_parse_pp3_missing_values(self):
        """Test parsing PP3 with missing values uses defaults"""
        pp3_path = Path(self.temp_dir) / "minimal.pp3"
        pp3_path.write_text("[Version]\nVersion=342\n")

        config, temp, green, comp = self.interpolator.parse_pp3(pp3_path)

        # Should use defaults
        assert temp == 5500
        assert green == 1.0
        assert comp == 0.0

    # Note: The interpolate_value method doesn't exist in the actual implementation
    # Interpolation is done inline in the process() method
    # These tests were removed as they test non-existent functionality

    def test_clamp_values(self):
        """Test that values are clamped to valid ranges"""
        # Temperature range: 2000-10000
        assert self.interpolator.clamp(1500, *self.interpolator.TEMP_RANGE) == 2000
        assert self.interpolator.clamp(5500, *self.interpolator.TEMP_RANGE) == 5500
        assert self.interpolator.clamp(15000, *self.interpolator.TEMP_RANGE) == 10000

        # Green range: 0.1-2.0
        assert self.interpolator.clamp(0.0, *self.interpolator.GREEN_RANGE) == 0.1
        assert self.interpolator.clamp(1.5, *self.interpolator.GREEN_RANGE) == 1.5
        assert self.interpolator.clamp(3.0, *self.interpolator.GREEN_RANGE) == 2.0

        # Compensation range: -5.0 to 5.0
        assert self.interpolator.clamp(-10.0, *self.interpolator.COMP_RANGE) == -5.0
        assert self.interpolator.clamp(0.0, *self.interpolator.COMP_RANGE) == 0.0
        assert self.interpolator.clamp(10.0, *self.interpolator.COMP_RANGE) == 5.0

    def test_case_sensitive_config(self):
        """Test that CaseSensitiveConfigParser preserves key case"""
        parser = CaseSensitiveConfigParser()
        parser.add_section("TestSection")
        parser.set("TestSection", "MixedCase", "value")
        parser.set("TestSection", "UPPERCASE", "value")
        parser.set("TestSection", "lowercase", "value")

        # Keys should preserve case
        assert "MixedCase" in parser.options("TestSection")
        assert "UPPERCASE" in parser.options("TestSection")
        assert "lowercase" in parser.options("TestSection")

    def test_write_pp3(self):
        """Test writing PP3 with updated values"""
        # Create initial PP3
        pp3_path = Path(self.temp_dir) / "test.pp3"
        self.create_test_pp3(pp3_path, temp=5500, green=1.0, comp=0.0)

        # Parse it
        config, _, _, _ = self.interpolator.parse_pp3(pp3_path)

        # Write PP3 with interpolated values for frame 50
        output_path = Path(self.temp_dir) / "output.pp3"
        # Interpolate values manually for frame 50 out of 101
        progress = 50 / 100  # 0.5
        temp = 5000 + (7000 - 5000) * progress  # 6000
        green = 0.8 + (1.2 - 0.8) * progress  # 1.0
        comp = -1.0 + (1.0 - (-1.0)) * progress  # 0.0

        # Create a non-dry-run interpolator for this test
        write_interpolator = SimpleInterpolator(
            directory=Path(self.temp_dir), dry_run=False
        )
        write_interpolator.write_pp3(config, temp, green, comp, output_path, 50, 101)

        # Read back and verify
        new_config = configparser.RawConfigParser()
        new_config.read(output_path)

        # Check interpolated values
        assert int(new_config.get("White Balance", "Temperature")) == 6000
        assert float(new_config.get("White Balance", "Green")) == 1.0
        assert float(new_config.get("Exposure", "Compensation")) == 0.0

        # Check crop was applied
        assert new_config.get("Crop", "Enabled") == "true"
        assert new_config.get("Crop", "Ratio") == "16:9"

        # Check resize was set
        assert new_config.get("Resize", "Enabled") == "true"
        assert int(new_config.get("Resize", "Width")) == 3840  # 4K
        assert int(new_config.get("Resize", "Height")) == 2160

    def test_get_image_dimensions_crop_disabled(self):
        """Test getting dimensions when crop is disabled"""
        pp3_path = Path(self.temp_dir) / "test.pp3"
        self.create_test_pp3(pp3_path)

        config, _, _, _ = self.interpolator.parse_pp3(pp3_path)
        width, height = self.interpolator.get_image_dimensions(config)

        assert width == 6056
        assert height == 4032

    def test_get_image_dimensions_crop_enabled(self):
        """Test getting dimensions when crop is enabled"""
        pp3_path = Path(self.temp_dir) / "test.pp3"
        content = """[Crop]
Enabled=true
X=100
Y=200
W=5000
H=3000
"""
        pp3_path.write_text(content)

        config, _, _, _ = self.interpolator.parse_pp3(pp3_path)
        width, height = self.interpolator.get_image_dimensions(config)

        # Should return default dimensions with warning
        assert width == 6056
        assert height == 4032

    def test_get_image_dimensions_cached(self):
        """Test that original dimensions are cached"""
        pp3_path = Path(self.temp_dir) / "test.pp3"
        self.create_test_pp3(pp3_path)

        config, _, _, _ = self.interpolator.parse_pp3(pp3_path)

        # First call
        width1, height1 = self.interpolator.get_image_dimensions(config)

        # Modify config
        config.set("Crop", "W", "1000")
        config.set("Crop", "H", "1000")

        # Second call should return cached values
        width2, height2 = self.interpolator.get_image_dimensions(config)

        assert width1 == width2 == 6056
        assert height1 == height2 == 4032
