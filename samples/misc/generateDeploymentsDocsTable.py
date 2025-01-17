from balpy.balpy import balpy


def main():
    network = "kovan"

    bal = balpy(network)
    output = bal.generateDeploymentsDocsTable()
    print(output)


if __name__ == "__main__":
    main()
