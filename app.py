import sqlite3
import datetime
import io
import base64
import re
import os
import qrcode
from functools import wraps
from werkzeug.security import check_password_hash
from flask import Flask, render_template, request, redirect, url_for, flash, session
from init_db import init_db

app = Flask(__name__)
app.secret_key = "secret_orders_app_key_2026_secured"
DB_NAME = "orders.db"

# 若資料庫不存在，自動初始化
if not os.path.exists(DB_NAME):
    init_db()

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

# ---------------------------------------------------------
# 權限驗證 Decorator (驗證 Session 與 管理員角色 role == 'admin')
# ---------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("admin_logged_in") or session.get("role") != "admin":
            flash("權限不足！後台所有頁面僅限已登入且具備管理員(admin)角色的使用者存取。", "danger")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

# ---------------------------------------------------------
# 認證 Routes (Werkzeug 雜湊密碼驗證)
# ---------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        # 100% 參數化查詢，防止 SQL 注入
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT admin_id, username, password, role FROM admin WHERE username = ?;", (username,))
        admin = cursor.fetchone()
        conn.close()

        # 使用 werkzeug.security check_password_hash 驗證雜湊密碼，不出現明碼
        if admin and check_password_hash(admin["password"], password) and admin["role"] == "admin":
            session["admin_logged_in"] = True
            session["username"] = admin["username"]
            session["role"] = admin["role"]
            flash("登入成功！歡迎使用訂單管理系統。", "success")
            return redirect(url_for("index"))
        else:
            flash("帳號、密碼錯誤或未具備管理員權限！", "danger")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("您已安全登出系統。", "info")
    return redirect(url_for("login"))

# ---------------------------------------------------------
# 儀表板 / 首頁 Route (需要管理員權限)
# ---------------------------------------------------------
@app.route("/")
@login_required
def index():
    conn = get_db()
    cursor = conn.cursor()

    # 1. 參數化與安全性統計查詢
    cursor.execute("SELECT COUNT(*) AS total FROM orders;")
    total_orders = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM customer;")
    total_customers = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM product;")
    total_products = cursor.fetchone()["total"]

    cursor.execute("SELECT COALESCE(SUM(quantity * unit_price), 0) AS total FROM order_item;")
    total_revenue = cursor.fetchone()["total"]

    # 2. 最新 5 筆訂單
    cursor.execute("""
        SELECT o.order_id, o.order_code, c.name AS customer_name, o.order_date, o.status, o.salesperson,
               COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS total_amount
        FROM orders o
        JOIN customer c ON o.customer_id = c.customer_id
        LEFT JOIN order_item oi ON o.order_id = oi.order_id
        GROUP BY o.order_id
        ORDER BY o.order_id DESC
        LIMIT 5;
    """)
    recent_orders = cursor.fetchall()
    conn.close()

    return render_template("index.html",
                           total_orders=total_orders,
                           total_revenue=total_revenue,
                           total_customers=total_customers,
                           total_products=total_products,
                           recent_orders=recent_orders)

# ---------------------------------------------------------
# 客戶管理 Routes (參數化查詢 + 管理員權限)
# ---------------------------------------------------------
@app.route("/customers", methods=["GET", "POST"])
@login_required
def customers():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()

        if name:
            cursor.execute("""
                INSERT INTO customer (name, phone, address, created_at)
                VALUES (?, ?, ?, datetime('now', 'localtime'));
            """, (name, phone, address))
            conn.commit()
            flash(f"已成功新增客戶「{name}」！", "success")
        conn.close()
        return redirect(url_for("customers"))

    cursor.execute("SELECT * FROM customer ORDER BY customer_id DESC;")
    customer_list = cursor.fetchall()
    conn.close()
    return render_template("customers.html", customers=customer_list)

