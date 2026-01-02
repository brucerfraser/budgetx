from ._anvil_designer import one_transactionTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from ....F_Global_Logic import Global
from datetime import date, datetime
import math



class one_transaction(one_transactionTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.dd_list = Global.ACCOUNTS
    self.init_components(**properties)
    self.date.tag = 'date'
    self.account_name = ''
    # date checker for when date drop down is "changed"...it still fires even if the date 
    # comes back the same, which would waste time refreshing the page
    self.check_date_change = date(2000,1,1)
    if not self.item['account']:
      self.account.text = self.account_name = "None selected"
    else:
      for f in self.dd_list:
        if self.item['account'] == f[1]:
          self.account_name = f[0]
          break
      self.account.text = self.account_name
    self.categorise()
    
    
  def categorise(self,**event_args):
    names_list = sorted(list(map(lambda x: x['display'], Global.CATEGORIES.values())))
    names_list.insert(0,"None")
    self.autocomplete_1.suggestions = names_list
    if self.item['category'] == None:
      self.category.text = "None"
    else:
      # print(Global.CATEGORIES[self.item['category']])
      self.category.text = Global.CATEGORIES[self.item['category']]['display']
      self.category.background = Global.CATEGORIES[self.item['category']]['colour']
      self.autocomplete_1.text = self.category.text
    
  def set_bg(self,odd,**event_args):
    objs = [self.account,self.date,self.amount,self.category,self.description,self.card_1,
           self.card_2,self.card_3,self.card_4,self.card_5,self.card_6]
    for obj in objs:
      if odd:
        obj.background = "#2B383E"
      else:
        obj.background = "#595A3B"
      if self.check_box_1.checked:
        obj.background = '#4682B4' #can be deleted/amended for transfer
    if self.item['amount'] < 0:
      self.amount.foreground = 'theme:Amount Negative'
    if self.item['category'] == None:
      self.category.background = 'theme:Amount Negative'
    else:
      self.category.background = Global.CATEGORIES[self.item['category']]['colour']

  def click_date(self, **event_args):
    self.check_date_change = self.item['date']
    self.date_picker_1.visible = True
    self.date_picker_1.focus()
    self.date.visible = False

  def date_picker_1_change(self, **event_args):
    # we should re-load if date has actually changed
    if self.item['date'] != self.check_date_change:
      frame = get_open_form()
      frm = frame.content_panel.get_components()[0]
      frm.load_me(False)
      self.update_a_transaction('date',self.item['date'],self.item['transaction_id'])
    self.date_picker_1.visible = False
    self.date.visible = True
    

  def click_account(self, **event_args):
    self.drop_down_1.visible = True
    self.drop_down_1.focus()
    # self.drop_down_1.
    self.account.visible = False

  def drop_down_1_change(self, **event_args):
    for f in self.dd_list:
      if self.item['account'] == f[1]:
        self.account_name = f[0]
        break
    self.account.text = self.account_name
    self.account.visible = True
    self.drop_down_1.visible = False
    # have to change the hash here
    self.update_a_transaction('account',self.item['account'],self.item['transaction_id'])
    
  def amount_click(self, **event_args):
    self.text_box_1.visible = True
    self.text_box_1.focus()
    self.amount.visible = False

  def some_lose_focus(self,**event_args):
    # must update here...
    self.item['amount'] = int(math.trunc(self.text_box_1.text*100))
    self.refresh_data_bindings()
    if self.item['amount'] < 0:
      self.amount.foreground = 'theme:Amount Negative'
    else:
      self.amount.foreground = ''
    get_open_form().content_panel.get_components()[0].rake_page()
    self.update_a_transaction('amount',self.item['amount'],self.item['transaction_id'])
    self.amount.visible = True
    self.text_box_1.visible = False

  def description_click(self, **event_args):
    self.text_box_2.visible = True
    self.text_box_2.focus()
    self.description.visible = False

  def desc_lose_focus(self, **event_args):
    self.refresh_data_bindings()
    self.update_a_transaction('description',self.item['description'],self.item['transaction_id'])
    self.description.visible = True
    self.text_box_2.visible = False

  def category_click(self, **event_args):
    self.autocomplete_1.visible = True
    if self.autocomplete_1.text == '':
      self.autocomplete_1.focus()
    else:
      self.autocomplete_1.select()
    self.category.visible = False

  def category_choose(self,**event_args):
    # first we check if it was Transfer and changed:
    if self.item['category'] == 'ec8e0085-8408-43a2-953f-ebba24549d96' and self.autocomplete_1.text != "Transfer":
      # we need to handle by giving a choice - do we delete corresponding 
      # (if there is one) or change its category to None?
      # First, either way, we change the category
      self.item['category'] = next((k for k, v in Global.CATEGORIES.items() if v.get('display') == self.autocomplete_1.text), None)
      self.update_a_transaction('category',self.item['category'],self.item['transaction_id'])
      self.category.text = self.autocomplete_1.text
      corr_id = Global.Transactions_Form.check_corresponding(self.item['transaction_id'])
      if corr_id:
        from ....F_PopUps.remove_transfer import remove_transfer
        if alert(remove_transfer(corr_id),buttons=[],large=False,dismissible=False):
          # we must delete
          Global.Transactions_Form.delete_trans_click([corr_id])
        else:
          #we must change to none
          app_tables.transactions.get(transaction_id=corr_id).update(category=None)
          [t for t in Global.TRANSACTIONS if t['transaction_id'] == corr_id][0]['category'] = None
          Global.Transactions_Form.load_me(Global.Transactions_Form.dash)
          
    # Then we check if it changed to Transfer
    elif self.autocomplete_1.text == "Transfer":
      if Global.Transactions_Form.handle_transfers(from_one_t=self.item['transaction_id']):
        self.item['category'] = next((k for k, v in Global.CATEGORIES.items() if v.get('display') == self.autocomplete_1.text), None)
        self.category.text = self.autocomplete_1.text
      else:
        self.autocomplete_1.text = ''
    #Otherwise we just do a normal update.
    else:
      self.item['category'] = next((k for k, v in Global.CATEGORIES.items() if v.get('display') == self.autocomplete_1.text), None)
      self.update_a_transaction('category',self.item['category'],self.item['transaction_id'])
      self.category.text = self.autocomplete_1.text
    
    if self.item['category']:
      Global.smarter(first=False,update=(self.item['category'],self.item['description']))
      self.category.background = Global.CATEGORIES[self.item['category']]['colour']
      self.category.foreground = 'theme:Surface'
      self.category.border = ''
    else:
      self.categorise()
    self.category.visible = True
    self.autocomplete_1.visible = False
    self.confirm.visible = False
    if self.item['category']:
      frame = get_open_form()
      frm = frame.content_panel.get_components()[0]
      frm.smart_cat_update()


  def autocomplete_1_lost_focus(self, **event_args):
    if self.item['category']:
      self.autocomplete_1.text = self.category.text
      self.category.visible = True
      self.autocomplete_1.visible = False
    else:
      self.category.text = "None"
      self.category.background = 'theme:Amount Negative'
      self.category.visible = True
      self.autocomplete_1.visible = False
    

  def am_i_smart(self,**event_args):
    if not self.item['category']:
      """
      What we're doing here is setting an automated category in name only on the link,
      but leaving the item[cat] empty. This eliminates potentially unnecessary server
      trips. BUT. Categorising on budget page will require some tricky effort
      """
      auto_id = Global.is_it_smart(self.item['description'])
      if auto_id:
        self.category.text = Global.CATEGORIES[auto_id]['display']
        c = Global.CATEGORIES[auto_id]['colour']
        self.category.border = "solid {b} 1px".format(b=c)
        self.category.background = ''
        self.category.bold = True
        self.category.foreground = 'theme:Amount Negative'
        self.confirm.visible = True
        # self.card_6.add_component(confirm)

  @handle('confirm','click')
  def confirm_click(self, **event_args):
    self.autocomplete_1.text = self.category.text
    self.category_choose()

  def update_a_transaction(self,key,value,id,**event_args):
    acc = 'none_yet' if not self.item['account'] else self.item['account']
    self.item['hash'] = str(self.item['date'].day) + str(self.item['date'].month) + str(self.item['date'].year) + str(self.item['amount']) + acc
    up_dict = {'hash':self.item['hash'],key:value}
    app_tables.transactions.get(transaction_id=id).update(**up_dict)

  def check_box_1_change(self, **event_args):
    get_open_form().content_panel.get_components()[0].rake_page()
    
  
