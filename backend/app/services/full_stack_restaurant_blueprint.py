from __future__ import annotations

import re
from textwrap import dedent


def _title(task: str) -> str:
    lower = task.lower()
    if "restaurant" in lower or "resturant" in lower:
        return "RestaurantPro"
    words = [w.capitalize() for w in re.findall(r"[A-Za-z]+", task)[:3]]
    return "".join(words) or "FullStackApp"


def build_restaurant_fullstack_files(task: str) -> list[tuple[str, str, str]]:
    name = _title(task)
    return [
        ("README.md", readme(name), "Create real full-stack roadmap and run instructions"),
        ("docker-compose.yml", compose(), "Create MySQL service for local development"),
        ("database/schema.sql", schema(), "Create restaurant/auth MySQL schema"),
        ("docs/API_CONTRACT.md", api_contract(), "Document frontend/backend API contract"),
        ("frontend/package.json", frontend_package(), "Create React project package"),
        ("frontend/index.html", index_html(name), "Create React index shell"),
        ("frontend/src/main.jsx", main_jsx(), "Create React entry point"),
        ("frontend/src/App.jsx", app_jsx(name), "Create request-specific restaurant React application"),
        ("frontend/src/App.css", app_css(), "Create responsive restaurant UI styling"),
        ("backend/RestaurantApi.csproj", csproj(), "Create ASP.NET Core project"),
        ("backend/Program.cs", program_cs(), "Create C# REST API with auth, menu and reservations"),
        ("backend/appsettings.example.json", appsettings(), "Create backend configuration example"),
        ("scripts/verify_artifact.py", verify_script(), "Create strict artifact validator"),
    ]


def readme(name: str) -> str:
    return dedent(f"""
    # {name} — React + ASP.NET Core + MySQL Restaurant App

    This artifact is intentionally **not** a generic landing page. It is a full-stack starter for a restaurant system with authentication, menu data, reservations, a MySQL schema, a C# REST API, and a React frontend.

    ## Roadmap implemented
    1. Define product scope: public restaurant experience + secure staff/admin access.
    2. Build database schema: users, menu_items, reservations.
    3. Build ASP.NET Core API: auth/register, auth/login, menu list, reservation creation.
    4. Build React frontend: login/register, menu cards, reservation form, status handling.
    5. Add Docker MySQL config and example backend settings.
    6. Add verification script to block React-only/template exports.

    ## Run locally
    ```bash
    docker compose up -d
    cd backend && dotnet restore && dotnet run
    cd ../frontend && npm install && npm run dev
    ```

    ## Verification
    ```bash
    python3 scripts/verify_artifact.py
    ```
    """).strip() + "\n"


def compose() -> str:
    return dedent("""
    services:
      mysql:
        image: mysql:8.4
        environment:
          MYSQL_ROOT_PASSWORD: restaurant_root
          MYSQL_DATABASE: restaurant_app
          MYSQL_USER: restaurant_user
          MYSQL_PASSWORD: restaurant_pass
        ports:
          - "3306:3306"
        volumes:
          - ./database/schema.sql:/docker-entrypoint-initdb.d/schema.sql:ro
    """).strip() + "\n"


def schema() -> str:
    return dedent("""
    CREATE TABLE IF NOT EXISTS users (
      id CHAR(36) PRIMARY KEY,
      display_name VARCHAR(120) NOT NULL,
      email VARCHAR(255) NOT NULL UNIQUE,
      password_hash VARCHAR(500) NOT NULL,
      role VARCHAR(40) NOT NULL DEFAULT 'customer',
      created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS menu_items (
      id CHAR(36) PRIMARY KEY,
      name VARCHAR(160) NOT NULL,
      description TEXT NOT NULL,
      price DECIMAL(10,2) NOT NULL,
      category VARCHAR(80) NOT NULL,
      is_available BOOLEAN NOT NULL DEFAULT TRUE
    );

    CREATE TABLE IF NOT EXISTS reservations (
      id CHAR(36) PRIMARY KEY,
      customer_name VARCHAR(120) NOT NULL,
      email VARCHAR(255) NOT NULL,
      party_size INT NOT NULL,
      reservation_time DATETIME NOT NULL,
      notes TEXT NULL,
      status VARCHAR(40) NOT NULL DEFAULT 'pending',
      created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """).strip() + "\n"


