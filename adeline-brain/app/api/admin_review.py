"""
Admin Review Page — /brain/admin/canonicals

Lightweight server-rendered HTML page for reviewing pending canonical lessons.
No JS framework; uses inline HTML + fetch() for one-click approve actions.
Requires a valid admin JWT (same as API endpoints).
"""
import logging
import os
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse

from app.api.middleware import get_current_user_id, require_role
from app.schemas.api_models import UserRole

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin-review"])

_BRAIN_URL = os.getenv("BRAIN_PUBLIC_URL", "/brain")


@router.get(
    "/canonicals",
    response_class=HTMLResponse,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def canonical_review_page(
    request: Request,
    user_id: str = Depends(get_current_user_id),
) -> HTMLResponse:
    """Serve the canonical pending-review dashboard."""
    from app.connections.canonical_store import canonical_store
    pending = await canonical_store.list_pending()

    rows_html = ""
    if not pending:
        rows_html = (
            '<tr><td colspan="5" style="text-align:center;padding:2rem;color:#6b7280;">'
            "No canonicals pending review. 🎉"
            "</td></tr>"
        )
    else:
        for item in pending:
            slug = item["slug"]
            track = item["track"].replace("_", " ").title()
            reason = item.get("needs_review_reason") or "—"
            updated = (item.get("updated_at") or "")[:10]
            rows_html += f"""
            <tr id="row-{slug}">
              <td style="padding:.75rem 1rem;font-weight:500;">{item['topic']}</td>
              <td style="padding:.75rem 1rem;">{track}</td>
              <td style="padding:.75rem 1rem;color:#6b7280;font-size:.875rem;">{reason}</td>
              <td style="padding:.75rem 1rem;color:#6b7280;font-size:.875rem;">{updated}</td>
              <td style="padding:.75rem 1rem;">
                <button
                  onclick="approve('{slug}', this)"
                  style="background:#16a34a;color:#fff;border:none;padding:.4rem .9rem;
                         border-radius:.375rem;cursor:pointer;font-size:.875rem;">
                  Approve
                </button>
              </td>
            </tr>"""

    pending_count = len(pending)
    api_base = f"{_BRAIN_URL}/api/admin/tasks"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Adeline — Canonical Review</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: system-ui, sans-serif; background: #f9fafb; color: #111827; }}
    header {{ background: #111827; color: #f9fafb; padding: 1rem 2rem;
              display: flex; align-items: center; gap: 1rem; }}
    header h1 {{ font-size: 1.25rem; font-weight: 600; }}
    header span {{ font-size: .875rem; color: #9ca3af; }}
    .badge {{ background: #dc2626; color: #fff; border-radius: 9999px;
              padding: .125rem .5rem; font-size: .75rem; font-weight: 700; }}
    main {{ max-width: 1100px; margin: 2rem auto; padding: 0 1rem; }}
    h2 {{ font-size: 1.1rem; font-weight: 600; margin-bottom: 1rem; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff;
             border-radius: .5rem; overflow: hidden;
             box-shadow: 0 1px 3px rgba(0,0,0,.1); }}
    thead {{ background: #f3f4f6; }}
    th {{ padding: .75rem 1rem; text-align: left; font-size: .8rem;
          font-weight: 600; color: #6b7280; text-transform: uppercase;
          letter-spacing: .05em; }}
    tr {{ border-bottom: 1px solid #f3f4f6; }}
    tr:last-child {{ border-bottom: none; }}
    .toast {{ position: fixed; bottom: 1.5rem; right: 1.5rem;
              background: #111827; color: #fff; padding: .75rem 1.25rem;
              border-radius: .5rem; font-size: .875rem;
              opacity: 0; transition: opacity .3s; pointer-events: none; }}
    .toast.show {{ opacity: 1; }}
  </style>
</head>
<body>
  <header>
    <h1>Adeline — Canonical Review</h1>
    <span>Pending approval</span>
    <span class="badge">{pending_count}</span>
  </header>
  <main>
    <h2>Pending Canonicals</h2>
    <table>
      <thead>
        <tr>
          <th>Topic</th><th>Track</th><th>Reason</th><th>Updated</th><th>Action</th>
        </tr>
      </thead>
      <tbody id="tbody">
        {rows_html}
      </tbody>
    </table>
  </main>
  <div class="toast" id="toast"></div>
  <script>
    function toast(msg, ok) {{
      const el = document.getElementById('toast');
      el.textContent = msg;
      el.style.background = ok ? '#16a34a' : '#dc2626';
      el.classList.add('show');
      setTimeout(() => el.classList.remove('show'), 3000);
    }}
    async function approve(slug, btn) {{
      btn.disabled = true;
      btn.textContent = 'Approving…';
      try {{
        const r = await fetch(`{api_base}/canonicals/${{slug}}/approve`, {{
          method: 'POST',
          headers: {{ 'Authorization': 'Bearer ' + getToken() }},
        }});
        if (r.ok) {{
          document.getElementById('row-' + slug).remove();
          toast('✓ Approved: ' + slug, true);
        }} else {{
          const e = await r.json();
          toast('Error: ' + (e.detail || r.status), false);
          btn.disabled = false; btn.textContent = 'Approve';
        }}
      }} catch(e) {{
        toast('Network error', false);
        btn.disabled = false; btn.textContent = 'Approve';
      }}
    }}
    function getToken() {{
      // Pull JWT from cookie 'sb-access-token' or localStorage
      const cookie = document.cookie.split(';').find(c => c.trim().startsWith('sb-access-token='));
      if (cookie) return cookie.split('=')[1];
      return localStorage.getItem('sb-access-token') || '';
    }}
  </script>
</body>
</html>"""
    return HTMLResponse(content=html)
