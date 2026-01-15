from ._anvil_designer import Category_holder_mobileTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from datetime import date
from ....F_Global_Logic import BUDGET
import anvil.js


class Category_holder_mobile(Category_holder_mobileTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    self.opened = False

  @handle('btw_add_subcat','click')
  def link_2_click(self, **event_args):
    from ....F_PopUps.work_a_category import work_a_category

    c = work_a_category(cat=False)
    result = alert(
      c,
      title="Add a sub-category to {cat}".format(cat=self.item["name"]),
      buttons=[],
      large=True,
    )
    if result:
      result["belongs_to"] = self.item["category_id"]
      for a in ["colour_back", "colour_text"]:
        del result[a]
      BUDGET.update_budget('add_sub_cat',result)
      # both app_tables and all_sub_cats updated
      if self.link_1.icon == "fa:angle-down":
        self.repeating_panel_1.items = sorted([sc for sc in BUDGET.all_sub_cats if sc['belongs_to'] == self.item['category_id'] and sc['order'] >= 0],
                                              key=lambda x: x['order'])
        odd = False
        for sc in self.repeating_panel_1.get_components():
          if odd:
            sc.background = "grey"
          odd = not odd

  def refresh_sub_cats(self, **event_args):
    frm = get_open_form().content_panel.get_components()[0]
    edit, edit_id = False, None
    for sc in self.repeating_panel_1.get_components():
      edit = True if sc.item["sub_category_id"] == frm.category_right else False
      if edit:
        edit_id = frm.category_right
        break
    item_list = []
    for line in BUDGET.all_sub_cats:
      try:
        if line["order"] >= 0:
          if line["belongs_to"] == self.item["category_id"]:
            item_list.append(line)
      except Exception as e:
        print("cat holder line 55", line, e)
    item_list = sorted(item_list, key=lambda i: i["order"])
    self.repeating_panel_1.items = item_list
    odd = False
    for sc in self.repeating_panel_1.get_components():
      if odd:
        sc.background = "grey"
      odd = not odd
    # if edit:
    #   for sc in self.repeating_panel_1.get_components():
    #     if sc.item['sub_category_id'] == edit_id:
    #       sc.link_1_click()

    #       break

  def link_1_click(self, **event_args):
    if self.link_1.icon == "fa:angle-right":
      self.repeating_panel_1.items = sorted([sc for sc in BUDGET.all_sub_cats if sc['belongs_to'] == self.item['category_id'] and sc['order'] >= 0],
                                            key=lambda x: x['order'])

      self.link_1.icon = "fa:angle-down"
      self.repeating_panel_1.visible = True
    else:
      self.link_1.icon = "fa:angle-right"
      self.repeating_panel_1.visible = False

    # Send detail to RH Panel
    frame = anvil.get_open_form()
    budg = frame.content_panel.get_components()[0]
    today = date.today()
    period = date(today.year, today.month, 1)
    budg.load_category_right(self.item["category_id"], period, True)
    # Make all other sub_cats clickable again (links vis, edit invis)
    budg.reset_sub_categories("")

  def calculate_me(self, **event_args):
    print(self.opened)

  def form_show(self, **event_args):
    for obj in [self.name_label, self.budget, self.actual]:
      obj.foreground = self.item["colour_text"]
      self.cp_budget_cat.background = self.item["colour_back"]
    self.name_label.role = 'title'
    anvil.js.get_dom_node(self).classList.add("bx-cat-row")
    self.start_listening()
    

  def start_listening(self, **event_args):
    # Attach only once per form instance
    if getattr(self, "_press_handlers_attached", False):
      return
    self._press_handlers_attached = True
    # anvil.js.get_dom_node(self).classList.add("cat-row")
    def attach():
      el = anvil.js.get_dom_node(self.cp_budget_cat)

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
        if self.opened:
          # reload entire budget page
          get_open_form().budget_page_link_click()
        else:
          budg = get_open_form().content_panel.get_components()[0]
          budg.animate_open_category(category_id=self.item["category_id"])
        

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

  
