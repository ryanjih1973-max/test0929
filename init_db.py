import sqlite3
import os
import sys
from werkzeug.security import generate_password_hash

# 避免 Windows 主機預設 CP950 編碼印出訊息時報鎖定或錯
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

DB_NAME = "orders.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 關閉外鍵以清理舊表
    cursor.execute("PRAGMA foreign_keys = OFF;")
    cursor.execute("DROP TABLE IF EXISTS order_item;")
    cursor.execute("DROP TABLE IF EXISTS orders;")
    cursor.execute("DROP TABLE IF EXISTS product;")
    cursor.execute("DROP TABLE IF EXISTS customer;")
    cursor.execute("DROP TABLE IF EXISTS admin;")
    
    # 啟用外鍵約束
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 0. 建立 admin 管理員表 (密碼為雜湊值, 含 role 角色)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admin (
        admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'admin'
    );
    """)

    # 1. 建立 customer 資料表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customer (
        customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        address TEXT,
        created_at TEXT DEFAULT (datetime('now', 'localtime'))
    );
    """)

    # 2. 建立 product 資料表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS product (
        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price INTEGER NOT NULL CHECK (price >= 0),
        stock INTEGER NOT NULL CHECK (stock >= 0),
        category TEXT
    );
    """)

    # 3. 建立 orders 資料表 (新增 order_code 訂單編號，格式驗證 SO+數字)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_code TEXT UNIQUE NOT NULL CHECK (order_code GLOB 'SO[0-9]*'),
        customer_id INTEGER NOT NULL,
        order_date TEXT NOT NULL,
        status TEXT NOT NULL CHECK (status IN ('處理中', '已出貨', '已完成', '已取消')),
        salesperson TEXT,
        FOREIGN KEY (customer_id) REFERENCES customer(customer_id) ON DELETE CASCADE
    );
    """)

    # 4. 建立 order_item 資料表 (數量正整數 CHECK (quantity > 0))
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_item (
        order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL CHECK (quantity > 0 AND CAST(quantity AS INTEGER) = quantity),
        unit_price INTEGER NOT NULL CHECK (unit_price >= 0),
        PRIMARY KEY (order_id, product_id),
        FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES product(product_id) ON DELETE RESTRICT
    );
    """)

    print("資料表建立完成！")

    # 插入預設管理員帳號 (密碼使用 werkzeug generate_password_hash 雜湊加密，不留明碼)
    hashed_password = generate_password_hash('admin123')
    cursor.execute("""
    INSERT INTO admin (username, password, role) VALUES (?, ?, ?);
    """, ('admin', hashed_password, 'admin'))

    # 1. 客戶資料 (5 筆)
    customers = [
        ('王小明', '0912-345-678', '臺北市信義區松智路1號', '2026-01-10 09:00:00'),
        ('李美玲', '0923-456-789', '新北市板橋區縣民大道二段7號', '2026-01-15 11:30:00'),
        ('張偉傑', '0934-567-890', '臺中市西屯區台灣大道三段99號', '2026-02-01 14:20:00'),
        ('陳雅婷', '0945-678-901', '高雄市苓雅區四維三路2號', '2026-02-20 16:45:00'),
        ('林志豪', '0956-789-012', '新竹市東區光復路二段101號', '2026-03-05 10:15:00')
    ]
    cursor.executemany("""
    INSERT INTO customer (name, phone, address, created_at)
    VALUES (?, ?, ?, ?);
    """, customers)

    # 2. 商品資料 (5 筆)
    products = [
        ('極速筆記型電腦', 35000, 20, '3C電子'),
        ('無線藍牙耳機', 2800, 50, '3C電子'),
        ('人體工學辦公椅', 6500, 15, '家具'),
        ('機械式電競鍵盤', 3200, 30, '周邊配件'),
        ('27吋4K顯示器', 12500, 10, '3C電子')
    ]
    cursor.executemany("""
    INSERT INTO product (name, price, stock, category)
    VALUES (?, ?, ?, ?);
    """, products)

    # 3. 訂單資料 (5 筆，訂單編號格式為 SO + 數字)
    orders = [
        ('SO2026001', 1, '2026-03-10 10:30:00', '已完成', '陳大為'),
        ('SO2026002', 2, '2026-03-12 14:15:00', '處理中', '林靜宜'),
        ('SO2026003', 3, '2026-03-15 09:45:00', '已出貨', '陳大為'),
        ('SO2026004', 4, '2026-03-18 16:20:00', '已完成', '張家豪'),
        ('SO2026005', 5, '2026-03-20 11:00:00', '處理中', '林靜宜')
    ]
    cursor.executemany("""
    INSERT INTO orders (order_code, customer_id, order_date, status, salesperson)
    VALUES (?, ?, ?, ?, ?);
    """, orders)

    # 4. 訂單明細資料 (7 筆)
    order_items = [
        (1, 1, 1, 35000),  # SO2026001: 筆電 (1台)
        (1, 4, 2, 3200),   # SO2026001: 鍵盤 (2個)
        (2, 2, 1, 2800),   # SO2026002: 耳機 (1個)
        (2, 5, 1, 12500),  # SO2026002: 顯示器 (1台)
        (3, 3, 2, 6500),   # SO2026003: 辦公椅 (2張)
        (4, 4, 1, 3200),   # SO2026004: 鍵盤 (1個)
        (5, 2, 3, 2800)    # SO2026005: 耳機 (3個)
    ]
    cursor.executemany("""
    INSERT INTO order_item (order_id, product_id, quantity, unit_price)
    VALUES (?, ?, ?, ?);
    """, order_items)

    conn.commit()
    conn.close()
    print("orders.db 資料庫初始化與測試資料插入完成 (密碼已雜湊化，含 SO 訂單編號)！")

if __name__ == "__main__":
    init_db()
