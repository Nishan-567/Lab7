import socket
import RPi.GPIO as GPIO

# --- GPIO setup ---
GPIO.setmode(GPIO.BCM)
led_pins = [2, 3, 4]
pwm_leds = []

for pin in led_pins:
    GPIO.setup(pin, GPIO.OUT)
    pwm = GPIO.PWM(pin, 1000)  # 1 kHz frequency
    pwm.start(0)
    pwm_leds.append(pwm)

# --- LED state storage ---
led_brightness = [0, 0, 0]  # Percent brightness for each LED

# --- HTML Template ---
def generate_html(selected_led=0):
    html = """\
HTTP/1.1 200 OK
Content-Type: text/html

<!DOCTYPE html>
<html>
<head>
    <title>LED Brightness Control</title>
    <style>
        body { font-family: Arial; margin: 40px; }
        form { border: 1px solid #888; padding: 10px; width: 250px; }
        label { display: block; margin-top: 10px; }
        input[type=submit] { margin-top: 10px; }
    </style>
</head>
<body>
    <form method="POST" action="/">
        <label><b>Brightness level:</b></label>
        <input type="range" name="brightness" min="0" max="100" value="{brightness}">
        <br>

        <label><b>Select LED:</b></label>
    """.format(brightness=led_brightness[selected_led])

    for i in range(3):
        checked = "checked" if i == selected_led else ""
        html += f'<input type="radio" name="led" value="{i}" {checked}> LED {i+1} ({led_brightness[i]}%)<br>'

    html += """\
        <input type="submit" value="Change Brightness">
    </form>
</body>
</html>
"""
    return html


# --- Helper to parse POST data ---
def parse_post_data(data):
    try:
        body = data.split("\r\n\r\n", 1)[1]
        params = dict(param.split("=") for param in body.split("&"))
        return params
    except Exception:
        return {}


# --- Main TCP/IP server ---
def run_server(host="0.0.0.0", port=8080):
    print(f"Starting server on {host}:{port}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port))
        s.listen(1)
        print("Server ready, connect via browser (http://<Pi_IP>:8080)")

        while True:
            conn, addr = s.accept()
            with conn:
                data = conn.recv(1024).decode("utf-8", errors="ignore")
                if not data:
                    continue

                # Handle POST request
                if data.startswith("POST"):
                    params = parse_post_data(data)
                    try:
                        led_index = int(params.get("led", "0"))
                        brightness = int(params.get("brightness", "0"))
                        brightness = max(0, min(brightness, 100))

                        led_brightness[led_index] = brightness
                        pwm_leds[led_index].ChangeDutyCycle(brightness)

                        print(f"LED {led_index+1} set to {brightness}% brightness")
                    except Exception as e:
                        print("Error:", e)
                    
                    # Always return updated HTML page
                    response = generate_html(selected_led=led_index)
                    conn.sendall(response.encode("utf-8"))

                else:  # Handle GET request
                    response = generate_html(selected_led=0)
                    conn.sendall(response.encode("utf-8"))


# --- Cleanup on exit ---
if __name__ == "__main__":
    try:
        run_server()
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        for pwm in pwm_leds:
            pwm.stop()
        GPIO.cleanup()
