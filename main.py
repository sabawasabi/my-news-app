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

def _get_news_robust(url, keywords=None):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        # XMLとして解析
        soup = BeautifulSoup(resp.content, "xml")
        items = []
        
        # 'item' または 'entry' (Atom形式) の両方を探す
        raw_items = soup.find_all(["item", "entry"])
        
        for item in raw_items:
            # タイトルとリンクを柔軟に取得
            title = (item.title.text if item.title else "").strip()
            link = ""
            if item.link:
                # RSSなら .text、Atomなら ['href'] に入っていることが多い
                link = item.link.text if not item.link.has_attr('href') else item.link['href']
            
            if not title: continue

            # キーワードチェック（あれば）
            if keywords:
                if any(k.lower() in title.lower() for k in keywords):
                    items.append((title, link))
            else:
                items.append((title, link))
            
            if len(items) >= 3: break
        return items
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return []

def main():
    # 1. アークナイツ (4Gamer RSS)
    # キーワードをあえて「ア」など一文字にして、まずはヒットするか確認するのも手です
    ark_news = _get_news_robust("https://www.4gamer.net/rss/index.xml", ["アークナイツ"])
    
    # 2. ゲーム総合 (4Gamer RSS)
    game_news = _get_news_robust("https://www.4gamer.net/rss/index.xml")
    
    # 3. 技術系 (Zenn RSS)
    zenn_news = _get_news_robust("https://zenn.dev/topics/python/feed")

    # メッセージ構築（ここは前回と同じ）
    lines = ["*【本日のニュース配信（再調整版）】*"]
    sections = [
        ("🔹 アークナイツ関連", ark_news),
        ("🎮 ゲーム総合", game_news),
        ("🐍 Python技術", zenn_news)
    ]
    for title, data in sections:
        lines.append(f"\n*{title}*")
        if data:
            for i, (t, u) in enumerate(data, 1):
                lines.append(f"{i}. {t}\n   {u}")
        else:
            lines.append("   (本日の新着は見つかりませんでした)")

    message = "\n".join(lines)
    print(message)
    
    if SLACK_WEBHOOK_URL:
        requests.post(SLACK_WEBHOOK_URL, json={"text": message})
        print("Slackへ送信しました！")

if __name__ == "__main__":
    main()