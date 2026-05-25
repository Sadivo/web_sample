/* ==========================================================================
   子專案數據自動檢視器 - 全域前端邏輯檔案 (ES5/ES6 混合相容，支援 Marked.js 載入)
   ========================================================================== */

(function () {
    // 確保只初始化一次，且必須要有傳入的專案數據
    if (window.__DV_INITIALIZED__ || !window.__PROJECT_DATA__) return;
    window.__DV_INITIALIZED__ = true;

    const projectData = window.__PROJECT_DATA__;
    const files = projectData.files || [];
    const projectName = projectData.name || '子專案';

    // 常用副檔名格式與圖示對應
    const FILE_TYPES = {
        md: { icon: '📝', label: 'Markdown 文檔' },
        csv: { icon: '📊', label: 'CSV 數據表' },
        json: { icon: '⚙️', label: 'JSON 配置' },
        png: { icon: '🖼️', label: '圖片' },
        jpg: { icon: '🖼️', label: '圖片' },
        jpeg: { icon: '🖼️', label: '圖片' },
        gif: { icon: '🖼️', label: '圖片' },
        svg: { icon: '🖼️', label: '圖片' },
        pdf: { icon: '📄', label: 'PDF 文檔' },
        txt: { icon: '📄', label: '純文字檔' },
        log: { icon: '📄', label: '日誌檔' }
    };

    // 輔助函式：取得檔案副檔名
    function getFileExtension(filename) {
        return filename.split('.').pop().toLowerCase();
    }

    // 輔助函式：轉換 HTML 特殊字元避免 XSS
    function escapeHTML(str) {
        return str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    // 輔助函式：動態載入外部腳本 (Promise 化)
    function loadScript(src) {
        return new Promise((resolve, reject) => {
            if (document.querySelector(`script[src="${src}"]`)) {
                resolve();
                return;
            }
            const script = document.createElement('script');
            script.src = src;
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    // 初始化 UI 元件
    function init() {
        // 1. 建立並加入懸浮按鈕 (FAB)
        const fab = document.createElement('button');
        fab.className = 'dv-fab';
        fab.innerHTML = `
            <svg viewBox="0 0 24 24">
                <path d="M20,18H4V8H20M20,6H12L10,4H4C2.89,4 2,4.89 2,6V18A2,2 0 0,0 4,20H20A2,2 0 0,0 22,18V8C22,6.89 21.1,6 20,6Z" />
            </svg>
            <span>數據庫 (${files.length})</span>
        `;
        document.body.appendChild(fab);

        // 2. 建立並加入彈窗結構 (Modal Overlay & Modal Window)
        const overlay = document.createElement('div');
        overlay.className = 'dv-overlay';
        overlay.innerHTML = `
            <div class="dv-modal">
                <div class="dv-header">
                    <h2 class="dv-title">
                        <svg viewBox="0 0 24 24" style="width:24px; height:24px; fill:currentColor;">
                            <path d="M20,18H4V8H20M20,6H12L10,4H4C2.89,4 2,4.89 2,6V18A2,2 0 0,0 4,20H20A2,2 0 0,0 22,18V8C22,6.89 21.1,6 20,6Z" />
                        </svg>
                        ${projectName} - 專案專屬數據庫
                    </h2>
                    <button class="dv-close-btn">&times;</button>
                </div>
                <div class="dv-body">
                    <div class="dv-sidebar">
                        <div class="dv-section-title">數據檔案清單</div>
                        <ul class="dv-file-list"></ul>
                    </div>
                    <div class="dv-preview">
                        <div class="dv-placeholder-msg">請由左側選擇欲查看的數據檔案</div>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);

        const fileListContainer = overlay.querySelector('.dv-file-list');
        const previewPane = overlay.querySelector('.dv-preview');
        const closeBtn = overlay.querySelector('.dv-close-btn');

        // 3. 生成左側檔案清單
        if (files.length === 0) {
            fileListContainer.innerHTML = '<li style="color: var(--dv-text-muted); font-size: 0.85rem; padding: 10px;">(無可用數據)</li>';
        } else {
            files.forEach((file) => {
                const ext = getFileExtension(file);
                const fileMeta = FILE_TYPES[ext] || { icon: '📄', label: '未知格式' };
                const li = document.createElement('li');
                li.className = 'dv-file-item';
                li.dataset.path = file;
                li.innerHTML = `
                    <span class="dv-file-icon" title="${fileMeta.label}">${fileMeta.icon}</span>
                    <span class="dv-file-name">${file}</span>
                `;
                li.addEventListener('click', () => {
                    // 切換選取狀態
                    overlay.querySelectorAll('.dv-file-item').forEach(el => el.classList.remove('active'));
                    li.classList.add('active');
                    // 渲染內容
                    renderFile(file, previewPane);
                });
                fileListContainer.appendChild(li);
            });
        }

        // 4. 綁定按鈕控制事件
        fab.addEventListener('click', () => {
            overlay.classList.add('active');
            // 如果目前預覽區是空的，且有檔案可看，預設載入第一個檔案
            if (files.length > 0 && !previewPane.querySelector('.dv-content-wrapper') && !previewPane.querySelector('.dv-loading')) {
                const firstItem = fileListContainer.querySelector('.dv-file-item');
                if (firstItem) firstItem.click();
            }
        });

        // 關閉事件
        const closeModal = () => overlay.classList.remove('active');
        closeBtn.addEventListener('click', closeModal);
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) closeModal();
        });
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && overlay.classList.contains('active')) closeModal();
        });
    }

    // ==========================================================================
    // 智慧多格式渲染引擎 (Smart Rendering Engine)
    // ==========================================================================
    function renderFile(filePath, container) {
        // 顯示載入動畫
        container.innerHTML = `
            <div class="dv-loading">
                <div class="dv-spinner"></div>
                <div>正在載入檔案內容...</div>
            </div>
        `;

        const ext = getFileExtension(filePath);

        // 對於圖片與 PDF，我們可以直接渲染，免去 fetch text 的開銷
        if (['png', 'jpg', 'jpeg', 'gif', 'svg'].includes(ext)) {
            renderImage(filePath, container);
            return;
        }
        if (ext === 'pdf') {
            renderPDF(filePath, container);
            return;
        }

        // 讀取文本型數據檔案
        fetch(filePath)
            .then(res => {
                if (!res.ok) throw new Error(`無法載入檔案，狀態碼：${res.status}`);
                return res.text();
            })
            .then(text => {
                switch (ext) {
                    case 'md':
                        renderMarkdown(text, container);
                        break;
                    case 'csv':
                        renderCSV(text, container);
                        break;
                    case 'json':
                        renderJSON(text, container);
                        break;
                    default:
                        renderPlainText(text, container);
                        break;
                }
            })
            .catch(err => {
                container.innerHTML = `
                    <div style="color: #ef4444; padding: 2rem; border: 1px dashed rgba(239, 68, 68, 0.3); border-radius: 12px; background: rgba(239, 68, 68, 0.05); text-align: center;">
                        <span style="font-size: 2rem;">⚠️</span>
                        <h3 style="margin-top: 10px;">讀取檔案失敗</h3>
                        <p style="font-size: 0.9rem; color: var(--dv-text-muted); margin-bottom: 0;">${err.message}</p>
                    </div>
                `;
            });
    }

    // 1. 渲染 Markdown
    function renderMarkdown(text, container) {
        // 動態從 CDN 載入 Marked.js (若尚未載入)
        loadScript('https://cdn.jsdelivr.net/npm/marked/marked.min.js')
            .then(() => {
                // 配置 marked 選項
                marked.setOptions({
                    breaks: true,
                    gfm: true
                });
                const html = marked.parse(text);
                container.innerHTML = `
                    <div class="dv-content-wrapper">
                        ${html}
                    </div>
                `;
            })
            .catch(() => {
                // CDN 載入失敗時降級為純文字顯示
                renderPlainText("【Markdown 解析器載入失敗，降級顯示純文字】\n\n" + text, container);
            });
    }

    // 2. 渲染 CSV 表格
    function renderCSV(text, container) {
        // 極輕量 CSV 解析程式 (支援雙引號引號內的逗號跳脫)
        function parseCSVLine(line) {
            const result = [];
            let current = '';
            let inQuotes = false;
            for (let i = 0; i < line.length; i++) {
                const char = line[i];
                if (char === '"') {
                    inQuotes = !inQuotes;
                } else if (char === ',' && !inQuotes) {
                    result.push(current.trim());
                    current = '';
                } else {
                    current += char;
                }
            }
            result.push(current.trim());
            return result;
        }

        const lines = text.split(/\r?\n/).filter(line => line.trim() !== '');
        if (lines.length === 0) {
            container.innerHTML = '<div class="dv-placeholder-msg">CSV 檔案為空</div>';
            return;
        }

        // 解析標頭與資料列
        const headerCells = parseCSVLine(lines[0]);
        let tableHTML = `<div class="dv-content-wrapper"><div class="dv-table-container"><table class="dv-csv-table"><thead><tr>`;
        
        headerCells.forEach(cell => {
            tableHTML += `<th>${escapeHTML(cell)}</th>`;
        });
        tableHTML += `</tr></thead><tbody>`;

        for (let i = 1; i < lines.length; i++) {
            const cells = parseCSVLine(lines[i]);
            tableHTML += `<tr>`;
            // 補齊或裁切單元格，以標頭為準
            for (let j = 0; j < headerCells.length; j++) {
                tableHTML += `<td>${escapeHTML(cells[j] || '')}</td>`;
            }
            tableHTML += `</tr>`;
        }

        tableHTML += `</tbody></table></div></div>`;
        container.innerHTML = tableHTML;
    }

    // 3. 渲染 JSON
    function renderJSON(text, container) {
        let formattedJSON = text;
        try {
            const obj = JSON.parse(text);
            formattedJSON = JSON.stringify(obj, null, 2);
        } catch (e) {
            // 解析失敗則直接以原本的文字展示
        }
        
        container.innerHTML = `
            <div class="dv-content-wrapper">
                <pre class="dv-code-block"><code>${escapeHTML(formattedJSON)}</code></pre>
            </div>
        `;
    }

    // 4. 渲染圖片
    function renderImage(filePath, container) {
        container.innerHTML = `
            <div class="dv-content-wrapper dv-image-container">
                <img class="dv-image-preview" src="${filePath}" alt="${filePath}">
                <div class="dv-image-info">圖片路徑: ${filePath}</div>
            </div>
        `;
    }

    // 5. 渲染 PDF
    function renderPDF(filePath, container) {
        container.innerHTML = `
            <div class="dv-content-wrapper dv-pdf-container">
                <iframe class="dv-pdf-iframe" src="${filePath}"></iframe>
            </div>
        `;
    }

    // 6. 渲染純文字
    function renderPlainText(text, container) {
        container.innerHTML = `
            <div class="dv-content-wrapper">
                <pre class="dv-code-block"><code>${escapeHTML(text)}</code></pre>
            </div>
        `;
    }

    // 當頁面 DOM 載入完畢後開始初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
