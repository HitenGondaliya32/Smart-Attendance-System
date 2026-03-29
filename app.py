from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from deepface import DeepFace
import csv
import os
import base64
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret123"

@app.route("/")
def home():
    return render_template("index.html")


# REGISTER
@app.route("/register")
def register_page():
    return render_template("register.html")

@app.route("/register_user", methods=["POST"])
def register_user():
    name = request.form["name"]
    img_data = request.form["image"]

    img_data = img_data.split(",")[1]

    users = []
    if os.path.exists("users.csv"):
        with open("users.csv", "r") as f:
            for row in csv.reader(f):
                if row:
                    users.append(row[0])

    if name in users:
        flash("❌ User already registered")
        return redirect(url_for("register_page"))

    path = f"dataset/{name}.jpg"
    with open(path, "wb") as f:
        f.write(base64.b64decode(img_data))

    with open("users.csv", "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([name])

    flash("✅ Registered Successfully")
    return redirect(url_for("login_page"))


# LOGIN

@app.route("/login")
def login_page():
    session.pop("admin", None)   
    return render_template("login.html")


@app.route("/verify", methods=["POST"])
def verify():
    session.pop("admin", None)   

    img_data = request.form["image"]
    img_data = img_data.split(",")[1]

    with open("captured.jpg", "wb") as f:
        f.write(base64.b64decode(img_data))

    users = []
    with open("users.csv", "r") as f:
        for row in csv.reader(f):
            if row:
                users.append(row[0])

    best_match = None
    best_distance = 999

    for user in users:
        try:
            result = DeepFace.verify(
                "captured.jpg",
                f"dataset/{user}.jpg",
                enforce_detection=False
            )

            if result["distance"] < best_distance:
                best_distance = result["distance"]
                best_match = user

        except:
            continue

    if best_match and best_distance < 0.35:
        user = best_match

        now = datetime.now()
        date = now.strftime("%Y-%m-%d")
        time = now.strftime("%H:%M:%S")

        filename = f"attendance_{date}.csv"

        already = False
        if os.path.exists(filename):
            with open(filename, "r") as f:
                for row in csv.reader(f):
                    if row and row[0] == user:
                        already = True

        if not already:
            with open(filename, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([user, date, time])

        flash(f"✅ Welcome {user}")
        return redirect(url_for("welcome", user=user))

    flash("❌ Face Not Recognized")
    return redirect(url_for("login_page"))


@app.route("/welcome/<user>")
def welcome(user):
    return render_template("welcome.html", user=user)


# DASHBOARD
@app.route("/dashboard")
def dashboard():
    data = []
    present = []

    date = request.args.get("date")
    today = datetime.now().strftime("%Y-%m-%d")

    filename = f"attendance_{date}.csv" if date else f"attendance_{today}.csv"

    if os.path.exists(filename):
        with open(filename, "r") as f:
            for i, row in enumerate(csv.reader(f), start=1):
                if len(row) >= 3:
                    data.append([i] + row)
                    present.append(row[0])

    users = []
    with open("users.csv", "r") as f:
        for row in csv.reader(f):
            if row:
                users.append(row[0])

    absent = list(set(users) - set(present))

    return render_template(
        "dashboard.html",
        data=data,
        absent=absent,
        total=len(users),
        present_count=len(present),
        is_admin=session.get("admin")
    )

#DOWNLOAD
@app.route("/download")
def download():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    today = datetime.now().strftime("%Y-%m-%d")
    return send_file(f"attendance_{today}.csv", as_attachment=True)


# ADMIN LOGIN
@app.route("/admin-login")
def admin_login():
    return render_template("admin_login.html")

@app.route("/admin-auth", methods=["POST"])
def admin_auth():
    if request.form["password"] == "admin123":
        session["admin"] = True
        return redirect(url_for("dashboard"))  
    else:
        flash("❌ Wrong Password")
        return redirect(url_for("admin_login"))


# ADMIN PANEL

@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    users = []
    with open("users.csv", "r") as f:
        for row in csv.reader(f):
            if row:
                users.append(row[0])

    return render_template("admin.html", users=users)
#delete user
@app.route("/delete_user/<name>")
def delete_user(name):
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    users = []
    with open("users.csv", "r") as f:
        for row in csv.reader(f):
            if row and row[0] != name:
                users.append(row)

    with open("users.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(users)

    img = f"dataset/{name}.jpg"
    if os.path.exists(img):
        os.remove(img)

    flash("🗑 User Deleted")
    return redirect(url_for("admin"))

#logout
@app.route("/admin-logout")
def admin_logout():
    session.pop("admin", None)
    flash("🔒 Logged Out")
    return redirect(url_for("admin_login"))


port = int(os.environ.get("PORT", 8080))
app.run(host="0.0.0.0", port=port)