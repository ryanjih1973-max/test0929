import sqlite3
import sys
import unicodedata

# 強制 stdout 使用 UTF-8 編碼
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

DB_NAME = "orders.db"

def visual_len(text):
    return sum(2 if unicodedata.east_asian_width(c) in ('F', 'W') else 1 for c in str(text))

def pad_str(text, width, align='left'):
    s = str(text)
    vlen = visual_len(s)
    padding = max(0, width - vlen)
    if align == 'right':
        return ' ' * padding + s
    return s + ' ' * padding

def check_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    print("=" * 85)
    print(" 📦 驗證 SQLite 資料庫: orders.db 內容 (含 Werkzeug 雜湊與 SO 格式編號)")
    print("=" * 85)

    # 0. 印出 admin 資料表 (顯示雜湊密碼與 role)
    print("\n【0. 管理員表 (admin - Werkzeug 雜湊儲存)】")
    headers = ["ID", "帳號", "雜湊密碼 (部分隱藏)", "角色"]
    widths = [6, 12, 50, 10]
    print("".join(pad_str(h, w) for h, w in zip(headers, widths)))
    print("-" * 85)
    cursor.execute("SELECT admin_id, username, password, role FROM admin WHERE admin_id = ?;", (1,))
    for row in cursor.fetchall():
        masked_pwd = row[2][:25] + "..."
        line = pad_str(row[0], widths[0]) + pad_str(row[1], widths[1]) + pad_str(masked_pwd, widths[2]) + pad_str(row[3], widths[3])
        print(line)

    # 1. 印出 customer 資料表
    print("\n【1. 客戶資料表 (customer)】")
    headers = ["ID", "姓名", "電話", "地址", "建檔日期"]
    widths = [6, 12, 16, 32, 14]
    print("".join(pad_str(h, w) for h, w in zip(headers, widths)))
    print("-" * 85)
    cursor.execute("SELECT customer_id, name, phone, address, created_at FROM customer;")
    for row in cursor.fetchall():
        print("".join(pad_str(val, w) for val, w in zip(row, widths)))

    # 2. 印出 product 資料表
    print("\n【2. 商品資料表 (product)】")
    headers = ["ID", "商品名稱", "單價(NT$)", "庫存", "分類"]
    widths = [6, 20, 12, 8, 12]
    print("".join(pad_str(h, w) for h, w in zip(headers, widths)))
    print("-" * 85)
    cursor.execute("SELECT product_id, name, price, stock, category FROM product;")
    for row in cursor.fetchall():
        print("".join(pad_str(val, w) for val, w in zip(row, widths)))

    # 3. 印出 orders 資料表 (包含 order_code SO+數字 驗證)
    print("\n【3. 訂單主表 (orders - 格式 SO+數字)】")
    headers = ["ID", "訂單編號(SO)", "客戶名稱", "訂單日期", "狀態", "業務人員"]
    widths = [6, 14, 12, 22, 10, 12]
    print("".join(pad_str(h, w) for h, w in zip(headers, widths)))
    print("-" * 85)
    cursor.execute("""
        SELECT o.order_id, o.order_code, c.name, o.order_date, o.status, o.salesperson
        FROM orders o
        JOIN customer c ON o.customer_id = c.customer_id;
    """)
    for row in cursor.fetchall():
        print("".join(pad_str(val, w) for val, w in zip(row, widths)))

    # 4. 印出 order_item 資料表
    print("\n【4. 訂單明細表 (order_item)】")
    headers = ["訂單ID", "商品名稱", "數量", "歷史單價(NT$)", "小計(NT$)"]
    widths = [8, 20, 8, 14, 12]
    print("".join(pad_str(h, w) for h, w in zip(headers, widths)))
    print("-" * 85)
    cursor.execute("""
        SELECT oi.order_id, p.name, oi.quantity, oi.unit_price, (oi.quantity * oi.unit_price) AS subtotal
        FROM order_item oi
        JOIN product p ON oi.product_id = p.product_id
        ORDER BY oi.order_id;
    """)
    for row in cursor.fetchall():
        print("".join(pad_str(val, w) for val, w in zip(row, widths)))

    print("=" * 85)
    conn.close()

if __name__ == "__main__":
    check_db()
