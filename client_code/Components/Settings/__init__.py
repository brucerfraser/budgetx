from ._anvil_designer import SettingsTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from ... import Global


class Settings(SettingsTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.item['dash_variances'] = app_tables.settings.get(id='budget')['dash_variances']
    self.init_components(**properties)
    self.item['category_list'] = app_tables.settings.get(id='budget')['dash_var_top_five']
    names_list = sorted(list(map(lambda x: x['display'], Global.CATEGORIES.values())))
    self.autocomplete_1.suggestions = names_list
    self.refresh_data_bindings()


  def category_choose(self,**event_args):
    cat_id = next((k for k, v in Global.CATEGORIES.items() if v.get('display') == self.autocomplete_1.text), None)
    self.item['category_list'].append({'name':self.autocomplete_1.text,'cat_id':cat_id})
    self.autocomplete_1.text = ''
    if len(self.item['category_list']) > 5:
      self.item['category_list'].pop(0)
    app_tables.settings.get(id='budget')['dash_var_top_five'] = self.item['category_list']
    self.refresh_data_bindings()

  def switch_1_change(self, **event_args):
    app_tables.settings.get(id='budget')['dash_variances'] = self.switch_1.checked
    self.refresh_data_bindings()
