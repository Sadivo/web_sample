# 航港大數據 — 資料庫架構規劃與來源總表

這份文件作為資料庫架構與資料來源的**單一事實來源（Single Source of Truth）**。
未來若有新組員加入或新資料表新增，請先於此 Markdown 檔案中擴充，後續再透過工具或 AI 轉成前端 HTML 視覺化網頁。

---

## 1. 總覽清單 (Overview)

| 資料表名稱 | 標籤 | 圖示 | 簡介說明 |
| --- | --- | --- | --- |
| `stations` | 原有 | 📡 | **測站/港口主檔**：統一存放所有氣象站、浮標、港口的基本資料（名稱、位置）。 |
| `chokepoints` | 原有 | 🌊 | **瓶頸點主檔**：全球 28 個重要海峽的基本資料。 |
| `marine_weather_obs` | 原有 | 🌬️ | **氣象海象觀測**：各測站每小時的風速、波高等觀測值。 |
| `weather_forecast_series` | ⭐ 新增 | 🔮 | **天氣預報序列**：未來 48 小時的逐小時預報存檔。 |
| `chokepoint_daily` | 原有 | ⚓ | **瓶頸點每日通過量**：海峽每天通過船數與擁塞指數。 |
| `uscg_port_status` | ⭐ 新增 | 🇺🇸 | **美西港口狀態**：洛杉磯、舊金山等港口是否開放的紀錄。 |
| `navigational_warnings`| 原有 | ⚠️ | **航行警報**：JCG、NGA 等機構發布的海事警報紀錄。 |
| `typhoons` | 原有 | 🌀 | **颱風事件**：颱風路徑與強度的歷史紀錄（含 GeoJSON）。 |
| `adiz_events` | ⭐ 新增 | ✈️ | **ADIZ 共機架次**：國防部每日公告的共機架次紀錄。 |
| `risk_scores` | ⭐ 新增 | 📈 | **綜合風險分數**：系統計算好的四分量加權風險分數。 |
| `vessels` | 🚢 shipping.db | 🛳️ | **船舶主檔**：25,617 艘船的基本資料。 |
| `ais_positions_summary`| 🚢 shipping.db | 📍 | **AIS 每日摘要**：每日各區域的摘要統計，不搬原始資料。 |
| `vessel_port_calls` | 🚢 shipping.db | ⚓ | **台灣港口進出港紀錄**：合併 tpnet_in/out 進出港記錄。 |
| `bunker_prices` | ⭐ 新增 | ⛽ | **港口燃油現貨價格**：高雄、洛杉磯、紐約、長灘等港口逐日燃油報價（OilMonster 爬蟲）。 |
| `freight_indices` | ⭐ 新增 | 📦 | **運價指數**：Freightos FBX 全球及台美航線逐日運價指數。 |
| `carbon_factors` | ⭐ 新增 | 🌿 | **燃料碳排係數靜態表**：MEPC.391(81) 規定的 32+ 種燃料 WtW/TtW Cf 值。 |
| `regulatory_zones` | ⭐ 新增 | 📋 | **排放管制區法規靜態表**：NAECA、MARPOL Annex VI 及台灣航港局低硫規範。 |

---

## 2. 資料表詳細設計 (Tables Detail)

### 2.1 `stations` (測站/港口主檔)
- **類型**: 靜態，不常變動
- **欄位定義**:
  | 欄位 | 型態 | 鍵 | 說明 |
  | --- | --- | --- | --- |
  | `station_id` | VARCHAR | PK | 測站代碼（如 466881、51101、KL） |
  | `name` | VARCHAR | | 測站/港口名稱 |
  | `type` | VARCHAR | | weather_station（氣象站）\| buoy（浮標）\| port（港口） |
  | `geom` | Geometry| | 座標（PostGIS 格式，支援空間查詢） |
  | `source` | VARCHAR | | 資料來源：CWA\|NDBC\|IOTH\|CWA_BUOY |
