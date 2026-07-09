from datetime import datetime
def parse_partner_date(value):
    return datetime.strptime(value, "%Y-%m-%d")
