from ._anvil_designer import Category_holderTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables


class Category_holder(Category_holderTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    self.link_1.text = self.category_name
    # Any code you write here will run before the form opens.
