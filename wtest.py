#! /usr/bin/env python3
#coding: utf8

import zmq

addr = 'tcp://127.0.0.1:25565'
ctx = zmq.Context()

def test():
    req = {
        'funcname': 'generate_address',
        'coin_name': 'BTC',
        'address_num': 1,
    }
    sock = ctx.socket(zmq.REQ)
    sock.connect(addr)
    sock.send_pyobj(req)
    ans = sock.recv_pyobj()
    print(ans)

if __name__ == '__main__':
    test()
