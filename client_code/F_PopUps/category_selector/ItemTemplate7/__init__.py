from ._anvil_designer import ItemTemplate7Template
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables


class ItemTemplate7(ItemTemplate7Template):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    

  @handle("", "show")
  def form_show(self, **event_args):
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
        
        print(self.item)
        # self.raise_event('x-close-alert',value=self.item)
        self.parent.raise_event('x-close-up-shop',cat=self.item)
        # print('fired-template')

      def do_double_tap():
        # Double-tap behavior (open/edit) — replace later with your popup
        # alert("DOUBLE TAP (open/edit)")
        # e.g. self.raise_event("x-open", txn_id=self.item["id"])
        pass

      def do_long_press():
        # alert("LONG PRESS (open/edits")  # (keep for testing)
        # e.g. self.raise_event("x-open", txn_id=self.item["id"])
        pass

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


    
