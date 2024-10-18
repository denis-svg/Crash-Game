import unittest
from app import app, db

class AuthServiceTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'  # Use in-memory database for tests
        app.config['JWT_SECRET_KEY'] = 'test-secret'
        cls.client = app.test_client()

        with app.app_context():  # Create application context
            db.create_all()  # Create the database schema for tests

    @classmethod
    def tearDownClass(cls):
        with app.app_context():
            db.drop_all()  # Clean up after tests

    def test_register(self):
        response = self.client.post('/user/v1/auth/register', json={'username': 'newuser', 'password': 'newpass'})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json['message'], 'User created')

        response = self.client.post('/user/v1/auth/register', json={'username': 'newuser', 'password': 'newpass'})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json['error'], 'User already exists')

    def test_login(self):
        self.client.post('/user/v1/auth/register', json={'username': 'testuser', 'password': 'testpass'})
        response = self.client.post('/user/v1/auth/login', json={'username': 'testuser', 'password': 'testpass'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('access_token', response.json)

        response = self.client.post('/user/v1/auth/login', json={'username': 'wronguser', 'password': 'wrongpass'})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json['error'], 'Invalid credentials')

    def test_get_balance(self):
        self.client.post('/user/v1/auth/register', json={'username': 'balanceuser', 'password': 'pass'})
        
        # Login to get the auth token
        response = self.client.post('/user/v1/auth/login', json={'username': 'balanceuser', 'password': 'pass'})
        auth_token = response.json['access_token']
        
        response = self.client.get('/user/v1/balance', headers={'Authorization': f'Bearer {auth_token}'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('balance', response.json)

    def test_set_balance(self):
        self.client.post('/user/v1/auth/register', json={'username': 'balanceuser', 'password': 'pass'})

        # Login to get the auth token
        response = self.client.post('/user/v1/auth/login', json={'username': 'balanceuser', 'password': 'pass'})
        auth_token = response.json['access_token']

        # Set the initial balance
        self.client.post('/user/v1/balance', json={'balance': 100}, headers={'Authorization': f'Bearer {auth_token}'})

        # Update the balance
        response = self.client.put('/user/v1/balance', json={'ammount': 50}, headers={'Authorization': f'Bearer {auth_token}'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['message'], 'Balance updated')

        # Check the balance
        response = self.client.get('/user/v1/balance', headers={'Authorization': f'Bearer {auth_token}'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['balance'], 150)  # Check if balance updated correctly

    def test_validate_user(self):
        self.client.post('/user/v1/auth/register', json={'username': 'validuser', 'password': 'pass'})

        # Login to get the auth token
        response = self.client.post('/user/v1/auth/login', json={'username': 'validuser', 'password': 'pass'})
        auth_token = response.json['access_token']

        response = self.client.get('/user/v1/auth/validate', headers={'Authorization': f'Bearer {auth_token}'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['status'], 'valid')
        self.assertEqual(response.json['username'], 'validuser')

    def test_status(self):
        response = self.client.get('/user/v1/status')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['status'], 'Auth Service Running')

if __name__ == '__main__':
    unittest.main()