@app.route("/customer/<int:customer_id>/edit", methods=["POST"])
@login_required
def edit_customer(customer_id):
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    address = request.form.get("address", "").strip()

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE customer
        SET name = ?, phone = ?, address = ?
        WHERE customer_id = ?;
    """, (name, phone, address, customer_id))
    conn.commit()
    conn.close()
    flash("客戶資料已更新！", "success")
    return redirect(url_for("customers"))

@app.route("/customer/<int:customer_id>/delete", methods=["POST"])
@login_required
def delete_customer(customer_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM customer WHERE customer_id = ?;", (customer_id,))
    conn.commit()
    conn.close()
    flash("客戶已順利刪除！", "info")
    return redirect(url_for("customers"))

# ---------------------------------------------------------
# 商品管理 Routes (參數化查詢 + 管理員權限)
# ---------------------------------------------------------
@app.route("/products", methods=["GET", "POST"])
@login_required
def products():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        
        try:
            price = int(request.form.get("price", 0))
            stock = int(request.form.get("stock", 0))
            if price < 0 or stock < 0:
                raise ValueError
        except ValueError:
            flash("單價與庫存必須為非負整數！", "danger")
            conn.close()
            return redirect(url_for("products"))

        if name:
            cursor.execute("""
                INSERT INTO product (name, price, stock, category)
                VALUES (?, ?, ?, ?);
            """, (name, price, stock, category))
            conn.commit()
            flash(f"已成功新增商品「{name}」！", "success")
        conn.close()
        return redirect(url_for("products"))

    cursor.execute("SELECT * FROM product ORDER BY product_id DESC;")
    product_list = cursor.fetchall()
    conn.close()
    return render_template("products.html", products=product_list)

@app.route("/product/<int:product_id>/edit", methods=["POST"])
@login_required
def edit_product(product_id):
    name = request.form.get("name", "").strip()
    category = request.form.get("category", "").strip()
    try:
        price = int(request.form.get("price", 0))
        stock = int(request.form.get("stock", 0))
        if price < 0 or stock < 0:
            raise ValueError
    except ValueError:
        flash("單價與庫存必須為非負整數！", "danger")
        return redirect(url_for("products"))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE product
        SET name = ?, category = ?, price = ?, stock = ?
        WHERE product_id = ?;
    """, (name, category, price, stock, product_id))
    conn.commit()
    conn.close()
    flash("商品資料已更新！", "success")
    return redirect(url_for("products"))

@app.route("/product/<int:product_id>/delete", methods=["POST"])
@login_required
def delete_product(product_id):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM product WHERE product_id = ?;", (product_id,))
        conn.commit()
        flash("商品已順利刪除！", "info")
    except sqlite3.IntegrityError:
        flash("無法刪除該商品，因為已有歷史訂單引用該商品紀錄！", "danger")
    finally:
        conn.close()
    return redirect(url_for("products"))

# ---------------------------------------------------------
# 訂單管理 Routes (SO 格式驗證 + 正整數數量二層防護 + 參數化 SQL)
# ---------------------------------------------------------
@app.route("/orders")
@login_required
def orders():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT o.order_id, o.order_code, c.name AS customer_name, c.phone AS customer_phone,
               o.order_date, o.status, o.salesperson,
               COUNT(oi.product_id) AS item_count,
               COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS total_amount
        FROM orders o
        JOIN customer c ON o.customer_id = c.customer_id
        LEFT JOIN order_item oi ON o.order_id = oi.order_id
        GROUP BY o.order_id
        ORDER BY o.order_id DESC;
    """)
    order_list = cursor.fetchall()
    conn.close()
    return render_template("orders.html", orders=order_list)

@app.route("/orders/new", methods=["GET", "POST"])
@login_required
def new_order():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":
        order_code = request.form.get("order_code", "").strip()
        customer_id = request.form.get("customer_id")
        salesperson = request.form.get("salesperson", "").strip()
        
        # 下拉選單商品與數量列表
        product_ids = request.form.getlist("product_id[]")
        quantities = request.form.getlist("quantity[]")

        # 4. 格式驗證: 訂單編號必須為 SO + 數字 (例如 SO2026006)
        if not order_code or not re.match(r"^SO\d+$", order_code):
            flash("訂單編號格式不符！必須是大寫 SO 開頭搭配數字 (例如: SO2026006)", "danger")
            conn.close()
            return redirect(url_for("new_order"))

        # 檢查訂單編號是否已存在
        cursor.execute("SELECT order_id FROM orders WHERE order_code = ?;", (order_code,))
        if cursor.fetchone():
            flash(f"訂單編號「{order_code}」已存在，請使用不同的 SO 訂單編號！", "danger")
            conn.close()
            return redirect(url_for("new_order"))

        if not customer_id or not product_ids or len(product_ids) == 0:
            flash("請選擇客戶並至少新增一項採購商品！", "danger")
            conn.close()
            return redirect(url_for("new_order"))

        # 5. 後端數量正整數驗證 (二層防護: 檢查正整數 & 庫存)
        selected_items = {}
        for pid_str, qty_str in zip(product_ids, quantities):
            if not pid_str:
                continue

            try:
                pid = int(pid_str)
                qty = int(qty_str)
                # 嚴格正整數檢查
                if qty <= 0:
                    raise ValueError
            except (ValueError, TypeError):
                flash("商品採購數量必須是大於 0 的正整數！", "danger")
                conn.close()
                return redirect(url_for("new_order"))

            cursor.execute("SELECT product_id, name, price, stock FROM product WHERE product_id = ?;", (pid,))
            prod = cursor.fetchone()
            if not prod:
                flash("選擇的商品不存在！", "danger")
                conn.close()
                return redirect(url_for("new_order"))

            # 若同一商品重複選擇，累加數量
            current_qty = selected_items.get(pid, {}).get("quantity", 0) + qty
            if current_qty > prod["stock"]:
                flash(f"商品「{prod['name']}」庫存不足！(剩餘庫存: {prod['stock']}，欲購總數: {current_qty})", "danger")
                conn.close()
                return redirect(url_for("new_order"))

            selected_items[pid] = {
                "product_id": pid,
                "name": prod["name"],
                "unit_price": prod["price"], # 保存「下單當時」的價格
                "quantity": current_qty
            }

        if not selected_items:
            flash("請至少選擇一項有效商品！", "danger")
            conn.close()
            return redirect(url_for("new_order"))

        # 寫入訂單主檔 (100% 參數化查詢)
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO orders (order_code, customer_id, order_date, status, salesperson)
            VALUES (?, ?, ?, '處理中', ?);
        """, (order_code, customer_id, now_str, salesperson))
        new_order_id = cursor.lastrowid

        # 寫入訂單明細檔與扣減庫存 (100% 參數化查詢)
        for item in selected_items.values():
            cursor.execute("""
                INSERT INTO order_item (order_id, product_id, quantity, unit_price)
                VALUES (?, ?, ?, ?);
            """, (new_order_id, item["product_id"], item["quantity"], item["unit_price"]))

            cursor.execute("""
                UPDATE product SET stock = stock - ? WHERE product_id = ?;
            """, (item["quantity"], item["product_id"]))

        conn.commit()
        conn.close()
        flash(f"訂單 [{order_code}] 建立成功！歷史單價已寫入，庫存已自動扣減。", "success")
        return redirect(url_for("order_detail", order_id=new_order_id))

    # GET 請求: 產生預設 SO 編號與下拉資料
    now_tag = datetime.datetime.now().strftime("%Y%m%d%H%M")
    default_so_code = f"SO{now_tag}"

    cursor.execute("SELECT customer_id, name, phone, address FROM customer ORDER BY customer_id ASC;")
    customer_list = cursor.fetchall()

    cursor.execute("SELECT product_id, name, price, stock, category FROM product ORDER BY product_id ASC;")
    product_list = cursor.fetchall()
    conn.close()

    return render_template("order_new.html",
                           default_so_code=default_so_code,
                           customers=customer_list,
                           products=product_list)

