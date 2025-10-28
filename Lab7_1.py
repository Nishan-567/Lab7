import socket
import RPi.GPIO as GPIO

# ---------------- GPIO Setup ----------------
GPIO.setmode(GPIO.BCM)
led_pins = { '1': 2, '2': 3, '3': 4 }
led_values = { '1': 0, '2': 0, '3': 0 }  # Brightness levels for each LED

pwm_leds = {}
for key, pin in led_pins.items():
    GPIO.setup(pin, GPIO.OUT)
    pwm = GPIO.PWM(pin, 1000)  # 1 kHz PWM frequency
    pwm.start(0)
    pwm_leds[key] = pwm

# ---------------- HTML Page ----------------
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
        border: 3px solid black;
        width: 230px;
        padding: 10px;
        font-family: Arial, sans-serif;
    }}
    label {{
        display: block;
        margin-top: 8px;
    }}
    input[type="range"] {{
        width: 100%;
    }}
    input[type="submit"] {{
        margin-top: 10px;
        width: 100%;
    }}
</style>
</head>
<body>
    <form method="POST">
        <label for="brightness">Brightness level:</label>
        <input type="range" id="brightness" name="brightness" min="0" max="100" value="0">

        <label style="margin-top: 10px;">Select LED:</label>
        <input type="radio" id="led1" name="led" value="1" checked>
        <label for="led1">LED 1 ({led_values['1']}%)</label><br>

        <input type="radio" id="led2" name="led" value="2">
        <label for="led2">LED 2 ({led_values['2']}%)</label><br>

        <input type="radio" id="led3" name="led" value="3">
        <label for="led3">LED 3 ({led_values['3']}%)</label><br>

        <input type="submit" value="Change Brightness">
    </form>
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
def run_server(host="0.0.0.0", port=8080):
    print(f"Starting server on {host}:{port}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port))
        s.listen(1)
        print("Server ready. Visit http://<Pi_IP>:8080 in your browser.")

        while True:
            conn, addr = s.accept()
            with conn:
                data = conn.recv(1024).decode("utf-8", errors="ignore")
                if not data:
                    continue

                if data.startswith("POST"):
                    params = parse_post_data(data)
                    led = params.get("led", "1")
                    brightness = params.get("brightness", "0")

                    try:
                        brightness = int(brightness)
                        brightness = max(0, min(100, brightness))
                        led_values[led] = brightness
                        pwm_leds[led].ChangeDutyCycle(brightness)
                        print(f"LED {led} set to {brightness}% brightness")
                    except Exception as e:
                        print("Error processing POST data:", e)

                # Always send updated HTML page
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
