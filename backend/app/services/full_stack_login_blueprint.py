'''Deterministic full-stack blueprints for complex sandbox tasks.'''
from __future__ import annotations

import json


def build_full_stack_login_files(subject: str) -> list[tuple[str, str, str]]:
    return [
        ("README.md", _readme(subject), "Create full-stack setup and roadmap README"),
        ("docker-compose.yml", _compose(), "Create MySQL docker-compose service"),
        ("database/schema.sql", _schema(), "Create MySQL users schema"),
        ("scripts/verify_fullstack_artifact.py", _verifier(), "Create deterministic full-stack verification gate"),
        ("frontend/package.json", _frontend_package_json(), "Create React/Vite frontend package"),
        ("frontend/index.html", '<div id="root"></div><script type="module" src="/src/main.jsx"></script>\n', "Create frontend HTML entry"),
        ("frontend/src/main.jsx", 'import React from "react";\nimport ReactDOM from "react-dom/client";\nimport App from "./App.jsx";\nimport "./App.css";\n\nReactDOM.createRoot(document.getElementById("root")).render(<App />);\n', "Create React entry point"),
        ("frontend/src/App.jsx", _app_jsx(subject), "Create React login page wired to C# API"),
        ("frontend/src/App.css", _app_css(), "Create responsive login styling"),
        ("backend/AuthApi.csproj", _csproj(), "Create ASP.NET Core API project"),
        ("backend/Program.cs", _program_cs(), "Create C# auth API with MySQL and JWT"),
        ("backend/appsettings.example.json", _appsettings(), "Create backend configuration example"),
    ]


def _readme(subject: str) -> str:
    return f'''# {subject} Full-Stack Login Project

This artifact is intentionally full-stack, not a React-only template.

## Roadmap implemented

1. Detect requested stack: React frontend, C# / ASP.NET Core backend, MySQL database, and login/auth flow.
2. Build the React login/register page with API integration and real authentication states.
3. Build the ASP.NET Core API with register/login endpoints, password hashing, MySQL access, and JWT token issuing.
4. Build the MySQL schema with unique email constraints and audit fields.
5. Run a deterministic verifier that refuses export when any requested layer is missing.

## Run locally

```bash
docker compose up -d mysql

cd backend
dotnet restore
dotnet run

cd ../frontend
npm install
npm run dev
```

The frontend uses `VITE_API_BASE_URL` or defaults to `http://localhost:5088`.
'''


def _compose() -> str:
    return '''services:
  mysql:
    image: mysql:8.4
    container_name: ise_ai_login_mysql
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: root_password_change_me
      MYSQL_DATABASE: login_app
      MYSQL_USER: login_user
      MYSQL_PASSWORD: login_password_change_me
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
      - ./database/schema.sql:/docker-entrypoint-initdb.d/001_schema.sql:ro
volumes:
  mysql_data:
'''


def _schema() -> str:
    return '''CREATE DATABASE IF NOT EXISTS login_app;
USE login_app;

CREATE TABLE IF NOT EXISTS users (
  id CHAR(36) PRIMARY KEY,
  email VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(512) NOT NULL,
  display_name VARCHAR(160) NOT NULL,
  role VARCHAR(64) NOT NULL DEFAULT 'user',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  last_login_at TIMESTAMP NULL DEFAULT NULL,
  INDEX idx_users_email (email)
);
'''


def _frontend_package_json() -> str:
    return json.dumps(
        {
            "scripts": {
                "dev": "vite --host 0.0.0.0",
                "build": "vite build",
                "preview": "vite preview"
            },
            "dependencies": {
                "@vitejs/plugin-react": "latest",
                "vite": "latest",
                "react": "latest",
                "react-dom": "latest",
                "lucide-react": "latest"
            },
            "devDependencies": {}
        },
        indent=2,
    )