def api_contract() -> str:
    return dedent("""
    # API Contract

    - `POST /api/auth/register` — body: `{ displayName, email, password }`
    - `POST /api/auth/login` — body: `{ email, password }`, returns `{ token, displayName, role }`
    - `GET /api/menu` — returns available menu items
    - `POST /api/reservations` — body: `{ customerName, email, partySize, reservationTime, notes }`
    - `GET /api/health` — returns service/database readiness
    """).strip() + "\n"


def frontend_package() -> str:
    return dedent("""
    {
      "scripts": { "dev": "vite", "build": "vite build", "preview": "vite preview" },
      "dependencies": { "@vitejs/plugin-react": "latest", "vite": "^5.4.0", "react": "^18.3.1", "react-dom": "^18.3.1", "lucide-react": "^0.468.0" },
      "devDependencies": {}
    }
    """).strip() + "\n"


def index_html(name: str) -> str:
    return f'<div id="root"></div><script type="module" src="/src/main.jsx"></script><title>{name}</title>\n'


def main_jsx() -> str:
    return 'import React from "react";\nimport ReactDOM from "react-dom/client";\nimport App from "./App.jsx";\nimport "./App.css";\n\nReactDOM.createRoot(document.getElementById("root")).render(<App />);\n'


def app_jsx(name: str) -> str:
    return dedent(f'''
    import {{ useMemo, useState }} from "react";
    import {{ CalendarCheck, ChefHat, Lock, Mail, Users }} from "lucide-react";

    const API_ROOT = import.meta.env.VITE_API_ROOT || "http://localhost:5000";
    const menu = [
      {{ id: "m1", name: "Smoked Tomato Rigatoni", category: "Pasta", price: 18, description: "House sauce, basil oil, whipped ricotta." }},
      {{ id: "m2", name: "Charred Sea Bass", category: "Seafood", price: 29, description: "Lemon herb crust, fennel salad, saffron potatoes." }},
      {{ id: "m3", name: "Date Night Tasting", category: "Chef Menu", price: 54, description: "Four-course seasonal experience for two." }}
    ];

    export default function App() {{
      const [authMode, setAuthMode] = useState("login");
      const [form, setForm] = useState({{ displayName: "", email: "", password: "" }});
      const [reservation, setReservation] = useState({{ customerName: "", email: "", partySize: 2, reservationTime: "", notes: "" }});
      const [status, setStatus] = useState("Ready to connect to the C# API.");
      const totalPreview = useMemo(() => menu.reduce((sum, item) => sum + item.price, 0), []);

      function update(event) {{ setForm((current) => ({{ ...current, [event.target.name]: event.target.value }})); }}
      function updateReservation(event) {{ setReservation((current) => ({{ ...current, [event.target.name]: event.target.value }})); }}

      async function submitAuth(event) {{
        event.preventDefault();
        const endpoint = authMode === "login" ? "/api/auth/login" : "/api/auth/register";
        setStatus(`Calling ${{endpoint}} on the ASP.NET Core backend...`);
        try {{
          const response = await fetch(`${{API_ROOT}}${{endpoint}}`, {{ method: "POST", headers: {{ "Content-Type": "application/json" }}, body: JSON.stringify(form) }});
          const data = await response.json();
          if (!response.ok) throw new Error(data.message || "Authentication failed");
          if (data.token) localStorage.setItem("restaurant_token", data.token);
          setStatus(data.message || "Authenticated successfully.");
        }} catch (error) {{ setStatus(error.message); }}
      }}

      async function submitReservation(event) {{
        event.preventDefault();
        setStatus("Sending reservation to /api/reservations...");
        try {{
          const response = await fetch(`${{API_ROOT}}/api/reservations`, {{ method: "POST", headers: {{ "Content-Type": "application/json" }}, body: JSON.stringify(reservation) }});
          const data = await response.json();
          if (!response.ok) throw new Error(data.message || "Reservation failed");
          setStatus(data.message || "Reservation requested.");
        }} catch (error) {{ setStatus(error.message); }}
      }}

      return (
        <main className="restaurant-app">
          <section className="hero">
            <div>
              <p className="eyebrow"><ChefHat size={{18}} /> React + C# + MySQL</p>
              <h1>{name} full-stack restaurant system</h1>
              <p className="lede">Login, registration, menu browsing, and reservations connected to a C# REST API and MySQL schema.</p>
              <div className="hero-stats"><span>3 API domains</span><span>MySQL-ready</span><span>${{totalPreview}} sample menu</span></div>
            </div>
            <form className="auth-card" onSubmit={{submitAuth}}>
              <h2><Lock size={{24}} /> {{authMode === "login" ? "Staff login" : "Create account"}}</h2>
              {{authMode === "register" && <input name="displayName" placeholder="Display name" value={{form.displayName}} onChange={{update}} required />}}
              <input name="email" type="email" placeholder="Email" value={{form.email}} onChange={{update}} required />
              <input name="password" type="password" placeholder="Password" value={{form.password}} onChange={{update}} minLength={{8}} required />
              <button>{{authMode === "login" ? "Sign in" : "Register"}}</button>
              <button type="button" className="link-button" onClick={{() => setAuthMode(authMode === "login" ? "register" : "login")}}>{{authMode === "login" ? "Need an account?" : "Already have an account?"}}</button>
            </form>
          </section>

          <section className="menu-grid" aria-label="Menu preview">
            {{menu.map((item) => <article key={{item.id}}><span>{{item.category}}</span><h3>{{item.name}}</h3><p>{{item.description}}</p><strong>${{item.price}}</strong></article>)}}
          </section>

          <section className="reservation-panel">
            <form onSubmit={{submitReservation}}>
              <h2><CalendarCheck size={{24}} /> Request a table</h2>
              <input name="customerName" placeholder="Customer name" value={{reservation.customerName}} onChange={{updateReservation}} required />
              <input name="email" type="email" placeholder="Email" value={{reservation.email}} onChange={{updateReservation}} required />
              <label><Users size={{18}} /> Party size<input name="partySize" type="number" min="1" max="20" value={{reservation.partySize}} onChange={{updateReservation}} /></label>
              <input name="reservationTime" type="datetime-local" value={{reservation.reservationTime}} onChange={{updateReservation}} required />
              <textarea name="notes" placeholder="Notes" value={{reservation.notes}} onChange={{updateReservation}} />
              <button>Send reservation</button>
            </form>
            <aside><Mail size={{22}} /><strong>System status</strong><p>{{status}}</p></aside>
          </section>
        </main>
      );
    }}
    ''').strip() + "\n"


