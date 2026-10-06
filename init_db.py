import sqlite3
import os
import sys

# 避免 Windows 主機預設 cp950 編碼印出訊息報錯
sys.stdout.reconfigure(encoding='utf-8')

DB_NAME = "orders.db"

def init_db():
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
        print(f"舊有 {DB_NAME} 已刪除，重新建立新資料庫...")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 啟用外鍵約束
    cursor.execute("PRAGMA foreign_keys = ON;")

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

    # 3. 建立 orders 資料表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        order_date TEXT NOT NULL,
        status TEXT NOT NULL,
        salesperson TEXT,
        FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
    );
    """)

    # 4. 建立 order_item 資料表 (複合主鍵 + CHECK 約束)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_item (
        order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL CHECK (quantity > 0),
        unit_price INTEGER NOT NULL CHECK (unit_price >= 0),
        PRIMARY KEY (order_id, product_id),
        FOREIGN KEY (order_id) REFERENCES orders(order_id),
        FOREIGN KEY (product_id) REFERENCES product(product_id)
    );
    """)

    print("資料表建立完成！")

    # 插入測試資料 (各 5 筆以上)
    # 1. 客戶資料 (5 筆)
    customers = [
        ('王小明', '0912-345-678', '臺北市信義區松智路1號', '2026-01-10'),
        ('李美玲', '0923-456-789', '新北市板橋區縣民大道二段7號', '2026-01-15'),
        ('張偉傑', '0934-567-890', '臺中市西屯區台灣大道三段99號', '2026-02-01'),
        ('陳雅婷', '0945-678-901', '高雄市苓雅區四維三路2號', '2026-02-20'),
        ('林志豪', '0956-789-012', '新竹市東區光復路二段101號', '2026-03-05')
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

    # 3. 訂單資料 (5 筆)
    orders = [
        (1, '2026-03-10 10:30:00', '已完成', '陳大為'),
        (2, '2026-03-12 14:15:00', '處理中', '林靜宜'),
        (3, '2026-03-15 09:45:00', '已出貨', '陳大為'),
        (4, '2026-03-18 16:20:00', '已完成', '張家豪'),
        (5, '2026-03-20 11:00:00', '處理中', '林靜宜')
    ]
    cursor.executemany("""
    INSERT INTO orders (customer_id, order_date, status, salesperson)
    VALUES (?, ?, ?, ?);
    """, orders)

    # 4. 訂單明細資料 (7 筆，涵蓋 5 筆訂單，訂單 1 與 訂單 2 包含多項商品)
    order_items = [
        (1, 1, 1, 35000),  # 訂單 1: 筆電 (1台)
        (1, 4, 2, 3200),   # 訂單 1: 鍵盤 (2個) -> 訂單 1 含多項商品
        (2, 2, 1, 2800),   # 訂單 2: 耳機 (1個)
        (2, 5, 1, 12500),  # 訂單 2: 顯示器 (1台) -> 訂單 2 含多項商品
        (3, 3, 2, 6500),   # 訂單 3: 辦公椅 (2張)
        (4, 4, 1, 3200),   # 訂單 4: 鍵盤 (1個)
        (5, 2, 3, 2800)    # 訂單 5: 耳機 (3個)
    ]
    cursor.executemany("""
    INSERT INTO order_item (order_id, product_id, quantity, unit_price)
    VALUES (?, ?, ?, ?);
    """, order_items)

    conn.commit()
    conn.close()
    print("測試資料插入完成！")

if __name__ == "__main__":
    init_db()
