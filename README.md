# connect_mysql

mysqlにpandasで繋ぐためのpackage

# version
0.0.4

# install

```shell
pip install -U connect_mysql
```

# usage

踏み台サーバ経由でDBにpython3,pandasでアクセスする
```python
from connect_mysql import MysqlConnectorViaBastion

bastion_server_info = {
    'host': 'ssh_hostname',
    'port': 22,
    'user': 'ssh_username',
    'key_path': 'path'
}
db_info = {
    'host': 'db_hostname',
    'port': 3306,
    'user': 'db_username',
    'db': 'db_name',
    'password': 'db_password'
}

with MysqlConnectorViaBastion(
    use_bastion=True, db_info=db_info, bastion_server_info=bastion_server_info) as connector:
    sample_table = connector.query('SELECT * FROM sample_table;')
```

※ Connectorクラスはversion0.0.4から非推奨になりました
```python
from connect_mysql import Connector
connector = Connector(host, db_name, user_name, password)
print(connecor.tablelist) # テーブルリストの取得
df = connector.get_query("SELECT * FROM sample_table;")
```