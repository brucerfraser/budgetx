from ._anvil_designer import Sub_categoryTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from datetime import date
from ..... import Global
from ..... import BUDGET



class Sub_category(Sub_categoryTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    
  def form_show(self, **event_args):
    self.a = 0
    self.b = 0
    period = date(Global.PERIOD[1], Global.PERIOD[0], 1)
    # get budget
    try:
      self.b = [b for b in BUDGET.all_budgets if b['belongs_to'] == self.item['sub_category_id'] and b['period'] == period][0]['budget_amount']
    except Exception as e:
      print("no budget amount set",e)
    # get actual
    self.a = BUDGET.get_actual(self.item['sub_category_id'])
    # budget incl roll-over will be obtained in the below function
    self.update_the_show()

  def update_the_show(self,**event_args):
    #we have to do roll-over calc here, because a budget update is cool but must update roll-over
    try:
      if self.b != BUDGET.roll_over_calc(id=self.item['sub_category_id']):
        self.budget.underline = True
      else:
        self.budget.underline = False
    except:
      print("Sub category line 44:",self.item,'\n',self.b)
    bar_b = BUDGET.roll_over_calc(id=self.item['sub_category_id'])
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
    if BUDGET.is_income(self.item['belongs_to']):
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
  
  def budget_edit_lost_focus(self, **event_args):
    period = date(Global.PERIOD[1], Global.PERIOD[0], 1)
    budg = anvil.get_open_form().content_panel.get_components()[0]
    self.budget_edit.text = BUDGET.neg_pos(self.budget_edit.text,
                                        self.item['belongs_to'])
    self.b = self.budget_edit.text * 100
    try:
      app_tables.budgets.get(period=period,
                              belongs_to=self.item['sub_category_id'])['budget_amount'] = self.b
    except:
      app_tables.budgets.add_row(belongs_to=self.item['sub_category_id'],
                              period=period,budget_amount=self.b)
    BUDGET.update_a_budget(self.b,period,self.item['sub_category_id'])
    self.a = BUDGET.get_actual(self.item['sub_category_id'])
    self.update_the_show()
    budg.update_numbers()
    self.edit_column_panel.visible = False
    self.link_1.visible = True

  def link_1_click(self, **event_args):
    # Fire something to budget form for RH panel.
    frame = anvil.get_open_form()
    budg = frame.content_panel.get_components()[0]
    today = date.today()
    period = date(today.year, today.month, 1)
    budg.load_category_right(self.item['sub_category_id'],period,False,self.item['belongs_to'])
    # Make all other sub_cats clickable again (links vis, edit invis)
    budg.reset_sub_categories(self.item['sub_category_id'])

    # Edit column_panel becomes visual.
    self.edit_column_panel.visible = True
    self.link_1.visible = False
    self.budget_edit.focus()
    self.budget_edit.select()
    

  def bg_set(self,**event_args):
    self.current_column_panel.background = 'theme:Secondary Container'
    self.edit_column_panel.background = 'theme:Secondary Container'

  def budget_edit_change(self, **event_args):
    self.a = BUDGET.get_actual(self.item['sub_category_id'])
    self.b = self.budget_edit.text
    if BUDGET.is_income(self.item['belongs_to']):
      if self.b < 0:
        self.b = self.b * -1
    else:
      if self.b > 0:
        self.b = self.b * -1
    self.update_bars(self.b,self.a)

  def actual_click(self, **event_args):
    """We need to call a pop-up"""
    fd,ld = BUDGET.date_me(False)
    Global.Transactions_Form.remove_from_parent()
    Global.Transactions_Form.dash = False
    Global.Transactions_Form.sub_cat = ('category',self.item['sub_category_id'])
    trigger = alert(Global.Transactions_Form,
                    title='{c} transactions for {f} to {l}'.format(c=Global.CATEGORIES[self.item['sub_category_id']]['display'],f=fd,l=ld),
                   buttons=[("Done",False),("Go to Transactions",True)],
                   large=True)
    if trigger:
      Global.Transactions_Form.remove_from_parent()
      Global.Transactions_Form.sub_cat = None
      get_open_form().transactions_page_link_click()
    
    

  

