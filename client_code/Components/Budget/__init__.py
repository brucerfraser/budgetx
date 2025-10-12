from ._anvil_designer import BudgetTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from .Category_holder import Category_holder


class Budget(BudgetTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    self.card_expenses.add_component(Category_holder(category_name="Other"))
    self.card_expenses.add_component(Category_holder(category_name="Mother"))
    self.card_expenses.add_component(Category_holder(category_name="Brother"))
    self.card_expenses.add_component(Category_holder(category_name="Wuther"))
    # Any code you write here will run before the form opens.
