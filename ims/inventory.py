"""Inventory Management: Purchase Order, Sales Order, Credit Sales, Return Product."""

from __future__ import annotations

from datetime import date

from .qt import *
from .db import db, money
from .widgets import (DIALOG_QSS, DataTable, ListDialog, LookupField, SearchBar,
                      dedit, pydate, dspin, info, error, confirm,
                      html_table, preview_html)
from .basic import ProductDetailDialog
from .people import CustomerForm, SupplierForm

PRODUCT_PICK_SQL = """
    SELECT p.id, p.code, p.model_name AS name, c.name AS category, p.stock_qty,
           p.purchase_rate, p.sales_rate, p.mrp_rate
    FROM products p LEFT JOIN categories c ON c.id = p.category_id
    WHERE p.company_id = app_company_id()
          AND (p.code ILIKE %s OR p.model_name ILIKE %s) ORDER BY p.code"""

SUPPLIER_PICK_SQL = """
    SELECT s.id, s.code, s.name, s.contact_no, d.total_due
    FROM suppliers s JOIN supplier_dues d ON d.id = s.id
    WHERE s.company_id = app_company_id()
          AND (s.code ILIKE %s OR s.name ILIKE %s) ORDER BY s.name"""

CUSTOMER_PICK_SQL = """
    SELECT c.id, c.code, c.name, c.contact_no, c.address, d.total_due
    FROM customers c JOIN customer_dues d ON d.id = c.id
    WHERE c.company_id = app_company_id()
          AND (c.code ILIKE %s OR c.name ILIKE %s OR c.contact_no ILIKE %s)
    ORDER BY c.name"""


def product_lookup(parent) -> LookupField:
    return LookupField("Products", ["Code", "Model", "Category", "Stock", "Pur.Rate", "Sales Rate", "MRP"],
                       PRODUCT_PICK_SQL, parent,
                       new_form_factory=lambda p: ProductDetailDialog(None, p))


def stock_tab() -> QWidget:
    """The 'Stock' tab shown inside Purchase Orders and Sales Orders windows."""
    w = QWidget()
    lay = QVBoxLayout(w)
    bar = SearchBar()
    lay.addWidget(bar)
    table = DataTable(["Stock Code", "Product Name", "Category", "Brand",
                       "Qty", "Pur.Rate", "MRP", "Total Price"])
    lay.addWidget(table, 1)
    total_lbl = QLabel("Total : 0")
    total_lbl.setStyleSheet("font-weight:bold")
    lay.addWidget(total_lbl)

    def load(search=""):
        rows = db().fetch_all(
            """SELECT p.id, p.code, p.model_name, cat.name AS category, b.name AS brand,
                      p.stock_qty, p.purchase_rate, p.mrp_rate,
                      p.stock_qty * p.purchase_rate AS total_price
               FROM products p
               LEFT JOIN categories cat ON cat.id = p.category_id
               LEFT JOIN brands b ON b.id = p.brand_id
               WHERE p.company_id = app_company_id()
                     AND (p.code ILIKE %s OR p.model_name ILIKE %s OR cat.name ILIKE %s
                          OR b.name ILIKE %s)
               ORDER BY p.code""", (f"%{search}%",) * 4)
        table.set_rows([(r["id"], r["code"], r["model_name"], r["category"], r["brand"],
                         money(r["stock_qty"]), money(r["purchase_rate"]),
                         money(r["mrp_rate"]), money(r["total_price"])) for r in rows])
        total_lbl.setText(f"Total : {len(rows)}")

    bar.searched.connect(load)
    load()
    w.reload = load
    return w


# ---------------------------------------------------------------------------
# Purchase Order

