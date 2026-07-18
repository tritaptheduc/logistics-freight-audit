# Automated Freight Invoice Audit & Anomaly Detection Engine

## 📌 Project Overview
This project builds an end-to-end automated **Freight Audit & Payment (FAP)** analytics system. In logistics operations, manually auditing carrier invoices against shipping contracts and actual operational execution is time-consuming and highly prone to human error. 

This solution automates the **3-Way Matching process** (Contract Rate vs. Bill of Lading vs. Carrier Invoice) to automatically detect invoice anomalies, calculate recoverable financial leakages, and visualize carrier performance.

### 🏗️ Tech Stack
- **Data Generation:** Python (`pandas`)
- **Data Warehouse & Transformation:** Google BigQuery (SQL CTEs & Window Functions)
- **BI Visualization:** Power BI Desktop

---

## ⚙️ Business Logic & Audit Rules
The core SQL engine runs automatically on BigQuery to evaluate each invoice against **4 critical logistics audit rules**:

1. **RULE_1: Duplicate Billing (`DUPLICATE_INVOICE`)**
   - *Logic:* Identifies if a specific Bill of Lading (BOL) or shipment is invoiced more than once by the carrier.
2. **RULE_2: Base Rate Overcharge (`BASE_RATE_OVERCHARGE`)**
   - *Logic:* Compares the invoiced base rate against the legally agreed contract master rate for specific origin-destination pairs.
3. **RULE_3: Fuel Surcharge Overcharge (`FUEL_SURCHARGE_OVERCHARGE`)**
   - *Logic:* Validates if the billed fuel percentage exceeds the benchmark rate defined in the contract.
4. **RULE_4: Invalid Demurrage (`INVALID_DEMURRAGE_CHARGE` / `DEMURRAGE_OVERCHARGE`)**
   - *Logic:* Flags instances where carriers charge detention/demurrage fees despite actual ground operations remaining within the contractually agreed free-time window.

---

## 📂 Data Architecture & Pipeline
1. **`src/01_data_generator.py`**: A Python script simulating ~1,000 real-world shipping transactions and intentionally injecting a 5-8% error rate across different carriers.
2. **`src/02_audit_logic.sql`**: Extracted data fields are joined and evaluated through an automated SQL View layout. If errors occur, the view flags the row status and isolates the exact `Recoverable_Overcharge_USD` value.
3. **`reports/freight_audit_dashboard.pbix`**: An interactive monitoring report designed to track total audit success rates, billing variances, and high-risk carrier rankings.

---

## 📈 Dashboard Key Insights & Preview
*(Note: Please insert your final updated dashboard screenshot here below)*

![Freight Audit Dashboard Preview](asset/dashboard_screenshot.jpg)

### Executive Metrics Built:
- **Total Invoices Audited:** Total volume of transactions processed through the automated engine.
- **Total Billed Amount:** Gross financial liability claimed by global vendors.
- **Recoverable Overcharge Amount:** Direct bottom-line cost savings flagged by the system to be rejected or disputed.
- **Error Invoice Rate (%):** Operational accuracy scorecard tracking historical vendor performance.

---

## 🚀 How to Run this Project Locally

### Prerequisites
- Python 3.x installed.
- Access to a Google Cloud Platform (GCP) Sandbox account with BigQuery enabled.
- Power BI Desktop installed (Windows only).

### Step 1: Generate Raw Datasets
Run the generator script to compile the synthetic databases into flat files:
```bash
pip install pandas
python src/01_data_generator.py
```

### Step 2: BigQuery Cloud Implementation
Create a dataset named `freight_audit_db` inside your BigQuery environment.

Upload the 3 newly generated flat-files into individual tables: `dim_contract_rates`, `fact_shipments_bol`, and `raw_carrier_invoices`.

Open a new query editor tab, paste the production script located at `src/02_audit_logic.sql`, and execute it to deploy the active analytic view.

### Step 3: Power BI Consumption
Open Power BI Desktop and choose Get Data -> Google BigQuery.

Connect directly to the production database and load data from `vw_freight_invoice_audit`.

Open the global report to see automated metrics updated live.

---
📄 License
This repository is distributed under the open-source MIT License. Feel free to leverage the data schema models or algorithms for commercial or learning initiatives.
