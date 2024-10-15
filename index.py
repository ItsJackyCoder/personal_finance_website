# 最主要的伺服器文件
# 只要更動code並儲存後,就會自己重新跑過一次伺服器,所以只要確認伺服器是否還在運行就可以了
# request:要接收到使用者資料所需要用到的module
# g:flask連接資料庫所需要的東西
# redirect:可以讓使用者導回主畫面的模組
import os  # 為了隱藏圓餅圖的文字(如果static裡面沒有資料就不顯示文字)
from flask import Flask, render_template, request, g, redirect, session, jsonify
import sqlite3
import uuid
import requests  # 為了全球即時匯率的API而使用的module
import math
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("agg")  # 老師說照寫就好

app = Flask(__name__)

# 設置 secret_key，確保使用者的 session 是安全的
app.secret_key = os.urandom(24)  # 使用隨機生成的密鑰

database = "datafile.db"


# 和flask使用sqlite3的官方文件所寫的文檔會有些不同
# 老師覺得這麼寫比較簡便
def get_db():
    # hasattr():hasattribute,去查看g有沒有一個attribute是sqlite_db
    if not hasattr(g, "sqlite_db"):
        g.sqlite_db = sqlite3.connect(database)

    return g.sqlite_db


# # 檢查使用者 session 是否存在於資料庫
# def check_user_in_db(session_id):
#     pass
    # conn = get_db()
    # cursor = conn.cursor()
    # cursor.execute("SELECT * FROM users WHERE sessionID = ?", (session_id,))

    # user = cursor.fetchone()

    # return user

    # 插入新的使用者資料到資料庫


# def insert_user(session_id):
#     pass
    # conn = get_db()
    # cursor = conn.cursor()
    # cursor.execute("INSERT INTO users (sessionID) VALUES (?)", (session_id,))

    # conn.commit()

    # 刪除使用者資料


# def delete_user(session_id):
#     pass
    # conn = get_db()
    # cursor = conn.cursor()
    # cursor.execute("DELETE FROM users WHERE sessionID = ?", (session_id,))
    # cursor.execute("DELETE FROM cash WHERE sessionID = ?", (session_id,))
    # cursor.execute("DELETE FROM stock WHERE sessionID = ?", (session_id,))

    # conn.commit()


@app.teardown_appcontext
# exception代表要是有發生什麼exception的話,它就會在此參數的位置(在這裡老師不會用到,但還是寫了)
# close_connection()在任何HTTP request結束時,都會被執行一次。
# e.g.按「重新整理」,也就是重新送了一個HTTP request到我們的伺服器,
# 當我們伺服器處理完這個HTTP request之後,就會執行以下的close_connection()
def close_connection(exception):  # 這個function是被自動執行的
    # 這行是老師為了讓我們知道這個function是自動被執行才寫的
    # print("我們正在關閉sql connection......")

    if hasattr(g, "sqlite_db"):
        g.sqlite_db.close()


# @app.route('/submit_code', methods=['POST'])
# def submit_code():
#     data = request.json
#     code = data.get('code')

#     # 儲存到資料庫
#     conn = get_db()
#     cursor = conn.cursor()
#     cursor.execute('INSERT INTO users (userID) VALUES (?)', (code,))
#     cursor.commit()

#     return jsonify({"status": "success"})


@app.route('/logout', methods=['POST'])
def logout():
    # 刪除 session 中的 user_id
    session.clear()  # 清除 session 表示登出

    return jsonify({"message": "Logged out successfully!"})


# 待改正
@app.route('/login', methods=['GET'])
def check_login_status():
    if 'user_id' in session:
        # 如果 session 裡有 user_id，表示已登入
        return jsonify({"is_logged_in": True})
    else:
        # 沒有 session，表示未登入
        return jsonify({"is_logged_in": False})


