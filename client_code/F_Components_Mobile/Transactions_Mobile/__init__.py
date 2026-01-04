from ._anvil_designer import Transactions_MobileTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from ...F_Global_Logic import Global,Transaction
import calendar
from datetime import date, datetime, timedelta


class Transactions_Mobile(Transactions_MobileTemplate):
  def __init__(self, dash=False, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    self.dash = dash
    self.which_form = "transactions"
    self.delete_list = []
    self.sub_cat = None
    self.searched = False
    # self.form_show()

  def form_show(self, **event_args):
    if self.sub_cat:
      self.load_me(self.dash, uncat=False, search=False, sub_cat=self.sub_cat)
      self.card_header.visible = False
    else:
      self.load_me(self.dash)
    

  def bottom_button_incoming(self,key,**event_args):
    if key == 'butt1':
      #search button
      alert("Search page will pop up in future")
    if key == 'butt2':
      #uncat button
      self.un_cat_button_click()
    if key == 'butt3':
      #add button
      self.add_trans_click()
    if key == 'butt4':
      #transfer button
      self.handle_transfers()
    if key == 'butt5':
      #delete button
      Transaction.work_transaction_data('delete_confirm',self.delete_list)
      

  def load_me(self, dash, uncat=False, search=False, sub_cat=None, **event_args):
    """
    sub_cat is a tuple of (key,value)
    """
    if self.dash:
      # self.card_3.role = "fixed-holder"
      self.card_header.visible = False
    else:
      # self.card_3.role = "fixed-holder-page"
      self.card_header.visible = True
    fd, ld = Transaction.date_me(dash)
    if not uncat and not search and not sub_cat:
      self.repeating_panel_1.items = sorted(
        [t for t in Global.TRANSACTIONS if t["date"] >= fd and t["date"] <= ld],
        key=lambda x: x["date"],
        reverse=True,
      )
    elif uncat:
      self.repeating_panel_1.items = sorted(
        [
          t
          for t in Global.TRANSACTIONS
          if t["date"] >= fd and t["date"] <= ld and t["category"] == None
        ],
        key=lambda x: x["date"],
        reverse=True,
      )
    elif search:
      self.repeating_panel_1.items = sorted(
        [
          t
          for t in Global.TRANSACTIONS
          if t["date"] >= fd
          and t["date"] <= ld
          and search.lower() in t["description"].lower()
          or search.lower() in str(t["amount"]).lower()
        ],
        key=lambda x: x["date"],
        reverse=True,
      )
    elif sub_cat:
      self.repeating_panel_1.items = sorted(
        [
          t
          for t in Global.TRANSACTIONS
          if t["date"] >= fd
          and t["date"] <= ld
          and (
            t[sub_cat[0]] == sub_cat[1]
            or Global.is_it_smart(t["description"]) == sub_cat[1]
          )
        ],
        key=lambda x: x["date"],
        reverse=True,
      )
    # self.repeating_panel_1.items = app_tables.transactions.search(tables.order_by("date",ascending=False),
    #                                                               date=q.between(fd,ld,True,True))

    self.which_form = "transactions"
    self.rake_page()


  def quick_sort(self, **event_args):
    fd, ld = Transaction.date_me(False)
    # we need the sorter, and sorter state
    k = event_args["sender"].text.lower()
    # cycle order: None,Up,Down
    s = {
      "fa:chevron-up": [k, "fa:chevron-down", False],
      "fa:chevron-down": ["date", "", False],
      "": [k, "fa:chevron-up", True],
    }
    key = s[event_args["sender"].icon][0]
    i = s[event_args["sender"].icon][1]
    a = s[event_args["sender"].icon][2]
    if key == "date" and i == "fa:chevron-down":
      i = ""
    if key == "account":
      self.repeating_panel_1.items = sorted(
        [t for t in Global.TRANSACTIONS if t["date"] >= fd and t["date"] <= ld],
        key=lambda x: (x[key], x["date"]),
        reverse=not a,
      )
      # self.repeating_panel_1.items = app_tables.transactions.search(tables.order_by(key,ascending=a),
      #                                                               tables.order_by("date",ascending=False),
      #                                                              date=q.between(fd,ld,True,True))
    else:
      self.repeating_panel_1.items = sorted(
        [t for t in Global.TRANSACTIONS if t["date"] >= fd and t["date"] <= ld],
        key=lambda x: x[key],
        reverse=not a,
      )
      # self.repeating_panel_1.items = app_tables.transactions.search(tables.order_by(key,ascending=a),
      #                                                              date=q.between(fd,ld,True,True))
    event_args["sender"].icon = i
    for obj in [self.date, self.account, self.amount, self.description]:
      if obj.text != event_args["sender"].text:
        obj.icon = ""
    self.rake_page()

  def smart_cat_update(self, **event_args):
    for trans in self.repeating_panel_1.get_components():
      trans.am_i_smart()

  def rake_page(self, **event_args):
    odd, i, o = True, 0, 0
    try:
      chk = (
        True
        if get_open_form().content_panel.get_components()[0].which_form
        == "transactions"
        else False
      )
    except:
      chk = False
      # error will occur during loading as there is no open form yet as Transactions page is loaded in Global
    for trans in self.repeating_panel_1.get_components():
      if odd:
        trans.set_bg(True)
      else:
        trans.set_bg(False)
      odd = not odd
      if trans.item["amount"] < 0:
        o += trans.item["amount"]
      else:
        i += trans.item["amount"]
      trans.card_1.role = 'txn-card-mobile-selected' if trans.checked else 'txn-card-mobile'
      if chk:
        if trans.checked:
          if trans.item["transaction_id"] not in self.delete_list:
            self.delete_list.append(trans.item["transaction_id"])
        else:
          if trans.item["transaction_id"] in self.delete_list:
            self.delete_list.remove(trans.item["transaction_id"])
      trans.am_i_smart()
    # self.delete_trans.enabled = True if len(self.delete_list) > 0 else False
    # self.btn_tfer.enabled = True if len(self.delete_list) > 0 else False
    self.inflow.text = "Inflow: R{a:.2f}".format(a=i / 100)
    self.outflow.text = "Outflow: R{a:.2f}".format(a=o / 100)
    print(self.delete_list)

  def un_cat_button_click(self, **event_args):
    # if self.un_cat_button.foreground == "theme:Primary":
    #   # un-click it
    #   self.un_cat_button.foreground = ""
    #   self.load_me(self.dash)
    # else:
    #   self.un_cat_button.foreground = "theme:Primary"
    #   self.load_me(self.dash, uncat=True)
    pass

  def search_button_click(self, **event_args):
    if self.search_button.foreground == "theme:Primary":
      # un-click it
      self.search_text.visible = False
      self.un_cat_button.visible = True
      self.search_text.text = ""
      self.search_button.foreground = ""
      if self.searched:
        self.load_me(self.dash)
        self.searched = False
    else:
      if self.un_cat_button.foreground == "theme:Primary":
        self.un_cat_button_click()
      self.search_button.foreground = "theme:Primary"
      self.search_text.visible = True
      self.un_cat_button.visible = False
      self.search_text.focus()

  def go_go(self, **event_args):
    if len(self.search_text.text) >= 3:
      self.searched = True
      self.load_me(self.dash, uncat=False, search=self.search_text.text)
    else:
      if self.searched:
        self.searched = False
        self.load_me(self.dash)

  def search_text_lost_focus(self, **event_args):
    if len(self.search_text.text) < 3:
      self.search_button_click()

  @handle("add_trans", "click")
  def add_trans_click(self, **event_args):
    date_new = date.today()
    hash_new = (
      str(date_new.day) + str(date_new.month) + str(date_new.year) + "0" + "none_yet"
    )
    id_new = Global.new_id_needed()
    new_trans = {
      "date": date_new,
      "amount": 0,
      "description": "",
      "category": None,
      "account": None,
      "notes": "",
      "hash": hash_new,
      "transaction_id": id_new,
      "transfer_account": None,
    }
    from ...F_PopUps.add_transaction import add_transaction

    alert(add_transaction(new_trans), buttons=[], large=True, dismissible=False)

  
  def delete_trans_click(self, alien=None, **event_args):
    pass

  @handle("btn_tfer", "click")
  def handle_transfers(self, from_one_t=None, **event_args):
    if from_one_t:
      l = [from_one_t]
    else:
      l = self.delete_list
    from ...F_PopUps.transfers import transfers

    result = alert(transfers(l), large=True, buttons=[], dismissible=False)
    if result:
      # we must build a list to add/edit in transaction list:
      # all_transactions and table transactions.
      anvil.server.call("handle_transfers", self.local_transfers(result))
      self.load_me(self.dash)
    return True if result else False

  def local_transfers(self, transfer_list, **event_args):
    for transfer in transfer_list:
      f_t = "From" if transfer["amount_two"] > 0 else "To"
      acc_one, acc_two = "", ""
      for g in Global.ACCOUNTS:
        # print(g[0],g[1],g[1]==transfer['account_one'])
        if g[1] == transfer["account_one"]:
          acc_two = g[0]
        if g[1] == transfer["account_two"]:
          acc_one = g[0]
      t_f = "From" if f_t == "To" else "From"
      desc_one = "{f_t} {acc}".format(f_t=t_f, acc=acc_one)
      desc_two = "{f_t} {acc}".format(f_t=f_t, acc=acc_two)

      # left t-id
      [t for t in Global.TRANSACTIONS if t["transaction_id"] == transfer["trans_one"]][
        0
      ]["transfer_account"] = transfer["account_two"]
      [t for t in Global.TRANSACTIONS if t["transaction_id"] == transfer["trans_one"]][
        0
      ]["category"] = "ec8e0085-8408-43a2-953f-ebba24549d96"
      [t for t in Global.TRANSACTIONS if t["transaction_id"] == transfer["trans_one"]][
        0
      ]["description"] = desc_one
      if transfer["exists"]:
        # right t-id
        [
          t for t in Global.TRANSACTIONS if t["transaction_id"] == transfer["trans_two"]
        ][0]["transfer_account"] = transfer["account_one"]
        [
          t for t in Global.TRANSACTIONS if t["transaction_id"] == transfer["trans_two"]
        ][0]["category"] = "ec8e0085-8408-43a2-953f-ebba24549d96"
        [
          t for t in Global.TRANSACTIONS if t["transaction_id"] == transfer["trans_two"]
        ][0]["description"] = desc_two
      else:
        # we have to make one transaction
        hash = (
          transfer["date_two"].strftime("%d%m%Y")
          + str(transfer["amount_two"])
          + transfer["account_two"]
        )
        t_acc = Global.new_id_needed()
        transfer["trans_two"] = t_acc
        Global.TRANSACTIONS.append(
          {
            "date": transfer["date_two"],
            "description": desc_two,
            "amount": transfer["amount_two"],
            "hash": hash,
            "account": transfer["account_two"],
            "transaction_id": t_acc,
            "category": "ec8e0085-8408-43a2-953f-ebba24549d96",
            "transfer_account": transfer["account_one"],
          }
        )
    return transfer_list

  def check_corresponding(self, t_id, **event_args):
    the_one = [t for t in Global.TRANSACTIONS if t["transaction_id"] == t_id][0]
    a_opp = -1 * the_one["amount"]
    d_bef = the_one["date"] - timedelta(days=2)
    d_aft = the_one["date"] + timedelta(days=2)
    try:
      return [
        t
        for t in Global.TRANSACTIONS
        if t["amount"] == a_opp and d_bef <= t["date"] and d_aft >= t["date"]
      ][0]["transaction_id"]
    except:
      return None
