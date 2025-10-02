import pytest
import json
from datetime import date
from app import app, db, Issue, Organization

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client

@pytest.fixture
def auth_client(client):
    """Client with authentication"""
    with client.session_transaction() as sess:
        sess['authenticated'] = True
    return client

@pytest.fixture
def sample_organization():
    organization = Organization(name='Test Organization')
    db.session.add(organization)
    db.session.commit()
    return organization

def test_login_page(client):
    """Test login page loads"""
    response = client.get('/login')
    assert response.status_code == 200
    assert b'Thinking Machine - Issues Log' in response.data

def test_login_success(client):
    """Test successful login"""
    response = client.post('/login', data={'password': 'admin123'})
    assert response.status_code == 302  # Redirect to index

def test_login_failure(client):
    """Test failed login"""
    response = client.post('/login', data={'password': 'wrong'})
    assert response.status_code == 200
    assert b'Invalid password' in response.data

def test_index_requires_auth(client):
    """Test index page requires authentication"""
    response = client.get('/')
    assert response.status_code == 302  # Redirect to login

def test_index_with_auth(auth_client):
    """Test index page with authentication"""
    response = auth_client.get('/')
    assert response.status_code == 200
    assert b'Issues' in response.data

def test_create_issue(auth_client, sample_organization):
    """Test creating a new issue"""
    issue_data = {
        'title': 'Test Issue',
        'description': 'Test description',
        'reporter': 'Test User',
        'owner': 'Test Owner',
        'organization_id': sample_organization.id,
        'status': 'Open',
        'importance': 'High',
        'date_reported': '2025-01-15'
    }
    
    response = auth_client.post('/issues', 
                               data=json.dumps(issue_data),
                               content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] == True
    
    # Verify issue was created
    issue = Issue.query.filter_by(title='Test Issue').first()
    assert issue is not None
    assert issue.title == 'Test Issue'
    assert issue.importance == 'High'

def test_export_csv(auth_client, sample_organization):
    """Test CSV export functionality"""
    # Create a test issue
    issue = Issue(
        title='Export Test',
        description='Test for export',
        reporter='Test User',
        organization_id=sample_organization.id,
        status='Open',
        importance='Medium',
        date_reported=date.today()
    )
    db.session.add(issue)
    db.session.commit()
    
    response = auth_client.get('/export.csv')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'text/csv; charset=utf-8'
    assert b'Export Test' in response.data
    
    # Test that filename includes current date
    from datetime import datetime
    current_date = datetime.now().strftime('%Y-%m-%d')
    expected_filename = f'issues_{current_date}.csv'
    content_disposition = response.headers.get('Content-Disposition', '')
    assert expected_filename in content_disposition

def test_create_organization(auth_client):
    """Test creating a new organisation"""
    response = auth_client.post('/organizations',
                               data=json.dumps({'name': 'Unique Test Organisation'}),
                               content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] == True
    assert data['name'] == 'Unique Test Organisation'
    
    # Verify organisation was created
    organization = Organization.query.filter_by(name='Unique Test Organisation').first()
    assert organization is not None
    assert organization.name == 'Unique Test Organisation'

def test_create_duplicate_organization(auth_client):
    """Test creating a duplicate organisation fails"""
    # Create first organisation via API
    response1 = auth_client.post('/organizations',
                                data=json.dumps({'name': 'Unique Duplicate Test'}),
                                content_type='application/json')
    assert response1.status_code == 200
    
    # Try to create duplicate
    response2 = auth_client.post('/organizations',
                                data=json.dumps({'name': 'Unique Duplicate Test'}),
                                content_type='application/json')
    
    assert response2.status_code == 400
    data = json.loads(response2.data)
    assert data['success'] == False
    assert 'already exists' in data['error']

def test_delete_unused_organization(auth_client):
    """Test deleting an unused organisation"""
    # Create organisation
    org = Organization(name='Unused Organisation')
    db.session.add(org)
    db.session.commit()
    org_id = org.id
    
    # Delete it
    response = auth_client.delete(f'/organizations/{org_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] == True
    
    # Verify it's deleted
    assert Organization.query.get(org_id) is None

def test_delete_used_organization(auth_client, sample_organization):
    """Test deleting a used organisation fails"""
    # Create an issue using the organisation
    issue = Issue(
        title='Test Issue',
        description='Test description',
        reporter='Test User',
        organization_id=sample_organization.id,
        status='Open',
        importance='Medium',
        date_reported=date.today()
    )
    db.session.add(issue)
    db.session.commit()
    
    # Try to delete the organisation
    response = auth_client.delete(f'/organizations/{sample_organization.id}')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['success'] == False
    assert 'used by' in data['error']
    assert data['issue_count'] == 1

def test_manage_organisations_page(auth_client, sample_organization):
    """Test the manage organisations page loads"""
    response = auth_client.get('/manage-organisations')
    assert response.status_code == 200
    assert b'Manage Organisations' in response.data
    assert sample_organization.name.encode() in response.data

def test_delete_issue(auth_client, sample_organization):
    """Test deleting an issue"""
    # Create a test issue
    issue = Issue(
        title='Test Issue to Delete',
        description='This will be deleted',
        reporter='Test User',
        organization_id=sample_organization.id,
        status='Open',
        importance='Medium',
        date_reported=date.today()
    )
    db.session.add(issue)
    db.session.commit()
    issue_id = issue.id
    
    # Verify issue exists
    assert Issue.query.get(issue_id) is not None
    
    # Delete the issue
    response = auth_client.delete(f'/issues/{issue_id}')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert data['success'] == True
    
    # Verify issue is deleted
    assert Issue.query.get(issue_id) is None