- **Metadata**:
  - **📥 資料來源**: CWA、NDBC、IOTH 各 API 的靜態站點資訊；人工整理匯入。
  - **🔢 運算欄位**: `type`（依來源標記）、`geom`（PostGIS 格式轉換）。
  - **⚠️ 重複欄位**: `station_id` 出現在 `marine_weather_obs` (FK)；港口代碼與 `vessel_port_calls.port_code` 重疊。

### 2.2 `chokepoints` (瓶頸點主檔)
- **類型**: 全球 28 個瓶頸點主檔
- **欄位定義**:
  | 欄位 | 型態 | 鍵 | 說明 |
  | --- | --- | --- | --- |
  | `chokepoint_id` | VARCHAR | PK | 如 chokepoint10（台灣海峽） |
  | `name_zh` | VARCHAR | | 中文名稱 |
  | `name_en` | VARCHAR | | 英文名稱 |
  | `geom` | Geometry| | 中心座標 |
  | `is_key_route` | BOOLEAN | | 是否為台美航線五大關鍵瓶頸點 |
- **Metadata**:
  - **📥 資料來源**: IMF PortWatch 靜態參照表；人工整理匯入。
  - **🔢 運算欄位**: `is_key_route`（依台美航線五大關鍵點標記）。
  - **⚠️ 重複欄位**: `chokepoint_id` 出現在 `chokepoint_daily` (FK)。

### 2.3 `marine_weather_obs` (氣象海象時序觀測)
- **類型**: 核心資料表
- **欄位定義**:
  | 欄位 | 型態 | 鍵 | 說明 |
  | --- | --- | --- | --- |
  | `id` | BIGSERIAL | PK | 自動編號主鍵 |
  | `station_id` | VARCHAR | FK | 關聯 stations 表 |
  | `obs_time` | TIMESTAMPTZ| | 觀測時間（含時區） |
  | `wind_speed` | FLOAT | | 風速 m/s |
  | `wind_direction`| FLOAT | | 風向 degrees |
  | `wind_gusts` | FLOAT | | 陣風 m/s |
  | `wave_height` | FLOAT | | 有效波高 Hs (m) |
  | `wave_period` | FLOAT | | 波浪週期 Tp (s) |
  | `wave_direction`| FLOAT | | 波向 degrees |
  | `air_temp` | FLOAT | | 氣溫 °C |
  | `sea_temp` | FLOAT | | 海溫 °C |
  | `source` | VARCHAR | | 資料來源 API（CWA、NDBC、IOTH…） |
- **Metadata**:
  - **📥 資料來源**: CWA、NDBC realtime2、IOTH Wave/Tide XML、Open-Meteo Marine 等。
  - **🔢 運算欄位**: （無）全部為原始觀測值。
  - **⚠️ 重複欄位**: `wind_speed`、`wave_height`、`air_temp` 也在 `weather_forecast_series`（預報/實測語意不同）。

### 2.4 `weather_forecast_series` (48h 逐小時天氣預報序列) ⭐
- **類型**: 時序資料
- **欄位定義**:
  | 欄位 | 型態 | 鍵 | 說明 |
  | --- | --- | --- | --- |
  | `id` | BIGSERIAL | PK | 自動編號主鍵 |
  | `fetched_at` | TIMESTAMPTZ| | 這筆預報是何時抓的 |
  | `lat` / `lon` | FLOAT | | 查詢座標（格點預報無測站 ID） |
  | `forecast_hour`| TIMESTAMPTZ| | 這筆資料預報的未來時間點 |
  | `wind_speed` | FLOAT | | 預報風速 m/s |
  | `wave_height` | FLOAT | | 預報波高 m |
  | `visibility_km`| FLOAT | | 能見度 km |
  | `precipitation`| FLOAT | | 降雨量 mm |
  | `temperature` | FLOAT | | 氣溫 °C |
