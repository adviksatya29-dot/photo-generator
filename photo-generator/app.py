from flask import Flask, render_template, request, redirect, url_for, session
import os
import cv2
import numpy as np
from rembg import remove

app = Flask(__name__)
app.secret_key = "secret123"

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "static"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


# ---------------- LOGIN ----------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == "Advik" and password == "321":
            session["user"] = username
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", error="Wrong username or password")

    return render_template("login.html")


# ---------------- DASHBOARD ----------------
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        file = request.files.get("photo")
        if file:
            path = os.path.join(UPLOAD_FOLDER, "input.jpg")
            file.save(path)
            return render_template("preview.html", image="input.jpg")

    return render_template("dashboard.html")


# ---------------- GENERATE ----------------
@app.route("/generate", methods=["POST"])
def generate():
    if "user" not in session:
        return redirect(url_for("login"))

    try:
        brightness = request.form.get("brightness", "medium")
        copies = int(request.form.get("copies", 6))

        input_path = os.path.join(UPLOAD_FOLDER, "input.jpg")

        # Remove background
        with open(input_path, "rb") as f:
            output = remove(f.read())

        no_bg_path = os.path.join(UPLOAD_FOLDER, "no_bg.png")
        with open(no_bg_path, "wb") as f:
            f.write(output)

        img = cv2.imread(no_bg_path, cv2.IMREAD_UNCHANGED)

        if img is None:
            return "Error loading image"

        # Ensure 4 channels
        if img.shape[2] == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)

        b, g, r, a = cv2.split(img)

        # Blue background
        bg = np.full((img.shape[0], img.shape[1], 3), (255, 0, 0), dtype=np.uint8)

        alpha = a / 255.0
        alpha = np.stack([alpha]*3, axis=-1)

        fg = cv2.merge((b, g, r))
        result = (fg * alpha + bg * (1 - alpha)).astype(np.uint8)

        # Brightness
        if brightness == "low":
            beta = -20
        elif brightness == "high":
            beta = 30
        else:
            beta = 0

        result = cv2.convertScaleAbs(result, alpha=1, beta=beta)

        # Passport size (simple correct)
        final = cv2.resize(result, (413, 531))

        # Border
        cv2.rectangle(final, (0, 0), (412, 530), (0, 0, 0), 2)

        # Create sheet (2 rows x 3 cols)
        rows, cols = 2, 3
        h, w = final.shape[:2]

        sheet = np.ones((rows*h, cols*w, 3), dtype=np.uint8) * 255

        count = 0
        for i in range(rows):
            for j in range(cols):
                if count < copies:
                    sheet[i*h:(i+1)*h, j*w:(j+1)*w] = final
                    count += 1

        output_path = os.path.join(OUTPUT_FOLDER, "output.jpg")
        cv2.imwrite(output_path, sheet)

        return render_template("result.html", image="output.jpg")

    except Exception as e:
        return f"Error: {str(e)}"


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0",port=10000)
