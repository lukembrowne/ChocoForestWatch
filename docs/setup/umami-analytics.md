# Umami Analytics Setup Guide for ChocoForestWatch

## Overview
This guide provides step-by-step instructions for setting up Umami analytics in your ChocoForestWatch application deployed on DigitalOcean.

## Prerequisites
- ChocoForestWatch application running on DigitalOcean
- Docker and Docker Compose installed
- Access to your server's environment variables
- PostgreSQL database already configured (which is used by your main application)

## Required Environment Variables

Add the following environment variables to your `.env` file on the server:

```bash
# Umami Analytics Configuration
UMAMI_APP_SECRET=your-super-secret-key-here-32-chars-min
VITE_UMAMI_WEBSITE_ID=your-website-id-from-umami-dashboard
VITE_UMAMI_URL=http://localhost:3001  # Development: http://localhost:3001, Production: https://your-domain.com/umami

# Umami Database Configuration (Production)
UMAMI_DB_NAME=umami
UMAMI_DB_USER=umami_user
UMAMI_DB_PASSWORD=your-secure-database-password-here
```

### Generating UMAMI_APP_SECRET
Generate a secure secret key (minimum 32 characters):
```bash
openssl rand -hex 32
```

## Setup Steps

### 1. Database Setup
The Umami service will automatically create a separate `umami` database within your existing PostgreSQL instance. No manual database setup is required.

### 2. Deploy the Updated Configuration
After adding the environment variables to your server's `.env` file:

```bash
# On your DigitalOcean server
cd /root/opt/ChocoForestWatch
git pull
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d --build
```

### 3. Access Umami Dashboard
Once deployed, access the Umami dashboard at:
```
https://your-domain.com/umami/
```

### 4. Initial Umami Setup
1. **First Login**: Use default credentials:
   - Username: `admin`
   - Password: `umami`

2. **Change Default Password**: Immediately change the default password for security.

3. **Add Website**: 
   - Click "Add website"
   - Enter your domain name (e.g., `your-domain.com`)
   - Copy the generated Website ID
   - Add this ID to your `.env` file as `VITE_UMAMI_WEBSITE_ID`

4. **Update Environment and Redeploy**:
   ```bash
   # Add VITE_UMAMI_WEBSITE_ID to .env file
   echo "VITE_UMAMI_WEBSITE_ID=your-copied-website-id" >> .env
   
   # Rebuild frontend with new website ID
   docker compose -f docker-compose.prod.yml down
   docker compose -f docker-compose.prod.yml up -d --build
   ```

## Service Architecture

### Docker Services
- **umami**: Runs on port 3001 internally, accessible via nginx proxy at `/umami`
- **Database**: Uses existing PostgreSQL with a separate `umami` database
- **Frontend**: Automatically includes tracking script when `VITE_UMAMI_WEBSITE_ID` is set

### Network Configuration
- Umami service connected to existing `app-network`
- Nginx proxy routes `/umami/*` requests to Umami service
- Frontend tracking script loads from `/umami/script.js`

## Analytics Features

### Automatic Tracking
- Page views
- Unique visitors
- User sessions
- Referrer information
- Browser and device data

### Privacy Features
- No cookies required
- GDPR compliant
- No personal data collection
- IP address anonymization
- Self-hosted (data stays on your server)

## Troubleshooting

### Common Issues

#### 1. Umami Service Won't Start
**Problem**: Container exits immediately
**Solution**: Check environment variables and database connection
```bash
docker compose -f docker-compose.prod.yml logs umami
```

#### 2. Tracking Script Not Loading
**Problem**: Browser console shows 404 for `/umami/script.js`
**Solution**: Verify nginx configuration and Umami service status
```bash
# Check if Umami service is running
docker compose -f docker-compose.prod.yml ps umami

# Check nginx logs
docker compose -f docker-compose.prod.yml logs frontend
```

#### 3. Database Connection Issues
**Problem**: Umami can't connect to PostgreSQL
**Solution**: Verify PostgreSQL is healthy and accessible
```bash
# Check database service
docker compose -f docker-compose.prod.yml logs db

# Check if umami database exists
docker compose -f docker-compose.prod.yml exec db psql -U $POSTGRES_USER -d $POSTGRES_DB -c "\\l"
```

### Service Status Commands
```bash
# Check all services status
docker compose -f docker-compose.prod.yml ps

# View Umami logs
docker compose -f docker-compose.prod.yml logs -f umami

# Restart Umami service only
docker compose -f docker-compose.prod.yml restart umami
```

## Security Considerations

### Access Control
- Umami dashboard accessible only through your domain
- Change default admin password immediately
- Consider implementing additional authentication layers if needed

### Data Privacy
- Analytics data stored locally on your server
- No data shared with third parties
- Compliant with privacy regulations (GDPR, CCPA)

### Database Security
- Umami uses existing PostgreSQL security settings
- Database connections encrypted within Docker network
- Environment variables protect sensitive configuration

## Maintenance

### Regular Tasks
1. **Monitor disk usage**: Analytics data accumulates over time
2. **Update Umami**: Periodically update to latest version
3. **Database maintenance**: Regular PostgreSQL maintenance applies

### Backup Considerations
- Umami data stored in PostgreSQL - included in existing database backups
- Export analytics data periodically from Umami dashboard if needed

### Updates
To update Umami to the latest version:
```bash
docker compose -f docker-compose.prod.yml pull umami
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d
```

## Support Resources

### Documentation
- [Umami Official Documentation](https://umami.is/docs)
- [Umami GitHub Repository](https://github.com/umami-software/umami)

### Configuration Files Modified
- `docker-compose.yml` - Development environment
- `docker-compose.prod.yml` - Production environment  
- `.github/workflows/deploy.yml` - Deployment workflow
- `frontend/index.html` - Tracking script integration
- `frontend/nginx.conf` - Proxy configuration

## Environment Variables Reference

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `UMAMI_APP_SECRET` | Yes | Secret key for Umami app | `a1b2c3d4e5f6...` (32+ chars) |
| `VITE_UMAMI_WEBSITE_ID` | Yes | Website ID from Umami dashboard | `12345678-1234-1234-1234-123456789abc` |
| `VITE_UMAMI_URL` | Yes | URL to Umami instance | `http://localhost:3001` (dev), `https://domain.com/umami` (prod) |

## Development vs Production

### Development (docker-compose.yml)
- Umami available at `http://localhost:3001/`
- Direct port access for debugging
- Environment variables loaded from `.env`

### Production (docker-compose.prod.yml)  
- Umami accessible only through nginx proxy
- Build-time environment variable injection
- Production security settings

This setup provides a complete, privacy-focused analytics solution that integrates seamlessly with your existing ChocoForestWatch infrastructure.