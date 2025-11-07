from ._anvil_designer import Sub_categoryTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from datetime import date
from ..... import Global



class Sub_category(Sub_categoryTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    # Get correct date
    period = date(Global.PERIOD[1], Global.PERIOD[0], 1)
    try:
      self.budget.text = str(app_tables.budgets.search(period=period,
                            belongs_to=self.item['sub_category_id'])[0]['budget_amount'])
      self.budget_edit.text = float(self.budget.text)
    except:
      self.budget.text = "0"
      self.budget_edit.text = 0

  def budget_edit_lost_focus(self, **event_args):
    today = date.today()
    period = date(today.year, today.month, 1)
    if not self.budget_edit.text == 0:
      try:
        app_tables.budgets.get(period=period,
                               belongs_to=self.item['sub_category_id'])[0]['budget_amount'] = self.budget_edit.text
      except:
        app_tables.budgets.add_row(belongs_to=self.item['sub_category_id'],
                                period=period,budget_amount=self.budget_edit.text)
      self.budget.text = str(self.budget_edit.text)
    frame = anvil.get_open_form()
    budg = frame.content_panel.get_components()[0]
    budg.close_cat_click()
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

