import os
import sys
import time
import glob
import datetime
import urllib.parse
import feedparser
from google import genai
from google.genai import types

# 1. 檢查並讀取 API Key
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("❌ 錯誤：找不到 GEMINI_API_KEY！請檢查 GitHub Settings > Secrets 設定。")
    sys.exit(1)

api_key = api_key.strip()
client = genai.Client(api_key=api_key)

today_dt = datetime.datetime.now()
today_str = today_dt.strftime("%Y-%m-%d")
date_display = today_dt.strftime("%Y 年 %m 月 %d 日")

# 建立歷史文章資料夾 posts
os.makedirs("posts", exist_ok=True)
post_filename = f"posts/{today_str}.html"

# 2. 抓取「路透中文網」與「Yahoo 奇摩財經」即時 RSS 新聞
rss_urls = [
    # 路透社中文網焦點
    "https://news.google.com/rss/search?q=site:cn.reuters.com+OR+site:reuters.com+hl:zh-TW&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
    # Yahoo 奇摩財經 (總經、美股、台股、美債)
    "https://news.google.com/rss/search?q=site:tw.stock.yahoo.com+OR+site:finance.yahoo.com+通膨+OR+聯準會+OR+美股+OR+美債+OR+殖利率&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
    # Google News 繁體中文全球金融市場
    "https://news.google.com/rss/search?q=聯準會+OR+美債殖利率+OR+美股三大指數&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
]

raw_news_items = []
print(f"正在從路透中文網及 Yahoo 奇摩財經抓取 {date_display} 最新實時金融新聞...")

for url in rss_urls:
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:6]: # 每個 Feed 擷取前 6 條新聞，精簡 Token 消耗
            title = entry.get('title', '')
            published = entry.get('published', '')
            summary = entry.get('summary', '')[:120]
            raw_news_items.append(f"【時間: {published}】\n標題: {title}\n摘要: {summary}\n")
    except Exception as e:
        print(f"⚠️ 抓取 RSS 失敗 ({url}): {e}")

if not raw_news_items:
    print("❌ 未能成功抓取到金融新聞資料！")
    sys.exit(1)

news_context = "\n".join(raw_news_items)
print(f"✅ 成功抓取 {len(raw_news_items)} 則精選新聞資料！")

# 3. 構建「機構級金融研報」Prompt
prompt = f"""
你是一位機構級的高級總體經濟分析師與資深財經主編。

今天確切的日期是：{date_display}。

以下是今天從「路透社中文網 (Reuters)」與「Yahoo 奇摩財經 (Yahoo Finance)」擷取的最新即時新聞與市場資料：

=== 今日中文財經新聞原始資料 ===
{news_context}
================================

【任務要求 - 深度機構級金融研報】：
請根據上述原始新聞，編譯並整理為一份內容詳實、論述完整且富含數據的《每日金融市場要聞》。

【寫作指南】：
1. **內容充實度**：請對每個新聞主題進行完整的段落寫作與分析，包含：
   - **事件與數據**：指數漲跌幅 %、美債殖利率 bp 變化、通膨率 %、央行目標利率及資產價格。
   - **市場影響與機構觀點**：說明該事件對債券殖利率曲線、股票估值或匯率帶來的影響。
2. **語系與金融術語**：請統一使用**標準繁體中文**及台灣金融市場用語（如：殖利率、聯準會、通膨、晶片、軟體、基點 bps）。
3. **嚴格防幻覺**：分析必須嚴格基於提供的新聞資料，絕不允許提及過去年份的歷史舊事件（如 2025 年初或更早的舊新聞）。

【報告章節結構】：
請將新聞內容分類為以下四個章節：
一、全球金融市場焦點與數據速覽
二、總體經濟、央行政策與債券市場
三、科技產業與企業財務動態
四、外匯、大宗商品與信用市場

【格式要求】：
- 使用繁體中文。
- 關鍵數字與百分比請以 <strong> 標籤加粗顯示。
- 格式直接輸出為排版美觀的 HTML 內文（使用 <h2>, <h3>, <ul>, <li>, <strong>, <p> 等標籤）。
"""

