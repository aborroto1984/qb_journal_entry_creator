from quick_books_db import QuickBooksDb
from seller_cloud_api import SellerCloudAPI
from qb_api import QbAPI
from email_helper import send_email
from datetime import datetime, timedelta
import traceback
from helpers import Helpers
from decimal_rounding import round_to_decimal


def main():
    try:
        config = {
            "run_DF": True,
            "run_WH": True,
            "run_VN": True,
            "run_combined": False,
            "run_individual": True,
        }

        class Frequency:
            def __init__(self):
                self.daily = "daily"
                self.weekly = "weekly"
                self.monthly = "monthly"

        h = Helpers()
        f = Frequency()
        sc_api = SellerCloudAPI()

        today = datetime.now() - timedelta(days=1)

        # from_date, to_date = h.create_date_range(today, f.monthly)
        from_date, to_date = h.create_date_range(today, f.daily)
        print(f"Date range. From date: {from_date}, To date: {to_date}")

        # Getting orders------------------------------------------------------------------------
        all_orders = {}

        # DF
        if config["run_DF"]:
            df_orders = h.get_sc_orders(from_date, to_date, 66, sc_api)
            if df_orders:
                all_orders["DF"] = df_orders

        # Dropship
        if config["run_WH"]:
            dropship_orders = h.get_sc_orders(from_date, to_date, 21, sc_api)
            if dropship_orders:
                all_orders["WH"] = dropship_orders

        # Amazon Vendor
        if config["run_VN"]:
            amz_ven_orders = h.get_sc_orders(
                from_date, to_date, 0, sc_api, channel_name="VN"
            )
            if amz_ven_orders:
                all_orders["VN"] = amz_ven_orders

        if all_orders:

            # Extracting cost of goods sold from SellerCloud------------------------------------------------------------------------
            qb_db = QuickBooksDb()
            current_refresh_token = qb_db.get_refresh_token()
            qb_api = QbAPI(current_refresh_token)

            if qb_api.client.refresh_token != current_refresh_token:
                qb_db.update_refresh_token(qb_api.client.refresh_token)

            channel_amounts_and_report = {}

            for channel, orders in all_orders.items():
                print(f"Processing {channel} - {len(orders)} orders...")

                # Extracting channel amounts and creating journal report rows
                channel_amount, report_rows = h.get_channel_cost_amounts(
                    orders, channel
                )

                channel_amount = round_to_decimal(channel_amount)
                report_path = h.create_journal_report(report_rows, channel)

                channel_amounts_and_report[channel] = {
                    "channel_amount": channel_amount,
                    "report_path": report_path,
                }
                print(
                    f"Channel: {channel}, Order: {len(orders)} Amount: {channel_amount}"
                )

            # Creating individual journal entries------------------------------------------------------------------------
            if config["run_individual"]:
                journals_created = []
                if not channel_amounts_and_report:
                    send_email(
                        "No journal created",
                        "There was no sales data to create journal with.",
                    )

                for channel, data in channel_amounts_and_report.items():
                    amount = data["channel_amount"]
                    report_path = data["report_path"]

                    if amount > 0:
                        journal_entry_number = qb_api.create_journal_entry(
                            amount, channel, to_date
                        )
                        if journal_entry_number:
                            journal_entry_id = qb_api.get_journal_entry_id(
                                journal_entry_number
                            )
                            if journal_entry_id:
                                print(
                                    f"Individual journal entry {journal_entry_number} created for {channel}"
                                )
                                if qb_api.attach_file_to_journal_entry(
                                    report_path, journal_entry_id
                                ):
                                    print(
                                        f"File attached to journal entry for {channel}"
                                    )
                                    journals_created.append(journal_entry_number)

                print("Individual journal entries created")
                entries_str = ", ".join(journals_created)
                send_email(
                    "Journal Entries Created",
                    f"Journal entries created: {entries_str}",
                )

            # Creating combined journal entry------------------------------------------------------------------------
            if config["run_combined"]:
                journal_entry_number = qb_api.create_combined_journal_entry(
                    channel_amounts_and_report, to_date
                )
                print(f"Combined journal created, entry number: {journal_entry_number}")
                journal_entry_id = qb_api.get_journal_entry_id(journal_entry_number)
                for file_path in [
                    amount["report_path"]
                    for amount in channel_amounts_and_report.values()
                ]:
                    if qb_api.attach_file_to_journal_entry(file_path, journal_entry_id):
                        print(
                            f"File {file_path} \nattached to journal entry {journal_entry_number}"
                        )

                print("Combined journal entry created")

    except Exception as e:
        print(e)
        send_email("Unexpected Error", traceback.format_exc())
        raise e


if __name__ == "__main__":
    main()
