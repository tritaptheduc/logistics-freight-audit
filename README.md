# 🚀 Automated Freight Invoice Audit & Anomaly Detection Engine

## 📌 Project Overview
In global logistics, freight invoice discrepancies represent a significant source of capital leakage, often accounting for **3% to 8% of total shipping expenditures** due to duplicate billings, data entry errors, or carrier overcharges.

This project delivers an **end-to-end, automated 3-Way Matching Data Engine** that programmatically cross-references **Carrier Invoices** against **Bill of Lading (BOL)** operational records and **Contract Tariff Agreements**. By transitioning from manual spot-checks to 100% automated algorithmic auditing, this engine instantly flags billing anomalies, quantifies financial leakage, and generates actionable data for carrier dispute resolution.

---

## 🏗️ System Architecture & Data Flow
The system processes data through a modern cloud data stack pipeline designed for high scalability and low maintenance:
1. **Ingestion & Data Generation**: A robust Python script simulates production-grade enterprise data (1,000+ logistics transactions) with complex, injected invoice anomalies based on real-world industry patterns.
2. **Storage & Processing**: Raw datasets are hosted on **Google BigQuery**, serving as the centralized source of truth.
3. **Transformation & Business Logic**: A high-performance BigQuery SQL View processes the algorithmic 3-way matching engine using common table expressions (CTEs) and analytical window functions.
4. **Visualization**: An analytical dashboard in **Power BI** translates audited rows into critical financial metrics, prioritizing the discovery of recoverable funds.

---

## 🛠️ Data Schema & Injected Anomalies
The underlying data model consists of three transactional and master tables linked via operational identifiers:

* **`dim_contract_rates` (Master Tariff)**: Contains contract-vetted logistics parameters including `Agreed_Base_Rate_USD`, `Agreed_Fuel_Surcharge_Pct`, and negotiated `Free_Demurrage_Days`.
* **`fact_shipments_bol` (ERP/TMS Reality)**: The ground-truth operational record documenting actual shipping timelines and `Actual_Demurrage_Days` incurred at port terminals.
* **`raw_carrier_invoices` (Financial Claims)**: Transactional bills received from ocean and road carriers (`Billed_Base_Rate_USD`, `Billed_Fuel_Surcharge_USD`, `Billed_Demurrage_USD`).

### Injected Core Audit Anomalies (Anomaly Injection Engine)
To prove the capability of the engine, the following auditing validations were programmatically injected into the source data:
* 🚩 **Duplicate Billing (RULE 1)**: Identical freight shipments billed multiple times under varying invoice numbers.
* 🚩 **Base Rate Overcharge (RULE 2)**: Discrepancies where the invoiced base fare exceeds the contractually binding rate.
* 🚩 **Fuel Surcharge Manipulation (RULE 3)**: Invoiced fuel percentages artificially inflated above agreed index pegs.
* 🚩 **Unjustified Demurrage (RULE 4)**: Premium port storage penalties levied despite cargo clearing within negotiated free-time limits.

---

## ⚙️ Core Transformation Code (BigQuery SQL Audit View)
The entire algorithmic verification runs on the warehouse level via a dedicated analytical script. This script processes multi-table joins, flags discrepancies dynamically, and calculates the **Recoverable Overcharge Amount**:

```sql
CREATE OR REPLACE VIEW `freight_audit_db.vw_freight_invoice_audit` AS
WITH DeduplicatedInvoices AS (
    SELECT 
        Invoice_Number, BOL_Number, Carrier,
        PARSE_DATE('%Y-%m-%d', Invoice_Date) AS Invoice_Date,
        Billed_Base_Rate_USD, Billed_Fuel_Surcharge_USD, Billed_Demurrage_USD, Billed_Total_Amount_USD,
        ROW_NUMBER() OVER(PARTITION BY BOL_Number ORDER BY Invoice_Date ASC, Invoice_Number ASC) AS invoice_occurence
    FROM `freight_audit_db.raw_carrier_invoices`
),
JoinedAuditData AS (
    SELECT 
        inv.Invoice_Number, inv.BOL_Number, inv.Carrier, inv.Invoice_Date, inv.invoice_occurence,
        PARSE_DATE('%Y-%m-%d', ship.Shipment_Date) AS Shipment_Date, ship.POL_Origin, ship.POD_Destination, ship.Container_Type, ship.Actual_Demurrage_Days,
        ctr.Contract_ID, ctr.Agreed_Base_Rate_USD, ctr.Agreed_Fuel_Surcharge_Pct, ctr.Free_Demurrage_Days,
        inv.Billed_Base_Rate_USD, inv.Billed_Fuel_Surcharge_USD, inv.Billed_Demurrage_USD, inv.Billed_Total_Amount_USD,
        ctr.Agreed_Base_Rate_USD AS Expected_Base_Rate_USD,
        ROUND(ctr.Agreed_Base_Rate_USD * ctr.Agreed_Fuel_Surcharge_Pct, 2) AS Expected_Fuel_Surcharge_USD,
        GREATEST(0, (ship.Actual_Demurrage_Days - ctr.Free_Demurrage_Days)) * 50.0 AS Expected_Demurrage_USD
    FROM DeduplicatedInvoices inv
    LEFT JOIN `freight_audit_db.fact_shipments_bol` ship ON inv.BOL_Number = ship.BOL_Number
    LEFT JOIN `freight_audit_db.dim_contract_rates` ctr ON ship.Contract_ID = ctr.Contract_ID
)
SELECT 
    Invoice_Number, BOL_Number, Carrier, Contract_ID, Invoice_Date, Shipment_Date, POL_Origin, POD_Destination, Container_Type, Billed_Total_Amount_USD,
    CASE WHEN invoice_occurence > 1 THEN 0.0 ELSE (Expected_Base_Rate_USD + Expected_Fuel_Surcharge_USD + Expected_Demurrage_USD) END AS Expected_Total_Amount_USD,
    CASE WHEN invoice_occurence > 1 THEN Billed_Total_Amount_USD ELSE GREATEST(0.0, ROUND(Billed_Total_Amount_USD - (Expected_Base_Rate_USD + Expected_Fuel_Surcharge_USD + Expected_Demurrage_USD), 2)) END AS Recoverable_Overcharge_USD,
    CASE 
        WHEN invoice_occurence > 1 THEN 'DUPLICATE_INVOICE'
        WHEN Billed_Base_Rate_USD > Expected_Base_Rate_USD THEN 'BASE_RATE_OVERCHARGE'
        WHEN Billed_Fuel_Surcharge_USD > Expected_Fuel_Surcharge_USD THEN 'FUEL_SURCHARGE_OVERCHARGE'
        WHEN Actual_Demurrage_Days <= Free_Demurrage_Days AND Billed_Demurrage_USD > 0 THEN 'INVALID_DEMURRAGE_CHARGE'
        WHEN Billed_Demurrage_USD > Expected_Demurrage_USD THEN 'DEMURRAGE_OVERCHARGE'
        ELSE 'PASSED'
    END AS Audit_Status
FROM JoinedAuditData;
