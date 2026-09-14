# Shiva's Salon Queue Management System

Open-source, production-oriented salon queue and callback system built with FastAPI, PostgreSQL, Docker, and a lightweight customer/owner web interface.

## What it does

### Customer
- View active salon services and gallery
- Join the queue without creating an account
- Receive a daily queue token
- Check status using the visible token number or a private status link
- Receive an automatic near-turn SMS when enabled

### Owner
- Secure owner login
- View waiting and serving customers
- Call the next customer
- Complete or cancel a queue entry
- Manage services
- Manage gallery items

## Architecture

- **Backend:** FastAPI + SQLAlchemy + PostgreSQL
- **Frontend:** HTML/CSS/JavaScript served by Nginx
- **Deployment:** Docker Compose
- **Authentication:** JWT for owner access and signed private queue-status tokens
- **Notifications:** Mock SMS for local development or MSG91 for real SMS

## Run locally

Requirements: Docker Desktop with Compose.

1. Create a `.env` file for the Compose project. Never commit real passwords, JWT secrets, or SMS credentials.
2. Set at least:

```env
POSTGRES_PASSWORD=replace-with-a-strong-password
SECRET_KEY=replace-with-a-long-random-secret
OWNER_USERNAME=owner
OWNER_PASSWORD=replace-with-a-strong-owner-password
```

3. Start the application:

```powershell
docker compose up -d --build
```

4. Open the customer site:

`http://localhost:8081`

5. Open the owner dashboard:

`http://localhost:8081/admin.html`

## Automatic SMS

The application checks customers near the front of the waiting queue whenever queue state changes. By default, SMS is set to `mock`, so local development logs the SMS instead of sending a real message.

For real Indian SMS, configure MSG91 in the deployment environment:

```env
SMS_PROVIDER=msg91
SMS_NEAR_TURN_THRESHOLD=2
MSG91_AUTHKEY=your-msg91-auth-key
MSG91_FLOW_ID=your-approved-flow-id
MSG91_SENDER_ID=your-approved-sender-id
```

The configured MSG91 flow must be approved for the SMS template used by the application. Do not commit these credentials to GitHub.

The near-turn notification is sent once per queue entry and is recorded in the database to prevent duplicate notifications.

## Open-source security notes

- Keep `.env` out of Git.
- Use a strong random `SECRET_KEY` in production.
- Use a strong PostgreSQL and owner password.
- Serve the production site over HTTPS.
- Restrict CORS to the real frontend domain.
- Do not expose PostgreSQL publicly.
- Replace the development/mock SMS provider with MSG91 only after its template and sender configuration are approved.

## License

MIT License. See `LICENSE`.
