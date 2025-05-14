# Katha Update: Business PIN and QR Code

This update adds customer connection features to the Katha credit management system:

## New Features

1. **Business Dashboard Enhancement**
   - Added a "Customer Connection Details" section to the business dashboard
   - Displays the unique 4-digit business PIN
   - Shows a QR code that customers can scan to connect

2. **Database Enhancements**
   - Automatic PIN generation when creating a business
   - PIN is stored in the database in the `access_pin` field of the `businesses` table

3. **QR Code Generation**
   - QR codes are automatically generated for each business
   - QR codes contain the business's PIN for easy customer connection
   - QR codes are stored in `static/qr_codes/` directory

## Installation

1. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run the database updates:
   ```
   ./run_db_updates.sh
   ```

3. Start the application:
   ```
   python app.py
   ```

## How It Works

1. When a business user logs in and views their dashboard, they will see:
   - Their business PIN (automatically generated if not already set)
   - A QR code that encodes their business information

2. Business owners can share their PIN with customers or let them scan the QR code

3. Customers can use either:
   - The PIN entry screen to manually enter the business PIN
   - The QR code scanner to quickly connect by scanning

## Technical Details

- QR codes contain data in the format: `business:{ACCESS_PIN}`
- Business PINs are 4 digits long and automatically generated
- The QR scanner in the customer app is designed to recognize and process this format
- QR codes are generated using the `qrcode` Python library 