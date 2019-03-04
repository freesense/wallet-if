#! /usr/bin/env python3
#coding: utf8

import time, bs4
from data import myconfig as cfg
from decimal import Decimal
from urllib import request
from urllib.error import HTTPError, URLError
from threading import Thread
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from wallet import random_pwd
from dbwrapper import Wrapper as dw

coin_name = 'BTC'
generating = False
print(f'Connecting {coin_name} wallet...', end = '')
rpc_conn = AuthServiceProxy(cfg.btc_rpcurl)
print('OK.')

def get_height_from_btc_com():
    url = 'https://btc.com'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.62 Safari/537.36'}
    req = request.Request(url, headers=headers)
    try:
        rsp = request.urlopen(req)
    except HTTPError as e:
        print('btc.com: {}'.format(e.code))
    except URLError as e:
        print('btc.com: {}'.format(e.reason))
    else:
        rsp = rsp.read()
        soup = bs4.BeautifulSoup(rsp, 'html.parser')
        node = soup.find('a', attrs = {'ga-type': 'block'})
        try:
            return int(''.join(node.text.split(',')))
        except:
            pass

    return None

def query_deposit(cname, restart_height, sync_time, chain_height, fee):
    def restart_bitcoind():
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
            restart_bitcoind()
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
    t = Thread(target = query_deposit, args = (coin_name, cfg.restart_btc_height, cfg.sync_btc_time, get_height_from_btc_com, cfg.btc_deposit_fee))
    t.start()

def withdraw(obj, pwd = None):
    txid, status = None, 'INVALID ADDRESS'
    isvalid = rpc_conn.validateaddress(obj['out_address'])
    if isvalid['isvalid']:
        rpc_conn.walletpassphrase(cfg.btc_wallet_pwd if pwd is None else pwd, 10)
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
    generate(coin_name, 1)
#    x = withdraw('admin123456', x[0], '0.00031')
#    print(x)
