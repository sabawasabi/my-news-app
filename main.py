import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def _get_soup(url: str) -> BeautifulSoup | None:
    """共通のリクエスト＆BeautifulSoup生成処理。失敗時はNoneを返す。"""
    headers = {"User-Agent": USER_AGENT}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = resp.apparent_encoding
        resp.raise_for_status()
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None
    return BeautifulSoup(resp.text, "html.parser")


def fetch_arknights_news(limit: int = 3):
    """
    ニュースサイト（Yahoo!ニューストップ）から『アークナイツ』を含む最新ニュースを最大limit件取得。
    """
    base_url = "https://news.yahoo.co.jp"
    soup = _get_soup(base_url)
    if soup is None:
        return []

    results: list[tuple[str, str]] = []
    seen_urls: set[str] = set()

    for a in soup.find_all("a"):
        title = (a.get_text() or "").strip()
        if "アークナイツ" not in title:
            continue

        href = (a.get("href") or "").strip()
        if not href or href.startswith("#"):
            continue

        if href.startswith("/"):
            href = base_url + href
        elif not href.startswith("http"):
            href = base_url + "/" + href.lstrip("/")

        if href in seen_urls:
            continue

        seen_urls.add(href)
        results.append((title, href))

        if len(results) >= limit:
            break

    return results


def fetch_game_ranking(limit: int = 3):
    """
    ファミ通のゲームソフト販売本数ランキングから上位limit件を取得。
    構造変化に強くするため、まずtable内、その後ページ全体からゲーム詳細へのリンクを探索。
    """
    url = "https://www.famitsu.com/ranking/game-sales/"
    base_url = "https://www.famitsu.com"
    soup = _get_soup(url)
    if soup is None:
        return []

    def normalize_href(href: str) -> str | None:
        if not href or href.startswith("#"):
            return None
        href = href.strip()
        if href.startswith("/"):
            href = base_url + href
        elif not href.startswith("http"):
            href = base_url + "/" + href.lstrip("/")
        return href

    results: list[tuple[str, str]] = []
    seen_urls: set[str] = set()

    # 1. ランキングtable内を優先的に探索
    table = soup.find("table")
    if table:
        for a in table.find_all("a"):
            title = (a.get_text() or "").strip()
            href = normalize_href(a.get("href") or "")
            if not title or not href:
                continue
            # ゲーム詳細ページらしきリンクのみに限定（パターンマッチ）
            if "/games/detail/" not in href and "/ranking/game-sales/" in href:
                # ランキングページ自身などはスキップ
                continue
            if href in seen_urls:
                continue
            seen_urls.add(href)
            results.append((title, href))
            if len(results) >= limit:
                return results

    # 2. 念のためページ全体からフォールバック検索
    if len(results) < limit:
        for a in soup.find_all("a"):
            title = (a.get_text() or "").strip()
            href = normalize_href(a.get("href") or "")
            if not title or not href:
                continue
            if "/games/detail/" not in href:
                continue
            if href in seen_urls:
                continue
            seen_urls.add(href)
            results.append((title, href))
            if len(results) >= limit:
                break

    return results[:limit]


def fetch_zenn_trend_python_ai(limit: int = 3):
    """
    Zennのトレンド（人気）からPython / AIトピックの記事を合計limit件取得。
    /topics/{topic}?tab=popular 上の /articles/〜 へのリンクを拾う。
    """
    base_url = "https://zenn.dev"
    topics = ["python", "ai"]

    results: list[tuple[str, str]] = []
    seen_urls: set[str] = set()

    for topic in topics:
        url = f"{base_url}/topics/{topic}?tab=popular"
        soup = _get_soup(url)
        if soup is None:
            continue

        for a in soup.find_all("a"):
            href = (a.get("href") or "").strip()
            if not href.startswith("/articles/"):
                continue

            title = (a.get_text() or "").strip()
            if not title:
                continue

            full_url = base_url + href
            if full_url in seen_urls:
                continue

            seen_urls.add(full_url)
            results.append((title, full_url))

            if len(results) >= limit:
                return results

    return results[:limit]


def build_slack_message(
    arknights_news: list[tuple[str, str]],
    game_ranking: list[tuple[str, str]],
    zenn_articles: list[tuple[str, str]],
) -> str:
    """
    3種類の情報を1つのSlackメッセージとして整形する。
    セクションごとに太字見出しを付与。
    """
    lines: list[str] = []

    # アークナイツ関連
    lines.append("*アークナイツ関連ニュース*")
    if arknights_news:
        for i, (title, url) in enumerate(arknights_news, start=1):
            lines.append(f"{i}. {title}")
            lines.append(f"{url}")
    else:
        lines.append("該当するニュースが見つかりませんでした。")
    lines.append("")  # 空行で区切り

    # ゲームランキング
    lines.append("*ゲーム全般：ランキング上位3件*")
    if game_ranking:
        for i, (title, url) in enumerate(game_ranking, start=1):
            lines.append(f"{i}. {title}")
            lines.append(f"{url}")
    else:
        lines.append("ランキング情報を取得できませんでした。")
    lines.append("")

    # Zennトレンド（Python/AI）
    lines.append("*技術系：Zennトレンド（Python / AI）*")
    if zenn_articles:
        for i, (title, url) in enumerate(zenn_articles, start=1):
            lines.append(f"{i}. {title}")
            lines.append(f"{url}")
    else:
        lines.append("関連する記事を取得できませんでした。")

    return "\n".join(lines)


def post_message_to_slack(text: str):
    """1つのテキストメッセージをSlackに送信。"""
    if not text:
        return
    if not SLACK_WEBHOOK_URL:
        print("SLACK_WEBHOOK_URL is not set in the .env file.")
        return

    payload = {"text": text}
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"Error posting to Slack: {e}")


def main():
    # 1. 各種情報を取得
    arknights_news = fetch_arknights_news(limit=3)
    game_ranking = fetch_game_ranking(limit=3)
    zenn_articles = fetch_zenn_trend_python_ai(limit=3)

    # 2. Slack用メッセージを構築
    message = build_slack_message(arknights_news, game_ranking, zenn_articles)

    # 3. コンソール出力（デバッグ用）＆Slack送信
    print(message)
    post_message_to_slack(message)


if __name__ == "__main__":
    main()