class PurchaseOrderForm(QDialog):
    def __init__(self, rec_id=None, parent=None):
        super().__init__(parent)
        self.rec_id = rec_id
        self.items: list[dict] = []
        self.setWindowTitle("Purchase Order")
        self.setMinimumSize(900, 620)
        self.setStyleSheet(DIALOG_QSS)
        lay = QVBoxLayout(self)

        sbox = QGroupBox("Supplier")
        sgrid = QGridLayout(sbox)
        self.pur_date = dedit()
        self.challan = QLineEdit()
        self.supplier = LookupField("All Suppliers", ["Code", "Name", "Contact No", "Total Due"],
                                    SUPPLIER_PICK_SQL,
                                    new_form_factory=lambda p: SupplierForm(None, p))
        self.supplier.selected.connect(self._supplier_picked)
        self.prev_due = dspin(read_only=True)
        sgrid.addWidget(QLabel("Pur. Date"), 0, 0); sgrid.addWidget(self.pur_date, 0, 1)
        sgrid.addWidget(QLabel("Challan No"), 0, 2); sgrid.addWidget(self.challan, 0, 3)
        sgrid.addWidget(QLabel("Supplier"), 1, 0); sgrid.addWidget(self.supplier, 1, 1, 1, 3)
        sgrid.addWidget(QLabel("Prev. Due"), 2, 0); sgrid.addWidget(self.prev_due, 2, 1)
        lay.addWidget(sbox)

        pbox = QGroupBox("Product")
        pgrid = QGridLayout(pbox)
        self.product = product_lookup(self)
        self.product.selected.connect(self._product_picked)
        self.prv_stock = dspin(read_only=True)
        self.qty = dspin(999999, 2); self.qty.setValue(1)
        self.mrp = dspin()
        self.sales_rate = dspin()
        self.pur_rate = dspin()
        self.dis_pct = dspin(100, 2)
        self.line_total = dspin(read_only=True)
        self._syncing = False
        for w in (self.qty, self.pur_rate):
            w.valueChanged.connect(self._recalc_line)
        for w in (self.mrp, self.pur_rate):
            w.valueChanged.connect(self._recalc_dis)
        self.dis_pct.valueChanged.connect(self._recalc_rate)
        add = QPushButton("Add"); add.clicked.connect(self._add_item)
        remove = QPushButton("Remove"); remove.clicked.connect(self._remove_item)
        pgrid.addWidget(QLabel("Product"), 0, 0); pgrid.addWidget(self.product, 0, 1, 1, 3)
        pgrid.addWidget(QLabel("Prv.Stock"), 0, 4); pgrid.addWidget(self.prv_stock, 0, 5)
        pgrid.addWidget(QLabel("Quantity"), 1, 0); pgrid.addWidget(self.qty, 1, 1)
        pgrid.addWidget(QLabel("MRP Rate"), 1, 2); pgrid.addWidget(self.mrp, 1, 3)
        pgrid.addWidget(QLabel("Total Amt"), 1, 4); pgrid.addWidget(self.line_total, 1, 5)
        pgrid.addWidget(QLabel("Sales Rate"), 2, 0); pgrid.addWidget(self.sales_rate, 2, 1)
        pgrid.addWidget(QLabel("Pur. Rate"), 2, 2); pgrid.addWidget(self.pur_rate, 2, 3)
        pgrid.addWidget(add, 2, 4); pgrid.addWidget(remove, 2, 5)
        pgrid.addWidget(QLabel("PP DIS. %"), 3, 0); pgrid.addWidget(self.dis_pct, 3, 1)
        lay.addWidget(pbox)

        mid = QHBoxLayout()
        self.grid = DataTable(["SN", "Name", "Category", "QTY", "MRP", "Dis(%)", "P.Rate", "Total"])
        mid.addWidget(self.grid, 2)

        totals = QFormLayout()
        self.g_total = dspin(read_only=True)
        self.flat_dis = dspin()
        self.flat_dis.valueChanged.connect(self._recalc_totals)
        self.net_total = dspin(read_only=True)
        self.pay_amount = dspin()
        self.pay_amount.valueChanged.connect(self._recalc_totals)
        self.curr_due = dspin(read_only=True)
        totals.addRow("G.Total", self.g_total)
        totals.addRow("Flat Dis.", self.flat_dis)
        totals.addRow("Net Total", self.net_total)
        totals.addRow("Pay Amount", self.pay_amount)
        totals.addRow("Curr. Due", self.curr_due)
        mid.addLayout(totals, 1)
        lay.addLayout(mid, 1)

        row = QHBoxLayout()
        save = QPushButton("Save"); save.clicked.connect(self.save)
        close = QPushButton("Close"); close.clicked.connect(self.reject)
        row.addStretch(1); row.addWidget(save); row.addWidget(close)
        lay.addLayout(row)

        if rec_id:
            self._load(rec_id)

    def _supplier_picked(self, rec):
        self.prev_due.setValue(float(rec.get("total_due") or 0))

    def _product_picked(self, rec):
        self.prv_stock.setValue(float(rec["stock_qty"]))
        self.mrp.setValue(float(rec["mrp_rate"]))
        self.sales_rate.setValue(float(rec["sales_rate"]))
        self.pur_rate.setValue(float(rec["purchase_rate"]))
        self.qty.setValue(1)
        self._recalc_line()

    def _recalc_dis(self):
        if self._syncing:
            return
        self._syncing = True
        mrp = self.mrp.value()
        if mrp > 0:
            self.dis_pct.setValue((mrp - self.pur_rate.value()) / mrp * 100)
        else:
            self.dis_pct.setValue(0)
        self._syncing = False

    def _recalc_rate(self):
        if self._syncing:
            return
        self._syncing = True
        self.pur_rate.setValue(self.mrp.value() * (1 - self.dis_pct.value() / 100))
        self._syncing = False

    def _recalc_line(self):
        self.line_total.setValue(self.qty.value() * self.pur_rate.value())

    def _add_item(self):
        if not self.product.record:
            info(self, "Select a product first.")
            return
        if self.qty.value() <= 0:
            info(self, "Quantity must be positive.")
            return
        rec = self.product.record
        self.items.append({
            "product_id": rec["id"], "name": rec["name"], "category": rec.get("category", ""),
            "qty": self.qty.value(), "mrp": self.mrp.value(), "dis": self.dis_pct.value(),
            "sales_rate": self.sales_rate.value(), "rate": self.pur_rate.value(),
            "total": self.line_total.value()})
        self.product.set_record(None)
        for w in (self.prv_stock, self.mrp, self.sales_rate, self.pur_rate,
                  self.dis_pct, self.line_total):
            w.setValue(0)
        self.qty.setValue(1)
        self._refresh_grid()

    def _remove_item(self):
        r = self.grid.currentRow()
        if 0 <= r < len(self.items):
            del self.items[r]
            self._refresh_grid()

    def _refresh_grid(self):
        self.grid.set_rows([(n, n + 1, it["name"], it["category"], money(it["qty"]),
                             money(it["mrp"]), money(it["dis"]), money(it["rate"]),
                             money(it["total"]))
                            for n, it in enumerate(self.items)])
        self._recalc_totals()

    def _recalc_totals(self):
        g = sum(it["total"] for it in self.items)
        self.g_total.setValue(g)
        net = g - self.flat_dis.value()
        self.net_total.setValue(net)
        self.curr_due.setValue(net - self.pay_amount.value())

    def _load(self, rec_id):
        p = db().fetch_one("SELECT * FROM purchases WHERE id = %s", (rec_id,))
        d = p["purchase_date"]
        self.pur_date.setDate(QDate(d.year, d.month, d.day))
        self.challan.setText(p["challan_no"])
        self.supplier.set_record(db().fetch_one(
            "SELECT id, code, name FROM suppliers WHERE id = %s", (p["supplier_id"],)))
        self.flat_dis.setValue(float(p["flat_discount"]))
        self.pay_amount.setValue(float(p["paid_amount"]))
        items = db().fetch_all(
            """SELECT pi.*, pr.model_name AS name, c.name AS category
               FROM purchase_items pi
               JOIN products pr ON pr.id = pi.product_id
               LEFT JOIN categories c ON c.id = pr.category_id
               WHERE pi.purchase_id = %s ORDER BY pi.id""", (rec_id,))
        self.items = [{"product_id": r["product_id"], "name": r["name"],
                       "category": r["category"], "qty": float(r["qty"]),
                       "mrp": float(r["mrp_rate"]), "dis": float(r["discount_pct"]),
                       "sales_rate": float(r["sales_rate"]), "rate": float(r["purchase_rate"]),
                       "total": float(r["total"])} for r in items]
        self._refresh_grid()

    def save(self):
        if not self.supplier.value():
            error(self, "Select a supplier.")
            return
        if not self.items:
            error(self, "Add at least one product.")
            return
        with db().transaction() as cur:
            if self.rec_id:   # revert previous stock, drop old items
                cur.execute("SELECT product_id, qty FROM purchase_items WHERE purchase_id = %s",
                            (self.rec_id,))
                for old in cur.fetchall():
                    cur.execute("UPDATE products SET stock_qty = stock_qty - %s WHERE id = %s",
                                (old["qty"], old["product_id"]))
                cur.execute("DELETE FROM purchase_items WHERE purchase_id = %s", (self.rec_id,))
                cur.execute(
                    """UPDATE purchases SET purchase_date=%s, challan_no=%s, supplier_id=%s,
                           gross_total=%s, flat_discount=%s, net_total=%s, paid_amount=%s
                       WHERE id=%s""",
                    (pydate(self.pur_date), self.challan.text(), self.supplier.value(),
                     self.g_total.value(), self.flat_dis.value(), self.net_total.value(),
                     self.pay_amount.value(), self.rec_id))
                pid = self.rec_id
            else:
                cur.execute(
                    """INSERT INTO purchases (purchase_date, challan_no, supplier_id, gross_total,
                           flat_discount, net_total, paid_amount)
                       VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                    (pydate(self.pur_date), self.challan.text(), self.supplier.value(),
                     self.g_total.value(), self.flat_dis.value(), self.net_total.value(),
                     self.pay_amount.value()))
                pid = cur.fetchone()["id"]
            for it in self.items:
                cur.execute(
                    """INSERT INTO purchase_items (purchase_id, product_id, qty, mrp_rate,
                           purchase_rate, sales_rate, discount_pct, total)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (pid, it["product_id"], it["qty"], it["mrp"], it["rate"],
                     it["sales_rate"], it["dis"], it["total"]))
                cur.execute(
                    """UPDATE products SET stock_qty = stock_qty + %s, purchase_rate = %s,
                           sales_rate = %s, mrp_rate = %s WHERE id = %s""",
                    (it["qty"], it["rate"], it["sales_rate"], it["mrp"], it["product_id"]))
        info(self, "Purchase order saved.")
        self.accept()


