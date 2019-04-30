"""
Create by Killer at 2019-04-30 14:04
"""

from uuid import uuid4

from flask import Flask, jsonify, request

from CoinBlockchain import CoinBlockchain

KCoin = CoinBlockchain()
node_id = str(uuid4()).replace("-", '')
print("当前节点钱包地址:", node_id)

app = Flask(__name__)

@app.route("/")
def index_page():
    return "Welcome to KCoin..."

@app.route("/chain")
def index_chain():
    response = {
        'chain': KCoin.chain,
        'length': len(KCoin.chain)
    }
    return jsonify(response), 200

@app.route('/mining')
def mining():
    last_block = KCoin.last_block
    proof = KCoin.proof_of_work(last_block)

    # 系统奖励币
    KCoin.new_transaction(
        sender="0",
        recipient=node_id,
        amount=25
    )

    block = KCoin.new_block(proof, KCoin.hash(last_block))

    response = {
        'message' : "new block created...",
        'height' : block['height'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'hash' : KCoin.hash(block),
        'prev_hash' : block['prev_hash']
    }

    return jsonify(response), 200


@app.route('/new_transaction', methods=['POST'])
def new_transactions():
    values = request.get_json()  # 抓取网络传输的信息
    required = ["sender", "recipient", "amount"]

    # 判断提交的json数据key是否合法
    if not all(key in values for key in required):
        return "数据不完整或格式错误", 400

    index = KCoin.new_transaction(values["sender"], values["recipient"], values["amount"])  # 新增交易

    response = {
        "message": f"交易添加到区块{index}"
    }

    return jsonify(response), 200

@app.route("/new_node", methods=["POST"])
def new_node():
    values = request.get_json()
    nodes = values.get("nodes") # 获取所有节点

    if nodes is None:
        return "空节点"

    for node in nodes:
        KCoin.register_node(node)

    response = {
        "message": "网络节点加入到区块",
        "nodes": list(KCoin.nodes)
    }

    return jsonify(response), 200

@app.route('/node_refresh')
def node_refresh():
    replaced = KCoin.resolve_conflicts() # 最长链选择

    print(replaced)

    if replaced:
        response = {
            'message' : "区块链被替换为最长有效链",
            'new_chain': KCoin.chain
        }
    else:
        response = {
            'message' : "当前区块链为最长，无需替换",
            'chain' : KCoin.chain
        }

    return jsonify(response), 200

if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(host='127.0.0.1', port=port)