@app.route("/")
def home():
    # 如果 session 不存在，生成新的 session_id
    # if 'session_id' not in session:
    #     session['session_id'] = str(uuid.uuid4())

    # session_id = session['session_id']

    # # 檢查使用者是否已經在資料庫中
    # user = check_user_in_db(session_id)

    # if not user:
    #     # 如果使用者不在資料庫中，插入資料
    #     insert_user(session_id)

    # print(session_id)

    userID = session.get('user_id')
    # userID = request.values["userCodeInput"]

    # 除了要render index.html之外,也要顯示出我們現金庫存的狀況
    conn = get_db()
    cursor = conn.cursor()
    result = cursor.execute(
        "select * from cash where userID = ? order by date_info ASC", (userID,))  # 升序
    cash_result = result.fetchall()  # a list of tuple

    # 測試用
    # print(userID)
    # print(cash_result)
    # print(cursor.execute("select * from cash").fetchall())
    # print(cursor.execute("select * from stock").fetchall())
    # print(cursor.execute("select * from users").fetchall())

    # 計算台幣與美金的總額
    taiwanese_dollars = 0
    us_dollars = 0

    for data in cash_result:
        taiwanese_dollars += data[1]
        us_dollars += data[2]

    # 獲取匯率資訊
    # r是個reponse(就是你的HTTP的回應)
    r = requests.get('https://tw.rter.info/capi.php')

    # r.json():會幫我們把獲得的r裡面的這些資料把它整理出來
    # currency是個dictionary,然後裡面的value又是一個dictionary
    # e.g.{'USDCNH': {'Exrate': 7.047633, 'UTC': '2024-10-08 07:59:59'}}
    currency = r.json()
    total = math.floor(taiwanese_dollars + us_dollars *
                       currency["USDTWD"]["Exrate"])  # 因為美金換成台幣有小數點,想把它換成整數

    # 取得所有股票資訊
    result2 = cursor.execute(
        """select * from stock where userID = ?""", (userID,))

    # a list of tuple
    # e.g. [(1, '0050', 100, 120.0, 15, 0, '2024-10-10')]
    stock_result = result2.fetchall()

    unique_stock_list = []  # a list of string

    # 找出每一個股票代號(不重複)
    for data in stock_result:
        if data[1] not in unique_stock_list:
            unique_stock_list.append(data[1])

    # 計算股票總市值
    total_stock_value = 0

    # 計算單一股票資訊
    stock_info = []

    # 標記每個股票的識別碼
    # stock_count = 0

    for stock in unique_stock_list:
        result = cursor.execute(
            """select * from stock where stock_id = ? and userID = ?""", (stock, userID))

        result = result.fetchall()  # 這裡的result是一個list

        stock_cost = 0  # 單一股票總花費
        shares = 0  # 單一股票股數

        for d in result:
            shares += d[2]

            # d[2]:股數, d[3]:價格, d[4]:手續費, d[5]:稅
            stock_cost += d[2] * d[3] + d[4] + d[5]

        # 證交所的API(老師說錄影當下時,它們的documentation寫得非常差)
        # 取得目前股價
        # 這是要發HTTP request到的地方
        url = "https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&stockNo=" + stock
        response = requests.get(url)
        data = response.json()  # 和第56行一樣的語法

        # data這個key的value是一個 alist of list
        # e.g.'data': [['113/10/01', '9,883,064', '1,816,503,951', '183.90', '184.60', '183.35', '183.60', '-0.35', '12,966']]
        price_array = data['data']

        # 最新日期的收盤價是存在這個price_array此list的最後一項
        # price_array[len(price_array)-1]也是一個list
        # 拿到收盤價後,要轉成float,因為原本是一個string
        current_price = float(
            price_array[len(price_array)-1][6].replace(",", ""))  # 我自己補上的,因為float()無法處理包含逗號的數字

        # 單一股票總市值
        # 老師把它換成一個整數
        total_value = round(current_price * shares)  # 或是int():直接截斷小數位數
        total_stock_value += total_value

        # 單一股票平均成本
        average_cost = round(stock_cost / shares, 2)  # 取到小數點後第二位

        # 單一股票的報酬率
        # 因為index.html的報酬率是用百分比呈現的,所以要*100
        rate_of_return = round((total_value - stock_cost)
                               * 100 / stock_cost, 2)

        # stock_count += 1

        # 把上面所有算的單一個股的資訊把它存進stock_info裡面
        stock_info.append({"stock_id": stock, "stock_cost": stock_cost, "total_value": total_value,
                          "average_cost": average_cost, "shares": shares, "current_price": current_price,
                           "rate_of_return": rate_of_return})

    # 計算單一股票占總股票資產的比例
    for stock in stock_info:
        stock["value_percentage"] = round(
            stock["total_value"] * 100 / total_stock_value, 2)

    # 如果unique_stock_list裡面有東西,我們再來繪製股票的圓餅圖,否則則不需要繪製
    # 繪製股票圓餅圖
    if len(unique_stock_list) != 0:
        # 用以下的code就可以繪製圖出來了
        labels = tuple(unique_stock_list)

        # list comprehensive的寫法(直接生成sizes這個新的list)
        sizes = [d["total_value"] for d in stock_info]

        # 根據list裡的資料數量來決定explode的數量
        e1 = [0.05 for i in range(len(stock_info))]

        fig, ax = plt.subplots(figsize=(6, 5))
        ax.pie(sizes, explode=e1, labels=labels,
               colors=['olivedrab', '#9ACD32',
                       '#15B01A', '#AAFF32', '#008000'],
               textprops={"size": "16"}, autopct=None, shadow=None)

        fig.subplots_adjust(top=1, bottom=0, right=1,
                            left=0, hspace=0, wspace=0)
        plt.savefig("static/piechart.jpg", dpi=200)

    else:
        try:  # 嘗試去作remove時,圖片可能會不存在,所以用try...except...去接收這個error
            os.remove("static/piechart.jpg")

        except:  # 如果圖片不存在,我們就不刪除
            pass

    # 繪製股票現金圓餅圖
    if us_dollars != 0 or taiwanese_dollars != 0 or total_stock_value != 0:

        # 為了取得想要隱藏的標籤而做的dicitonary
        hidden_label = {"us_dollars": us_dollars,
                        "taiwanese_dollars": taiwanese_dollars, "total_stock_value": total_stock_value}

        labels = ("USD", "TWD", "STOCK")
        sizes = (us_dollars * currency["USDTWD"]["Exrate"],
                 taiwanese_dollars, total_stock_value)

        # 根據list裡的資料數量來決定explode的數量
        sizes_count = [x for x in list(sizes) if x != 2]

        # 因為如果沒有任何資料或是只有其中一個的話,就不需要explode
        e2 = [0.05 for i in range(
            len(sizes_count))]

        fig, ax = plt.subplots(figsize=(6, 5))
        ax.pie(sizes, explode=e2, labels=labels,
               colors=['olivedrab', '#9ACD32',
                       '#15B01A', '#AAFF32', '#008000'],
               textprops={"size": "16"}, autopct=None, shadow=None)

        fig.subplots_adjust(top=1, bottom=0, right=1,
                            left=0, hspace=0, wspace=0)

        # 取得想要隱藏的標籤
        # plt.gca().texts是自己設定的文本對象(可能不只一個)
        # lbl是hidden_label這個dicitonary的每一個key
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
    # os.path.exists()是一個Boolean,查看此檔案或資料夾是否存在(有教過)
    data = {"show_pic_1": os.path.exists("static/piechart.jpg"), "show_pic_2": os.path.exists("static/piechart2.jpg"), "total": total,
            "currency": currency["USDTWD"]["Exrate"], "ud": us_dollars, "td": taiwanese_dollars, "cash_result": cash_result, "stock_info": stock_info}

    # flask就會自己到templates裡面去找到idex.html,然後去把它顯示出來
    # data=data:這樣在index.html裡面就可以用data這個物件來獲取dictionary裡面的值
    return render_template("index.html", data=data)


