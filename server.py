from flask import Flask, request, jsonify, session, redirect, url_for
from flask_cors import CORS
from datetime import datetime
import os
import logging

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Secret key – environmentdan o'qiladi (Render.io da qo'shing!)
app.secret_key = os.getenv('SECRET_KEY') or 'fallback_secret_for_local'

# Login/parol – environmentdan o'qiladi (xavfsiz)
ADMIN_LOGIN = os.getenv('ADMIN_LOGIN') or "admin"
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD') or "1978"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

pages = {}    # client_id → sahifa ma'lumotlari
messages = {} # client_id → matn (box ga chiqadigan)

def login_required(f):
    def wrap(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_input = request.form.get('login')
        password_input = request.form.get('password')
        if login_input == ADMIN_LOGIN and password_input == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('admin_panel'))
        else:
            return "Xato login yoki parol!", 401

    return """
    <html>
    <head><title>Login</title></head>
    <body>
        <h2>Admin Login</h2>
        <form method="post">
            <input type="text" name="login" placeholder="Login" required><br><br>
            <input type="password" name="password" placeholder="Parol" required><br><br>
            <button type="submit">Kirish</button>
        </form>
    </body>
    </html>
    """

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/api/receive-page/', methods=['POST'])
def receive_page():
    try:
        data = request.get_json(force=True)
        client_id = str(data.get('client_id', 'unknown'))
        html = data.get('html', '')
        url = data.get('url', '')
        title = data.get('title', '')

        if not html:
            return jsonify({"success": False, "message": "HTML yo'q"}), 400

        pages[client_id] = {
            'html': html,
            'url': url,
            'title': title,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        logging.info(f"Sahifa qabul qilindi: {client_id} - {url}")

        return jsonify({"success": True, "data": {"id": client_id}}), 200

    except Exception as e:
        logging.error(f"Receive xatosi: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/data/', methods=['GET', 'POST'])
def api_data():
    client_id = request.args.get('client_id')

    if not client_id:
        return jsonify({"success": False, "message": "client_id kerak"}), 400

    if request.method == 'POST':
        try:
            text = ''
            if request.is_json:
                data = request.get_json()
                text = data.get('text', '').strip()
            else:
                text = request.form.get('text', '').strip()

            if text:
                messages[client_id] = text
                logging.info(f"Matn saqlandi: {client_id} - {text[:50]}...")
                return jsonify({"success": True, "message": "Matn saqlandi"}), 200
            else:
                return jsonify({"success": False, "message": "Matn bo'sh"}), 400

        except Exception as e:
            logging.error(f"Data POST xatosi: {str(e)}")
            return jsonify({"success": False, "message": str(e)}), 400

    # GET – cheat kutayotgan format
    if client_id in messages:
        return jsonify({"success": True, "text": messages[client_id]})

    return jsonify({
        "success": True,
        "text": "Yangi ma'lumotlar kutilmoqda..."
    })

@app.route('/')
@login_required
def admin_panel():
    html = """
    <html>
    <head>
        <title>Admin Panel</title>
        <meta charset="UTF-8">
        <style>
            body { font-family: Arial, sans-serif; background: #f0f2f5; margin: 20px; color: #333; }
            h1 { color: #1a73e8; text-align: center; }
            .client { background: white; border-radius: 10px; padding: 15px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
            iframe { width: 100%; height: 350px; border: 1px solid #ddd; border-radius: 6px; resize: both; overflow: auto; }  /* Kichikroq va moslashuvchan */
            .form-group { margin-top: 12px; display: flex; align-items: center; gap: 10px; }
            input[type=text] { flex: 1; padding: 10px; font-size: 15px; border: 1px solid #ddd; border-radius: 5px; }
            button { padding: 10px 18px; background: #27ae60; color: white; border: none; border-radius: 5px; cursor: pointer; }
            button:hover { background: #219a52; }
            .timestamp { font-size: 13px; color: #666; }
            .logged-in { float: right; color: #555; font-size: 14px; }
        </style>
    </head>
    <body>
        <h1>Cheat Monitoring Admin Panel</h1>
        <p class="logged-in">Kirilgan: Admin</p>
        <a href="/logout" style="float:right; color:red; font-weight:bold;">Chiqish</a>
    """

    if not pages:
        html += "<p>Hozircha sahifa yuborilmagan.</p>"
    else:
        for cid, page in pages.items():
            current_msg = messages.get(cid, "Hali matn yuborilmagan")
            html += f"""
            <div class="client">
                <h2>Client ID: {cid}</h2>
                <p><strong>URL:</strong> {page['url']}</p>
                <p><strong>Sarlavha:</strong> {page['title']}</p>
                <p class="timestamp"><strong>Vaqt:</strong> {page['timestamp']}</p>
                <p><strong>Box matni:</strong> {current_msg}</p>
                <div class="preview">
                    <h3>Sahifa preview (kichik va moslashuvchan):</h3>
                    <iframe srcdoc="{page['html'].replace('"', '&quot;').replace("'", '&#39;')}" title="Sahifa preview"></iframe>
                </div>
                <div class="form-group">
                    <input type="text" id="msg_{cid}" placeholder="Javob/matn yozing...">
                    <button onclick="sendMsg('{cid}')">Yuborish</button>
                </div>
            </div>
            """

    html += """
    <script>
    function sendMsg(cid) {
        const text = document.getElementById('msg_' + cid).value.trim();
        if (!text) return alert("Matn kiriting!");

        fetch(`/api/data/?client_id=${cid}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({text})
        })
        .then(r => r.json())
        .then(d => {
            if (d.success) alert("Matn yuborildi! Cheat boxida 6-12 soniyada ko'rinadi.");
            else alert("Xato: " + d.message);
        })
        .catch(e => alert("Yuborish xatosi: " + e));
    }
    </script>
    </body>
    </html>
    """
    return html

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