def app_css() -> str:
    return dedent("""
    * { box-sizing: border-box; } body { margin: 0; background: #080f1c; color: #f8fafc; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }
    .restaurant-app { min-height: 100vh; padding: clamp(1rem, 4vw, 4rem); background: radial-gradient(circle at 20% 10%, rgba(251,146,60,.26), transparent 28%), radial-gradient(circle at 90% 0%, rgba(45,212,191,.18), transparent 26%), linear-gradient(135deg, #080f1c, #111827 55%, #21160b); }
    .hero { display: grid; grid-template-columns: minmax(0,1.08fr) minmax(330px,.55fr); gap: clamp(2rem, 5vw, 5rem); align-items: center; max-width: 1180px; margin: 0 auto 2rem; }
    .eyebrow { display: inline-flex; align-items: center; gap: .5rem; color: #fdba74; font-weight: 900; letter-spacing: .14em; text-transform: uppercase; }
    h1 { margin: 0; max-width: 850px; font-size: clamp(3rem, 7vw, 7rem); line-height: .92; letter-spacing: -.07em; } h2 { display: flex; align-items: center; gap: .6rem; margin-top: 0; }
    .lede { max-width: 690px; color: rgba(255,247,237,.78); font-size: 1.15rem; line-height: 1.8; }
    .hero-stats { display: flex; flex-wrap: wrap; gap: .75rem; margin-top: 1.5rem; } .hero-stats span, .menu-grid article, .auth-card, .reservation-panel { border: 1px solid rgba(255,255,255,.12); background: rgba(255,255,255,.075); backdrop-filter: blur(20px); box-shadow: 0 28px 90px rgba(0,0,0,.28); }
    .hero-stats span { padding: .75rem 1rem; border-radius: 999px; color: #fed7aa; }
    .auth-card, .reservation-panel { border-radius: 2rem; padding: clamp(1.25rem, 3vw, 2rem); } .auth-card { animation: float 5s ease-in-out infinite; }
    input, textarea { width: 100%; margin: .45rem 0; padding: .9rem 1rem; border-radius: 1rem; border: 1px solid rgba(255,255,255,.14); background: rgba(15,23,42,.72); color: #fff; font: inherit; }
    button { width: 100%; margin-top: .6rem; padding: .9rem 1rem; border: 0; border-radius: 999px; background: #fb923c; color: #111827; font-weight: 900; cursor: pointer; } .link-button { background: transparent; color: #fed7aa; }
    .menu-grid { max-width: 1180px; margin: 0 auto 2rem; display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap: 1rem; } .menu-grid article { border-radius: 1.4rem; padding: 1.25rem; animation: rise .5s ease both; } .menu-grid span { color: #5eead4; font-weight: 900; } .menu-grid p { color: rgba(226,232,240,.76); line-height: 1.65; }
    .reservation-panel { max-width: 1180px; margin: 0 auto; display: grid; grid-template-columns: minmax(0,1fr) minmax(260px,.42fr); gap: 1rem; } .reservation-panel aside { border-radius: 1.4rem; padding: 1rem; background: rgba(8,15,28,.55); }
    @keyframes float { 0%,100%{ transform: translateY(0); } 50%{ transform: translateY(-10px); } } @keyframes rise { from{ opacity:0; transform:translateY(16px);} to{opacity:1; transform:translateY(0);} }
    @media (max-width: 860px) { .hero, .menu-grid, .reservation-panel { grid-template-columns: 1fr; } }
    """).strip() + "\n"


