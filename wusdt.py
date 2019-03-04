#! /usr/bin/env python3
#coding: utf8

# ./omnicore-cli -datadir=/mnt/usdt -rpcuser=admin -rpcpassword=admin123456 -rpcport=58886 getblockchaininfo
# ./omnicore-cli -datadir=/mnt/usdt -rpcuser=admin -rpcpassword=admin123456 -rpcport=58886 omni_gettransaction 947d6cb3a8c5301f5c54eecba6255bb1bd4ebfbdcaf577b7b99a0911ec9b1600
# ./omnicore-cli -datadir=/mnt/usdt -rpcuser=admin -rpcpassword=admin123456 -rpcport=58886 encryptwallet admin654321

import time, bs4, os
from data import myconfig as cfg
from decimal import Decimal
from urllib import request
from threading import Thread
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from dbwrapper import Wrapper as dw

coin_name = 'USDT'
generating = False
print(f'Connecting {coin_name} wallet...', end = '')
rpc_conn = AuthServiceProxy(cfg.usdt_rpcurl)
print('OK.')

def get_chain_height():
    return None

def query_deposit(cname, restart_height, sync_time, chain_height, fee):
    def restart_omnicored():
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
            return rpc_conn.omni_listtransactions('*', 10000)
        except:# Exception as e:
#            print('xxxxxxxxxxxxxxxxx', e)
            return []

    check_time = 0
    while 1:
        old_check_time = check_time
        check_time = time.time()
        if check_time - old_check_time >= 600 and check_block_height():
            restart_omnicored()
        else:
            txs = check_transaction()
            params = []
            for tx in txs:
                if tx['propertyid'] != 31 or tx['confirmations'] < 6:
                    continue
                else:
                    params.append((cname, tx["referenceaddress"], Decimal(tx['amount']), 0, tx['txid'], tx['txid'], cname, tx["referenceaddress"]))
            deposit(params)
            time.sleep(0.5)

def run():
    t = Thread(target = query_deposit, args = (coin_name, cfg.restart_usdt_height, cfg.sync_usdt_time, get_chain_height, cfg.usdt_deposit_fee))
    t.start()

def withdraw(obj, pwd = None):
    os.system("python3 wusdt_withdraw.py {} {} {} {}".format(obj['id'], obj['in_address'], obj['out_address'], obj['tx_num']))

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
    rpc_conn.walletpassphrase(cfg.usdt_wallet_pwd, 60)
    print('unlock wallet success.')
    balance = rpc_conn.omni_getbalance('1FSZjDFYTxa1Uy8K8eCQBWvh4DjN2uiMns', 31)
    print(balance)
    #xxx = rpc_conn.omni_sendsto('1KKbyixSasoGkbiQNYcMkZoGMuTnY9wG9t', 31, '109.56')
    xxx = rpc_conn.omni_send('1FSZjDFYTxa1Uy8K8eCQBWvh4DjN2uiMns', '1KKbyixSasoGkbiQNYcMkZoGMuTnY9wG9t', 31, '109.56')
    print('send success', xxx)
#    print(generate(1))
