from django.test import TestCase
from rest_framework.test import APIClient
from core.models import Project, TrainingPolygonSet

class TrainingPolygonSetTests(TestCase):
    def setUp(self):
        # Create test client
        self.client = APIClient()
        
        # Create test project
        self.project = Project.objects.create(
            name="Test Project",
            description="Test Description",
            classes=[{"name": "Forest"}, {"name": "Non-Forest"}]
        )
        
        # Create test training set
        self.training_set = TrainingPolygonSet.objects.create(
            project=self.project,
            name="Test Training Set",
            basemap_date="2023-01",
            polygons={"type": "FeatureCollection", "features": []},
            feature_count=0
        )

    def test_get_training_polygons(self):
        """Test retrieving training polygons with filters"""
        # Test getting training polygons for specific project and set
        response = self.client.get(
            '/api/training-sets/',
            {'project_id': self.project.id, 'id': self.training_set.id}
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]['name'], "Test Training Set")

    def test_get_training_polygons_invalid_id(self):
        """Test retrieving training polygons with invalid ID"""
        response = self.client.get(
            '/api/training-sets/',
            {'project_id': 999, 'id': 999}
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)
