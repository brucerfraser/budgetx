from ._anvil_designer import Budget_miniTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import random
from ...F_Global_Logic import BUDGET


class Budget_mini(Budget_miniTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    if app_tables.settings.get(id='budget')['dash_variances']:
      self.item['category_list'] = app_tables.settings.get(id='budget')['dash_var_top_five']
    else:
      pass
      #choose top 5 here
    
    glances = []
    for i in self.item['category_list']:
      glances.append([c for c in BUDGET.all_sub_cats if c['sub_category_id'] == i['cat_id']][0])
    self.repeating_panel_1.items = glances    
    # Any code you write here will run before the form opens.
