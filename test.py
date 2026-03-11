import requests


url = "https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockPrice&data_id=" + \
    "2330" + "&start_date=" + "2026-03-10"

response = requests.get(url)
data = response.json()

current_price = data.get("data")[0].get("close")

print(data)

print(current_price)
