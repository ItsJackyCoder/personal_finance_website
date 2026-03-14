# 最主要的伺服器文件
# 只要更動code並儲存後,就會自己重新跑過一次伺服器,所以只要確認伺服器是否還在運行就可以了
# request:要接收到使用者資料所需要用到的module
# g:flask連接資料庫所需要的東西
# redirect:可以讓使用者導回主畫面的模組
from mysql.connector import pooling  # 連線池
from datetime import date, datetime, time
from zoneinfo import ZoneInfo
import mysql.connector  # MySQL資料庫
import os  # 為了隱藏圓餅圖的文字(如果static裡面沒有資料就不顯示文字)
from flask import Flask, render_template, request, g, redirect, session, jsonify
# import uuid
import numpy as np
import requests  # 為了全球即時匯率的API而使用的module
import math
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("agg")  # 照寫就好

app = Flask(__name__)

# 設置secret_key,確保使用者的session是安全的
app.secret_key = os.urandom(24)  # 使用隨機生成的密鑰

# MySQL資料庫配置
DB_CONFIG = {
    'host': os.environ.get("DB_HOST"),  # MySQL主機地址
    'user': os.environ.get("DB_USER"),  # 使用者名稱
    'password': os.environ.get("DB_PASSWORD"),  # 密碼
    'database': os.environ.get("DB_NAME"),  # 資料庫名稱
}


mysql_pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="mysql_pool",
    pool_size=8,
    **DB_CONFIG
)

# Findmind的token
token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wMy0xMiAxNDoxMDoxNyIsInVzZXJfaWQiOiJqYWNreTUzNzI4IiwiZW1haWwiOiJqYWNreTUzNzI4QGdtYWlsLmNvbSIsImlwIjoiNjEuNzQuMzIuMTEyIn0.cXnO9npd-rvHzZ94WGIC5HlUcFWWOnDgB5K3o9hmf-0"


def current_time():  # 取得目前的時間
    return datetime.now(ZoneInfo("Asia/Taipei"))


def get_db():
    if not hasattr(g, "mysql_db"):
        g.mysql_db = mysql_pool.get_connection()  # 從連線池中獲取連線

    return g.mysql_db


@app.teardown_appcontext
def close_connection(exception):  # 這個function是被自動執行的
    db = g.pop("mysql_db", None)  # 從g中獲取mysql_db連線

    if db is not None:
        db.close()


@app.route('/logout', methods=['POST'])
def logout():
    # 刪除session中的user_id
    session.pop("user_id", None)  # 清除 session 表示登出

    return jsonify({"message": "Logged out successfully!"})


