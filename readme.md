## 通讯

- 服务端使用zmq.REP模式
- recv_pyobj/send_pyobj

### response

``` json
{
    'errno': 1,
    'errmsg': 'proceeding',
}

{
    'errno': 100,
    'errmsg': 'unknown method'
}

{
    'errno': 101,
    'errmsg': 'Invalid coin name',
}

{
    'errno': 102,
    'errmsg': 'method not exists',
}
```

## 产生钱包地址

### request

``` python
{
    'funcname': 'generate_address',
    'coin_name': 'xxx',           # 货币代码（ETH/BTC/LTC……）
    'address_num': xxx,           # 产生钱包地址的数量
}
```

### response

``` json
# 正在产生地址，不可重复请求
{
    'errno': 103,
    'errmsg': 'proceeding',
}
```

``` sql
insert jys_coin_address(coin, in_address, password) values(货币代码, 产生的钱包地址, 钱包密码（如果需要的话）)
```

## 提币

### request

``` python
{
    'funcname': 'withdraw',
    'coin_name': 'xxx',           # 货币代码
    'in_address': 'xxx',          # 内部转出钱包地址
    'out_address': 'xxx',         # 外部转入钱包地址
    'tx_num': 'xxx',              # 转账数量
    'id': xxx,                    # jys_recharge_distill.id
}
```

### response

``` sql
update jys_recharge_distill set
 txid=txid,
 `status`=COMPLETE/FAILED,
 remark=null/reason
where id=request.id
```

## 充币

### notify

``` http
# 发现充币后notify
get /v1/wallet/receiveNotify
```

### response

``` sql
insert jys_recharge_distill(coin, in_address, amount, fee, txid, `type`, `status`) select
 货币代码,
 内部转入钱包地址,
 转账数量,
 计收手续费,
 txid,
 "IN",
 "PENDING" from dual where
    not exists
    (select txid from jys_recharge_distill where txid=txid)
    and (select count(*) from jys_coin_address where
        coin=货币代码
        and in_address=内部转入钱包地址) > 0
```