class PurchaseOrdersDialog(QDialog):
    """Purchase Orders window with [Purchase Order | Stock] tabs, as in the video."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Purchase Orders")
        self.setMinimumSize(980, 560)
        self.setStyleSheet(DIALOG_QSS)
        outer = QHBoxLayout(self)
        self.tabs = QTabWidget()

        po_tab = QWidget()
        lay = QVBoxLayout(po_tab)
        self.search = SearchBar()
        self.search.searched.connect(self.reload)
        lay.addWidget(self.search)
        self.table = DataTable(["Pur. Date", "Challan No", "Supplier Name", "Contact Person",
                                "Address", "Contact No", "NetAmt", "PaidAmt", "PaymentDue"])
        self.table.doubleClicked.connect(lambda *_: self.on_edit())
        lay.addWidget(self.table, 1)
        self.total_lbl = QLabel("Total : 0")
        self.total_lbl.setStyleSheet("font-weight:bold")
        lay.addWidget(self.total_lbl)
        self.tabs.addTab(po_tab, "Purchase Order")
        self.stock = stock_tab()
        self.tabs.addTab(self.stock, "Stock")
        outer.addWidget(self.tabs, 1)

        side = QVBoxLayout()
        for name, fn in [("New", self.on_new), ("Edit", self.on_edit),
                         ("Invoice", self.on_invoice), ("Return", self.on_return),
                         ("Close", self.accept)]:
            b = QPushButton(name); b.setMinimumWidth(90); b.clicked.connect(fn)
            side.addWidget(b)
        side.addStretch(1)
        outer.addLayout(side)
        self.reload("")

    def reload(self, search=None):
        if search is None:
            search = self.search.edit.text().strip()
        rows = db().fetch_all(
            """SELECT p.id, p.purchase_date, p.challan_no, s.name, s.contact_person,
                      s.address, s.contact_no, p.net_total, p.paid_amount,
                      p.net_total - p.paid_amount AS due
               FROM purchases p JOIN suppliers s ON s.id = p.supplier_id
               WHERE p.company_id = app_company_id()
                     AND (s.name ILIKE %s OR p.challan_no ILIKE %s)
               ORDER BY p.purchase_date DESC, p.id DESC""", (f"%{search}%",) * 2)
        self.table.set_rows([(r["id"], r["purchase_date"].strftime("%d %b %Y"), r["challan_no"],
                              r["name"], r["contact_person"], r["address"], r["contact_no"],
                              money(r["net_total"]), money(r["paid_amount"]), money(r["due"]))
                             for r in rows])
        self.total_lbl.setText(f"Total : {len(rows)}")
        self.stock.reload()

    def on_new(self):
        if PurchaseOrderForm(None, self).exec():
            self.reload()

    def on_edit(self):
        rec_id = self.table.current_id()
        if rec_id is None:
            info(self, "Select a purchase order first.")
            return
        if PurchaseOrderForm(rec_id, self).exec():
            self.reload()

    def on_return(self):
        rec_id = self.table.current_id()
        if rec_id is None:
            info(self, "Select a purchase order first.")
            return
        if PurchaseReturnForm(rec_id, self).exec():
            self.reload()

    def on_invoice(self):
        rec_id = self.table.current_id()
        if rec_id is None:
            info(self, "Select a purchase order first.")
            return
        p = db().fetch_one(
            """SELECT p.*, s.name AS supplier, s.contact_no, s.address
               FROM purchases p JOIN suppliers s ON s.id = p.supplier_id
               WHERE p.id = %s""", (rec_id,))
        items = db().fetch_all(
            """SELECT pr.model_name, c.name AS category, pi.qty, pi.purchase_rate, pi.total
               FROM purchase_items pi
               JOIN products pr ON pr.id = pi.product_id
               LEFT JOIN categories c ON c.id = pr.category_id
               WHERE pi.purchase_id = %s""", (rec_id,))
        rows = [[i + 1, r["model_name"], r["category"], float(r["qty"]),
                 float(r["purchase_rate"]), float(r["total"])] for i, r in enumerate(items)]
        body = (f"<p><b>Challan No:</b> {p['challan_no']} &nbsp; "
                f"<b>Date:</b> {p['purchase_date']:%d/%m/%Y}<br>"
                f"<b>Supplier:</b> {p['supplier']} &nbsp; {p['contact_no']} &nbsp; {p['address']}</p>"
                + html_table(["SI", "Product", "Category", "Qty", "Pur.Rate", "Total"], rows,
                             ["Total", "", "", float(sum(r["qty"] for r in items)), None,
                              float(p["net_total"])])
                + f"<p align='right'><b>Paid:</b> {money(p['paid_amount'])} &nbsp; "
                  f"<b>Due:</b> {money(p['net_total'] - p['paid_amount'])}</p>")
        preview_html(self, "Purchase Invoice", body)


# ---------------------------------------------------------------------------
# Purchase Return

class PurchaseReturnForm(QDialog):
    """Return Product: give back purchased items to the supplier and destock."""

    def __init__(self, purchase_id: int, parent=None):
        super().__init__(parent)
        self.purchase_id = purchase_id
        self.setWindowTitle("Purchase Return")
        self.setMinimumSize(700, 520)
        self.setStyleSheet(DIALOG_QSS)
        purchase = db().fetch_one(
            """SELECT p.*, s.name AS supplier, d.total_due
               FROM purchases p JOIN suppliers s ON s.id = p.supplier_id
               JOIN supplier_dues d ON d.id = s.id WHERE p.id = %s""", (purchase_id,))

        lay = QVBoxLayout(self)
        head = QGroupBox("Supplier")
        form = QGridLayout(head)
        self.return_no = QLineEdit(f"PRTN-{db().next_serial('purchase_returns'):04d}")
        self.return_no.setReadOnly(True)
        self.return_date = dedit()
        form.addWidget(QLabel("Return No"), 0, 0); form.addWidget(self.return_no, 0, 1)
        form.addWidget(QLabel("Return Date"), 0, 2); form.addWidget(self.return_date, 0, 3)
        form.addWidget(QLabel("Challan"), 1, 0)
        form.addWidget(QLabel(f"<b>{purchase['challan_no']}</b>"), 1, 1)
        form.addWidget(QLabel("Supplier"), 1, 2)
        form.addWidget(QLabel(f"<b>{purchase['supplier']}</b>"), 1, 3)
        form.addWidget(QLabel("Prev. Due"), 2, 0)
        form.addWidget(QLabel(f"<b>{money(purchase['total_due'])}</b>"), 2, 1)
        lay.addWidget(head)

        lay.addWidget(QLabel("Set the quantity to return for each product:"))
        items = db().fetch_all(
            """SELECT pi.product_id, pr.model_name, pi.qty, pi.purchase_rate
               FROM purchase_items pi JOIN products pr ON pr.id = pi.product_id
               WHERE pi.purchase_id = %s ORDER BY pi.id""", (purchase_id,))
        self.grid = QTableWidget(len(items), 4)
        self.grid.setHorizontalHeaderLabels(["Product", "Pur. Qty", "P.Rate", "Return Qty"])
        self.grid.verticalHeader().setVisible(False)
        self.grid.horizontalHeader().setStretchLastSection(True)
        self._items = items
        self._spins = []
        for r, it in enumerate(items):
            for c, val in enumerate([it["model_name"], money(it["qty"]), money(it["purchase_rate"])]):
                cell = QTableWidgetItem(str(val))
                cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.grid.setItem(r, c, cell)
            spin = dspin(float(it["qty"]), 2)
            spin.setRange(0, float(it["qty"]))
            spin.valueChanged.connect(self._recalc)
            self.grid.setCellWidget(r, 3, spin)
            self._spins.append(spin)
        lay.addWidget(self.grid, 1)

        foot = QFormLayout()
        self.net_total = dspin(read_only=True)
        self.back_amount = dspin()
        foot.addRow("Net Total", self.net_total)
        foot.addRow("Back Amount", self.back_amount)
        lay.addLayout(foot)

        row = QHBoxLayout()
        ret = QPushButton("Return"); ret.clicked.connect(self.save)
        close = QPushButton("Close"); close.clicked.connect(self.reject)
        row.addStretch(1); row.addWidget(ret); row.addWidget(close)
        lay.addLayout(row)

    def _recalc(self):
        total = sum(s.value() * float(it["purchase_rate"])
                    for s, it in zip(self._spins, self._items))
        self.net_total.setValue(total)
        self.back_amount.setValue(total)

    def save(self):
        returns = [(it, s.value()) for it, s in zip(self._items, self._spins) if s.value() > 0]
        if not returns:
            info(self, "Set a return quantity first.")
            return
        with db().transaction() as cur:
            cur.execute(
                """INSERT INTO purchase_returns (return_no, return_date, purchase_id, net_total,
                       back_amount) VALUES (%s,%s,%s,%s,%s) RETURNING id""",
                (self.return_no.text(), pydate(self.return_date), self.purchase_id,
                 self.net_total.value(), self.back_amount.value()))
            rid = cur.fetchone()["id"]
            for it, qty in returns:
                cur.execute(
                    """INSERT INTO purchase_return_items (return_id, product_id, qty, unit_price,
                           total) VALUES (%s,%s,%s,%s,%s)""",
                    (rid, it["product_id"], qty, it["purchase_rate"],
                     qty * float(it["purchase_rate"])))
                cur.execute("UPDATE products SET stock_qty = stock_qty - %s WHERE id = %s",
                            (qty, it["product_id"]))
        info(self, "Purchase return saved.")
        self.accept()


def purchase_return_invoice_html(return_id: int) -> str:
    r = db().fetch_one(
        """SELECT r.*, p.challan_no, s.name AS supplier, s.contact_no, s.address
           FROM purchase_returns r JOIN purchases p ON p.id = r.purchase_id
           JOIN suppliers s ON s.id = p.supplier_id WHERE r.id = %s""", (return_id,))
    items = db().fetch_all(
        """SELECT pr.model_name, ri.qty, ri.unit_price, ri.total
           FROM purchase_return_items ri JOIN products pr ON pr.id = ri.product_id
           WHERE ri.return_id = %s""", (return_id,))
    rows = [[i + 1, it["model_name"], float(it["qty"]), float(it["unit_price"]), float(it["total"])]
            for i, it in enumerate(items)]
    return (
        f"<p><b>Return No:</b> {r['return_no']} &nbsp; <b>Return Date:</b> {r['return_date']:%d/%m/%Y}<br>"
        f"<b>Challan No:</b> {r['challan_no']}<br>"
        f"<b>Supplier:</b> {r['supplier']} &nbsp; <b>Contact No:</b> {r['contact_no']}<br>"
        f"<b>Address:</b> {r['address']}</p>"
        + html_table(["SI", "Product Name", "Qty.", "Unit Price", "Total"], rows,
                     ["Total", "", float(sum(it["qty"] for it in items)), None, float(r["net_total"])])
        + f"<p align='right'><b>Back Amount:</b> {money(r['back_amount'])}</p>"
        + "<br><br><table width='100%'><tr>"
          "<td>Receiver's Signature</td>"
          "<td align='right'>Authorized Signature</td></tr></table>")


class PurchaseReturnsDialog(ListDialog):
    title = "Purchase Return"
    headers = ["Return Date", "Return No", "Challan No", "Supplier", "Contact No",
               "Net Total", "Back Amount"]
    buttons = ("Invoice", "Delete", "Close")

    def load_rows(self, search):
        rows = db().fetch_all(
            """SELECT r.id, r.return_date, r.return_no, p.challan_no, s.name, s.contact_no,
                      r.net_total, r.back_amount
               FROM purchase_returns r JOIN purchases p ON p.id = r.purchase_id
               JOIN suppliers s ON s.id = p.supplier_id
               WHERE r.company_id = app_company_id()
                     AND (s.name ILIKE %s OR r.return_no ILIKE %s OR p.challan_no ILIKE %s)
               ORDER BY r.return_date DESC""", (f"%{search}%",) * 3)
        return [(r["id"], r["return_date"].strftime("%d %b %Y"), r["return_no"],
                 r["challan_no"], r["name"], r["contact_no"], money(r["net_total"]),
                 money(r["back_amount"])) for r in rows]

    def delete_sql(self):
        return "DELETE FROM purchase_returns WHERE id = %s AND company_id = app_company_id()"

    def open_form(self, rec_id=None):
        info(self, "Open a purchase order and press Return to create a purchase return.")
        return False

    def on_invoice(self):
        rec_id = self.table.current_id()
        if rec_id is None:
            info(self, "Select a purchase return first.")
            return
        preview_html(self, "Purchase Return Invoice", purchase_return_invoice_html(rec_id))


# ---------------------------------------------------------------------------
# Sales Order

def sale_invoice_html(sale_id: int) -> str:
    s = db().fetch_one(
        """SELECT s.*, c.name AS customer, c.contact_no, c.address, d.total_due
           FROM sales s JOIN customers c ON c.id = s.customer_id
           JOIN customer_dues d ON d.id = c.id WHERE s.id = %s""", (sale_id,))
    items = db().fetch_all(
        """SELECT pr.model_name, cat.name AS category, si.qty, si.unit_price,
                  si.discount_pct, si.total
           FROM sale_items si JOIN products pr ON pr.id = si.product_id
           LEFT JOIN categories cat ON cat.id = pr.category_id
           WHERE si.sale_id = %s""", (sale_id,))
    rows = [[i + 1, r["model_name"], r["category"], float(r["qty"]), float(r["unit_price"]),
             float(r["discount_pct"]), float(r["total"])] for i, r in enumerate(items)]
    return (
        f"<p><b>Invoice No:</b> {s['invoice_no']} &nbsp; <b>Sales Date:</b> {s['sales_date']:%d/%m/%Y}<br>"
        f"<b>Buyer Name:</b> {s['customer']} &nbsp; <b>Mobile No:</b> {s['contact_no']}<br>"
        f"<b>Buyer Address:</b> {s['address']} &nbsp; <b>Sold By:</b> {s['sold_by']}</p>"
        + html_table(["SI", "Product Name", "Category", "Qty.", "Sales Price", "DIS.", "Total Amt."],
                     rows, ["Total", "", "", float(sum(r["qty"] for r in items)), None, None,
                            float(s["gross_total"])])
        + "<br>" + html_table(
            ["Sales Amt.", "Discount", "VAT", "Net Total", "Paid", "Curr. Due", "Total Outstanding"],
            [[float(s["gross_total"]), float(s["flat_discount"]), float(s["vat_amount"]),
              float(s["net_total"]), float(s["paid_amount"]),
              float(s["net_total"] - s["paid_amount"]), float(s["total_due"])]])
        + "<br><br><table width='100%'><tr>"
          "<td>Receiver's Signature</td>"
          "<td align='right'>Authorized Signature</td></tr></table>")


class SalesOrderForm(QDialog):
    def __init__(self, rec_id=None, username: str = "", parent=None):
        super().__init__(parent)
        self.rec_id = rec_id
        self.username = username
        self.items: list[dict] = []
        self.setWindowTitle("Sales Order")
        self.setMinimumSize(920, 640)
        self.setStyleSheet(DIALOG_QSS)
        lay = QVBoxLayout(self)

        cbox = QGroupBox("Customer")
        cgrid = QGridLayout(cbox)
        self.invoice = QLineEdit(); self.invoice.setReadOnly(True)
        self.sales_date = dedit()
        self.prev_due = dspin(read_only=True)
        self.customer = LookupField("Customers", ["Code", "Name", "Contact", "Address", "Due"],
                                    CUSTOMER_PICK_SQL,
                                    new_form_factory=lambda p: CustomerForm(None, p))
        self.customer.selected.connect(
            lambda rec: self.prev_due.setValue(float(rec.get("total_due") or 0)))
        self.remind = dedit()
        cgrid.addWidget(QLabel("Invoice"), 0, 0); cgrid.addWidget(self.invoice, 0, 1)
        cgrid.addWidget(QLabel("Sales Date"), 0, 2); cgrid.addWidget(self.sales_date, 0, 3)
        cgrid.addWidget(QLabel("Prev. Due"), 0, 4); cgrid.addWidget(self.prev_due, 0, 5)
        cgrid.addWidget(QLabel("Customer"), 1, 0); cgrid.addWidget(self.customer, 1, 1, 1, 3)
        cgrid.addWidget(QLabel("R. Date"), 1, 4); cgrid.addWidget(self.remind, 1, 5)
        lay.addWidget(cbox)

        pbox = QGroupBox("Product")
        pgrid = QGridLayout(pbox)
        self.product = product_lookup(self)
        self.product.selected.connect(self._product_picked)
        self.stock = dspin(read_only=True)
        self.qty = dspin(999999, 2); self.qty.setValue(1)
        self.rate = dspin()
        self.dis_pct = dspin(100, 2)
        self.line_total = dspin(read_only=True)
        for w in (self.qty, self.rate, self.dis_pct):
            w.valueChanged.connect(self._recalc_line)
        add = QPushButton("Add"); add.clicked.connect(self._add_item)
        remove = QPushButton("Remove"); remove.clicked.connect(self._remove_item)
        pgrid.addWidget(QLabel("Product"), 0, 0); pgrid.addWidget(self.product, 0, 1, 1, 3)
        pgrid.addWidget(QLabel("Stock"), 0, 4); pgrid.addWidget(self.stock, 0, 5)
        pgrid.addWidget(QLabel("Quantity"), 1, 0); pgrid.addWidget(self.qty, 1, 1)
        pgrid.addWidget(QLabel("Sales Rate"), 1, 2); pgrid.addWidget(self.rate, 1, 3)
        pgrid.addWidget(QLabel("Total"), 1, 4); pgrid.addWidget(self.line_total, 1, 5)
        pgrid.addWidget(QLabel("Discount %"), 2, 0); pgrid.addWidget(self.dis_pct, 2, 1)
        pgrid.addWidget(add, 2, 4); pgrid.addWidget(remove, 2, 5)
        lay.addWidget(pbox)

        mid = QHBoxLayout()
        self.grid = DataTable(["SN", "Name", "Category", "Qty", "U.Price", "Dis(%)", "Total"])
        mid.addWidget(self.grid, 2)

        right = QVBoxLayout()
        card = QGroupBox("Card Payment")
        cform = QFormLayout(card)
        self.bank = QComboBox()
        self.bank.addItem("--Select Bank--", None)
        for b in db().fetch_all(
                "SELECT id, name FROM banks WHERE company_id = app_company_id() ORDER BY name"):
            self.bank.addItem(b["name"], b["id"])
        self.card_amount = dspin()
        self.card_amount.valueChanged.connect(self._recalc_totals)
        cform.addRow("Bank", self.bank)
        cform.addRow("Amount", self.card_amount)
        right.addWidget(card)

        totals = QFormLayout()
        self.flat_dis = dspin(); self.flat_dis.valueChanged.connect(self._recalc_totals)
        self.vat_pct = dspin(100, 2); self.vat_pct.valueChanged.connect(self._recalc_totals)
        self.net_total = dspin(read_only=True)
        self.cash_paid = dspin(); self.cash_paid.valueChanged.connect(self._recalc_totals)
        self.paid_amount = dspin(read_only=True)
        self.curr_due = dspin(read_only=True)
        totals.addRow("Flat Dis.", self.flat_dis)
        totals.addRow("VAT %", self.vat_pct)
        totals.addRow("Net Total", self.net_total)
        totals.addRow("Cash Paid", self.cash_paid)
        totals.addRow("Paid Amount", self.paid_amount)
        totals.addRow("Curr. Due", self.curr_due)
        right.addLayout(totals)
        mid.addLayout(right, 1)
        lay.addLayout(mid, 1)

        row = QHBoxLayout()
        save = QPushButton("Save"); save.clicked.connect(self.save)
        close = QPushButton("Close"); close.clicked.connect(self.reject)
        row.addStretch(1); row.addWidget(save); row.addWidget(close)
        lay.addLayout(row)

        if rec_id:
            self._load(rec_id)
        else:
            n = db().next_serial("sales")
            self.invoice.setText(f"INV-{n:07d}")

    def _product_picked(self, rec):
        self.stock.setValue(float(rec["stock_qty"]))
        self.rate.setValue(float(rec["sales_rate"]))
        self.qty.setValue(1)
        self._recalc_line()

    def _recalc_line(self):
        base = self.qty.value() * self.rate.value()
        self.line_total.setValue(base * (1 - self.dis_pct.value() / 100))

    def _add_item(self):
        if not self.product.record:
            info(self, "Select a product first.")
            return
        if self.qty.value() <= 0:
            info(self, "Quantity must be positive.")
            return
        if self.qty.value() > self.stock.value():
            if not confirm(self, "Quantity exceeds available stock. Continue?"):
                return
        rec = self.product.record
        self.items.append({"product_id": rec["id"], "name": rec["name"],
                           "category": rec.get("category", ""), "qty": self.qty.value(),
                           "rate": self.rate.value(), "dis": self.dis_pct.value(),
                           "total": self.line_total.value()})
        self.product.set_record(None)
        for w in (self.stock, self.rate, self.dis_pct, self.line_total):
            w.setValue(0)
        self.qty.setValue(1)
        self._refresh_grid()

    def _remove_item(self):
        r = self.grid.currentRow()
        if 0 <= r < len(self.items):
            del self.items[r]
            self._refresh_grid()

    def _refresh_grid(self):
        self.grid.set_rows([(n, n + 1, it["name"], it["category"], money(it["qty"]),
                             money(it["rate"]), money(it["dis"]), money(it["total"]))
                            for n, it in enumerate(self.items)])
        self._recalc_totals()

    def _recalc_totals(self):
        g = sum(it["total"] for it in self.items)
        after_dis = g - self.flat_dis.value()
        vat = after_dis * self.vat_pct.value() / 100
        net = after_dis + vat
        self.net_total.setValue(net)
        paid = self.cash_paid.value() + self.card_amount.value()
        self.paid_amount.setValue(paid)
        self.curr_due.setValue(net - paid)

    def _load(self, rec_id):
        s = db().fetch_one("SELECT * FROM sales WHERE id = %s", (rec_id,))
        self.invoice.setText(s["invoice_no"])
        d = s["sales_date"]
        self.sales_date.setDate(QDate(d.year, d.month, d.day))
        self.customer.set_record(db().fetch_one(
            "SELECT id, code, name FROM customers WHERE id = %s", (s["customer_id"],)))
        self.flat_dis.setValue(float(s["flat_discount"]))
        self.card_amount.setValue(float(s["card_amount"]))
        self.cash_paid.setValue(float(s["paid_amount"]) - float(s["card_amount"]))
        if s["card_bank_id"]:
            i = self.bank.findData(s["card_bank_id"])
            self.bank.setCurrentIndex(max(i, 0))
        items = db().fetch_all(
            """SELECT si.*, pr.model_name AS name, c.name AS category
               FROM sale_items si JOIN products pr ON pr.id = si.product_id
               LEFT JOIN categories c ON c.id = pr.category_id
               WHERE si.sale_id = %s ORDER BY si.id""", (rec_id,))
        self.items = [{"product_id": r["product_id"], "name": r["name"],
                       "category": r["category"], "qty": float(r["qty"]),
                       "rate": float(r["unit_price"]), "dis": float(r["discount_pct"]),
                       "total": float(r["total"])} for r in items]
        self._refresh_grid()

    def save(self):
        if not self.customer.value():
            error(self, "Select a customer.")
            return
        if not self.items:
            error(self, "Add at least one product.")
            return
        gross = sum(it["total"] for it in self.items)
        vat = (gross - self.flat_dis.value()) * self.vat_pct.value() / 100
        with db().transaction() as cur:
            if self.rec_id:
                cur.execute("SELECT product_id, qty FROM sale_items WHERE sale_id = %s",
                            (self.rec_id,))
                for old in cur.fetchall():
                    cur.execute("UPDATE products SET stock_qty = stock_qty + %s WHERE id = %s",
                                (old["qty"], old["product_id"]))
                cur.execute("DELETE FROM sale_items WHERE sale_id = %s", (self.rec_id,))
                cur.execute(
                    """UPDATE sales SET sales_date=%s, customer_id=%s, gross_total=%s,
                           flat_discount=%s, vat_amount=%s, net_total=%s, paid_amount=%s,
                           card_bank_id=%s, card_amount=%s, remind_date=%s WHERE id=%s""",
                    (pydate(self.sales_date), self.customer.value(), gross,
                     self.flat_dis.value(), vat, self.net_total.value(),
                     self.paid_amount.value(), self.bank.currentData(),
                     self.card_amount.value(), pydate(self.remind), self.rec_id))
                sid = self.rec_id
            else:
                cur.execute(
                    """INSERT INTO sales (invoice_no, sales_date, customer_id, sale_kind,
                           gross_total, flat_discount, vat_amount, net_total, paid_amount,
                           card_bank_id, card_amount, remind_date, sold_by)
                       VALUES (%s,%s,%s,'CASH',%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                    (self.invoice.text(), pydate(self.sales_date), self.customer.value(),
                     gross, self.flat_dis.value(), vat, self.net_total.value(),
                     self.paid_amount.value(), self.bank.currentData(),
                     self.card_amount.value(), pydate(self.remind), self.username))
                sid = cur.fetchone()["id"]
            for it in self.items:
                cur.execute(
                    """INSERT INTO sale_items (sale_id, product_id, qty, unit_price,
                           discount_pct, total) VALUES (%s,%s,%s,%s,%s,%s)""",
                    (sid, it["product_id"], it["qty"], it["rate"], it["dis"], it["total"]))
                cur.execute("UPDATE products SET stock_qty = stock_qty - %s WHERE id = %s",
                            (it["qty"], it["product_id"]))
        self.saved_id = sid
        info(self, "Sales order saved.")
        self.accept()