@ app.route("/", methods=["POST"])
def sumbit_userID():  # 可以接收到使用者提交出來的資料
    # 1.取得使用者輸入的金額和日期資料
    # 這些request.values的key就是cash.html裡的<input> tag裡的name所設定的值
    userID = request.values["userCodeInput"]
    pwd = request.values["pwdInput"]

    # 測試用-->有成功抓到使用者輸入的正確資訊
    print(userID)
    print(pwd)

    # 2.更新數據庫資料
    # get_db():裡面的code,如果有必要的話,會自動幫我們連接到資料庫
    conn = get_db()
    cursor = conn.cursor()
    result = cursor.execute("""select * from users""")

    users_result = result.fetchall()
    total_users = {}

    for data in users_result:
        name, password = data

        total_users[name] = password

    # 測試用
    print(total_users)

    # 如果帳號不在DB裡,代表是新用戶,所以直接存入DB裡面
    # if userID not in total_users:
    #     cursor.execute("""insert into users (userID, password) values (?,?)""",
    #                    (userID, pwd))

    #     # 儲存在session中,以讓其他的route也能調用此變數
    #     session['user_id'] = userID

    #     conn.commit()

    #     return jsonify({"status": "success"})

    # 帳密都有在DB的話,就給登入
    if (userID, pwd) in users_result:

        # 儲存在session中,以讓其他的route也能調用此變數
        session['user_id'] = userID

        return jsonify({"status": "success"})

    # 如果有此帳號,但沒有此密碼,那就print出「密碼錯誤」
    elif userID in total_users and total_users[userID] != pwd:
        return jsonify({"status": "error", "message": "密碼錯誤!!!"})

    elif userID not in total_users:
        return jsonify({"status": "error", "message": "查無此帳號!!!"})


