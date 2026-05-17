# 基於 API 確認表的純粹資料庫架構設計 (API-Driven Database Schema)

這份架構圖**完全遵循您的 `API確認表.xlsx`** 內的欄位與模組分類，將 API 定義的 SubCategories 轉化為關聯式資料庫 (RDBMS) 的實體資料表。

我們將原本散落的 API 回傳欄位，精煉為四大核心領域（Domain）：
1. **核心主檔層 (Core Entities)**：船舶、港口、航線、航次。
2. **商業營運層 (Commercial)**：合約、聯盟、市場票價與法規。
3. **動態觀測層 (Dynamic Context)**：AIS 軌跡、氣象海象、地緣風險。
4. **引擎預測層 (Engine Outputs)**：由模擬引擎產生的延遲、成本、風險與評估結果。

---

## API 領域驅動 ER Diagram (Mermaid)

```mermaid
erDiagram
    %% ==========================================
    %% 1. 核心主檔層 (Core Entities)
    %% 涵蓋：vessel, Physical, VesselRisk, Port, Route, Voyage
    %% ==========================================
    vessels {
        TEXT vessel_id PK
        TEXT imo "IMO (L1)"
        INTEGER mmsi "MMSI (L1)"
        TEXT name
        TEXT vessel_type
        INTEGER teu_capacity
        FLOAT deadweight_ton
        FLOAT max_draft
        FLOAT engine_power_kw
        TEXT fuel_type
        FLOAT fuel_efficiency
        TEXT flag
        TEXT class_society
        INTEGER build_year
        %% from Physical
        FLOAT max_speed
        FLOAT min_speed
        FLOAT draft_limit
        FLOAT fuel_capacity
        %% from VesselRisk
        TEXT ghs_rating
        INTEGER psc_detentions
        FLOAT inspection_score
        BOOLEAN anomaly_flag
        TEXT anomaly_type
    }

    ports {
        TEXT port_id PK
        TEXT name
        TEXT country
        FLOAT max_draft
        INTEGER berth_count
        FLOAT port_capacity
    }

    routes {
        TEXT route_id PK
        TEXT origin_port FK
        TEXT destination_port FK
        FLOAT distance_nm
        FLOAT base_duration_hr
        JSONB chokepoints
        FLOAT depth_limit
    }

    voyages {
        TEXT voyage_id PK
        TEXT vessel_id FK
        TEXT route_id FK
        JSONB port_sequence
        INTEGER total_legs
        INTEGER current_leg
    }

    vessels ||--o{ voyages : "執行"
    routes ||--o{ voyages : "依循"
    ports ||--o{ routes : "起迄"

    %% ==========================================
    %% 2. 商業營運層 (Commercial & Operations)
    %% 涵蓋：Contract, Alliance, Market, Regulatory
    %% ==========================================
    contracts {
        TEXT contract_id PK
        TEXT vessel_id FK
        INTEGER commitment_teu
        INTEGER contract_remaining_teu
        DATE deadline
        INTEGER contract_time_window
        FLOAT penalty_per_teu
        INTEGER contract_priority
        FLOAT min_service_level
        %% from Alliance
        INTEGER slot_quota
        BOOLEAN schedule_fixed
        TEXT slot_exchange_rule
    }

    market_data {
        BIGSERIAL id PK
        DATE record_date
        FLOAT fuel_price
        TEXT fuel_type
        FLOAT freight_index
        FLOAT charter_rate
        FLOAT carbon_price
        FLOAT port_fuel_price
    }

    regulations {
        TEXT zone_id PK
        BOOLEAN eca_zone
        FLOAT emission_limit
        TEXT fuel_restriction
        BOOLEAN carbon_tax_applicable
    }

    vessels ||--o{ contracts : "綁定合約"

    %% ==========================================
    %% 3. 動態觀測層 (Dynamic Context)
    %% 涵蓋：Tracking, Environment, Risk
    %% ==========================================
    vessel_tracking {
        BIGSERIAL id PK
        TEXT vessel_id FK
        TEXT voyage_id FK
        TIMESTAMPTZ timestamp
        FLOAT lat
        FLOAT lon
        FLOAT speed_knots
        FLOAT heading
        TEXT nav_status
        TEXT leg_status
        TEXT next_port
        TIMESTAMPTZ eta_port
    }

    environment_obs {
        BIGSERIAL id PK
        TIMESTAMPTZ forecast_time
        FLOAT wind_speed
        FLOAT wave_height
        FLOAT current_speed
        FLOAT visibility
        BOOLEAN storm_flag
        FLOAT tide_level
    }

    risk_events {
        BIGSERIAL id PK
        FLOAT geopolitics_risk
        FLOAT piracy_risk
        FLOAT bottleneck_density
        BOOLEAN sanctions_flag
        TEXT insurance_zone
        JSONB risk_zone_polygon
    }

    voyages ||--o{ vessel_tracking : "航次軌跡"

    %% ==========================================
    %% 4. 引擎預測層 (Engine Outputs / Simulations)
    %% 涵蓋：Route Evaluation, Delay Engine, Cost Engine, Risk Engine, Port Engine
    %% ==========================================
    engine_route_evaluations {
        BIGSERIAL id PK
        TEXT voyage_id FK
        TEXT route_id FK
        
        %% from Delay Engine
        FLOAT delay_probability
        FLOAT eta_variance
        FLOAT eta_p50
        FLOAT eta_p90
        
        %% from Cost Engine
        FLOAT fuel_cost
        FLOAT delay_cost
        FLOAT penalty_cost
        FLOAT carbon_cost
        FLOAT total_cost
        
        %% from Risk Engine
        FLOAT total_risk_score
        FLOAT weather_risk
        FLOAT geopolitics_risk
        FLOAT congestion_risk
        
        %% from Route Evaluation
        FLOAT segment_eta
        FLOAT fuel_consumption
        FLOAT carbon_emission
        FLOAT unmet_commitment_penalty
        FLOAT profit
    }

    engine_port_predictions {
        BIGSERIAL id PK
        TEXT port_id FK
        FLOAT expected_wait_time
        FLOAT expected_wait_time_at_eta
        FLOAT congestion_score
        FLOAT capacity_utilization_port
        FLOAT overflow_risk
        FLOAT port_delay_cost
    }

    voyages ||--o| engine_route_evaluations : "產生模擬結果"
    ports ||--o{ engine_port_predictions : "港口預測狀態"
```

## 設計思維解析 (Architecture Rationale)

1. **實體整併**：在 API 中，`vessel`、`Physical` (物理限制) 與 `VesselRisk` (安檢紀錄) 被拆分為不同的 API 分類，但在資料庫底層，這些都是同一艘船的屬性，因此我們將其完美整併至單一的 `vessels` 實體表。
2. **商業邏輯支援**：API 中定義了 `Contract` 與 `Alliance`，這意味著這個系統不僅僅是「避險」，還牽涉到「運力調度」與「違約罰金 (`penalty_cost`)」。因此獨立出 `contracts` 表格，讓航次模擬時可以精算利潤 (`profit`)。
3. **強大的模擬引擎層 (Engine Outputs)**：API 確認表中擁有高達 6 種不同的 Engine (Cost, Delay, Risk, Port, Route, Voyage)，這些輸出非常適合存入 `engine_route_evaluations` 與 `engine_port_predictions` 表中，作為前端 Dashboard 展示歷史預測與未來趨勢的資料源。
