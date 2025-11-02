from ._anvil_designer import ReportsTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from ... import Global


class Reports(ReportsTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    names_list = list(map(lambda x: x['display'], Global.CATEGORIES.values()))
    self.autocomplete_1.suggestions = names_list
    # Any code you write here will run before the form opens.

  def autocomplete_1_pressed_enter(self, **event_args):
    print(next((k for k, v in Global.CATEGORIES.items() if v.get('display') == self.autocomplete_1.text), None))
