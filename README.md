# connect_mysql

mysqlにpythonで繋ぐためのmodule

# version
0.0.3

# install

```shell
pip install -U connect_mysql
```

# usage

```python
from connect_mysql import Connector
connector = Connector(host, db_name, user_name, password)
print(connecor.tablelist) # テーブルリストの取得
df = connector.get_query("SELECT * FROM sample_table;")
```