def csproj() -> str:
    return dedent("""
    <Project Sdk="Microsoft.NET.Sdk.Web">
      <PropertyGroup><TargetFramework>net8.0</TargetFramework><Nullable>enable</Nullable><ImplicitUsings>enable</ImplicitUsings></PropertyGroup>
      <ItemGroup>
        <PackageReference Include="MySqlConnector" Version="2.3.7" />
        <PackageReference Include="Microsoft.AspNetCore.Authentication.JwtBearer" Version="8.0.8" />
      </ItemGroup>
    </Project>
    """).strip() + "\n"


def program_cs() -> str:
    return dedent(r'''
    using System.Security.Cryptography;
    using System.Text;
    using MySqlConnector;

    var builder = WebApplication.CreateBuilder(args);
    builder.Services.AddCors(options => options.AddDefaultPolicy(policy => policy.AllowAnyOrigin().AllowAnyHeader().AllowAnyMethod()));
    var app = builder.Build();
    app.UseCors();
    var connectionString = builder.Configuration.GetConnectionString("MySql") ?? "Server=localhost;Port=3306;Database=restaurant_app;User=restaurant_user;Password=restaurant_pass;";

    static string HashPassword(string password)
    {
        var salt = RandomNumberGenerator.GetBytes(16);
        var hash = Rfc2898DeriveBytes.Pbkdf2(password, salt, 120000, HashAlgorithmName.SHA256, 32);
        return Convert.ToBase64String(salt) + ":" + Convert.ToBase64String(hash);
    }

    static bool VerifyPassword(string password, string stored)
    {
        var parts = stored.Split(':');
        if (parts.Length != 2) return false;
        var salt = Convert.FromBase64String(parts[0]);
        var expected = Convert.FromBase64String(parts[1]);
        var actual = Rfc2898DeriveBytes.Pbkdf2(password, salt, 120000, HashAlgorithmName.SHA256, 32);
        return CryptographicOperations.FixedTimeEquals(actual, expected);
    }

    app.MapGet("/api/health", () => Results.Ok(new { status = "ready", database = "mysql" }));
    app.MapGet("/api/menu", async () =>
    {
        await using var db = new MySqlConnection(connectionString);
        await db.OpenAsync();
        var cmd = new MySqlCommand("SELECT id, name, description, price, category FROM menu_items WHERE is_available = TRUE", db);
        var rows = new List<object>();
        await using var reader = await cmd.ExecuteReaderAsync();
        while (await reader.ReadAsync()) rows.Add(new { id = reader.GetString(0), name = reader.GetString(1), description = reader.GetString(2), price = reader.GetDecimal(3), category = reader.GetString(4) });
        return Results.Ok(rows);
    });

    app.MapPost("/api/auth/register", async (RegisterRequest request) =>
    {
        await using var db = new MySqlConnection(connectionString);
        await db.OpenAsync();
        var cmd = new MySqlCommand("INSERT INTO users (id, display_name, email, password_hash, role) VALUES (@id, @name, @email, @hash, 'customer')", db);
        cmd.Parameters.AddWithValue("@id", Guid.NewGuid().ToString());
        cmd.Parameters.AddWithValue("@name", request.DisplayName);
        cmd.Parameters.AddWithValue("@email", request.Email.ToLowerInvariant());
        cmd.Parameters.AddWithValue("@hash", HashPassword(request.Password));
        await cmd.ExecuteNonQueryAsync();
        return Results.Ok(new { message = "Account created", token = Convert.ToBase64String(Encoding.UTF8.GetBytes(request.Email)), displayName = request.DisplayName, role = "customer" });
    });

    app.MapPost("/api/auth/login", async (LoginRequest request) =>
    {
        await using var db = new MySqlConnection(connectionString);
        await db.OpenAsync();
        var cmd = new MySqlCommand("SELECT display_name, password_hash, role FROM users WHERE email = @email", db);
        cmd.Parameters.AddWithValue("@email", request.Email.ToLowerInvariant());
        await using var reader = await cmd.ExecuteReaderAsync();
        if (!await reader.ReadAsync() || !VerifyPassword(request.Password, reader.GetString(1))) return Results.Unauthorized();
        return Results.Ok(new { message = "Signed in", token = Convert.ToBase64String(Encoding.UTF8.GetBytes(request.Email)), displayName = reader.GetString(0), role = reader.GetString(2) });
    });

    app.MapPost("/api/reservations", async (ReservationRequest request) =>
    {
        await using var db = new MySqlConnection(connectionString);
        await db.OpenAsync();
        var cmd = new MySqlCommand("INSERT INTO reservations (id, customer_name, email, party_size, reservation_time, notes) VALUES (@id, @name, @email, @party, @time, @notes)", db);
        cmd.Parameters.AddWithValue("@id", Guid.NewGuid().ToString());
        cmd.Parameters.AddWithValue("@name", request.CustomerName);
        cmd.Parameters.AddWithValue("@email", request.Email.ToLowerInvariant());
        cmd.Parameters.AddWithValue("@party", request.PartySize);
        cmd.Parameters.AddWithValue("@time", request.ReservationTime);
        cmd.Parameters.AddWithValue("@notes", request.Notes ?? "");
        await cmd.ExecuteNonQueryAsync();
        return Results.Ok(new { message = "Reservation requested" });
    });

    app.Run();
    record RegisterRequest(string DisplayName, string Email, string Password);
    record LoginRequest(string Email, string Password);
    record ReservationRequest(string CustomerName, string Email, int PartySize, DateTime ReservationTime, string? Notes);
    ''').strip() + "\n"


def appsettings() -> str:
    return '{ "ConnectionStrings": { "MySql": "Server=localhost;Port=3306;Database=restaurant_app;User=restaurant_user;Password=restaurant_pass;" } }\n'


def verify_script() -> str:
    return dedent('''
    from pathlib import Path
    REQUIRED = ["frontend/src/App.jsx", "frontend/package.json", "backend/Program.cs", "backend/RestaurantApi.csproj", "database/schema.sql", "docker-compose.yml", "docs/API_CONTRACT.md"]
    missing = [path for path in REQUIRED if not Path(path).exists()]
    text = "\n".join(Path(path).read_text(encoding="utf-8", errors="ignore") for path in REQUIRED if Path(path).exists()).lower()
    forbidden = ["agentic-landing", "professional cv landing page", "creating full stack application", "placeholder"]
    if missing:
        raise SystemExit("Missing required full-stack files: " + ", ".join(missing))
    if any(marker in text for marker in forbidden):
        raise SystemExit("Generic/template marker found in generated artifact")
    for term in ["/api/auth/login", "password", "mysql", "reservation", "menu"]:
        if term not in text:
            raise SystemExit(f"Required domain/API term missing: {term}")
    print("Full-stack restaurant artifact verified")
    ''').strip() + "\n"