class SalesOrdersDialog(QDialog):
    """All Sales Orders window: [Orders | Stock] tabs + New/Edit/Invoice/Return."""

    def __init__(self, username: str = "", parent=None):
        super().__init__(parent)
        self.username = username
        self.setWindowTitle("All Sales Orders")
        self.setMinimumSize(980, 560)
        self.setStyleSheet(DIALOG_QSS)
        outer = QHBoxLayout(self)
        self.tabs = QTabWidget()

        tab = QWidget()
        lay = QVBoxLayout(tab)
        self.search = SearchBar()
        self.search.searched.connect(self.reload)
        lay.addWidget(self.search)
        self.table = DataTable(["Sales Date", "Invoice No", "Customer", "Address",
                                "Contact No", "Total Amt", "Rec.Amt", "Due Amt"])
        self.table.doubleClicked.connect(lambda *_: self.on_edit())
        lay.addWidget(self.table, 1)
        self.total_lbl = QLabel("Total : 0")
        self.total_lbl.setStyleSheet("font-weight:bold")
        lay.addWidget(self.total_lbl)
        self.tabs.addTab(tab, "Orders")
        self.stock = stock_tab()
        self.tabs.addTab(self.stock, "Stock")
        outer.addWidget(self.tabs, 1)

        side = QVBoxLayout()
        for name, fn in [("New", self.on_new), ("Edit", self.on_edit),
                         ("Invoice", self.on_invoice), ("Return", self.on_return),
                         ("Close", self.accept)]:
            b = QPushButton(name); b.setMinimumWidth(90); b.clicked.connect(fn)
            side.addWidget(b)
        side.addStretch(1)
        outer.addLayout(side)
        self.reload("")

    def reload(self, search=None):
        if search is None:
            search = self.search.edit.text().strip()
        rows = db().fetch_all(
            """SELECT s.id, s.sales_date, s.invoice_no, c.name, c.address, c.contact_no,
                      s.net_total, s.paid_amount, s.net_total - s.paid_amount AS due
               FROM sales s JOIN customers c ON c.id = s.customer_id
               WHERE s.company_id = app_company_id() AND s.sale_kind = 'CASH'
                     AND (c.name ILIKE %s OR s.invoice_no ILIKE %s)
               ORDER BY s.sales_date DESC, s.id DESC""", (f"%{search}%",) * 2)
        self.table.set_rows([(r["id"], r["sales_date"].strftime("%d %b %Y"), r["invoice_no"],
                              r["name"], r["address"], r["contact_no"], money(r["net_total"]),
                              money(r["paid_amount"]), money(r["due"])) for r in rows])
        self.total_lbl.setText(f"Total : {len(rows)}")
        self.stock.reload()

    def on_new(self):
        form = SalesOrderForm(None, self.username, self)
        if form.exec():
            self.reload()
            if confirm(self, "Show invoice?"):
                preview_html(self, "Invoice/Bill", sale_invoice_html(form.saved_id))

    def on_edit(self):
        rec_id = self.table.current_id()
        if rec_id is None:
            info(self, "Select a sales order first.")
            return
        if SalesOrderForm(rec_id, self.username, self).exec():
            self.reload()

    def on_invoice(self):
        rec_id = self.table.current_id()
        if rec_id is None:
            info(self, "Select a sales order first.")
            return
        preview_html(self, "Invoice/Bill", sale_invoice_html(rec_id))

    def on_return(self):
        rec_id = self.table.current_id()
        if rec_id is None:
            info(self, "Select a sales order first.")
            return
        if SalesReturnForm(rec_id, self).exec():
            self.reload()


