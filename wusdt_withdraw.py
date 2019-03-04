#! /usr/bin/env python3
#coding: utf8

import sys
from data import myconfig as cfg
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from dbwrapper import Wrapper as dw

usdt_conn = AuthServiceProxy(cfg.usdt_rpcurl)

if __name__ == '__main__':
    # params: id, inaddr, outaddr, amount
    print(sys.argv)
    txid, status = None, 'INVALID ADDRESS'
    usdt_conn.walletpassphrase(cfg.usdt_wallet_pwd, 60)
    print('unlock wallet success.')
    try:
        balance = usdt_conn.omni_getbalance(sys.argv[-2], 31)
        print(type(balance), balance)
    except Exception as e:
        print(e)
    else:
        try:
            txid = usdt_conn.omni_send(sys.argv[-3], sys.argv[-2], 31, sys.argv[-1])
        except JSONRPCException as e:
            if e.code == -206:
                status = 'BTC NOT ENOUGH'
                print('withdraw', status)
            else:
                status = e.message
                print('withdraw', str(e))
        else:
            status = 'COMPLETE'
            print('success', txid)
    db = dw()
    lastid, status = db.wallet_withdraw(sys.argv[-4], txid, status)
    print(f">>> withdraw USDT {sys.argv[-3]}->{sys.argv[-2]}: txid={txid} record={lastid} status={status}")
