"""
Broker Screener - IDX Top Broker Summary (Full Python / CLI)
Langsung panggil RapidAPI, tanpa HTML/proxy.

CARA PAKAI:
1. Install dependency:
   pip install requests --break-system-packages

2. Set API key (pilih salah satu cara):
   a) Environment variable (disarankan):
      export RAPIDAPI_KEY="api_key_anda"
   b) Atau isi langsung di variabel API_KEY di bawah (kurang aman kalau file
      ini di-share ke orang lain / diupload ke GitHub publik).

3. Jalankan:
   python broker_screener.py
   python broker_screener.py --min-value 1000000000 --top 10
   python broker_screener.py --period week --sort volume
"""

import os
import sys
import csv
import argparse
import requests
from datetime import datetime

# ============================================================
# KONFIGURASI API
# ============================================================

API_HOST = "indonesia-stock-exchange-idx.p.rapidapi.com"
BASE_URL = f"https://{API_HOST}/api/market-detector/top-broker"

# Opsi B: isi langsung di sini kalau tidak mau pakai environment variable
# API_KEY = "isi_key_anda_di_sini"
API_KEY = os.environ.get("RAPIDAPI_KEY")

# Mapping argumen CLI yang lebih manusiawi -> nilai enum API
PERIOD_MAP = {
    "day": "TB_PERIOD_LAST_1_DAY",
    "week": "TB_PERIOD_LAST_1_WEEK",
    "month": "TB_PERIOD_LAST_1_MONTH",
}
SORT_MAP = {
    "value": "TB_SORT_BY_TOTAL_VALUE",
    "volume": "TB_SORT_BY_TOTAL_VOLUME",
    "frequency": "TB_SORT_BY_TOTAL_FREQUENCY",
}
ORDER_MAP = {
    "desc": "ORDER_BY_DESC",
    "asc": "ORDER_BY_ASC",
}
MARKET_MAP = {
    "all": "MARKET_TYPE_ALL",
    "reguler": "MARKET_TYPE_RG",
    "tunai": "MARKET_TYPE_TN",
    "negosiasi": "MARKET_TYPE_NG",
}


def parse_args():
    p = argparse.ArgumentParser(description="Broker Screener IDX")
    p.add_argument("--market", choices=MARKET_MAP.keys(), default="all")
    p.add_argument("--period", choices=PERIOD_MAP.keys(), default="day")
    p.add_argument("--sort", choices=SORT_MAP.keys(), default="value")
    p.add_argument("--order", choices=ORDER_MAP.keys(), default="desc")
    p.add_argument("--min-value", type=float, default=0,
                   help="Filter: total value transaksi minimum (rupiah)")
    p.add_argument("--top", type=int, default=20, help="Jumlah baris teratas ditampilkan")
    p.add_argument("--export-csv", type=str, default=None,
                   help="Simpan hasil ke file CSV, contoh: --export-csv hasil.csv")
    p.add_argument("--show-raw", action="store_true",
                   help="Tampilkan JSON mentah dari API (untuk debug struktur field)")
    return p.parse_args()


def fetch_top_broker(market, period, sort, order):
    if not API_KEY:
        print("ERROR: RAPIDAPI_KEY belum diset.")
        print('Jalankan: export RAPIDAPI_KEY="api_key_anda"')
        print("atau isi langsung variabel API_KEY di dalam script ini.")
        sys.exit(1)

    headers = {
        "Content-Type": "application/json",
        "x-rapidapi-host": API_HOST,
        "x-rapidapi-key": API_KEY,
    }
    params = {
        "marketType": MARKET_MAP[market],
        "period": PERIOD_MAP[period],
        "order": ORDER_MAP[order],
        "sort": SORT_MAP[sort],
    }

    resp = requests.get(BASE_URL, headers=headers, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def extract_rows(data):
    """Cari list data di dalam response, format API bisa beda-beda strukturnya."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("data", "results", "items"):
            if key in data and isinstance(data[key], list):
                return data[key]
        # fallback: ambil list pertama yang ditemukan di level atas
        for v in data.values():
            if isinstance(v, list):
                return v
    return []


def get_field(row, candidates):
    """Ambil nilai dari beberapa kemungkinan nama field (karena nama field
    di response API bisa snake_case atau camelCase)."""
    for c in candidates:
        if c in row:
            return row[c]
    return None


def screen_rows(rows, min_value, top_n):
    filtered = []
    for row in rows:
        total_value = get_field(row, ["total_value", "totalValue", "value"]) or 0
        if total_value >= min_value:
            filtered.append(row)
    return filtered[:top_n]


def print_table(rows):
    if not rows:
        print("\nTidak ada data yang lolos kriteria screening.\n")
        return

    keys = list(rows[0].keys())
    widths = {k: max(len(str(k)), *(len(str(r.get(k, ""))) for r in rows)) for k in keys}
    widths = {k: min(w, 22) for k, w in widths.items()}  # batasi lebar kolom

    def fmt_row(values):
        return " | ".join(str(v)[:widths[k]].ljust(widths[k]) for k, v in zip(keys, values))

    print(f"\n{'='*80}")
    print(f"BROKER SCREENER REPORT — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}")
    print(fmt_row(keys))
    print("-" * 80)
    for row in rows:
        print(fmt_row([row.get(k, "") for k in keys]))
    print(f"{'='*80}")
    print(f"Total: {len(rows)} baris ditampilkan\n")


def export_csv(rows, filename):
    if not rows:
        print("Tidak ada data untuk diexport.")
        return
    keys = list(rows[0].keys())
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Hasil disimpan ke: {filename}")


def main():
    args = parse_args()

    print("Mengambil data dari RapidAPI...")
    try:
        raw = fetch_top_broker(args.market, args.period, args.sort, args.order)
    except requests.exceptions.HTTPError as e:
        print(f"Error dari API: {e}")
        print("Cek apakah API key masih valid/aktif di dashboard RapidAPI.")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"Error koneksi: {e}")
        sys.exit(1)

    if args.show_raw:
        import json
        print(json.dumps(raw, indent=2, ensure_ascii=False))
        return

    rows = extract_rows(raw)
    if not rows:
        print("Data kosong atau struktur response tidak dikenali.")
        print("Jalankan dengan --show-raw untuk melihat bentuk JSON aslinya.")
        return

    results = screen_rows(rows, args.min_value, args.top)
    print_table(results)

    if args.export_csv:
        export_csv(results, args.export_csv)


if __name__ == "__main__":
    main()
