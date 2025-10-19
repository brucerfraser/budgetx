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
    

  def link_2_click(self, **event_args):
    from ....Pop_menus.work_a_category import work_a_category
    c = work_a_category(cat=False)
    result = alert(c,title="Add a sub-category to {cat}".format(cat=self.item['name']),
                  buttons=[],large=True)
    if result:
      result['belongs_to'] = self.item['category_id']
      for a in ['colour_back','colour_text']:
        del result[a]
      app_tables.sub_categories.add_row(**result)
      if self.link_1.icon == 'fa:angle-down':
        self.repeating_panel_1.items = app_tables.sub_categories.search(belongs_to=self.item['category_id'])


  def link_1_click(self, **event_args):
    if self.link_1.icon == 'fa:angle-right':
      self.link_1.icon = 'fa:angle-down'
      
      self.repeating_panel_1.items = app_tables.sub_categories.search(belongs_to=self.item['category_id'])
      self.repeating_panel_1.visible = True
    else:
      self.link_1.icon = 'fa:angle-right'
      self.repeating_panel_1.visible = False
