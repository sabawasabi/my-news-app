import os
import requests
from bs4 import BeautifulSoup
import warnings
from bs4 import XMLParsedAsHTMLWarning
from dotenv import load_dotenv

# 警告を非表示にする
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

load_dotenv()
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

def _get_news_robust(url, keywords=None):
    # 日本のブラウザを装う（GitHubの海外サーバー感を薄める）
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        # HTMLパーサーで粘り強く解析
        soup = BeautifulSoup(resp.content, "html.parser")
        items = []
        
        # RSS/Atomのどちらでも対応できるように全ての 'item' か 'entry' を探す
        for raw_item in soup.find_all(["item", "entry"]):
            title_tag = raw_item.find("title")
            title = title_tag.get_text().strip() if title_tag else ""
            
            # URL取得を強化：linkタグのテキスト、またはhref属性の両方を探す
            link_tag = raw_item.find("link")
            link = ""
            if link_tag:
                link = link_tag.get_text().strip() or link_tag.get("href") or ""
            
            if not title: continue

            if keywords:
                if any(k.lower() in title.lower() for k in keywords):
                    items.append((title, link))
            else:
                items.append((title, link))
            
            if len(items) >= 3: break
        return items
    except Exception as e:
        print(f"Error: {e}")
        return []

def main():
    ark_news = _get_news_robust("https://www.4gamer.net/rss/index.xml", ["アークナイツ"])
    game_news = _get_news_robust("https://www.4gamer.net/rss/index.xml")
    zenn_news = _get_news_robust("https://zenn.dev/topics/python/feed")

    lines = ["*【本日のニュース配信（完成版）】*"]
    for sect_title, data in [("🔹 アークナイツ関連", ark_news), ("🎮 ゲーム総合", game_news), ("🐍 Python技術", zenn_news)]:
        lines.append(f"\n*{sect_title}*")
        if data:
            for i, (t, u) in enumerate(data, 1):
                lines.append(f"{i}. {t}\n   {u}")
        else:
            lines.append("   (本日の新着は見つかりませんでした)")

    message = "\n".join(lines)
    print(message)
    if SLACK_WEBHOOK_URL:
        requests.post(SLACK_WEBHOOK_URL, json={"text": message})

if __name__ == "__main__":
    main()