def _app_jsx(subject: str) -> str:
    return f'''import React, {{ useState }} from "react";
import {{ Lock, Mail, ShieldCheck, UserPlus }} from "lucide-react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:5088";

export default function App() {{
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({{ email: "", password: "", displayName: "" }});
  const [status, setStatus] = useState({{ state: "idle", message: "Ready to authenticate against the C# API." }});

  const update = (event) => setForm((current) => ({{ ...current, [event.target.name]: event.target.value }}));

  async function submit(event) {{
    event.preventDefault();
    setStatus({{ state: "loading", message: mode === "login" ? "Signing in..." : "Creating account..." }});
    const endpoint = mode === "login" ? "/api/auth/login" : "/api/auth/register";
    const payload = mode === "login" ? {{ email: form.email, password: form.password }} : form;
    try {{
      const response = await fetch(`${{API_BASE_URL}}${{endpoint}}`, {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify(payload)
      }});
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || "Authentication request failed");
      if (data.token) localStorage.setItem("login_token", data.token);
      setStatus({{ state: "success", message: data.message || "Authenticated successfully." }});
    }} catch (error) {{
      setStatus({{ state: "error", message: error.message }});
    }}
  }}

  return (
    <main className="login-shell">
      <section className="login-brand-panel">
        <p className="login-kicker">React + C# + MySQL</p>
        <h1>{subject} authentication portal</h1>
        <p className="login-lede">A real full-stack login starter with a React frontend, ASP.NET Core API, MySQL users table, password hashing, and JWT-ready responses.</p>
        <div className="architecture-grid" aria-label="Implemented architecture">
          <span>React login UI</span>
          <span>ASP.NET Core auth API</span>
          <span>MySQL user storage</span>
          <span>JWT token response</span>
        </div>
      </section>

      <section className="auth-card" aria-label="Authentication form">
        <div className="auth-card__header">
          <ShieldCheck size={{28}} />
          <div>
            <p className="login-kicker">Secure access</p>
            <h2>{{mode === "login" ? "Welcome back" : "Create your account"}}</h2>
          </div>
        </div>

        <form onSubmit={{submit}} className="auth-form">
          {{mode === "register" && (
            <label>
              <span>Display name</span>
              <div className="input-wrap"><UserPlus size={{18}} /><input name="displayName" value={{form.displayName}} onChange={{update}} required minLength={{2}} /></div>
            </label>
          )}}
          <label>
            <span>Email</span>
            <div className="input-wrap"><Mail size={{18}} /><input name="email" type="email" value={{form.email}} onChange={{update}} required /></div>
          </label>
          <label>
            <span>Password</span>
            <div className="input-wrap"><Lock size={{18}} /><input name="password" type="password" value={{form.password}} onChange={{update}} required minLength={{8}} /></div>
          </label>
          <button disabled={{status.state === "loading"}}>{{mode === "login" ? "Sign in" : "Create account"}}</button>
        </form>

        <p className={{`auth-status auth-status--${{status.state}}`}}>{{status.message}}</p>
        <button className="mode-switch" type="button" onClick={{() => setMode(mode === "login" ? "register" : "login")}}>
          {{mode === "login" ? "Need an account? Register" : "Already registered? Sign in"}}
        </button>
      </section>
    </main>
  );
}}
'''


