import hashlib
import json
from time import time
from urllib.parse import urlparse
from uuid import uuid4

import requests
from flask import Flask, jsonify, request

class Blockchain(object):

    def __init__(self):
        self.current_transactions = [] # 交易池
        self.chain = [] # 链
        self.nodes = set() # 节点列表

        # Create the genesis block
        self.new_block(previous_hash = '0', proof=100)

    def register_node(self, address):
        """
        Add a new node to the list of nodes
        :param address: Address of node. Eg. 'http://192.168.1.164:8081'
        :return:
        """
        parsed_url = urlparse(address)
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)
        elif parsed_url.path:
            self.nodes.add(parsed_url.netloc)
        else:
            raise ValueError('Invalid URL')


    def valid_chain(self, chain):
        """
        Determine if a given blockchain is valid
        :param chain: A blockchain
        :return: True if valid, False if not
        """
        prev_block = chain[0]
        current_height = 1

        while current_height < len(chain):
            block = chain[current_height]
            print(f'{prev_block}')
            print(f'{block}')
            # Check that the path of the block is correct
            prev_block_hash = self.hash(prev_block)
            if block['previous_hash'] != prev_block_hash:
                return False

            # Check that the proof of work is correct
            if not self.valid_proof(prev_block['proof'], block['proof'], prev_block_hash):
                return False

            prev_block = block
            current_height += 1
        return True

    def resolve_conflicts(self):
        """
        This is consensus algorith, it resolves conflicts by replacing
        chain with the longest one in the network.
        :return:  True if chain was replaced, False if not
        """
        neighbours = self.nodes
        new_chain = None

        # looking for chains longer than current
        max_length = len(self.chain)

        # Grab and verify the chains from all the nodes in network
        for node in neighbours:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # Check if the length is longer and the chain is valid
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # Replacing chain if discovered a new, valid chain longer than current
        if new_chain:
            self.chain = new_chain
            return True
        return False


    def new_block(self, proof, previous_hash):
        """
        Create a new Block in the BlockChain
        :param proof:  The proof given by the Proof of Work algorithm
        :param previous_hash: Hash of previous Block
        :return:  New Block
        """
        block = {
            'height': len(self.chain) + 1,
            'timestamp' : time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1])
        }

        # reset the current list of transactions
        self.current_transactions = []

        self.chain.append(block)
        return block


    def new_transaction(self, sender, recipient, amount):
        """
        Creates a new transaction to go into the next mined Block
        :param sender:  Address of the Sender
        :param recipient:  Address of the Recipient
        :param amount:  Amount to send
        :return: The index of the Block that will hold this transaction
        """

        self.current_transactions.append(
            {
                'sender': sender,
                'recipient': recipient,
                'amount': amount
            }
        )

        return self.last_block['height'] + 1


    @property
    def last_block(self):
        return self.chain[-1]

    @staticmethod
    def hash(block):
        """
        Create a SHA-256 hash of Block
        :param block:
        :return:
        """
        # We must make sure that the Dictionary is Ordered, or we'll have iconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def proof_of_work(self, last_block):
        """
        Simple Proof of Work Algorithm

        - Find a number p' such that hash(pp') contains leading 4 zeros
        - Where p is the previous proof, and p' is the new proof
        :param last_block: <dict>last Block
        :return: <int>
        """
        last_proof = last_block['proof']
        last_hash = self.hash(last_block)

        proof = 0
        while self.valid_proof(last_proof, proof, last_hash) is False:
            proof += 1
        return proof

    @staticmethod
    def valid_proof(last_proof, proof, last_hash):
        """
        Validates the Proof
        :param last_proof: <int> Previous Proof
        :param proof: <int> Current Proof
        :param last_hash: <str>The hash of the Previous Block
        :return: <bool>True if correct, False if not
        """
        guess = f'{last_proof}{proof}{last_hash}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()

        return guess_hash[:4] == "0000"



# Instantiate the Node
app = Flask(__name__)

# Generate a globally unique adress for this node
node_identifier = str(uuid4()).replace("-", "")

# Instantiate the Blockchain
blockChain = Blockchain()

@app.route('/mine', methods=['GET'])
def mine():
    # Run the proof of work algorithm tho get tne next proof
    last_block = blockChain.last_block
    proof = blockChain.proof_of_work(last_block)

    # Must receive a reward for finding the proof.
    # The sender is "0" to signify that this node has mined a new coin
    blockChain.new_transaction(sender='0', recipient=node_identifier, amount=1)

    # Forge the new Block by adding it to the chain
    previous_hash = blockChain.hash(last_block)
    block = blockChain.new_block(proof, previous_hash)

    response = {
        'message': "New Block Forged",
        "height": block['height'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash']
    }

    return jsonify(response), 200


@app.route('/transaction/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    # Check that the required fields are in the POST'ed data
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return "Missing values", 400

    # Create a new transaction
    height = blockChain.new_transaction(values['sender'], values['recipient'], values['amount'])
    response = {'message': f'Transaction will be added of Block {height}'}
    return jsonify(response), 200


@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain':blockChain.chain,
        'length': len(blockChain.chain)
    }
    return jsonify(response), 200


@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockChain.register_node(node)

    response = {
        "message": 'New nodes have been added',
        'total_nodes': list(blockChain.nodes)
    }

    return jsonify(response), 201


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockChain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockChain.chain
        }

    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockChain.chain
        }

    return jsonify(response), 200

if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(host='0.0.0.0', port=port)