from ._anvil_designer import TransactionsTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from ... import Global
import calendar
from datetime import date

class Transactions(TransactionsTemplate):
  def __init__(self,dash=False, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    self.all_transactions = anvil.server.call('load_budget_data',True)
    self.dash = dash
    self.sub_cat = None
    self.searched = False
    self.form_show()

  def form_show(self, **event_args):
    if self.sub_cat:
      self.load_me(self.dash,uncat=False,search=False,sub_cat=self.sub_cat)
      self.card_header.visible = False
    else:
      self.load_me(self.dash)

  def reload_from_upload(self,new_list,**event_args):
    for new in new_list:
      if len([t for t in self.all_transactions if t['hash'] == new['hash']]) == 0:
        #we have a new transaction
        new['amount'] = int(float(new['amount'])*100)
        new['notes'] = None
        new['category'] = None
        self.all_transactions.append(new)
    # self.all_transactions = anvil.server.call('load_budget_data',True)
      

  def load_me(self,dash,uncat=False,search=False,sub_cat=None,**event_args):
    """
    sub_cat is a tuple of (key,value)
    """
    fd,ld = self.date_me(dash)
    if not uncat and not search and not sub_cat:
      self.repeating_panel_1.items = sorted([t for t in self.all_transactions if t['date'] >= fd and t['date'] <= ld],
                                            key = lambda x: x['date'],reverse=True)
    elif uncat:
      self.repeating_panel_1.items = sorted([t for t in self.all_transactions if t['date'] >= fd and t['date'] <= ld and t['category'] == None],
                                            key = lambda x: x['date'],reverse=True)
    elif search:
      self.repeating_panel_1.items = sorted([t for t in self.all_transactions if t['date'] >= fd and t['date'] <= ld and search.lower() in t['description'].lower() or search.lower() in str(t['amount']).lower()],
                                            key = lambda x: x['date'],reverse=True)
    elif sub_cat:
      self.repeating_panel_1.items = sorted([t for t in self.all_transactions if t['date'] >= fd and t['date'] <= ld and (t[sub_cat[0]] == sub_cat[1] or Global.is_it_smart(t['description']) == sub_cat[1])],
                                            key = lambda x: x['date'],reverse=True)
    # self.repeating_panel_1.items = app_tables.transactions.search(tables.order_by("date",ascending=False),
    #                                                               date=q.between(fd,ld,True,True))
    if self.dash:
      self.card_3.role = 'fixed-holder'
      self.card_header.visible = False
    else:
      self.card_3.role = 'fixed-holder-page'
      self.card_header.visible = True
    self.which_form = 'transactions'
    self.rake_page()
    
  
  def date_me(self,dash,**event_args):
    m,y = None,None
    if dash:
      m = date.today().month
      y = date.today().year
      days_in_month = calendar.monthrange(y, m)[1]
      return date(y,m,1),date(y,m,days_in_month)
    else:
      p = Global.PERIOD
      if p[0] + p[1] == 0:
        #we have a custom
        return Global.CUSTOM[0],Global.CUSTOM[1]
      else:
        m = p[0]
        y = p[1]
        days_in_month = calendar.monthrange(y, m)[1]
        return date(y,m,1),date(y,m,days_in_month)

  def quick_sort(self,**event_args):
    fd,ld = self.date_me(False)
    #we need the sorter, and sorter state
    k = event_args['sender'].text.lower()
    #cycle order: None,Up,Down
    s = {"fa:chevron-up":[k,"fa:chevron-down",False],
         "fa:chevron-down":["date","",False],
        "":[k,"fa:chevron-up",True]}
    key = s[event_args['sender'].icon][0]
    i = s[event_args['sender'].icon][1]
    a = s[event_args['sender'].icon][2]
    if key == "date" and i == "fa:chevron-down":
      i = ""
    if key == 'account':
      self.repeating_panel_1.items = sorted([t for t in self.all_transactions if t['date'] >= fd and t['date'] <= ld],
                                            key = lambda x: (x[key],x['date']),reverse = not a)
      # self.repeating_panel_1.items = app_tables.transactions.search(tables.order_by(key,ascending=a),
      #                                                               tables.order_by("date",ascending=False),
      #                                                              date=q.between(fd,ld,True,True))
    else:
      self.repeating_panel_1.items = sorted([t for t in self.all_transactions if t['date'] >= fd and t['date'] <= ld],
                                            key = lambda x: x[key],reverse = not a)
      # self.repeating_panel_1.items = app_tables.transactions.search(tables.order_by(key,ascending=a),
      #                                                              date=q.between(fd,ld,True,True))
    event_args['sender'].icon = i
    for obj in [self.date,self.account,self.amount,self.description]:
      if obj.text != event_args['sender'].text:
        obj.icon = ''
    self.rake_page()

  def smart_cat_update(self,**event_args):
    for trans in self.repeating_panel_1.get_components():
      trans.am_i_smart()

  def rake_page(self,**event_args):
    odd,i,o = True,0,0
    for trans in self.repeating_panel_1.get_components():
      if odd:
        trans.set_bg(True)
      else:
        trans.set_bg(False)
      odd = not odd
      if trans.item['amount'] < 0:
        o += trans.item['amount']
      else:
        i += trans.item['amount']
      trans.am_i_smart()
    self.inflow.text = "Inflow: R{a:.2f}".format(a=i/100)
    self.outflow.text = "Outflow: R{a:.2f}".format(a=o/100)

  def un_cat_button_click(self, **event_args):
    if self.un_cat_button.foreground == 'theme:Primary':
      #un-click it
      self.un_cat_button.foreground = ''
      self.load_me(self.dash)
    else:
      self.un_cat_button.foreground = 'theme:Primary'
      self.load_me(self.dash,uncat=True)

  def search_button_click(self, **event_args):
    if self.search_button.foreground == 'theme:Primary':
      #un-click it
      self.search_text.visible = False
      self.un_cat_button.visible = True
      self.search_text.text = ''
      self.search_button.foreground = ''
      if self.searched:
        self.load_me(self.dash)
        self.searched = False
    else:
      if self.un_cat_button.foreground == 'theme:Primary':
        self.un_cat_button_click()
      self.search_button.foreground = 'theme:Primary'
      self.search_text.visible = True
      self.un_cat_button.visible = False
      self.search_text.focus()

  def go_go(self, **event_args):
    if len(self.search_text.text) >= 3:
      self.searched = True
      self.load_me(self.dash,uncat=False,search=self.search_text.text)
    else:
      if self.searched:
        self.searched = False
        self.load_me(self.dash)

  def search_text_lost_focus(self, **event_args):
    if len(self.search_text.text) < 3:
      self.search_button_click()

  def add_trans_click(self, **event_args):
    date_new = date.today()
    hash_new = str(date_new.day) + str(date_new.month) + str(date_new.year) + '0' + 'none_yet'
    id_new = Global.new_id_needed()
    new_trans = {'date':date_new,'amount':0,
                'description':'                  ',
                'category':None,
                'account':None,'notes':'',
                'hash':hash_new,'transaction_id':id_new}
    t_list = self.repeating_panel_1.items
    t_list.insert(0,new_trans)
    self.all_transactions.insert(0,new_trans)
    app_tables.transactions.add_row(**new_trans)
    self.repeating_panel_1.items = t_list
    self.rake_page()
    # self.repeating_panel_1.get_components()[0].click_date()
    

  
    
