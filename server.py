from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import logging  # Log qilish uchun

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})  # Barcha originlarga ruxsat (cheat kod uchun)

# Log sozlamalari (optimal ish uchun)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Saqlash (in-memory, real serverda database ishlatish mumkin)
pages = {}       # client_id → sahifa ma'lumotlari (asosan HTML)
messages = {}    # client_id → matn (javoblar)

@app.route('/api/receive-page/', methods=['POST'])
def receive_page():
    try:
        data = request.get_json(force=True)  # Cheat koddan JSON yoki encoded kelganda ham o'qiydi
        client_id = str(data.get('client_id', 'unknown'))
        html = data.get('html', '')
        url = data.get('url', '')
        title = data.get('title', '')

        if not html:
            logging.warning("HTML bo'sh keldi, client_id: " + client_id)
            return jsonify({"success": False, "message": "HTML kerak"}), 400

        pages[client_id] = {
            'html': html,  # Asosan HTML saqlaymiz (optimal hajm uchun)
            'url': url,
            'title': title,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        logging.info(f"Sahifa qabul qilindi, client_id: {client_id}, URL: {url}")

        return jsonify({
            "success": True,
            "data": {"id": client_id}
        }), 200

    except Exception as e:
        logging.error(f"Xato receive_page'da: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/data/', methods=['GET', 'POST'])
def api_data():
    client_id = request.args.get('client_id')

    if not client_id:
        logging.warning("client_id bo'sh keldi")
        return jsonify({"success": False, "message": "client_id kerak"}), 400

    if request.method == 'POST':
        try:
            text = ''
            if request.is_json:
                data = request.get_json()
                text = data.get('text', '').strip()
            else:
                text = request.form.get('text', '').strip()

            if not text:
                logging.warning("Matn bo'sh keldi, client_id: " + client_id)
                return jsonify({"success": False, "message": "Matn kerak"}), 400

            messages[client_id] = text
            logging.info(f"Matn saqlandi, client_id: {client_id}, matn: {text[:50]}...")

            return jsonify({"success": True, "message": "Matn saqlandi"}), 200

        except Exception as e:
            logging.error(f"Xato api_data POST'da: {str(e)}")
            return jsonify({"success": False, "message": str(e)}), 400

    # GET: Matn qaytarish
    if client_id in messages:
        return jsonify({"success": True, "text": messages[client_id]})

    # Default xabar
    return jsonify({
        "success": True,
        "text": "Yangi ma'lumot kutilmoqda..."
    })

@app.route('/')
def admin_panel():
    html = """
    <html>
    <head>
        <title>Admin Panel - Cheat Monitoring</title>
        <meta charset="UTF-8">
        <style>
            body { font-family: Arial, sans-serif; background: #f0f2f5; margin: 20px; color: #333; }
            h1 { color: #1a73e8; text-align: center; }
            .client { background: white; border-radius: 10px; padding: 20px; margin-bottom: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
            iframe { width: 100%; height: 700px; border: 1px solid #ddd; border-radius: 8px; resize: both; overflow: auto; }  # Yangi: iframe resize mumkin
            .form-group { margin-top: 15px; display: flex; align-items: center; }
            input[type=text] { flex: 1; padding: 12px; font-size: 16px; border: 1px solid #ddd; border-radius: 5px; }
            button { padding: 12px 20px; background: #27ae60; color: white; border: none; border-radius: 5px; cursor: pointer; margin-left: 10px; }
            button:hover { background: #219a52; }
            .preview { margin-top: 20px; }
            .timestamp { font-size: 14px; color: #666; }
        </style>
    </head>
    <body>
        <h1>Cheat Monitoring Admin Panel</h1>
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
                <p class="timestamp"><strong>Yuborilgan vaqt:</strong> {page['timestamp']}</p>
                <p><strong>Hozirgi box matni:</strong> {current_msg}</p>
                <div class="preview">
                    <h3>Sahifa preview (iframe):</h3>
                    <iframe srcdoc="{page['html'].replace('"', '&quot;').replace("'", '&#39;')}" title="Sahifa preview"></iframe>
                </div>
                <div class="form-group">
                    <input type="text" id="msg_{cid}" placeholder="Client {cid} ga matn yuboring (javoblar, buyruq)...">
                    <button onclick="sendMsg('{cid}')">Yuborish</button>
                </div>
            </div>
            """

    html += """
    <script>
    function sendMsg(cid) {
        const text = document.getElementById('msg_' + cid).value.trim();
        if (!text) {
            alert("Matn kiriting!");
            return;
        }

        fetch(`/api/data/?client_id=${cid}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({text: text})
        })
        .then(r => r.json())
        .then(d => {
            if (d.success) {
                alert("Matn yuborildi! Cheat boxida tez orada ko'rinadi.");
                document.getElementById('msg_' + cid).value = '';
            } else {
                alert("Xato: " + d.message);
            }
        })
        .catch(e => alert("Yuborish xatosi: " + e));
    }
    </script>
    </body>
    </html>
    """
    return html

if __name__ == '__main__':
    print("Server ishga tushdi: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
