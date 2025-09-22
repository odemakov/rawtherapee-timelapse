from rawtherapee_timelapse.cli import SimpleInterpolator


class TestZoom:
    """Test the apply_zoom_to_crop function"""

    def setup_method(self):
        """Create a SimpleInterpolator instance for testing"""
        from pathlib import Path

        self.interpolator = SimpleInterpolator(directory=Path("."), dry_run=True)

    def test_zoom_center_anchor(self):
        """Test zoom with center anchor"""
        # Original image and crop
        original_width, original_height = 6000, 4000
        crop_x, crop_y, crop_w, crop_h = 0, 312, 6000, 3375

        # Apply 80% zoom (zoom in)
        new_x, new_y, new_w, new_h = self.interpolator.apply_zoom_to_crop(
            crop_x,
            crop_y,
            crop_w,
            crop_h,
            original_width,
            original_height,
            0.8,
            "center",
        )

        # Should reduce size by 20% and center
        assert new_w == 4800  # 6000 * 0.8
        assert new_h == 2700  # 3375 * 0.8
        assert new_x == 600  # 0 + (6000 - 4800) / 2
        assert new_y == 649  # 312 + (3375 - 2700) / 2

    def test_zoom_top_anchor(self):
        """Test zoom with top anchor"""
        # Original image and crop
        original_width, original_height = 6000, 4000
        crop_x, crop_y, crop_w, crop_h = 0, 312, 6000, 3375

        # Apply 80% zoom
        new_x, new_y, new_w, new_h = self.interpolator.apply_zoom_to_crop(
            crop_x, crop_y, crop_w, crop_h, original_width, original_height, 0.8, "top"
        )

        assert new_w == 4800
        assert new_h == 2700
        assert new_x == 600  # Centered horizontally
        assert new_y == 312  # Top stays at same position

    def test_zoom_bottom_anchor(self):
        """Test zoom with bottom anchor"""
        # Original image and crop
        original_width, original_height = 6000, 4000
        crop_x, crop_y, crop_w, crop_h = 0, 312, 6000, 3375

        # Apply 80% zoom
        new_x, new_y, new_w, new_h = self.interpolator.apply_zoom_to_crop(
            crop_x,
            crop_y,
            crop_w,
            crop_h,
            original_width,
            original_height,
            0.8,
            "bottom",
        )

        assert new_w == 4800
        assert new_h == 2700
        assert new_x == 600  # Centered horizontally
        assert new_y == 987  # 312 + (3375 - 2700)
        # Bottom edge should stay: 987 + 2700 = 3687, original: 312 + 3375 = 3687 ✓

    def test_zoom_stays_within_bounds(self):
        """Test that zoom respects image boundaries"""
        # Original image and crop near edge
        original_width, original_height = 6000, 4000
        crop_x, crop_y, crop_w, crop_h = 0, 0, 6000, 3375

        # Apply 50% zoom (extreme zoom in)
        new_x, new_y, new_w, new_h = self.interpolator.apply_zoom_to_crop(
            crop_x, crop_y, crop_w, crop_h, original_width, original_height, 0.5, "top"
        )

        assert new_w == 3000  # 6000 * 0.5
        assert new_h == 1687  # 3375 * 0.5
        assert new_x == 1500  # Centered
        assert new_y == 0  # Can't go negative

    def test_no_zoom(self):
        """Test with 100% zoom (no change)"""
        original_width, original_height = 6000, 4000
        crop_x, crop_y, crop_w, crop_h = 0, 312, 6000, 3375

        new_x, new_y, new_w, new_h = self.interpolator.apply_zoom_to_crop(
            crop_x,
            crop_y,
            crop_w,
            crop_h,
            original_width,
            original_height,
            1.0,
            "center",
        )

        # Should be unchanged
        assert (new_x, new_y, new_w, new_h) == (crop_x, crop_y, crop_w, crop_h)

    def test_zoom_sequence(self):
        """Test a zoom sequence from 80% to 100%"""
        original_width, original_height = 6000, 4000

        # Get initial 16:9 crop
        crop_x, crop_y, crop_w, crop_h = self.interpolator.calculate_16_9_crop(
            original_width, original_height, "center", 0.0
        )

        # Test various points in the zoom sequence
        zoom_levels = [0.8, 0.85, 0.9, 0.95, 1.0]
        previous_w = 0

        for zoom in zoom_levels:
            new_x, new_y, new_w, new_h = self.interpolator.apply_zoom_to_crop(
                crop_x,
                crop_y,
                crop_w,
                crop_h,
                original_width,
                original_height,
                zoom,
                "center",
            )

            # Width should increase as we zoom out
            assert new_w > previous_w or zoom == 0.8
            previous_w = new_w

            # Aspect ratio should be maintained
            assert abs(new_w / new_h - 16 / 9) < 0.01
