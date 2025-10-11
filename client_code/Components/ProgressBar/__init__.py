from ._anvil_designer import ProgressBarTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables


class ProgressBar(ProgressBarTemplate):
  def __init__(self, **properties):
    
    self.init_components(**properties)
    self.min_value = -100
    self.max_value = 100
    self.value = 0
    self.zero_offset = 0 # Offset from center, if needed
    self.update_progress_bar()
    

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

  # def update_progress_bar(self):
  #   """Calculates and sets the width of the positive and negative bars."""
  #   # try:
  #   #   print(self.value,self.min_value,self.max_value)
  #   # except:
  #   #   print("not working")
  #   try:
  #     value = self.value
  #     min_v = self.min_value
  #     max_v = self.max_value
  #     z_o = self.zero_offset
  #     print("using real-value",self.value,self.min_value)
  #   except:
  #     print("using fail-safe")
  #     value = 0
  #     min_v = -100
  #     max_v = 100
  #     z_o = 0
      
  #   if value is None or min_v is None or max_v is None:
  #     # Safely get the DOM nodes and set width
  #     self.dom_nodes["progress-bar-positive"].style.width = "0%"
  #     self.dom_nodes["progress-bar-negative"].style.width = "0%"
  #     return

  #   # Ensure value stays within bounds
  #   value = max(min_v, min(max_v, value))
      
  #   # Access HTML elements via dom_nodes dictionary
  #   positive_bar = self.dom_nodes["progress-bar-positive"]
  #   negative_bar = self.dom_nodes["progress-bar-negative"]

  #   if value >= 0:
  #     positive_range = max_v
  #     percent = (value / positive_range) if positive_range != 0 else 0
  #     positive_bar.style.width = f"{percent * 50}%"
  #     negative_bar.style.width = "0%"
  #   else:
  #     negative_range = abs(min_v)
  #     print("range-test:",negative_range,min_v)
  #     percent = (abs(value) / negative_range) if negative_range != 0 else 0
  #     negative_bar.style.width = f"{percent * 50}%"
  #     positive_bar.style.width = "0%"

  #   self.refresh_data_bindings()

  def update_progress_bar(self):
    """Calculates and sets the width of the positive and negative bars."""
    try:
      value = self.value
      min_v = self.min_value
      max_v = self.max_value
      z_o = self.zero_offset
    except:
      value = 0
      min_v = -100
      max_v = 100
      z_o = 0

    positive_bar = self.dom_nodes["progress-bar-positive"]
    negative_bar = self.dom_nodes["progress-bar-negative"]
    value_label = self.dom_nodes["progress-value-label"]

    if value is None or min_v is None or max_v is None or min_v >= max_v:
      # Hide both bars if the range is invalid or not set
      positive_bar.style.width = "0%"
      negative_bar.style.width = "0%"
      value_label.text = ""
      return

    # Ensure value stays within bounds
    value = max(min_v, min(max_v, value))
    # Format the currency value for the label
    # Use an f-string for formatting: 'R {value:,.2f}' will add commas for thousands and 2 decimal places
    value_label.text = f"R {value:,.2f}" 

    if min_v >= 0:
      # Case: Range is entirely non-negative (e.g., 0 to 100)
      # Bar starts from the far left
      positive_bar.style.left = "0%"
      negative_bar.style.width = "0%"

      total_range = max_v - min_v
      if total_range == 0:
        percent = 0
      else:
        percent = (value - min_v) / total_range

      positive_bar.style.width = f"{percent * 100}%"
    else:
      # Case: Range includes negative values (e.g., -50 to 100)
      # Bar expands from the zero point
      total_range = max_v - min_v

      if value >= 0:
        positive_bar.style.left = f"{abs(min_v) / total_range * 100}%"
        positive_bar.style.width = f"{(value / total_range) * 100}%"
        negative_bar.style.width = "0%"
      else:
        negative_bar.style.right = f"{max_v / total_range * 100}%"
        negative_bar.style.width = f"{(abs(value) / total_range) * 100}%"
        positive_bar.style.width = "0%"

    self.refresh_data_bindings()
    
