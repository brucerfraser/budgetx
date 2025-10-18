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
    # print(self.my_identity)
    
    # Any code you write here will run before the form opens.

  def link_2_click(self, **event_args):
    from ....Pop_menus.work_a_category import work_a_category
    c = work_a_category()
    result = alert(c,title="Add a sub-category to {cat}".format(cat=self.item['name']),
                  buttons=[],large=True)
    print(result, self.item['category_id'])
