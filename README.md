ACLCore - Django ACL Middleware

- What it does: Enforces allow/deny for requests based on app, route (path+method), and user_id header.
- How to run:
  - cd middleware/ACL && source ./venv/bin/activate
  - python manage.py migrate
  - python manage.py runserver 8001
- Quick use:
  - Sync routes: python manage.py aclcore_sync_routes --application myapp
  - Seed fake data (optional):python manage.py faker --application 1
  - Call any endpoint with headers:
    - X-User-Id: user-123
    - X-ACL-App: myapp
- Admin (manage roles/routes): http://127.0.0.1:8001/admin/
- Test flow:
  - Assign roles to user (admin or shell), hit a registered route with headers → 200 if allowed, 403 otherwise.
