from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Project

@receiver(post_save, sender=User)
def create_example_project(sender, instance, created, **kwargs):
    """Creates an example project for new users"""
    if created:  # Only for newly created users
        try:
            Project.create_from_template(instance)
        except Exception as e:
            print(f"Failed to create example project for user {instance.username}: {e}") 