import os
import requests
from bs4 import BeautifulSoup
import warnings
import re
from bs4 import XMLParsedAsHTMLWarning
from dotenv import load_dotenv

# 警告を非表示にする
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

load_dotenv()
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

def clean_text(text):
    """<![CDATA[ ... ]]> などのノイズを取り除く"""
    if not text:
        return ""
    # CDATAの中身だけを抽出、またはタグを削除
    text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', text, flags=re.DOTALL)
    return text.strip()

def _get_news_robust(url, keywords=None):
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.content, "html.parser")
        items = []
        
        for raw_item in soup.find_all(["item", "entry"]):
            # タイトルの取得とクリーニング
            title_tag = raw_item.find("title")
            title = clean_text(title_tag.get_text()) if title_tag else ""
            
            # リンクの取得（複数のパターンに対応）
            link = ""
            link_tag = raw_item.find("link")
            if link_tag:
                # テキストノードにあるか、href属性にあるか
                link = link_tag.get_text().strip() or link_tag.get("href") or ""
            
            # それでも取れない場合、guidタグなどを探す（RSSの予備）
            if not link:
                guid_tag = raw_item.find("guid")
                if guid_tag:
                    link = guid_tag.get_text().strip()

            if not title or not link: continue

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
    ark_news = _get_news_robust("https://www.4gamer.net/rss/index.xml", ["アークナイツ"])
    game_news = _get_news_robust("https://www.4gamer.net/rss/index.xml")
    zenn_news = _get_news_robust("https://zenn.dev/topics/python/feed")

    lines = ["*【本日のニュース配信（ハイパーリンク版）】*"]
    sections = [
        ("🔹 アークナイツ関連", ark_news),
        ("🎮 ゲーム総合", game_news),
        ("🐍 Python技術", zenn_news)
    ]
    
    for sect_title, data in sections:
        lines.append(f"\n*{sect_title}*")
        if data:
            for i, (t, u) in enumerate(data, 1):
                # Slackの特殊構文 <URL|表示名> を使用
                lines.append(f"{i}. <{u}|{t}>")
        else:
            lines.append("   (本日の新着は見つかりませんでした)")

    message = "\n".join(lines)
    print(message) # 確認用にターミナルにも出す
    
    if SLACK_WEBHOOK_URL:
        requests.post(SLACK_WEBHOOK_URL, json={"text": message})

if __name__ == "__main__":
    main()