@ app.route("/register", methods=["POST"])
def register_userID():
    regID = request.values["regUserCode"]
    regPwd = request.values["regPwd"]

    # 測試用-->有成功抓到使用者輸入的正確資訊
    print(regID)
    print(regPwd)

    # 2.更新數據庫資料
    # get_db():裡面的code,如果有必要的話,會自動幫我們連接到資料庫
    conn = get_db()
    cursor = conn.cursor()
    result = cursor.execute("""select * from users""")

    users_result = result.fetchall()
    total_users = {}

    for data in users_result:
        name, password = data

        total_users[name] = password

    print(total_users)

    # 如果沒有重複的帳號,就給註冊
    if regID not in total_users:
        cursor.execute("""insert into users (userID, password) values (?,?)""",
                       (regID, regPwd))

        # 儲存在session中,以讓其他的route也能調用此變數
        session['user_id'] = regID

        conn.commit()

        return jsonify({"status": "success"})

    # 如果有此帳號,那就print出「帳號已有人使用!」
    elif regID in total_users:
        return jsonify({"status": "error", "message": "帳號已有人使用!!!"})


@ app.route("/cash")
def cash_form():
    return render_template("cash.html")


# 設定新的route來接收cash.html的表單的內容。
# POST methods:在HTTP協議中有說,你如果要對你的伺服器去提交資料的話,
# 這時候就可以使用這個POST methods
@ app.route("/cash", methods=["POST"])
def sumbit_cash():  # 可以接收到使用者提交出來的資料
    userID = session.get('user_id')

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

    # transaction_id會自己去生成
    cursor.execute("""insert into cash (taiwanese_dollars, us_dollars, note, date_info, userID) values (?, ?, ?, ?, ?)""",
                   (taiwanese_dollars, us_dollars, note, date, userID))

    conn.commit()

    # 3.將使用者導回主頁面
    return redirect("/")


@ app.route("/cash-delete", methods=["POST"])
def cash_delete():
    # request.values["id"]必須得跟index.html第50行看不見<input> tag的name的值一致
    transaction_id = request.values["id"]
    userID = session.get('user_id')

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """delete from cash where transaction_id = ? and userID = ?""", (transaction_id, userID))

    conn.commit()

    # 當使用者刪除某一筆資料後,把頁面重新導回到首頁
    return redirect("/")


@ app.route("/stock")
def stock_form():
    return render_template("stock.html")


@ app.route("/stock", methods=["POST"])
def submit_stock():
    userID = session.get('user_id')

    # 1.取得股票資訊、日期資料
    url = "https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&stockNo=" + \
        request.values['stock-id']

    response = requests.get(url)
    data = response.json()

    # 初始化錯誤標記
    error = False

    # 如果查無此股票代碼,就請使用者在重新輸入一次
    if "data" in data:
        stock_id = request.values['stock-id']

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

    # transaction_id可以不用管它
    cursor.execute("""insert into stock (stock_id, stock_num, stock_price, processing_fee, tax, date_info, userID) values (?, ?, ?, ?, ?, ?, ?)""",
                   (stock_id, stock_num, stock_price, processing_fee, tax, date, userID))

    conn.commit()

    # 3.將使用者導回主頁面
    return redirect("/")


@ app.route("/stock-delete", methods=["POST"])
def stock_delete():
    # request.values["id"]必須得跟index.html第50行看不見<input> tag的name的值一致
    stock_id = request.values["stock_id"]
    userID = session.get('user_id')

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """delete from stock where stock_id = ? and userID = ?""", (stock_id, userID))

    conn.commit()

    # 當使用者刪除某一筆資料後,把頁面重新導回到首頁
    return redirect("/")


# 使用者關閉頁面後刪除資料的 API
# @ app.route('/delete_user', methods=['POST'])
# def handle_user_deletion():
#     session_id = session.get('session_id')

#     if session_id:
#         delete_user(session_id)
#         session.pop('session_id', None)  # 清除 session

#     return '', 204


# @ app.route('/clear_session', methods=['POST'])
# def clear_session():
#     session.pop('session_id', None)  # 移除 session_id
#     return '', 204  # No content


# 之前的
# @ app.route('/clear_data', methods=['POST'])
# def clear_data():
#     conn = get_db()
#     cursor = conn.cursor()

#     cursor.execute("DELETE FROM cash")  # 或其他需要清空的資料表
#     cursor.execute("DELETE FROM stock")

#     conn.commit()

#     return '', 204  # 返回204表示請求成功但不返回內容


if __name__ == "__main__":
    import time

    start_time = time.time()  # 開始計時
    app.run(debug=True)
    end_time = time.time()  # 結束計時

    print(f"執行時間: {end_time - start_time:.2f} 秒")  # 輸出執行時間
