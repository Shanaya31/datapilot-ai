from datapilot.quality.anomaly import volume_anomaly


def test_no_history_uses_static_bounds():
    result = volume_anomaly(current=50, history=[], fallback_min=100, fallback_max=1000)
    assert result["method"] == "static_bounds"
    assert result["is_anomaly"] is True  # 50 < fallback_min


def test_trailing_median_flags_large_drop():
    result = volume_anomaly(current=100, history=[1000, 1050, 980, 1010], tolerance_pct=50)
    assert result["method"] == "trailing_median"
    assert result["is_anomaly"] is True


def test_trailing_median_allows_normal_variation():
    result = volume_anomaly(current=1020, history=[1000, 1050, 980, 1010], tolerance_pct=50)
    assert result["is_anomaly"] is False
