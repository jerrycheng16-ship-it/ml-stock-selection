import os
import sys
import time
import glob
import datetime
from google import genai
from google.genai import types

# 1. 檢查並讀取 API Key
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("❌ 錯誤：找不到 GEMINI_API_KEY！請檢查 GitHub Settings > Secrets 設定。")
    sys.exit(1)

api_key = api_key.strip()
client = genai.Client(api_key=api_key)

# 取得今天日期
today_dt = datetime.datetime.now()
today_str = today_dt.strftime("%Y-%m-%d")
date_display = today_dt.strftime("%Y 年 %m 月 %d 日")

# 建立歷史文章資料夾 posts
os.makedirs("posts", exist_ok=True)
post_filename = f"posts/{today_str}.html"

# 2. 構建帶有強烈時間限制與 Google Search Grounding 的 Prompt
prompt = f"""
你是一位機構級的專業金融分析師與總體經濟研究員。

今天的精準日期是：{date_display}。

【重要任務與聯網指令】：
請使用 Google 搜尋工具，搜尋最近 24 小時內（即 {date_display} 當天與前一日）全球金融市場、聯準會（Fed）政策動態、美債殖利率、美股三大指數與大宗商品的最新報導與即時數據。

【嚴格寫作規範 - 防歷史幻覺】：
1. 所有新聞與數據必須限定為【最近 24 小時內】發生的最新事件。
2. 嚴禁引述任何過去年份的歷史舊新聞（例如：嚴禁提及 2025 年初的 DeepSeek 事件或 2023 年的美債高點事件）。
3. 若當日市場處於週末休市，請總結剛收盤的最新周線表現與最新發布的經濟數據。
4. 著重於定量數據：包含指數漲跌幅 %、美債殖利率點數（bps）、通膨指標（CPI/PCE）與利率期貨預估值。

【報告架構與格式】：
請將內容分為以下四個章節：
一、全球金融市場焦點與數據速覽
二、總體經濟、央行政策與債券市場
三、科技產業與企業財務動態
四、外匯、大宗商品與信用市場

要求：
- 使用繁體中文。
- 請將關鍵數字與數據用 <strong> 標籤加粗顯示。
- 格式請直接輸出為排版美觀的 HTML 內文（包含 <h2>, <h3>, <ul>, <li>, <strong> 等標籤）。
"""

# 3. 呼叫 Gemini API（開啟 Google Search Grounding，且關閉 AFC 以避免死鎖）
models_to_try = ['gemini-3.8-flash']
content_html = None

for model_name in models_to_try:
    print(f"🔄 開始嘗試模型: {model_name} (開啟實時 Google Search 搜尋)...")
    for attempt in range(1, 5):
        try:
            print(f"正在發送 API 請求 (模型: {model_name}, 第 {attempt} 次嘗試)...")
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[{"google_search": {}}],  # 啟用 Google 官方實時搜尋功能
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

# 4. 寫入當天的獨立文章頁面
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
        strong {{ color: #c0392b; }} /* 數據加粗紅字強調 */
        a {{ color: #3498db; text-decoration: none; }}
        .back-link {{ display: inline-block; margin-bottom: 15px; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <a href="../index.html" class="back-link">← 返回首頁文章目錄</a>
        <h1>每日金融市場要聞</h1>
        <div style="color: #7f8c8d;">日期：{today_str}（即時 Google 搜尋數據與市場解讀）</div>
        <hr>
        {content_html}
    </div>
</body>
</html>
"""

with open(post_filename, "w", encoding="utf-8") as f:
    f.write(post_html_template)

# 5. 掃描 posts 資料夾，更新首頁 index.html
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
