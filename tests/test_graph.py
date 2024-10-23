from samples.theGraph.getPoolIds import main as get_pool_ids
from samples.theGraph.getPools import main as get_pools

from balpy.graph.graph import main as endpoint_prices

TEST_NETWORK = "gnosis-chain"


def test_get_pool_ids():
    get_pool_ids(TEST_NETWORK)


def test_get_pools():
    get_pools(TEST_NETWORK)


def test_bal_graph():
    endpoint_prices()
