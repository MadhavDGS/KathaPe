# KathaPe - Digital Credit Book

KathaPe is a modern digital credit book application designed to help businesses manage customer credit accounts efficiently. The application allows businesses to track credit transactions with their customers, while customers can monitor their balances with multiple businesses.

## Features

- **Business Dashboard**: Manage customer accounts, track credit and payments
- **Customer Dashboard**: View balances with multiple businesses
- **QR Code Integration**: Easy connection between businesses and customers
- **Transaction Management**: Record credit and payment transactions
- **User Profiles**: Separate interfaces for businesses and customers
- **WhatsApp Reminders**: Integration with WhatsApp for payment reminders
- **Theme Support**: Light and dark theme options
- **Responsive Design**: Works on all devices - mobile, tablet, and desktop

## Technology Stack

- **Backend**: Python with Flask
- **Database**: PostgreSQL with Supabase
- **Frontend**: HTML/CSS, JavaScript, Jinja2 Templates
- **Authentication**: Custom auth system with session management

## Getting Started

### Prerequisites

- Python 3.10 or later
- PostgreSQL database
- Supabase account (optional, for production)

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/MadhavDGS/KathaPe.git
   cd KathaPe
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   Create a `.env` file in the root directory with the following variables:
   ```
   DATABASE_URL=your_database_url
   SECRET_KEY=your_secret_key
   UPLOAD_FOLDER=path_to_upload_folder
   ```

5. Initialize the database:
   ```
   python setup_database.py
   ```

6. Run the application:
   ```
   flask run
   ```

## Deployment on Render

1. Fork or clone this repository to your GitHub account
2. Create a new Web Service on Render
3. Connect your GitHub repository
4. Set the following:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
5. Add environment variables in the Render dashboard
6. Deploy the application

## Screenshots

- Business Dashboard
- Customer Dashboard
- Login/Register Screens
- Transaction Management

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contact

For any inquiries, please reach out to [your contact information]. 