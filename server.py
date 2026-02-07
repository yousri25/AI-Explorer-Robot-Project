from http.server import SimpleHTTPRequestHandler, HTTPServer
import os
from urllib.parse import parse_qs, unquote

PORT = 8080
BASE = os.path.dirname(os.path.abspath(__file__))

class RobotHandler(SimpleHTTPRequestHandler):

    def do_GET(self):
        if self.path == "/":
            self.send_login()
        elif self.path == "/missions":
            self.send_missions()
        elif self.path.startswith("/browse"):
            self.browse_folder()
        elif self.path == "/logout":
            self.redirect("/")
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == "/login":
            length = int(self.headers.get("Content-Length", 0))
            data = self.rfile.read(length).decode()
            fields = parse_qs(data)

            if fields.get("user", [""])[0] == "robotique" and fields.get("pass", [""])[0] == "admin":
                self.redirect("/missions")
            else:
                self.send_login("Invalid credentials")

    # ---------- UI ----------

    def send_login(self, msg=""):
        self.html("Robot Login", f"""
<div class="login-box">
    <img src="/logo.jpg" class="logo">
    <h2>Robot Control Center</h2>
    <form method="post" action="/login">
        <input name="user" placeholder="Username" required>
        <input name="pass" type="password" placeholder="Password" required>
        <button>Login</button>
        <p class="error">{msg}</p>
    </form>
</div>
""", login=True)

    def send_missions(self):
        missions = sorted([d for d in os.listdir(BASE) if d.startswith("mission_")])

        cards = ""
        for m in missions:
            cards += f"""
            <div class="mission-card" onclick="location.href='/browse?path={m}'">
                <h3>{m}</h3>
                <p>View mission data</p>
            </div>
            """

        self.html("Mission Dashboard", f"""
<header>
    <div class="header-left">
        <img src="/logo.jpg">
        <h1>AI Robot Missions</h1>
    </div>
    <a href="/logout" class="logout-btn">Logout</a>
</header>

<div class="grid">
    {cards if cards else "<p>No missions found.</p>"}
</div>
""")

    def browse_folder(self):
        qs = parse_qs(self.path.split("?",1)[1])
        rel = unquote(qs.get("path", [""])[0])
        path = os.path.join(BASE, rel)

        if not os.path.exists(path):
            self.redirect("/missions")
            return

        items = ""
        for name in sorted(os.listdir(path)):
            full = os.path.join(path, name)
            new = f"{rel}/{name}"

            if os.path.isdir(full):
                items += f"""
                <div class="file-card folder" onclick="location.href='/browse?path={new}'">
                    📁 {name}
                </div>
                """
            else:
                items += f"""
                <div class="file-card" onclick="window.open('/{new}')">
                    📄 {name}
                </div>
                """

        back = "/missions" if "/" not in rel else f"/browse?path={'/'.join(rel.split('/')[:-1])}"

        self.html("Browser", f"""
<header>
    <div class="header-left">
        <img src="/logo.jpg">
        <h1>{rel}</h1>
    </div>
    <a href="/logout" class="logout-btn">Logout</a>
</header>

<a class="back-btn" href="{back}">⬅ Back</a>

<div class="grid">
    {items}
</div>
""")

    # ---------- HTML FRAME ----------

    def html(self, title, body, login=False):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()

        self.wfile.write(f"""
<!DOCTYPE html>
<html>
<head>
<title>{title}</title>
<style>
body {{
    margin:0;
    background:#f4f7fb;
    font-family:Segoe UI, Arial;
}}

header {{
    display:flex;
    justify-content:space-between;
    align-items:center;
    background:white;
    padding:15px 30px;
    border-bottom:3px solid #1e90ff;
}}

.header-left {{
    display:flex;
    align-items:center;
}}

header img {{
    height:50px;
    margin-right:15px;
}}

h1,h2 {{
    color:#1e90ff;
}}

.grid {{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(250px,1fr));
    gap:20px;
    padding:30px;
}}

.mission-card, .file-card {{
    background:white;
    padding:20px;
    border-radius:12px;
    box-shadow:0 6px 15px rgba(0,0,0,.1);
    cursor:pointer;
    transition:.3s;
}}

.mission-card:hover, .file-card:hover {{
    transform:translateY(-5px);
    box-shadow:0 10px 25px rgba(0,0,0,.2);
}}

.folder {{
    border-left:5px solid #1e90ff;
}}

.back-btn {{
    display:inline-block;
    margin:20px 30px;
    padding:10px 20px;
    background:#1e90ff;
    color:white;
    border-radius:20px;
    text-decoration:none;
    transition:.3s;
}}

.back-btn:hover {{
    background:#0b5ed7;
    transform:translateX(-5px);
}}

.logout-btn {{
    background:#ff4d4d;
    color:white;
    padding:8px 16px;
    border-radius:20px;
    text-decoration:none;
    transition:.3s;
}}

.logout-btn:hover {{
    background:#cc0000;
}}

.login-box {{
    width:300px;
    margin:auto;
    margin-top:10%;
    background:white;
    padding:30px;
    border-radius:12px;
    text-align:center;
    box-shadow:0 10px 30px rgba(0,0,0,.2);
}}

.logo {{
    height:60px;
    margin-bottom:10px;
}}

input, button {{
    width:100%;
    padding:10px;
    margin:10px 0;
}}

button {{
    background:#1e90ff;
    color:white;
    border:none;
    cursor:pointer;
}}

.error {{ color:red; }}
</style>
</head>
<body>
{body}
</body>
</html>
""".encode())

    def redirect(self, loc):
        self.send_response(302)
        self.send_header("Location", loc)
        self.end_headers()

# ---------- RUN ----------
os.chdir(BASE)
print(f"Server running → http://localhost:{PORT}")
HTTPServer(("", PORT), RobotHandler).serve_forever()
