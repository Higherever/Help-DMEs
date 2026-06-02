from backend.scripts.scrape_master import (
    filter_plus_playstyles,
    merge_playstyle_sources,
    normalize_playstyles,
    playstyles_are_current,
)


def test_merge_prefers_futbin_when_it_has_playstyles():
    futbin = normalize_playstyles(
        [
            {"name": "Rapid", "is_plus": True, "icon_url": "/playstyles/26/plus/rapid.png"},
            {"name": "Intercept", "is_plus": True, "icon_url": "/playstyles/26/plus/intercept.png"},
        ],
        source="futbin",
    )
    futgg = normalize_playstyles(
        [
            {"name": "Rapid", "is_plus": False, "icon_url": "/playstyles/26/rapid.png"},
            {"name": "Pinged Pass", "is_plus": True, "icon_url": "/playstyles/26/plus/pingedpass.png"},
        ],
        source="futgg",
    )

    merged = merge_playstyle_sources(futbin, futgg)
    rendered = filter_plus_playstyles(merged)

    assert [ps["slug"] for ps in rendered] == ["rapid", "intercept"]
    assert rendered[0]["source"] == "futbin"
    assert rendered[0]["verified_by_futgg"] is False


def test_merge_uses_futgg_when_futbin_has_no_playstyles():
    futgg = normalize_playstyles(
        [
            {"name": "Rapid", "is_plus": True, "icon_url": "/playstyles/26/plus/rapid.png"},
            {"name": "Intercept", "is_plus": False, "icon_url": "/playstyles/26/intercept.png"},
        ],
        source="futgg",
    )

    merged = merge_playstyle_sources([], futgg)
    rendered = filter_plus_playstyles(merged)

    assert [ps["slug"] for ps in rendered] == ["rapid"]
    assert rendered[0]["source"] == "futgg_fallback"
    assert rendered[0]["verified_by_futgg"] is True


def test_filter_plus_accepts_legacy_is_plus_and_tier():
    playstyles = [
        {"name": "Rapid", "is_plus": False, "tier": "base"},
        {"name": "Pinged Pass", "is_plus": True},
        {"name": "Intercept", "tier": "plus"},
    ]

    rendered = filter_plus_playstyles(playstyles)

    assert [ps["slug"] for ps in rendered] == ["pinged_pass", "intercept"]


def test_playstyles_current_requires_canonical_fields():
    legacy = [{"name": "Rapid", "is_plus": True}]
    current = normalize_playstyles(
        [{"name": "Rapid", "is_plus": True, "icon_url": "/playstyles/26/plus/rapid.png"}],
        source="futbin",
    )

    assert playstyles_are_current(legacy) is False
    assert playstyles_are_current(current) is True
