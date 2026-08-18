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