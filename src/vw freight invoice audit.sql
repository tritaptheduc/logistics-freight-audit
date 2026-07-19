-- Tạo hoặc thay thế View Kiểm toán Hóa đơn Cước
CREATE OR REPLACE VIEW `freight_audit_db.vw_freight_invoice_audit` AS

WITH DeduplicatedInvoices AS (
    -- Step 1: Nhận diện Hóa đơn Trùng (RULE 1: Duplicate Billing)
    SELECT 
        Invoice_Number,
        BOL_Number,
        Carrier,
        Invoice_Date,
        Billed_Base_Rate_USD,
        Billed_Fuel_Surcharge_USD,
        Billed_Demurrage_USD,
        Billed_Total_Amount_USD,
        
        -- Đánh số thứ tự để tìm hóa đơn trùng trên cùng 1 BOL_Number
        ROW_NUMBER() OVER(
            PARTITION BY BOL_Number 
            ORDER BY Invoice_Date ASC, Invoice_Number ASC
        ) AS invoice_occurence
    FROM 
        `freight_audit_db.raw_carrier_invoices`
),

JoinedAuditData AS (
    -- Step 2: Join dữ liệu Hóa đơn với Vận đơn thực tế và Hợp đồng cước chuẩn
    SELECT 
        inv.Invoice_Number,
        inv.BOL_Number,
        inv.Carrier,
        inv.Invoice_Date,
        inv.invoice_occurence,
        
        -- Thông tin Vận đơn thực tế
        Shipment_Date,
        ship.POL_Origin,
        ship.POD_Destination,
        ship.Container_Type,
        ship.Actual_Demurrage_Days,
        
        -- Thông tin Hợp đồng thỏa thuận
        ctr.Contract_ID,
        ctr.Agreed_Base_Rate_USD,
        ctr.Agreed_Fuel_Surcharge_Pct,
        ctr.Free_Demurrage_Days,
        
        -- Chi tiết Số tiền Hãng đòi trên Hóa đơn
        inv.Billed_Base_Rate_USD,
        inv.Billed_Fuel_Surcharge_USD,
        inv.Billed_Demurrage_USD,
        inv.Billed_Total_Amount_USD,
        
        -- Tính toán Giá đúng chuẩn theo Hợp đồng
        ctr.Agreed_Base_Rate_USD AS Expected_Base_Rate_USD,
        ROUND(ctr.Agreed_Base_Rate_USD * ctr.Agreed_Fuel_Surcharge_Pct, 2) AS Expected_Fuel_Surcharge_USD,
        
        -- Phí Demurrage đúng = (Số ngày thực tế - Số ngày free) * 50 USD/ngày (Nếu <= 0 thì bằng 0)
        GREATEST(0, (ship.Actual_Demurrage_Days - ctr.Free_Demurrage_Days)) * 50.0 AS Expected_Demurrage_USD

    FROM 
        DeduplicatedInvoices inv
    LEFT JOIN 
        `freight_audit_db.fact_shipments_bol` ship ON inv.BOL_Number = ship.BOL_Number
    LEFT JOIN 
        `freight_audit_db.dim_contract_rates` ctr ON ship.Contract_ID = ctr.Contract_ID
)

-- Step 3: Áp dụng Business Logic & Gắn Cờ Lỗi (Audit Flags)
SELECT 
    Invoice_Number,
    BOL_Number,
    Carrier,
    Contract_ID,
    Invoice_Date,
    Shipment_Date,
    POL_Origin,
    POD_Destination,
    Container_Type,
    
    -- Số tiền Hóa đơn vs Số tiền Chuẩn
    Billed_Total_Amount_USD,
    
    -- Nếu là Hóa đơn trùng (occurence > 1), Số tiền hợp lệ (Expected) sẽ bằng 0
    CASE 
        WHEN invoice_occurence > 1 THEN 0.0
        ELSE (Expected_Base_Rate_USD + Expected_Fuel_Surcharge_USD + Expected_Demurrage_USD)
    END AS Expected_Total_Amount_USD,
    
    -- Tính Số tiền Sai lệch có thể Thu hồi (Recoverable Overcharge Amount)
    CASE 
        WHEN invoice_occurence > 1 THEN Billed_Total_Amount_USD
        ELSE GREATEST(0.0, ROUND(Billed_Total_Amount_USD - (Expected_Base_Rate_USD + Expected_Fuel_Surcharge_USD + Expected_Demurrage_USD), 2))
    END AS Recoverable_Overcharge_USD,
    
    -- 🚩 GẮN CỜ PHÂN LOẠI LỖI (AUDIT ANOMALY FLAG)
    CASE 
        WHEN invoice_occurence > 1 
            THEN 'DUPLICATE_INVOICE'
        WHEN Billed_Base_Rate_USD > Expected_Base_Rate_USD 
            THEN 'BASE_RATE_OVERCHARGE'
        WHEN Billed_Fuel_Surcharge_USD > Expected_Fuel_Surcharge_USD 
            THEN 'FUEL_SURCHARGE_OVERCHARGE'
        WHEN Actual_Demurrage_Days <= Free_Demurrage_Days AND Billed_Demurrage_USD > 0 
            THEN 'INVALID_DEMURRAGE_CHARGE'
        WHEN Billed_Demurrage_USD > Expected_Demurrage_USD 
            THEN 'DEMURRAGE_OVERCHARGE'
        ELSE 'PASSED'
    END AS Audit_Status,
    
    -- Chi tiết lỗi
    Billed_Base_Rate_USD, Expected_Base_Rate_USD,
    Billed_Fuel_Surcharge_USD, Expected_Fuel_Surcharge_USD,
    Billed_Demurrage_USD, Expected_Demurrage_USD

FROM 
    JoinedAuditData;