# ---------------------------------------------------------------------------
# Return Product

class SalesReturnForm(QDialog):
    """Return Product: give back items from a sale, refund and restock."""

    def __init__(self, sale_id: int, parent=None):
        super().__init__(parent)
        self.sale_id = sale_id
        self.setWindowTitle("Return Product")
        self.setMinimumSize(700, 520)
        self.setStyleSheet(DIALOG_QSS)
        sale = db().fetch_one(
            """SELECT s.*, c.name AS customer, d.total_due
               FROM sales s JOIN customers c ON c.id = s.customer_id
               JOIN customer_dues d ON d.id = c.id WHERE s.id = %s""", (sale_id,))

        lay = QVBoxLayout(self)
        head = QGroupBox("Customer")
        form = QGridLayout(head)
        self.return_no = QLineEdit(f"RTN-{db().next_serial('sales_returns'):04d}")
        self.return_no.setReadOnly(True)
        self.return_date = dedit()
        form.addWidget(QLabel("Return No"), 0, 0); form.addWidget(self.return_no, 0, 1)
        form.addWidget(QLabel("Return Date"), 0, 2); form.addWidget(self.return_date, 0, 3)
        form.addWidget(QLabel("Invoice"), 1, 0)
        form.addWidget(QLabel(f"<b>{sale['invoice_no']}</b>"), 1, 1)
        form.addWidget(QLabel("Customer"), 1, 2)
        form.addWidget(QLabel(f"<b>{sale['customer']}</b>"), 1, 3)
        form.addWidget(QLabel("Prev. Due"), 2, 0)
        form.addWidget(QLabel(f"<b>{money(sale['total_due'])}</b>"), 2, 1)
        lay.addWidget(head)

        lay.addWidget(QLabel("Set the quantity to return for each product:"))
        items = db().fetch_all(
            """SELECT si.product_id, pr.model_name, si.qty, si.unit_price
               FROM sale_items si JOIN products pr ON pr.id = si.product_id
               WHERE si.sale_id = %s ORDER BY si.id""", (sale_id,))
        self.grid = QTableWidget(len(items), 4)
        self.grid.setHorizontalHeaderLabels(["Product", "Sold Qty", "U.Price", "Return Qty"])
        self.grid.verticalHeader().setVisible(False)
        self.grid.horizontalHeader().setStretchLastSection(True)
        self._items = items
        self._spins = []
        for r, it in enumerate(items):
            for c, val in enumerate([it["model_name"], money(it["qty"]), money(it["unit_price"])]):
                cell = QTableWidgetItem(str(val))
                cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.grid.setItem(r, c, cell)
            spin = dspin(float(it["qty"]), 2)
            spin.setRange(0, float(it["qty"]))
            spin.valueChanged.connect(self._recalc)
            self.grid.setCellWidget(r, 3, spin)
            self._spins.append(spin)
        lay.addWidget(self.grid, 1)

        foot = QFormLayout()
        self.net_total = dspin(read_only=True)
        self.back_amount = dspin()
        foot.addRow("Net Total", self.net_total)
        foot.addRow("Back Amount", self.back_amount)
        lay.addLayout(foot)

        row = QHBoxLayout()
        ret = QPushButton("Return"); ret.clicked.connect(self.save)
        close = QPushButton("Close"); close.clicked.connect(self.reject)
        row.addStretch(1); row.addWidget(ret); row.addWidget(close)
        lay.addLayout(row)

    def _recalc(self):
        total = sum(s.value() * float(it["unit_price"])
                    for s, it in zip(self._spins, self._items))
        self.net_total.setValue(total)
        self.back_amount.setValue(total)

    def save(self):
        returns = [(it, s.value()) for it, s in zip(self._items, self._spins) if s.value() > 0]
        if not returns:
            info(self, "Set a return quantity first.")
            return
        with db().transaction() as cur:
            cur.execute(
                """INSERT INTO sales_returns (return_no, return_date, sale_id, net_total,
                       back_amount) VALUES (%s,%s,%s,%s,%s) RETURNING id""",
                (self.return_no.text(), pydate(self.return_date), self.sale_id,
                 self.net_total.value(), self.back_amount.value()))
            rid = cur.fetchone()["id"]
            for it, qty in returns:
                cur.execute(
                    """INSERT INTO sale_return_items (return_id, product_id, qty, unit_price,
                           total) VALUES (%s,%s,%s,%s,%s)""",
                    (rid, it["product_id"], qty, it["unit_price"],
                     qty * float(it["unit_price"])))
                cur.execute("UPDATE products SET stock_qty = stock_qty + %s WHERE id = %s",
                            (qty, it["product_id"]))
        info(self, "Product return saved.")
        self.accept()


