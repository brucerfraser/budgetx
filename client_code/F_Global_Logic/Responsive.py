import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
# client_code/F_Global_Logic/Responsive.py
import anvil.js

# Breakpoints (match your theme’s existing ~998px mobile switch)
PHONE_MAX = 480
MOBILE_MAX = 998


def viewport_width(default=1200) -> int:
  """Current viewport width in px (safe fallback)."""
  try:
    w = int(anvil.js.window.innerWidth)
    return w if w > 0 else default
  except Exception:
    return default


def viewport_height(default=800) -> int:
  """Current viewport height in px (safe fallback)."""
  try:
    h = int(anvil.js.window.innerHeight)
    return h if h > 0 else default
  except Exception:
    return default


def is_phone() -> bool:
  """True for phone-sized layouts."""
  return viewport_width() <= PHONE_MAX


def is_mobile() -> bool:
  """True for mobile/tablet-ish widths (includes phone)."""
  return viewport_width() <= MOBILE_MAX


def mode() -> str:
  """
  Returns: "phone" | "mobile" | "desktop"
  - phone  : <= PHONE_MAX
  - mobile : <= MOBILE_MAX
  - desktop: >  MOBILE_MAX
  """
  w = viewport_width()
  if w <= PHONE_MAX:
    return "phone"
  if w <= MOBILE_MAX:
    return "mobile"
  return "desktop"


def on_resize(handler, call_immediately=False):
  """
  Register a resize/orientation handler.
  Returns the internal callback so you can remove it later if needed.

  handler: callable (no-arg preferred; if it accepts 1 arg, it will receive the JS event)
  """
  win = anvil.js.window

  def _cb(evt=None):
    try:
      handler()
    except TypeError:
      handler(evt)

  win.addEventListener("resize", _cb)
  win.addEventListener("orientationchange", _cb)

  if call_immediately:
    _cb()

  return _cb


def remove_resize_listener(callback):
  """Remove a callback returned by on_resize()."""
  win = anvil.js.window
  try:
    win.removeEventListener("resize", callback)
    win.removeEventListener("orientationchange", callback)
  except Exception:
    pass
