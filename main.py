import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os

# .envファイルから環境変数を読み込む
load_dotenv()

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

def post_news_to_slack(news_list):
    """
    ニュースのリスト（(title, url)）をSlackに投げる。
    """
    if not news_list:
        return
    if not SLACK_WEBHOOK_URL:
        print("SLACK_WEBHOOK_URL is not set in the .env file.")
        return
    for title, url in news_list:
        # タイトルを太字、冒頭に絵文字、タイトルとURLの間を1行空ける
        text = f"📢 *{title}*\n\n{url}"
        payload = {
            "text": text
        }
        try:
            response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
            response.raise_for_status()
        except Exception as e:
            print(f"Error posting to Slack: {e}")

def fetch_itmedia_news_top(limit: int = 5):
    keywords = ["AI", "クラウド", "セキュリティ"]  # フィルタリング用キーワードを定義

    url = "https://www.itmedia.co.jp/news/"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    resp = requests.get(url, headers=headers, timeout=10)
    resp.encoding = resp.apparent_encoding
    resp.raise_for_status()  # エラー時に例外を投げる

    soup = BeautifulSoup(resp.text, "html.parser")

    # トップストーリー枠（colBoxTopStories）から記事一覧を取得
    news_links = []
    base_url = "https://www.itmedia.co.jp"

    top_stories = soup.find("div", id="colBoxTopStories")
    if not top_stories:
        print("colBoxTopStories not found")
        return

    # .colBoxTitle 内の a タグが記事タイトル＋リンク
    for a in top_stories.select(".colBoxTitle a"):
        title = (a.get_text() or "").strip()
        href = (a.get("href") or "").strip()
        if not title or not href:
            continue

        # href が相対パスならサイトの base を補う
        if href.startswith("/"):
            href = base_url + href
        elif not href.startswith("http"):
            href = base_url + "/" + href.lstrip("/")

        # 見出しに keywords のいずれかが含まれている場合のみ追加
        if any(keyword in title for keyword in keywords):
            news_links.append((title, href))

    # 重複を除外
    seen = set()
    unique_news = []
    for title, href in news_links:
        if href not in seen and len(title) > 0:
            seen.add(href)
            unique_news.append((title, href))

    # 上位 limit 件だけ取り出し
    news_to_notify = unique_news[:limit]

    # 上位 limit 件だけ出力
    for i, (title, href) in enumerate(news_to_notify, start=1):
        print(f"{i}. {title}")
        print(f"   {href}")
        print()

    # ニュースが1件以上あった場合のみSlack通知
    if news_to_notify:
        post_news_to_slack(news_to_notify)

if __name__ == "__main__":
    fetch_itmedia_news_top(limit=5)