import sqlite3

# 運行這個db_setting.py後,就會在資料庫創建以下兩個table
conn = sqlite3.connect("datafile.db")
cursor = conn.cursor()

# 創建兩個table(表格)
# cash table會紀錄使用者現金庫存的變化
# datetype real:代表是有小數點的數
# datetype varchar(30):代表是一個string
# datetype date:紀錄日期(哪一天作更動的)
cursor.execute(
    """create table cash (transaction_id integer primary key, taiwanese_dollars integer, us_dollars real, note varchar(30), date_info date)""")

# cash table紀錄股票
# datetype varchar(10):是一個string,然後最多10個字
cursor.execute(
    """create table stock (transaction_id integer primary key, stock_id varchar(10), stock_num integer, stock_price real, processing_fee integer, tax integer, date_info date)""")

conn.commit()
conn.close()