@app.route("/")
def home():
    userID = session.get('user_id')
    show_modal = userID is None

    if show_modal:
        data = {
            "show_pic_1": False,
            "show_pic_2": False,
            "total": 0,
            "currency": 0,
            "ud": 0,
            "td": 0,
            "cash_result": [],
            "total_stock_info": [],
            "updated_time": 0
        }

        return render_template("index.html", data=data, show_modal=show_modal)

    # 除了要render index.html之外,也要顯示出我們現金庫存的狀況
    con = get_db()
    cursor = con.cursor()

    cursor.execute(
        "SELECT MIN(last_updated_time) FROM stock WHERE userID=%s", (userID,))

    row = cursor.fetchone()
    last_updated_time = row[0] if row else None

    # 如果資料庫抓出來的是naive datetime,補上台灣時區
    if last_updated_time is not None and last_updated_time.tzinfo is None:
        last_updated_time = last_updated_time.replace(
            tzinfo=ZoneInfo("Asia/Taipei")
        )

    # 更新收盤價(每日下午3點後)
    today_3pm = datetime.combine(current_time().date(), time(
        15, 0), tzinfo=ZoneInfo("Asia/Taipei"))

    # 判斷是否為交易日(週一～週五)
    is_weekday = current_time().weekday() < 5

    if is_weekday and current_time() >= today_3pm and (last_updated_time is None or last_updated_time < today_3pm):
        cursor.execute(
            "SELECT DISTINCT stock_id FROM stock WHERE userID = %s", (userID,))

        stock_ids = cursor.fetchall()  # e.g.[('2330',), ('2317',), ('2454',)]

        for row in stock_ids:
            stock_id = row[0]

            url = "https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockPrice&data_id=" + \
                stock_id + "&start_date=" + \
                current_time().strftime("%Y-%m-%d") + "&token=" + token

            response = requests.get(url)
            api_data = response.json()

            # 防呆
            stock_data = api_data.get("data", [])
            if not stock_data:
                continue

            current_price = stock_data[0].get("close")
            if current_price is None:
                continue

            cursor.execute(
                "UPDATE stock SET current_price = %s, last_updated_time = %s WHERE stock_id= %s AND userID =%s", (
                    current_price, current_time().strftime("%Y-%m-%d %H:%M:%S"), stock_id, userID))

        con.commit()

    cursor.execute(
        "SELECT * FROM cash WHERE userID = %s ORDER BY date_info ASC", (userID,))  # 升序
    cash_result = cursor.fetchall()  # a list of tuple

    # 計算台幣與美金的總額
    taiwanese_dollars = 0
    us_dollars = 0

    for data in cash_result:
        taiwanese_dollars += data[1]
        us_dollars += data[2]

    # 獲取匯率資訊
    # r是個response(就是你的HTTP的回應)
    r = requests.get('https://tw.rter.info/capi.php')

    # r.json():會幫我們把獲得的r裡面的這些資料把它整理出來
    # currency是個dictionary,然後裡面的value又是一個dictionary
    # e.g.{'USDCNH': {'Exrate': 7.047633, 'UTC': '2024-10-08 07:59:59'}}
    currency = r.json()
    total = math.floor(taiwanese_dollars + us_dollars *
                       currency["USDTWD"]["Exrate"])  # 因為美金換成台幣有小數點,想把它換成整數

    # 取得所有股票資訊
    cursor.execute(
        "SELECT * FROM stock WHERE userID = %s", (userID,))

    # a list of tuple
    # e.g. [(1, '0050', '股票名稱',100, 120.0, 15, 0, '2024-10-10')]
    stock_result = cursor.fetchall()

    unique_stock_list = []  # a list of string

    # 找出每一個股票代號(不重複)
    for data in stock_result:
        if data[1] not in unique_stock_list:
            unique_stock_list.append(data[1])

    # 計算股票總市值
    total_stock_value = 0

    # 計算單一股票資訊
    stock_info = []

    # 總體股票的資訊
    total_stock_info = []

    # 紀錄目前最新股價的更新時間
    updated_time = 0

    if len(stock_result) != 0:
        updated_time = stock_result[0][9]

    # 計算總股票成本
    total_stock_cost = 0

    current_price = 0

    for stock in unique_stock_list:
        cursor.execute(
            "SELECT * FROM stock WHERE stock_id = %s and userID = %s", (stock, userID))

        result = cursor.fetchall()  # 這裡的result是一個list

        stock_cost = 0  # 單一股票總花費
        shares = 0  # 單一股票股數

        # stock_name = ""  # 單一股票名稱

        for d in result:
            shares += d[3]

            # d[3]:股數, d[4]:價格, d[5]:手續費, d[6]:稅
            stock_cost += round(d[3] * d[4] + d[5] + d[6])

        # result的回傳類似[(1,....,...),(2,....,...),....]
        current_price = result[-1][10]

        total_stock_cost += stock_cost

        # 單一股票總市值
        # 把它換成一個整數
        total_value = round(current_price * shares)  # 或是int():直接截斷小數位數
        total_stock_value += total_value

        # 把上面所有算的單一個股的資訊把它存進stock_info裡面
        stock_info.append(
            {"stock_id": stock, "total_value": total_value})

    total_profit = round(total_stock_value - total_stock_cost)

    total_stock_info.append({"total_stock_value": total_stock_value, "total_stock_cost": total_stock_cost,
                             "total_profit": total_profit})

    # 如果unique_stock_list裡面有東西,我們再來繪製股票的圓餅圖,否則則不需要繪製

    # 繪製股票圓餅圖
    if len(unique_stock_list) != 0:
        # 用以下的code就可以繪製圖出來了
        labels = tuple(unique_stock_list)

        # list comprehensive的寫法(直接生成sizes這個新的list)
        sizes = [d["total_value"] for d in stock_info]

        # 根據list裡的資料數量來決定explode的數量
        e1 = [0.03 for i in range(len(stock_info))]

        fig, ax = plt.subplots(figsize=(6, 5))
        color_stock = plt.cm.Pastel1(np.linspace(0, 1, len(sizes)))

        ax.pie(sizes, explode=e1, labels=labels,
               colors=color_stock,
               textprops={"size": "13"}, autopct=None, shadow=None)

        fig.subplots_adjust(top=1, bottom=0, right=1,
                            left=0, hspace=0, wspace=0)
        plt.savefig("static/piechart.jpg", dpi=200)

    else:
        try:  # 嘗試去作remove時,圖片可能會不存在,所以用try...except...去接收這個error
            os.remove("static/piechart.jpg")

        except:  # 如果圖片不存在,我們就不刪除
            pass

    # 繪製現金圓餅圖
    if us_dollars != 0 or taiwanese_dollars != 0 or total_stock_value != 0:

        # 為了取得想要隱藏的標籤而做的dictionary
        hidden_label = {"us_dollars": us_dollars,
                        "taiwanese_dollars": taiwanese_dollars, "total_stock_value": total_stock_value}

        twn = max(taiwanese_dollars, 0)
        us = max(us_dollars * currency["USDTWD"]["Exrate"], 0)
        stock = max(total_stock_value, 0)

        if twn == 0:
            twn_label = ""
        else:
            twn_label = "TWD"

        if us == 0:
            us_label = ""
        else:
            us_label = "USD"

        if stock == 0:
            stock_label = ""
        else:
            stock_label = "STOCK"

        labels = (us_label, twn_label, stock_label)

        sizes = (us, twn, stock)

        # 根據list裡的資料數量來決定explode的數量
        sizes_count = [x for x in list(sizes) if x != 2]

        # 因為如果沒有任何資料或是只有其中一個的話,就不需要explode
        e2 = [0.03 for i in range(
            len(sizes_count))]

        fig, ax = plt.subplots(figsize=(6, 5))

        # colors=['olivedrab', '#9ACD32', '#15B01A', '#AAFF32', '#008000']

        # color_cash = plt.cm.YlGn(np.linspace(0.3, 0.9, len(sizes)))
        ax.pie(sizes, explode=e2, labels=labels,
               colors=[
                   "#A9C1A9",
                   "#C8D5B9",
                   "#B7B7A4",
                   "#D4A5A5",
                   "#9BA4B5"
               ],
               textprops={"size": "13"}, autopct=None, shadow=None)

        fig.subplots_adjust(top=1, bottom=0, right=1,
                            left=0, hspace=0, wspace=0)

        # 取得想要隱藏的標籤
        # plt.gca().texts是自己設定的文本對象(可能不只一個)
        # lbl是hidden_label這個dictionary的每一個key
        for txt in plt.gca().texts:
            for lbl in hidden_label:
                if hidden_label["us_dollars"] == 0 and txt.get_text() == "USD":
                    txt.set_visible(False)

                    break

                elif hidden_label["taiwanese_dollars"] == 0 and txt.get_text() == "TWD":
                    txt.set_visible(False)

                    break

                elif hidden_label["total_stock_value"] == 0 and txt.get_text() == "STOCK":
                    txt.set_visible(False)

                    break

        plt.savefig("static/piechart2.jpg", dpi=200)

    else:
        try:  # 嘗試去作remove時,圖片可能會不存在,所以用try...except...去接收這個error
            os.remove("static/piechart2.jpg")

        except:  # 如果圖片不存在,我們就不刪除
            pass

    # 製作一個物件,裡面是我們所有要把它帶到index.html裡面,去填入的數值
    # os.path.exists()是一個Boolean,查看此檔案或資料夾是否存在
    data = {"show_pic_1": os.path.exists("static/piechart.jpg"), "show_pic_2": os.path.exists("static/piechart2.jpg"), "total": total,
            "currency": currency["USDTWD"]["Exrate"], "ud": us_dollars, "td": taiwanese_dollars, "cash_result": cash_result,
            "total_stock_info": total_stock_info, "updated_time": updated_time}

    # flask就會自己到templates裡面去找到idex.html,然後去把它顯示出來
    # data=data:這樣在index.html裡面就可以用data這個物件來獲取dictionary裡面的值
    return render_template("index.html", data=data, show_modal=show_modal)


