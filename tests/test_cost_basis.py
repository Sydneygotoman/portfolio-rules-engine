from app.rules_engine.cost_basis import MATERIAL_MISMATCH_PCT, detect_mismatch


def test_no_mismatch_when_venue_figure_not_recorded(position_factory, metadata_factory):
    p = position_factory(metadata=metadata_factory(cost_basis=1.0, venue_reported_cost_basis=None))
    assert detect_mismatch(p) is None


def test_pass_within_material_threshold(position_factory, metadata_factory):
    p = position_factory(metadata=metadata_factory(cost_basis=1.0, venue_reported_cost_basis=1.10))
    assert detect_mismatch(p).status == "pass"


def test_warning_beyond_material_threshold(position_factory, metadata_factory):
    p = position_factory(metadata=metadata_factory(cost_basis=1.0, venue_reported_cost_basis=1.20))
    assert detect_mismatch(p).status == "warning"


def test_render_example_from_the_build_spec(position_factory, metadata_factory):
    # docs/rules-engine-build-spec.md §3: Swyftx recorded ~$6.29, actual ~$0.40
    p = position_factory(
        asset="RENDER",
        metadata=metadata_factory(asset="RENDER", cost_basis=0.40, venue_reported_cost_basis=6.29),
    )
    result = detect_mismatch(p)
    assert result.status == "warning"
    assert "entered figure" in result.reason
