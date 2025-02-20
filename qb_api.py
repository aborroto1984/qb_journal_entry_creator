from config import client_data, ref_id_map
from intuitlib.client import AuthClient
from quickbooks import QuickBooks
from quickbooks.objects import (
    Class,
    Account,
    Invoice,
    JournalEntry,
    JournalEntryLine,
    JournalEntryLineDetail,
    Attachable,
    AttachableRef,
    Customer,
)
from datetime import datetime
import os


class QbAPI:
    def __init__(self, current_refresh_token):
        self.auth_client = AuthClient(
            client_id=client_data["client_id"],
            client_secret=client_data["client_secret"],
            environment=client_data["environment"],
            redirect_uri=client_data["redirect_uri"],
        )
        self.client = QuickBooks(
            auth_client=self.auth_client,
            refresh_token=current_refresh_token,
            company_id=client_data["realm_id"],
        )

    def get_journal_entry_id(self, doc_name):
        """
        Gets the ID of a QuickBooks journal entry by its document number (DocNumber).
        """
        try:
            if JournalEntry.filter(DocNumber=doc_name, qb=self.client):
                return JournalEntry.filter(DocNumber=doc_name, qb=self.client)[0].Id
            else:
                return False
        except Exception as e:
            print(
                f"There was an error checking if PO: {doc_name} was already invoiced: {e}"
            )
            return False

    def create_journal_entry(self, amount, channel, to_date):
        """
        Creates a journal entry in QuickBooks for a specific channel.
        """
        try:
            # Creating credit line
            credit_line_detail = JournalEntryLineDetail()
            credit_line_detail.AccountRef = Account.get(29, qb=self.client).to_ref()
            credit_line_detail.PostingType = "Credit"
            credit_line_detail.TaxApplicableOn = "Sales"

            credit_line = JournalEntryLine()
            credit_line.Amount = amount
            credit_line.JournalEntryLineDetail = credit_line_detail

            # Creating cost line
            cost_line_detail = JournalEntryLineDetail()
            cost_line_detail.AccountRef = Account.get(46, qb=self.client).to_ref()
            cost_line_detail.ClassRef = Class.get(
                ref_id_map[channel]["class_ref_id"], qb=self.client
            ).to_ref()
            cost_line_detail.PostingType = "Debit"
            cost_line_detail.TaxApplicableOn = "Sales"

            cost_line = JournalEntryLine()
            cost_line.Amount = amount
            cost_line.JournalEntryLineDetail = cost_line_detail

            # Creating journal entry
            date = to_date[:10]
            date = datetime.strptime(date, "%m/%d/%Y")
            date_for_doc_name = date.strftime("%m%d%Y")
            journal_entry = JournalEntry()
            journal_entry.DocNumber = f"{channel}_COG_{date_for_doc_name}_SC"
            journal_entry.TxnDate = date.strftime("%Y-%m-%d")
            journal_entry.Line = [credit_line, cost_line]

            journal_entry.save(qb=self.client)
            return journal_entry.DocNumber

        except Exception as e:
            print(f"Error while creating journal entry: {e}")

    def create_combined_journal_entry(self, channel_amounts_and_report, to_date):
        """
        Creates a combined journal entry in QuickBooks for all channels.
        """
        try:
            total_amount = sum(
                amount["channel_amount"]
                for amount in channel_amounts_and_report.values()
            )

            lines = []

            # Creating credit line
            credit_line_detail = JournalEntryLineDetail()
            credit_line_detail.AccountRef = Account.get(29, qb=self.client).to_ref()
            credit_line_detail.PostingType = "Credit"
            credit_line_detail.TaxApplicableOn = "Sales"

            credit_line = JournalEntryLine()
            credit_line.Amount = total_amount
            credit_line.JournalEntryLineDetail = credit_line_detail
            lines.append(credit_line)

            for channel, amount in channel_amounts_and_report.items():
                # Creating cost line
                cost_line_detail = JournalEntryLineDetail()
                cost_line_detail.AccountRef = Account.get(46, qb=self.client).to_ref()
                cost_line_detail.ClassRef = Class.get(
                    ref_id_map[channel]["class_ref_id"], qb=self.client
                ).to_ref()
                cost_line_detail.PostingType = "Debit"
                cost_line_detail.TaxApplicableOn = "Sales"

                cost_line = JournalEntryLine()
                cost_line.Amount = amount["channel_amount"]
                cost_line.JournalEntryLineDetail = cost_line_detail
                lines.append(cost_line)

            # Creating journal entry
            date = datetime.strptime(to_date, "%m/%d/%Y")
            date_for_doc_name = date.strftime("%b%d").upper()

            journal_entry = JournalEntry()
            journal_entry.DocNumber = f"COG_{date_for_doc_name}_SC"
            # journal_entry.DocNumber = "test_journal"
            journal_entry.TxnDate = date.strftime("%Y-%m-%d")
            journal_entry.Line = lines

            journal_entry.save(qb=self.client)
            return journal_entry.DocNumber

        except Exception as e:
            print(f"Error while creating journal entry: {e}")

    def attach_file_to_journal_entry(self, file_path, journal_entry_id):
        """
        Attaches a file to a QuickBooks journal entry.
        """
        try:
            file_name = os.path.basename(file_path)

            attachment = Attachable()

            attachable_ref = AttachableRef()
            attachable_ref.EntityRef = {
                "type": "JournalEntry",  # The type of the entity being referenced
                "value": journal_entry_id,  # The ID of the journal entry
            }
            attachment.AttachableRef.append(attachable_ref)

            attachment.FileName = file_name
            attachment._FilePath = file_path
            attachment.ContentType = (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            attachment.save(qb=self.client)

            return True

        except Exception as e:
            print(f"Error while attaching file to journal entry: {e}")
            return False

    def delete_journal_entry(self, txn_id):
        """
        Deletes a QuickBooks journal entry by its transaction ID (TxnId).

        Args:
            quickbooks_client (QuickBooks): The authenticated QuickBooks client.
            txn_id (str): The transaction ID (TxnId) of the journal entry to delete.

        Returns:
            bool: True if the entry was successfully deleted, False otherwise.
        """
        try:
            # Retrieve the journal entry by TxnId
            journal_entry = JournalEntry.filter(DocNumber=txn_id, qb=self.client)[0]

            # Delete the journal entry
            journal_entry.delete(qb=self.client)

            print(f"Journal entry with TxnId {txn_id} has been deleted.")
            return True
        except Exception as e:
            print(f"Failed to delete journal entry with TxnId {txn_id}: {e}")
            return False
