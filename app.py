import os
import csv
import io
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, Response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash
from models import db, User, Organization, Issue, Comment

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Admin password from environment
ADMIN_PASSWORD = os.environ.get('APP_PASSWORD', 'admin123')

def require_auth(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session['authenticated'] = True
            return redirect(url_for('index'))
        else:
            flash('Invalid password', 'error')
    return render_template('login.html')

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('authenticated', None)
    return redirect(url_for('login'))

@app.route('/')
@require_auth
def index():
    # Get filter parameters
    status_filter = request.args.get('status', '')
    owner_filter = request.args.get('owner', '')
    organization_filter = request.args.get('organization', '')
    search_query = request.args.get('q', '')

    # Build query
    query = Issue.query

    if status_filter:
        query = query.filter(Issue.status == status_filter)
    if owner_filter:
        query = query.filter(Issue.owner == owner_filter)
    if organization_filter:
        query = query.filter(Issue.organization_id == organization_filter)
    if search_query:
        query = query.filter(
            (Issue.title.contains(search_query)) |
            (Issue.description.contains(search_query)) |
            (Issue.reporter.contains(search_query))
        )

    # Sort by display_order first (for manual ordering), then by date_reported (oldest first = most important)
    query = query.order_by(Issue.display_order.asc(), Issue.date_reported.asc())

    issues = query.all()

    # Get filter options
    statuses = db.session.query(Issue.status).distinct().all()
    owners = db.session.query(Issue.owner).filter(Issue.owner.isnot(None)).distinct().all()
    organizations = Organization.query.all()

    return render_template('index.html', 
                         issues=issues,
                         statuses=[s[0] for s in statuses],
                         owners=[o[0] for o in owners],
                         organizations=organizations,
                         current_filters={
                             'status': status_filter,
                             'owner': owner_filter,
                             'organization': organization_filter,
                             'q': search_query
                         },
                         date=date)

@app.route('/issues', methods=['POST'])
@require_auth
def create_issue():
    data = request.get_json()
    
    issue = Issue(
        title=data['title'],
        description=data.get('description', ''),
        reporter=data['reporter'],
        owner=data.get('owner'),
        organization_id=data.get('organization_id'),
        status=data.get('status', 'Open'),
        importance=data.get('importance', 'Medium'),
        date_reported=datetime.strptime(data['date_reported'], '%Y-%m-%d').date() if data.get('date_reported') else date.today(),
        target_date=datetime.strptime(data['target_date'], '%Y-%m-%d').date() if data.get('target_date') else None
    )
    
    db.session.add(issue)
    db.session.commit()
    
    return jsonify({'success': True, 'id': issue.id})

@app.route('/issues/<int:issue_id>', methods=['POST'])
@require_auth
def update_issue(issue_id):
    issue = Issue.query.get_or_404(issue_id)
    data = request.get_json()
    
    # Update fields
    issue.title = data.get('title', issue.title)
    issue.description = data.get('description', issue.description)
    issue.reporter = data.get('reporter', issue.reporter)
    issue.owner = data.get('owner', issue.owner)
    issue.organization_id = data.get('organization_id', issue.organization_id)
    issue.status = data.get('status', issue.status)
    issue.importance = data.get('importance', issue.importance)
    issue.target_date = datetime.strptime(data['target_date'], '%Y-%m-%d').date() if data.get('target_date') else None
    issue.updated_at = datetime.utcnow()
    
    db.session.commit()
    return jsonify({'success': True})

@app.route('/issues/<int:issue_id>/edit')
@require_auth
def edit_issue_form(issue_id):
    issue = Issue.query.get_or_404(issue_id)
    organizations = Organization.query.all()
    return render_template('edit_form.html', issue=issue, organizations=organizations)

@app.route('/issues/<int:issue_id>', methods=['DELETE'])
@require_auth
def delete_issue(issue_id):
    issue = Issue.query.get_or_404(issue_id)
    
    # Delete associated comments first
    Comment.query.filter_by(issue_id=issue_id).delete()
    
    # Delete the issue
    db.session.delete(issue)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/issues/<int:issue_id>/comment', methods=['POST'])
@require_auth
def add_comment(issue_id):
    issue = Issue.query.get_or_404(issue_id)
    data = request.get_json()
    
    comment = Comment(
        issue_id=issue_id,
        author=data['author'],
        body=data['body']
    )
    
    db.session.add(comment)
    db.session.commit()
    
    return jsonify({'success': True})

# Add organization management routes
@app.route('/organizations', methods=['POST'])
@require_auth
def create_organization():
    data = request.get_json()
    
    # Check if organization already exists
    existing = Organization.query.filter_by(name=data['name']).first()
    if existing:
        return jsonify({'success': False, 'error': 'Organisation name already exists'}), 400
    
    try:
        organization = Organization(name=data['name'])
        db.session.add(organization)
        db.session.commit()
        return jsonify({'success': True, 'id': organization.id, 'name': organization.name})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Organisation name already exists'}), 400

@app.route('/organizations/<int:org_id>', methods=['DELETE'])
@require_auth
def delete_organization(org_id):
    organization = Organization.query.get_or_404(org_id)
    
    # Check if organization is used by any issues
    issue_count = Issue.query.filter_by(organization_id=org_id).count()
    if issue_count > 0:
        return jsonify({
            'success': False, 
            'error': f"Can't delete '{organization.name}'. It's used by {issue_count} issues. Reassign or close those issues first.",
            'issue_count': issue_count
        }), 400
    
    db.session.delete(organization)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/manage-organisations')
@require_auth
def manage_organisations():
    organizations = Organization.query.all()
    # Get issue counts for each organization
    org_data = []
    for org in organizations:
        issue_count = Issue.query.filter_by(organization_id=org.id).count()
        org_data.append({
            'id': org.id,
            'name': org.name,
            'created_at': org.created_at,
            'issue_count': issue_count
        })
    return render_template('manage_organisations.html', organizations=org_data)

@app.route('/export.csv')
@require_auth
def export_csv():
    # Apply same filters as index
    status_filter = request.args.get('status', '')
    owner_filter = request.args.get('owner', '')
    organization_filter = request.args.get('organization', '')
    search_query = request.args.get('q', '')

    query = Issue.query

    if status_filter:
        query = query.filter(Issue.status == status_filter)
    if owner_filter:
        query = query.filter(Issue.owner == owner_filter)
    if organization_filter:
        query = query.filter(Issue.organization_id == organization_filter)
    if search_query:
        query = query.filter(
            (Issue.title.contains(search_query)) |
            (Issue.description.contains(search_query)) |
            (Issue.reporter.contains(search_query))
        )

    # Always sort by date_reported (oldest first)
    query = query.order_by(Issue.date_reported.asc())
    issues = query.all()

    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Title', 'Description', 'Organisation', 'Status', 'Date Reported', 
                    'Reported By', 'Owner', 'Importance', 'Target Date'])
    
    # Write data
    for issue in issues:
        organization_name = issue.organization.name if issue.organization else ''
        writer.writerow([
            issue.title,
            issue.description or '',
            organization_name,
            issue.status,
            issue.date_reported.strftime('%Y-%m-%d') if issue.date_reported else '',
            issue.reporter,
            issue.owner or '',
            issue.importance,
            issue.target_date.strftime('%Y-%m-%d') if issue.target_date else ''
        ])
    
    output.seek(0)
    
    # Generate filename with current date
    current_date = datetime.now().strftime('%Y-%m-%d')
    filename = f'issues_{current_date}.csv'
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )

