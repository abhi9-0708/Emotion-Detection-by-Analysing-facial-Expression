import unittest
import sqlite3
import cv2
import numpy as np
import io
from flask import Flask

# Import internal functions and variables from app.py
from app import (
    validate_email,
    validate_password,
    get_db_connection,
    init_db,
    face_cascade,
    img_size,
    predict_emotion_from_image,
    recommend_media,
    app
)

def detect_face(img):
    """ Detects a face in the image and returns a bounding box. """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    return faces

class WhiteBoxTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()  # Initialize Flask test client

    def test_validate_email(self):
        self.assertTrue(validate_email("user@example.com"))
        self.assertFalse(validate_email("userexample.com"))
        self.assertFalse(validate_email("user@.com"))

    def test_validate_password(self):
        self.assertTrue(validate_password("12345678"))
        self.assertFalse(validate_password("1234"))
        
    def test_db_connection_and_init(self):
        init_db()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
        table = cursor.fetchone()
        self.assertIsNotNone(table, "Users table should exist after initialization.")
        conn.close()
        
    def test_detect_face_no_face(self):
        dummy_img = np.zeros((img_size, img_size, 3), dtype=np.uint8)
        faces = detect_face(dummy_img)
        self.assertEqual(len(faces), 0, "No face should be detected in a blank image.")
    
    def test_predict_emotion_no_face(self):
        dummy_img = np.zeros((img_size, img_size, 3), dtype=np.uint8)
        annotated_img, emotion_id = predict_emotion_from_image(dummy_img)
        self.assertIsNone(emotion_id, "No face should return None emotion.")
    
    def test_recommend_media(self):
        for emotion_id in range(7):
            recommendations = recommend_media(emotion_id)
            self.assertIn("music", recommendations, "Music recommendations should be present.")
            self.assertIn("podcasts", recommendations, "Podcast recommendations should be present.")
    
    def test_upload_image_no_face(self):
        dummy_img = np.zeros((img_size, img_size, 3), dtype=np.uint8)
        data = {'file': (io.BytesIO(dummy_img.tobytes()), 'test.jpg')}
        response = self.client.post('/upload_image', data=data, content_type='multipart/form-data')
        self.assertIn(response.status_code, [200, 302, 400], "Response should be 200, 302, or 400 if no face is detected.")
    
    def test_live_webcam_no_face(self):
        dummy_frame = np.zeros((img_size, img_size, 3), dtype=np.uint8)
        data = {'frame': (io.BytesIO(dummy_frame.tobytes()), 'frame.jpg')}
        response = self.client.post('/live_webcam', data=data, content_type='multipart/form-data')
        self.assertIn(response.status_code, [200, 400], "Response should be 200 or 400 if no face is detected.")
    
    def test_feedback_submission(self):
        test_feedback = "This is a test feedback."
        data = {'feedback': test_feedback}
        response = self.client.post('/feedback', data=data, content_type='application/x-www-form-urlencoded')
        self.assertIn(response.status_code, [200, 302], "Feedback submission should return 200 or a redirect (302).")

if __name__ == '__main__':
    unittest.main()
