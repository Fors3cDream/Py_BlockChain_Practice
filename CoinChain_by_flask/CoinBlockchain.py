"""
Create by Killer at 2019-04-30 13:37
"""

import hashlib
import json
import time
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse
import requests

class CoinBlockchain(object):

    def __init__(self):
        self.chain = []
        self.current_transactions = [] # 交易池
        self.nodes = set() # 节点
        self.new_block(proof=100, prev_hash=1) # 创世区块


    # 新增区块
    def new_block(self, proof:int, prev_hash:Optional[str])->Dict[str, Any]: # 指定返回类型为字典
        block = {
            'height': len(self.chain) + 1, # 区块高度 +1
            'timestamp': time.time(), # 时间戳
            'transactions': self.current_transactions, # 交易池
            'proof': proof, # 工作量证明
            'prev_hash': prev_hash or self.hash(self.chain[-1]) # 上个区块的哈希
        }

        self.current_transactions = [] # 当新区块生成后，交易池要清空
        self.chain.append(block) # 添加到链上

        return block


    def new_transaction(self, sender:str, recipient: str, amount: int) -> int:
        # 生成交易信息
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount
        })

        return self.last_block['height'] + 1 # 索引标记交易的数据

    @staticmethod
    def hash(block:Dict[str, Any])->str:
        block_str = json.dumps(block, sort_keys=True).encode("utf-8")
        return hashlib.sha256(block_str).hexdigest()

    @property
    def last_block(self)->Dict[str,Any]:
        return self.chain[-1]

    # 挖矿依赖于上一个区块的proof
    def proof_of_work(self, last_block)->int:
        last_proof = last_block['proof']
        last_hash = self.hash(last_block)

        proof = 0 # 循环求解符合条件的合法哈希
        while self.valid_proof(last_proof, proof) is False:
            proof += 1

        return proof

    @staticmethod
    def valid_proof(last_proof:int, proof:int)->bool:
        guess = f'{last_proof}{proof}'.encode('utf-8')
        guess_hash = hashlib.sha256(guess).hexdigest()

        return guess_hash[:4] == "0000" # 计算难度

    def register_node(self, addr:str)->None:
        parsed_url = urlparse(addr)
        if parsed_url.netloc:
            if parsed_url.netloc not in self.nodes:
                self.nodes.add(parsed_url.netloc)
                print("Add node: ", parsed_url.netloc)
        elif parsed_url.path:
            if parsed_url.path not in self.nodes:
                self.nodes.add(parsed_url.path)
                print("Add node: ", parsed_url.path)
        else:
            raise ValueError("URL无效")


    # 验证区块链
    # 1 - 区块哈希合法性
    # 2 - 区块工作量证明合法性
    def valid_chain(self, chain:List[Dict[str, Any]])->bool:
        last_block = chain[0] # 从第一区块开始
        current_height = 1

        while current_height < len(chain): # 循环验证
            block = chain[current_height]
            if block['prev_hash'] != self.hash(last_block): # 区块哈希校验
                return False

            if not self.valid_proof(last_block['proof'], block['prooof']): # 工作量证明验证
                return False

            last_block = block
            current_height += 1

        return True


    #共识算法
    # 有时候由于不同的矿工同时"挖矿"成功，区块链会出现短暂分叉。
    # 一段时间后，区块链会重新成为一条单独的主链，这个过程依赖于共识算法，共识又
    # 必要依赖于节点同步。
    # 通过节点同步帮助主链选择最长链
    def resolve_conflicts(self)->bool: # 冲突 一致性算法的一种
        # 取得节点中最长的链来替代当前链
        neighbours = self.nodes # 备份节点
        print(neighbours)
        new_chain = None
        max_length = len(self.chain)

        for node in neighbours: # 刷新每个网络节点， 获取最长更新
            response = requests.get(f"http://{node}/chain") # 获取节点的区块链
            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                if length > max_length:
                    max_length = length
                    new_chain = chain

        if new_chain:
            self.chain = new_chain
            return True
        else:
            return False