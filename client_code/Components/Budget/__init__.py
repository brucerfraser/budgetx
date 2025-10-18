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
    inc_d = {}
    for inc in app_tables.categories.search(name='Income'):
      inc_d = dict(inc)
    self.card_2.add_component(Category_holder(item=inc_d))
    # self.income_holder.my_identity = app_tables.categories.search(name='Income')
    cats = []
    for cat in app_tables.categories.search():
      cat_d = {}
      cat_d = dict(cat)
      if cat_d['name'] != 'Income':
        cats.append(cat_d)
  
    self.expense_categories.items = cats
    # for cat in app_tables.categories.search():
    #   cat_d = {}
    #   cat_d = dict(cat)
    #   if cat_d['name'] != 'Income':
    #     self.card_expenses.add_component(Category_holder(my_identity=cat_d))
    
    # self.card_expenses.add_component(Category_holder(category_name="Other"))
    # self.card_expenses.add_component(Category_holder(category_name="Mother"))
    # self.card_expenses.add_component(Category_holder(category_name="Brother"))
    # self.card_expenses.add_component(Category_holder(category_name="Wuther"))
    # Any code you write here will run before the form opens.

  def add_category_click(self, **event_args):
    from ...Pop_menus.work_a_category import work_a_category
    c = work_a_category()
    result = alert(c,title="Add a category",buttons=[],large=True)
    # print(result)
    if result:
      cat_d = {}
      app_tables.categories.add_row(**result)
      for cat in app_tables.categories.search(q.not_(name='Income')):
        cat_d = dict(cat)
        self.card_expenses.add_component(Category_holder(my_identity=cat_d))
    
    
    