def sales_return_invoice_html(return_id: int) -> str:
    r = db().fetch_one(
        """SELECT r.*, s.invoice_no, c.name AS customer, c.contact_no, c.address
           FROM sales_returns r JOIN sales s ON s.id = r.sale_id
           JOIN customers c ON c.id = s.customer_id WHERE r.id = %s""", (return_id,))
    items = db().fetch_all(
        """SELECT pr.model_name, ri.qty, ri.unit_price, ri.total
           FROM sale_return_items ri JOIN products pr ON pr.id = ri.product_id
           WHERE ri.return_id = %s""", (return_id,))
    rows = [[i + 1, it["model_name"], float(it["qty"]), float(it["unit_price"]), float(it["total"])]
            for i, it in enumerate(items)]
    return (
        f"<p><b>Return No:</b> {r['return_no']} &nbsp; <b>Return Date:</b> {r['return_date']:%d/%m/%Y}<br>"
        f"<b>Invoice No:</b> {r['invoice_no']}<br>"
        f"<b>Customer:</b> {r['customer']} &nbsp; <b>Contact No:</b> {r['contact_no']}<br>"
        f"<b>Address:</b> {r['address']}</p>"
        + html_table(["SI", "Product Name", "Qty.", "Unit Price", "Total"], rows,
                     ["Total", "", float(sum(it["qty"] for it in items)), None, float(r["net_total"])])
        + f"<p align='right'><b>Back Amount:</b> {money(r['back_amount'])}</p>"
        + "<br><br><table width='100%'><tr>"
          "<td>Receiver's Signature</td>"
          "<td align='right'>Authorized Signature</td></tr></table>")


