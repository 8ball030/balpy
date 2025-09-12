# basics
import json
import math
import time

# for customized endpoints
import requests

# thegraph queries
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

from balpy.enums.types import Chain, SwapType

DEFAULT_SWAP_OPTIONS = {
    "maxPools": 4,
    "queryBatchSwap": True,
}

BALANCER_API_ENDPOINT = "https://api-v3.balancer.fi/"


class TheGraph(object):
    client = None

    """
    A starting point for querying pool data from the Balancer Subgraph.
        At time of writing, this package does not cover all types of queries
        possible to the Balancer V2 Subgraph. It does, however, allow users
        to query pool data, among other things. Types of queries will ultimately
        grow to include all possible queries to the Balancer Subgraph.

        For more information on the Subgraph, please go to:
        https://thegraph.com/legacy-explorer/subgraph/balancer-labs/balancer-v2
    """

    def __init__(self, network="mainnet", customUrl=None, usingJsonEndpoint=False):
        super(TheGraph, self).__init__()
        self.network = network
        self.initBalV2Graph(customUrl=customUrl, usingJsonEndpoint=usingJsonEndpoint)

    def printJson(self, curr_dict):
        print(json.dumps(curr_dict, indent=4))

    def callCustomEndpoint(self, query):
        query = query.replace("\n", " ")
        query = query.replace("\t", "")
        queryDict = {"query": query}
        serializedData = json.dumps(queryDict)
        headers = {"Content-Type": "application/json"}
        r = requests.post(self.graphUrl, data=serializedData, headers=headers)
        response = r.json()
        return response["data"]

    def assertInit(self):
        if self.client is None:
            print()
            print("[ERROR] Subgraph not initialized.")
            print('Call "initBalV2Graph(network)" before calling this function.')
            print()
            return None

    def initBalV2Graph(self, customUrl, usingJsonEndpoint, verbose=False):
        if customUrl is not None and usingJsonEndpoint:
            self.client = "CUSTOM"
            self.graphUrl = customUrl
            return True

        network_string = ""
        if not self.network == "mainnet":
            network_string = "-" + self.network

        if verbose:
            print("Balancer V2 Subgraph initializing on:", self.network, "...")

        graphUrl = (
            "https://api.thegraph.com/subgraphs/name/balancer-labs/balancer"
            + network_string
            + "-v2"
        )
        if customUrl is not None and not usingJsonEndpoint:
            graphUrl = customUrl

        balancer_transport = RequestsHTTPTransport(url=graphUrl, verify=True, retries=3)
        self.client = Client(transport=balancer_transport)

        if verbose:
            print("Successfully initialized on network:", self.network)

    def getPoolTokens(self, pool_id, verbose=False):
        self.assertInit()

        if verbose:
            print("Querying tokens for pool with ID:", pool_id)

        pool_token_query = """
        query {{
          poolTokens(first: 8, where: {{ poolId: "{pool_id}" }}) {{
            id
            poolId {{
                id
            }}
            symbol
            name
            decimals
            address
            balance
            weight
          }}
        }}
        """
        formatted_query_string = pool_token_query.format(pool_id=pool_id)
        if self.client == "CUSTOM":
            response = self.callCustomEndpoint(formatted_query_string)
        else:
            response = self.client.execute(gql(formatted_query_string))
        if verbose:
            print("Got pool tokens.")
        return response["poolTokens"]

    def getNumPools(self, verbose=False):
        self.assertInit()
        if verbose:
            print("Querying number of pools...")

        # get number of balancer pools on v2
        balancers_query = """
        query {
            balancers(first: 5) {
            id
            poolCount
          }
        }
        """
        if self.client == "CUSTOM":
            response = self.callCustomEndpoint(balancers_query)
        else:
            response = self.client.execute(gql(balancers_query))

        if verbose:
            print("Got response from the Subgraph")

        for balancer in response["balancers"]:
            if balancer["id"] == "2":
                num_pools = balancer["poolCount"]
                return num_pools
        return None

    def getPools(self, batch_size, skips, verbose=False):
        self.assertInit()
        if verbose:
            print("Querying pools #", skips, "through #", skips + batch_size, "...")

        query_string = """
            query {{
              pools(first: {first}, skip: {skip}) {{
                id
                address
                poolType
                strategyType
                swapFee
              }}
            }}
            """
        formatted_query_string = query_string.format(first=batch_size, skip=skips)
        if self.client == "CUSTOM":
            response = self.callCustomEndpoint(formatted_query_string)
        else:
            response = self.client.execute(gql(formatted_query_string))

        if verbose:
            print("Got pools.")
        return response

    def getV2Pools(self, batch_size, verbose=False):
        if self.client is None:
            self.initBalV2Graph(verbose=verbose)

        num_pools = self.getNumPools(verbose=verbose)
        num_calls = math.ceil(num_pools / batch_size)

        if verbose:
            print("Querying", num_pools, "pools...")

        # query all pools by batch to save time
        pool_tokens = {}
        for i in range(num_calls):
            response = self.getPools(batch_size, batch_size * i, verbose)

            for pool in response["pools"]:
                curr_id = pool["id"]
                curr_pool_token_data = self.getPoolTokens(curr_id, verbose=verbose)
                pool_data = {}
                pool_data["tokens"] = curr_pool_token_data
                pool_data["poolType"] = pool["poolType"]
                pool_data["swapFee"] = pool["swapFee"]
                pool_tokens[curr_id] = pool_data
        return pool_tokens

    def getV2PoolIDs(self, batch_size, pool_filter=None, verbose=False):
        if self.client is None:
            self.initBalV2Graph(verbose=verbose)

        num_pools = self.getNumPools(verbose=verbose)
        num_calls = math.ceil(num_pools / batch_size)

        if verbose:
            print("Querying", num_pools, "pools...")

        # query all pools by batch to save time
        poolIdsByType = {}
        for i in range(num_calls):
            response = self.getPools(batch_size, batch_size * i, verbose)
            for pool in response["pools"]:
                if (
                    pool_filter is not None
                    and pool_filter.lower() not in pool["poolType"].lower()
                ):
                    continue
                if pool["poolType"] not in poolIdsByType.keys():
                    poolIdsByType[pool["poolType"]] = []
                poolIdsByType[pool["poolType"]].append(pool["id"])
        header = {}
        header["stamp"] = time.time()
        poolCount = 0
        for t in poolIdsByType.keys():
            poolCount += len(poolIdsByType[t])
        header["numPools"] = poolCount

        data = {}
        data["header"] = header
        data["pools"] = poolIdsByType
        return data

    def getPoolBptPriceEstimate(self, poolId, verbose=False):
        self.assertInit()
        if verbose:
            print("Getting data for pool", poolId, "from the subgraph...")

        query_string = """
            query {{
                pools(where:{{id: "{poolId}"}}) {{
                    totalShares
                    totalLiquidity
                }}
            }}
            """
        formatted_query_string = query_string.format(poolId=poolId)
        response = self.client.execute(gql(formatted_query_string))

        pool = response["pools"][0]
        pricePerBpt = float(pool["totalLiquidity"]) / float(pool["totalShares"])

        if verbose:
            print("Got price data:", pricePerBpt)
        return pricePerBpt

    def getPoolsAndTokens(self, batch_size, skips, verbose=False):
        self.assertInit()
        query_string = """
            query {{
              pools(first: {first}, skip: {skip}) {{
                id
                tokens {{
                  token
                  {{
                    id
                  }}
                }}
              }}
            }}
        """
        formatted_query_string = query_string.format(first=batch_size, skip=skips)

        response = self.client.execute(gql(formatted_query_string))
        if self.client == "CUSTOM":
            response = self.callCustomEndpoint(formatted_query_string)
        else:
            response = self.client.execute(gql(formatted_query_string))
        return response

    def getSorGetSwapPaths(
        self,
        chain: Chain,
        swapAmount: float,
        tokenIn: str,
        tokenOut: str,
        swapType: str = SwapType.EXACT_IN.value,
        swapOptions: dict = None,
        queryBatchSwap: bool = True,
        retries: int = 3,
    ):
        """
        Calls the SOR api from the Balancer to get swap paths.
        Args:
            chain (Chain): The chain to query.
            swapAmount (float): The amount to swap.
            tokenIn (str): The token to swap in.
            tokenOut (str): The token to swap out.
            swapType (SwapType, optional): The type of swap. Defaults to SwapType.EXACT_IN.
            swapOptions (dict, optional): The options for the swap. Defaults to None.
            queryBatchSwap (bool, optional): Whether to query batch swap. Defaults to True.
        Returns:
            dict: The response from the SOR.

        """
        if not swapOptions:
            swapOptions = DEFAULT_SWAP_OPTIONS
            swapOptions["timestamp"] = int(time.time())
        query_string = """
          query sorGetSwapPaths(
            $chain: GqlChain!,
            $swapAmount: AmountHumanReadable!,
            $swapType: GqlSorSwapType!,
            $tokenIn: String!,
            $tokenOut: String!,
            $useProtocolVersion: Int
          ) {
            sorGetSwapPaths(
              chain: $chain,
              swapAmount: $swapAmount,
              swapType: $swapType,
              tokenIn: $tokenIn,
              tokenOut: $tokenOut,
              useProtocolVersion: $useProtocolVersion
            ) {
              swaps {
                  assetOutIndex,
                  amount,
                  assetInIndex,
                  poolId
                }

              returnAmount,
              tokenInAmount,
              tokenOutAmount,
              effectivePrice,
              tokenAddresses
            }
            }
        """
        params = {
            "chain": chain.upper(),
            "swapAmount": swapAmount,
            "tokenIn": tokenIn,
            "tokenOut": tokenOut,
            "swapType": swapType,
            "useProtocolVersion": 2,
        }

        response = requests.post(
            BALANCER_API_ENDPOINT, json={"query": query_string, "variables": params}
        )
        if response.status_code != 200:
            if "banned" in response.text and retries > 0:
                # We sleep for 5 seconds to avoid being banned
                time.sleep(5)
                print("We got banned from the Balancer API. Sleeping for 5 seconds.")
                return self.getSorGetSwapPaths(
                    chain,
                    swapAmount,
                    tokenIn,
                    tokenOut,
                    swapType,
                    swapOptions,
                    queryBatchSwap,
                )

            raise Exception(
                f"Error querying the Balancer API: {response.text} {response.status_code}"
            )
        response_json = response.json()
        if response_json.get("errors"):
            raise Exception(f"SOR GraphQL Error: {response_json.get('errors')}")

        data = response_json.get("data", {}).get("sorGetSwapPaths")
        if not data:
            raise Exception("SOR GraphQL Error: No data returned")
        return data

    def getCurrentPrices(
        self,
        chain: Chain,
        cooldown: int = 5,
        retries: int = 0,
    ):
        """
        get the current prices of all pools
        """
        query = """
        query GetTokenCurrentPrices($chains: [GqlChain!]) {
          tokenGetCurrentPrices(chains: $chains) {
            price
            address
          }
        }
        """
        response = requests.post(
            BALANCER_API_ENDPOINT,
            json={"query": query, "variables": {"chains": [chain.upper()]}},
        )
        if response.status_code in [429, 500]:
            timeout = cooldown * (retries + 1)
            print(
                f"We got banned from the Balancer API. Sleeping for {timeout} seconds."
            )
            time.sleep(timeout)
            return self.getCurrentPrices(chain, cooldown, retries + 1)
        return response.json()["data"]["tokenGetCurrentPrices"]

    def getTicker(self, chain: Chain, baseAsset: str, quoteAsset: str, amount: float):
        """Get the current bid/ask price of a token."""

        query = """
        query GetBidAsk(
            $chain: GqlChain!,
            $swapAmount: AmountHumanReadable!,
            $tokenIn: String!,
            $tokenOut: String!
            ) {
            bid: sorGetSwapPaths(
                chain: $chain,
                swapAmount: $swapAmount,
                swapType: EXACT_IN,
                tokenIn: $tokenIn,
                tokenOut: $tokenOut,
                useProtocolVersion: 2,
                considerPoolsWithHooks: true

            ) {
                ...SorQuote
            }

            ask: sorGetSwapPaths(
                chain: $chain,
                swapAmount: $swapAmount,
                swapType: EXACT_OUT,
                tokenIn: $tokenOut,
                tokenOut: $tokenIn,
                useProtocolVersion: 2,
                considerPoolsWithHooks: true
            ) {
                ...SorQuote
            }
            }

            fragment SorQuote on GqlSorGetSwapPaths {
            swaps {
                assetOutIndex
                amount
                assetInIndex
                poolId
            }
            returnAmount
            swapAmount
            tokenInAmount
            tokenOutAmount
            effectivePrice
            effectivePriceReversed
            tokenAddresses
            tokenIn
            }
        """
        params = {
            "chain": chain.upper(),
            "swapAmount": str(amount),
            "tokenIn": baseAsset,
            "tokenOut": quoteAsset,
        }

        response = requests.post(
            BALANCER_API_ENDPOINT, json={"query": query, "variables": params}
        )

        if response.status_code != 200:
            raise Exception(
                f"Error querying the Balancer API: {response.text} {response.status_code}"
            )

        response_json = response.json()
        if response_json.get("errors"):
            raise Exception(f"SOR GraphQL Error: {response_json.get('errors')}")

        data = response_json.get("data", {})
        ask_data = data.get("ask", {})
        bid_data = data.get("bid", {})

        if not ask_data or not bid_data:
            raise Exception("Incomplete data returned from API")

        return data


def main():
    network = Chain.GNOSIS.value

    graph = TheGraph(network, customUrl=BALANCER_API_ENDPOINT, usingJsonEndpoint=True)

    for i in range(0, 10):
        config = {
            "chain": network,
            "swapAmount": str(50.00 * (1 + i**3)),
            "swapType": "EXACT_IN",
            # "tokenOut": "0xcE11e14225575945b8E6Dc0D4F2dD4C570f79d9f",
            # "tokenIn": "0xe91d153e0b41518a2ce8dd3d7944fa863463a97d",
            "tokenIn": "0xcE11e14225575945b8E6Dc0D4F2dD4C570f79d9f",
            "tokenOut": "0xe91d153e0b41518a2ce8dd3d7944fa863463a97d",
        }

        paths = graph.getSorGetSwapPaths(**config)
        rate = paths["effectivePrice"]
        print(
            f"{1 / float(rate)} for 1 {config['tokenIn']} to {config['tokenOut']} size: {config['swapAmount']} output: {paths['returnAmount']}"
        )


if __name__ == "__main__":
    main()
