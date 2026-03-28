import os
import requests
from bs4 import BeautifulSoup
import warnings
import re
from bs4 import XMLParsedAsHTMLWarning
from dotenv import load_dotenv

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
load_dotenv()
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

def clean_text(text):
    if not text: return ""
    text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', text, flags=re.DOTALL)
    return text.strip()

def _get_news_robust(url, keywords=None):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        # GitHub Actions環境（lxmlなし）でも動くよう、標準の html.parser を使用
        soup = BeautifulSoup(resp.content, "html.parser")
        
        items = []
        # item(RSS系) または entry(Atom系) を探す
        raw_items = soup.find_all(["item", "entry"])
        
        for raw_item in raw_items:
            # 1. タイトル取得
            title_tag = raw_item.find("title")
            title = clean_text(title_tag.get_text()) if title_tag else ""
            
            # 2. リンク取得 (ここがZenn復活のキモです)
            link = ""
            link_tag = raw_item.find("link")
            if link_tag:
                # Zenn(Atom)は href属性にある。4Gamer(RSS)はタグの中身にある。
                # 両方チェックして、ある方を採用する
                link = link_tag.get("href") or link_tag.get_text().strip()
            
            # 3. 4Gamer(RSS 1.0)特有のリンク補完
            if not link and raw_item.has_attr('rdf:about'):
                link = raw_item['rdf:about']

            if not title or not link:
                continue

            # キーワード判定
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
    print("--- ニュース取得（XML解析版）を開始 ---")
    ark_news = _get_news_robust("https://www.4gamer.net/rss/index.xml", ["アークナイツ"])
    game_news = _get_news_robust("https://www.4gamer.net/rss/index.xml")
    zenn_news = _get_news_robust("https://zenn.dev/topics/python/feed")

    lines = ["*【本日のニュース配信（完全復活版）】*"]
    sections = [("🔹 アークナイツ", ark_news), ("🎮 ゲーム総合", game_news), ("🐍 Python技術", zenn_news)]
    
    for sect_title, data in sections:
        lines.append(f"\n*{sect_title}*")
        if data:
            for i, (t, u) in enumerate(data, 1):
                lines.append(f"{i}. <{u}|{t}>")
        else:
            lines.append("   (新着なし)")

    message = "\n".join(lines)
    print(message)
    
    if SLACK_WEBHOOK_URL:
        requests.post(SLACK_WEBHOOK_URL, json={"text": message})
        print("--- Slack送信完了 ---")
    else:
        print("--- Slack通知はスキップ（URL未設定） ---")

if __name__ == "__main__":
    main()