import pytest
from balpy.graph.graph import main as endpoint_prices
from samples.theGraph.getPoolIds import main as get_pool_ids
from samples.theGraph.getPools import main as get_pools


TEST_NETWORK = "gnosis-chain"


@pytest.mark.skip(reason="This test is deprecated")
def test_get_pool_ids():
    get_pool_ids(TEST_NETWORK)


@pytest.mark.skip(reason="This test is deprecated")
def test_get_pools():
    get_pools(TEST_NETWORK)


def test_bal_graph():
    endpoint_prices()
