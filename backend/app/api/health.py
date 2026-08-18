"""Liveness endpoint. Does not query the database."""
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/debug/seed-check")
def debug_seed_check():
    from app.database.session import SessionLocal
    from app.models.employee import Employee
    session = SessionLocal()
    try:
        employees = session.query(Employee).all()
        return {
            "employee_count": len(employees),
            "employees": [{"code": e.employee_code, "email": e.email} for e in employees],
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        session.close()


@router.post("/debug/seed-run")
def debug_seed_run():
    from app.database.seed import seed_development_data
    from app.database.session import SessionLocal
    session = SessionLocal()
    try:
        org = seed_development_data(session)
        session.commit()
        return {"status": "ok", "organization_code": org.code, "organization_id": str(org.id)}
    except Exception as e:
        session.rollback()
        import traceback
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}
    finally:
        session.close()
