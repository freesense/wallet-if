#! /usr/bin/env python3
#coding: utf8

# pip3 install web3, ethereum

import time, bs4, random
from data import myconfig as cfg
from decimal import Decimal, localcontext
from threading import Thread
from urllib import request
from dbwrapper import Wrapper as dw
from urllib.error import HTTPError, URLError
from web3 import Web3, HTTPProvider, personal
from web3.utils.encoding import (hexstr_if_str, to_bytes, to_hex)
from eth_utils.crypto import keccak
from eth_utils import encode_hex
from ethereum.abi import encode_abi, decode_abi

coin_name = 'ETH'
generating = False
print(f'Connecting {coin_name} wallet...', end = '')
w3 = Web3(HTTPProvider(cfg.eth_rpcurl))
print('OK.')

def random_pwd(length = 12):
    lst = '1234567890~!@#$%^&*()_+|}{":?><abcdefghijklmnopqrstuvwxyz-=,./;ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    s = ''
    for _ in range(length):
        s += random.choice(lst)
    return s

def func_sign_to_4bytes(event_signature):
    '''ASCII Keccak hash 4bytes
    '''
    return keccak(text=event_signature.replace(' ', ''))[:4]

ERC20_TRANSFER_ABI_PREFIX = encode_hex(
    func_sign_to_4bytes('transfer(address, uint256)')
)

def from_unit(number, unit):
    '''币种精度转换
    '''

    if number == 0:
        return 0

    with localcontext() as ctx:
        ctx.prec = 999
        d_number = Decimal(value=number, context=ctx)
        result_value = d_number / Decimal(unit)

    return result_value

class TransactionData(object):
    '''交易数据模型
    '''
    from_address = None
    to_address = None
    token_address = None
    ether_amount = 0
    token_amount = 0
    num_confirmations = -1

def get_height_from_etherscan_io():
    url = 'https://etherscan.io'
    headers = { 'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36 Edge/15.15063'}
    req = request.Request(url, headers=headers)
    try:
        rsp = request.urlopen(req)
    except HTTPError as e:
        print('etherscan.io: {}'.format(e.code))
    except URLError as e:
        print('etherscan.io: {}'.format(e.reason))
    else:
        rsp = rsp.read()
        soup = bs4.BeautifulSoup(rsp, 'html.parser')
        h4s = soup.find_all('h4', limit=2)
        try:
            return int(h4s[1].text.split('\n')[0])
        except:
            pass

    return None

def query_deposit(cname, restart_height, sync_time, chain_height, fee):
    def restart_ethd():
        pass

    def check_block_height():
        syncing = w3.eth.syncing
        net_height = chain_height()
        height = w3.eth.blockNumber
        print(f'net-height: {net_height}, this-height: {height}')
        if net_height is None or height is None or height >= net_height or net_height - height >= restart_height:
            return False
        else:
            return True

    check_time = 0
    while 1:
        old_check_time = check_time
        check_time = time.time()
        if check_time - old_check_time >= 600 and check_block_height():
            print('restart_ethd')
            restart_ethd()
        else:
            params = []
            txhashes = w3.eth.getBlock('latest').get('transactions')
            for txid in txhashes:
                try:
                    txid = hexstr_if_str(to_hex, txid)
                    tx_data = TransactionData()
                    tx = w3.eth.getTransaction(txid)
                    if tx:
                        tx_data.from_address = tx['from']
                        tx_data.to_address = tx['to']
                        tx_data.ether_amount = w3.fromWei(tx['value'], 'ether')
                        if not tx.get('blockNumber'):
                            tx_data.num_confirmations = 0
                        else:
                            tx_block_number = int(tx['blockNumber'])
                            cur_block_number = int(w3.eth.blockNumber)
                            tx_data.num_confirmations = cur_block_number - tx_block_number + 1
                            tx_data.block_hash = tx['blockHash']
                            tx_data.block_num = tx_block_number
                        tx_input = tx.get('input')
                        if tx_input and (tx_input.lower().startswith(ERC20_TRANSFER_ABI_PREFIX.lower())):
                            to, amount = decode_abi(['address', 'uint256'], hexstr_if_str(to_bytes, tx_input[len(ERC20_TRANSFER_ABI_PREFIX):]))
                            tx_data.to_address = w3.toChecksumAddress(to)
                            tx_data.token_amount = int(amount)
                            tx_data.token_address = tx['to']
                    #print(tx_data.to_address, tx_data.ether_amount, type(tx_data.ether_amount))
                    if not tx_data.to_address or tx_data.ether_amount == 0:
                        continue
                except Exception as e:
                    print(e)
                    continue
                _amount = tx_data.ether_amount - Decimal(fee) if tx_data.ether_amount > Decimal(fee) else Decimal(0)
                _fee = Decimal(fee) if tx_data.ether_amount > Decimal(fee) else tx_data.ether_amount
                params.append((cname, tx_data.to_address, _amount, _fee, txid, txid, cname, tx_data.to_address))

            deposit(params, collect)
            time.sleep(0.5)

