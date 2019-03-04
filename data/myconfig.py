#coding: utf8

# laowo online
#db_ip = "47.75.188.104"
#db_port = 14937
#db_user = "bu_zhi_dao"
#db_pwd = "l#h^6)6~6"
#database = "lwjys_db"

# laowo local
db_ip = "192.168.10.198"
db_port = 3306
db_user = "develop"
db_pwd = "!@#$mysql"
database = "jys_db"

# wallet config
wallet_svraddr = "tcp://*:25565"
deposit_notify_url = 'http://172.31.40.232:8000/v1/wallet/receiveNotify'

# bitcoin
restart_btc_height = 10
sync_btc_time = 20 * 60
btc_wallet_pwd = 'admin654321'
btc_rpcurl = 'http://admin:admin123456@127.0.0.1:58885'
btc_deposit_fee = '0'

# ethereum
restart_eth_height = 10
sync_eth_time = 20 * 60
eth_jys_wallet = '0x3454069F8f07bFBBA74c5AA121581469074d7dCB'
eth_jys_wallet_pwd = 'Ltd/d:d08:&Z'
eth_rpcurl = 'http://127.0.0.1:8545'
eth_deposit_fee = '0.01'
eth_retain = '0.00096'

# usdt
restart_usdt_height = 10
sync_usdt_time = 20 * 60
usdt_wallet_pwd = 'admin654321'
usdt_rpcurl = 'http://admin:admin123456@127.0.0.1:58886'
usdt_deposit_fee = '0'
usdt_withdraw_command = './omnicore-cli -datadir=/mnt/usdt -rpcuser=admin -rpcpassword=admin123456 -rpcport=58886 omni_send "%s" "%s" 31 "%s"'

# ltc
restart_ltc_height = 10
sync_ltc_time = 20 * 60
ltc_wallet_pwd = 'admin654321'
ltc_rpcurl = 'http://admin:admin123456@127.0.0.1:58887'
ltc_deposit_fee = '0'
