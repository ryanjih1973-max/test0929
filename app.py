import sqlite3
import datetime
import io
import base64
import qrcode
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session

app = Flask(__name__)
app.secret_key = "secret_orders_app_key_2026"
DB_NAME = "orders.db"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("admin_logged_in"):
            flash("請先登入管理員帳號！", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

# ---------------------------------------------------------
# 認證 Route
# ---------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admin WHERE username = ? AND password = ?", (username, password))
        admin = cursor.fetchone()
        conn.close()

        if admin:
            session["admin_logged_in"] = True
            session["username"] = admin["username"]
            flash("登入成功！歡迎使用訂單管理系統。", "success")
            return redirect(url_for("index"))
        else:
            flash("帳號或密碼錯誤，請重新輸入 (預設: admin / admin123)", "danger")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("您已安全登出系統。", "info")
    return redirect(url_for("login"))

# ---------------------------------------------------------
# 儀表板 / 首頁 Route
# ---------------------------------------------------------
@app.route("/")
@login_required
def index():
    conn = get_db()
    cursor = conn.cursor()

    # 1. 統計資料
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
        SELECT o.order_id, c.name AS customer_name, o.order_date, o.status, o.salesperson,
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
# 客戶管理 Routes
# ---------------------------------------------------------
@app.route("/customers", methods=["GET", "POST"])
@login_required
def customers():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":
        name = request.form.get("name")
        phone = request.form.get("phone")
        address = request.form.get("address")

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
    name = request.form.get("name")
    phone = request.form.get("phone")
    address = request.form.get("address")

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
# 商品管理 Routes
# ---------------------------------------------------------
@app.route("/products", methods=["GET", "POST"])
@login_required
def products():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":
        name = request.form.get("name")
        category = request.form.get("category")
        price = int(request.form.get("price", 0))
        stock = int(request.form.get("stock", 0))

        if name and price >= 0 and stock >= 0:
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
    name = request.form.get("name")
    category = request.form.get("category")
    price = int(request.form.get("price", 0))
    stock = int(request.form.get("stock", 0))

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
# 訂單管理 Routes
# ---------------------------------------------------------
@app.route("/orders")
@login_required
def orders():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT o.order_id, c.name AS customer_name, c.phone AS customer_phone,
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
        customer_id = request.form.get("customer_id")
        salesperson = request.form.get("salesperson")
        product_ids = request.form.getlist("product_ids")

        if not customer_id or not product_ids:
            flash("請填寫完整資訊並至少勾選一項商品！", "danger")
            return redirect(url_for("new_order"))

        # 檢查所選商品與庫存
        selected_items = []
        for pid_str in product_ids:
            pid = int(pid_str)
            qty = int(request.form.get(f"quantity_{pid}", 1))

            cursor.execute("SELECT product_id, name, price, stock FROM product WHERE product_id = ?;", (pid,))
            prod = cursor.fetchone()
            if not prod:
                continue

            if qty > prod["stock"]:
                flash(f"商品「{prod['name']}」庫存不足 (剩餘: {prod['stock']}，欲購: {qty})", "danger")
                conn.close()
                return redirect(url_for("new_order"))

            selected_items.append({
                "product_id": pid,
                "name": prod["name"],
                "unit_price": prod["price"], # 儲存下單當時的價格
                "quantity": qty
            })

        # 建立訂單
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO orders (customer_id, order_date, status, salesperson)
            VALUES (?, ?, '處理中', ?);
        """, (customer_id, now_str, salesperson))
        new_order_id = cursor.lastrowid

        # 寫入 order_item 明細與扣減庫存
        for item in selected_items:
            cursor.execute("""
                INSERT INTO order_item (order_id, product_id, quantity, unit_price)
                VALUES (?, ?, ?, ?);
            """, (new_order_id, item["product_id"], item["quantity"], item["unit_price"]))

            cursor.execute("""
                UPDATE product SET stock = stock - ? WHERE product_id = ?;
            """, (item["quantity"], item["product_id"]))

        conn.commit()
        conn.close()
        flash(f"訂單 #{new_order_id} 建立成功！商品歷史單價已寫入，庫存已扣減。", "success")
        return redirect(url_for("order_detail", order_id=new_order_id))

    cursor.execute("SELECT customer_id, name, phone, address FROM customer ORDER BY customer_id ASC;")
    customer_list = cursor.fetchall()

    cursor.execute("SELECT product_id, name, price, stock, category FROM product ORDER BY product_id ASC;")
    product_list = cursor.fetchall()
    conn.close()

    return render_template("order_new.html", customers=customer_list, products=product_list)

@app.route("/order/<int:order_id>")
@login_required
def order_detail(order_id):
    conn = get_db()
    cursor = conn.cursor()

    # 查訂單主檔與客戶資訊
    cursor.execute("""
        SELECT o.order_id, o.order_date, o.status, o.salesperson,
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

    # 查訂單明細
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

    # 產生專屬出貨單 QRCode Data URI
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
        flash(f"訂單 #{order_id} 狀態已更新為「{new_status}」！", "success")
    return redirect(request.referrer or url_for("orders"))

@app.route("/order/<int:order_id>/delete", methods=["POST"])
@login_required
def delete_order(order_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM orders WHERE order_id = ?;", (order_id,))
    conn.commit()
    conn.close()
    flash(f"訂單 #{order_id} 已成功刪除！", "info")
    return redirect(url_for("orders"))

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
