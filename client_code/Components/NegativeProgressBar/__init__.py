from ._anvil_designer import NegativeProgressBarTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables


class NegativeProgressBar(NegativeProgressBarTemplate):
  def __init__(self,**properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    from anvil import *

class ProgressBarZero(ProgressBarZeroTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.zero_offset = 0 # Offset from center, if needed

  @property
  def value(self):
    return self._value

  @value.setter
  def value(self, val):
    self._value = val
    self.update_progress_bar()

  @property
  def min_value(self):
    return self._min_value

  @min_value.setter
  def min_value(self, val):
    self._min_value = val
    self.update_progress_bar()

  @property
  def max_value(self):
    return self._max_value

  @max_value.setter
  def max_value(self, val):
    self._max_value = val
    self.update_progress_bar()

  def update_progress_bar(self):
    """Calculates and sets the width of the positive and negative bars."""
    value = self.value
    min_v = self.min_value
    max_v = self.max_value

    if value is None or min_v is None or max_v is None:
      self.progress_bar_positive.get_dom_node().style.width = "0%"
      self.progress_bar_negative.get_dom_node().style.width = "0%"
      return

    total_range = max_v - min_v
    zero_point = abs(min_v) / total_range
    current_position = (value - min_v) / total_range

    if value >= 0:
      positive_percent = (value / max_v) if max_v != 0 else 0
      self.progress_bar_positive.get_dom_node().style.width = f"{positive_percent * 50 + self.zero_offset}%"
      self.progress_bar_negative.get_dom_node().style.width = "0%"
    else:
      negative_percent = (abs(value) / abs(min_v)) if min_v != 0 else 0
      self.progress_bar_negative.get_dom_node().style.width = f"{negative_percent * 50 - self.zero_offset}%"
      self.progress_bar_positive.get_dom_node().style.width = "0%"

    self.refresh_data_bindings()
