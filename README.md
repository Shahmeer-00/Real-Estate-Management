
# 🏠 Real Estate Management Dashboard

A modern, interactive real estate management system built with **Python** and **Streamlit**. It is designed as a beginner-friendly BS Computer Science / Data Science university project and can be deployed for free on **Streamlit Community Cloud**.

## Project Overview

The dashboard helps a real estate agency manage properties, customers, agents, inquiries and viewings, sales, rental agreements, payments, and reports. All amounts are in **Pakistani Rupees (PKR)**. Every dashboard number is calculated from the records stored in the application. Nothing is hardcoded.

## Main Features

- **Dashboard**: KPI cards (properties by status, customers, agents, sales revenue, rental income, pending payments), recent listings, recent transactions, distribution charts and monthly income charts.
- **Properties**: add, edit, view and delete listings; search, filter (type, listing type, price range, status) and sort; card view with images or a placeholder; duplicate-ID protection.
- **Customers**: registration, search/filter, and a profile showing inquiries, transactions, rentals and payments.
- **Agents**: CRUD, property assignment, performance statistics and commission tracking.
- **Inquiries & Viewings**: status tracking, viewing scheduling, outcomes and conversion rate.
- **Sales & Transactions**: automatic commission, duplicate-sale prevention, status updates, summaries (downloadable).
- **Rentals**: agreements, overlap prevention, automatic expiry, upcoming expirations, rent schedule generation.
- **Payments**: partial payments with accurate balances, overdue detection, unique reference numbers, payment history.
- **Reports & Analytics**: filters by date range, property type, city and agent; charts and tables; CSV export of all seven record types.
- **Data tools**: JSON backup download, restore, sample data, and a guarded erase option.

### Built-in business rules

| Rule | Behaviour |
|---|---|
| Property status | Calculated automatically: Sold, Rented, Under Negotiation or Available |
| Sales revenue | Only **Completed** sales count; Pending and Cancelled never do |
| Commission | Sale price x commission %, once per transaction, completed sales only |
| Rental income | Only rent actually **received** (Monthly Rent payments); deposits are not income |
| Pending payments | Remaining balance of Pending, Partially Paid and Overdue payments (cancelled transactions excluded) |
| Deletion | Records that are used by other records cannot be deleted |

## Technologies Used

- Python 3.9 or newer
- [Streamlit](https://streamlit.io/) for the web interface
- [Pandas](https://pandas.pydata.org/) for tables and charts data
- Python standard library (`json`, `datetime`, `pathlib`, `re`, ...) for storage and logic

## Project Structure

```
real-estate-dashboard/
├── app.py            # Entire application: UI, logic, data handling
├── requirements.txt  # Third-party dependencies
└── README.md         # Documentation
```

At runtime the app creates `realestate_data.json` to store your data. It is generated automatically and is not part of the source code (do not commit it if it contains private data).

## Prerequisites

- Python 3.9+ ([python.org](https://www.python.org/downloads/))
- `pip` (included with Python)
- Git and a free GitHub account (for deployment)

## Installation

### 1. Get the files

Place `app.py`, `requirements.txt` and `README.md` in one folder, for example `real-estate-dashboard`.

### 2. Create a virtual environment

```bash
cd real-estate-dashboard

# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

## Running Locally

```bash
streamlit run app.py
```

Your browser opens at `http://localhost:8501`. On the Dashboard you can click **Load sample data** to explore with demo records.

## Uploading to GitHub

1. Create a new **public** repository on GitHub (for example `real-estate-dashboard`).
2. In your project folder run:

```bash
git init
git add app.py requirements.txt README.md
git commit -m "Initial commit: Real Estate Management Dashboard"
git branch -M main
git remote add origin https://github.com/<your-username>/real-estate-dashboard.git
git push -u origin main
```

(Optionally add a `.gitignore` locally containing `realestate_data.json` and `venv/` so private data is never uploaded. It is not needed by the app.)

## Deploying on Streamlit Community Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
2. Click **Create app** (or **New app**) and choose **Deploy a public app from GitHub**.
3. Select your repository, the branch `main`, and set **Main file path** to `app.py`.
4. (Optional) Choose a custom app URL.
5. Click **Deploy**. The first build installs the packages from `requirements.txt` and takes a few minutes.
6. Open the generated URL and share it. Every `git push` to the branch redeploys the app automatically.

## Sample Workflow

1. **Agents** > *Add Agent*: create an agent with a commission percentage (for example 2%).
2. **Customers** > *Register Customer*: add a seller and a buyer.
3. **Properties** > *Add Property*: list a house "For Sale" at PKR 20,000,000 and assign the agent.
4. **Inquiries** > *Register Inquiry*: record the buyer's interest, then schedule a viewing.
5. **Sales** > *New Transaction*: choose the property, buyer, seller and agent. The commission is calculated automatically. Save it as *Pending* (the property becomes *Under Negotiation*).
6. **Payments** > *Record Payment*: add a *Sale Payment* of PKR 5,000,000 with status *Partially Paid*. The remaining balance is shown.
7. **Sales** > *Update / Cancel*: set the transaction to *Completed*. The property becomes *Sold*, revenue and commission update everywhere.
8. **Rentals**: create an agreement for a rental property, click **Generate rent schedule**, then record rent in **Payments**. Unpaid rent becomes *Overdue* after its due date.
9. **Reports & Analytics**: filter by date, type, city or agent and download CSV files.

## Data Persistence Limitations

- Data is stored in Streamlit Session State and saved to a local file (`realestate_data.json`) after every successful change. It survives normal reruns and page navigation.
- **On Streamlit Community Cloud, local files are NOT guaranteed to persist.** Restarts, redeployments, inactivity sleep and moving the app can erase the file. This app does not provide guaranteed permanent cloud storage.
- Use **About & Help > Download full backup** regularly, and **Restore backup** after a reset.
- The app is intended for one user or a small demo group. If several people edit at the same time, the last save wins.
- For production use, replace the JSON storage with a real database (see Future Improvements).

## Troubleshooting

| Problem | Solution |
|---|---|
| `streamlit: command not found` | Activate the virtual environment, then run `pip install -r requirements.txt`. Or use `python -m streamlit run app.py`. |
| Data disappeared on Streamlit Cloud | Expected after restarts; restore from your JSON backup. |
| Message about an unreadable data file | The bad file was kept as `realestate_data.corrupted.json` and the app started empty. Restore a backup. |
| "Cannot delete" message | The record is used by others (for example a customer with a transaction). Remove or reassign those records first. |
| A property is missing from the sale form | It must be "For Sale", not sold/rented, and have no pending or completed transaction. |
| Property image does not appear | Use a full `http://` or `https://` image link. A placeholder is shown if the link is missing or broken. |
| Deployment build fails | Check that `requirements.txt` is in the repository root and the main file path is `app.py`. |
| Port already in use | Run `streamlit run app.py --server.port 8502`. |

## Future Improvement Suggestions

- Replace JSON storage with SQLite, PostgreSQL or Supabase for permanent storage.
- Add user login and roles (admin, agent).
- Upload property photos, PDF rental agreements and receipts.
- Email or SMS reminders for rent due dates and viewings.
- Map view for properties, and rental commission rules.
- Automated tests and an audit log of changes.
