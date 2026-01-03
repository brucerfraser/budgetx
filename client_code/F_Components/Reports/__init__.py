from ._anvil_designer import ReportsTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from ..Reports_mini import Reports_mini
from ...F_Global_Logic import Global
import anvil.js

LONG_MS = 450

class Reports(ReportsTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    self.cp_reports.add_component(Reports_mini(full_screen=True))

  @handle("", "show")
  def form_show(self, **event_args):
  # Attach only once per form instance
    if getattr(self, "_press_handlers_attached", False):
      return
    self._press_handlers_attached = True

    def attach():
      el = anvil.js.get_dom_node(self)

      self._press_timer = None
      self._long_fired = False

      def clear_timer():
        if self._press_timer is not None:
          anvil.js.window.clearTimeout(self._press_timer)
          self._press_timer = None

      def start_press(evt=None):
        clear_timer()
        self._long_fired = False

        def fire():
          self._long_fired = True
          alert("Works LONG")

        self._press_timer = anvil.js.window.setTimeout(fire, LONG_MS)

      def end_press(evt=None):
        clear_timer()
        if not self._long_fired:
          alert("Works SHORT")

      # ✅ One set of events for both desktop + mobile
      el.addEventListener("pointerdown", start_press)
      el.addEventListener("pointerup", end_press)
      el.addEventListener("pointercancel", end_press)

    # ✅ ensure DOM exists before binding
    anvil.js.window.setTimeout(attach, 0)