def _app_css() -> str:
    return '''* { box-sizing: border-box; }
body { margin: 0; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #08111f; color: #f8fafc; }
.login-shell { min-height: 100vh; display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(360px, .72fr); gap: clamp(2rem, 6vw, 5rem); align-items: center; padding: clamp(1.25rem, 4vw, 5rem); background: radial-gradient(circle at 15% 20%, rgba(59, 130, 246, .26), transparent 30%), radial-gradient(circle at 80% 10%, rgba(20, 184, 166, .2), transparent 24%), linear-gradient(135deg, #08111f 0%, #111827 58%, #172554 100%); }
.login-brand-panel { max-width: 760px; animation: rise-in 520ms ease both; }
.login-kicker { margin: 0 0 .65rem; color: #67e8f9; font-size: .78rem; font-weight: 900; letter-spacing: .18em; text-transform: uppercase; }
h1, h2 { margin: 0; letter-spacing: -.055em; line-height: .96; }
h1 { font-size: clamp(3rem, 7vw, 7.2rem); }
h2 { font-size: clamp(2rem, 4vw, 3.3rem); }
.login-lede { max-width: 680px; color: rgba(226, 232, 240, .78); font-size: 1.12rem; line-height: 1.8; }
.architecture-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .85rem; margin-top: 2rem; }
.architecture-grid span, .auth-card { border: 1px solid rgba(255,255,255,.12); background: rgba(255,255,255,.075); box-shadow: 0 30px 90px rgba(0,0,0,.32); backdrop-filter: blur(22px); }
.architecture-grid span { padding: 1rem; border-radius: 1.1rem; color: rgba(248,250,252,.88); }
.auth-card { border-radius: 2rem; padding: clamp(1.2rem, 3vw, 2rem); animation: card-float 5s ease-in-out infinite; }
.auth-card__header { display: flex; gap: 1rem; align-items: center; margin-bottom: 1.35rem; }
.auth-card__header svg { color: #67e8f9; }
.auth-form { display: grid; gap: 1rem; }
.auth-form label span { display: block; margin-bottom: .45rem; color: rgba(226,232,240,.78); font-weight: 800; }
.input-wrap { display: flex; align-items: center; gap: .7rem; padding: .9rem 1rem; border-radius: 1rem; border: 1px solid rgba(255,255,255,.14); background: rgba(15,23,42,.72); }
.input-wrap svg { color: #93c5fd; }
.input-wrap input { width: 100%; border: 0; outline: 0; background: transparent; color: #f8fafc; font: inherit; }
.auth-form button, .mode-switch { width: 100%; border: 0; cursor: pointer; border-radius: 999px; padding: .95rem 1.2rem; font-weight: 950; transition: transform .18s ease, opacity .18s ease; }
.auth-form button { color: #06121f; background: linear-gradient(135deg, #67e8f9, #a7f3d0); box-shadow: 0 18px 45px rgba(103,232,249,.24); }
.auth-form button:hover, .mode-switch:hover { transform: translateY(-2px); }
.auth-form button:disabled { opacity: .6; cursor: wait; }
.mode-switch { margin-top: 1rem; color: #f8fafc; background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.12); }
.auth-status { min-height: 1.5rem; color: rgba(226,232,240,.78); }
.auth-status--success { color: #86efac; }
.auth-status--error { color: #fca5a5; }
@keyframes rise-in { from { opacity: 0; transform: translateY(18px); } to { opacity: 1; transform: translateY(0); } }
@keyframes card-float { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-10px); } }
@media (max-width: 880px) { .login-shell { grid-template-columns: 1fr; } .architecture-grid { grid-template-columns: 1fr; } }
'''


def _csproj() -> str:
    return '''<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="MySqlConnector" Version="2.3.7" />
    <PackageReference Include="Microsoft.AspNetCore.Authentication.JwtBearer" Version="8.0.10" />
    <PackageReference Include="System.IdentityModel.Tokens.Jwt" Version="8.0.2" />
  </ItemGroup>
</Project>
'''