def run():
    t = Thread(target = query_deposit, args = (coin_name, cfg.restart_eth_height, cfg.sync_eth_time, get_height_from_etherscan_io, cfg.eth_deposit_fee))
    t.start()
    #t.join()

def collect(params):
    def updatedb(id, txid, status, remark):
        db = dw()
        _, status = db.wallet_withdraw(id, txid, status, remark)
        print(f">>> collect {coin_name} {in_address}->{cfg.eth_jys_wallet}: txid={txid} status={status}, remark={remark}")

    gas_limit = 21000
    gas_price = w3.eth.gasPrice * 4

    for row in params:  # (id, in_address, txid, amount+fee, passwd)
        id, in_address, txid, amount, passwd = row
        tx = {
            'gas': gas_limit,
            'gasPrice': gas_price,
            'from': in_address,
            'to': cfg.eth_jys_wallet,
            'nonce': w3.eth.getTransactionCount(in_address),
            'value': w3.eth.getBalance(in_address) - gas_limit * gas_price - 200000 - w3.toWei(cfg.eth_retain, 'ether'),
        }

        try:
            _txid = w3.personal.sendTransaction(tx, passwd)
        except Exception as e:
            updatedb(id, txid, 'FAILED', e.args[0]['message'])
            continue

        updatedb(id, txid, "PENDING", None)

def withdraw(obj):
    def updatedb(txid, status, remark = None):
        db = dw()
        lastid, status = db.wallet_withdraw(obj['id'], txid, status, remark)
        print(f">>> withdraw {obj['coin_name']} {obj['in_address']}->{obj['out_address']}: txid={txid} record={lastid} status={status}, remark={remark}")

    gas_limit = 21000
    gas_price = w3.eth.gasPrice * 4

    tx = {
        'gas': gas_limit,
        'gasPrice': gas_price,
        'from': cfg.eth_jys_wallet,
        'to': obj['out_address'],
        'nonce': w3.eth.getTransactionCount(cfg.eth_jys_wallet),
        'value': w3.toWei(obj['tx_num'], 'ether'),
    }

    try:
        txid = w3.personal.sendTransaction(tx, cfg.eth_jys_wallet_pwd)
    except Exception as e:
        updatedb(None, 'FAILED', e.args[0]['message'])
        return

    updatedb(txid.hex(), "COMPLETE")

def generate(name, num, conn = None):
    addresses = []
    for _ in range(num):
        passphrase = random_pwd()
        addresses.append((w3.personal.newAccount(passphrase), passphrase))

    db = dw()
    affected, data = db.wallet_address(name, tuple(addresses))
    global generating
    generating = False
    print(f'>>> generate {name} address: {affected} {data}')

if __name__ == '__main__':
    import wallet
    deposit = wallet.deposit
    query_deposit(coin_name, cfg.restart_eth_height, cfg.sync_eth_time, get_height_from_etherscan_io, cfg.eth_deposit_fee)
#    print(withdraw('admin123456', '0x7c4bD7c98dECE264616AEF4BaCc0e10217aB0f3C', '0x2F8e8fF15e86D5a6640b8F1624591b56b6905D03', '10000'))
#    print(w3.eth.accounts)
#    print(generate(coin_name, 1))
#    print(w3.eth.accounts)
