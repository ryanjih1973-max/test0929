import sqlite3
import sys
import unicodedata

# 強制 stdout 使用 UTF-8 編碼，防止 Windows 預設 CP950 導致中文印出報錯或亂碼
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

DB_NAME = "orders.db"

def visual_len(text):
    """計算包含全形中文字元的顯示寬度"""
    return sum(2 if unicodedata.east_asian_width(c) in ('F', 'W') else 1 for c in str(text))

def pad_str(text, width, align='left'):
    """根據顯示寬度進行補空白，確保表格對齊不歪斜"""
    s = str(text)
    vlen = visual_len(s)
    padding = max(0, width - vlen)
    if align == 'right':
        return ' ' * padding + s
    return s + ' ' * padding

def check_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    print("=" * 80)
    print(" 📦 驗證 SQLite 資料庫: orders.db 內容 (繁體中文完整無亂碼)")
    print("=" * 80)

    # 1. 印出 customer 資料表
    print("\n【1. 客戶資料表 (customer)】")
    headers = ["ID", "姓名", "電話", "地址", "建檔日期"]
    widths = [6, 12, 16, 32, 14]
    header_str = "".join(pad_str(h, w) for h, w in zip(headers, widths))
    print(header_str)
    print("-" * 80)

    cursor.execute("SELECT customer_id, name, phone, address, created_at FROM customer;")
    for row in cursor.fetchall():
        line = "".join(pad_str(val, w) for val, w in zip(row, widths))
        print(line)

    # 2. 印出 product 資料表
    print("\n【2. 商品資料表 (product)】")
    headers = ["ID", "商品名稱", "單價(NT$)", "庫存", "分類"]
    widths = [6, 20, 12, 8, 12]
    header_str = "".join(pad_str(h, w) for h, w in zip(headers, widths))
    print(header_str)
    print("-" * 80)

    cursor.execute("SELECT product_id, name, price, stock, category FROM product;")
    for row in cursor.fetchall():
        line = "".join(pad_str(val, w) for val, w in zip(row, widths))
        print(line)

    # 3. 印出 orders 資料表
    print("\n【3. 訂單主表 (orders)】")
    headers = ["訂單ID", "客戶名稱", "訂單日期", "狀態", "業務人員"]
    widths = [8, 12, 22, 10, 12]
    header_str = "".join(pad_str(h, w) for h, w in zip(headers, widths))
    print(header_str)
    print("-" * 80)

    cursor.execute("""
        SELECT o.order_id, c.name, o.order_date, o.status, o.salesperson
        FROM orders o
        JOIN customer c ON o.customer_id = c.customer_id;
    """)
    for row in cursor.fetchall():
        line = "".join(pad_str(val, w) for val, w in zip(row, widths))
        print(line)

    # 4. 印出 order_item 資料表
    print("\n【4. 訂單明細表 (order_item) - 含有多項商品案例】")
    headers = ["訂單ID", "商品名稱", "數量", "歷史單價(NT$)", "小計(NT$)"]
    widths = [8, 20, 8, 14, 12]
    header_str = "".join(pad_str(h, w) for h, w in zip(headers, widths))
    print(header_str)
    print("-" * 80)

    cursor.execute("""
        SELECT oi.order_id, p.name, oi.quantity, oi.unit_price, (oi.quantity * oi.unit_price) AS subtotal
        FROM order_item oi
        JOIN product p ON oi.product_id = p.product_id
        ORDER BY oi.order_id;
    """)
    for row in cursor.fetchall():
        line = "".join(pad_str(val, w) for val, w in zip(row, widths))
        print(line)

    # 5. 統計範例: 每筆訂單總金額彙整
    print("\n【5. 訂單總金額統計彙整】")
    headers = ["訂單ID", "客戶名稱", "商品項目數", "訂單總金額(NT$)"]
    widths = [8, 12, 12, 16]
    header_str = "".join(pad_str(h, w) for h, w in zip(headers, widths))
    print(header_str)
    print("-" * 80)

    cursor.execute("""
        SELECT o.order_id, c.name, COUNT(oi.product_id) AS item_count, SUM(oi.quantity * oi.unit_price) AS total_amount
        FROM orders o
        JOIN customer c ON o.customer_id = c.customer_id
        JOIN order_item oi ON o.order_id = oi.order_id
        GROUP BY o.order_id;
    """)
    for row in cursor.fetchall():
        line = "".join(pad_str(val, w) for val, w in zip(row, widths))
        print(line)

    print("=" * 80)
    conn.close()

if __name__ == "__main__":
    check_db()