class ReturnsDialog(ListDialog):
    title = "Sales Return"
    headers = ["ReturnDate", "Return No", "Invoice No", "Customer", "Contact No",
               "Net Total", "Back Amount"]
    buttons = ("Invoice", "Delete", "Close")

    def load_rows(self, search):
        rows = db().fetch_all(
            """SELECT r.id, r.return_date, r.return_no, s.invoice_no, c.name, c.contact_no,
                      r.net_total, r.back_amount
               FROM sales_returns r JOIN sales s ON s.id = r.sale_id
               JOIN customers c ON c.id = s.customer_id
               WHERE r.company_id = app_company_id()
                     AND (c.name ILIKE %s OR r.return_no ILIKE %s OR s.invoice_no ILIKE %s)
               ORDER BY r.return_date DESC""", (f"%{search}%",) * 3)
        return [(r["id"], r["return_date"].strftime("%d %b %Y"), r["return_no"],
                 r["invoice_no"], r["name"], r["contact_no"], money(r["net_total"]),
                 money(r["back_amount"])) for r in rows]

    def delete_sql(self):
        return "DELETE FROM sales_returns WHERE id = %s AND company_id = app_company_id()"

    def open_form(self, rec_id=None):
        info(self, "Open a sales order and press Return to create a product return.")
        return False

    def on_invoice(self):
        rec_id = self.table.current_id()
        if rec_id is None:
            info(self, "Select a sales return first.")
            return
        preview_html(self, "Sales Return Invoice", sales_return_invoice_html(rec_id))


# ---------------------------------------------------------------------------
# Damage Product

class DamageProductForm(QDialog):
    """Write off damaged/broken stock: pick a product, quantity and reason."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Damage Product")
        self.setMinimumSize(560, 380)
        self.setStyleSheet(DIALOG_QSS)
        lay = QVBoxLayout(self)

        form = QFormLayout()
        self.damage_no = QLineEdit(f"DMG-{db().next_serial('damaged_products'):04d}")
        self.damage_no.setReadOnly(True)
        self.damage_date = dedit()
        self.product = product_lookup(self)
        self.product.selected.connect(self._product_picked)
        self.stock = dspin(read_only=True)
        self.qty = dspin(999999, 2); self.qty.setValue(1)
        self.rate = dspin()
        self.total = dspin(read_only=True)
        self.remarks = QLineEdit()
        for w in (self.qty, self.rate):
            w.valueChanged.connect(self._recalc)
        form.addRow("Damage No", self.damage_no)
        form.addRow("Damage Date", self.damage_date)
        form.addRow("Product", self.product)
        form.addRow("Stock", self.stock)
        form.addRow("Quantity", self.qty)
        form.addRow("Rate", self.rate)
        form.addRow("Total", self.total)
        form.addRow("Remarks", self.remarks)
        lay.addLayout(form)

        row = QHBoxLayout()
        save = QPushButton("Save"); save.clicked.connect(self.save)
        close = QPushButton("Close"); close.clicked.connect(self.reject)
        row.addStretch(1); row.addWidget(save); row.addWidget(close)
        lay.addLayout(row)

    def _product_picked(self, rec):
        self.stock.setValue(float(rec["stock_qty"]))
        self.rate.setValue(float(rec["purchase_rate"]))
        self.qty.setValue(1)
        self._recalc()

    def _recalc(self):
        self.total.setValue(self.qty.value() * self.rate.value())

    def save(self):
        if not self.product.record:
            error(self, "Select a product.")
            return
        if self.qty.value() <= 0:
            error(self, "Quantity must be positive.")
            return
        if self.qty.value() > self.stock.value():
            if not confirm(self, "Quantity exceeds available stock. Continue?"):
                return
        with db().transaction() as cur:
            cur.execute(
                """INSERT INTO damaged_products (damage_no, damage_date, product_id, qty,
                       rate, total, remarks) VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (self.damage_no.text(), pydate(self.damage_date), self.product.value(),
                 self.qty.value(), self.rate.value(), self.total.value(),
                 self.remarks.text()))
            cur.execute("UPDATE products SET stock_qty = stock_qty - %s WHERE id = %s",
                        (self.qty.value(), self.product.value()))
        info(self, "Damage entry saved.")
        self.accept()


class DamageProductsDialog(ListDialog):
    title = "Damage Product"
    headers = ["Damage Date", "Damage No", "Product", "Qty", "Rate", "Total", "Remarks"]
    buttons = ("New", "Delete", "Close")

    def load_rows(self, search):
        rows = db().fetch_all(
            """SELECT d.id, d.damage_date, d.damage_no, p.model_name, d.qty, d.rate,
                      d.total, d.remarks
               FROM damaged_products d JOIN products p ON p.id = d.product_id
               WHERE d.company_id = app_company_id()
                     AND (p.model_name ILIKE %s OR d.damage_no ILIKE %s)
               ORDER BY d.damage_date DESC""", (f"%{search}%",) * 2)
        return [(r["id"], r["damage_date"].strftime("%d %b %Y"), r["damage_no"],
                 r["model_name"], money(r["qty"]), money(r["rate"]), money(r["total"]),
                 r["remarks"]) for r in rows]

    def open_form(self, rec_id=None):
        return bool(DamageProductForm(self).exec())

    def delete_sql(self):
        return "DELETE FROM damaged_products WHERE id = %s AND company_id = app_company_id()"


# ---------------------------------------------------------------------------
# Credit Sales (installments)