- **Metadata**:
  - **📥 資料來源**: Open-Meteo Forecast API、Open-Meteo Marine。
  - **🔢 運算欄位**: （無）全部為 API 直接回傳的格點預報值。
  - **⚠️ 重複欄位**: 部分欄位與 `marine_weather_obs` 語意不同。

### 2.5 `chokepoint_daily` (每日通過量 + 擁塞指數)
- **欄位定義**:
  | 欄位 | 型態 | 鍵 | 說明 |
  | --- | --- | --- | --- |
  | `id` | BIGSERIAL | PK | 自動編號主鍵 |
  | `chokepoint_id` | VARCHAR | FK | 關聯 chokepoints 表 |
  | `obs_date` | DATE | | 觀測日期 |
  | `status` | VARCHAR | | open\|restricted\|unknown |
  | `n_total` | INT | | 當日總通過船數 |
  | `n_container` | INT | | 貨櫃輪數量 |
  | `n_tanker` | INT | | 油輪數量 |
  | `n_cargo` | INT | | 散貨輪數量 |
  | `congestion_index`| FLOAT | | 擁塞指數（今日÷7日均線）>1.2 = 壅塞 |
- **Metadata**:
  - **📥 資料來源**: IMF PortWatch ArcGIS REST API。
  - **🔢 運算欄位**: `congestion_index`、`status`（依 congestion_index 推導）。
  - **⚠️ 重複欄位**: `n_total` 可與 `ais_positions_summary.vessel_count` 交叉比對。

### 2.6 `uscg_port_status` (美西港口開放狀態) ⭐
- **欄位定義**:
  | 欄位 | 型態 | 鍵 | 說明 |
  | --- | --- | --- | --- |
  | `id` | BIGSERIAL | PK | 自動編號主鍵 |
  | `fetched_at` | TIMESTAMPTZ| | 抓取時間 |
  | `zone` | VARCHAR | | LA_LB\|SF\|SEATTLE\|SAN_DIEGO\|HONOLULU |
  | `port_name` | VARCHAR | | 港口名稱 |
  | `status` | VARCHAR | | open\|closed\|restricted |
  | `condition` | TEXT | | 詳細狀態說明文字 |
- **Metadata**:
  - **📥 資料來源**: USCG navcen.uscg.gov HTML 爬蟲。
  - **🔢 運算欄位**: （無）全部為爬蟲直接解析結果。

### 2.7 `navigational_warnings` (多來源航行警報)
- **欄位定義**:
  | 欄位 | 型態 | 鍵 | 說明 |
  | --- | --- | --- | --- |
  | `warning_id` | VARCHAR | PK | 來源機構警報編號 |
  | `source` | VARCHAR | | JCG\|NGA\|MARAD\|UKMTO |
  | `issue_date` | TIMESTAMPTZ| | 警報發布時間 |
  | `cancel_date` | TIMESTAMPTZ| | 警報取消時間 |
  | `area_name` | VARCHAR | | 影響區域名稱 |
  | `description` | TEXT | | 警報內容描述 |
  | `severity` | VARCHAR | | info\|warning\|urgent |
- **Metadata**:
  - **📥 資料來源**: JCG、NGA、MARAD、UKMTO 等官方網站。
  - **🔢 運算欄位**: `severity`（系統依警報關鍵字正規化後的分級）。

### 2.8 `typhoons` (颱風路徑與強度紀錄)
- **欄位定義**:
  | 欄位 | 型態 | 鍵 | 說明 |
  | --- | --- | --- | --- |
  | `id` | BIGSERIAL | PK | 自動編號主鍵 |
  | `system_id` | VARCHAR | | 颱風系統編號 |
  | `name` | VARCHAR | | 颱風名稱 |
  | `obs_time` | TIMESTAMPTZ| | 觀測時間 |
  | `geom` | Geometry| | 當下中心座標（PostGIS） |
  | `max_wind_kt` | FLOAT | | 最大風速（節） |
  | `storm_path` | JSON | | 預報路徑 GeoJSON LineString |
  | `source` | VARCHAR | | CWA\|JTWC |
