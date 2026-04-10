# ruff: noqa no lint...

import random
from shutil import copy
import stat
import time
from flask import Flask, Response, jsonify, request

app = Flask(__name__)

# --- Market status state: "open" | "closed" | "holiday" ---
market_state = "open"
state = {"market": "open", "auth_error": False}
MARKET_RESPONSES = {
    "open": {
        "exchange": "US",
        "holiday": None,
        "isOpen": True,
        "session": "regular",
        "timezone": "America/New_York",
    },
    "closed": {
        "exchange": "US",
        "holiday": None,
        "isOpen": False,
        "session": "pre-market",
        "timezone": "America/New_York",
    },
    "holiday": {
        "exchange": "US",
        "holiday": "Thanksgiving Day",
        "isOpen": False,
        "session": "holiday",
        "timezone": "America/New_York",
    },
}
BASE_GHI = 5077.212
VARIATION_PCT = 0.005  # ±.5%


def randomized_ghi(base: float, pct: float) -> float:
    """
    Return a value randomly varied around base by ±pct.
    Example: base=5077, pct=0.05 → range ≈ 4823–5331
    """
    delta = base * pct
    value = random.uniform(base - delta, base + delta)
    return round(value, 3)


SOLAR_RESPONSE = {
    "lat": 51.4395,
    "lon": 0.0998,
    "date": "2023-04-08",
    "interval": "1d",
    "tz": "+01:00",
    "sunrise": "2023-04-08T06:19:47",
    "sunset": "2023-04-08T19:44:18",
    "intervals": [
        {
            "start": "00:00",
            "end": "23:59",
            "avg_irradiance": {
                "clear_sky": {"ghi": 238.342, "dni": 378.646, "dhi": 46.256},
                "cloudy_sky": {"ghi": 211.551, "dni": 274.013, "dhi": 76.882},
            },
            "max_irradiance": {
                "clear_sky": {"ghi": 732.078, "dni": 875.758, "dhi": 111.881},
                "cloudy_sky": {"ghi": 687.804, "dni": 784.251, "dhi": 341.816},
            },
            "irradiation": {
                "clear_sky": {"ghi": 5720.2, "dni": 9087.497, "dhi": 1110.14},
                "cloudy_sky": {"ghi": BASE_GHI, "dni": 6576.317, "dhi": 1845.173},
            },
        }
    ],
}


@app.route("/api/v1/quote")
def quote():
    if state["auth_error"]:
        return jsonify({"error": "Invalid API key."}), 401
    symbol = request.args.get("symbol", "SPY")

    # Base data — randomise the current price (c) around a realistic range
    base_price = 662.29
    c = round(random.uniform(base_price * 0.97, base_price * 1.03), 2)
    pc = 666.06
    d = round(c - pc, 2)
    dp = round((d / pc) * 100, 3)

    data = {
        "c": c,
        "d": d,
        "dp": dp,
        "h": 672.335,
        "l": 661.36,
        "o": 669.27,
        "pc": pc,
        "t": int(time.time()),
    }

    return jsonify(data)


@app.route("/api/v1/status/open", methods=["GET", "POST"])
def status_open() -> Response:
    state["market"] = "open"
    return jsonify({"state": state["market"], "message": "Market set to OPEN"})


@app.route("/api/v1/status/close", methods=["GET", "POST"])
def status_close() -> Response:
    state["market"] = "closed"
    return jsonify({"state": state["market"], "message": "Market set to CLOSED"})


@app.route("/api/v1/status/holiday", methods=["GET", "POST"])
def status_holiday() -> Response:
    state["market"] = "holiday"
    return jsonify({"state": state["market"], "message": "Market set to HOLIDAY"})


@app.route("/api/v1/status/auth", methods=["GET", "POST"])
def status_auth() -> Response:
    state["auth_error"] = not state["auth_error"]
    flag = state["auth_error"]
    return jsonify(
        {
            "auth_error": flag,
            "message": f"Auth error {'ENABLED' if flag else 'DISABLED'}",
        }
    )


@app.route("/api/v1/stock/market-status")
def status():
    if state["auth_error"]:
        return jsonify({"error": "Invalid API key."}), 401
    response = MARKET_RESPONSES.get(state["market"], MARKET_RESPONSES["open"])
    return jsonify({**response, "t": int(time.time())})


@app.get("/energy")
def energy():
    """
    Returns static dummy irradiance data.

    Query parameters are accepted but ignored,
    allowing drop-in replacement for the real API.
    """
    # Optional: echo query params if useful for debugging
    lat = request.args.get("lat")
    lon = request.args.get("lon")
    date = request.args.get("date")

    response = SOLAR_RESPONSE.copy()

    # Randomize only this field
    response["intervals"][0]["irradiation"]["cloudy_sky"]["ghi"] = randomized_ghi(BASE_GHI, VARIATION_PCT)
    if lat:
        response["lat"] = float(lat)
    if lon:
        response["lon"] = float(lon)
    if date:
        response["date"] = date

    return jsonify(response)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
