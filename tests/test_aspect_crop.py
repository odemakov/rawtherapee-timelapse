from pathlib import Path

from rawtherapee_timelapse.cli import SimpleInterpolator


class TestAspectCrop:
    """Test the calculate_16_9_crop function"""

    def setup_method(self):
        """Create a SimpleInterpolator instance for testing"""

        self.interpolator = SimpleInterpolator(directory=Path("."), dry_run=True)

    def test_crop_from_3_2_center(self):
        """Test cropping from 3:2 to 16:9 with center drift"""
        # 3:2 image
        width, height = 6000, 4000

        x, y, w, h = self.interpolator.calculate_16_9_crop(width, height, "center", 0.0)

        # Should crop height to maintain 16:9
        assert w == 6000
        assert h == 3375  # 6000 * 9 / 16
        assert x == 0
        assert y == 312  # (4000 - 3375) / 2

    def test_crop_from_4_3_center(self):
        """Test cropping from 4:3 to 16:9 with center drift"""
        # 4:3 image
        width, height = 4000, 3000

        x, y, w, h = self.interpolator.calculate_16_9_crop(width, height, "center", 0.0)

        # Should crop height to maintain 16:9
        assert w == 4000
        assert h == 2250  # 4000 * 9 / 16
        assert x == 0
        assert y == 375  # (3000 - 2250) / 2

    def test_crop_already_16_9(self):
        """Test cropping when image is already 16:9"""
        # Already 16:9
        width, height = 1920, 1080

        x, y, w, h = self.interpolator.calculate_16_9_crop(width, height, "center", 0.0)

        # Should not crop
        assert (x, y, w, h) == (0, 0, 1920, 1080)

    def test_crop_wider_than_16_9(self):
        """Test cropping when image is wider than 16:9"""
        # Ultra-wide image
        width, height = 4000, 1000

        x, y, w, h = self.interpolator.calculate_16_9_crop(width, height, "center", 0.0)

        # Should crop width instead
        assert w == 1777  # 1000 * 16 / 9
        assert h == 1000
        assert x == 1111  # (4000 - 1777) / 2
        assert y == 0

    def test_drift_top(self):
        """Test top drift mode"""
        width, height = 6000, 4000

        x, y, w, h = self.interpolator.calculate_16_9_crop(width, height, "top", 0.0)

        assert w == 6000
        assert h == 3375
        assert x == 0
        assert y == 0  # Anchored at top

    def test_drift_bottom(self):
        """Test bottom drift mode"""
        width, height = 6000, 4000

        x, y, w, h = self.interpolator.calculate_16_9_crop(width, height, "bottom", 0.0)

        assert w == 6000
        assert h == 3375
        assert x == 0
        assert y == 625  # 4000 - 3375, anchored at bottom

    def test_drift_top_to_bottom(self):
        """Test animated drift from top to bottom"""
        width, height = 6000, 4000

        # Start (progress=0)
        x, y, w, h = self.interpolator.calculate_16_9_crop(
            width, height, "top-to-bottom", 0.0
        )
        assert y == 0  # Start at top

        # Middle (progress=0.5)
        x, y, w, h = self.interpolator.calculate_16_9_crop(
            width, height, "top-to-bottom", 0.5
        )
        assert y == 312  # (4000 - 3375) * 0.5

        # End (progress=1.0)
        x, y, w, h = self.interpolator.calculate_16_9_crop(
            width, height, "top-to-bottom", 1.0
        )
        assert y == 625  # 4000 - 3375

    def test_drift_bottom_to_top(self):
        """Test animated drift from bottom to top"""
        width, height = 6000, 4000

        # Start (progress=0)
        x, y, w, h = self.interpolator.calculate_16_9_crop(
            width, height, "bottom-to-top", 0.0
        )
        assert y == 625  # Start at bottom

        # Middle (progress=0.5)
        x, y, w, h = self.interpolator.calculate_16_9_crop(
            width, height, "bottom-to-top", 0.5
        )
        assert y == 312  # Middle position

        # End (progress=1.0)
        x, y, w, h = self.interpolator.calculate_16_9_crop(
            width, height, "bottom-to-top", 1.0
        )
        assert y == 0  # End at top

    def test_nikon_z6_dimensions(self):
        """Test with actual Nikon Z6 dimensions"""
        width, height = 6056, 4032

        x, y, w, h = self.interpolator.calculate_16_9_crop(width, height, "center", 0.0)

        # Should crop to 16:9
        assert w == 6056
        assert h == 3406  # 6056 * 9 / 16 = 3406.5
        assert x == 0
        assert y == 313  # (4032 - 3406) / 2