@app.route("/", methods=["POST"])
def submit_userID():  # 可以接收到使用者提交出來的資料
    # 1.取得使用者輸入的金額和日期資料
    # 這些request.values的key就是cash.html裡的<input> tag裡的name所設定的值
    userID = request.values["userCodeInput"]
    pwd = request.values["pwdInput"]

    # 2.更新數據庫資料
    # get_db():裡面的code,如果有必要的話,會自動幫我們連接到資料庫
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT userID, password FROM users")

    users_result = cursor.fetchall()
    total_users = {}

    for data in users_result:
        name, password = data

        total_users[name] = password

    # 帳密都有在DB的話,就給登入
    if (userID, pwd) in users_result:

        # 儲存在session中,以讓其他的route也能調用此變數
        session['user_id'] = userID

        return jsonify({"status": "success"})

    # 如果有此帳號,但沒有此密碼,那就print出「密碼錯誤」
    elif userID in total_users and total_users[userID] != pwd:
        return jsonify({"status": "error", "message": "Incorrect password!!!"})

    elif userID not in total_users:
        return jsonify({"status": "error", "message": "Account not found!!!"})


@app.route("/register", methods=["POST"])
def register_userID():
    regID = request.values["regUserCode"]
    regPwd = request.values["regPwd"]

    # 2.更新數據庫資料
    # get_db():裡面的code,如果有必要的話,會自動幫我們連接到資料庫
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT userID, password FROM users")

    users_result = cursor.fetchall()
    total_users = {}

    for data in users_result:
        name, password = data
        total_users[name] = password

    # 如果沒有重複的帳號,就給註冊
    if regID not in total_users:
        cursor.execute("INSERT INTO users (userID, password, created_at) VALUES (%s,%s,%s)",
                       (regID, regPwd, current_time().strftime("%Y-%m-%d %H:%M:%S")))

        # 儲存在session中,以讓其他的route也能調用此變數
        session['user_id'] = regID

        conn.commit()

        return jsonify({"status": "success"})

    # 如果有此帳號,那就print出「帳號已有人使用!」
    elif regID in total_users:
        return jsonify({"status": "error", "message": "Account is already in use!!!"})


