# -*- coding: utf-8 -*-
"""
Fournisseur d'actualités financières temps réel sans jeton API.
Combine Yahoo Finance (via yfinance) et le flux RSS Google News pour une couverture complète et illimitée.
"""

import re
import html
import datetime
import requests
import xml.etree.ElementTree as ET
import yfinance as yf


def clean_text(raw_text: str) -> str:
    """Nettoie le texte HTML et les espaces redondants."""
    if not raw_text:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw_text)
    text = html.unescape(text)
    return " ".join(text.split()).strip()


def parse_timestamp(pub_time) -> str:
    """Convertit divers formats de date en chaîne lisible (YYYY-MM-DD HH:MM)."""
    if not pub_time:
        return ""
    try:
        if isinstance(pub_time, (int, float)):
            dt = datetime.datetime.fromtimestamp(pub_time)
            return dt.strftime("%Y-%m-%d %H:%M")
        if isinstance(pub_time, str):
            for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%a, %d %b %Y %H:%M:%S %Z", "%Y-%m-%d %H:%M:%S"):
                try:
                    dt = datetime.datetime.strptime(pub_time[:25].strip(), fmt)
                    return dt.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    continue
            return pub_time[:16]
    except Exception:
        pass
    return str(pub_time)[:16]


def get_yfinance_news(ticker: str, limit: int = 10) -> list:
    """Récupère les actualités via yfinance (compatible anciennes et nouvelles versions)."""
    articles = []
    try:
        t = yf.Ticker(ticker)
        yf_news = t.news or []
        for item in yf_news[:limit]:
            if not isinstance(item, dict):
                continue
            
            # Gestion nouveau format yfinance (imbriqué sous 'content')
            if "content" in item and isinstance(item["content"], dict):
                cnt = item["content"]
                title = clean_text(cnt.get("title", ""))
                summary = clean_text(cnt.get("summary", ""))
                pub_date = parse_timestamp(cnt.get("pubDate") or cnt.get("displayTime"))
                provider = ""
                if isinstance(cnt.get("provider"), dict):
                    provider = cnt["provider"].get("displayName", "Yahoo Finance")
                link = ""
                if isinstance(cnt.get("canonicalUrl"), dict):
                    link = cnt["canonicalUrl"].get("url", "")
                elif isinstance(cnt.get("clickThroughUrl"), dict):
                    link = cnt["clickThroughUrl"].get("url", "")
            else:
                title = clean_text(item.get("title", ""))
                summary = clean_text(item.get("summary", ""))
                pub_date = parse_timestamp(item.get("providerPublishTime"))
                provider = item.get("publisher", "Yahoo Finance")
                link = item.get("link", "")
            
            if title:
                articles.append({
                    "title": title,
                    "summary": summary,
                    "publisher": provider or "Yahoo Finance",
                    "published": pub_date,
                    "link": link,
                    "source": "Yahoo"
                })
    except Exception as e:
        print(f"⚠️ [Yahoo News] {ticker}: {e}")
    
    return articles


def get_google_news_rss(query: str, limit: int = 8) -> list:
    """Récupère les actualités via Google News RSS (aucun quota, gratuit)."""
    articles = []
    try:
        url = f"https://news.google.com/rss/search?q={query}+stock&hl=en-US&gl=US&ceid=US:en"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        res = requests.get(url, headers=headers, timeout=6)
        if res.status_code == 200:
            root = ET.fromstring(res.content)
            for item in root.findall(".//item")[:limit]:
                title_elem = item.find("title")
                link_elem = item.find("link")
                pub_elem = item.find("pubDate")
                source_elem = item.find("source")

                title = clean_text(title_elem.text if title_elem is not None else "")
                link = link_elem.text if link_elem is not None else ""
                pub_date = parse_timestamp(pub_elem.text if pub_elem is not None else "")
                publisher = source_elem.text if source_elem is not None else "Google News"

                if title:
                    articles.append({
                        "title": title,
                        "summary": "",
                        "publisher": publisher,
                        "published": pub_date,
                        "link": link,
                        "source": "Google"
                    })
    except Exception as e:
        print(f"⚠️ [Google News RSS] {query}: {e}")

    return articles


def get_news(ticker: str, limit: int = 15) -> list:
    """
    Récupère un flux combiné et dédupliqué d'actualités pour un ticker donné.
    100% gratuit et sans limite de jetons API.
    """
    clean_ticker = ticker.split(".")[0]
    articles = []

    # 1. Yahoo Finance direct
    yf_articles = get_yfinance_news(ticker, limit=limit)
    articles.extend(yf_articles)

    # 2. Si pas assez de news, complément Google News
    if len(articles) < limit:
        g_articles = get_google_news_rss(clean_ticker, limit=limit - len(articles))
        articles.extend(g_articles)

    # 3. Déduplication par titre normalisé
    seen_titles = set()
    unique_articles = []
    for art in articles:
        norm_title = re.sub(r"[^a-zA-Z0-9]", "", art["title"].lower())[:40]
        if norm_title and norm_title not in seen_titles:
            seen_titles.add(norm_title)
            unique_articles.append(art)

    return unique_articles[:limit]