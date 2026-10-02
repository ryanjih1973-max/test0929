from flask import Flask, render_template_string

app = Flask(__name__)

# 一頁式網站 HTML 模板（內嵌美觀的 CSS 樣式）
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hello World - Flask 一頁式網站</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Microsoft JhengHei", sans-serif;
        }
        body {
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
        }
        .card {
            background: rgba(255, 255, 255, 0.95);
            padding: 2.5rem 3.5rem;
            border-radius: 1.25rem;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.2);
            text-align: center;
            max-width: 500px;
            width: 90%;
            transition: transform 0.3s ease;
        }
        .card:hover {
            transform: translateY(-5px);
        }
        h1 {
            font-size: 2.5rem;
            color: #4a5568;
            margin-bottom: 1rem;
        }
        p {
            font-size: 1.1rem;
            color: #718096;
            line-height: 1.6;
            margin-bottom: 1.5rem;
        }
        .badge {
            display: inline-block;
            background-color: #e2e8f0;
            color: #4a5568;
            padding: 0.4rem 1rem;
            border-radius: 9999px;
            font-size: 0.875rem;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="card">
        <h1>👋 Hello, World!</h1>
        <p>歡迎來到使用 <strong>Python Flask</strong> 建立的一頁式網站。 製作者:季振忠助理教授</p>
        <span class="badge">Flask Web App</span>
    </div>
</body>
</html>
"""

@app.route("/")
def hello_world():
    return render_template_string(HTML_TEMPLATE)

if __name__ == "__main__":
    # 本地測試時啟動，預設網址為 http://127.0.0.1:5000
    app.run(debug=True, host="127.0.0.1", port=5000)