@app.route("/cash")
def cash_form():
    # 作個權限控管,避免user直接輸入網址進入某個頁面
    if "user_id" not in session:  # 如果user沒有登入,也就沒有Session,所以就導回主頁面
        return redirect("/")
    else:
        # 因為"cash.html"有用了data這個變數,不傳入的話會出現錯誤
        return render_template("cash.html", data=None)


# 設定新的route來接收cash.html的表單的內容。
# POST methods:在HTTP協議中有說,你如果要對你的伺服器去提交資料的話,
# 這時候就可以使用這個POST methods
@app.route("/cash", methods=["POST"])
def submit_cash():  # 可以接收到使用者提交出來的資料
    userID = session.get('user_id')

    transaction_id = request.values["transaction_id"]

    # 1.取得使用者輸入的金額和日期資料
    taiwanese_dollars = 0
    us_dollars = 0

    # 這些request.values的key就是cash.html裡的<input> tag裡的name所設定的值
    if request.values["taiwanese-dollars"] != "":
        taiwanese_dollars = request.values["taiwanese-dollars"]

    if request.values["us-dollars"] != "":
        us_dollars = request.values["us-dollars"]

    note = request.values["note"]
    date = request.values["date"]

    # 2.更新數據庫資料
    # get_db():裡面的code,如果有必要的話,會自動幫我們連接到資料庫
    conn = get_db()
    cursor = conn.cursor()

    if transaction_id != "":  # 如果是非空字串,代表是修改資料
        cursor.execute("UPDATE cash SET taiwanese_dollars=%s, us_dollars=%s, note=%s, date_info=%s WHERE transaction_id=%s",
                       (taiwanese_dollars, us_dollars, note, date, transaction_id))
    else:
        # transaction_id會自己去生成
        cursor.execute("INSERT INTO cash (taiwanese_dollars, us_dollars, note, date_info, userID) VALUES (%s, %s, %s, %s, %s)",
                       (taiwanese_dollars, us_dollars, note, date, userID))

    conn.commit()

    # 3.將使用者導回主頁面
    return redirect("/")


