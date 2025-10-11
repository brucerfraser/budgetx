from ._anvil_designer import Budget_miniTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import random


class Budget_mini(Budget_miniTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    temp = []
    for i in range(0,5):
      temp.append({'name':'Category ' + str(i),'val':random.randint(-100, 100),
                  'min':-100,'max':100})
    self.repeating_panel_1.items = temp      
    # Any code you write here will run before the form opens.
