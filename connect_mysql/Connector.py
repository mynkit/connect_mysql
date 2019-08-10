import os
import re
import traceback
import mysql.connector
import pandas as pd


class Connector(object):
    def __init__(self, host, db_name, user_name, password):
        """
        * __init__時の処理
            * mysqlへの接続
            * 現在のDBにおけるテーブルリスト(self.tablelist)の取得
        """
        self.host = host
        self.db_name = db_name
        self.user_name = user_name
        self.password = password
        self.__connect()
        self._get_tablelist()

    def __connect(self):
        """
        * passwordは環境変数('estie_database_password')より取得
            * もしなければself.passwordを採用
        """
        self.__con = mysql.connector.connect(
            host=self.host, db=self.db_name, user=self.user_name, password=self.password)
        print("-- 接続完了 --")

    def disconnect(self):
        """
        * mysqlとの接続を終了する
        """
        self.__con.close()
        print("-- 接続終了 --")

    def show_grants(self):
        """
        * 自分(self.user_name)の権限を確認する
        """
        return self.get_query("show grants for %s" % self.user_name)

    def show_dblist(self):
        """
        * データベース一覧を取得
        """
        try:
            cur = self.__con.cursor()
            cur.execute("show databases;")
            print("--- データベースリスト ---")
            print([row[0] for row in cur.fetchall()])
            print("--------------------")
            cur.close()
        except:
            print("====== show_dblistメソッドのエラー文 ======")
            traceback.print_exc()
            print("========= show_dblistメソッドのエラー文ここまで =========")

    def change_db(self, db_name):
        """
        * データベースを変更する
            * db_name: 変更後のデータベース名
        """
        try:
            cur = self.__con.cursor()
            cur.execute("use %s;" % db_name)
            self.db_name = db_name  # 変更できたらself.db_nameも変更後のdb名に変更しておく
            print("--- データベースを%sに切り替えました ---" % db_name)
            cur.close()
            self._get_tablelist()  # 新たなテーブルリスト取得
        except:
            print("====== change_dbメソッドのエラー文 ======")
            traceback.print_exc()
            print("========= change_dbメソッドのエラー文ここまで =========")
        
    def _get_tablelist(self):
        """
        * テーブル一覧を取得
        """
        try:
            cur = self.__con.cursor()
            cur.execute("show tables from %s;" % self.db_name)
            self.tablelist = [row[0] for row in cur.fetchall()]
            cur.close()
        except:
            print("====== _get_tablelistメソッドのエラー文 ======")
            traceback.print_exc()
            print("========= _get_tablelistメソッドのエラー文ここまで =========")

    def send_query(self, query):
        """
        * returnなしのクエリを叩く
        """
        try:
            cur = self.__con.cursor()
            cur.execute(query)
            cur.close()
        except:
            print("====== send_queryメソッドのエラー文 ======")
            traceback.print_exc()
            print("========= send_queryメソッドのエラー文ここまで =========")

    def get_query(self, query):
        """
        * returnありのクエリを叩く
        """
        try:
            query = query.lower()  # sql文を小文字にする
            tablename_candidate = re.findall(
                r"from\s.+?[\s;]", query)[-1] if len(re.findall(r"from\s.+?[\s;]", query)) > 0 else None
            tablename = re.sub(
                r"from\s(.+?)[\s;]", r"\1", tablename_candidate) if tablename_candidate is not None else None
            tablename = tablename if tablename in self.tablelist else None

            cur = self.__con.cursor()
            if tablename is not None:
                cur.execute("show columns from %s;" % tablename)
                columns = [r[0] for r in cur.fetchall()]
                cur.execute(query)
                currect_table = pd.DataFrame(
                    [list(r) for r in cur.fetchall()], columns=columns)
                cur.close()
                return currect_table
            else:
                cur.execute(query)
                items = [r[0] for r in cur.fetchall()]
                cur.close()
                return items
        except:
            print("====== get_queryメソッドのエラー文 ======")
            traceback.print_exc()
            print("========= get_queryメソッドのエラー文ここまで =========")

    def get_table(self, tablename):
        """
        * テーブルをデータフレームとして取得
        """
        try:
            cur = self.__con.cursor()
            cur.execute("show columns from %s;" % tablename)
            columns = [r[0] for r in cur.fetchall()]
            cur.execute("select * from %s;" % tablename)
            currect_table = pd.DataFrame(
                [list(r) for r in cur.fetchall()], columns=columns)
            cur.close()
            return currect_table
        except:
            print("====== get_tableメソッドのエラー文 ======")
            traceback.print_exc()
            print("========= get_tableメソッドのエラー文ここまで =========")
            return pd.DataFrame()

    def show_table(self, tablename):
        """
        tableの中身除く
        """
        try:
            current_table = self.get_table(tablename)
            print("--- %sテーブルの中身除く ---" % tablename)
            print("%sテーブルのレコード数: %d" % (tablename, len(currect_table)))
            print(current_table.head())
            print("---------------------")
        except:
            print("====== show_tableメソッドのエラー文 ======")
            traceback.print_exc()
            print("========= show_tableメソッドのエラー文ここまで =========")

    def __insert_or_replace_table(self, method, tablename, new_table: pd.DataFrame):
        """
        データフレーム(new_table)をtablenameにinsert into or replace intoする
            method: 'insert' or 'replace' or 'INSERT' or 'REPLACE'
        """
        method = method.upper()
        if method not in ["INSERT", "REPLACE"]:
            raise Exception("method: 'insert' or 'replace' or 'INSERT' or 'REPLACE'")
        try:
            print("==== 新たなテーブルに置き換え ====")
            cur = self.__con.cursor()
            cur.execute("show columns from %s;" % tablename)
            columns = [r[0] for r in cur.fetchall()]
            '''カラムとその順番をrds上のテーブルに合わせる'''
            new_table = new_table.loc[:, columns]
            '''空白文字は半角スペースで置き換える(文字化け防止)'''
            new_table = new_table.applymap(lambda x: re.sub(
                "\s", " ", x) if type(x) is str else x)
            '''sql文としてのcolumnsとvaluesの指定'''
            columns = ','.join(columns)
            values = [str(tuple(v)) for v in new_table.values.tolist()]
            values = ','.join(values)
            values = re.sub("None([,\)])", "Null\\1", values)  # Nullに置換する
            values = re.sub("nan([,\)])", "Null\\1", values)  # Nullに置換する

            sql = "{} INTO {} ({}) VALUES {} ;".format(
                method, tablename, columns, values)
            cur.execute(sql)
            self.__con.commit()
            cur.close()
        except:
            print("====== __insert_or_replace_tableメソッドのエラー文 ======")
            traceback.print_exc()
            print("========= __insert_or_replace_tableメソッドのエラー文ここまで =========")

    def insert_table(self, tablename, new_table: pd.DataFrame):
        """
        データフレーム(new_table)をtablenameにinsert intoする
        """
        self.__insert_or_replace_table("insert", tablename, new_table)

    def replace_table(self, tablename, new_table: pd.DataFrame):
        """
        データフレーム(new_table)をtablenameにreplace intoする
        """
        self.__insert_or_replace_table("replace", tablename, new_table)