@app.route("/cash-delete", methods=["POST"])
def cash_delete():
    # request.values["id"]必須得跟index.html第50行看不見<input> tag的name的值一致
    transaction_id = request.values["id"]
    userID = session.get('user_id')

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM cash WHERE transaction_id = %s and userID = %s", (transaction_id, userID))

    conn.commit()

    return redirect("/cash-inventory")


@app.route("/cash-update", methods=["POST"])
def cash_update():
    transaction_id = request.values["updateId"]
    userID = session.get('user_id')

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM cash WHERE transaction_id = %s and userID = %s", (transaction_id, userID))

    # 如果用fetchall()會是以陣列形式出現 e.g.[(XXX,XXX)]
    data = cursor.fetchone()  # output:(XXX,XXX)

    return render_template("/cash.html", data=data)


@app.route("/cash-inventory")
def cash_inventory():
    if "user_id" not in session:  # 如果user沒有登入,也就沒有Session,所以就導回主頁面
        return redirect("/")

    userID = session.get('user_id')

    # 除了要render index.html之外,也要顯示出我們現金庫存的狀況
    con = get_db()
    cursor = con.cursor()
    cursor.execute(
        "SELECT * FROM cash WHERE userID = %s ORDER BY date_info DESC", (userID,))  # 降序
    cash_result = cursor.fetchall()  # a list of tuple

    data = {"cash_result": cash_result}

    return render_template("cash-inventory.html", data=data)


@app.route("/stock")
def stock_form():
    # 作個權限控管,避免user直接輸入網址進入某個頁面
    if "user_id" not in session:  # 如果user沒有登入,也就沒有Session,所以就導回主頁面
        return redirect("/")
    else:
        # 因為"stock.html"有用了data這個變數,不傳入的話會出現錯誤
        return render_template("stock.html", data=None)


