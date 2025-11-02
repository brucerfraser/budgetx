from ._anvil_designer import date_pickerTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from ... import Global
import calendar
from datetime import date

class date_picker(date_pickerTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

  def form_show(self, **event_args):
    # get transaction start and end date:
    for row in app_tables.transactions.search(tables.order_by('date',ascending=True)):
      budget_x_first_date = row['date']
      break
    m = date.today().month
    y = date.today().year
    d = calendar.monthrange(y,m)[1]
    budget_x_last_date = date(y,m,d)

    """
      Generates a list of lists with month-year combos between two dates.
      
      Each inner list contains:
      [0] A text string in format "mmmm yy" (e.g., "November 25")
      [1] A tuple of (month number, year number) (e.g., (11, 2025))
      """
    result = []
    current_date = budget_x_first_date
    while current_date <= budget_x_last_date:
      # Format the string: %B is full month name, %y is two-digit year
      month_string = current_date.strftime("%B %Y")
      # Create the tuple (month number, year number)
      month_tuple = (current_date.month, current_date.year)
      # Append the inner list to the main result list
      result.append([month_string, month_tuple])
      # Move to the first day of the next month
      # relativedelta(months=+1) is the reliable way to increment months
      next = current_date.month + 1
      try:
        #If below doesn't work, we've gone to next year
        current_date = date(current_date.year, next,1)
      except:
        #go to next year
        next = current_date.year + 1
        current_date = date(next,1,1)
    self.drop_down_1.items = result
    self.drop_down_1.selected_value = Global.PERIOD
    if self.drop_down_1.selected_value == result[-1][1]:
      #selected is last month in drop down
      self.next.enabled = False
    else:
      self.next.enabled = True
    if self.drop_down_1.selected_value == result[0][1]:
      #selected is first month in drop down
      self.prev.enabled = False
    else:
      self.prev.enabled = True
    

  def drop_down_1_change(self, **event_args):
    m = self.drop_down_1.selected_value[0]
    y = self.drop_down_1.selected_value[1]
    Global.make_date(m,y)
    frame = anvil.get_open_form()
    frm = frame.content_panel.get_components()[0]
    frm.load_me(False)
    result = self.drop_down_1.items
    if self.drop_down_1.selected_value == result[-1][1]:
      #selected is last month in drop down
      self.next.enabled = False
    else:
      self.next.enabled = True
    if self.drop_down_1.selected_value == result[0][1]:
      #selected is first month in drop down
      self.prev.enabled = False
    else:
      self.prev.enabled = True

  def next_click(self, **event_args):
    result = self.drop_down_1.items
    i = 0
    for d in result:
      if d[1] == self.drop_down_1.selected_value:
        break
      else:
        i += 1
    self.drop_down_1.selected_value = result[i + 1][1]
    self.drop_down_1_change()

  def prev_click(self, **event_args):
    result = self.drop_down_1.items
    i = 0
    for d in result:
      if d[1] == self.drop_down_1.selected_value:
        break
      else:
        i += 1
    self.drop_down_1.selected_value = result[i - 1][1]
    self.drop_down_1_change()
    


    
