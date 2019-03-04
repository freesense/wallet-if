#! /usr/bin/env python3
#coding: utf8

import time, bs4
from data import myconfig as cfg
from decimal import Decimal
from urllib import request
from threading import Thread
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from dbwrapper import Wrapper as dw

coin_name = 'LTC'
generating = False
print(f'Connecting {coin_name} wallet...', end = '')
rpc_conn = AuthServiceProxy(cfg.ltc_rpcurl)
print('OK.')

def get_chain_height():
    return None

def query_deposit(cname, restart_height, sync_time, chain_height, fee):
    def restart_litecoind():
        # todo
        time.sleep(sync_time)

    def check_block_height():
        '''
        return: False means no need restart, elsewise restart.
        '''
        net_height = chain_height()
        try:
            height = rpc_conn.getblockcount()
        except Exception as e:
            height = None
            print(e)
        if net_height is None or height is None or height >= net_height or net_height - height >= restart_height:
            return False
        else:
            return True

    def check_transaction():
        try:
            return rpc_conn.listtransactions('*', 10000)
        except:# Exception as e:
#            print('xxxxxxxxxxxxxxxxx', e)
            return []

    check_time = 0
    time_received = 0
    while 1:
        old_check_time = check_time
        check_time = time.time()
        if check_time - old_check_time >= 600 and check_block_height():
            restart_litecoind()
        else:
            txs = check_transaction()
            params = []
            txs.sort(key = lambda x: x['timereceived'])
            for tx in txs:
                if tx['category'] != 'receive' or time_received > tx['timereceived'] or tx['confirmations'] < 6:
                    continue
                else:
                    time_received = tx['timereceived']
                    params.append((cname, tx['address'], Decimal(tx['amount']), 0, tx['txid'], tx['txid'], cname, tx['address']))
            deposit(params)
            time.sleep(0.5)

def run():
    t = Thread(target = query_deposit, args = (coin_name, cfg.restart_ltc_height, cfg.sync_ltc_time, get_chain_height, cfg.ltc_deposit_fee))
    t.start()

def withdraw(obj, pwd = None):
    txid, status = None, 'INVALID ADDRESS'
    isvalid = rpc_conn.validateaddress(obj['out_address'])
    if isvalid['isvalid']:
        rpc_conn.walletpassphrase(cfg.ltc_wallet_pwd, 10)
        txid = rpc_conn.sendtoaddress(obj['out_address'], str(obj['tx_num']))
        status = 'COMPLETE'
    db = dw()
    lastid, status = db.wallet_withdraw(obj['id'], txid, status)
    print(f">>> withdraw {obj['coin_name']} {obj['in_address']}->{obj['out_address']}: txid={txid} record={lastid} status={status}")

def generate(name, num):
    from socket import timeout
    def getaddr():
        count = 0
        while count < 5:
            try:
                addr = rpc_conn.getnewaddress()
            except timeout:
                count += 1
                time.sleep(0.2)
                continue
            else:
                return addr
        return None

    result = []
    for _ in range(num):
        addr = getaddr()
        print(name, addr)
        if addr is not None:
            result.append((addr, ''))

    db = dw()
    affected, data = db.wallet_address(name, result)
    global generating
    generating = False
    print(f'>>> generate {name} address: {affected} {data}')

if __name__ == '__main__':
    import wallet
    deposit = wallet.deposit
#    print(generate(1))
