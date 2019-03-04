#! /usr/bin/env python3
#coding: utf8

import zmq, sys, random
from urllib import request, parse
from data import myconfig as cfg
from threading import Lock
from concurrent.futures import ThreadPoolExecutor
from dbwrapper import Wrapper as dw

locker = Lock()

def random_pwd(length = 12):
    lst = '1234567890~!@#$%^&*()_+|}{":?><abcdefghijklmnopqrstuvwxyz-=,./;ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    s = ''
    for _ in range(length):
        s += random.choice(lst)
    return s

def single_thread(func):
    def func_wrapper(*args):
        with locker:
            func(*args)
    return func_wrapper

def generate_address(pool, mod, coin_name, num):
    func_generate = getattr(mod, 'generate', None)
    if func_generate is None:
        return {
            'errno': 102,
            'errmsg': 'method not exists',
        }

    if getattr(mod, 'generating', False) == True:
        return {
            'errno': 103,
            'errmsg': 'proceeding',
        }

    setattr(mod, 'generating', True)
    pool.submit(func_generate, coin_name, num)
    return {
        'errno': 1,
        'errmsg': 'proceeding',
    }

def withdraw(pool, mod, obj):
    func_withdraw = getattr(mod, 'withdraw', None)
    if func_withdraw is None:
        return {
            'errno': 104,
            'errmsg': 'method not exists',
        }

    pool.submit(func_withdraw, obj)
    return {
        'errno': 1,
        'errmsg': 'proceeding',
    }

@single_thread
def deposit(params, cb = None):
    conn = dw()
    errno, data = conn.wallet_deposit(params)
    if errno != 0:
        print('deposit error {}: {}'.format(errno, data))
    elif data['id'] != 0:
        # ethereum gathering
        datas = conn.ethereum_collect()    # (id, in_address, txid, amount+fee, passwd)
        cb(datas)
        try:
            request.urlopen(cfg.deposit_notify_url)
        except Exception as e:
            print(cfg.deposit_notify_url, e)
        else:
            print('deposit', data['id'])

def main():
    if len(sys.argv) == 1:
        sys.argv.append('wethereum')

    mods = {}
    for m in sys.argv[1:]:
        try:
            mod = __import__(m)
        except Exception as e:
            print(f'module {m} not exists: {e}')
        else:
            func_run = getattr(mod, 'run', None)
            func_withdraw = getattr(mod, 'withdraw', None)
            func_generate = getattr(mod, 'generate', None)
            if func_run is None or func_withdraw is None or func_generate is None:
                print(f'function {m}.run/withdraw/generate not exists.')
            else:
                mods[mod.coin_name] = mod
                mod.deposit = deposit
                func_run()

    print('Supportted coin:', ','.join([x for x in mods.keys()]))
    random.seed()

    pool = ThreadPoolExecutor(20)

    ctx = zmq.Context()
    wallet_svr = ctx.socket(zmq.REP)
    wallet_svr.bind(cfg.wallet_svraddr)
    print(f'inwallet service listening on {cfg.wallet_svraddr}...')

    while 1:
        obj = wallet_svr.recv_pyobj()
        print('Request:', obj)

        mod = mods.get(obj['coin_name'], None)
        if mod is None:
            ans = {
                'errno': 101,
                'errmsg': 'Invalid coin name',
            }
        elif obj['funcname'] == 'generate_address':
            ans = generate_address(pool, mod, obj['coin_name'], obj['address_num'])
        elif obj['funcname'] == 'withdraw':
            ans = withdraw(pool, mod, obj)
        else:
            ans = {
            'errno': 100,
            'errmsg': 'unknown method'
        }

        print('Response:', ans)
        wallet_svr.send_pyobj(ans)

    wallet_svr.close()
    ctx.term()

if __name__ == '__main__':
    main()
