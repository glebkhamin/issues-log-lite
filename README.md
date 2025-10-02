# Thinking Machine - Issues Log

A lightweight Flask application for tracking issues with HTMX and Tailwind CSS. No React, no Docker - just simple, fast web development.

## Features

- **Issue Management**: Create, edit, and track issues with priority calculation
- **Priority System**: Automatic Eisenhower matrix-based priority calculation (P1-P4)
- **Filtering & Search**: Filter by status, owner, project, priority, and search text
- **CSV Import/Export**: Import issues from CSV and export filtered results with date-stamped filenames
- **Comments**: Add comments to issues
- **Responsive Design**: Clean, modern UI with Tailwind CSS
- **HTMX Integration**: Dynamic interactions without page reloads

## Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment** (optional):
   ```bash
   cp env.example .env
   # Edit .env to set your admin password
   ```

3. **Run the application**:
   ```bash
   python app.py
   ```

4. **Access the application**:
   - Open http://localhost:5001
   - Login with password: `admin123` (or your custom password from .env)

## Environment Variables

- `APP_PASSWORD`: Admin password for login (default: `admin123`)
- `SECRET_KEY`: Flask secret key for sessions (default: auto-generated)

## Priority System

The application automatically calculates issue priority based on the Eisenhower matrix:

- **P1**: High Importance + High Urgency (Do First)
- **P2**: High Importance + Medium/Low Urgency (Schedule)
- **P3**: Medium Importance + High/Medium Urgency (Delegate)
- **P4**: Low Importance + Any Urgency (Eliminate)

## CSV Import Format

Import issues using a CSV file with these columns:
```
Title, Project, Status, Priority, Owner, Reporter, Date Reported, Target Date, Importance, Urgency, Tags, Description
```

## Running Tests

```bash
pytest test_app.py -v
```

## Project Structure

```
├── app.py              # Main Flask application
├── models.py           # SQLAlchemy models
├── test_app.py         # Test suite
├── requirements.txt    # Python dependencies
├── env.example         # Environment variables template
├── README.md          # This file
└── templates/         # Jinja2 templates
    ├── base.html      # Base template
    ├── index.html     # Main issues page
    ├── login.html     # Login page
    ├── import.html    # CSV import page
    └── edit_form.html # Issue edit form partial
```

## Database

The application uses SQLite (`db.sqlite3`) which is created automatically on first run. Sample data is loaded based on the provided Excel issues log.

## Technologies Used

- **Flask**: Web framework
- **SQLAlchemy**: Database ORM
- **HTMX**: Dynamic interactions
- **Tailwind CSS**: Styling
- **Jinja2**: Template engine
- **pytest**: Testing framework

## License

MIT License - feel free to use and modify as needed.