@app.route("/order/<int:order_id>")
@login_required
def order_detail(order_id):
    conn = get_db()
    cursor = conn.cursor()

    # 查訂單主檔 (參數化查詢)
    cursor.execute("""
        SELECT o.order_id, o.order_code, o.order_date, o.status, o.salesperson,
               c.name AS customer_name, c.phone AS customer_phone, c.address AS customer_address
        FROM orders o
        JOIN customer c ON o.customer_id = c.customer_id
        WHERE o.order_id = ?;
    """, (order_id,))
    order = cursor.fetchone()

    if not order:
        conn.close()
        flash("找不到該筆訂單！", "danger")
        return redirect(url_for("orders"))

    # 查訂單明細 (參數化查詢)
    cursor.execute("""
        SELECT oi.product_id, p.name AS product_name, p.category,
               oi.quantity, oi.unit_price, (oi.quantity * oi.unit_price) AS subtotal
        FROM order_item oi
        JOIN product p ON oi.product_id = p.product_id
        WHERE oi.order_id = ?;
    """, (order_id,))
    items = cursor.fetchall()
    conn.close()

    total_amount = sum(item["subtotal"] for item in items)

    # 產生專屬出貨單 QRCode Data URI (指向 SO 訂單)
    order_url = f"{request.host_url}order/{order_id}"
    qr = qrcode.QRCode(version=1, box_size=5, border=2)
    qr.add_data(order_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_code_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    qr_code_url = f"data:image/png;base64,{qr_code_base64}"

    return render_template("order_detail.html",
                           order=order,
                           items=items,
                           total_amount=total_amount,
                           qr_code_url=qr_code_url)

@app.route("/order/<int:order_id>/update_status", methods=["POST"])
@login_required
def update_order_status(order_id):
    new_status = request.form.get("status")
    if new_status in ['處理中', '已出貨', '已完成', '已取消']:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE orders SET status = ? WHERE order_id = ?;", (new_status, order_id))
        conn.commit()
        conn.close()
        flash(f"訂單狀態已成功更新為「{new_status}」！", "success")
    return redirect(request.referrer or url_for("orders"))

@app.route("/order/<int:order_id>/delete", methods=["POST"])
@login_required
def delete_order(order_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM orders WHERE order_id = ?;", (order_id,))
    conn.commit()
    conn.close()
    flash("訂單已成功刪除！", "info")
    return redirect(url_for("orders"))

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
