"""MIS Report center: the All Report button grid and every report it produces."""

from __future__ import annotations

from datetime import date

from .qt import *
from .db import db, money
from .widgets import DIALOG_QSS, dedit, pydate, html_table, preview_html, info


class DateRangeDialog(QDialog):
    """From/To picker used by most reports."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setStyleSheet(DIALOG_QSS)
        lay = QVBoxLayout(self)
        row = QHBoxLayout()
        self.from_date = dedit(date.today().replace(day=1))
        self.to_date = dedit()
        row.addWidget(QLabel("From Date"))
        row.addWidget(self.from_date)
        row.addWidget(QLabel("To"))
        row.addWidget(self.to_date)
        lay.addLayout(row)
        btns = QHBoxLayout()
        ok = QPushButton("Preview"); ok.clicked.connect(self.accept)
        close = QPushButton("Close"); close.clicked.connect(self.reject)
        btns.addStretch(1); btns.addWidget(ok); btns.addWidget(close)
        lay.addLayout(btns)

    @staticmethod
    def get(title, parent) -> tuple[date, date] | None:
        dlg = DateRangeDialog(title, parent)
        if dlg.exec():
            return pydate(dlg.from_date), pydate(dlg.to_date)
        return None


def _f(v):
    return float(v or 0)


class Reports:
    """Every report returns (title, body_html)."""

    def __init__(self, parent):
        self.parent = parent

    def _range(self, title) -> tuple[date, date] | None:
        return DateRangeDialog.get(title, self.parent)

    def show(self, title, body):
        preview_html(self.parent, title, body)

    # -- basic ---------------------------------------------------------------
    def product_information(self):
        rows = db().fetch_all(
            """SELECT p.code, p.model_name, cat.name AS category, com.name AS company,
                      p.stock_qty, p.purchase_rate, p.sales_rate, p.mrp_rate
               FROM products p
               LEFT JOIN categories cat ON cat.id = p.category_id
               LEFT JOIN companies com ON com.id = p.company_id ORDER BY p.code""")
        self.show("Product Information", html_table(
            ["Code", "Model", "Category", "Company", "Stock", "Pur.Rate", "Sales Rate", "MRP"],
            [[r["code"], r["model_name"], r["category"], r["company"], _f(r["stock_qty"]),
              _f(r["purchase_rate"]), _f(r["sales_rate"]), _f(r["mrp_rate"])] for r in rows]))

    def employee_information(self):
        rows = db().fetch_all(
            """SELECT code, name, contact_no, designation, joining_date, gross_salary
               FROM employees ORDER BY code""")
        self.show("Employee Information", html_table(
            ["Code", "Name", "Contact No", "Designation", "Joining Date", "Gross Salary"],
            [[r["code"], r["name"], r["contact_no"], r["designation"],
              r["joining_date"].strftime("%d %b %Y"), _f(r["gross_salary"])] for r in rows]))

    def customer_due(self):
        rows = db().fetch_all(
            """SELECT c.customer_type, c.code, c.name, c.contact_no, c.address, d.total_due
               FROM customers c JOIN customer_dues d ON d.id = c.id
               WHERE d.total_due <> 0 ORDER BY c.name""")
        self.show("Due Customer List", html_table(
            ["Cus Type", "Code", "Customer Name", "Contact No", "Address", "Total Due"],
            [[r["customer_type"], r["code"], r["name"], r["contact_no"], r["address"],
              _f(r["total_due"])] for r in rows],
            ["Total", "", "", "", "", _f(sum(r["total_due"] for r in rows))]))

    def supplier_due(self):
        rows = db().fetch_all(
            """SELECT s.code, s.name, s.contact_no, s.address, d.total_due
               FROM suppliers s JOIN supplier_dues d ON d.id = s.id
               WHERE d.total_due <> 0 ORDER BY s.name""")
        self.show("Supplier Due Report", html_table(
            ["Code", "Supplier Name", "Contact No", "Address", "Total Due"],
            [[r["code"], r["name"], r["contact_no"], r["address"], _f(r["total_due"])]
             for r in rows],
            ["Total", "", "", "", _f(sum(r["total_due"] for r in rows))]))

    def stock_report(self):
        rows = db().fetch_all(
            """SELECT p.code, p.model_name, cat.name AS category, com.name AS company,
                      p.stock_qty, p.purchase_rate, p.stock_qty * p.purchase_rate AS value
               FROM products p
               LEFT JOIN categories cat ON cat.id = p.category_id
               LEFT JOIN companies com ON com.id = p.company_id
               WHERE p.stock_qty <> 0 ORDER BY p.code""")
        self.show("Available Stock Info", html_table(
            ["Code", "Product", "Category", "Company", "Qty", "Pur.Rate", "Total Price"],
            [[r["code"], r["model_name"], r["category"], r["company"], _f(r["stock_qty"]),
              _f(r["purchase_rate"]), _f(r["value"])] for r in rows],
            ["Total", "", "", "", _f(sum(r["stock_qty"] for r in rows)), None,
             _f(sum(r["value"] for r in rows))]))

    def expense_income(self):
        rng = self._range("Expense and Income Report")
        if not rng:
            return
        inc = db().fetch_all(
            """SELECT income_date AS d, description, amount FROM incomes
               WHERE income_date BETWEEN %s AND %s ORDER BY income_date""", rng)
        exp = db().fetch_all(
            """SELECT expense_date AS d, description, amount FROM expenses
               WHERE expense_date BETWEEN %s AND %s ORDER BY expense_date""", rng)
        body = ("<h4>Income</h4>" + html_table(
                    ["Date", "Description", "Amount"],
                    [[r["d"].strftime("%d %b %Y"), r["description"], _f(r["amount"])] for r in inc],
                    ["Total", "", _f(sum(r["amount"] for r in inc))])
                + "<h4>Expense</h4>" + html_table(
                    ["Date", "Description", "Amount"],
                    [[r["d"].strftime("%d %b %Y"), r["description"], _f(r["amount"])] for r in exp],
                    ["Total", "", _f(sum(r["amount"] for r in exp))]))
        self.show(f"Expense and Income: {rng[0]:%d %b %Y} to {rng[1]:%d %b %Y}", body)

    def upcoming_installments(self):
        rows = db().fetch_all(
            """SELECT i.schedule_date, s.invoice_no, c.name, c.contact_no, i.amount
               FROM installments i JOIN sales s ON s.id = i.sale_id
               JOIN customers c ON c.id = s.customer_id
               WHERE i.status = 'Due' AND i.schedule_date >= CURRENT_DATE
               ORDER BY i.schedule_date LIMIT 200""")
        self.show("Upcoming Installment", html_table(
            ["Schedule", "Invoice No", "Customer", "Contact No", "Amount"],
            [[r["schedule_date"].strftime("%d %b %Y"), r["invoice_no"], r["name"],
              r["contact_no"], _f(r["amount"])] for r in rows],
            ["Total", "", "", "", _f(sum(r["amount"] for r in rows))]))

    def installment_collection(self):
        rng = self._range("Installment Collection")
        if not rng:
            return
        rows = db().fetch_all(
            """SELECT i.paid_date, s.invoice_no, c.name, i.paid_amount
               FROM installments i JOIN sales s ON s.id = i.sale_id
               JOIN customers c ON c.id = s.customer_id
               WHERE i.status = 'Paid' AND i.paid_date BETWEEN %s AND %s
               ORDER BY i.paid_date""", rng)
        self.show("Installment Collection", html_table(
            ["Pay Date", "Invoice No", "Customer", "Amount"],
            [[r["paid_date"].strftime("%d %b %Y"), r["invoice_no"], r["name"],
              _f(r["paid_amount"])] for r in rows],
            ["Total", "", "", _f(sum(r["paid_amount"] for r in rows))]))

    def defaulting_customers(self):
        rows = db().fetch_all(
            """SELECT DISTINCT c.code, c.name, c.contact_no, c.address, d.total_due
               FROM installments i JOIN sales s ON s.id = i.sale_id
               JOIN customers c ON c.id = s.customer_id
               JOIN customer_dues d ON d.id = c.id
               WHERE i.status = 'Due' AND i.schedule_date < CURRENT_DATE
               ORDER BY c.name""")
        self.show("Defaulting Customer List", html_table(
            ["Code", "Customer Name", "Contact No", "Address", "Total Due"],
            [[r["code"], r["name"], r["contact_no"], r["address"], _f(r["total_due"])]
             for r in rows]))

    # -- sales / purchase ------------------------------------------------------
    def _sales_grouped(self, group_expr: str, label: str, rng):
        rows = db().fetch_all(
            f"""SELECT {group_expr} AS grp, SUM(gross_total) AS total_sales,
                       SUM(flat_discount) AS discount, SUM(net_total) AS net,
                       SUM(paid_amount) AS received,
                       SUM(net_total - paid_amount) AS due
                FROM sales WHERE sales_date BETWEEN %s AND %s
                GROUP BY grp ORDER BY grp""", rng)
        self.show(label, html_table(
            ["Date", "Total Sales", "Discount/Adjust", "Net Sales", "Receive Amt", "Due"],
            [[str(r["grp"]), _f(r["total_sales"]), _f(r["discount"]), _f(r["net"]),
              _f(r["received"]), _f(r["due"])] for r in rows],
            ["Total", _f(sum(r["total_sales"] for r in rows)),
             _f(sum(r["discount"] for r in rows)), _f(sum(r["net"] for r in rows)),
             _f(sum(r["received"] for r in rows)), _f(sum(r["due"] for r in rows))]))

    def daily_sales(self):
        rng = self._range("Daily Sales Report")
        if rng:
            self._sales_grouped("sales_date", f"Sales From {rng[0]:%d %b %Y} To {rng[1]:%d %b %Y}", rng)

    def monthly_sales(self):
        rng = self._range("Monthly Sales Report")
        if rng:
            self._sales_grouped("to_char(sales_date, 'YYYY Mon')",
                                f"Monthly Sales: {rng[0]:%b %Y} to {rng[1]:%b %Y}", rng)

    def yearly_sales(self):
        rng = self._range("Yearly Sales Report")
        if rng:
            self._sales_grouped("extract(year from sales_date)::int",
                                f"Sales For the Year", rng)

    def _purchase_grouped(self, group_expr: str, label: str, rng):
        rows = db().fetch_all(
            f"""SELECT {group_expr} AS grp, SUM(gross_total) AS total,
                       SUM(flat_discount) AS discount, SUM(net_total) AS net,
                       SUM(paid_amount) AS paid, SUM(net_total - paid_amount) AS due
                FROM purchases WHERE purchase_date BETWEEN %s AND %s
                GROUP BY grp ORDER BY grp""", rng)
        self.show(label, html_table(
            ["Date", "Total Purchase", "Discount", "Net Purchase", "Paid Amt", "Due"],
            [[str(r["grp"]), _f(r["total"]), _f(r["discount"]), _f(r["net"]), _f(r["paid"]),
              _f(r["due"])] for r in rows],
            ["Total", _f(sum(r["total"] for r in rows)), _f(sum(r["discount"] for r in rows)),
             _f(sum(r["net"] for r in rows)), _f(sum(r["paid"] for r in rows)),
             _f(sum(r["due"] for r in rows))]))

    def daily_purchase(self):
        rng = self._range("Daily Purchase Report")
        if rng:
            self._purchase_grouped("purchase_date",
                                   f"Purchase From {rng[0]:%d %b %Y} To {rng[1]:%d %b %Y}", rng)

    def monthly_purchase(self):
        rng = self._range("Monthly Purchase Report")
        if rng:
            self._purchase_grouped("to_char(purchase_date, 'YYYY Mon')", "Monthly Purchase Report", rng)

    def yearly_purchase(self):
        rng = self._range("Yearly Purchase Report")
        if rng:
            self._purchase_grouped("extract(year from purchase_date)::int", "Yearly Purchase Report", rng)

    def customer_wise_sales(self):
        rng = self._range("Customer Wise Sales")
        if not rng:
            return
        rows = db().fetch_all(
            """SELECT c.code, c.name, COUNT(s.id) AS orders, SUM(s.net_total) AS net,
                      SUM(s.paid_amount) AS paid, SUM(s.net_total - s.paid_amount) AS due
               FROM sales s JOIN customers c ON c.id = s.customer_id
               WHERE s.sales_date BETWEEN %s AND %s
               GROUP BY c.code, c.name ORDER BY c.name""", rng)
        self.show("Customer Wise Sales", html_table(
            ["Code", "Customer", "Orders", "Net Sales", "Received", "Due"],
            [[r["code"], r["name"], r["orders"], _f(r["net"]), _f(r["paid"]), _f(r["due"])]
             for r in rows],
            ["Total", "", "", _f(sum(r["net"] for r in rows)),
             _f(sum(r["paid"] for r in rows)), _f(sum(r["due"] for r in rows))]))

    def supplier_wise_purchase(self):
        rng = self._range("Supplier Wise Purchase")
        if not rng:
            return
        rows = db().fetch_all(
            """SELECT s.code, s.name, COUNT(p.id) AS orders, SUM(p.net_total) AS net,
                      SUM(p.paid_amount) AS paid, SUM(p.net_total - p.paid_amount) AS due
               FROM purchases p JOIN suppliers s ON s.id = p.supplier_id
               WHERE p.purchase_date BETWEEN %s AND %s
               GROUP BY s.code, s.name ORDER BY s.name""", rng)
        self.show("Supplier Wise Purchase", html_table(
            ["Code", "Supplier", "Orders", "Net Purchase", "Paid", "Due"],
            [[r["code"], r["name"], r["orders"], _f(r["net"]), _f(r["paid"]), _f(r["due"])]
             for r in rows]))

    def customer_ledger(self):
        from .widgets import PickerDialog
        from .inventory import CUSTOMER_PICK_SQL
        rec = PickerDialog.pick("Customers", ["Code", "Name", "Contact", "Address", "Due"],
                                CUSTOMER_PICK_SQL, self.parent)
        if not rec:
            return
        sales = db().fetch_all(
            """SELECT sales_date AS d, 'Sale ' || invoice_no AS what, net_total AS debit,
                      paid_amount AS credit
               FROM sales WHERE customer_id = %s
               UNION ALL
               SELECT entry_date, 'Collection ' || receipt_no, 0, amount + adjustment
               FROM cash_collections WHERE customer_id = %s
               ORDER BY d""", (rec["id"], rec["id"]))
        balance = _f(db().scalar("SELECT opening_due FROM customers WHERE id = %s", (rec["id"],)))
        rows = [["", "Opening Due", None, None, balance]]
        for r in sales:
            balance += _f(r["debit"]) - _f(r["credit"])
            rows.append([r["d"].strftime("%d %b %Y"), r["what"], _f(r["debit"]),
                         _f(r["credit"]), balance])
        self.show(f"Customer Ledger — {rec['name']}",
                  html_table(["Date", "Particulars", "Debit", "Credit", "Balance"], rows))

    def supplier_ledger(self):
        from .widgets import PickerDialog
        from .inventory import SUPPLIER_PICK_SQL
        rec = PickerDialog.pick("All Suppliers", ["Code", "Name", "Contact No", "Total Due"],
                                SUPPLIER_PICK_SQL, self.parent)
        if not rec:
            return
        entries = db().fetch_all(
            """SELECT purchase_date AS d, 'Purchase ' || challan_no AS what,
                      net_total AS debit, paid_amount AS credit
               FROM purchases WHERE supplier_id = %s
               UNION ALL
               SELECT entry_date, 'Payment ' || voucher_no, 0, amount
               FROM cash_deliveries WHERE supplier_id = %s
               ORDER BY d""", (rec["id"], rec["id"]))
        balance = _f(db().scalar("SELECT opening_due FROM suppliers WHERE id = %s", (rec["id"],)))
        rows = [["", "Opening Due", None, None, balance]]
        for r in entries:
            balance += _f(r["debit"]) - _f(r["credit"])
            rows.append([r["d"].strftime("%d %b %Y"), r["what"], _f(r["debit"]),
                         _f(r["credit"]), balance])
        self.show(f"Supplier Ledger — {rec['name']}",
                  html_table(["Date", "Particulars", "Debit", "Credit", "Balance"], rows))

    def bank_ledger(self):
        rng = self._range("Bank Ledger")
        if not rng:
            return
        rows = db().fetch_all(
            """SELECT t.entry_date, t.tran_no, b.name AS bank, t.tran_type, t.amount, t.remarks
               FROM bank_transactions t LEFT JOIN banks b ON b.id = t.bank_id
               WHERE t.entry_date BETWEEN %s AND %s ORDER BY t.entry_date""", rng)
        if not rows:
            info(self.parent, "No Record Found.")
            return
        self.show("Bank Ledger", html_table(
            ["Date", "Tran No", "Bank", "Type", "Amount", "Remarks"],
            [[r["entry_date"].strftime("%d %b %Y"), r["tran_no"], r["bank"], r["tran_type"],
              _f(r["amount"]), r["remarks"]] for r in rows]))

    def cash_receive_delivery(self):
        rng = self._range("Cash Receive and Delivery")
        if not rng:
            return
        rec = db().fetch_all(
            """SELECT cc.entry_date AS d, c.name, cc.amount FROM cash_collections cc
               JOIN customers c ON c.id = cc.customer_id
               WHERE cc.entry_date BETWEEN %s AND %s ORDER BY cc.entry_date""", rng)
        pay = db().fetch_all(
            """SELECT cd.entry_date AS d, s.name, cd.amount FROM cash_deliveries cd
               JOIN suppliers s ON s.id = cd.supplier_id
               WHERE cd.entry_date BETWEEN %s AND %s ORDER BY cd.entry_date""", rng)
        body = ("<h4>Cash Receive (from customers)</h4>" + html_table(
                    ["Date", "Customer", "Amount"],
                    [[r["d"].strftime("%d %b %Y"), r["name"], _f(r["amount"])] for r in rec],
                    ["Total", "", _f(sum(r["amount"] for r in rec))])
                + "<h4>Cash Delivery (to suppliers)</h4>" + html_table(
                    ["Date", "Supplier", "Amount"],
                    [[r["d"].strftime("%d %b %Y"), r["name"], _f(r["amount"])] for r in pay],
                    ["Total", "", _f(sum(r["amount"] for r in pay))]))
        self.show("Cash Receive and Delivery", body)

    def product_wise_sales_purchase(self):
        rng = self._range("Product Wise Sales and Purchase")
        if not rng:
            return
        rows = db().fetch_all(
            """SELECT p.code, p.model_name,
                      COALESCE((SELECT SUM(pi.qty) FROM purchase_items pi
                                JOIN purchases pu ON pu.id = pi.purchase_id
                                WHERE pi.product_id = p.id
                                  AND pu.purchase_date BETWEEN %s AND %s), 0) AS bought,
                      COALESCE((SELECT SUM(si.qty) FROM sale_items si
                                JOIN sales s ON s.id = si.sale_id
                                WHERE si.product_id = p.id
                                  AND s.sales_date BETWEEN %s AND %s), 0) AS sold,
                      p.stock_qty
               FROM products p ORDER BY p.code""", rng + rng)
        self.show("Product Wise Sales and Purchase", html_table(
            ["Code", "Product", "Purchased Qty", "Sold Qty", "Current Stock"],
            [[r["code"], r["model_name"], _f(r["bought"]), _f(r["sold"]), _f(r["stock_qty"])]
             for r in rows]))

    def company_benefit(self):
        rng = self._range("Company Benefit (By Product)")
        if not rng:
            return
        rows = db().fetch_all(
            """SELECT p.code, p.model_name, SUM(si.qty) AS qty, SUM(si.total) AS sold_amt,
                      SUM(si.qty * p.purchase_rate) AS cost
               FROM sale_items si JOIN sales s ON s.id = si.sale_id
               JOIN products p ON p.id = si.product_id
               WHERE s.sales_date BETWEEN %s AND %s
               GROUP BY p.code, p.model_name ORDER BY p.code""", rng)
        self.show("Company Benefit (By Product)", html_table(
            ["Code", "Product", "Qty", "Sales Amt", "Cost", "Benefit"],
            [[r["code"], r["model_name"], _f(r["qty"]), _f(r["sold_amt"]), _f(r["cost"]),
              _f(r["sold_amt"]) - _f(r["cost"])] for r in rows]))

    def customer_wise_benefit(self):
        rng = self._range("Customer Wise Benefit")
        if not rng:
            return
        rows = db().fetch_all(
            """SELECT c.name, SUM(si.total) AS sold_amt, SUM(si.qty * p.purchase_rate) AS cost
               FROM sale_items si JOIN sales s ON s.id = si.sale_id
               JOIN customers c ON c.id = s.customer_id
               JOIN products p ON p.id = si.product_id
               WHERE s.sales_date BETWEEN %s AND %s GROUP BY c.name ORDER BY c.name""", rng)
        self.show("Customer Wise Benefit", html_table(
            ["Customer", "Sales Amt", "Cost", "Benefit"],
            [[r["name"], _f(r["sold_amt"]), _f(r["cost"]),
              _f(r["sold_amt"]) - _f(r["cost"])] for r in rows]))

    def customer_wise_returns(self):
        rows = db().fetch_all(
            """SELECT r.return_date, r.return_no, s.invoice_no, c.name, r.net_total,
                      r.back_amount
               FROM sales_returns r JOIN sales s ON s.id = r.sale_id
               JOIN customers c ON c.id = s.customer_id ORDER BY r.return_date DESC""")
        self.show("Customer Wise Returns Details", html_table(
            ["Return Date", "Return No", "Invoice", "Customer", "Net Total", "Back Amount"],
            [[r["return_date"].strftime("%d %b %Y"), r["return_no"], r["invoice_no"],
              r["name"], _f(r["net_total"]), _f(r["back_amount"])] for r in rows]))

    def cash_in_hand(self):
        rng = self._range("Cash In Hand")
        if not rng:
            return
        q = lambda sql: _f(db().scalar(sql, rng))
        cash_sales = q("SELECT SUM(paid_amount) FROM sales WHERE sales_date BETWEEN %s AND %s")
        collections = q("SELECT SUM(amount) FROM cash_collections WHERE entry_date BETWEEN %s AND %s")
        other_income = q("SELECT SUM(amount) FROM incomes WHERE income_date BETWEEN %s AND %s")
        cash_paid = q("SELECT SUM(paid_amount) FROM purchases WHERE purchase_date BETWEEN %s AND %s")
        deliveries = q("SELECT SUM(amount) FROM cash_deliveries WHERE entry_date BETWEEN %s AND %s")
        expense = q("SELECT SUM(amount) FROM expenses WHERE expense_date BETWEEN %s AND %s")
        returns = q("SELECT SUM(back_amount) FROM sales_returns WHERE return_date BETWEEN %s AND %s")
        debit = cash_sales + collections + other_income
        credit = cash_paid + deliveries + expense + returns
        body = html_table(
            ["Debit Patriculars", "Debit Amt.", "Credit Patriculars", "Credit Amt."],
            [["Cash Sales", cash_sales, "Cash Paid (purchase)", cash_paid],
             ["Cash Collection From Customer", collections, "Cash Delivery to Supplier", deliveries],
             ["Other Income", other_income, "Expense", expense],
             ["", None, "Sales Return Refund", returns],
             ["Total Debit", debit, "Total Credit", credit],
             ["", None, "Current Cash In Hand", debit - credit]])
        self.show(f"Cash In Hand Report: From {rng[0]:%d %b %Y} to {rng[1]:%d %b %Y}", body)

    def profit_and_loss(self):
        rng = self._range("Profit and Loss")
        if not rng:
            return
        q = lambda sql: _f(db().scalar(sql, rng))
        sales_amt = q("SELECT SUM(si.total) FROM sale_items si JOIN sales s ON s.id = si.sale_id "
                      "WHERE s.sales_date BETWEEN %s AND %s")
        cogs = q("SELECT SUM(si.qty * p.purchase_rate) FROM sale_items si "
                 "JOIN sales s ON s.id = si.sale_id JOIN products p ON p.id = si.product_id "
                 "WHERE s.sales_date BETWEEN %s AND %s")
        discount = q("SELECT SUM(flat_discount) FROM sales WHERE sales_date BETWEEN %s AND %s")
        other_income = q("SELECT SUM(amount) FROM incomes WHERE income_date BETWEEN %s AND %s")
        expense = q("SELECT SUM(amount) FROM expenses WHERE expense_date BETWEEN %s AND %s")
        interest = q("SELECT SUM(interest_amount) FROM sales WHERE sales_date BETWEEN %s AND %s")
        gross = sales_amt - cogs
        net = gross - discount + other_income + interest - expense
        body = html_table(["Particulars", "Amount"],
                          [["Sales Amount", sales_amt],
                           ["Cost of Goods Sold", cogs],
                           ["Gross Profit", gross],
                           ["(-) Discount", discount],
                           ["(+) Other Income", other_income],
                           ["(+) Credit Interest", interest],
                           ["(-) Expense", expense],
                           ["Net Profit / (Loss)", net]])
        self.show(f"Profit and Loss: {rng[0]:%d %b %Y} to {rng[1]:%d %b %Y}", body)


class AllReportDialog(QDialog):
    """The 'All Report' button grid, matching the video layout."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("All Report")
        self.setMinimumSize(880, 480)
        self.setStyleSheet(DIALOG_QSS + "QPushButton { min-height: 46px; }")
        self.reports = Reports(self)
        lay = QVBoxLayout(self)

        basic = QGroupBox("Basic Report")
        bgrid = QGridLayout(basic)
        self._add_buttons(bgrid, [
            ("Product\nInformation", self.reports.product_information),
            ("Employee\nInformation", self.reports.employee_information),
            ("Customer\nDue Report", self.reports.customer_due),
            ("Supplier Due\nReport", self.reports.supplier_due),
            ("Stock Report", self.reports.stock_report),
            ("Expense and\nIncome Report", self.reports.expense_income),
            ("Upcoming\nInstallment", self.reports.upcoming_installments),
            ("Installment\nCollection", self.reports.installment_collection),
            ("Defaulting\nCustomer List", self.reports.defaulting_customers)])
        lay.addWidget(basic)

        sales = QGroupBox("Sales ,Credit Sales, Cash Collection and Purchase Report")
        sgrid = QGridLayout(sales)
        self._add_buttons(sgrid, [
            ("Daily Sales\nReport", self.reports.daily_sales),
            ("Monthly\nSales Report", self.reports.monthly_sales),
            ("Yearly Sales\nReport", self.reports.yearly_sales),
            ("Customer\nWise Sales", self.reports.customer_wise_sales),
            ("Customer\nLedger", self.reports.customer_ledger),
            ("Daily\nPurchase\nReport", self.reports.daily_purchase),
            ("Monthly\nPurchase\nReport", self.reports.monthly_purchase),
            ("Yearly\nPurchase\nReport", self.reports.yearly_purchase),
            ("Supplier\nWise\nPurchase", self.reports.supplier_wise_purchase),
            ("Bank Ledger", self.reports.bank_ledger),
            ("Supplier\nLedger", self.reports.supplier_ledger),
            ("Cash Receive\nand Delivery", self.reports.cash_receive_delivery),
            ("Product Wise\nSales and\nPurchase", self.reports.product_wise_sales_purchase),
            ("Company\nBenefit (By\nProduct)", self.reports.company_benefit),
            ("Customer\nWise Benefit", self.reports.customer_wise_benefit),
            ("Customer\nWise Returns\nDetails", self.reports.customer_wise_returns),
            ("Cash In Hand", self.reports.cash_in_hand),
            ("Profit and\nLoss", self.reports.profit_and_loss)])
        lay.addWidget(sales, 1)

    @staticmethod
    def _add_buttons(grid: QGridLayout, buttons, per_row: int = 9):
        for i, (label, fn) in enumerate(buttons):
            b = QPushButton(label)
            b.clicked.connect(lambda checked=False, f=fn: f())
            grid.addWidget(b, i // per_row, i % per_row)
