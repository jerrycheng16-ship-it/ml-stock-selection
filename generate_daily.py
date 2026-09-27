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

today_str = datetime.datetime.now().strftime("%Y-%m-%d")

# 建立歷史文章資料夾 posts
os.makedirs("posts", exist_ok=True)
post_filename = f"posts/{today_str}.html"

# 2. 抓取聚焦於「金融市場與總體經濟數據」的即時新聞 RSS
rss_urls = [
    "https://news.google.com/rss/search?q=site:wsj.com+market+OR+economy+OR+Fed&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=Federal+Reserve+OR+inflation+OR+yields+OR+treasury&hl=en-US&gl=US&ceid=US:en",
    "https://feeds.a.dj.com/rss/RSSMarketsMain.xml"
]

raw_news_items = []
print("正在抓取全球金融市場與總體經濟最新新聞...")

for url in rss_urls:
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:8]:
            title = entry.get('title', '')
            published = entry.get('published', '')
            link = entry.get('link', '')
            raw_news_items.append(f"【發布時間: {published}】\n標題: {title}\n連結: {link}\n")
    except Exception as e:
        print(f"⚠️ 抓取 RSS 失敗 ({url}): {e}")

if not raw_news_items:
    print("❌ 未能成功抓取到金融新聞資料！")
    sys.exit(1)

news_context = "\n".join(raw_news_items)
print(f"✅ 成功抓取 {len(raw_news_items)} 則金融市場與經濟數據相關新聞！")

# 3. 構建專業金融分析 Prompt
prompt = f"""
你是一位專業的機構級金融分析師與總體經濟研究員。

以下是今天（{today_str}）全球主要權威財經媒體（含 WSJ、Bloomberg、Reuters 等）發布的最新即時新聞列表：

=== 今日金融市場與經濟原始新聞資料 ===
{news_context}
=======================================

【任務與報導重點】：
請根據上述「真實新聞標題資料」，將內容翻譯並編譯為一份專業的《每日金融市場要聞》。

1. **報導核心聚焦**：
   - **總體經濟與央行政策**：關注聯準會 (Fed) 利率路徑、CPI/PCE 通膨數據、非農就業、GDP 及美債殖利率變化。
   - **金融市場動態**：美股三大指數、外匯市場、大宗商品（原油、黃金）及加密貨幣走勢。
   - **產業與科技巨頭**：AI 算力產業鏈、半導體業及大型科技股（Magnificent 7）動向。

2. **嚴格防幻覺規範**：
   - 僅能根據提供的原始標題資料進行翻譯、整理與分類。
   - 絕不可補充任何未在列表中出現的歷史舊事件或自行編造數據。

3. **格式要求**：
   - 請將新聞分類為四個章節：
     一、全球金融市場焦點
     二、總體經濟與央行政策
     三、科技產業與企業動態
     四、大宗商品與外匯市場
   - 使用繁體中文。
   - 格式直接輸出為排版美觀的 HTML 內文（包含 <h2>, <h3>, <ul>, <li>, <strong> 等標籤）。
"""

# 4. 呼叫 Gemini API
models_to_try = ['gemini-3.8-flash']
content_html = None

for model_name in models_to_try:
    print(f"🔄 開始嘗試模型: {model_name}")
    for attempt in range(1, 5):
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
            wait_time = attempt * 10
            print(f"⚠️ 失敗原因: {e}")
            print(f"⏳ 等待 {wait_time} 秒後進行下一次重試...")
            time.sleep(wait_time)
    
    if content_html:
        break

if not content_html:
    print("❌ API 伺服器持續繁忙，請過一段時間後再手動觸發。")
    sys.exit(1)

# 5. 寫入當天的獨立文章頁面
post_html_template = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>每日金融市場要聞 - {today_str}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; color: #333; background: #f9f9f9; }}
        .container {{ background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }}
        h1 {{ color: #111; border-bottom: 2px solid #2c3e50; padding-bottom: 10px; font-size: 1.8em; }}
        h2 {{ color: #2c3e50; margin-top: 25px; border-bottom: 1px solid #eee; padding-bottom: 5px; }}
        ul {{ padding-left: 20px; }}
        li {{ margin-bottom: 8px; }}
        a {{ color: #3498db; text-decoration: none; }}
        .back-link {{ display: inline-block; margin-bottom: 15px; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <a href="../index.html" class="back-link">← 返回首頁文章目錄</a>
        <h1>每日金融市場要聞</h1>
        <div style="color: #7f8c8d;">日期：{today_str}（即時金融數據與市場編譯）</div>
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
    list_items += f'<li><a href="{post_path}">【{date_part}】每日金融市場要聞與總經解讀</a></li>\n'

index_html_template = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>每日金融市場要聞 - 歷史存檔</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; color: #333; background: #f9f9f9; }}
        .container {{ background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }}
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
        <p>自動追蹤全球總體經濟、央行利率政策、美債殖利率與金融市場最新動態。</p>
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