@app.route("/stock", methods=["POST"])
def submit_stock():  # 提交股票資料時
    userID = session.get('user_id')

    # stock price
    url = "https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockPrice&data_id=" + \
        request.values['stock-id'] + "&start_date=" + \
        current_time().strftime("%Y-%m-%d") + "&token=" + token

    response = requests.get(url)
    data = response.json()

    # 初始化錯誤標記
    error = False

    # 如果查無此股票代碼,就請使用者在重新輸入一次
    if data.get("data"):
        stock_id = request.values['stock-id']
        current_price = data.get("data")[0].get("close")

    else:
        # flash("查無此股票代碼,請重新輸入!")  # 設置一次性訊息
        error = True  # 設置錯誤標記
        stock_id = request.values['stock-id']

        # 保持在同一頁面並傳遞錯誤標記
        return render_template("stock.html", error=error, stock_id=stock_id)

    stock_num = request.values['stock-num']
    stock_price = request.values['stock-price']

    # 因為使用者可能不會填手續費和交易稅
    processing_fee = 0
    tax = 0

    if request.values["processing-fee"] != "":
        processing_fee = request.values["processing-fee"]

    if request.values["tax"] != "":
        tax = request.values["tax"]

    date = request.values["date"]

    # 2.更新數據庫的資料
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM stock_info WHERE stock_id = %s", (stock_id,))

    stock_info = cursor.fetchall()

    # transaction_id可以不用管它
    cursor.execute("INSERT INTO stock (stock_id, stock_name, stock_num, stock_price, processing_fee, tax, date_info, userID, last_updated_time,current_price) VALUES (%s,%s,%s, %s, %s, %s, %s, %s, %s, %s)",
                   (stock_id, None, stock_num, stock_price, processing_fee, tax, date, userID, current_time().strftime("%Y-%m-%d %H:%M:%S"), current_price))

    conn.commit()

    if len(stock_info) == 0:  # 沒找到資料
        # stock name
        url = "https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockInfo&data_id=" + stock_id

        response = requests.get(url)
        data = response.json()

        stock_name = data.get("data")[0].get("stock_name")

        cursor.execute(
            "INSERT INTO stock_info (stock_id, stock_name) VALUES(%s,%s)", (stock_id, stock_name))

        conn.commit()

    # 3.將使用者導回主頁面
    return redirect("/")


@app.route("/stock-inventory")
def stock_inventory():
    if "user_id" not in session:  # 如果user沒有登入,也就沒有Session,所以就導回主頁面
        return redirect("/")

    userID = session.get('user_id')

    # 除了要render index.html之外,也要顯示出我們現金庫存的狀況
    con = get_db()
    cursor = con.cursor()

    # 取得所有股票資訊
    cursor.execute(
        "SELECT * FROM stock WHERE userID = %s", (userID,))

    # a list of tuple
    # e.g. [(1, '0050', '股票名稱',100, 120.0, 15, 0, '2024-10-10')]
    stock_result = cursor.fetchall()

    unique_stock_list = []  # a list of string

    # 找出每一個股票代號(不重複)
    for data in stock_result:
        if data[1] not in unique_stock_list:
            unique_stock_list.append(data[1])

    # 計算股票總市值
    total_stock_value = 0

    # 計算單一股票資訊
    stock_info = []

    # 紀錄目前最新股價的更新時間
    updated_time = 0

    if len(stock_result) != 0:
        updated_time = stock_result[0][9].strftime("%Y-%m-%d")

    current_price = 0

    for stock in unique_stock_list:
        cursor.execute(
            "SELECT * FROM stock WHERE stock_id = %s and userID = %s", (stock, userID))

        result = cursor.fetchall()  # 這裡的result是一個list

        current_price = result[-1][10]
        stock_cost = 0  # 單一股票總花費
        shares = 0  # 單一股票股數
        stock_name = ""  # 單一股票名稱

        for d in result:
            shares += d[3]

            # d[3]:股數, d[4]:價格, d[5]:手續費, d[6]:稅
            stock_cost += round(d[3] * d[4] + d[5] + d[6])

        # 查找股票名字
        stock_id = result[-1][1]

        cursor.execute(
            "SELECT * FROM stock_info WHERE stock_id = %s", (stock_id,))

        result = cursor.fetchall()  # 只會有一筆

        stock_name = result[-1][1]

        # 單一股票總市值
        # 把它換成一個整數
        total_value = round(current_price * shares)  # 或是int():直接截斷小數位數
        total_stock_value += total_value

        # 單一股票平均成本
        average_cost = round(stock_cost / shares, 2)  # 取到小數點後第二位

        # 單一股票的報酬率
        # 因為index.html的報酬率是用百分比呈現的,所以要*100
        rate_of_return = round((total_value - stock_cost)
                               * 100 / stock_cost, 2)

        # 把上面所有算的單一個股的資訊把它存進stock_info裡面
        stock_info.append({"stock_id": stock, "stock_cost": stock_cost, "total_value": total_value,
                          "average_cost": average_cost, "shares": shares, "current_price": current_price,
                           "rate_of_return": rate_of_return, "stock_name": stock_name})

    # 計算單一股票占總股票資產的比例
    for stock in stock_info:
        stock["value_percentage"] = round(
            stock["total_value"] * 100 / total_stock_value, 2)

    # 製作一個物件,裡面是我們所有要把它帶到index.html裡面,去填入的數值
    # os.path.exists()是一個Boolean,查看此檔案或資料夾是否存在
    data = {"stock_info": stock_info,
            "updated_time": updated_time}

    return render_template("stock-inventory.html", data=data)


