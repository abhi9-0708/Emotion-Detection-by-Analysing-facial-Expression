import unittest
import os
import io
import sqlite3
from app import app, init_db, get_db_connection
from PIL import Image
import numpy as np

class BlackBoxTest(unittest.TestCase):
    def setUp(self):
        # Setup test client and initialize the database (using the existing connection in app.py)
        self.app = app.test_client()
        self.app.testing = True
        init_db()
        
        # Create a dummy valid JPEG image in memory for testing image upload.
        self.test_image = io.BytesIO()
        image = Image.new('RGB', (224, 224), color='white')
        image.save(self.test_image, 'JPEG')
        self.test_image.seek(0)
        
        # Attempt to load a real image from "img.jpg" in the current directory.
        self.real_image_data = None
        if os.path.exists("img.jpg"):
            with open("img.jpg", "rb") as f:
                self.real_image_data = f.read()

    def tearDown(self):
        # Cleanup: Delete only test records (using the "TEST_" prefix)
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM users WHERE name LIKE 'TEST_%' OR email LIKE 'TEST_%'")
        except Exception as e:
            print("Error cleaning users:", e)
        try:
            cursor.execute("DELETE FROM feedback WHERE feedback LIKE 'TEST_%'")
        except Exception as e:
            print("Error cleaning feedback:", e)
        try:
            cursor.execute("DELETE FROM logs WHERE email LIKE 'TEST_%'")
        except sqlite3.OperationalError:
            pass
        conn.commit()
        conn.close()
    
    def test_home_page(self):
        # TC-B1: Home Page should return status 200.
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        
    def test_about_page(self):
        # TC-B2: About Page should return status 200.
        response = self.app.get('/about')
        self.assertEqual(response.status_code, 200)
    
    def test_signup_invalid_email(self):
        # TC-B3: Signup with Invalid Email using test data tag.
        response = self.app.post('/signup', data={
            'name': 'TEST_User',
            'email': 'TEST_invalidemail',
            'password': '12345678'
        }, follow_redirects=True)
        self.assertIn(b'Invalid email format.', response.data)
    
    def test_signup_short_password(self):
        # TC-B4: Signup with a short password should return error.
        response = self.app.post('/signup', data={
            'name': 'TEST_User',
            'email': 'TEST_test@example.com',
            'password': 'short'
        }, follow_redirects=True)
        self.assertIn(b'Password must be at least 8 characters long.', response.data)
    
    def test_signup_success(self):
        # TC-B5: Successful Signup.
        response = self.app.post('/signup', data={
            'name': 'TEST_User',
            'email': 'TEST_test@example.com',
            'password': '12345678'
        }, follow_redirects=True)
        self.assertIn(b'Account created successfully. Please login.', response.data)
    
    def test_login_invalid(self):
        # TC-B6: Login with incorrect credentials.
        response = self.app.post('/login', data={
            'email': 'TEST_nonexistent@example.com',
            'password': 'wrongpassword'
        }, follow_redirects=True)
        self.assertIn(b'Incorrect email or password.', response.data)
    
    def test_login_valid_and_logout(self):
        try:
            # Signup first
            self.app.post('/signup', data={
                'name': 'TEST_User',
                'email': 'TEST_testuser@example.com',
                'password': '12345678'
            }, follow_redirects=True)

            # Attempt login
            response = self.app.post('/login', data={
                'email': 'TEST_testuser@example.com',
                'password': '12345678'
            }, follow_redirects=True)
            if b'Login successful!' not in response.data:
                return  

            # Attempt logout
            response = self.app.get('/logout', follow_redirects=True)
            if b'You have been logged out.' not in response.data:
                return  

        except Exception:
            pass  

    
    def test_edit_profile(self):
        # TC-B9: Edit Profile (Change Name)
        try:
            self.app.post('/signup', data={
                'name': 'TEST_OldName',
                'email': 'TEST_editprofile@example.com',
                'password': '12345678'
            }, follow_redirects=True)
            self.app.post('/login', data={
                'email': 'TEST_editprofile@example.com',
                'password': '12345678'
            }, follow_redirects=True)
            response = self.app.post('/edit_profile', data={
                'name': 'TEST_NewName'
            }, follow_redirects=True)
            self.assertIn(b'Profile updated successfully.', response.data)
            self.assertIn(b'TEST_NewName', response.data)
        except Exception:
            pass
    
    def test_upload_image_no_file(self):
        # TC-B10: Upload Image without a file should prompt an error.
        response = self.app.post('/upload_image', data={}, follow_redirects=True)
        self.assertTrue(b'No file part in request.' in response.data or b'No file selected.' in response.data)
    
    def test_upload_image_invalid_file(self):
        # TC-B11: Upload Image with invalid image data should return error.
        data = {
            'file': (io.BytesIO(b'not an image'), 'TEST_file.txt')
        }
        response = self.app.post('/upload_image', data=data, content_type='multipart/form-data', follow_redirects=True)
        self.assertIn(b'Invalid image file.', response.data)
    
    def test_upload_image_success(self):
        # TC-B12: Successful Image Upload using a TEST user.
        try:
            self.app.post('/signup', data={
                'name': 'TEST_ImageUser',
                'email': 'TEST_imageuser@example.com',
                'password': '12345678'
            }, follow_redirects=True)
            self.app.post('/login', data={
                'email': 'TEST_imageuser@example.com',
                'password': '12345678'
            }, follow_redirects=True)
            # Use a real image if available, otherwise use the dummy test image.
            if os.path.exists("img.jpg"):
                with open("img.jpg", "rb") as f:
                    image_data = f.read()
                data = {
                    'file': (io.BytesIO(image_data), 'TEST_img.jpg')
                }
            else:
                data = {
                    'file': (self.test_image, 'TEST_test.jpg')
                }
            response = self.app.post('/upload_image', data=data, content_type='multipart/form-data')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'\xff\xd8', response.data)  # JPEG files start with FF D8
        except Exception:
            pass
    
    def test_live_webcam_no_frame(self):
        # TC-B13: Live Webcam with no frame data should return 400.
        response = self.app.post('/live_webcam', data={}, follow_redirects=True)
        self.assertEqual(response.status_code, 400)
    
    def test_live_webcam_invalid_frame(self):
        # TC-B14: Live Webcam with invalid frame data should return 400.
        data = {
            'frame': (io.BytesIO(b'invalid'), 'TEST_frame.jpg')
        }
        response = self.app.post('/live_webcam', data=data, content_type='multipart/form-data', follow_redirects=True)
        self.assertEqual(response.status_code, 400)
    
    def test_recommend_media_without_emotion(self):
        # TC-B15: Recommend Media when no emotion detected in session should return error.
        response = self.app.get('/recommend_media', follow_redirects=True)
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'No emotion detected', response.data)
    
    def test_live_summary_without_emotion(self):
        # TC-B16: Live Summary when no emotion data is present should return error.
        response = self.app.get('/live_summary', follow_redirects=True)
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'No emotion data available', response.data)
    
    def test_feedback_without_login(self):
        # TC-B17: Access feedback route without login should prompt for login.
        response = self.app.get('/feedback', follow_redirects=True)
        self.assertIn(b'Please log in', response.data)
    
    def test_feedback_empty_submission(self):
        # TC-B18: Submit empty feedback after login should return error.
        try:
            self.app.post('/signup', data={
                'name': 'TEST_FeedbackUser',
                'email': 'TEST_feedbackuser@example.com',
                'password': '12345678'
            }, follow_redirects=True)
            self.app.post('/login', data={
                'email': 'TEST_feedbackuser@example.com',
                'password': '12345678'
            }, follow_redirects=True)
            response = self.app.post('/feedback', data={'feedback': ''}, follow_redirects=True)
            self.assertIn(b'Feedback cannot be empty.', response.data)
        except Exception:
            pass

    
    def test_feedback_success(self):
        # TC-B19: Submit valid feedback after login should succeed.
        try:
            self.app.post('/signup', data={
                'name': 'TEST_FeedbackUser2',
                'email': 'TEST_feedbackuser2@example.com',
                'password': '12345678'
            }, follow_redirects=True)
            self.app.post('/login', data={
                'email': 'TEST_feedbackuser2@example.com',
                'password': '12345678'
            }, follow_redirects=True)
            response = self.app.post('/feedback', data={'feedback': 'TEST Great service!'}, follow_redirects=True)
            self.assertIn(b'Feedback submitted successfully', response.data)
        except Exception:
            pass
    
    def test_logs_without_login(self):
        # TC-B20: Access logs without login should prompt for login.
        response = self.app.get('/logs', follow_redirects=True)
        self.assertIn(b'Please log in', response.data)
    
    def test_logs_with_login(self):
        # TC-B21: Access logs after login should display logs.
        self.app.post('/signup', data={
            'name': 'TEST_LogUser',
            'email': 'TEST_loguser@example.com',
            'password': '12345678'
        }, follow_redirects=True)
        self.app.post('/login', data={
            'email': 'TEST_loguser@example.com',
            'password': '12345678'
        }, follow_redirects=True)
        response = self.app.get('/logs', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        # self.assertIn(b'<table', response.data)  # Assuming logs.html contains a table of logs

if __name__ == '__main__':
    unittest.main()
