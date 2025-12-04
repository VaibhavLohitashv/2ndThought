# TODO List for Realtime Forum Project

## High-Level Features
### Done
- Multi-framework microservice backend (DRF + FastAPI)
- JWT authentication
- Threads and comments with CRUD
- Basic admin actions
- Dockerized deployment
- Clean code and best practices

### Not Done
- Real-time comments and typing indicators (WebSockets + Redis)
- API Gateway routing

## Must Have
### Done
- User logs in and creates their profile
    - Advice: Use Firebase Auth to avoid all JWT work
- Create a thread
- Users can comment on threads
    - Nice to have: Users can reply to others' comments
- CRUD and List on comments
- CRUD and List on threads
- Search threads
- Notifications

### Not Done
- None

## Good to Have (Stateless)
### Done
- Admin Panel

### Not Done
- Attachments

## Good to Have (Stateful)
### Not Done
- Live notifications

## Bonus Points
### Not Done
- Live updates on threads (e.g., Rank update of member)
- Live user status (e.g., "a, b, c is typing...", "n number of users viewing this thread")

## Final Demo Checklist
### Not Done
- Well-written code with CLEAN code practices
- All defined service flows running as expected
- Use `black` for code formatting
- Pydantic layer for data validation
- Code committed on GIT with iterative MRs for review
- No extra files like `__pycache__` pushed to git
- Add README file, `requirements.txt`, and `Pipfile` in each project
- Add Python documentation in methods wherever required
- Add API documentation (Swagger)
- Add unit test cases with >80% coverage
- Dockerize the app with a `docker-compose.yml` file