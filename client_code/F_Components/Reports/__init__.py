from ._anvil_designer import ReportsTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from ...F_Global_Logic import Global,Reporting
import anvil.js



class Reports(ReportsTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)

    # --- Dropdown: available visuals (for now) ---
    self._visuals = [
      "Accounts Overview",
      "Category Pie",
      "Category Variance",
      "Category Variance + Income",
    ]
    self.drop_down_1.items = self._visuals

    # default selection
    self.drop_down_1.selected_value = "Accounts Overview"

    # --- Slider setup (Anvil Extras Slider) ---
    # We treat it as discrete stops 0..5.
    # (Exact property names may differ slightly depending on your Slider dep,
    # but value changes will still come through as slider_1.value)
    try:
      self.slider_1.min = 0
      self.slider_1.max = 5
      self.slider_1.step = 1
      self.slider_1.value = 0
    except Exception:
      # If the dep uses different property names, at least force a sane default.
      self.slider_1.value = 0

    # Label reflects current slider selection
    self._update_slider_label()

    # Render default visual immediately
    self._render_selected_visual()


  # ----------------------------
  # UI helpers
  # ----------------------------

  
  def _update_slider_label(self):
    v = int(self.slider_1.value or 0)
    self.label_1.text = Reporting.slider_label(v)

  def _current_range(self):
    v = int(self.slider_1.value or 0)
    return Reporting.slider_date_range(v)

  def _clear_output(self):
    # Remove everything inside the output panel
    for c in list(self.column_panel_1.get_components()):
      c.remove_from_parent()

  def _render_plot_component(self, plot_component):
    self._clear_output()
    self.column_panel_1.add_component(plot_component, full_width_row=True)

  def _render_selected_visual(self):
    start, end = self._current_range()
    selected = self.drop_down_1.selected_value

    if selected == "Accounts Overview":
      plot = Reporting.accounts_overview_plot(start, end, height=500)
      self._render_plot_component(plot)

    elif selected == "Category Pie":
      plot = Reporting.category_pie_plot(start, end, height=500)
      self._render_plot_component(plot)

    elif selected == "Category Variance":
      plot = Reporting.category_variance_plot(start, end, height=500)
      self._render_plot_component(plot)

    elif selected == "Category Variance + Income":
      plot = Reporting.category_variance_plus_income_plot(start, end, height=500)
      self._render_plot_component(plot)

    else:
      self._clear_output()
      self.column_panel_1.add_component(
        Label(text=f"Unknown visual: {selected}", align="center"),
        full_width_row=True
      )


  # ----------------------------
  # Event handlers
  # ----------------------------

  @handle('slider_1','change')
  def slider_1_change(self, **event_args):
    self._update_slider_label()
    self.button_1_click()
    # UX: don’t auto-rebuild on slide unless you want it.
    # For now: just update label. Button triggers render.
    # If you want live-update later: call self._render_selected_visual()

  @handle('drop_down_1','change')
  def drop_down_1_change(self, **event_args):
    # optional: keep UI ready; still render only on button click
    self.button_1_click()

  @handle('button_1','click')
  def button_1_click(self, **event_args):
    self._render_selected_visual()