@app.route('/import', methods=['GET', 'POST'])
@require_auth
def import_csv():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(url_for('import_csv'))
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('import_csv'))
        
        if file and file.filename.endswith('.csv'):
            # Read CSV
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_input = csv.DictReader(stream)
            
            issues = []
            for row in csv_input:
                # Create or get organization (support both Organization and Organisation)
                organization = None
                org_name = row.get('Organisation') or row.get('Organization')
                if org_name:
                    organization = Organization.query.filter_by(name=org_name).first()
                    if not organization:
                        organization = Organization(name=org_name)
                        db.session.add(organization)
                        db.session.flush()
                
                # Parse dates
                date_reported = None
                if row.get('Date Reported'):
                    try:
                        date_reported = datetime.strptime(row['Date Reported'], '%Y-%m-%d').date()
                    except:
                        pass
                
                target_date = None
                if row.get('Target Date'):
                    try:
                        target_date = datetime.strptime(row['Target Date'], '%Y-%m-%d').date()
                    except:
                        pass
                
                issue = Issue(
                    title=row.get('Title', ''),
                    description=row.get('Description', ''),
                    reporter=row.get('Reporter', ''),
                    owner=row.get('Owner') or None,
                    organization_id=organization.id if organization else None,
                    status=row.get('Status', 'Open'),
                    importance=row.get('Importance', 'Medium'),
                    date_reported=date_reported or date.today(),
                    target_date=target_date
                )
                
                issues.append(issue)
            
            # Commit all issues
            for issue in issues:
                db.session.add(issue)
            db.session.commit()
            
            flash(f'Successfully imported {len(issues)} issues', 'success')
            return redirect(url_for('index'))
    
    return render_template('import.html')

@app.route('/issues/reorder', methods=['POST'])
@require_auth
def reorder_issues():
    """Reorder issues based on drag and drop"""
    try:
        data = request.get_json()
        issue_ids = data.get('issue_ids', [])
        
        if not issue_ids:
            return jsonify({'success': False, 'error': 'No issue IDs provided'}), 400
        
        # Update the display_order for each issue based on its position
        for index, issue_id in enumerate(issue_ids):
            issue = Issue.query.get(issue_id)
            if issue:
                issue.display_order = index
                issue.updated_at = datetime.utcnow()
        
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

