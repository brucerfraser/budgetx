from ._anvil_designer import Dashboard_Screen_MobileTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from ...F_Global_Logic import Global
from ...F_Components.Budget_mini import Budget_mini
from ...F_Components.Reports_mini import Reports_mini


class Dashboard_Screen_Mobile(Dashboard_Screen_MobileTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    self.which_form = "dashboard"
    self.load_everything()
    if app_tables.settings.get(id="budget")["dash_variances"]:
      self.label_1_copy.text = "Chosen budget variances"
    else:
      self.label_1_copy.text = "Top 5 (worst) variances"

  def load_everything(self, **event_args):
    Global.Transactions_Form.dash = True
    Global.Transactions_Form.remove_from_parent()
    self.crd_trans_list.add_component(Global.Transactions_Form)
    self.link_budget.add_component(Budget_mini())
    self.link_report.add_component(Reports_mini())
    self.start_listening()

  def bottom_button_incoming(self,key,**event_args):
    if key == 'butt1':
      #info button
      alert("Information page will pop up in future")
  
  def link_budget_click(self, **event_args):
    get_open_form().ping_ping("budget")

  def link_report_click(self, **event_args):
    get_open_form().ping_ping("reports")

  def smart_cat_update(self, **event_args):
    Global.Transactions_Form.smart_cat_update()

  def start_listening(self,**event_args):
    # Attach only once per form instance
    if getattr(self, "_press_handlers_attached", False):
      return
    self._press_handlers_attached = True

    def attach():
      el = anvil.js.get_dom_node(self.crd_trans_list)

      # --- Gesture state ---
      self._press_timer = None
      self._long_fired = False
      self._moved = False
      self._start_x = None
      self._start_y = None

      # Tuning knobs
      LONG_MS = getattr(self, "LONG_MS", 450)
      MOVE_PX = getattr(self, "MOVE_PX", 10)

      def clear_timer():
        if self._press_timer is not None:
          anvil.js.window.clearTimeout(self._press_timer)
          self._press_timer = None

      def get_xy(evt):
        # Use dict-style access for Anvil JS proxy safety
        try:
          return evt["clientX"], evt["clientY"]
        except Exception:
          return None, None

      def start_press(evt=None):
        clear_timer()
        self._long_fired = False
        self._moved = False

        x, y = get_xy(evt)
        self._start_x, self._start_y = x, y

        def fire():
          # Only fire long-press if we haven't scrolled/moved
          if self._moved or self._long_fired:
            return
          self._long_fired = True
          # alert("Works LONG")   # replace with raise_event("x-open", ...) later

        self._press_timer = anvil.js.window.setTimeout(fire, LONG_MS)

      def move_press(evt=None):
        if self._start_x is None or self._start_y is None:
          return

        x, y = get_xy(evt)
        if x is None or y is None:
          return

        if abs(x - self._start_x) > MOVE_PX or abs(y - self._start_y) > MOVE_PX:
          self._moved = True
          clear_timer()  # cancel pending long-press once user scrolls

      def end_press(evt=None):
        clear_timer()

        # If user scrolled, treat as scroll (no tap)
        if self._moved:
          return

        # If long already fired, do nothing
        if self._long_fired:
          return

        # Otherwise it's a normal tap
        get_open_form().ping_ping("transactions")
        print("fired")

      def cancel_press(evt=None):
        clear_timer()

      # ✅ One set of events for both desktop + mobile
      # Passive down/move keeps scrolling smooth
      el.addEventListener("pointerdown", start_press, {"passive": True})
      el.addEventListener("pointermove", move_press, {"passive": True})
      el.addEventListener("pointerup", end_press)
      el.addEventListener("pointercancel", cancel_press)

    # ✅ ensure DOM exists before binding
    anvil.js.window.setTimeout(attach, 0)