from piccolo.table import Table
from piccolo.columns import (
    Varchar,
    UUID,
    ForeignKey,
    Date,
    DoublePrecision,
)





class ProductGuide(Table):
    id = UUID(primary_key=True)
    product = Varchar(null=False)
    line_of_business = Varchar(null=True)
    active_substance = Varchar(null=True)


#

class Remains(Table):
    id = UUID(primary_key=True)
    line_of_business = Varchar(null=False)
    warehouse = Varchar(null=True)
    parent_element = Varchar(null=True)
    nomenclature = Varchar(null=True)
    party_sign = Varchar(null=True)
    buying_season = Varchar(null=True)
    nomenclature_series = Varchar(null=True)
    mtn = Varchar(null=True)
    origin_country = Varchar(null=True)
    germination = Varchar(null=True)
    crop_year = Varchar(null=True)
    quantity_per_pallet = Varchar(null=True)
    active_substance = Varchar(null=True)
    certificate = Varchar(null=True)
    certificate_start_date = Varchar(null=True)
    certificate_end_date = Varchar(null=True)
    buh = DoublePrecision()
    skl = DoublePrecision()
    weight = Varchar(null=True)
    product = ForeignKey(references=ProductGuide)


class Submissions(Table):
    id = UUID(primary_key=True)
    division = Varchar(null=True)
    manager = Varchar(null=True)
    company_group = Varchar(null=True)
    client = Varchar(null=True)
    contract_supplement = Varchar(null=True)
    parent_element = Varchar(null=True)
    manufacturer = Varchar(null=True)
    active_ingredient = Varchar(null=True)
    nomenclature = Varchar(null=True)
    party_sign = Varchar(null=True)
    buying_season = Varchar(null=True)
    line_of_business = Varchar(null=True)
    period = Varchar(null=True)
    shipping_warehouse = Varchar(null=True)
    document_status = Varchar(null=True)
    delivery_status = Varchar(null=True)
    shipping_address = Varchar(null=True)
    transport = Varchar(null=True)
    plan = DoublePrecision()
    fact = DoublePrecision()
    different = DoublePrecision()
    product = ForeignKey(references=ProductGuide)


class AvailableStock(Table):
    id = UUID(primary_key=True)
    nomenclature = Varchar(null=True)
    party_sign = Varchar(null=True)
    buying_season = Varchar(null=True)
    division = Varchar(null=True)
    line_of_business = Varchar(null=True)
    available = DoublePrecision()
    product = ForeignKey(references=ProductGuide)


class ProductUnderSubmissions(Table):
    id = UUID(primary_key=True)
    product = ForeignKey(references=ProductGuide)
    quantity = DoublePrecision()


class MovedData(Table):
    id = UUID(primary_key=True)
    product = Varchar()
    contract = Varchar(null=True)
    date = Date()
    line_of_business = Varchar()
    qt_order = Varchar()
    qt_moved = Varchar()
    party_sign = Varchar()
    period = Varchar()
    order = Varchar()


class MovedNot(Table):
    id = UUID(primary_key=True)
    product = Varchar()
    quantity = Varchar()
    contract = Varchar()
    note = Varchar()


class Payment(Table):
    id = UUID(primary_key=True)
    contract_supplement = Varchar()
    contract_type = Varchar()
    prepayment_amount = DoublePrecision()
    amount_of_credit = DoublePrecision()
    prepayment_percentage = DoublePrecision()
    loan_percentage = DoublePrecision()
    planned_amount = DoublePrecision()
    planned_amount_excluding_vat = DoublePrecision()
    actual_sale_amount = DoublePrecision()
    actual_payment_amount = DoublePrecision()



