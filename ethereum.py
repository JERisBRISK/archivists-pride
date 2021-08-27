import json
import requests
from web3 import Web3

class Ethereum:
    w3 = Web3(Web3.HTTPProvider('https://mainnet.infura.io/v3/58c9fc5b6b7b493089f4d174a610beeb'))
    # based on https://eips.ethereum.org/EIPS/eip-1155
    EIP_1155 = json.loads('''
    [{
        "constant": true,
        "inputs":[
            {"name": "_owner", "type": "address"},
            {"name": "_id", "type": "uint256"}
        ],
        "name": "balanceOf",
        "outputs": [
            {"name":"", "type": "uint256"}
        ],
        "payable": false,
        "stateMutability": "view",
        "type": "function"
    }]
    ''')

    @staticmethod
    def GetEthInFiat(ethQty: float, fiat="USD"):
        response = requests.get('https://api.coinbase.com/v2/exchange-rates?currency=ETH')
        data = json.loads(response.text)
        rate = float(data['data']['rates'][fiat])
        return rate * ethQty

    @staticmethod
    def GetTokenQuantity(walletAddress, contractAddress, tokenId):
        contract = Ethereum.w3.eth.contract(Ethereum.w3.toChecksumAddress(contractAddress), abi=Ethereum.EIP_1155)
        wallet = Ethereum.w3.toChecksumAddress(walletAddress)
        return int(contract.functions.balanceOf(wallet, tokenId).call())
