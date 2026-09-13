"""
Backfill utility for legacy approved admissions applications.

Fixes rows in the ``applications`` table that are already marked as APPROVED
but are missing their linked ``users`` / ``students`` / ``enrollments``
records (e.g. "Daman Zahra") — which previously left active-student counters
at zero, emptied the Fee Challan dropdown, and broke foreign-key references.

The provisioning logic is shared with the live approval endpoint
(``POST /applications/{id}/approve``) and is fully idempotent: existing
User / Student / Enrollment records are never duplicated, and each
application is committed separately so a single bad row cannot abort the
entire backfill.

Usage (run from the backend project root with DATABASE_URL set):

    python backfill_approved_applications.py               # all approved applications
    python backfill_approved_applications.py --email daman.zahra@example.com
    python backfill_approved_applications.py --dry-run     # report only, no writes
"""

import argparse
import sys

from sqlalchemy import func

import models
from database import SessionLocal
from routers.applications import provision_student_records, provision_summary


def backfill(email_filter: str | None = None, dry_run: bool = False) -> int:
    """
    Provision missing records for every approved application.

    Returns the number of applications processed. Exits non-zero (via the
    caller) if any application failed, so it is CI / cron friendly.
    """
    db = SessionLocal()
    failures = 0
    processed = 0
    try:
        query = db.query(models.Application).filter(
            func.lower(models.Application.status) == "approved"
        )
        if email_filter:
            query = query.filter(
                func.lower(models.Application.email) == email_filter.strip().lower()
            )

        apps = query.order_by(models.Application.id).all()
        print(f"Found {len(apps)} approved application(s) to backfill"
              f"{' (DRY RUN — nothing will be written)' if dry_run else ''}")

        for app_record in apps:
            processed += 1
            try:
                provisioned = provision_student_records(db, app_record)
                summary = provision_summary(provisioned)
                created = [k.replace("_created", "") for k, v in summary.items() if v]
                if dry_run:
                    db.rollback()
                    status_line = (
                        "WOULD CREATE: " + ", ".join(created)
                        if created
                        else "nothing (records already exist)"
                    )
                else:
                    db.commit()
                    status_line = (
                        "CREATED: " + ", ".join(created)
                        if created
                        else "nothing (records already exist)"
                    )
                print(f"  [{app_record.id}] {app_record.full_name} <{app_record.email}> -> {status_line}")
            except Exception as exc:  # noqa: BLE001 — keep going, report at the end
                db.rollback()
                failures += 1
                print(f"  [{app_record.id}] {app_record.full_name} <{app_record.email}> -> FAILED: {exc}",
                      file=sys.stderr)
    finally:
        db.close()

    print(f"Done. Processed {processed} application(s), {failures} failure(s).")
    return failures


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill User/Student/Enrollment records for approved applications.")
    parser.add_argument("--email", help="Only backfill the application with this email address.")
    parser.add_argument("--dry-run", action="store_true", help="Report what would be created without writing.")
    args = parser.parse_args()

    failed = backfill(email_filter=args.email, dry_run=args.dry_run)
    sys.exit(1 if failed else 0)
