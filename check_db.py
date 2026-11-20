import os
import sys

# Ensure backend directory is in python path
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.database import engine
from sqlalchemy import text

def check_database():
    print("=" * 70)
    print("  AgriLink RTO Platform - Live Supabase Database Inspector")
    print("=" * 70)

    try:
        with engine.connect() as conn:
            # 1. Registered Users
            users = conn.execute(text("""
                SELECT id, name, email, phone, role, 
                       (face_descriptor IS NOT NULL) as has_face,
                       created_at 
                FROM users 
                ORDER BY created_at DESC 
                LIMIT 10
            """)).fetchall()

            total_users = conn.execute(text("SELECT count(*) FROM users")).scalar()
            print(f"\n👤 LATEST USERS (Total Registered: {total_users}):")
            print("-" * 70)
            if not users:
                print("  No users found.")
            for u in users:
                face_status = "✓ Face Enrolled" if u[5] else "— Password Only"
                reg_date = u[6].strftime("%Y-%m-%d %H:%M:%S") if u[6] else "N/A"
                print(f"  • {u[1]:<22} | Email: {u[2]:<30} | Role: {u[4]:<14} | {face_status} | {reg_date}")

            # 2. Registered Fleet Vehicles
            vehicles = conn.execute(text("""
                SELECT id, registration_number, vehicle_class, make_model, owner_name, status, verification_status
                FROM vehicles 
                ORDER BY created_at DESC 
                LIMIT 10
            """)).fetchall()

            total_vehicles = conn.execute(text("SELECT count(*) FROM vehicles")).scalar()
            print(f"\n🚚 REGISTERED FLEET (Total Vehicles: {total_vehicles}):")
            print("-" * 70)
            for v in vehicles:
                print(f"  • {v[1]:<14} | {v[3]:<32} | Owner: {v[4]:<16} | Status: {v[5]}")

            # 3. Rental Bookings
            bookings = conn.execute(text("""
                SELECT id, booking_ref, vehicle_id, renter_name, status, start_time, end_time, created_at
                FROM bookings 
                ORDER BY created_at DESC 
                LIMIT 10
            """)).fetchall()

            total_bookings = conn.execute(text("SELECT count(*) FROM bookings")).scalar()
            print(f"\n📅 RECENT BOOKINGS (Total Bookings: {total_bookings}):")
            print("-" * 70)
            if not bookings:
                print("  No bookings placed yet.")
            for b in bookings:
                created = b[7].strftime("%Y-%m-%d %H:%M") if b[7] else "N/A"
                print(f"  • Ref: {b[1]:<18} | Renter: {b[3]:<18} | Status: {b[4]:<12} | Placed: {created}")

            # 4. Outbox Inter-service Events
            outbox = conn.execute(text("""
                SELECT id, event_type, aggregate_id, published, created_at
                FROM outbox_events 
                ORDER BY created_at DESC 
                LIMIT 5
            """)).fetchall()
            print(f"\n📡 LATEST OUTBOX EVENTS (Inter-Service Messages):")
            print("-" * 70)
            if not outbox:
                print("  No outbox events.")
            for ev in outbox:
                pub_status = "Dispatched" if ev[3] else "Pending"
                print(f"  • Event: {ev[1]:<24} | Aggregate ID: {ev[2]:<16} | Status: {pub_status}")

            print("\n" + "=" * 70)
            print("  Supabase Database Connection: ACTIVE & SYNCED")
            print("  Cloud Dashboard: https://supabase.com/dashboard/project/mgilglfzakfqmssxadrx")
            print("=" * 70 + "\n")

    except Exception as e:
        print(f"\n[ERROR] Database check failed: {e}")

if __name__ == "__main__":
    check_database()
