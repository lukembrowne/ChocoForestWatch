# Choco Forest Watch

A full-stack application for deforestation monitoring, built with Quasar (Vue.js) frontend and a robust backend system.

## Project Overview

Choco Forest Watch is a comprehensive forest monitoring system that helps track and manage forest resources. The application consists of:

- Frontend: Quasar (Vue.js) application
- Backend: Django API
- Database: PostgreSQL with PostGIS
- Redis: For caching and background tasks
- Infrastructure: Docker containers deployed on DigitalOcean

## Development Setup

### Prerequisites

- Node.js (v16 or higher)
- Yarn or npm
- Docker and Docker Compose
- Git

### Local Deployment with Docker

1. Clone the repository:
   ```bash
   git clone git@github.com:lukembrowne/ChocoForestWatch.git
   cd ChocoForestWatch
   ```

2. Create a `.env.prod` file in the root directory with the following variables:
   ```bash
   # Database
   POSTGRES_DB=chocoforest
   POSTGRES_USER=your_user
   POSTGRES_PASSWORD=your_password

   # Frontend
   VITE_API_URL=http://localhost:8000
   VUE_APP_PLANET_API_KEY=your_planet_api_key
   VITE_SENTRY_DSN=your_sentry_dsn

   # Add other environment variables as needed
   ```

3. Create required directories for data persistence:
   ```bash
   mkdir -p data/{planet_quads,predictions,models} media logs
   ```

4. Start the application using Docker Compose:
   ```bash
   docker compose -f docker-compose.prod.yml up --build
   ```

   This will start:
   - PostgreSQL database with PostGIS extension (port 5432)
   - Redis server (port 6379)
   - Django backend (port 8000)
   - Quasar frontend (port 9000)

5. Access the application:
   - Frontend: http://localhost:9000
   - Backend API: http://localhost:8000

### Development Workflow

1. **Create a GitHub Issue**
   - Go to the GitHub repository issues section
   - Create a new issue describing the feature or bug fix
   - Use appropriate labels (e.g., `enhancement`, `bug`, `documentation`)
   - Assign the issue to yourself or team member

2. **Branch Creation**
   - Create a new branch from `dev` using the issue number:
     ```bash
     git checkout dev
     git pull origin dev
     git checkout -b issue-123/feature-description
     ```
   - The branch name should reference the issue number for traceability
   - Branch naming conventions:
     - `issue-123/feature-name` for new features
     - `issue-123/bugfix-name` for bug fixes
     - `issue-123/hotfix-name` for urgent production fixes

3. **Development**
   - Update documentation as needed
   - Commit your changes with conventional commits:
     ```bash
     git commit -m "feat: add new feature (#123)"
     # or
     git commit -m "fix: resolve issue with X (#123)"
     ```
   - Reference the issue number in commit messages

4. **Pull Request**
   - Push your branch to GitHub:
     ```bash
     git push origin issue-123/feature-description
     ```
   - Create a Pull Request (PR) from your branch to `dev`
   - Link the PR to the related issue using GitHub's linking syntax
   - Fill in the PR template with:
     - Description of changes
     - Testing performed
     - Screenshots (if applicable)
     - Any additional notes

5. **Code Review**
   - Request review from team members
   - Address review comments
   - Ensure all CI checks pass
   - Update the PR as needed

6. **Merge and Release**
   - Once approved, squash and merge your PR into `dev`
   - When ready for release:
     - Create a PR from `dev` to `main`
     - After review and approval, merge to `main`
     - Tag the release with version number
     - The merge to `main` will trigger the deployment workflow

### Branch Strategy

- `main`: Production-ready code
  - Should never receive direct commits
  - Only receives changes through merges from `dev`
  - Protected branch with required reviews
- `dev`: Development branch for integrating features
  - Main integration branch for all features
  - Protected branch with required reviews
  - Should be kept up to date with `main` through regular merges
