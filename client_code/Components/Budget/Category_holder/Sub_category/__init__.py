from ._anvil_designer import Sub_categoryTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from datetime import date



class Sub_category(Sub_categoryTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    # Get today's date
    today = date.today()
    period = date(today.year, today.month, 1)
    try:
      self.budget.text = app_tables.budgets.search(period=period,
                                                   belongs_to=self.item['sub_category_id'])[0]['budget_amount']
    except:
      self.budget.text = 0

  def budget_edit_lost_focus(self, **event_args):
    today = date.today()
    period = date(today.year, today.month, 1)
    if not self.budget.text == 0:
      try:
        app_tables.budgets.get(period=period,
                               belongs_to=self.item['sub_category_id'])[0]['budget_amount'] = self.budget.text
      except:
        app_tables.budgets.add_row(belongs_to=self.item['sub_category_id'],
                                period=period,budget_amount=self.budget.text)

  def link_1_click(self, **event_args):
    # Fire something to budget form for RH panel.

    # Make all other sub_cats clickable again (links vis, edit invis)

    # Edit column_panel becomes visual.
    
    """This method is called when the link is clicked"""
    pass