- **Metadata**:
  - **📥 資料來源**: CWA 颱風警報 JSON API、JTWC。
  - **🔢 運算欄位**: `geom`、`storm_path`。

### 2.9 `adiz_events` (ADIZ 共機架次日誌) ⭐
- **欄位定義**:
  | 欄位 | 型態 | 鍵 | 說明 |
  | --- | --- | --- | --- |
  | `id` | BIGSERIAL | PK | 自動編號主鍵 |
  | `event_date` | DATE | UQ | 事件日期（每日一筆） |
  | `aircraft_count`| INT | | 共機總架次 |
  | `aircraft_crossed`| INT | | 穿越中線架次 |
  | `ship_count` | INT | | 共艦艘數 |
  | `raw_text` | TEXT | | 國防部新聞稿全文備份 |
- **Metadata**:
  - **📥 資料來源**: MND（國防部）官網新聞稿 scraping。
  - **🔢 運算欄位**: `aircraft_count`、`aircraft_crossed`、`ship_count`（由 NLP 提取）。

### 2.10 `risk_scores` (四分量加權風險分數) ⭐
- **欄位定義**:
  | 欄位 | 型態 | 鍵 | 說明 |
  | --- | --- | --- | --- |
  | `id` | BIGSERIAL | PK | 自動編號主鍵 |
  | `computed_at` | TIMESTAMPTZ| | 計算時間 |
  | `lat` / `lon` | FLOAT | | 查詢座標 |
  | `weather_risk` | FLOAT | | 天氣風險子分數 0~1 |
  | `geopolitics_risk`| FLOAT | | 地緣風險子分數 0~1 |
  | `congestion_risk`| FLOAT | | 壅塞風險子分數 0~1 |
  | `vessel_risk` | FLOAT | | 船舶風險子分數 0~1 |
  | `total_risk_score`| FLOAT | | 加權總分 0~1 |
  | `risk_level` | VARCHAR | | minimal\|low\|medium\|high\|critical |
  | `dominant_factor`| VARCHAR | | 主因 |
  | `adiz_sortie_count`| INT | | 計算當下的共機架次 |
- **Metadata**:
  - **📥 資料來源**: 系統計算產出（無直接原始 API）。

### 2.11 `vessels` (船舶主檔) 🚢
- **欄位定義**:
  | 欄位 | 型態 | 鍵 | 說明 |
  | --- | --- | --- | --- |
  | `mmsi` | INTEGER | PK | AIS 船舶識別碼 |
  | `imo` | INTEGER | | IMO 國際海事組織編號 |
  | `name` | TEXT | | 船名 |
  | `vessel_type_label`| TEXT | | 船型名稱 (Cargo\|Tanker...) |
  | `length_m` | INTEGER | | 船長 (m) |
  | `max_draft_m` | REAL | | 最大吃水 (m) |
  | `regions_seen` | TEXT | | 曾出現的區域列表 |
- **Metadata**:
  - **📥 資料來源**: shipping.db `vessels` 表，各欄位原始來源：
    - `imo`、`name`、`vessel_type`、`max_draft_m` ← Equasis / IMO GISIS
    - `mmsi` ← ITU MARS / VesselFinder（AIS）
    - `length_m`、`width_m`、`call_sign`、`destination` ← AIS transponder 廣播（非登記資料）
    - `vessel_type_label`、`regions_seen`、`first_seen`、`last_seen` ← 系統運算

### 2.12 `ais_positions_summary` (AIS 每日區域摘要) 🚢
- **欄位定義**:
  | 欄位 | 型態 | 鍵 | 說明 |
  | --- | --- | --- | --- |
  | `id` | BIGSERIAL | PK | 自動編號主鍵 |
  | `summary_date` | DATE | | 統計日期 |
  | `region` | VARCHAR | | 區域 (us_west\|asean...) |
  | `vessel_count` | INTEGER | | 當日總船隻數 |
  | `avg_sog` | FLOAT | | 平均船速 |