- `issue-*/*`: Feature/fix branches for specific issues
- `release/*`: Release preparation branches (if needed)
- `hotfix/*`: Urgent production fixes
  - Branch from `main`
  - Must be merged back to both `main` and `dev`

### Branch Synchronization

1. **Regular Dev-Main Sync**
   ```bash
   # Keep dev up to date with main
   git checkout dev
   git pull origin dev
   git merge main
   git push origin dev
   ```

2. **Hotfix Process**
   ```bash
   # Create hotfix branch from main
   git checkout main
   git pull origin main
   git checkout -b hotfix/urgent-fix

   # After fixing, merge to both main and dev
   git checkout main
   git merge hotfix/urgent-fix
   git push origin main

   git checkout dev
   git merge hotfix/urgent-fix
   git push origin dev
   ```

3. **Release Process**
   ```bash
   # Create release branch from dev
   git checkout dev
   git pull origin dev
   git checkout -b release/v1.0.0

   # After testing, merge to main and back to dev
   git checkout main
   git merge release/v1.0.0
   git tag -a v1.0.0 -m "Release v1.0.0"
   git push origin main --tags

   git checkout dev
   git merge release/v1.0.0
   git push origin dev
   ```

### Important Notes

1. Never make direct commits to `main` or `dev`
2. Always create feature branches from `dev`
3. Keep `dev` synchronized with `main` regularly
4. Use hotfix branches for urgent production fixes
5. Tag all releases in `main`
6. Ensure CI passes before merging to any protected branch

### Deployment Process

The application is automatically deployed when changes are pushed to the `main` branch. The deployment process:

1. GitHub Actions workflow is triggered on push to `main`
2. The workflow:
   - Connects to the DigitalOcean droplet
   - Pulls the latest code
   - Builds Docker images using `docker-compose.prod.yml`
   - Restarts containers with new images
   - Maintains data persistence through Docker volumes

## Project Structure

```
ChocoForestWatch/
├── frontend/           # Quasar frontend application
├── backend/           # Django backend
├── .github/           # GitHub Actions workflows
├── data/             # Persistent data storage
│   ├── planet_quads/ # Planet imagery data
│   ├── predictions/  # Model predictions
│   └── models/       # ML models
├── media/            # User-uploaded media
├── logs/             # Application logs
└── docker-compose.prod.yml # Production Docker configuration
```

## Data Processing Workflows

### NICFI Imagery Processing (one time)

The system includes automated workflows for processing NICFI (Norway's International Climate and Forests Initiative) satellite imagery:

1. **Data Transfer**
   - Use `migrate_nicfi_data.sh` to transfer NICFI imagery from Google Drive to DigitalOcean Spaces
   - This script handles the  transfer of large imagery datasets

2. **STAC Integration**
   - Process transferred imagery using `build_nicfi_STAC.py`
   - Builds SpatioTemporal Asset Catalog (STAC) metadata
   - Inserts STAC records into PGSTAC database
   - Enables seamless integration with TiTiler for dynamic tile serving
   - Provides standardized access to imagery through STAC API endpoints


### Establish training set

   - Make new project if needed
   - Use 'training module' to draw training polygons
   - Uses stratified random sampling across quads
   - aiming for ~50 features per class per month

### Fit model
   - Use `run_train_predict_pipeline.py` to start an overall modeling run and fit separate moodels for each month
      - will call `train_and_predict_by_month.py` for each month
      - will upload prediction COGs to DO Spaces and add collection to PGStac

### Create composite image
   - run `create_composite 2025_05_19.py` to create an annual compose of Forest / Non-forest based on monthly data

### Test against benchmarks
   - run `test_benchmarks 2025_05_19.py` to test accuracy against training data / comparea to other forest cover datasets


## Contributing

1. Follow the development workflow outlined above
2. Ensure all tests pass before submitting PRs
3. Follow the existing code style and conventions
4. Update documentation as needed
5. Create issues for any bugs or feature requests

## License

....

## Support

....