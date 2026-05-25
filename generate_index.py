import os
from pathlib import Path
import json
import re

def inject_data_viewer(project_dir):
    """
    自動掃描子專案目錄下的數據檔案，並將其注入至 index.html 的 body 結尾前。
    支援的副檔名包含：.md, .csv, .json, .txt, .log, .pdf, .png, .jpg, .jpeg, .gif, .svg
    每次執行時會自動清理舊的注入區塊並重新注入最新的數據。
    """
    index_file = project_dir / "index.html"
    if not index_file.exists():
        return
        
    valid_exts = {".md", ".csv", ".json", ".txt", ".log", ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".svg"}
    data_files = []
    
    # 遞迴遍歷專案目錄下的所有檔案
    for file_path in project_dir.rglob("*"):
        if file_path.is_file():
            # 排除特定網頁引導檔案與隱藏檔案
            if file_path.name.lower() in {"index.html", "note.txt"} or file_path.name.startswith("."):
                continue
            
            # 排除特殊排除目錄中的檔案
            parts = file_path.relative_to(project_dir).parts
            if any(p.startswith(".") or p in {".git", "__pycache__", "node_modules", "old"} for p in parts):
                continue
                
            if file_path.suffix.lower() in valid_exts:
                # 轉成相對於子專案目錄的相對路徑，並將 Windows 分隔符 \ 轉成 /
                rel_path = file_path.relative_to(project_dir).as_posix()
                data_files.append(rel_path)
                
    # 檔案名稱排序
    data_files.sort()
    
    # 讀取 index.html
    try:
        with open(index_file, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"❌ 無法讀取子專案網頁 {index_file}: {e}")
        return

    # 清除先前可能已注入的舊區塊
    pattern = r"<!-- DATA_VIEWER_INJECTED_START -->.*?<!-- DATA_VIEWER_INJECTED_END -->"
    content = re.sub(pattern, "", content, flags=re.DOTALL)
    
    # 組裝數據中繼資料 JSON
    project_meta = {
        "name": project_dir.name,
        "files": data_files
    }
    project_meta_json = json.dumps(project_meta, ensure_ascii=False, indent=2)
    # 將 JSON 內容縮排，保持 HTML 代碼美觀
    indented_meta = "\n".join("      " + line for line in project_meta_json.split("\n"))
    
    # 構造注入代碼塊
    injection_code = f"""<!-- DATA_VIEWER_INJECTED_START -->
    <link rel="stylesheet" href="../global_data_viewer.css">
    <script>
      window.__PROJECT_DATA__ = {indented_meta.strip()};
    </script>
    <script src="../global_data_viewer.js"></script>
<!-- DATA_VIEWER_INJECTED_END -->"""

    # 尋找 </body> 標籤進行注入，若不存在則附加至最末尾
    if "</body>" in content:
        content = content.replace("</body>", f"{injection_code}\n</body>")
    else:
        content = content + f"\n{injection_code}"
        
    # 寫回子專案網頁
    try:
        with open(index_file, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  ⚡ 成功為子專案 [{project_dir.name}] 注入數據查看器 (共偵測到 {len(data_files)} 個數據檔案)")
    except Exception as e:
        print(f"❌ 無法寫入子專案網頁 {index_file}: {e}")

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
                # 呼叫數據查看器注入邏輯
                inject_data_viewer(item)
                
                note_file = item / "note.txt"
                note_text = ""
                if note_file.exists():
                    try:
                        with open(note_file, "r", encoding="utf-8") as nf:
                            note_text = nf.read().strip()
                    except Exception as e:
                        print(f"無法讀取 {note_file}: {e}")
                projects.append({"name": item.name, "note": note_text})
                
    # 依字母順序排序專案
    projects.sort(key=lambda x: x["name"])
    
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
        .card-content {{
            flex-grow: 1;
            padding-right: 15px;
        }}
        .card h2 {{
            margin: 0;
            font-size: 1.25rem;
            font-weight: 500;
            word-break: break-all;
        }}
        .card p.desc {{
            margin: 0.5rem 0 0 0;
            font-size: 0.9rem;
            color: var(--text-muted);
            line-height: 1.4;
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
            p_name = proj["name"]
            p_note = proj["note"]
            desc_html = f'\n                    <p class="desc">{p_note}</p>' if p_note else ''
            html_content += f"""
            <a href="{p_name}/index.html" class="card">
                <div class="card-content">
                    <h2>{p_name}</h2>{desc_html}
                </div>
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
