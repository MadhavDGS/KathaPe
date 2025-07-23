# KathaPe - Separated Applications

This project has been restructured to separate business and customer functionalities into independent applications.

## Directory Structure

```
KathaPe/
├── business_app/          # Business application
│   ├── app.py            # Main business Flask app
│   ├── run.py            # Run script for business app
│   ├── requirements.txt  # Business app dependencies
│   ├── templates/        # Business-specific templates
│   │   ├── base.html     # Base template
│   │   ├── login.html    # Login page
│   │   ├── register.html # Registration page
│   │   └── business/     # Business pages
│   └── static/           # Business static files
│
├── customer_app/          # Customer application
│   ├── app.py            # Main customer Flask app
│   ├── run.py            # Run script for customer app
│   ├── requirements.txt  # Customer app dependencies
│   ├── templates/        # Customer-specific templates
│   │   ├── base.html     # Base template
│   │   ├── login.html    # Login page
│   │   ├── register.html # Registration page
│   │   └── customer/     # Customer pages
│   └── static/           # Customer static files
│
├── shared/               # Shared utilities and resources
│   ├── common_utils.py   # Common functions and database utilities
│   ├── templates/        # Shared templates
│   └── static/           # Shared static files
│
└── app_launcher.py       # Main launcher for both apps
```

## Running the Applications

### Option 1: Run Both Applications Together
```bash
python app_launcher.py both
```
- Business app: http://localhost:5001
- Customer app: http://localhost:5002

### Option 2: Run Applications Separately

#### Business Application Only:
```bash
python app_launcher.py business
# OR
cd business_app && python run.py
```

#### Customer Application Only:
```bash
python app_launcher.py customer
# OR
cd customer_app && python run.py
```

## Features

### Business Application (Port 5001)
- Business dashboard
- Customer management
- Transaction management
- QR code generation
- Business profile management

### Customer Application (Port 5002)
- Customer dashboard
- Business selection via PIN
- Transaction history
- Profile management
- API endpoints for mobile apps

## Shared Features
- Common database utilities
- Authentication and session management
- Shared templates and styling
- Database connection pooling
- Request logging middleware

## Environment Setup

Each application can have its own `.env` file, or share a common one from the parent directory.

Required environment variables:
```
DATABASE_URL=your_database_url
SECRET_KEY=your_secret_key
```

## Development

Both applications share the common utilities from the `shared/` directory, ensuring consistency while maintaining separation of concerns.

Each app can be developed, deployed, and scaled independently while sharing the same database and core functionalities.
