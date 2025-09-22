from rawtherapee_timelapse.cli import SimpleInterpolator


class TestEasing:
    """Test the easing functions"""

    def setup_method(self):
        """Create a SimpleInterpolator instance for testing"""
        from pathlib import Path

        self.interpolator = SimpleInterpolator(directory=Path("."), dry_run=True)

    def test_linear_easing(self):
        """Test linear easing (no easing)"""
        assert self.interpolator.apply_easing(0.0, "linear") == 0.0
        assert self.interpolator.apply_easing(0.25, "linear") == 0.25
        assert self.interpolator.apply_easing(0.5, "linear") == 0.5
        assert self.interpolator.apply_easing(0.75, "linear") == 0.75
        assert self.interpolator.apply_easing(1.0, "linear") == 1.0

    def test_ease_in(self):
        """Test ease-in (slow start, accelerating)"""
        assert self.interpolator.apply_easing(0.0, "ease-in") == 0.0
        assert self.interpolator.apply_easing(0.5, "ease-in") == 0.25  # t²
        assert self.interpolator.apply_easing(1.0, "ease-in") == 1.0

        # Should start slower than linear
        assert self.interpolator.apply_easing(0.25, "ease-in") < 0.25

    def test_ease_out(self):
        """Test ease-out (fast start, decelerating)"""
        assert self.interpolator.apply_easing(0.0, "ease-out") == 0.0
        assert self.interpolator.apply_easing(0.5, "ease-out") == 0.75  # 1 - (1-t)²
        assert self.interpolator.apply_easing(1.0, "ease-out") == 1.0

        # Should start faster than linear
        assert self.interpolator.apply_easing(0.25, "ease-out") > 0.25

    def test_ease_in_out(self):
        """Test ease-in-out (slow at both ends)"""
        assert self.interpolator.apply_easing(0.0, "ease-in-out") == 0.0
        assert self.interpolator.apply_easing(0.5, "ease-in-out") == 0.5  # Midpoint
        assert self.interpolator.apply_easing(1.0, "ease-in-out") == 1.0

        # Should be slower than linear at start and end
        assert self.interpolator.apply_easing(0.25, "ease-in-out") < 0.25
        assert self.interpolator.apply_easing(0.75, "ease-in-out") > 0.75

    def test_exponential_easing(self):
        """Test exponential easing (ease-in-out)"""
        assert self.interpolator.apply_easing(0.0, "exponential") == 0.0
        assert self.interpolator.apply_easing(1.0, "exponential") == 1.0

        # At midpoint should be 0.5 (symmetric ease-in-out)
        assert self.interpolator.apply_easing(0.5, "exponential") == 0.5

        # Should be very slow at the start
        assert self.interpolator.apply_easing(0.1, "exponential") < 0.01

        # Should be very slow at the end
        assert self.interpolator.apply_easing(0.9, "exponential") > 0.99

    def test_default_easing(self):
        """Test fallback to linear for unknown easing"""
        # Unknown easing should default to linear
        assert self.interpolator.apply_easing(0.5, "unknown") == 0.5
        assert self.interpolator.apply_easing(0.5, "") == 0.5

    def test_ease_cubic(self):
        """Test the ease_cubic helper function"""
        assert self.interpolator.ease_cubic(0.0) == 0.0
        assert self.interpolator.ease_cubic(0.5) == 0.5  # Midpoint
        assert self.interpolator.ease_cubic(1.0) == 1.0

        # Should be smooth S-curve
        assert self.interpolator.ease_cubic(0.25) < 0.25
        assert self.interpolator.ease_cubic(0.75) > 0.75

    def test_easing_monotonic(self):
        """Test that all easing functions are monotonically increasing"""
        easings = ["linear", "ease-in", "ease-out", "ease-in-out", "exponential"]

        for easing in easings:
            values = []
            for i in range(11):  # 0.0 to 1.0 in 0.1 steps
                t = i / 10.0
                values.append(self.interpolator.apply_easing(t, easing))

            # Check that values are non-decreasing
            for i in range(len(values) - 1):
                assert values[i] <= values[i + 1], (
                    f"{easing} is not monotonic at {i / 10.0}"
                )
