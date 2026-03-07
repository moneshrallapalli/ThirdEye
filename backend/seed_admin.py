"""
Seed admin user for initial setup
"""
from database import SessionLocal, User
from auth import get_password_hash
from datetime import datetime
from loguru import logger


def seed_admin_user():
    """Create initial admin user"""
    db = SessionLocal()

    try:
        # Check if admin already exists
        admin_email = "moneshrallapalli@gmail.com"
        existing_admin = db.query(User).filter(User.email == admin_email).first()

        if existing_admin:
            logger.info(f"Admin user already exists: {admin_email}")
            return

        # Create admin user
        admin_user = User(
            email=admin_email,
            hashed_password=get_password_hash("admin123"),
            full_name="Admin User",
            is_active=True,  # Pre-activated for admin
            is_verified=True,  # Pre-verified for admin
            verification_token=None,
            verification_token_expires=None
        )

        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        logger.success(f"✅ Admin user created successfully!")
        logger.info(f"   Email: {admin_email}")
        logger.info(f"   Password: admin123")
        logger.warning(f"   ⚠️  Please change the password after first login!")

    except Exception as e:
        logger.error(f"Failed to create admin user: {str(e)}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    logger.info("Seeding admin user...")
    seed_admin_user()
