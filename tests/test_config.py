from datapilot.config import entities, expected_columns, pipeline_for_entity, require_entity


def test_entities_match_pipelines_yaml():
    assert set(entities()) == {"orders", "inventory", "customers"}


def test_expected_columns_orders():
    cols = expected_columns("orders")
    assert "order_id" in cols and "customer_id" in cols


def test_pipeline_for_entity():
    assert pipeline_for_entity("orders") == "orders_pipeline"


def test_require_entity_rejects_unknown():
    import pytest
    with pytest.raises(ValueError):
        require_entity("not_a_real_entity")
