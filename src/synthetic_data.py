import pandas as pd
import random
from datetime import datetime, timedelta

# Cấu hình hạt giống ngẫu nhiên để dữ liệu cố định mỗi lần chạy
random.seed(42)

# ---------------------------------------------------------
# 1. TẠO BẢNG MASTER: dim_contract_rates (Cước Hợp Đồng)
# ---------------------------------------------------------
carriers = ['Maersk', 'CMA CGM', 'COSCO', 'ONE', 'Evergreen', 'MSC', 'Hapag-Lloyd']
pol_list = ['VNHPH (Hai Phong)', 'VNSGN (Cat Lai)', 'VNDNG (Da Nang)']
pod_list = ['CNSHA (Shanghai)', 'DEHAM (Hamburg)', 'NLRTM (Rotterdam)', 'USLAX (Los Angeles)']
container_types = ['20DC', '40HC']

contract_data = []
contract_id_counter = 1001

for carrier in carriers:
    for pol in pol_list:
        for pod in pod_list:
            for cont in container_types:
                # Giả lập giá cước hợp đồng hợp lý
                base_rate = random.randint(400, 3200)
                fuel_pct = random.choice([0.10, 0.12, 0.15]) # 10%, 12%, 15%
                free_demurrage = random.choice([5, 7, 10]) # 5, 7 hoặc 10 ngày free
                
                contract_data.append({
                    'Contract_ID': f"CTR-{contract_id_counter}",
                    'Carrier': carrier,
                    'POL_Origin': pol,
                    'POD_Destination': pod,
                    'Container_Type': cont,
                    'Agreed_Base_Rate_USD': base_rate,
                    'Agreed_Fuel_Surcharge_Pct': fuel_pct,
                    'Free_Demurrage_Days': free_demurrage
                })
                contract_id_counter += 1

df_contracts = pd.DataFrame(contract_data)

# ---------------------------------------------------------
# 2. TẠO BẢNG VẬN ĐƠN: fact_shipments_bol (Thực tế Vận chuyển)
# ---------------------------------------------------------
num_shipments = 1000
shipment_data = []

start_date = datetime(2026, 1, 1)

for i in range(1, num_shipments + 1):
    bol_num = f"BOL2026{i:05d}"
    # Chọn ngẫu nhiên 1 hợp đồng từ danh sách
    matched_contract = df_contracts.sample(1).iloc[0]
    
    ship_date = start_date + timedelta(days=random.randint(0, 180))
    # Số ngày lưu bãi thực tế (ngẫu nhiên từ 1 đến 15 ngày)
    actual_demurrage_days = random.randint(1, 15)
    
    shipment_data.append({
        'BOL_Number': bol_num,
        'Contract_ID': matched_contract['Contract_ID'],
        'Carrier': matched_contract['Carrier'],
        'POL_Origin': matched_contract['POL_Origin'],
        'POD_Destination': matched_contract['POD_Destination'],
        'Container_Type': matched_contract['Container_Type'],
        'Shipment_Date': ship_date.strftime('%Y-%m-%d'),
        'Actual_Demurrage_Days': actual_demurrage_days,
        'Free_Demurrage_Days_Ref': matched_contract['Free_Demurrage_Days'],
        'Agreed_Base_Rate_Ref': matched_contract['Agreed_Base_Rate_USD'],
        'Agreed_Fuel_Pct_Ref': matched_contract['Agreed_Fuel_Surcharge_Pct']
    })

df_shipments = pd.DataFrame(shipment_data)

# ---------------------------------------------------------
# 3. TẠO BẢNG HÓA ĐƠN: raw_carrier_invoices (Có chèn lỗi)
# ---------------------------------------------------------
invoice_data = []
inv_id_counter = 5001

