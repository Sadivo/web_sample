import os
from pathlib import Path

def generate_index():
    # 獲取當前目錄
    base_dir = Path(".")
    projects = []
    
    # 預設要忽略的隱藏目錄與特定資料夾
    ignore_dirs = {".git", ".venv", ".vscode", ".idea", "__pycache__", "node_modules"}
    
    # 掃描資料夾
    for item in base_dir.iterdir():
        # 條件：必須是資料夾、不在忽略清單中、且不以 "." 開頭
        if item.is_dir() and item.name not in ignore_dirs and not item.name.startswith("."):
            # 條件：資料夾內必須要有 index.html 才視為有效專案入口
            index_file = item / "index.html"
            if index_file.exists():
                projects.append(item.name)
                
    # 依字母順序排序專案
    projects.sort()
    
    # ==========================================
    # HTML 與 CSS 樣式模板 (深色玻璃擬物化風格)
    # ==========================================
    html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>專案目錄入口</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #0f172a;
            --card-bg: rgba(255, 255, 255, 0.05);
            --card-border: rgba(255, 255, 255, 0.1);
            --card-hover: rgba(255, 255, 255, 0.12);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent: #38bdf8;
        }}
        body {{
            margin: 0;
            padding: 0;
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: var(--text-main);
            min-height: 100vh;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 4rem 2rem;
        }}
        header {{
            text-align: center;
            margin-bottom: 4rem;
        }}
        h1 {{
            font-size: 3rem;
            margin-bottom: 0.5rem;
            background: linear-gradient(to right, #38bdf8, #818cf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 700;
        }}
        p.subtitle {{
            color: var(--text-muted);
            font-size: 1.1rem;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 2rem;
        }}
        .card {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 2rem;
            text-decoration: none;
            color: var(--text-main);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .card:hover {{
            transform: translateY(-8px);
            background: var(--card-hover);
            border-color: rgba(255, 255, 255, 0.25);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
        }}
        .card h2 {{
            margin: 0;
            font-size: 1.25rem;
            font-weight: 500;
            word-break: break-all;
            padding-right: 15px;
        }}
        .icon {{
            background: rgba(255,255,255,0.08);
            min-width: 44px;
            height: 44px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
            color: var(--accent);
            transition: all 0.3s ease;
            font-size: 1.2rem;
        }}
        .card:hover .icon {{
            transform: translateX(5px);
            background: rgba(56, 189, 248, 0.2);
            color: #fff;
        }}
        .empty-state {{
            text-align: center;
            grid-column: 1 / -1;
            padding: 3rem;
            color: var(--text-muted);
            background: var(--card-bg);
            border-radius: 16px;
            border: 1px dashed var(--card-border);
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>專案目錄入口</h1>
            <p class="subtitle">目前共偵測到 {len(projects)} 個專案</p>
        </header>
        <div class="grid">"""
    
    # 動態插入專案卡片
    if not projects:
        html_content += """
            <div class="empty-state">
                <h2>尚無可用專案</h2>
                <p>請確認子資料夾內包含 index.html 檔案</p>
            </div>"""
    else:
        for proj in projects:
            html_content += f"""
            <a href="{proj}/index.html" class="card">
                <h2>{proj}</h2>
                <div class="icon">➔</div>
            </a>"""
            
    # 收尾
    html_content += """
        </div>
    </div>
</body>
</html>"""
    
    # 將組裝好的 HTML 寫入 index.html
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"✅ 成功生成 index.html！共收錄 {len(projects)} 個專案資料夾。")

if __name__ == "__main__":
    generate_index()
