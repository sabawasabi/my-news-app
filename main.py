def _get_news_robust(url, keywords=None):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        
        # 修正ポイント：XMLパーサーがなくても動くようにする
        try:
            # まずは理想的なXMLモードで試す
            soup = BeautifulSoup(resp.content, "xml")
        except Exception:
            # もしXMLモードが使えなければ、標準のHTMLモードで解析する
            soup = BeautifulSoup(resp.content, "html.parser")
        
        items = []
        # XMLでもHTMLでも「item」または「entry」という名前のタグを探す
        raw_items = soup.find_all(["item", "entry"])
        
        for raw_item in raw_items:
            title_tag = raw_item.find("title")
            title = clean_text(title_tag.get_text()) if title_tag else ""
            
            link = ""
            link_tag = raw_item.find("link")
            if link_tag:
                # 属性(href)か中身のテキストか、取れる方を採用
                link = link_tag.get("href") or link_tag.get_text().strip() or ""
            
            # 4Gamer(RSS 1.0)特有の linkタグが空の場合の対策
            if not link and raw_item.has_attr('rdf:about'):
                link = raw_item['rdf:about']

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