for idx, row in df_shipments.iterrows():
    inv_num = f"INV-2026-{inv_id_counter}"
    bol_num = row['BOL_Number']
    carrier = row['Carrier']
    inv_date = datetime.strptime(row['Shipment_Date'], '%Y-%m-%d') + timedelta(days=random.randint(2, 7))
    
    base_rate = row['Agreed_Base_Rate_Ref']
    fuel_pct = row['Agreed_Fuel_Pct_Ref']
    free_days = row['Free_Demurrage_Days_Ref']
    actual_days = row['Actual_Demurrage_Days']
    
    # Mặc định tính đúng
    billed_base = base_rate
    billed_fuel = round(base_rate * fuel_pct, 2)
    
    # Tính phí Demurrage đúng (chỉ phạt số ngày vượt quá free_days)
    excess_days = max(0, actual_days - free_days)
    billed_demurrage = excess_days * 50.0 # 50 USD/ngày phạt
    
    # --- CHÈN LỖI NGHIỆP VỤ (ANOMALY INJECTION) ---
    rand_val = random.random()
    
    # Lỗi 1: Base Rate Overcharge (~3% số hóa đơn)
    if rand_val < 0.03:
        billed_base += random.choice([50, 100, 150, 200])
        
    # Lỗi 2: Fuel Surcharge Overcharge (~3% số hóa đơn)
    elif rand_val < 0.06:
        billed_fuel = round(base_rate * (fuel_pct + 0.05), 2) # Tăng thêm 5% phụ phí
        
    # Lỗi 3: Invalid Demurrage Charge (~2% số hóa đơn)
    # Hàng chưa vượt quá Free Days nhưng vẫn bị tính phạt Demurrage
    elif rand_val < 0.08 and actual_days <= free_days:
        billed_demurrage = 150.0 # Kê khống 150 USD
        
    total_billed = billed_base + billed_fuel + billed_demurrage
    
    invoice_data.append({
        'Invoice_Number': inv_num,
        'BOL_Number': bol_num,
        'Carrier': carrier,
        'Invoice_Date': inv_date.strftime('%Y-%m-%d'),
        'Billed_Base_Rate_USD': billed_base,
        'Billed_Fuel_Surcharge_USD': billed_fuel,
        'Billed_Demurrage_USD': billed_demurrage,
        'Billed_Total_Amount_USD': total_billed
    })
    inv_id_counter += 1

# Lỗi 4: Duplicate Invoices (~2% số hóa đơn bị trùng)
df_invoices = pd.DataFrame(invoice_data)
duplicate_samples = df_invoices.sample(n=20, random_state=42).copy()
# Đổi số hóa đơn để mô phỏng việc phát hành lại hóa đơn trùng cho cùng 1 vận đơn
duplicate_samples['Invoice_Number'] = duplicate_samples['Invoice_Number'].apply(lambda x: f"{x}-DUP")
duplicate_samples['Invoice_Date'] = pd.to_datetime(duplicate_samples['Invoice_Date']) + timedelta(days=1)
duplicate_samples['Invoice_Date'] = duplicate_samples['Invoice_Date'].dt.strftime('%Y-%m-%d')

# Nối hóa đơn trùng vào bảng chính
df_invoices_final = pd.concat([df_invoices, duplicate_samples], ignore_index=True)

# ---------------------------------------------------------
# 4. XUẤT RA CÁC FILE CSV
# ---------------------------------------------------------
# Loại bỏ các cột tạm dùng để tham chiếu trong Bảng Shipments trước khi lưu
df_shipments_clean = df_shipments.drop(columns=['Free_Demurrage_Days_Ref', 'Agreed_Base_Rate_Ref', 'Agreed_Fuel_Pct_Ref'])

df_contracts.to_csv('dim_contract_rates.csv', index=False)
df_shipments_clean.to_csv('fact_shipments_bol.csv', index=False)
df_invoices_final.to_csv('raw_carrier_invoices.csv', index=False)

print("✅ Đã tạo thành công 3 file CSV:")
print(f" 1. dim_contract_rates.csv ({len(df_contracts)} dòng)")
print(f" 2. fact_shipments_bol.csv ({len(df_shipments_clean)} dòng)")
print(f" 3. raw_carrier_invoices.csv ({len(df_invoices_final)} dòng - bao gồm 20 hóa đơn trùng)")