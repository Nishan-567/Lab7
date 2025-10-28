import socket
import RPi.GPIO as GPIO

# ---------------- GPIO Setup ----------------
GPIO.setmode(GPIO.BCM)
led_pins = {'1': 2, '2': 3, '3': 4}
led_values = {'1': 0, '2': 0, '3': 0}

pwm_leds = {}
for key, pin in led_pins.items():
    GPIO.setup(pin, GPIO.OUT)
    pwm = GPIO.PWM(pin, 1000)  # 1kHz PWM
    pwm.start(0)
    pwm_leds[key] = pwm

# ---------------- HTML + JavaScript ----------------
def html_page():
    return f"""HTTP/1.1 200 OK
Content-Type: text/html

<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>LED Brightness Control</title>
<style>
    body {{
        font-family: Arial, sans-serif;
        margin: 40px;
    }}
    .control-box {{
        border: 2px solid black;
        padding: 15px;
        width: 260px;
        border-radius: 8px;
    }}
    .led-control {{
        display: flex;
        align-items: center;
        margin-bottom: 12px;
    }}
    .led-label {{
        width: 50px;
        font-weight: bold;
    }}
    input[type="range"] {{
        flex-grow: 1;
        margin: 0 10px;
    }}
    .value-display {{
        width: 30px;
        text-align: right;
        font-weight: bold;
    }}
</style>
</head>
<body>
    <div class="control-box">
        <div class="led-control">
            <span class="led-label">LED1</span>
            <input type="range" id="led1" min="0" max="100" value="{led_values['1']}" oninput="updateLED(1)">
            <span id="val1" class="value-display">{led_values['1']}</span>
        </div>
        <div class="led-control">
            <span class="led-label">LED2</span>
            <input type="range" id="led2" min="0" max="100" value="{led_values['2']}" oninput="updateLED(2)">
            <span id="val2" class="value-display">{led_values['2']}</span>
        </div>
        <div class="led-control">
            <span class="led-label">LED3</span>
            <input type="range" id="led3" min="0" max="100" value="{led_values['3']}" oninput="updateLED(3)">
            <span id="val3" class="value-display">{led_values['3']}</span>
        </div>
    </div>

<script>
function updateLED(ledNum) {{
    let slider = document.getElementById("led" + ledNum);
    let valueDisplay = document.getElementById("val" + ledNum);
    let brightness = slider.value;
    valueDisplay.textContent = brightness;

    fetch("/", {{
        method: "POST",
        headers: {{
            "Content-Type": "application/x-www-form-urlencoded"
        }},
        body: "led=" + ledNum + "&brightness=" + brightness
    }});
}}
</script>
</body>
</html>"""

# ---------------- Helper: Parse POST Data ----------------
def parse_post_data(request):
    try:
        body = request.split("\r\n\r\n", 1)[1]
        params = dict(param.split("=") for param in body.split("&"))
        return params
    except Exception:
        return {}

# ---------------- TCP/IP Server ----------------
def run_server(host="", port=8080):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((host, port))
    s.listen(1)
    print("Visit http://172.20.10.8:8080 in your browser.")

    while True:
        conn, addr = s.accept()
        with conn:
            data = conn.recv(2048).decode("utf-8", errors="ignore")
            if not data:
                continue

            # Handle POST request (from JS fetch)
            if data.startswith("POST"):
                params = parse_post_data(data)
                led = params.get("led")
                brightness = params.get("brightness")

                if led in led_values and brightness is not None:
                    try:
                        brightness = int(brightness)
                        brightness = max(0, min(100, brightness))
                        led_values[led] = brightness
                        pwm_leds[led].ChangeDutyCycle(brightness)
                        print(f"LED {led} → {brightness}%")
                    except Exception as e:
                        print("POST parse error:", e)

                # Respond minimally to JS (no page reload)
                conn.sendall(b"HTTP/1.1 204 No Content\r\n\r\n")

            else:  # Handle initial GET request
                response = html_page()
                conn.sendall(response.encode("utf-8"))

# ---------------- Main ----------------
if __name__ == "__main__":
    try:
        run_server()
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        for pwm in pwm_leds.values():
            pwm.stop()
        GPIO.cleanup()
