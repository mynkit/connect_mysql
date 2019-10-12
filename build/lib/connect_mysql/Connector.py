'''mysqlへ接続してテーブル操作するためのクラスを作成

Todo:
    __insert_or_replace_tableメソッドで, Noneやnanを無理やりNullに文字列に変換しているので，もう少し賢いロジックにできそう

'''

import os
import re
import traceback
import mysql.connector
import pandas as pd


class Connector(object):
    '''mysqlに接続してテーブル操作する

    Args:
        host (str): DBのhost
        db_name (str): DB名
        user_name (str): DBのログインユーザ
        password (str): DBのログインパスワード

    Attributes:
        __con (mysql.connector.connection_cext.CMySQLConnection): mysqlへのconnection情報
        db_name (str): 現在接続中のDB名
        tablelist ([str]): 現在のDBのテーブル名リスト

    '''

    def __init__(self, host, db_name, user_name, password):
        self.host = host
        self.db_name = db_name
        self.user_name = user_name
        self.password = password
        self.__connect()
        self.get_tablelist()

    def __connect(self):
        '''DBにログイン
        '''
        self.__con = mysql.connector.connect(
            host=self.host, db=self.db_name, user=self.user_name, password=self.password)
        print('-- 接続完了 --')

    def disconnect(self):
        '''mysqlとの接続を終了する
        '''
        self.__con.close()
        print('-- 接続終了 --')

    def show_grants(self) -> pd.DataFrame:
        '''自分(self.user_name)の権限を確認する

        Returns:
            pd.DataFrame

        '''
        return self.get_query('show grants for %s' % self.user_name)

    def get_dblist(self) -> list:
        '''アクセス可能なデータベース一覧を取得

        Returns:
            [str]

        '''
        try:
            cur = self.__con.cursor()
            cur.execute('show databases;')
            dblist = [row[0] for row in cur.fetchall()]
            cur.close()
            return dblist
        except:
            print('====== get_dblistメソッドのエラー文 ======')
            traceback.print_exc()
            print('========= get_dblistメソッドのエラー文ここまで =========')

    def change_db(self, db_name):
        '''データベースを変更する

        Args:
            db_name: 変更後のデータベース名

        '''
        try:
            cur = self.__con.cursor()
            cur.execute('use %s;' % db_name)
            self.db_name = db_name  # 変更できたらself.db_nameも変更後のdb名に変更しておく
            print('--- データベースを%sに切り替えました ---' % db_name)
            cur.close()
            self.get_tablelist()  # 新たなテーブルリスト取得
        except:
            print('====== change_dbメソッドのエラー文 ======')
            traceback.print_exc()
            print('========= change_dbメソッドのエラー文ここまで =========')

    def get_tablelist(self):
        '''テーブル一覧を取得

        Attributues:
            tablelist([str]): テーブルリスト

        '''
        try:
            cur = self.__con.cursor()
            cur.execute('show tables from %s;' % self.db_name)
            self.tablelist = [row[0] for row in cur.fetchall()]
            cur.close()
        except:
            print('====== get_tablelistメソッドのエラー文 ======')
            traceback.print_exc()
            print('========= get_tablelistメソッドのエラー文ここまで =========')

    def send_query(self, query: str):
        '''returnなしのクエリを叩く

        Args:
            query (str): SQL文

        '''
        try:
            cur = self.__con.cursor()
            cur.execute(query)
            cur.close()
        except:
            print('====== send_queryメソッドのエラー文 ======')
            traceback.print_exc()
            print('========= send_queryメソッドのエラー文ここまで =========')

    def get_query(self, query: str) -> pd.DataFrame:
        '''returnありのクエリを叩く

        Args:
            query (str): SQL文

        Returns:
            pd.DataFrame

        '''
        try:
            cur = self.__con.cursor(dictionary=True)
            cur.execute(query)
            currect_table = pd.io.json.json_normalize(cur.fetchall())
            cur.close()
            return currect_table
        except:
            print('====== get_queryメソッドのエラー文 ======')
            traceback.print_exc()
            print('========= get_queryメソッドのエラー文ここまで =========')

    def get_table(self, tablename: str) -> pd.DataFrame:
        '''テーブルをデータフレームとして取得
        '''
        try:
            return self.get_query('select * from %s;' % tablename)
        except:
            print('====== get_tableメソッドのエラー文 ======')
            traceback.print_exc()
            print('========= get_tableメソッドのエラー文ここまで =========')
            return pd.DataFrame()

    def __insert_or_replace_table(self, method, tablename, new_table: pd.DataFrame):
        '''
        データフレーム(new_table)をtablenameにinsert into or replace intoする
            method: 'insert' or 'replace' or 'INSERT' or 'REPLACE'
        '''
        method = method.upper()
        if method not in ['INSERT', 'REPLACE']:
            raise Exception(
                "method: 'insert' or 'replace' or 'INSERT' or 'REPLACE'")
        try:
            print('==== 新たなテーブルに置き換え ====')
            cur = self.__con.cursor()
            cur.execute('show columns from %s;' % tablename)
            columns = [r[0] for r in cur.fetchall()]
            '''カラムとその順番をrds上のテーブルに合わせる'''
            new_table = new_table.loc[:, columns]
            '''空白文字は半角スペースで置き換える(文字化け防止)'''
            new_table = new_table.applymap(lambda x: re.sub(
                '\s', ' ', x) if type(x) is str else x)
            '''sql文としてのcolumnsとvaluesの指定'''
            columns = ','.join(columns)
            values = [str(tuple(v)) for v in new_table.values.tolist()]
            values = ','.join(values)
            values = re.sub('None([,\)])', 'Null\\1', values)  # Nullに置換する
            values = re.sub('nan([,\)])', 'Null\\1', values)  # Nullに置換する

            sql = '{} INTO {} ({}) VALUES {} ;'.format(
                method, tablename, columns, values)
            cur.execute(sql)
            self.__con.commit()
            cur.close()
        except:
            print('====== __insert_or_replace_tableメソッドのエラー文 ======')
            traceback.print_exc()
            print('========= __insert_or_replace_tableメソッドのエラー文ここまで =========')

    def insert_table(self, tablename: str, new_table: pd.DataFrame):
        '''データフレーム(new_table)をtablenameにinsert intoする
        '''
        self.__insert_or_replace_table('insert', tablename, new_table)

    def replace_table(self, tablename: str, new_table: pd.DataFrame):
        '''データフレーム(new_table)をtablenameにreplace intoする
        '''
        self.__insert_or_replace_table('replace', tablename, new_table)