@app.route("/stock-delete", methods=["POST"])
def stock_delete():
    # request.values["id"]必須得跟index.html第50行看不見<input> tag的name的值一致
    stock_id = request.values["stock_id"]
    userID = session.get('user_id')

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM stock WHERE stock_id = %s and userID = %s", (stock_id, userID))

    conn.commit()

    return redirect("/stock-inventory")


@app.route("/stock-update", methods=["POST"])
def stock_update():
    stockID = request.form["updateStockId"]
    userID = session.get('user_id')

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT SUM(stock_num) FROM stock WHERE stock_id=%s and userId=%s", (stockID, userID))

    stockNumTotal = cursor.fetchone()[0]

    return render_template("/stock-sell.html", stockID=stockID, stockNumTotal=stockNumTotal)


@app.route("/stock-sell", methods=["POST"])
def stock_sell():
    stock_id = request.form["stockSellId"]
    stock_num = int(request.form["stock-num"])
    userID = session.get('user_id')

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT stock_num FROM stock WHERE stock_id=%s and userId=%s ORDER BY date_info ASC", (stock_id, userID))

    data = cursor.fetchall()  # output:[(1000,), (1500,), (3000,)]

    for num in data:
        if stock_num >= num[0]:  # 假如stock_num＝3500
            cursor.execute(
                "SELECT MIN(date_info) FROM stock WHERE stock_id = %s", (stock_id,))
            earliest_date = cursor.fetchone()[0]

            cursor.execute(
                "DELETE FROM stock WHERE stock_id=%s and date_info=%s", (stock_id, earliest_date))

            conn.commit()
            stock_num -= num[0]
        else:
            cursor.execute(
                "SELECT MIN(date_info) FROM stock WHERE stock_id = %s", (stock_id,))
            earliest_date = cursor.fetchone()[0]

            cursor.execute(
                "UPDATE stock SET stock_num=%s WHERE stock_id=%s and date_info=%s", (num[0]-stock_num, stock_id, earliest_date))

            conn.commit()

            break

    return redirect("/")


@app.route("/stock-statement", methods=["POST"])
def stock_statements():
    stockID = request.form["statementsId"]
    userID = session.get('user_id')

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM stock WHERE stock_id = %s and userID = %s ORDER BY date_info DESC", (stockID, userID))

    # 如果用fetchall()會是以陣列形式出現 e.g.[(XXX,XXX)]
    # output:[(4, '6591', 1000, 25.0, 0, 0, datetime.date(2024, 12, 26), 'Jacky'), (5, '6591', 1500, 25.6, 0, 0, datetime.date(2024, 12, 27), 'Jacky')]
    data = cursor.fetchall()

    return render_template("/stock-statement.html", data=data)


if __name__ == "__main__":
    app.run(debug=True)