# 4. 呼叫 Gemini API (加入 gemini-2.5-flash 作為備用模型)
models_to_try = ['gemini-3.8-flash', 'gemini-2.5-flash']
content_html = None

for model_name in models_to_try:
    print(f"🔄 開始嘗試模型: {model_name}...")
    for attempt in range(1, 4): # 每個模型嘗試 3 次
        try:
            print(f"正在發送 API 請求 (模型: {model_name}, 第 {attempt} 次嘗試)...")
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
                )
            )
            content_html = response.text
            print("✅ 成功取得 API 回應！")
            break
        except Exception as e:
            wait_time = attempt * 20 # 等待時間拉長至 20s、40s，給配額充分冷卻
            print(f"⚠️ 失敗原因: {e}")
            print(f"⏳ 等待 {wait_time} 秒後進行下一次重試...")
            time.sleep(wait_time)
    
    if content_html:
        break

if not content_html:
    print("❌ API 伺服器持續繁忙或配額不足，請稍後再試。")
    sys.exit(1)

# 5. 寫入當天的獨立文章頁面
post_html_template = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>每日金融市場要聞 - {today_str}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.6; max-width: 850px; margin: 0 auto; padding: 20px; color: #333; background: #f9f9f9; }}
        .container {{ background: #fff; padding: 35px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
        h1 {{ color: #111; border-bottom: 2px solid #2c3e50; padding-bottom: 12px; font-size: 1.9em; }}
        h2 {{ color: #2c3e50; margin-top: 30px; border-bottom: 1px solid #eee; padding-bottom: 6px; font-size: 1.4em; }}
        h3 {{ color: #34495e; margin-top: 20px; font-size: 1.15em; }}
        p {{ margin-bottom: 12px; font-size: 1.02em; }}
        ul {{ padding-left: 22px; margin-bottom: 15px; }}
        li {{ margin-bottom: 10px; line-height: 1.7; }}
        strong {{ color: #c0392b; }} /* 數據加粗紅字強調 */
        a {{ color: #3498db; text-decoration: none; }}
        .back-link {{ display: inline-block; margin-bottom: 15px; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <a href="../index.html" class="back-link">← 返回首頁文章目錄</a>
        <h1>每日金融市場要聞</h1>
        <div style="color: #7f8c8d;">日期：{today_str}（路透中文網 & Yahoo 奇摩財經 深度編譯）</div>
        <hr>
        {content_html}
    </div>
</body>
</html>
"""

with open(post_filename, "w", encoding="utf-8") as f:
    f.write(post_html_template)

# 6. 掃描 posts 資料夾，更新首頁 index.html
all_posts = glob.glob("posts/*.html")
all_posts.sort(reverse=True)

list_items = ""
for post_path in all_posts:
    date_part = os.path.basename(post_path).replace(".html", "")
    list_items += f'<li><a href="{post_path}">【{date_part}】每日金融市場要聞（路透 & Yahoo 財經摘要）</a></li>\n'

index_html_template = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>每日金融市場要聞 - 歷史存檔</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.6; max-width: 850px; margin: 0 auto; padding: 20px; color: #333; background: #f9f9f9; }}
        .container {{ background: #fff; padding: 35px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
        h1 {{ color: #111; border-bottom: 2px solid #2c3e50; padding-bottom: 10px; }}
        ul.post-list {{ list-style-type: none; padding: 0; }}
        ul.post-list li {{ padding: 12px 0; border-bottom: 1px solid #eee; }}
        ul.post-list a {{ color: #2c3e50; text-decoration: none; font-size: 1.1em; font-weight: 500; }}
        ul.post-list a:hover {{ color: #3498db; text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>每日金融市場要聞</h1>
        <p>自動彙整路透社中文網與 Yahoo 奇摩財經最新總體經濟數據、央行動態與金融市場深度剖析。</p>
        <hr>
        <h2>歷史文章列表（點擊觀看詳細內容）</h2>
        <ul class="post-list">
            {list_items}
        </ul>
    </div>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(index_html_template)

print("🎉 歷史文章與首頁更新完畢！")
