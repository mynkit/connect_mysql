'''踏み台サーバ経由でMySqlにアクセスする

Required:
    $ pip install sshtunnel PyMysql

Examples:
    >>> from connect_mysql import MysqlConnectorViaBation
    >>> bastion_server_info = {
    >>>     'host': 'ssh_hostname',
    >>>     'port': 22,
    >>>     'user': 'ssh_username',
    >>>     'key_path': 'path'
    >>> }
    >>> db_info = {
    >>>     'host': 'db_hostname',
    >>>     'port': 3306,
    >>>     'user': 'db_username',
    >>>     'db': 'db_name',
    >>>     'password': 'db_password'
    >>> }
    >>> with MysqlConnectorViaBation(
    >>>     use_bastion=True, db_info=db_info, bastion_server_info=bastion_server_info) as connector:
    >>> sample_table = connector.query('SELECT * FROM sample_table;')
    >>> print(sample_table)

'''

from sshtunnel import SSHTunnelForwarder
import pymysql
import traceback
import pandas as pd
pd.options.display.max_columns = None  # カラム全部表示させる


class MysqlConnector:
    '''mysqlにつなぐ

    Args:
        host (str):
        user (str):
        db (str):
        password (str):
        port (int): default 3306.

    '''

    def __init__(self, host: str, user: str, db: str, password: str, port=3306):
        self.conn = pymysql.connect(
            host=host, user=user, db=db, password=password, port=port, cursorclass=pymysql.cursors.DictCursor)

    def query(self, sql: str, print_error=False) -> pd.DataFrame:
        '''クエリ投げる

        Args:
            sql (str): sql文
            print_error (bool): エラーを吐き出すかどうか．default False

        Returns:
            pd.DataFrame

        '''
        try:
            cur = self.conn.cursor()
            cur.execute(sql)
            result = cur.fetchall()
            return pd.concat([pd.io.json.json_normalize(r) for r in result]).reset_index(drop=True)
        except:
            # エラーが出た場合は空のデータフレームを返す
            if print_error:
                traceback.print_exc()
            return pd.DataFrame()


class MysqlConnectorViaBation(MysqlConnector):
    '''踏み台サーバ経由でmysqlに繋ぐ

    Args:
        use_bastion (bool): DBログインに踏み台サーバを経由するかどうか

        bastion_server_info (dist): 踏み台サーバのログイン情報
            host (str): 踏み台サーバのhost名
            port (int): 踏み台サーバのport
            user (str): 踏み台サーバログイン用のユーザ名
            key_path (str): 秘密鍵のpath

        db_info (dict): mysqlDBのログイン情報
            host (str): mysqlDBのhost名
            port (int): mysqlDBのport
            user (str): mysqlDBログイン用のユーザ名
            db (str): DB名
            password (str): ログインpassword

    Examples:
        with MysqlConnectorViaBation(
            use_bastion=True, db_info=db_info, bastion_server_info=bastion_server_info) as connector:
            sample_table = connector.query('SELECT * FROM sample_table;')
            print(sample_table)

    '''

    def __init__(self, use_bastion: bool, db_info={}, bastion_server_info={}):
        self.db_info = db_info
        self.bastion_server_info = bastion_server_info
        if use_bastion:
            # 踏み台からDBにアクセスする場合
            self.bastion_login(self.bastion_server_info)
            super().__init__(host='127.0.0.1', port=self.tunnel.local_bind_port,
                             user=self.db_info['user'], db=self.db_info['db'], password=self.db_info['password'])

        else:
            # 踏み台を経由せず，直接DBにアクセスする場合
            super().__init__(host=self.db_info['host'], port=self.db_info['port'],
                             user=self.db_info['user'], db=self.db_info['db'], password=self.db_info['password'])

    def bastion_login(self, bastion_server_info: dict):
        '''
        Args:
            bastion_server_info (dist): 踏み台サーバのログイン情報
                host (str): 踏み台サーバのhost名
                port (int): 踏み台サーバのport
                user (str): 踏み台サーバログイン用のユーザ名
                key_path (str): 秘密鍵のpath

        '''
        self.tunnel = SSHTunnelForwarder(
            (self.bastion_server_info['host'],
             self.bastion_server_info['port']),
            ssh_username=self.bastion_server_info['user'],
            ssh_pkey=self.bastion_server_info['key_path'],
            remote_bind_address=(self.db_info['host'], self.db_info['port']))
        self.tunnel.start()

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        try:
            self.conn.close()  # DB接続の終了
        except:
            pass
        try:
            self.tunnel.stop()  # SSH接続の終了
        except:
            pass
