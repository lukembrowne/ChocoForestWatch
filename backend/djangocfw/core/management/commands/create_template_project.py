from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Project

class Command(BaseCommand):
    help = 'Creates or updates the template project for the first superuser'

    def handle(self, *args, **options):
        # Get first superuser
        superuser = User.objects.filter(is_superuser=True).first()
        if not superuser:
            self.stdout.write(self.style.ERROR('No superuser found. Please create a superuser first.'))
            return

        # Check if a template project already exists
        if Project.objects.filter(is_template=True).exists():
            self.stdout.write(self.style.WARNING('Template project already exists. No action taken.'))
            return

        # Create basic template project
        template = Project.objects.create(
            name="Example Project",
            description="This is an example project to help you get started.",
            is_template=True,
            owner=superuser,
            classes=[
                {"name": "Forest", "color": "#00FF00"},
                {"name": "Non-Forest", "color": "#FFFF00"},
                {"name": "Cloud", "color": "#FFFFFF"},
                {"name": "Shadow", "color": "#808080"},
                {"name": "Water", "color": "#0000FF"}
            ]
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created template project for superuser {superuser.username}. '
                f'You can now edit this project through the web interface.'
            )
        ) 