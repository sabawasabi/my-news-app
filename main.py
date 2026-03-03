import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

def _get_news(url, keywords=None):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "xml") # RSS(XML)形式を読み込む
        items = []
        for item in soup.find_all("item")[:10]: # 多めに取ってから絞る
            title = item.title.text
            link = item.link.text
            if keywords:
                if any(k in title.lower() for k in keywords):
                    items.append((title, link))
            else:
                items.append((title, link))
            if len(items) >= 3: break
        return items
    except:
        return []

def main():
    # ニュース取得を飛ばして、テストメッセージだけ作る
    message = "【テスト通知】プログラムは動いています！ニュース取得だけ再調整が必要です。"
    print(message)
    
    # Slack送信
    if SLACK_WEBHOOK_URL:
        response = requests.post(SLACK_WEBHOOK_URL, json={"text": message})
        print(f"Slack送信結果ステータス: {response.status_code}") # 200なら成功
    else:
        print("Webhook URLが設定されていません")

if __name__ == "__main__":
    main()