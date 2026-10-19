# FastAPI JWT Authentication Microservice

A REST API project featuring user registration, password hashing, JWT bearer tokens, SQLite persistence, protected CRUD routes, Pydantic validation, and Swagger/OpenAPI docs.

## 1. Requirements
- Python 3.10 or newer
- VS Code or another editor

## 2. Create and activate a virtual environment

Windows PowerShell:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use Command Prompt:
```bat
.venv\Scripts\activate.bat
```

## 3. Install dependencies
```bash
python -m pip install -r requirements.txt
```

## 4. Run the server
```bash
uvicorn main:app --reload
```

Open:
- API home: http://127.0.0.1:8000/
- Swagger UI: http://127.0.0.1:8000/docs
- OpenAPI JSON: http://127.0.0.1:8000/openapi.json

## 5. Try it in Swagger
1. `POST /auth/register`: create a user. Use a username such as `student1`, email `student1@example.com`, and a password of at least 8 characters.
2. `POST /auth/login`: enter the username and password in the form fields. Copy `access_token` from the response.
3. Click **Authorize** near the top of Swagger and paste the token (or use the OAuth2 form).
4. Use `POST /items` to create a private item.
5. Use `GET /items`, `GET /items/{item_id}`, `PUT /items/{item_id}`, and `DELETE /items/{item_id}` to test CRUD operations.

## API routes

| Method | Route | Purpose | Authentication |
|---|---|---|---|
| GET | `/` | Service information | No |
| GET | `/health` | Health check | No |
| POST | `/auth/register` | Register user | No |
| POST | `/auth/login` | Login and receive JWT | No |
| GET | `/users/me` | Current user's profile | Yes |
| POST | `/items` | Create an item | Yes |
| GET | `/items` | List your items | Yes |
| GET | `/items/{item_id}` | Read your item | Yes |
| PUT | `/items/{item_id}` | Update your item | Yes |
| DELETE | `/items/{item_id}` | Delete your item | Yes |

## Run tests
```bash
pytest -v
```

## Security notes
- The default secret key is for local development only. Before deployment, set a long random `JWT_SECRET_KEY` environment variable.
- Use HTTPS in production, configure allowed origins as needed, and consider rate limiting, account verification, password-reset flows, and database migrations.
- Passwords are hashed and never returned by the API.
