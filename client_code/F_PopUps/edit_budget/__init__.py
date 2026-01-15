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
    
    self.category_view.visible = True
    if not big_cat:
      nts = None
      if len([b for b in BUDGET.all_budgets if b['period'] == self.period and b['belongs_to'] == self.category_not_sub_cat]) > 0:
        nts = [b for b in BUDGET.all_budgets if b['period'] == self.period and b['belongs_to'] == self.category_not_sub_cat][0]['notes']
      c = [b for b in BUDGET.all_cats if b['category_id'] == self.category_not_sub_cat][0]['name']
      sc = [b for b in BUDGET.all_sub_cats if b['sub_category_id'] == self.category][0]['name']
      self.label_2.text = c + " - " + sc
      self.notes.text = nts
      self.column_panel_2.visible = True
      self.edit_card.visible = True
      self.edit_name.text = sc
    else:
      c = [b for b in BUDGET.all_cats if b['category_id'] == self.category][0]['name']
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

  def clear_edit(self,**event_args):
    self.edit_card.visible, self.category_view.visible = False,False

  def edit_switch_change(self, **event_args):
    if self.edit_switch.checked:
      if self.category_not_sub_cat:
        budg = get_open_form().content_panel.get_components()[0]
        self.roll_over.enabled = True
        self.drop_down_1.items = budg.date_picker_bruce_1.drop_down_1.items
        self.roll_over.checked = [s for s in BUDGET.all_sub_cats if s['sub_category_id'] == self.category][0]['roll_over']
        if self.roll_over.checked:
          r_o_d = [s for s in BUDGET.all_sub_cats if s['sub_category_id'] == self.category][0]['roll_over_date']
          if r_o_d:
            m = r_o_d.month
            y = r_o_d.year
            self.drop_down_1.selected_value = (m,y)
          self.drop_down_1.visible = True
        self.colours.visible = False
      else:
        self.roll_over.enabled,self.roll_over.checked = False,False
        self.bg_colour.set_color([c for c in BUDGET.all_cats if c['category_id'] == self.category][0]['colour_back'])
        self.text_colour.set_color([c for c in BUDGET.all_cats if c['category_id'] == self.category][0]['colour_text'])
        self.colours.visible = True
      self.edit_details.visible = True
      self.edit_name.select()
    else:
      self.edit_details.visible = False
    

