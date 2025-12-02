from ._anvil_designer import budget_glancesTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from .... import Global
from datetime import date


class budget_glances(budget_glancesTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run before the form opens.

  def form_show(self, **event_args):
    self.a = 0
    self.b = 0
    period = date(Global.PERIOD[1], Global.PERIOD[0], 1)
    budg = anvil.get_open_form().content_panel.get_components()[0]
    # get budget
    try:
      self.b = [b for b in budg.all_budgets if b['belongs_to'] == self.item['sub_category_id'] and b['period'] == period][0]['budget_amount']
    except Exception as e:
      print("no budget amount set",e)
    # get actual
    self.a = get_open_form().content_panel.get_components()[0].get_actual(self.item['sub_category_id'])
    # budget incl roll-over will be obtained in the below function
    self.update_the_show()

  def update_the_show(self,**event_args):
    #we have to do roll-over calc here, because a budget update is cool but must update roll-over
    budg = anvil.get_open_form().content_panel.get_components()[0]
    try:
      if self.b != budg.roll_over_calc(id=self.item['sub_category_id']):
        self.budget.underline = True
      else:
        self.budget.underline = False
    except:
      print("Sub category line 44:",self.item,'\n',self.b)
    bar_b = budg.roll_over_calc(id=self.item['sub_category_id'])
    self.budget.text = "({b:.2f})".format(b=-self.b/100) if self.b < 0 else "{b:.2f}".format(b=self.b/100)
    self.budget.foreground = 'theme:Amount Negative' if self.b < 0 else ''
    self.budget_edit.text = float(self.b/100)
    a_t = "(R {actual:.2f})".format(actual=-self.a) if self.a < 0 else "R {actual:.2f}".format(actual=self.a)
    self.actual.text,self.actual_edit.text = a_t,a_t
    self.actual.foreground = 'theme:Amount Negative' if self.a < 0 else ''
    self.actual_edit.foreground = 'theme:Amount Negative' if self.a < 0 else ''
    self.update_bars(bar_b/100,self.a)

  def update_bars(self,b,a,**event_args):
    #income bars are different
    maxi,min,v = 0,0,0
    if get_open_form().content_panel.get_components()[0].is_income(self.item['belongs_to']):
      self.progress_bar_1.min_value = 0
      self.progress_bar_1_edit.min_value = 0
      self.progress_bar_1.max_value = max(b,a)
      self.progress_bar_1_edit.max_value = max(b,a)
      self.progress_bar_1.value = a
      self.progress_bar_1_edit.value = a
    else:
      # if still have budget, set a standard zero point at 25% of the bar.
      # if budget exceeded, set equal min point to max, zero halfway
      # if spend exceeds double of budget, set zero at 75%
      if a >= b and b != 0:
        maxi = -b
        min = b/4
        v = -(b-a)
      elif a < b and a >= 2*b:
        maxi = -b
        min = b
        v = a - b
      elif a < b and a < 2*b:
        maxi = -a/4
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
      self.progress_bar_1.min_value,self.progress_bar_1_edit.min_value = min,min
      self.progress_bar_1.max_value,self.progress_bar_1_edit._max_value = maxi,maxi
      self.progress_bar_1.value,self.progress_bar_1_edit.value = v,v
      self.progress_bar_1.refresh_data_bindings()