def init_db():
    """Initialize database with sample data"""
    with app.app_context():
        db.create_all()
        
        # Create sample organisations
        if not Organization.query.first():
            organizations = [
                Organization(name='HAL Platform'),
                Organization(name='Data Views'),
                Organization(name='Contract Management'),
                Organization(name='Document History'),
                Organization(name='Form Builder'),
                Organization(name='Data Manager')
            ]
            for organization in organizations:
                db.session.add(organization)
            db.session.commit()
        
        # Create sample issues based on the Excel data
        if not Issue.query.first():
            organizations = {o.name: o for o in Organization.query.all()}
            
            sample_issues = [
                {
                    'title': 'HAL issue',
                    'description': 'HAL platform issue.',
                    'reporter': 'Prith',
                    'owner': 'Neeraj',
                    'organization': 'HAL Platform',
                    'status': 'In Progress',
                    'importance': 'High',
                    'date_reported': '2025-09-22'
                },
                {
                    'title': 'Data views issue',
                    'description': 'Table layout saves filters, segments, formatting but cannot save column order or selected columns. Planned for future builds.',
                    'reporter': 'Prith',
                    'owner': 'Neeraj',
                    'organization': 'Data Views',
                    'status': 'In Progress',
                    'importance': 'Medium',
                    'date_reported': '2025-08-27'
                },
                {
                    'title': 'Contract price tables',
                    'description': 'Contract price tables issue.',
                    'reporter': 'Smit',
                    'owner': None,
                    'organization': 'Contract Management',
                    'status': 'Open',
                    'importance': 'Medium',
                    'date_reported': '2025-09-09'
                },
                {
                    'title': 'Redcentric job ID inconsistent assignment',
                    'description': 'Reprocessing requires 2 attempts for correct job ID assignment. Raised after Richard\'s job ID task.',
                    'reporter': 'Gleb',
                    'owner': 'Eldho',
                    'organization': 'Data Manager',
                    'status': 'Completed',
                    'importance': 'High',
                    'date_reported': '2025-09-11'
                },
                {
                    'title': 'Simfoni exceptions page',
                    'description': 'Exceptions page issue.',
                    'reporter': 'Gleb',
                    'owner': 'Aswin',
                    'organization': 'Data Views',
                    'status': 'In Progress',
                    'importance': 'Medium',
                    'date_reported': '2025-09-15'
                },
                {
                    'title': 'Database/Document History sort by timestamp',
                    'description': 'Request to add descending sort by timestamp.',
                    'reporter': 'Gleb',
                    'owner': 'Aswin',
                    'organization': 'Document History',
                    'status': 'In Progress',
                    'importance': 'Low',
                    'date_reported': '2025-09-15'
                },
                {
                    'title': 'Renae Caliber invoice issue',
                    'description': 'Awaiting additional info from Renae.',
                    'reporter': 'Renae',
                    'owner': None,
                    'organization': 'Contract Management',
                    'status': 'Pending Info',
                    'importance': 'Medium',
                    'date_reported': '2025-09-24'
                },
                {
                    'title': 'Data-view (DuckDB performance)',
                    'description': 'DuckDB currently loads all data at once, causing performance issues. Updating to fetch in chunks with SQL queries.',
                    'reporter': 'Richard',
                    'owner': None,
                    'organization': 'Data Views',
                    'status': 'In Progress',
                    'importance': 'High',
                    'date_reported': '2025-09-24'
                },
                {
                    'title': 'Form builder for insights page',
                    'description': 'Form builder issue.',
                    'reporter': 'Richard',
                    'owner': None,
                    'organization': 'Form Builder',
                    'status': 'Open',
                    'importance': 'Low',
                    'date_reported': '2025-09-24'
                },
                {
                    'title': 'Data Manager - editing & updating',
                    'description': 'Allow editing/updating data back into database from frontend (e.g. contract management).',
                    'reporter': 'Richard',
                    'owner': 'Gleb',
                    'organization': 'Data Manager',
                    'status': 'Open',
                    'importance': 'Medium',
                    'date_reported': '2025-09-26'
                },
                {
                    'title': 'Document history page issue (Redcentric)',
                    'description': 'Not urgent issue on document history page.',
                    'reporter': 'Richard',
                    'owner': None,
                    'organization': 'Document History',
                    'status': 'Open',
                    'importance': 'Low',
                    'date_reported': '2025-09-10'
                }
            ]
            
            for issue_data in sample_issues:
                organization = organizations.get(issue_data['organization'])
                
                issue = Issue(
                    title=issue_data['title'],
                    description=issue_data['description'],
                    reporter=issue_data['reporter'],
                    owner=issue_data['owner'],
                    organization_id=organization.id if organization else None,
                    status=issue_data['status'],
                    importance=issue_data['importance'],
                    date_reported=datetime.strptime(issue_data['date_reported'], '%Y-%m-%d').date()
                )
                db.session.add(issue)
            
            db.session.commit()

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=True, host='0.0.0.0', port=port)
