from ._anvil_designer import one_transaction_mobileTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from ....F_Global_Logic import Global,Transaction


class one_transaction_mobile(one_transaction_mobileTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    self.checked = False
    self.LONG_MS = 450
    self.MOVE_PX = 10

  def extra_layout(self,**event_args):
    for a in Global.ACCOUNTS:
      if self.item['account'] == a[1]:
        self.lbl_account.text = a[0]
        break
    if self.lbl_account.text == '':
      self.lbl_account.text = 'No Account'
    if self.item['category']:
      self.lbl_category.text = Global.CATEGORIES[self.item['category']]['display']
    else:
      self.lbl_category.text = "None"

  def set_bg(self,odd,**event_args):
    objs = [self.card_1,self.lbl_account,self.lbl_date,self.lbl_amount,self.lbl_category,
           self.lbl_description]
    for obj in objs:
      if odd:
        obj.background = "#2B383E"
      else:
        obj.background = "#595A3B"
      if self.checked:
        self.card_1.role = 'txn-card-mobile-selected' #can be deleted/amended for transfer
      else:
        self.card_1.role = 'txn-card-mobile'
    if self.item['amount'] < 0:
      self.lbl_amount.foreground = 'theme:Amount Negative'
    if self.item['category'] == None:
      self.lbl_category.background = 'theme:Amount Negative'
    else:
      self.lbl_category.background = Global.CATEGORIES[self.item['category']]['colour']

  def am_i_smart(self,**event_args):
    if not self.item['category']:
      """
      What we're doing here is setting an automated category in name only on the link,
      but leaving the item[cat] empty. This eliminates potentially unnecessary server
      trips. BUT. Categorising on budget page will require some tricky effort
      """
      auto_id = Global.is_it_smart(self.item['description'])
      if auto_id:
        self.lbl_category.text = Global.CATEGORIES[auto_id]['display']
        c = Global.CATEGORIES[auto_id]['colour']
        self.lbl_category.border = "solid {b} 1px".format(b=c)
        self.lbl_category.background = ''
        self.lbl_category.bold = True
        self.lbl_category.foreground = 'theme:Amount Negative'

  @handle("", "show")
  def form_show(self, **event_args):
    # first do some extras:
    self.extra_layout()
    self.start_listening()

  def start_listening(self, **event_args):
    # Attach only once per form instance
    if getattr(self, "_press_handlers_attached", False):
      return
    self._press_handlers_attached = True
  
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
        self.checked = not self.checked
        Global.Transactions_Form.rake_page()
  
      def do_double_tap():
        # Double-tap behavior (open/edit) — replace later with your popup
        from ....F_PopUps.category_selector import category_selector
        c = None
        if self.lbl_category.text != "None":
          c = self.lbl_category.text 
        cat_name = alert(category_selector(self.item['description'],c),buttons=[],large=False)
        if cat_name:
          self.item['category'] = next((k for k, v in Global.CATEGORIES.items() if v.get('display') == cat_name), None)
          self.lbl_category.text = cat_name
          Transaction.work_transaction_data('update',self.item)
          Global.Transactions_Form.load_me(Global.Transactions_Form.dash)
        
  
      def do_long_press():
        alert("LONG PRESS (open/edits")  # (keep for testing)
        # e.g. self.raise_event("x-open", txn_id=self.item["id"])
  
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