class CreditSaleForm(QDialog):
    def __init__(self, username: str = "", parent=None):
        super().__init__(parent)
        self.username = username
        self.items: list[dict] = []
        self.setWindowTitle("Credit Sales")
        self.setMinimumSize(920, 640)
        self.setStyleSheet(DIALOG_QSS)
        lay = QVBoxLayout(self)

        cbox = QGroupBox("Customer")
        cgrid = QGridLayout(cbox)
        self.invoice = QLineEdit(f"INV-{db().next_serial('sales'):07d}")
        self.invoice.setReadOnly(True)
        self.sales_date = dedit()
        self.prev_due = dspin(read_only=True)
        self.customer = LookupField("Customers", ["Code", "Name", "Contact", "Address", "Due"],
                                    CUSTOMER_PICK_SQL,
                                    new_form_factory=lambda p: CustomerForm(None, p))
        self.customer.selected.connect(
            lambda rec: self.prev_due.setValue(float(rec.get("total_due") or 0)))
        cgrid.addWidget(QLabel("Invoice"), 0, 0); cgrid.addWidget(self.invoice, 0, 1)
        cgrid.addWidget(QLabel("Sales Date"), 0, 2); cgrid.addWidget(self.sales_date, 0, 3)
        cgrid.addWidget(QLabel("Prev. Due"), 0, 4); cgrid.addWidget(self.prev_due, 0, 5)
        cgrid.addWidget(QLabel("Customer"), 1, 0); cgrid.addWidget(self.customer, 1, 1, 1, 5)
        lay.addWidget(cbox)

        pbox = QGroupBox("Product")
        pgrid = QGridLayout(pbox)
        self.product = product_lookup(self)
        self.product.selected.connect(self._product_picked)
        self.stock = dspin(read_only=True)
        self.qty = dspin(999999, 2); self.qty.setValue(1)
        self.rate = dspin()
        self.line_total = dspin(read_only=True)
        for w in (self.qty, self.rate):
            w.valueChanged.connect(self._recalc_line)
        add = QPushButton("Add"); add.clicked.connect(self._add_item)
        remove = QPushButton("Remove"); remove.clicked.connect(self._remove_item)
        pgrid.addWidget(QLabel("Product"), 0, 0); pgrid.addWidget(self.product, 0, 1, 1, 3)
        pgrid.addWidget(QLabel("Stock"), 0, 4); pgrid.addWidget(self.stock, 0, 5)
        pgrid.addWidget(QLabel("Quantity"), 1, 0); pgrid.addWidget(self.qty, 1, 1)
        pgrid.addWidget(QLabel("Unit Price"), 1, 2); pgrid.addWidget(self.rate, 1, 3)
        pgrid.addWidget(QLabel("Total"), 1, 4); pgrid.addWidget(self.line_total, 1, 5)
        pgrid.addWidget(add, 2, 4); pgrid.addWidget(remove, 2, 5)
        lay.addWidget(pbox)

        mid = QHBoxLayout()
        self.grid = DataTable(["SN", "Name", "Category", "Qty", "U.Price", "Total"])
        mid.addWidget(self.grid, 2)

        right = QFormLayout()
        self.grand_total = dspin(read_only=True)
        self.down_payment = dspin(); self.down_payment.valueChanged.connect(self._recalc_totals)
        self.interest_rate = dspin(100, 2); self.interest_rate.valueChanged.connect(self._recalc_totals)
        self.interest_amount = dspin(read_only=True)
        self.remaining = dspin(read_only=True)
        self.net_amount = dspin(read_only=True)
        self.installments = QSpinBox(); self.installments.setRange(1, 60); self.installments.setValue(6)
        self.install_date = dedit()
        right.addRow("Grand Total", self.grand_total)
        right.addRow("Down Payment", self.down_payment)
        right.addRow("Interest Rate(%)", self.interest_rate)
        right.addRow("Interest Amount", self.interest_amount)
        right.addRow("Remaining Amt.", self.remaining)
        right.addRow("Net Amount", self.net_amount)
        right.addRow("Installments", self.installments)
        right.addRow("Install Date", self.install_date)
        mid.addLayout(right, 1)
        lay.addLayout(mid, 1)

        row = QHBoxLayout()
        save = QPushButton("Save"); save.clicked.connect(self.save)
        close = QPushButton("Close"); close.clicked.connect(self.reject)
        row.addStretch(1); row.addWidget(save); row.addWidget(close)
        lay.addLayout(row)

    def _product_picked(self, rec):
        self.stock.setValue(float(rec["stock_qty"]))
        self.rate.setValue(float(rec["sales_rate"]))
        self.qty.setValue(1)
        self._recalc_line()

    def _recalc_line(self):
        self.line_total.setValue(self.qty.value() * self.rate.value())

    def _add_item(self):
        if not self.product.record:
            info(self, "Select a product first.")
            return
        rec = self.product.record
        self.items.append({"product_id": rec["id"], "name": rec["name"],
                           "category": rec.get("category", ""), "qty": self.qty.value(),
                           "rate": self.rate.value(), "total": self.line_total.value()})
        self.product.set_record(None)
        for w in (self.stock, self.rate, self.line_total):
            w.setValue(0)
        self.qty.setValue(1)
        self.grid.set_rows([(n, n + 1, it["name"], it["category"], money(it["qty"]),
                             money(it["rate"]), money(it["total"]))
                            for n, it in enumerate(self.items)])
        self._recalc_totals()

    def _remove_item(self):
        r = self.grid.currentRow()
        if 0 <= r < len(self.items):
            del self.items[r]
            self.grid.set_rows([(n, n + 1, it["name"], it["category"], money(it["qty"]),
                                 money(it["rate"]), money(it["total"]))
                                for n, it in enumerate(self.items)])
            self._recalc_totals()

    def _recalc_totals(self):
        g = sum(it["total"] for it in self.items)
        self.grand_total.setValue(g)
        remaining = g - self.down_payment.value()
        interest = remaining * self.interest_rate.value() / 100
        self.interest_amount.setValue(interest)
        self.remaining.setValue(remaining + interest)
        self.net_amount.setValue(g + interest)

    def save(self):
        if not self.customer.value():
            error(self, "Select a customer.")
            return
        if not self.items:
            error(self, "Add at least one product.")
            return
        n_inst = self.installments.value()
        per = round(self.remaining.value() / n_inst, 2)
        start = pydate(self.install_date)
        with db().transaction() as cur:
            cur.execute(
                """INSERT INTO sales (invoice_no, sales_date, customer_id, sale_kind,
                       gross_total, net_total, paid_amount, interest_rate, interest_amount,
                       sold_by)
                   VALUES (%s,%s,%s,'CREDIT',%s,%s,%s,%s,%s,%s) RETURNING id""",
                (self.invoice.text(), pydate(self.sales_date), self.customer.value(),
                 self.grand_total.value(), self.net_amount.value(),
                 self.down_payment.value(), self.interest_rate.value(),
                 self.interest_amount.value(), self.username))
            sid = cur.fetchone()["id"]
            for it in self.items:
                cur.execute(
                    """INSERT INTO sale_items (sale_id, product_id, qty, unit_price, total)
                       VALUES (%s,%s,%s,%s,%s)""",
                    (sid, it["product_id"], it["qty"], it["rate"], it["total"]))
                cur.execute("UPDATE products SET stock_qty = stock_qty - %s WHERE id = %s",
                            (it["qty"], it["product_id"]))
            for i in range(n_inst):
                m = start.month - 1 + i
                due = date(start.year + m // 12, m % 12 + 1, min(start.day, 28))
                amount = per if i < n_inst - 1 else round(
                    self.remaining.value() - per * (n_inst - 1), 2)
                cur.execute(
                    """INSERT INTO installments (sale_id, schedule_date, amount)
                       VALUES (%s,%s,%s)""", (sid, due, amount))
        info(self, "Credit sale saved.")
        self.accept()


class InstallmentsDialog(QDialog):
    """Installment schedule of one credit sale, with a Paid button."""

    def __init__(self, sale_id: int, parent=None):
        super().__init__(parent)
        self.sale_id = sale_id
        self.setWindowTitle("Installment Details")
        self.setMinimumSize(680, 480)
        self.setStyleSheet(DIALOG_QSS)
        lay = QVBoxLayout(self)
        s = db().fetch_one(
            """SELECT s.invoice_no, c.name FROM sales s
               JOIN customers c ON c.id = s.customer_id WHERE s.id = %s""", (sale_id,))
        lay.addWidget(QLabel(f"<b>Invoice: {s['invoice_no']} — {s['name']}</b>"))
        self.table = DataTable(["Schedule", "Amount", "Paid", "Pay Date", "Status"])
        lay.addWidget(self.table, 1)
        row = QHBoxLayout()
        paid = QPushButton("Paid"); paid.clicked.connect(self.mark_paid)
        close = QPushButton("Close"); close.clicked.connect(self.accept)
        row.addStretch(1); row.addWidget(paid); row.addWidget(close)
        lay.addLayout(row)
        self.reload()

    def reload(self):
        rows = db().fetch_all(
            "SELECT * FROM installments WHERE sale_id = %s ORDER BY schedule_date",
            (self.sale_id,))
        self.table.set_rows([(r["id"], r["schedule_date"].strftime("%d %b %Y"),
                              money(r["amount"]), money(r["paid_amount"]),
                              r["paid_date"].strftime("%d %b %Y") if r["paid_date"] else "",
                              r["status"]) for r in rows])

    def mark_paid(self):
        inst_id = self.table.current_id()
        if inst_id is None:
            info(self, "Select an installment.")
            return
        inst = db().fetch_one("SELECT * FROM installments WHERE id = %s", (inst_id,))
        if inst["status"] == "Paid":
            info(self, "Already paid.")
            return
        if not confirm(self, f"Receive {money(inst['amount'])} for this installment?"):
            return
        with db().transaction() as cur:
            cur.execute(
                """UPDATE installments SET paid_amount = amount, paid_date = CURRENT_DATE,
                       status = 'Paid' WHERE id = %s""", (inst_id,))
            cur.execute("UPDATE sales SET paid_amount = paid_amount + %s WHERE id = %s",
                        (inst["amount"], self.sale_id))
        self.reload()


class CreditSalesDialog(ListDialog):
    title = "Credit Sales"
    headers = ["Sales Date", "Invoice No", "Customer", "Contact No", "Net Amount",
               "Paid", "Due", "Installments"]
    buttons = ("New", "Edit", "Invoice", "Close")

    def __init__(self, username: str = "", parent=None):
        self.username = username
        super().__init__(parent)

    def load_rows(self, search):
        rows = db().fetch_all(
            """SELECT s.id, s.sales_date, s.invoice_no, c.name, c.contact_no, s.net_total,
                      s.paid_amount, s.net_total - s.paid_amount AS due,
                      (SELECT COUNT(*) FROM installments i WHERE i.sale_id = s.id
                        AND i.status = 'Paid') || '/' ||
                      (SELECT COUNT(*) FROM installments i WHERE i.sale_id = s.id) AS inst
               FROM sales s JOIN customers c ON c.id = s.customer_id
               WHERE s.company_id = app_company_id() AND s.sale_kind = 'CREDIT'
                     AND (c.name ILIKE %s OR s.invoice_no ILIKE %s)
               ORDER BY s.sales_date DESC, s.id DESC""", (f"%{search}%",) * 2)
        return [(r["id"], r["sales_date"].strftime("%d %b %Y"), r["invoice_no"], r["name"],
                 r["contact_no"], money(r["net_total"]), money(r["paid_amount"]),
                 money(r["due"]), r["inst"]) for r in rows]

    def open_form(self, rec_id=None):
        if rec_id is None:
            return bool(CreditSaleForm(self.username, self).exec())
        InstallmentsDialog(rec_id, self).exec()
        return True

    def on_invoice(self):
        rec_id = self.table.current_id()
        if rec_id is None:
            info(self, "Select a credit sale first.")
            return
        preview_html(self, "Invoice/Bill", sale_invoice_html(rec_id))
