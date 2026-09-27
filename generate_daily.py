import os
import sys
import glob
import datetime
from google import genai

# 1. 檢查並讀取 API Key
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("❌ 錯誤：找不到 GEMINI_API_KEY！請檢查 GitHub Settings > Secrets 是否設定正確。")
    sys.exit(1)

# 清除金鑰前後可能誤複製到的空格或換行
api_key = api_key.strip()
client = genai.Client(api_key=api_key)

today_str = datetime.datetime.now().strftime("%Y-%m-%d")

# 建立歷史文章資料夾 posts
os.makedirs("posts", exist_ok=True)
post_filename = f"posts/{today_str}.html"

# 2. 設定 Prompt
prompt = f"""
你是一位專業的金融分析師。請為我整理今天（{today_str}）《華爾街日報》(WSJ) 的重點摘要。

重點要求：
1. 聚焦於：全球宏觀經濟、Fed貨幣政策、中東與地緣政治、美中貿易與AI科技產業發展。
2. 結構包含：頭條焦點、總體經濟與央行、產業與科技、市場與商品。
3. 嚴格限制：請勿包含任何紫微斗數、算命、占星或非理性分析內容。
4. 使用繁體中文，格式請直接輸出為排版美觀的 HTML 內文（包含 <h2>, <h3>, <ul>, <li>, <strong> 等標籤）。
"""

# 3. 呼叫 Gemini API（加上 Try-Except 捕捉精確錯誤）
try:
    print("正在發送 API 請求...")
    response = client.models.generate_content(
        model='gemini-2.0-flash',  # 使用當前標準穩定模型
        contents=prompt,
    )
    content_html = response.text
    print("✅ 成功取得 API 回應！")
except Exception as e:
    print(f"❌ API 請求失敗！具體錯誤原因：{e}")
    sys.exit(1)

# 4. 寫入當天的獨立文章頁面
post_html_template = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>華爾街日報重點摘要 - {today_str}</title>
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
        <h1>華爾街日報 每日重點摘要</h1>
        <div style="color: #7f8c8d;">日期：{today_str}</div>
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
    list_items += f'<li><a href="{post_path}">【{date_part}】華爾街日報重點摘要與市場解讀</a></li>\n'

index_html_template = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>華爾街日報 每日摘要歷史存檔</title>
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
        <h1>華爾街日報 每日摘要日誌</h1>
        <p>自動追蹤全球宏觀經濟、央行政策與地緣政治趨勢。</p>
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