- **Metadata**:
  - **📥 資料來源**: shipping.db `positions` 表（641 萬筆）每日批次彙整。原始 AIS 訊號來源：aisstream.io（台灣周邊沿岸）+ Searoutes 衛星 AIS（太平洋中段補盲）。

### 2.13 `vessel_port_calls` (台灣港口進出港紀錄) 🚢
- **欄位定義**:
  | 欄位 | 型態 | 鍵 | 說明 |
  | --- | --- | --- | --- |
  | `id` | BIGSERIAL | PK | 自動編號主鍵 |
  | `visa_no` | VARCHAR | | 港務局簽證號 |
  | `direction` | VARCHAR | | in\|out |
  | `port_code` | VARCHAR | | 港口代碼 (KEL\|KHH...) |
  | `eta_dt` | TIMESTAMPTZ| | 預計到港時間 |
- **Metadata**:
  - **📥 資料來源**: shipping.db `tpnet_in`（37,604 筆）與 `tpnet_out`（42,395 筆），原始來源為台灣港務局 TPNET 港機系統。

### 2.14 `bunker_prices` (港口燃油現貨價格) ⭐
- **類型**: 時序資料，工作日每日更新
- **欄位定義**:
  | 欄位 | 型態 | 鍵 | 說明 |
  | --- | --- | --- | --- |
  | `id` | BIGSERIAL | PK | 自動編號主鍵 |
  | `fetched_at` | TIMESTAMPTZ | | 爬蟲抓取時間 |
  | `price_date` | DATE | | 報價所屬日期（OilMonster 頁面日期） |
  | `port_name` | VARCHAR | | 港口名稱（Kaohsiung / Los_Angeles / New_York / Long_Beach） |
  | `fuel_type` | VARCHAR | | 燃料類型（VLSFO \| MGO \| IFO380 \| HSFO \| LSMGO \| ULSFO \| IFO180） |
  | `price_usd_per_mt` | FLOAT | | 燃油現貨價格（美元 / 公噸） |
  | `source_url` | VARCHAR | | 資料來源 URL |
- **Metadata**:
  - **📥 資料來源**: OilMonster 爬蟲（高雄、洛杉磯、紐約、長灘）。實際抓取確認可取得：IFO 380、MGO、VLSFO、HSFO、LSMGO 0.1%、ULSFO 等。Ship & Bunker 台灣港口頁有登入牆，已以 OilMonster 替代。
  - **🔢 運算欄位**: （無）全部為爬蟲直接解析結果。
  - **⚠️ 重複欄位**: `port_name` 中的 Kaohsiung 可與 `vessel_port_calls.port_code = KHH` 對應；`fuel_type` 與 `carbon_factors.fuel_type` 形成 FK 關係（碳排計算時使用）。
  - **💡 備註**: Long Beach 最近可用日期較舊（2024-10）；Kaohsiung 最新（2026-05）。建議加欄位 `is_stale BOOLEAN` 標記資料新鮮度。

### 2.15 `freight_indices` (運價指數) ⭐
- **類型**: 時序資料，工作日每日更新
- **欄位定義**:
  | 欄位 | 型態 | 鍵 | 說明 |
  | --- | --- | --- | --- |
  | `id` | BIGSERIAL | PK | 自動編號主鍵 |
  | `fetched_at` | TIMESTAMPTZ | | 爬蟲抓取時間 |
  | `index_code` | VARCHAR | | 指數代碼（FBX / FBX01 / FBX02 / FBX03 / FBX04） |
  | `route_name` | TEXT | | 航線名稱（如 China/East Asia → North America West Coast） |
  | `value_usd_per_feu` | FLOAT | | 運價（美元 / FEU） |
  | `change_percent` | FLOAT | | 與前期相比變動百分比 |
  | `source` | VARCHAR | | 資料來源（Freightos_FBX \| SCFI） |
