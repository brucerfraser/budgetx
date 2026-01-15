from ._anvil_designer import Budget_MobileTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from .Category_holder_mobile import Category_holder_mobile
import calendar
from datetime import date, datetime, timedelta
from ...F_Global_Logic import Global
from ...F_Global_Logic import BUDGET
import anvil.js


class Budget_Mobile(Budget_MobileTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    self.category_right = ""
    self.period_right = None
    self.cat_sub_cat = None
    self.which_form = "budget_m"
    inc_d = {}
    cats = []
    """
    METHOD LOCAL with backup
    """
    try:
      inc_d = [c for c in BUDGET.all_cats if c["name"] == "Income"][0]
    except Exception as e:
      for inc in app_tables.categories.search(name="Income"):
        inc_d = dict(inc)
      print("Budget form mobile line 35: Income backup table search use because of \n", e)
    self.income_cat_holder = Category_holder_mobile(item=inc_d)
    self.card_2.add_component(self.income_cat_holder)
    try:
      cats = sorted(
        [
          c
          for c in BUDGET.all_cats
          if not c["name"] == "Income" and not c["order"] == -1
        ],
        key=lambda x: x["order"],
      )
    except Exception as e:
      for cat in app_tables.categories.search(tables.order_by("order")):
        cat_d = {}
        cat_d = dict(cat)
        if cat_d["name"] != "Income" and cat_d["order"] != -1:
          cats.append(cat_d)
      print("Budget form mobile line 53: Expesnse backup table search use because of \n", e)
    """
    END local load methods
    """
    self.expense_categories.items = cats
    self.update_numbers()

  @handle("", "show")
  def form_show(self, **event_args):
    # self.load_me(False)
    anvil.js.window.document.documentElement.style.setProperty(
      "--mobile-headerbudget", "540px"
    )

  def header_numbers(self,**event_args):
    pass

  # ------------------------------
  # Mobile category "open" animation
  # ------------------------------
  def animate_open_category(self, category_id, **event_args):
    """Fade non-selected categories, slide the category list up over the header,
    then hide header components. After the animation you can inject/expand
    sub-categories under the selected item.

    Called from the Category_holder_mobile item on single-tap.
    """
    self.grid_panel_1.visible = False
    self.card_exp_header.visible = False
    self.income_cat_holder.remove_from_parent()
    self.expense_categories.items = []
    # The anim hides everything. No worries, we just add the correct category again, even if it's income
    cats = [c for c in BUDGET.all_cats if c["category_id"] == category_id]
    self.expense_categories.items = cats
    self.update_numbers()
    # automatically open the tapped category's sub-cats
    for cat in self.expense_categories.get_components():
      cat.opened = True
      from ...F_PopUps.budget_category import budget_category
      cat.add_component(budget_category(cat_id=category_id))
    anvil.js.window.document.documentElement.style.setProperty(
      "--mobile-headerbudget", "195px"
    )

  def smart_cat_update(self, **event_args):
    Global.Transactions_Form.smart_cat_update()

  def load_me(self, dash, **event_args):
    # this happens after date selection changes at top
    # get date
    fd, ld = BUDGET.date_me(dash)

    # go through cats and update any open sub_cats
    self.update_numbers()
    for inc in self.card_2.get_components()[-1].repeating_panel_1.get_components():
      inc.form_show()
    for category in self.expense_categories.get_components():
      if category.link_1.icon == "fa:angle-down":
        # sub-cats are open
        for sub_cat in category.repeating_panel_1.get_components():
          sub_cat.form_show()

  def add_category_click(self, **event_args):
    from ...F_PopUps.work_a_category import work_a_category
    c = work_a_category()
    result = alert(c, title="Add a category", buttons=[], large=True)
    # print(result)
    if result:
      for a in ["roll_over", "roll_over_date"]:
        del result[a]
      result["order"] = max(BUDGET.all_cats, key=lambda x: x["order"])["order"] + 1
      BUDGET.update_budget('add_cat',result)
      self.expense_categories.items = sorted(
        [
          c
          for c in BUDGET.all_cats
          if not c["name"] == "Income" and not c["order"] == -1
        ],
        key=lambda x: x["order"],
      )

  
  def load_category_right(self, cat, period, big_cat=False, b_to="", **event_args):
    self.category_right, self.period_right = cat, period
    self.cat_sub_cat = b_to
    if not big_cat:
      nts = None
      try:
        nts = app_tables.budgets.get(period=period, belongs_to=cat)["notes"]
      except Exception as e:
        print("error:", e)

      sc = app_tables.sub_categories.get(sub_category_id=cat)["name"]
      c = app_tables.categories.get(category_id=b_to)["name"]
      self.label_2.text = c + " - " + sc
      self.notes.text = nts
      self.column_panel_2.visible = True
      self.edit_card.visible = True
      self.edit_name.text = app_tables.sub_categories.get(
        sub_category_id=self.category_right
      )["name"]
    else:
      self.label_2.text = app_tables.categories.get(category_id=self.category_right)[
        "name"
      ]
      self.column_panel_2.visible = False
      if not self.label_2.text == "Income":
        self.edit_card.visible = True
        self.edit_name.text = app_tables.categories.get(
          category_id=self.category_right
        )["name"]
      else:
        self.edit_card.visible = False
    self.edit_details.visible, self.edit_switch.checked, self.drop_down_1.visible = (
      False,
      False,
      False,
    )
    self.drop_down_1.selected_value = None
    self.close_cat.visible = True

  def reset_sub_categories(self, cat, **event_args):
    for category in self.expense_categories.get_components():
      # print(category)
      if category.link_1.icon == "fa:angle-down":
        # sub-cats are open
        for sub_cat in category.repeating_panel_1.get_components():
          if sub_cat.item["sub_category_id"] != cat:
            sub_cat.edit_column_panel.visible = False
            sub_cat.link_1.visible = True
    for inc in self.card_2.get_components()[-1].repeating_panel_1.get_components():
      # print(inc.item)
      if inc.item["sub_category_id"] != cat:
        inc.edit_column_panel.visible = False
        inc.link_1.visible = True

  def update_notes(self, **event_args):
    if not self.notes.text == "":
      try:
        app_tables.budgets.get(
          belongs_to=self.category_right, period=self.period_right
        )["notes"] = self.notes.text
      except:
        app_tables.budgets.add_row(
          belongs_to=self.category_right,
          period=self.period_right,
          budget_amount=0,
          notes=self.notes.text,
        )

  def edit_switch_change(self, **event_args):
    if self.edit_switch.checked:
      if self.cat_sub_cat:
        self.roll_over.enabled = True
        self.drop_down_1.items = self.date_picker_bruce_1.drop_down_1.items
        self.roll_over.checked = [
          s for s in BUDGET.all_sub_cats if s["sub_category_id"] == self.category_right
        ][0]["roll_over"]
        # self.roll_over.checked = app_tables.sub_categories.get(sub_category_id=self.category_right)['roll_over']
        if self.roll_over.checked:
          r_o_d = [
            s
            for s in BUDGET.all_sub_cats
            if s["sub_category_id"] == self.category_right
          ][0]["roll_over_date"]
          if r_o_d:
            m = r_o_d.month
            y = r_o_d.year
            self.drop_down_1.selected_value = (m, y)
          self.drop_down_1.visible = True
        self.colours.visible = False
      else:
        self.roll_over.enabled, self.roll_over.checked = False, False
        self.bg_colour.set_color(
          [c for c in BUDGET.all_cats if c["category_id"] == self.category_right][0][
            "colour_back"
          ]
        )
        self.text_colour.set_color(
          [c for c in BUDGET.all_cats if c["category_id"] == self.category_right][0][
            "colour_text"
          ]
        )
        self.colours.visible = True
      self.edit_details.visible = True
      self.edit_name.select()
    else:
      self.edit_details.visible = False

  def change_order(self, **event_args):
    up = None
    if event_args["sender"].icon == "fa:angle-up":
      up = True
    else:
      up = False
    if self.cat_sub_cat == "":
      ret = Global.change_order_controller(
        up=up, id=self.category_right, the_list_o_d=BUDGET.all_cats
      )
    else:
      ret = Global.change_order_controller(
        up=up, id=self.category_right, the_list_o_d=BUDGET.all_sub_cats
      )

    # ret = 'cat' means it's a category, 'uy2346iuy...' = sub_category belongs_to, None means do noting
    if ret[0] == "cat":
      BUDGET.all_cats = ret[1]
      open_cats = []
      for category in self.expense_categories.get_components():
        # find if opened or not:
        if (
          category.link_1.icon == "fa:angle-down"
          and category.item["category_id"] == self.category_right
        ):
          open_cats.append(category.item["category_id"])
      for oc in open_cats:
        print("budget line 257 check open cats", oc)
      self.expense_categories.items = []
      self.expense_categories.items = sorted(
        [c for c in BUDGET.all_cats if c["name"] != "Income"], key=lambda i: i["order"]
      )
      if open_cats:
        for category in self.expense_categories.get_components():
          if category.item["category_id"] in open_cats:
            category.link_1_click()
    elif ret[0] != None:
      BUDGET.all_sub_cats = ret[1]
      # ret[0] is belongs_to. Find object and reload.
      for category in self.expense_categories.get_components():
        if category.item["category_id"] == ret[0]:
          category.refresh_sub_cats()
          # for sub_cat in category.repeating_panel_1.get_components():
          #   if sub_cat.item['sub_category_id'] == self.category_right:
          #     sub_cat.link_1_click()
          #     break

  def name_change(self, **event_args):
    ret = anvil.server.call(
      "name_change", cat_id=self.category_right, new_name=self.edit_name.text
    )

  def live_name_update(self, **event_args):
    # print(self.cat_sub_cat)
    if self.cat_sub_cat == "":
      # update the category
      for category in self.expense_categories.get_components():
        if category.item["category_id"] == self.category_right:
          category.name_label.text = self.edit_name.text
          break
    else:
      # update the sub_category
      # print('fired')

      for category in self.expense_categories.get_components():
        # print(category.item['name'],category.item['category_id'])
        if category.item["category_id"] == self.cat_sub_cat:
          # print('......fired!')
          for sub_cat in category.repeating_panel_1.get_components():
            # print(sub_cat.item['name'],sub_cat.item['sub_category_id'],self.category_right)
            if sub_cat.item["sub_category_id"] == self.category_right:
              sub_cat.sub_cat_name.text = self.edit_name.text
              sub_cat.sub_cat_name_edit.text = self.edit_name.text
              break

  def close_cat_click(self, **event_args):
    self.reset_sub_categories(cat="")
    self.close_cat.visible = False
    self.label_2.text = ""
    self.column_panel_2.visible = False
    self.edit_card.visible = False

  def archive_click(self, **event_args):
    if alert(
      "Archive {c}? You can undo this in settings later.".format(c=self.label_2.text),
      title="Archive a category",
      buttons=[("Cancel", False), ("Archive", True)],
    ):
      anvil.server.call("archive", b_to=self.cat_sub_cat, cat_id=self.category_right)
      self.close_cat_click()
      # run a refresh of categories
      # use cat_sub_cat for knowing if cat or sub_cat
      if self.cat_sub_cat == "":
        cats = []
        for cat in app_tables.categories.search(
          q.not_(order=-1), tables.order_by("order")
        ):
          cat_d = {}
          cat_d = dict(cat)
          if cat_d["name"] != "Income":
            cats.append(cat_d)
        open = False
        for category in self.expense_categories.get_components():
          # find if opened or not:
          if (
            category.link_1.icon == "fa:angle-down"
            and category.item["category_id"] == self.category_right
          ):
            open = True
        self.expense_categories.items = []
        self.expense_categories.items = cats
        if open:
          for category in self.expense_categories.get_components():
            if category.item["category_id"] == self.category_right:
              category.link_1_click()
      else:
        # Sub_cat. Find it and reload.
        for category in self.expense_categories.get_components():
          if category.item["category_id"] == self.cat_sub_cat:
            category.refresh_sub_cats()

  def roll_over_change(self, **event_args):
    app_tables.sub_categories.get(sub_category_id=self.category_right)["roll_over"] = (
      self.roll_over.checked
    )
    if self.roll_over.checked:
      self.drop_down_1.visible = True
      self.drop_down_1.selected_value = None
    else:
      self.drop_down_1.visible = False
      app_tables.sub_categories.get(sub_category_id=self.category_right)[
        "roll_over_date"
      ] = None

  def drop_down_1_change(self, **event_args):
    r_o_d = date(
      self.drop_down_1.selected_value[1], self.drop_down_1.selected_value[0], 1
    )
    app_tables.sub_categories.get(sub_category_id=self.category_right)[
      "roll_over_date"
    ] = r_o_d

  def update_numbers(self,expand=True, **event_args):
    """
    Called when needed - budget updated etc
    1. Goes through each cat holder and works out:
      a. Actual spent/earned
      b. Total budget
      c. Adjusts total budget for any roll-overs
      d. Updates category prog bar
    """
    fd, ld = BUDGET.date_me(False)
    
    cat = self.card_2.get_components()[-1]
    if isinstance(cat, Category_holder_mobile):
      a, b = 0, 0
      income_budget, income_actual = 0, 0
      for sub_cat in [
        s for s in BUDGET.all_sub_cats if s["belongs_to"] == cat.item["category_id"]
      ]:
        a += BUDGET.get_actual(id=sub_cat["sub_category_id"])
        try:
          b += [
            budget
            for budget in BUDGET.all_budgets
            if budget["period"] == fd
            and budget["belongs_to"] == sub_cat["sub_category_id"]
          ][0]["budget_amount"]
          # roll-over function. Nah - not sure what to do with roll_over on income
        except:
          b += 0
      income_actual += a
      income_budget += b
  
      self.update_number_writer(b / 100, a, cat)

    expense_budget, expense_actual = 0, 0
    for cat in self.expense_categories.get_components():
      a, b = 0, 0
      for sub_cat in [
        s for s in BUDGET.all_sub_cats if s["belongs_to"] == cat.item["category_id"]
      ]:
        a += BUDGET.get_actual(id=sub_cat["sub_category_id"])
        try:
          """
          We go straight to roll-over function
          this function checks if it's roll-over and calcs the whole line. if it is not RO,
          just returns current period budget.
          """
          b += BUDGET.roll_over_calc(id=sub_cat["sub_category_id"])
        except Exception as e:
          b += 0
          print(e, "\non line 372 of Budget form (roll_over_calc function error)")
      expense_actual += a
      expense_budget += b
      self.update_number_writer(b / 100, a, cat)
    if isinstance(self.card_2.get_components()[-1], Category_holder_mobile):
      self.update_rh_header(income_actual, income_budget, expense_actual, expense_budget, expand)
      self.update_cat_warning()

  def update_cat_warning(self, **event_args):
    fd, ld = BUDGET.date_me(False)
    un_cat = len(
      [
        t
        for t in Global.TRANSACTIONS
        if t["date"] >= fd and t["date"] <= ld and t["category"] == None
      ]
    )
    warning = "{n} uncategorised transactions for this month".format(n=un_cat)
    self.label_uncat.text = "All transactions categorised!" if un_cat == 0 else warning
    self.label_uncat.foreground = (
      "theme:Amount Negative" if un_cat > 0 else "theme:Primary"
    )
    self.fix_it.foreground = "theme:Amount Negative" if un_cat > 0 else "green"
    self.fix_it.text = "FIX IT!" if un_cat > 0 else "YOU ROCK!"
    self.fix_it.role = "button-orange" if un_cat > 0 else "button-green"
    self.fix_it.enabled = True if un_cat > 0 else False

  def update_rh_header(self, i_a, i_b, e_a, e_b, expand=True, **event_args):
    self.grid_panel_1.clear()
    #DATA
    e_v = e_a - (e_b / 100)
    i_v = i_a - (i_b / 100)
    budget_in = (
      "(R{b:,.2f})".format(b=-i_b / 100) if i_b < 0 else "R{b:,.2f}".format(b=i_b / 100)
    )
    variance_in = (
      "(R{b:,.2f})".format(b=-i_v) if i_v < 0 else "R{b:,.2f}".format(b=i_v)
    )
    actual_in = (
      "(R{b:,.2f})".format(b=-i_a) if i_a < 0 else "R{b:,.2f}".format(b=i_a)
    )
    variance_in_foreground = (
      "theme:Amount Negative" if i_v < 0 else "theme:Primary"
    )

    budget_out = (
      "(R{b:,.2f})".format(b=-e_b / 100) if e_b < 0 else "R{b:,.2f}".format(b=e_b / 100)
    )
    variance_out = (
      "(R{b:,.2f})".format(b=-e_v) if e_v < 0 else "R{b:,.2f}".format(b=e_v)
    )
    actual_out = (
      "(R{b:,.2f})".format(b=-e_a) if e_a < 0 else "R{b:,.2f}".format(b=e_a)
    )
    budget_out_foreground = "theme:Amount Negative" if e_b < 0 else "theme:Primary"
    variance_out_foreground = (
      "theme:Amount Negative" if e_v < 0 else "theme:Primary"
    )
    actual_out_foreground = "theme:Amount Negative" if e_a < 0 else "theme:Primary"
    # DATA WRITE header
    i = 'fa:chevron-down' if expand else 'fa:chevron-up'
    b=Button(role='button-blue',
             foreground='blue',
             icon=i,
            text='')
    b.set_event_handler('click',self.change_grid)
    self.grid_panel_1.add_component(Label(text="Income",foreground="theme:Primary"),
                                   col_xs=1,width_xs=4,row="Header")
    self.grid_panel_1.add_component(b,
                                   col_xs=5,width_xs=2,row="Header")
    self.grid_panel_1.add_component(Label(text="Expenses",foreground="theme:Negative Amount"),
                                    col_xs=7,width_xs=5,row="Header")
    if expand:
      self.grid_panel_1.add_component(Label(text=budget_in),
                                      col_xs=1,width_xs=4,row="Budget")
      self.grid_panel_1.add_component(Label(text="Budget"),
                                      col_xs=5,width_xs=2,row="Budget")
      self.grid_panel_1.add_component(Label(text=budget_out),
                                      col_xs=7,width_xs=5,row="Budget")
      self.grid_panel_1.add_component(Label(text=variance_in,
                                            foreground=variance_in_foreground),
                                      col_xs=1,width_xs=4,row="Variance")
      self.grid_panel_1.add_component(Label(text="Variance"),
                                      col_xs=5,width_xs=2,row="Variance")
      self.grid_panel_1.add_component(Label(text=variance_out,
                                          foreground=variance_out_foreground),
                                      col_xs=7,width_xs=5,row="Variance")
      self.grid_panel_1.add_component(Label(text=actual_in),
                                      col_xs=1,width_xs=4,row="Actuals")
      self.grid_panel_1.add_component(Label(text="Actual"),
                                      col_xs=5,width_xs=2,row="Actuals")
      self.grid_panel_1.add_component(Label(text=actual_out,
                                            foreground=actual_out_foreground),
                                      col_xs=7,width_xs=5,row="Actuals")
    
    for th in self.grid_panel_1.get_components():
      th.spacing_above="none"
      th.spacing_below="none"
      th.font_size = 18

  def change_grid(self,**event_args):
    if event_args['sender'].icon == 'fa:chevron-down':
      event_args['sender'].icon = 'fa:chevron-up'
      self.update_numbers(False)
      anvil.js.window.document.documentElement.style.setProperty(
        "--mobile-headerbudget", "395px"
      )
    else:
      event_args['sender'].icon = 'fa:chevron-down'
      self.update_numbers(True)
      anvil.js.window.document.documentElement.style.setProperty(
        "--mobile-headerbudget", "540px"
      )

  def update_number_writer(self, b, a, comp, **event_args):
    """
    Writes a Category holders header bar
    comp is the actual instance of the category bar
    a is the total actual spent/earned for the cat
    b is the total budgeted for the cat
    """
    comp.actual.text = (
      "(R {actual:.2f})".format(actual=-a)
      if a < 0
      else "R {actual:.2f}".format(actual=a)
    )
    comp.budget.text = "({b:.2f})".format(b=-b) if b < 0 else "{b:.2f}".format(b=b)
    # income bars are different
    maxi, min, v = 0, 0, 0
    if BUDGET.is_income(comp.item["category_id"]):
      comp.progress_bar_1.min_value = 0
      comp.progress_bar_1.max_value = max(b, a)
      comp.progress_bar_1.value = a
    else:
      # if still have budget, set a standard zero point at 25% of the bar.
      # if budget exceeded, set equal min point to max, zero halfway
      # if spend exceeds double of budget, set zero at 75%
      if a >= b and b != 0:
        maxi = -b
        min = b / 4
        v = -(b - a)
      elif a < b and a >= 2 * b:
        maxi = -b
        min = b
        v = a - b
      elif a < b and a < 2 * b:
        maxi = -a / 4
        min = a
        v = a
      elif a == 0 and b == 0:
        maxi = 10.0
        min = -10.0
        v = 0.0
      else:
        maxi = 10.0
        min = -10.0
        v = 0.0
      comp.progress_bar_1.min_value = min
      comp.progress_bar_1.max_value = maxi
      comp.progress_bar_1.value = v

  def a_colour_change(self, **event_args):
    for cat in self.expense_categories.get_components():
      if cat.item["category_id"] == self.category_right:
        # we have our category
        new = {
          "colour_text": self.text_colour.get_color(),
          "colour_back": self.bg_colour.get_color(),
        }
        app_tables.categories.get(category_id=self.category_right).update(**new)
        cat.item["colour_back"] = new["colour_back"]
        cat.item["colour_text"] = new["colour_text"]
        cat.form_show()
        i = BUDGET.all_cats.index(
          [c for c in BUDGET.all_cats if c["category_id"] == self.category_right][0]
        )
        BUDGET.all_cats[i]["colour_back"] = new["colour_back"]
        BUDGET.all_cats[i]["colour_text"] = new["colour_text"]
        break

  def fix_it_click(self, **event_args):
    fd, ld = BUDGET.date_me(False)
    Global.Transactions_Form.remove_from_parent()
    Global.Transactions_Form.dash = False
    Global.Transactions_Form.sub_cat = ("category", None)
    trigger = alert(
      Global.Transactions_Form,
      title="Uncategorised transactions for {f} to {l}".format(f=fd, l=ld),
      buttons=[("Done", False), ("Go to Transactions", True)],
      large=True,
    )
    if trigger:
      Global.Transactions_Form.remove_from_parent()
      Global.Transactions_Form.sub_cat = None
      get_open_form().transactions_page_link_click()
