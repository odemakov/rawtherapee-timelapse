from pathlib import Path

from rawtherapee_timelapse.cli import SimpleInterpolator


class TestZoomFactor:
    """Test the calculate_zoom_factor function"""

    def setup_method(self):
        """Create a SimpleInterpolator instance for testing"""
        from pathlib import Path

        self.interpolator = SimpleInterpolator(directory=Path("."), dry_run=True)

    def test_no_zoom(self):
        """Test when zoom start equals zoom end (no zoom)"""
        self.interpolator.zoom_start = 1.0
        self.interpolator.zoom_end = 1.0

        assert self.interpolator.calculate_zoom_factor(0.0) == 1.0
        assert self.interpolator.calculate_zoom_factor(0.5) == 1.0
        assert self.interpolator.calculate_zoom_factor(1.0) == 1.0

    def test_zoom_in(self):
        """Test zoom in from 100% to 80% field of view"""
        self.interpolator.zoom_start = 1.0  # 100%
        self.interpolator.zoom_end = 0.8  # 80%
        self.interpolator.zoom_easing = "linear"

        # Start: 100% FOV
        assert self.interpolator.calculate_zoom_factor(0.0) == 1.0

        # Middle: 90% FOV
        assert self.interpolator.calculate_zoom_factor(0.5) == 0.9

        # End: 80% FOV
        assert self.interpolator.calculate_zoom_factor(1.0) == 0.8

    def test_zoom_out(self):
        """Test zoom out from 80% to 100% field of view"""
        self.interpolator.zoom_start = 0.8  # 80%
        self.interpolator.zoom_end = 1.0  # 100%
        self.interpolator.zoom_easing = "linear"

        # Start: 80% FOV
        assert self.interpolator.calculate_zoom_factor(0.0) == 0.8

        # Middle: 90% FOV
        assert self.interpolator.calculate_zoom_factor(0.5) == 0.9

        # End: 100% FOV
        assert self.interpolator.calculate_zoom_factor(1.0) == 1.0

    def test_zoom_with_easing(self):
        """Test zoom with different easing functions"""
        self.interpolator.zoom_start = 1.0
        self.interpolator.zoom_end = 0.5

        # Linear easing
        self.interpolator.zoom_easing = "linear"
        linear_mid = self.interpolator.calculate_zoom_factor(0.5)
        assert linear_mid == 0.75  # Linear interpolation

        # Ease-in (slower at start)
        self.interpolator.zoom_easing = "ease-in"
        ease_in_quarter = self.interpolator.calculate_zoom_factor(0.25)
        assert ease_in_quarter > 0.875  # Should be closer to start value

        # Ease-out (slower at end)
        self.interpolator.zoom_easing = "ease-out"
        ease_out_three_quarter = self.interpolator.calculate_zoom_factor(0.75)
        assert ease_out_three_quarter < 0.625  # Should be closer to end value

    def test_extreme_zoom(self):
        """Test extreme zoom values"""
        self.interpolator.zoom_start = 1.0
        self.interpolator.zoom_end = 0.5  # 50% FOV
        self.interpolator.zoom_easing = "linear"

        factors = []
        for i in range(5):
            progress = i / 4.0
            factors.append(self.interpolator.calculate_zoom_factor(progress))

        # Should interpolate from 1.0 to 0.5
        assert factors == [1.0, 0.875, 0.75, 0.625, 0.5]

    def test_zoom_level_parsing(self):
        """Test zoom level string parsing in __init__"""
        from pathlib import Path

        # Test range parsing
        interp1 = SimpleInterpolator(
            directory=Path("."), zoom_level="90-100", dry_run=True
        )
        assert interp1.zoom_start == 0.9
        assert interp1.zoom_end == 1.0

        # Test single value parsing
        interp2 = SimpleInterpolator(directory=Path("."), zoom_level="85", dry_run=True)
        assert interp2.zoom_start == 0.85
        assert interp2.zoom_end == 0.85

        # Test default
        interp3 = SimpleInterpolator(
            directory=Path("."), zoom_level="100-100", dry_run=True
        )
        assert interp3.zoom_start == 1.0
        assert interp3.zoom_end == 1.0

    def test_zoom_factor_range(self):
        """Test that zoom factors stay within reasonable bounds"""
        test_cases = [
            ("100-50", 0.5, 1.0),  # Zoom in to 50%
            ("50-100", 0.5, 1.0),  # Zoom out from 50%
            ("80-90", 0.8, 0.9),  # Small zoom
            ("100-100", 1.0, 1.0),  # No zoom
        ]

        for zoom_level, expected_min, expected_max in test_cases:
            interp = SimpleInterpolator(
                directory=Path("."), zoom_level=zoom_level, dry_run=True
            )

            # Test at various progress points
            for i in range(11):
                progress = i / 10.0
                factor = interp.calculate_zoom_factor(progress)
                assert expected_min <= factor <= expected_max