- **Metadata**:
  - **📥 資料來源**: Freightos FBX 爬蟲（已成功）；SCFI 公開頁有航線名稱、單位，但運價空白需登入，暫不列入。Freightos 方法論涵蓋高雄，可作台美航線公開代理指標。
  - **🔢 運算欄位**: （無）全部為爬蟲直接解析結果。
  - **⚠️ 重複欄位**: `route_name` 中 FBX01（西岸）/ FBX03（東岸）與專案台美航線研究直接對應；`value_usd_per_feu` 可與燃油成本合併計算運輸總費用。
  - **💡 備註**: FBX 僅有 East Asia 籃子（含台灣），非台灣單獨數字；若需更精確需付費訂閱 API。

### 2.16 `carbon_factors` (燃料碳排係數靜態參照表) ⭐
- **類型**: 靜態，IMO 修訂時才更新（約每 3~5 年）
- **欄位定義**:
  | 欄位 | 型態 | 鍵 | 說明 |
  | --- | --- | --- | --- |
  | `fuel_type` | VARCHAR | PK | 燃料類型（VLSFO / MGO / LNG / Methanol / HFO…） |
  | `cf_wtw` | FLOAT | | Well-to-Wake 碳排係數（gCO₂eq / gFuel） |
  | `cf_ttw` | FLOAT | | Tank-to-Wake 碳排係數（gCO₂eq / gFuel） |
  | `unit` | VARCHAR | | 單位說明（gCO2eq/gFuel） |
  | `imo_doc` | VARCHAR | | 來源文件（MEPC.391(81)） |
  | `updated_at` | DATE | | 係數最後更新日期 |
- **Metadata**:
  - **📥 資料來源**: MEPC.391(81) 免費 PDF（32 種燃料 WtW Cf 係數），人工整理一次性匯入。
  - **🔢 運算欄位**: （無）全部為 IMO 官方係數。
  - **⚠️ 重複欄位**: `fuel_type` 為 `bunker_prices.fuel_type` 的參照鍵；碳排估算公式：`CO₂ = 燃油消耗量(t) × Cf`。
  - **💡 備註**: 燃油消耗估算所需輸入（ship_type, draft, speed, wave/wind/current）來自 `vessels` 表與 `marine_weather_obs`，三表結合後可估算 F13（燃油消耗）與 F14/F25（碳排）。

### 2.17 `regulatory_zones` (排放管制區及合規法規靜態參照) ⭐
- **類型**: 半靜態（法規修訂時更新）
- **欄位定義**:
  | 欄位 | 型態 | 鍵 | 說明 |
  | --- | --- | --- | --- |
  | `zone_id` | VARCHAR | PK | 區域識別碼（NAECA / TW_PORT / GLOBAL） |
  | `zone_name` | VARCHAR | | 區域名稱（North American ECA / 台灣港口低硫區 / 全球公海） |
  | `zone_type` | VARCHAR | | ECA \| port_rule \| global |
  | `sulfur_limit_pct` | FLOAT | | 含硫量上限（%，ECA = 0.10 / 台灣港口 = 0.50 / 全球 = 0.50） |
  | `nox_tier` | VARCHAR | | NOx 標準等級（Tier I \| Tier II \| Tier III） |
  | `applies_to` | VARCHAR | | 適用情境（entering \| at_berth \| all） |
  | `carbon_tax_applicable`| BOOLEAN | | 是否課碳（歐盟 ETS 轄區 = TRUE；美國 / 台灣 = FALSE） |
  | `geom` | Geometry | | 管制區地理範圍（PostGIS；GLOBAL 可為 NULL） |
  | `source_doc` | VARCHAR | | 法規來源（MARPOL Annex VI \| NAECA \| 台灣航港局） |
  | `effective_date` | DATE | | 生效日期 |
