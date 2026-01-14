from ._anvil_designer import Sub_category_mobileTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from datetime import date
from .....F_Global_Logic import BUDGET
from .....F_Global_Logic import Global


class Sub_category_mobile(Sub_category_mobileTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    self.txt_edit_budget = None
    self.a = 0
    self.b = 0

  def form_show(self, **event_args):
    self.a = 0
    self.b = 0
    period = date(Global.PERIOD[1], Global.PERIOD[0], 1)
    # get budget
    try:
      self.b = [
        b
        for b in BUDGET.all_budgets
        if b["belongs_to"] == self.item["sub_category_id"] and b["period"] == period
      ][0]["budget_amount"]
    except Exception as e:
      print("no budget amount set", e)
    # get actual
    self.a = BUDGET.get_actual(self.item["sub_category_id"])
    # budget incl roll-over will be obtained in the below function
    self.update_the_show()
    self.bg_set()
    self.start_listening()

  def update_the_show(self, **event_args):
    # we have to do roll-over calc here, because a budget update is cool but must update roll-over
    try:
      if self.b != BUDGET.roll_over_calc(id=self.item["sub_category_id"]):
        self.budget.underline = True
      else:
        self.budget.underline = False
    except:
      print("Sub category line 44:", self.item, "\n", self.b)
    bar_b = BUDGET.roll_over_calc(id=self.item["sub_category_id"])
    self.budget.text = (
      "({b:.2f})".format(b=-self.b / 100)
      if self.b < 0
      else "{b:.2f}".format(b=self.b / 100)
    )
    self.budget.foreground = "theme:Amount Negative" if self.b < 0 else ""
    a_t = (
      "(R {actual:.2f})".format(actual=-self.a)
      if self.a < 0
      else "R {actual:.2f}".format(actual=self.a)
    )
    self.actual.text = a_t
    self.actual.foreground = "theme:Amount Negative" if self.a < 0 else ""
    self.update_bars(bar_b / 100, self.a)

  def update_bars(self, b, a, **event_args):
    # income bars are different
    maxi, min, v = 0, 0, 0
    if BUDGET.is_income(self.item["belongs_to"]):
      self.progress_bar_1.min_value = 0
      self.progress_bar_1.max_value = max(b, a)
      self.progress_bar_1.value = a
    else:
      # if still have budget, set a standard zero point at 25% of the bar.
      # if budget exceeded, set equal min point to max, zero halfway
      # if spend exceeds double of budget, set zero at 75%
      if a >= b and b != 0:
        maxi = -b
        min = b / 4
        v = -(b - a)
      elif a < b and a >= 2 * b:
        maxi = -b
        min = b
        v = a - b
      elif a < b and a < 2 * b:
        maxi = -a / 4
        min = a
        v = a
      elif a == 0 and b == 0:
        maxi = 10.0
        min = -10.0
        v = 0.0
      else:
        maxi = 10.0
        min = -10.0
        v = 0.0
      self.progress_bar_1.min_value = min
      self.progress_bar_1.max_value = maxi
      self.progress_bar_1.value = v
      self.progress_bar_1.refresh_data_bindings()

  def budget_edit_lost_focus(self, **event_args):
    period = date(Global.PERIOD[1], Global.PERIOD[0], 1)
    budg = anvil.get_open_form().content_panel.get_components()[0]
    self.budget_edit.text = BUDGET.neg_pos(
      self.budget_edit.text, self.item["belongs_to"]
    )
    self.b = self.budget_edit.text * 100
    try:
      app_tables.budgets.get(period=period, belongs_to=self.item["sub_category_id"])[
        "budget_amount"
      ] = self.b
    except:
      app_tables.budgets.add_row(
        belongs_to=self.item["sub_category_id"], period=period, budget_amount=self.b
      )
    BUDGET.update_a_budget(self.b, period, self.item["sub_category_id"])
    self.a = BUDGET.get_actual(self.item["sub_category_id"])
    self.update_the_show()
    budg.update_numbers()
    self.edit_column_panel.visible = False
    self.link_1.visible = True

  def edit_me(self, **event_args):
    # Fire something to budget form for RH panel.
    frame = anvil.get_open_form()
    budg = frame.content_panel.get_components()[0]
    today = date.today()
    period = date(today.year, today.month, 1)
    budg.load_category_right(
      self.item["sub_category_id"], period, False, self.item["belongs_to"]
    )
    # Make all other sub_cats clickable again (links vis, edit invis)
    budg.reset_sub_categories(self.item["sub_category_id"])

    # Edit column_panel becomes visual.
    self.edit_column_panel.visible = True
    self.link_1.visible = False
    self.budget_edit.focus()
    self.budget_edit.select()

  def bg_set(self, **event_args):
    col = [c for c in BUDGET.all_cats if c['category_id'] == self.item['belongs_to']][0]['colour_back']
    self.card_1.border = 'solid {c} 1px'.format(c=col)
    # self.current_column_panel.background = "theme:Secondary Container"
    # self.edit_column_panel.background = "theme:Secondary Container"

  def budget_edit_start(self,**event_args):
    if self.txt_edit_budget:
      self.budget_edit_finish()
    else:
      t = self.b/100 if self.b else None
      self.txt_edit_budget = TextBox(placeholder="Enter budget",
                                     text=t,type='number')
      self.txt_edit_budget.set_event_handler('change',self.budget_edit_change)
      self.txt_edit_budget.set_event_handler('pressed_enter',self.budget_edit_finish)
      self.txt_edit_budget.set_event_handler('lost_focus',self.budget_edit_finish)
      self.flow_panel_1.add_component(self.txt_edit_budget)
      self.budget.visible = False
      self.txt_edit_budget.select()
    
  
  def budget_edit_update(self, **event_args):
    self.a = BUDGET.get_actual(self.item["sub_category_id"])
    self.b = self.txt_edit_budget.text * 100
    if BUDGET.is_income(self.item["belongs_to"]):
      if self.b < 0:
        self.b = self.b * -1
    else:
      if self.b > 0:
        self.b = self.b * -1
    self.budget.text = (
      "({b:.2f})".format(b=-self.b / 100)
      if self.b < 0
      else "{b:.2f}".format(b=self.b / 100)
    )
    self.update_bars(self.b, self.a)

  def budget_edit_change(self,**event_args):
    self.budget_edit_update()

  def budget_edit_finish(self,**event_args):
    self.budget_edit_update()
    self.txt_edit_budget.remove_from_parent()
    self.budget.visible = True
    self.txt_edit_budget = None


  def actual_click(self, **event_args):
    """We need to call a pop-up"""
    fd, ld = BUDGET.date_me(False)
    Global.Transactions_Form.remove_from_parent()
    Global.Transactions_Form.dash = False
    Global.Transactions_Form.sub_cat = ("category", self.item["sub_category_id"])
    trigger = alert(
      Global.Transactions_Form,
      title="{c} transactions for {f} to {l}".format(
        c=Global.CATEGORIES[self.item["sub_category_id"]]["display"], f=fd, l=ld
      ),
      buttons=[("Done", False), ("Go to Transactions", True)],
      large=True,
    )
    if trigger:
      Global.Transactions_Form.remove_from_parent()
      Global.Transactions_Form.sub_cat = None
      get_open_form().transactions_page_link_click()

  def start_listening(self, **event_args):
    # Attach only once per form instance
    if getattr(self, "_press_handlers_attached", False):
      return
    self._press_handlers_attached = True
    # anvil.js.get_dom_node(self).classList.add("cat-row")
    def attach():
      el = anvil.js.get_dom_node(self)

      # --- Gesture state ---
      self._press_timer = None
      self._long_fired = False
      self._moved = False
      self._start_x = None
      self._start_y = None

      # --- Double-tap state ---
      self._last_tap_ms = 0
      self._tap_timer = None  # used to delay single-tap action until we know it's not a double-tap

      # Tuning knobs
      LONG_MS = getattr(self, "LONG_MS", 450)
      MOVE_PX = getattr(self, "MOVE_PX", 10)
      DOUBLE_TAP_MS = getattr(self, "DOUBLE_TAP_MS", 300)  # max gap between taps
      SINGLE_TAP_DELAY_MS = getattr(self, "SINGLE_TAP_DELAY_MS", 220)  # wait briefly to detect 2nd tap

      def clear_press_timer():
        if self._press_timer is not None:
          anvil.js.window.clearTimeout(self._press_timer)
          self._press_timer = None

      def clear_tap_timer():
        if self._tap_timer is not None:
          anvil.js.window.clearTimeout(self._tap_timer)
          self._tap_timer = None

      def get_xy(evt):
        try:
          return evt["clientX"], evt["clientY"]
        except Exception:
          return None, None

      def now_ms():
        # Anvil-safe access to high-res clock
        try:
          return int(anvil.js.window.performance.now())
        except Exception:
          return int(anvil.js.Date.new().getTime())

      def do_single_tap():
        # Your existing single-tap behavior (toggle selection)
        if not self.txt_edit_budget:
          self.budget_edit_start()
        
        


      def do_double_tap():
        # Double-tap behavior (open/edit) — replace later with your popup
        Notification("Double Tap").show()


      def do_long_press():
        Notification("Long Press").show()

      def start_press(evt=None):
        clear_press_timer()
        self._long_fired = False
        self._moved = False

        x, y = get_xy(evt)
        self._start_x, self._start_y = x, y

        def fire():
          # Only fire long-press if we haven't scrolled/moved
          if self._moved or self._long_fired:
            return
          self._long_fired = True
          clear_tap_timer()  # don't allow pending single-tap after a long press
          do_long_press()

        self._press_timer = anvil.js.window.setTimeout(fire, LONG_MS)

      def move_press(evt=None):
        if self._start_x is None or self._start_y is None:
          return

        x, y = get_xy(evt)
        if x is None or y is None:
          return

        if abs(x - self._start_x) > MOVE_PX or abs(y - self._start_y) > MOVE_PX:
          self._moved = True
          clear_press_timer()  # cancel pending long-press once user scrolls

      def end_press(evt=None):
        clear_press_timer()

        # If user scrolled, treat as scroll (no tap)
        if self._moved:
          return

        # If long already fired, do nothing
        if self._long_fired:
          return

        # --- Tap / Double-tap logic ---
        t = now_ms()
        gap = t - self._last_tap_ms

        if gap <= DOUBLE_TAP_MS:
          # It's a double-tap
          self._last_tap_ms = 0
          clear_tap_timer()
          do_double_tap()
          return

        # Potential first tap: delay single-tap slightly to see if 2nd tap arrives
        self._last_tap_ms = t
        clear_tap_timer()

        def fire_single():
          # If another tap came in, _last_tap_ms would have been reset above
          if self._last_tap_ms == t:
            self._last_tap_ms = 0
            do_single_tap()

        self._tap_timer = anvil.js.window.setTimeout(fire_single, SINGLE_TAP_DELAY_MS)

      def cancel_press(evt=None):
        clear_press_timer()
        # if gesture is cancelled, don't keep a pending single-tap
        clear_tap_timer()

      # ✅ One set of events for both desktop + mobile
      el.addEventListener("pointerdown", start_press, {"passive": True})
      el.addEventListener("pointermove", move_press, {"passive": True})
      el.addEventListener("pointerup", end_press)
      el.addEventListener("pointercancel", cancel_press)

    # ✅ ensure DOM exists before binding
    anvil.js.window.setTimeout(attach, 0)
