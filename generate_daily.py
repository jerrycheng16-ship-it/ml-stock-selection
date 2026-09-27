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

# 2. 抓取聚焦於「具體數據、總經指標與市場走勢」的即時新聞 RSS
rss_urls = [
    "https://news.google.com/rss/search?q=site:wsj.com+inflation+OR+CPI+OR+PCE+OR+yields+OR+Fed&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=Federal+Reserve+interest+rates+yield+curve+treasury&hl=en-US&gl=US&ceid=US:en",
    "https://feeds.a.dj.com/rss/RSSMarketsMain.xml"
]

raw_news_items = []
print("正在抓取全球金融市場與具體數據相關最新新聞...")

for url in rss_urls:
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:10]:
            title = entry.get('title', '')
            published = entry.get('published', '')
            summary = entry.get('summary', '')
            raw_news_items.append(f"【發布時間: {published}】\n標題: {title}\n摘要: {summary}\n")
    except Exception as e:
        print(f"⚠️ 抓取 RSS 失敗 ({url}): {e}")

if not raw_news_items:
    print("❌ 未能成功抓取到金融新聞資料！")
    sys.exit(1)

news_context = "\n".join(raw_news_items)
print(f"✅ 成功抓取 {len(raw_news_items)} 則新聞資料！")

# 3. 構建「數據導向」的機構級金融分析 Prompt
prompt = f"""
你是一位機構級固定收益與總體經濟分析師。

以下是今天（{today_str}）全球財經媒體發布的最新即時新聞與數據資料：

=== 今日金融市場與經濟原始新聞資料 ===
{news_context}
=======================================

【任務要求 - 數據驅動型晨報】：
請根據上述原始新聞，編譯一份強調「定量數據與精確指標」的《每日金融市場要聞》。

1. **數據寫作重點（關鍵要求）**：
   - **總體經濟數據**：若新聞提及通膨、就業或經濟數據，請明確寫出確切數值（如 CPI 年增率 %、基點 bps、利率區間 %、預估值與前值對比）。
   - **債券與利率市場**：強調美債殖利率變化（如 10 年期/2 年期殖利率點數變化 bps、倒掛或陡峭化程度）、聯準會降息/升息機率。
   - **資產價格走勢**：包含具體漲跌幅 % 或點數（如美股指數、原油價格 $/桶、美元指數 DXY 走勢）。

2. **嚴格防幻覺規範**：
   - 具體數據必須嚴格基於提供的新聞內容。若新聞中無特定數字，請基於新聞事件進行精準的量化邏輯推論（如：因強勁就業數據引發美債殖利率上揚 X 個基點），切勿編造虛構數據。

3. **章節結構**：
   一、全球金融市場焦點與數據速覽
   二、總體經濟、央行政策與債券市場
   三、科技產業與企業財務表現
   四、外匯、大宗商品與信用市場

4. **格式規範**：
   - 使用繁體中文，語言風格需專業、客觀且具備機構研報品質。
   - 請將關鍵數據與百分比以 <strong>標籤加粗顯示</strong>。
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
        strong {{ color: #c0392b; }} /* 將數據加粗強調顯色 */
        a {{ color: #3498db; text-decoration: none; }}
        .back-link {{ display: inline-block; margin-bottom: 15px; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <a href="../index.html" class="back-link">← 返回首頁文章目錄</a>
        <h1>每日金融市場要聞</h1>
        <div style="color: #7f8c8d;">日期：{today_str}（機構級總經數據與市場編譯）</div>
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
    list_items += f'<li><a href="{post_path}">【{date_part}】每日金融市場要聞與總經數據解讀</a></li>\n'

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
        <p>自動追蹤全球總體經濟指標、央行利率政策、美債殖利率變動與金融市場數據。</p>
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
