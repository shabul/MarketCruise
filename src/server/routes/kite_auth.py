import os

from dotenv import set_key
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

_ENV_FILE = ".env"


@router.get("/kite/login")
async def kite_login():
    """Redirect browser to Zerodha Kite login page."""
    api_key = os.environ.get("KITE_API_KEY", "")
    if not api_key:
        return HTMLResponse("<h3>KITE_API_KEY not set in .env</h3>", status_code=400)
    login_url = f"https://kite.zerodha.com/connect/login?v=3&api_key={api_key}"
    return HTMLResponse(f'<meta http-equiv="refresh" content="0; url={login_url}">')


@router.get("/kite/callback")
async def kite_callback(request_token: str = "", status: str = "", action: str = ""):
    """Zerodha redirects here after login. Exchange request_token for access_token."""
    if status != "success" or not request_token:
        return HTMLResponse(_page("Login failed", f"Status: {status}", success=False))

    api_key = os.environ.get("KITE_API_KEY", "")
    api_secret = os.environ.get("KITE_API_SECRET", "")

    if not api_key or not api_secret:
        return HTMLResponse(_page("Error", "KITE_API_KEY or KITE_API_SECRET not set in .env", success=False))

    try:
        from kiteconnect import KiteConnect
        kite = KiteConnect(api_key=api_key)
        session = kite.generate_session(request_token, api_secret=api_secret)
        access_token = session["access_token"]

        # Save to .env
        if not os.path.exists(_ENV_FILE):
            open(_ENV_FILE, "w").close()
        set_key(_ENV_FILE, "KITE_ACCESS_TOKEN", access_token)

        # Also update the running process environment
        os.environ["KITE_ACCESS_TOKEN"] = access_token

        user_name = session.get("user_name", "")
        return HTMLResponse(_page(
            "Connected!",
            f"Logged in as {user_name}. Access token saved to .env. Redirecting to the dashboard now.",
            success=True,
            redirect_url="/",
            redirect_delay=0,
        ))
    except Exception as e:
        return HTMLResponse(_page("Error", str(e), success=False))


@router.post("/kite/postback")
async def kite_postback():
    """Receives order update webhooks from Zerodha (optional)."""
    return {"status": "ok"}


def _page(
    title: str,
    message: str,
    success: bool,
    redirect_url: str = "",
    redirect_delay: int = 0,
) -> str:
    color = "#3fb950" if success else "#f85149"
    icon = "✓" if success else "✗"
    redirect_meta = ""
    redirect_script = ""
    redirect_hint = ""
    if success and redirect_url:
        redirect_meta = f'<meta http-equiv="refresh" content="{redirect_delay}; url={redirect_url}">'
        redirect_script = f"""
<script>
  window.location.replace({redirect_url!r});
</script>"""
        redirect_hint = f'<p><a href="{redirect_url}">Continue to dashboard</a></p>'
    return f"""<!DOCTYPE html>
<html>
<head><title>MarketCruise — Kite Auth</title>
{redirect_meta}
<style>
  body {{ background:#0d1117; color:#c9d1d9; font-family:'Segoe UI',sans-serif;
         display:flex; align-items:center; justify-content:center; height:100vh; margin:0; }}
  .card {{ background:#161b22; border:1px solid #30363d; border-radius:12px;
           padding:40px; text-align:center; max-width:420px; }}
  .icon {{ font-size:3rem; color:{color}; }}
  h2 {{ color:{color}; }}
  a {{ color:#79c0ff; }}
</style></head>
<body>
  <div class="card">
    <div class="icon">{icon}</div>
    <h2>{title}</h2>
    <p>{message}</p>
    {redirect_hint}
    <a href="/">← Back to Dashboard</a>
  </div>
  {redirect_script}
</body>
</html>"""