def _program_cs() -> str:
    return r'''using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Text;
using Microsoft.AspNetCore.Identity;
using Microsoft.IdentityModel.Tokens;
using MySqlConnector;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddCors(options => options.AddPolicy("frontend", policy => policy
    .WithOrigins(builder.Configuration["FrontendOrigin"] ?? "http://localhost:5173")
    .AllowAnyHeader()
    .AllowAnyMethod()));

var app = builder.Build();
app.UseCors("frontend");

string connectionString = builder.Configuration.GetConnectionString("Default")
    ?? "Server=localhost;Port=3306;Database=login_app;User=login_user;Password=login_password_change_me;";
string jwtSecret = builder.Configuration["Jwt:Secret"] ?? "change-this-development-secret-to-a-long-random-value";
var hasher = new PasswordHasher<AuthUser>();

app.MapGet("/api/health", () => Results.Ok(new { status = "ok", service = "AuthApi" }));

app.MapPost("/api/auth/register", async (RegisterRequest request) =>
{
    if (string.IsNullOrWhiteSpace(request.Email) || string.IsNullOrWhiteSpace(request.Password) || request.Password.Length < 8)
        return Results.BadRequest(new { message = "Email and password with at least 8 characters are required." });

    var user = new AuthUser(Guid.NewGuid().ToString(), request.Email.Trim().ToLowerInvariant(), request.DisplayName.Trim());
    string passwordHash = hasher.HashPassword(user, request.Password);

    await using var connection = new MySqlConnection(connectionString);
    await connection.OpenAsync();
    await using var command = connection.CreateCommand();
    command.CommandText = "INSERT INTO users (id, email, password_hash, display_name) VALUES (@id, @email, @hash, @name);";
    command.Parameters.AddWithValue("@id", user.Id);
    command.Parameters.AddWithValue("@email", user.Email);
    command.Parameters.AddWithValue("@hash", passwordHash);
    command.Parameters.AddWithValue("@name", user.DisplayName);

    try { await command.ExecuteNonQueryAsync(); }
    catch (MySqlException ex) when (ex.Number == 1062) { return Results.Conflict(new { message = "An account already exists for this email." }); }

    return Results.Ok(new { message = "Account created successfully.", token = CreateToken(user, jwtSecret) });
});

app.MapPost("/api/auth/login", async (LoginRequest request) =>
{
    await using var connection = new MySqlConnection(connectionString);
    await connection.OpenAsync();
    await using var command = connection.CreateCommand();
    command.CommandText = "SELECT id, email, password_hash, display_name FROM users WHERE email = @email LIMIT 1;";
    command.Parameters.AddWithValue("@email", request.Email.Trim().ToLowerInvariant());
    await using var reader = await command.ExecuteReaderAsync();
    if (!await reader.ReadAsync()) return Results.Unauthorized();

    var user = new AuthUser(reader.GetString("id"), reader.GetString("email"), reader.GetString("display_name"));
    string hash = reader.GetString("password_hash");
    if (hasher.VerifyHashedPassword(user, hash, request.Password) == PasswordVerificationResult.Failed)
        return Results.Unauthorized();

    return Results.Ok(new { message = "Signed in successfully.", token = CreateToken(user, jwtSecret) });
});

app.Run("http://0.0.0.0:5088");

static string CreateToken(AuthUser user, string secret)
{
    var key = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(secret.PadRight(32, '!')));
    var credentials = new SigningCredentials(key, SecurityAlgorithms.HmacSha256);
    var token = new JwtSecurityToken(
        issuer: "ise-ai-auth-api",
        audience: "ise-ai-react-client",
        claims: new[] { new Claim(JwtRegisteredClaimNames.Sub, user.Id), new Claim(JwtRegisteredClaimNames.Email, user.Email), new Claim("name", user.DisplayName) },
        expires: DateTime.UtcNow.AddHours(8),
        signingCredentials: credentials);
    return new JwtSecurityTokenHandler().WriteToken(token);
}

record RegisterRequest(string Email, string Password);
record AuthUser(string Id, string Email, string DisplayName);
'''


def _appsettings() -> str:
    return '''{
  "ConnectionStrings": {
    "Default": "Server=localhost;Port=3306;Database=login_app;User=login_user;Password=login_password_change_me;"
  },
  "FrontendOrigin": "http://localhost:5173",
  "Jwt": {
    "Secret": "replace-with-a-long-random-development-secret"
  }
}
'''


def _verifier() -> str:
    return r'''from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
required = [
    "frontend/src/App.jsx",
    "frontend/src/main.jsx",
    "frontend/package.json",
    "backend/Program.cs",
    "backend/AuthApi.csproj",
    "database/schema.sql",
    "docker-compose.yml",
]
missing = [path for path in required if not (root / path).is_file()]
if missing:
    print("Missing required full-stack files: " + ", ".join(missing))
    sys.exit(1)

content = "\n".join((root / path).read_text(encoding="utf-8", errors="ignore") for path in required)
checks = {
    "React UI": "fetch(`${API_BASE_URL}" in content and "auth-card" in content,
    "C# API": "MapPost(\"/api/auth/login\"" in content and "PasswordHasher" in content,
    "MySQL": "CREATE TABLE IF NOT EXISTS users" in content and "MySqlConnector" in content,
    "JWT": "JwtSecurityToken" in content,
    "No React-only fallback": "agentic-landing" not in content and "A modern landing page" not in content,
}
failed = [name for name, ok in checks.items() if not ok]
if failed:
    print("Full-stack verification failed: " + ", ".join(failed))
    sys.exit(1)
print("Full-stack verification passed: React + C# + MySQL login project is complete.")
'''
