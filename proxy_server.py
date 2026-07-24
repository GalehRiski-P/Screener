"""
Proxy Server - Broker Screener
Menjembatani HTML screener <-> RapidAPI (supaya tidak kena CORS block)

CARA PAKAI:
1. Install dependency:
   pip install flask flask-cors requests --break-system-packages

2. Set API key sebagai environment variable:
   export RAPIDAPI_KEY="api_key_anda"

3. Jalankan server:
   python proxy_server.py

4. Buka broker_screener.html di browser SEPERTI BIASA.
   HTML akan otomatis memanggil proxy ini (http://localhost:5000) alih-alih
   langsung ke RapidAPI, sehingga tidak kena CORS.
"""

import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)  # izinkan diakses dari file HTML lokal

API_HOST = "indonesia-stock-exchange-idx.p.rapidapi.com"
BASE_URL = f"https://{API_HOST}/api/market-detector/top-broker"


@app.route("/api/top-broker", methods=["GET"])
def top_broker():
    api_key = request.headers.get("x-rapidapi-key") or os.environ.get("RAPIDAPI_KEY")

    if not api_key:
        return jsonify({"error": "RAPIDAPI_KEY belum diset (env var atau header)."}), 400

    params = {
        "marketType": request.args.get("marketType", "MARKET_TYPE_ALL"),
        "period": request.args.get("period", "TB_PERIOD_LAST_1_DAY"),
        "order": request.args.get("order", "ORDER_BY_DESC"),
        "sort": request.args.get("sort", "TB_SORT_BY_TOTAL_VALUE"),
    }

    headers = {
        "Content-Type": "application/json",
        "x-rapidapi-host": API_HOST,
        "x-rapidapi-key": api_key,
    }

    try:
        resp = requests.get(BASE_URL, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        return jsonify(resp.json())
    except requests.exceptions.HTTPError as e:
        return jsonify({"error": f"API error: {e}", "detail": resp.text}), resp.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Connection error: {e}"}), 502


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    print("Proxy server jalan di http://localhost:5000")
    print("Buka broker_screener.html di browser Anda sekarang.")
    app.run(host="0.0.0.0", port=5000, debug=True)