- **Metadata**:
  - **📥 資料來源**: NAECA（美國西岸 200 海浬、東岸、墨西哥灣、夏威夷）；MARPOL Annex VI；台灣交通部航港局低硫規範（港內使用 ≤ 0.5% 燃料）；人工整理一次性匯入。
  - **🔢 運算欄位**: `carbon_tax_applicable`（依制度整理：美國無航運碳稅；EU ETS 僅適用歐洲港口）。
  - **⚠️ 重複欄位**: `zone_id` 可關聯 `vessel_port_calls.port_code`（靠港時觸發 port_rule 檢核）；ECA 地理範圍可與 `chokepoints.geom` 做空間交集。
  - **💡 備註**: 含碳燃料估算公式（非 ETS 課稅區使用者可選用）：`含碳價格 = fuel_price + (Cf × carbon_market_price)`；相關係數來自 `carbon_factors`。

---

## 3. 資料流 (Data Flow)

- **氣象資料流**:
  `Open-Meteo` / `CWA` -> `marine_weather_obs` -> API `GET /risk/weather`
- **海象資料流**:
  `IOTH` / `NDBC` / `USCG` -> API `GET /risk/ocean`
- **瓶頸點資料流**:
  `IMF PortWatch` -> `chokepoint_daily` -> API `GET /risk/chokepoint`
- **地緣風險資料流**:
  `MND 爬蟲` -> `adiz_events` -> API `GET /risk/geo`
- **風險分數計算流**:
  `weather` + `adiz` + `chokepoint` + `vessels` -> 計算 -> `risk_scores` -> API `GET /feature/risk_score`
- **燃油價格資料流**:
  `OilMonster 爬蟲` -> `bunker_prices` -> API `GET /feature/fuel_cost`
- **運價指數資料流**:
  `Freightos FBX 爬蟲` -> `freight_indices` -> API `GET /feature/freight_rate`
- **碳排估算資料流**:
  `carbon_factors`（MEPC 靜態）+ `vessels` + `marine_weather_obs` -> 計算 -> API `GET /feature/carbon_estimate`
- **燃料策略建議資料流**:
  `bunker_prices` + `carbon_factors` + `regulatory_zones` + `freight_indices` -> 計算 -> API `GET /feature/fuel_strategy`

---

## 4. 負責人與權責區分 (Owners)

### 👤 彭銪 (Peng)
- **職責**: 氣象 / 航行 / 地緣 / 風險分數
- **負責資料庫/表**: 
  - `stations`, `chokepoints`, `marine_weather_obs`, `weather_forecast_series`, `chokepoint_daily`, `uscg_port_status`, `navigational_warnings`, `typhoons`, `adiz_events`, `risk_scores`

### 👤 林子玲 (Lin)
- **職責**: shipping.db 負責人 · 船舶 / AIS / 港口進出港
- **負責資料庫/表**: 
  - `vessels`, `ais_positions_summary`, `vessel_port_calls`

### 👤 楊映亭 (Yang)
- **職責**: 燃油市場 / 運價指數 / 碳排合規 / 燃料策略
- **負責資料庫/表**: 
  - `bunker_prices`, `freight_indices`, `carbon_factors`, `regulatory_zones`
- **已完成爬蟲**:
  - ✅ OilMonster — 高雄、洛杉磯、紐約、長灘港口燃油現貨價（IFO 380 / MGO / VLSFO / HSFO / LSMGO / ULSFO）
  - ✅ Freightos FBX — 全球 + 台美四條航線逐日運價指數（FBX / FBX01–FBX04）
- **待辦**:
  - 🔲 將 MEPC.391(81) Cf 係數人工匯入 `carbon_factors`
  - 🔲 整理 NAECA / MARPOL / 台灣航港局資料至 `regulatory_zones`
  - 🔲 實作 API 端點 `GET /feature/fuel_cost`、`GET /feature/carbon_estimate`、`GET /feature/fuel_strategy`

---
> 💡 **維護建議**: 未來若有新增資料庫、資料表、爬蟲程式或新進組員，請依照上述結構直接新增章節，統一使用本檔案管理。
