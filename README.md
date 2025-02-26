# QuickBooks Journal Entry Automation System

This project automates the process of retrieving sales data from SellerCloud, calculating cost of goods sold, and creating journal entries in QuickBooks.

## Features
- Fetches sales data from SellerCloud for multiple channels.
- Calculates cost of goods sold (COGS).
- Creates individual and combined journal entries in QuickBooks.
- Attaches reports to journal entries in QuickBooks.
- Sends email notifications for errors and updates.

## Project Structure
```
project_root/
├── config.py              # Configuration file for database, API, and email credentials
├── decimal_rounding.py    # Rounds decimal values for financial accuracy
├── email_helper.py        # Sends email notifications
├── helpers.py             # Utility functions for data processing
├── main.py                # Main script orchestrating journal entry creation
├── qb_api.py              # Handles QuickBooks API interactions
├── quick_books_db.py      # Manages QuickBooks database operations
├── seller_cloud_api.py    # Interfaces with SellerCloud API
```

## Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/your-repo/qb-journal-automation.git
cd qb-journal-automation
```

### 2. Install Dependencies
Ensure you have Python 3 installed, then install dependencies:
```bash
pip install -r requirements.txt
```

### 3. Configure the System
Modify `config.py` with your database, QuickBooks, and SellerCloud credentials.

Example database configuration:
```python
db_config = {
    "ExampleDb": {
        "server": "your.database.windows.net",
        "database": "YourDB",
        "username": "your_user",
        "password": "your_password",
        "driver": "{ODBC Driver 17 for SQL Server}",
    },
}
```
Example email configuration:
```python
SENDER_EMAIL = "your_email@example.com"
SENDER_PASSWORD = "your_email_password"
```

## Usage
Run the main script to start the journal entry process:
```bash
python main.py
```

## How It Works
1. Fetches sales data from SellerCloud.
2. Calculates cost of goods sold for each channel.
3. Creates individual journal entries in QuickBooks.
4. Optionally creates a combined journal entry.
5. Attaches generated reports to QuickBooks entries.
6. Sends email notifications upon success or failure.

## Tech Stack
- Python 3
- Azure SQL Database (`pyodbc`)
- SellerCloud API Integration
- QuickBooks API Integration
- Email Notifications (`smtplib`)
- Decimal rounding for financial accuracy

## Troubleshooting
- If you encounter database connection issues, ensure `ODBC Driver 17` is installed.
- If emails fail to send, ensure your SMTP settings allow external authentication.
- Verify SellerCloud and QuickBooks credentials if API requests fail.
