from ._anvil_designer import edit_budgetTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from ...F_Global_Logic import BUDGET


class edit_budget(edit_budgetTemplate):
  def __init__(self, embedded=True, **properties):
    # Set Form properties and Data Bindings.
    self.embedded=embedded
    self.init_components(**properties)
    self.period = None
    self.category = None
    self.category_not_sub_cat = None
    self.drop_down_1.selected_value = None

  @handle("", "show")
  def form_show(self, **event_args):
    if not self.embedded:
      # call edit_switch
      pass
    else:
      self.edit_card.visible, self.category_view.visible = False,False

  def load_for_edit(self,cat,period,big_cat=False,b_to='', **event_args):
    self.category,self.period = cat,period
    self.category_not_sub_cat = b_to
    c = [b for b in BUDGET.all_cats if b['category_id'] == self.category][0]['name']
    if not big_cat:
      nts = None
      if len([b for b in BUDGET.all_budgets if b['period'] == self.period and b['belongs_to'] == self.category_not_sub_cat]) > 0:
        nts = [b for b in BUDGET.all_budgets if b['period'] == self.period and b['belongs_to'] == self.category_not_sub_cat][0]['notes']
      sc = [b for b in BUDGET.all_sub_cats if b['sub_category_id'] == self.category][0]['name']
      self.label_2.text = c + " - " + sc
      self.notes.text = nts
      self.column_panel_2.visible = True
      self.edit_card.visible = True
      self.edit_name.text = sc
    else:
      self.label_2.text = c
      self.column_panel_2.visible = False
      if not self.label_2.text == "Income":
        self.edit_card.visible = True
        self.edit_name.text = c
      else:
        self.edit_card.visible = False
    self.edit_details.visible,self.edit_switch.checked,self.drop_down_1.visible = False,False,False
    self.drop_down_1.selected_value = None
    self.close_cat.visible = True
    

