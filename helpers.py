from seller_cloud_api import SellerCloudAPI
from email_helper import send_email
from datetime import datetime
import pandas as pd
from qb_api import QbAPI
import os
import pathlib
from datetime import timedelta


class Frequency:
    def __init__(self):
        self.daily = "daily"
        self.weekly = "weekly"
        self.monthly = "monthly"


class Helpers:
    def get_channel_amounts(self, invoices, channel):
        """Gets the total amount of the invoices."""
        rows = []
        total_amount = 0
        for sc_id, invoice in invoices.items():
            for line in invoice.Line:
                if line.DetailType == "SalesItemLineDetail":
                    total_amount += line.Amount
                    if channel == "VN":
                        sku = line.Description.split(",")[0]
                    else:
                        sku = line.Description

                    # This prevents adding rows for taxes and shipping in the report.
                    if line.Description == "Taxes" or line.Description == "Shipping":
                        continue

                    rows.append(
                        {
                            "sc_order_id": sc_id,
                            "purchase_order_number": invoice.DocNumber,
                            "sku": sku,
                            "item_cost": line.SalesItemLineDetail.UnitPrice,
                            "qty": line.SalesItemLineDetail.Qty,
                            "total_cost": line.SalesItemLineDetail.UnitPrice
                            * line.SalesItemLineDetail.Qty,
                        }
                    )
        return total_amount, rows

    def format_po_date(self, date):
        try:
            dt_obj = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%f")
        except ValueError:
            # Fallback to parsing without microseconds
            dt_obj = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S")

        return dt_obj.strftime("%Y-%m-%d %I:%M %p").lower()

    def get_channel_cost_amounts(self, orders, channel):
        """Gets the total amount of the invoices."""
        rows = []
        total_amount = 0
        for order in orders:
            for item in order["Items"]:
                item_cost = item["AverageCost"]
                rows.append(
                    {
                        "po_date": self.format_po_date(order["ShipDate"]),
                        "sc_order_id": order["ID"],
                        "purchase_order_number": order["OrderSourceOrderID"],
                        "sku": item["ProductIDOriginal"],
                        "item_cost": item_cost,
                        "qty": item["Qty"],
                        "total_cost": item_cost * item["Qty"],
                    }
                )
                total_amount += item_cost * item["Qty"]
        return total_amount, rows

    def create_date_range(self, date, frequency: Frequency):
        """Finds the first and last date according to the frequency."""
        if frequency == "daily":
            first_day = date.strftime("%m/%d/%Y 00:00:00")
            last_day = date.strftime("%m/%d/%Y 23:59:59")
        elif frequency == "weekly":
            first_day = date - timedelta(days=date.weekday())
            last_day = date + timedelta(days=6 - date.weekday())
            first_day, last_day = self.split_week_if_ends_in_month(first_day, last_day)

        elif frequency == "monthly":
            first_day = date.replace(day=1).strftime("%m/%d/%Y 00:00:00")
            last_day = (
                date.replace(month=date.month + 1, day=1) - timedelta(days=1)
            ).strftime("%m/%d/%Y 23:59:59")

        return first_day, last_day

    def split_week_if_ends_in_month(self, first_day, last_day):
        """Splits the week if it ends in a month. Returns week start and end dates."""

        date_format = "%m/%d/%Y %H:%M:%S"

        # Calculate the last day of the start date's month
        next_month = first_day.replace(day=28) + timedelta(
            days=4
        )  # This will never fail
        end_of_month = next_month - timedelta(days=next_month.day)

        # Adjust the end date if it exceeds the end of the month
        if last_day > end_of_month:
            last_day = end_of_month.replace(hour=23, minute=59, second=59)
            first_day = first_day.replace(hour=0, minute=0, second=0)
        else:
            last_day = last_day.replace(hour=23, minute=59, second=59)
            first_day = first_day.replace(hour=0, minute=0, second=0)

        # Return the new date range in the desired string format
        return first_day.strftime(date_format), last_day.strftime(date_format)

    def split_dict(self, input_dict, chunk_size):
        """
        Splits a dictionary into a list of dictionaries of a designated size.

        :param input_dict: Dictionary to be split.
        :param chunk_size: Size of each chunk.
        :return: List of dictionaries.
        """
        # Convert the dictionary items to a list
        items = list(input_dict.items())

        # Use list comprehension to split the list into chunks
        chunked_dicts = [
            dict(items[i : i + chunk_size]) for i in range(0, len(items), chunk_size)
        ]

        return chunked_dicts

    def get_sc_orders(
        self, from_date, to_date, channel, sc_api: SellerCloudAPI, channel_name=None
    ):
        """Gets orders from SellerCloud."""
        try:
            orders = []
            page = 1
            while True:
                if channel_name == "VN":
                    excecute = "GET_AMZ_VEN_ORDERS"

                else:
                    excecute = "GET_SELLERCLOUD_ORDERS"

                response = sc_api.execute(
                    {
                        "url_args": {
                            "from": from_date,
                            "to": to_date,
                            "channel": channel,
                            "page": page,
                        }
                    },
                    excecute,
                )

                if response.status_code == 200:
                    if response.json()["Items"]:
                        orders.extend(response.json()["Items"])
                        page += 1
                    else:
                        break
                else:
                    print(f"Error: Received status code {response.status_code}")
                    raise Exception(
                        f"Error: Received while getting orders from SellerCloud code {response.status_code}"
                    )

            return orders
        except Exception as e:
            print(f"There was an error getting the orders from SellerCloud: {e}")
            return None

    def failure_reporting(self, where, po):
        send_email(f"Error {where}", f"Error creating order for PO: {po}.")

    def create_journal_report(self, rows, channel):
        channel_name_map = {
            "VN": "amazon_vendor",
            "DF": "direct_fulfillment",
            "WH": "dropship",
        }

        df = pd.DataFrame(rows)
        directory = self._create_local_dir()
        file_name = os.path.join(directory, f"{channel_name_map[channel]}_orders.xlsx")
        df.to_excel(file_name, index=False)

        return file_name

    def _create_local_dir(self):
        dir_name = f"{datetime.now().strftime('%b%d,%Y').upper()}"
        local_dir = pathlib.Path(f"tmp/{dir_name}")
        local_dir.mkdir(parents=True, exist_ok=True)
        return local_dir
