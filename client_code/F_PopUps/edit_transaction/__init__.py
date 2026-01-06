from ._anvil_designer import edit_transactionTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from datetime import date, timedelta
import time
from ...F_Global_Logic.Global import Transactions_Form
from ...F_Global_Logic import Global, Transaction


class edit_transaction(edit_transactionTemplate):
  def __init__(self, new_trans, **properties):
    # Set Form properties and Data Bindings.
    self.item = new_trans
    self.was_transfer = self.item['category'] == "ec8e0085-8408-43a2-953f-ebba24549d96"
    self.holder = ""
    self.init_components(**properties)
    self.cats = [item['display'] for item in Global.CATEGORIES.values()]
    self.rp_category.set_event_handler('x-close-up-shop',self.close_category)
    self.cp_category.set_event_handler('x-answer',self.save_handler)
    self.remove_box = None

  @handle("", "show")
  def form_show(self, **event_args):
    self.drop_down_1.items = Global.ACCOUNTS
    self.dd_transfer.items = Global.ACCOUNTS
    self.text_box_1.text = self.item['amount'] / 100
    self.categorise()

  @handle("btn_cancel", "click")
  @handle("btn_save", "click")
  def tally_up(self, **event_args):
    if event_args["sender"].text == "cancel":
      self.raise_event("x-close-alert", value=None)
    elif event_args["sender"].text == "save":
      if self.cp_transfer.visible and self.cp_transfer.background == "#b2d8b2":
        # we can save
        self.save_and_send()
        self.raise_event("x-close-alert", value=None)
      elif not self.cp_transfer.visible:
        # we can save
        self.save_and_send()
        self.raise_event("x-close-alert", value=None)
      else:
        # flash a bit
        on = False
        for i in range(0, 5):
          self.cp_transfer.background = "#FFCDC9" if on else ""
          on = not on
          time.sleep(0.2)
        self.cp_transfer.background = "#FFCDC9"

  def save_and_send(self, **event_args):
    # we have to manually assign here due to the Cancel philosophy - write-back on fields auto updates TRANSACTIONS
    self.item["amount"] = self.text_box_1.text * 100
    self.item['date'] = self.date_picker_1.date
    self.item['description'] = self.txt_description.text
    self.item['transfer_account'] = self.dd_transfer.selected_value
    self.item['account'] = self.drop_down_1.selected_value
    self.item["hash"] = (
      str(self.item["date"].day)
      + str(self.item["date"].month)
      + str(self.item["date"].year)
      + str(self.item["amount"])
      + str(self.item["account"])
    )
    self.save_handler()

  def categorise(self, **event_args):
    if self.item['category']:
      self.link_category.text = Global.CATEGORIES[self.item['category']]['display']
      self.link_category.background = Global.CATEGORIES[self.item['category']]['colour']
      self.link_category.foreground = 'black'
    self.txt_category.visible = False
    self.cp_selector.visible = False

  @handle('link_category','click')
  def open_category(self,**event_args):
    if self.link_category.text not in ['','None']:
      self.txt_category.text = self.link_category.text
    if self.txt_category.text:
      t = self.txt_category.text
      self.rp_category.items = [l for l in self.cats if t.lower() in l.lower()]
    self.link_category.visible = False
    self.txt_category.visible = True
    self.cp_selector.visible = True
    self.txt_category.select()

  @handle('txt_category','change')
  def ping_ping(self,**event_args):
    if self.txt_category.text:
      self.rp_category.visible = True
      t = self.txt_category.text
      self.rp_category.items = [l for l in self.cats if t.lower() in l.lower()]
    else:
      self.rp_category.visible = False
      self.rp_category.items = []

  @handle('txt_category','pressed_enter')
  def close_category_enter(self,**event_args):
    l = self.rp_category.items
    if l:
      self.close_category(cat=l[0])

    
  @handle('txt_category','lost_focus')
  def close_category(self,cat=None,**event_args):
    cat = cat if cat else self.txt_category.text
    c = next((k for k, v in Global.CATEGORIES.items() if v.get("display") == cat),None)    
    self.item['category'] = c if c else self.item['category']
    self.categorise()
    self.cp_selector.visible = False
    self.txt_category.visible = False
    self.txt_category.text = ''
    self.link_category.visible = True
    self.update_transfer()
      
  @handle("drop_down_1", "change")
  @handle("text_box_1", "lost_focus")
  @handle("date_picker_1", "change")
  def update_transfer(self, **event_args):
    if self.item["category"] == "ec8e0085-8408-43a2-953f-ebba24549d96":
      # we have a transfer
      self.holder = self.txt_description.text
      acc_name = "<No Account>"
      acc_name_two = "<No Account>"
      for g in Global.ACCOUNTS:
        if g[1] == self.item["account"]:
          acc_name = g[0]
        if g[1] == self.dd_transfer.selected_value:
          acc_name_two = g[0]
      f_t = "From" if self.item["amount"] < 0 else "To"
      t_f = "From" if f_t == "To" else "To"
      dte = self.item["date"] if self.item["date"] else "<No Date>"
      self.lbl_tfer_detail.text = "{f} {a} on {d} {t}:".format(
        f=f_t, a=acc_name, d=dte, t=t_f
      )
      self.lbl_tfer_amount.text = "R {ama:.2f}".format(ama=-1 * self.item["amount"])
      self.txt_description.text = "{f} {a}".format(f=t_f, a=acc_name_two)
      self.item["description"] = self.txt_description.text
      self.lbl_tfer_amount.foreground = (
        "theme:Amount Negative" if self.item["amount"] > 0 else "theme:Primary"
      )
      self.lbl_tfer_detail.foreground = (
        "theme:Amount Negative" if self.item["amount"] < 0 else "theme:Primary"
      )
      self.cp_transfer.visible = True
    else:
      if self.cp_transfer.visible:
        self.item["description"] = self.txt_description.text = self.holder
        self.lbl_tfer_detail.text = ""
        self.lbl_tfer_amount.text = ""
        self.dd_transfer.selected_value = None
        self.cp_transfer.visible = False

  @handle("dd_transfer", "change")
  def tfer_account(self, **event_args):
    if self.dd_transfer.selected_value:
      self.cp_transfer.background = "#b2d8b2"
      acc_name = ""
      for g in Global.ACCOUNTS:
        if g[1] == self.dd_transfer.selected_value:
          acc_name = g[0]
          break
      f_t = "From" if self.item["amount"] > 0 else "To"
      self.item["description"] = self.txt_description.text = "{f} {a}".format(
        f=f_t, a=acc_name
      )
    else:
      self.cp_transfer.background = "#FFCDC9"

  def save_handler(self,confirm=None,**event_args):
    # first we check if it was Transfer and changed:
    if confirm:
      if confirm == "delete":
        corr_id = Global.Transactions_Form.check_corresponding(self.item['transaction_id'])
        Transaction.work_transaction_data('delete_immediate',[corr_id])
      else:
        Transaction.work_transaction_data('change_on_key',{'transaction_id':corr_id,'key':'category','value':None})
      Global.Transactions_Form.load_me(Global.Transactions_Form.dash)
      self.remove_box.remove_from_parent()
      
    elif self.item['category'] != 'ec8e0085-8408-43a2-953f-ebba24549d96' and self.was_transfer:
      # we need to handle by giving a choice - do we delete corresponding 
      # (if there is one) or change its category to None?
      # First, either way, we change the category
      Transaction.work_transaction_data('update',self.item)
      corr_id = Global.Transactions_Form.check_corresponding(self.item['transaction_id'])
      if corr_id:
        from ...F_PopUps.remove_transfer import remove_transfer
        self.remove_box = remove_transfer(corr_id,True)
        for obj in self.cp_category.get_components():
          obj.visible = False
        self.cp_category.add_component(self.remove_box)

    # Then we check if it changed to Transfer
    elif self.item['category'] == 'ec8e0085-8408-43a2-953f-ebba24549d96' and not self.was_transfer:
      # First update transaction
      Transaction.work_transaction_data('update',self.item)
      # now we check if there's a corresponding
      corr_id = Global.Transactions_Form.check_corresponding(self.item['transaction_id'])
      if corr_id:
        Transaction.work_transaction_data('change_one_key',{'transaction_id':corr_id,'key':'category',
                                                            'value':'ec8e0085-8408-43a2-953f-ebba24549d96'})
      else:
        hash_new = str(self.item['date'].day) + str(self.item['date'].month) + str(self.item['date'].year) + str(-1 * self.item['amount']) + self.item['transfer_account']
        for g in Global.ACCOUNTS:
          # print(g[0],g[1],g[1]==transfer['account_one'])
          if g[1] == self.item['account']:
            acc_name = g[0]
            break
        f_t = "From" if self.item['amount'] < 0 else "To"
        new_trans = {'date':self.item['date'],
                    'amount':-1 * self.item['amount'],
                    'description':"{f} {a}".format(f=f_t,a=acc_name),
                    'category':"ec8e0085-8408-43a2-953f-ebba24549d96",
                    'account':self.item['transfer_account'],
                    'notes':'',
                    'hash':hash_new,'transaction_id':Global.new_id_needed(),
                    'transfer_account':self.item['account']}
        Transaction.work_transaction_data('add',new_trans)
      
    #Otherwise we just do a normal update.
    else:
      Transaction.work_transaction_data('update',self.item)

    if self.item['category']:
      Global.smarter(first=False,update=(self.item['category'],self.item['description']))
    Global.Transactions_Form.smart_cat_update()
    