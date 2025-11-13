from ._anvil_designer import Category_holderTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from datetime import date


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
      # find the max order in this category, add to result, add to all_sub_cats in main form
      frm = get_open_form().content_panel.get_components()[0]
      result = frm.get_me_max_order(res=result)
      app_tables.sub_categories.add_row(**result)
      # both app_tables and all_sub_cats updated
      if self.link_1.icon == 'fa:angle-down':
        self.repeating_panel_1.items = app_tables.sub_categories.search(q.not_(order=-1),tables.order_by("order"),
                                                                        belongs_to=self.item['category_id'])
        odd = False
        for sc in self.repeating_panel_1.get_components():
          if odd:
            sc.background = 'grey'
          odd = not odd

  def refresh_sub_cats(self, **event_args):
    frm = get_open_form().content_panel.get_components()[0]
    edit, edit_id = False,None
    for sc in self.repeating_panel_1.get_components():
      edit = True if sc.item['sub_category_id'] == frm.category_right else False
      if edit:
        edit_id = frm.category_right
        break
    frm = get_open_form().content_panel.get_components()[0]
    self.repeating_panel_1.items = sorted([l for l in frm.all_sub_cats if l['order'] != -1 and l['belongs_to'] == self.item['category_id']],key=lambda l_i: l_i['order'])
    odd = False
    for sc in self.repeating_panel_1.get_components():
      if odd:
        sc.background = 'grey'
      odd = not odd
    if edit:
      for sc in self.repeating_panel_1.get_components():
        if sc.item['sub_category_id'] == edit_id:
          sc.link_1_click()
          break
    
  
  def link_1_click(self, **event_args):
    if self.link_1.icon == 'fa:angle-right':
      self.repeating_panel_1.items = app_tables.sub_categories.search(q.not_(order=-1),tables.order_by('order'),
                                                                      belongs_to=self.item['category_id'])
      
      self.link_1.icon = 'fa:angle-down'
      self.repeating_panel_1.visible = True
    else:
      self.link_1.icon = 'fa:angle-right'
      self.repeating_panel_1.visible = False

    # Send detail to RH Panel
    frame = anvil.get_open_form()
    budg = frame.content_panel.get_components()[0]
    today = date.today()
    period = date(today.year, today.month, 1)
    budg.load_category_right(self.item['category_id'],period,True)
    # Make all other sub_cats clickable again (links vis, edit invis)
    budg.reset_sub_categories("")

  def calculate_me(self,info,**event_args):
    pass

  def form_show(self, **event_args):
    for obj in [self.name_label,self.budget,self.actual]:
      obj.foreground = self.item['colour_text']
      self.link_1.background = self.item['colour_back']


