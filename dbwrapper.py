#coding: utf8

import time
import pymysql
from decimal import Decimal
from data import myconfig as cfg

def ErrorWrapper(onerror):
    def inner(func):
        def invoke_func(db, *args, **kwargs):
            while 1:
                try:
                    retvalue = func(db, *args, **kwargs)
                except Exception as e:
                    print('>>> {} error\n{}\n>>> sql: {}\n>>> params: {}'.format(func.__name__, e, db.baksql, db.bakargs))
                    if e.args[0] == 2013:
                        db.on_error()
                        continue
                    kwargs['error'] = e
                    return onerror(db, *args, **kwargs)
                else:
                    return retvalue
        return invoke_func
    return inner

class Wrapper(object):
    def __init__(self):
        self.recharge_insert_id = 0
        self.reconnect()

    def reconnect(self):
        elapse, max_elapse = 1000, 60000
        while 1:
            try:
#                print(f'user: {cfg.db_user}, pwd: {cfg.db_pwd}, host: {cfg.db_ip}, db: {cfg.database}')
                self.conn = pymysql.connect(user = cfg.db_user, password = cfg.db_pwd, host = cfg.db_ip, port=cfg.db_port, database = cfg.database)
                self.cursor = self.conn.cursor()
            except Exception as e:
                print('Mysql connect failed! {}'.format(e))
                time.sleep(elapse if elapse < max_elapse else max_elapse)
                elapse <<= 1
            else:
#                self.cursor.execute('set autocommit=0')
                break

    def exec(self, sql, *args):
#        print(f'>>> sql: {sql}, args: {args}')
        self.baksql, self.bakargs = sql, args
        affected = 0
        if len(args) == 1 and (isinstance(args[0], list) or isinstance(args[0], tuple)):
            affected = self.cursor.executemany(sql, args[0])
            self.cursor.execute('commit')
        else:
            affected = self.cursor.execute(sql, args)
        return affected

    def on_error(self, *args, **kwargs):
        ''' 一般化错误处理：重连
        '''
        self.cursor.close()
        self.conn.close()
        self.reconnect()

    def on_order_error(self, **kwargs):
        self.on_error(**kwargs)
        return 8801, kwargs['error']

    @ErrorWrapper(on_order_error)
    def on_order(self, **kwargs):
        ''' 写委托库，产生委托编号
        '''
        otype = kwargs['otype']
        if otype & 0x02:
            self.exec("call add_cancel(%s, %s)", kwargs['user_id'], kwargs['related_id'])
        else:
            self.exec("call add_order(%s, %s, %s, %s, %s, %s)", kwargs['user_id'], kwargs['symbol'], kwargs['reference'], kwargs['otype'], kwargs['price'], kwargs['qty'])
        data = self.cursor.fetchall()
        return 0, data[0]

    def check_order_error(self, **kwargs):
        self.on_error(**kwargs)
        return 8802, kwargs['error']

    @ErrorWrapper(check_order_error)
    def check_order(self, **kwargs):
        ''' 检查订单合法性
        '''
        self.exec("call check_consign(%s, %s)", kwargs['user_id'], kwargs['consign_id'])
        result = self.cursor.fetchall()
        return 0, result

    def on_tick_error(self, **kwargs):
        self.on_error(kwargs)
        return 8803, kwargs['error']

    @ErrorWrapper(on_tick_error)
    def on_tick(self, **kwargs):
        ''' TICK成交
        '''
        if kwargs['oid_activated'] == 0:    # 撤单成交
            qty_cancelled = kwargs['qty']
            oid_proactive = kwargs['oid_proactive']
            self.exec("call on_cancel(%s, %s)", oid_proactive, qty_cancelled)
        elif kwargs['qty'] == 0:    # market_buy finished
            self.exec("call on_market_buy_finished(%s)", kwargs['oid_activated'])
        else:   # 普通成交
            self.exec("call on_tick(%s, %s, %s, %s)", kwargs['oid_activated'], kwargs['oid_proactive'], Decimal(kwargs['price']), Decimal(kwargs['qty']))
        result = self.cursor.fetchall()
        return 0, result[0]

    def get_all_symbol(self, **kwargs):
        ''' 获得全部交易对
        '''
        sql = '''select m.id, m.datum_id, m.datum_name, n.trade_id, n.trade_name from
            (select a.id, b.coin as datum_name, b.id as datum_id from jys_all_symbol a, jys_all_coin b where a.datum_coin_id=b.id) m,
            (select a.id, b.coin as trade_name, b.id as trade_id from jys_all_symbol a, jys_all_coin b where a.trade_coin_id=b.id) n
            where m.id=n.id'''
        self.exec(sql)
        datas = self.cursor.fetchall()
        symbols = []
        symbolids = {}
        for row in datas:
            symbols.append((row[0], '{}/{}'.format(row[4], row[2])))
            symbolids['{}/{}'.format(row[3], row[1])] = row[0]

        return symbols, symbolids

    def get_last_id(self):
        self.cursor.execute('select last_insert_id()')
        return self.cursor.fetchall()[0][0]

    def wallet_address_error(self, **kwargs):
        self.on_error(kwargs)
        return 8900, kwargs['error']

    @ErrorWrapper(wallet_address_error)
    def wallet_address(self, coin_name, addresses):
        sql = 'insert jys_coin_address(coin, in_address, password) values(%s, %s, %s)'
        params = []
        for addr, pwd in addresses:
            params.append((coin_name, addr, pwd))
        affected = self.exec(sql, params)
        return affected, 'OK'

    def wallet_withdraw_error(self, **kwargs):
        self.on_error(kwargs)
        return 8901, kwargs['error']

    @ErrorWrapper(wallet_withdraw_error)
    def wallet_withdraw(self, _id, txid, _status, _remark = None):
        sql = 'update jys_recharge_distill set txid=%s, `status`=%s, remark=%s where id=%s'
        self.exec(sql, txid, _status, _remark, _id)
        lastid = self.get_last_id()
        self.exec('commit')
        return lastid, 'OK'

    def wallet_deposit_error(self, **kwargs):
        self.on_error(kwargs)
        return 8902, kwargs['error']

    @ErrorWrapper(wallet_deposit_error)
    def wallet_deposit(self, params):
        sql = 'insert jys_recharge_distill(coin, in_address, amount, fee, txid, `type`, `status`) select %s, %s, %s, %s, %s, "IN", "PENDING" from dual where not exists (select txid from jys_recharge_distill where txid=%s) and (select count(*) from jys_coin_address where coin=%s and in_address=%s) > 0'
        self.exec(sql, params)
        lastid = self.get_last_id()
        self.exec('commit')
        if self.recharge_insert_id == lastid:
            return 0, { 'id': 0 }
        else:
            self.recharge_insert_id = lastid
            return 0, { 'id': self.recharge_insert_id }

    def ethereum_collect_error(self, **kwargs):
        self.on_error(kwargs)
        return 8902, kwargs['error']

    @ErrorWrapper(ethereum_collect_error)
    def ethereum_collect(self):
        sql = "select a.id,a.in_address,a.txid,a.amount+a.fee,b.password from jys_recharge_distill a,jys_coin_address b where a.coin='ETH' and a.`status`='PENDING' and a.`type`='IN' and a.in_address=b.in_address and b.coin=a.coin"
        self.exec(sql)
        return self.cursor.fetchall()

if __name__ == '__main__':
    obj = Wrapper()
    obj.get_all_symbol()
#    consign_id = obj.on_order(user_id=3998, symbol=229, otype=0, price=1344032, qty=2501)
#    print(consign_id)
