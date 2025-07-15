# ChocoForestWatch Documentation

This directory contains comprehensive documentation for the ChocoForestWatch project, organized by topic and audience.

## 📚 Documentation Overview

### 🚀 Setup & Installation
- **[Umami Analytics Setup](setup/umami-analytics.md)** - Complete guide for integrating Umami analytics
- **[Development Environment](setup/development.md)** - Setting up local development environment
- **[Production Deployment](setup/deployment.md)** - DigitalOcean production deployment guide

### 🏗️ Architecture & Technical Design
- **[Services Overview](architecture/services.md)** - Docker services and their roles
- **[Database Design](architecture/database.md)** - PostgreSQL schema and relationships
- **[API Documentation](architecture/api.md)** - Django REST API endpoints and usage

### 🔄 Development Workflows
- **[Testing Procedures](workflows/testing.md)** - Running tests and quality assurance
- **[CI/CD Pipeline](workflows/ci-cd.md)** - GitHub Actions deployment workflow
- **[Troubleshooting](workflows/troubleshooting.md)** - Common issues and solutions

### 👥 User Guides
- **[Model Training](user-guides/training-models.md)** - ML model training and management
- **[Analysis Features](user-guides/analysis-features.md)** - Using the analysis panel and features

## 🔍 Quick Links

### For Developers
- [CLAUDE.md](../CLAUDE.md) - Instructions for Claude Code assistant
- [Main README](../README.md) - Project overview and quick start
- [Development Setup](setup/development.md)

### For System Administrators
- [Production Deployment](setup/deployment.md)
- [Umami Analytics](setup/umami-analytics.md)
- [Troubleshooting Guide](workflows/troubleshooting.md)

### For Users
- [User Guides](user-guides/) - End-user documentation
- [API Documentation](architecture/api.md)

## 📝 Contributing to Documentation

When adding new documentation:

1. **Choose the right location**:
   - `setup/` - Installation and configuration guides
   - `architecture/` - Technical design and system documentation
   - `workflows/` - Development processes and procedures
   - `user-guides/` - End-user facing documentation

2. **Follow naming conventions**:
   - Use lowercase with hyphens: `my-feature.md`
   - Be descriptive but concise
   - Include purpose in filename

3. **Update this index** when adding new documents

4. **Cross-reference related documents** to improve navigation

## 📋 Documentation Standards

- **Markdown format** (.md files)
- **Clear headings** and table of contents for longer documents
- **Code examples** with proper syntax highlighting
- **Step-by-step instructions** for procedures
- **Screenshots** where helpful (store in `docs/images/`)
- **Version information** when relevant

