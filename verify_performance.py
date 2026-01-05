import time
from backend.database import SessionLocal
from backend import models
from sqlalchemy import func

def verify_performance():
    db = SessionLocal()
    try:
        print("Verifying data counts...")
        start_time = time.time()
        user_count = db.query(models.User).count()
        item_count = db.query(models.Item).count()
        feedback_count = db.query(models.Feedback).count()
        item_user_count = db.query(models.ItemUser).count()
        end_time = time.time()
        
        print(f"Data Counts (Time taken: {end_time - start_time:.4f}s):")
        print(f"- Users: {user_count}")
        print(f"- Items: {item_count}")
        print(f"- ItemUsers: {item_user_count}")
        print(f"- Feedbacks: {feedback_count}")
        
        print("\nTesting Search Performance...")
        # Simulate searching for items with specific keyword
        keyword = "的" # Very common character in Chinese dummy text
        start_time = time.time()
        results = db.query(models.Item).filter(
            (models.Item.title.contains(keyword)) | 
            (models.Item.description.contains(keyword))
        ).limit(20).all()
        end_time = time.time()
        print(f"Search '{keyword}' (limit 20) took: {end_time - start_time:.4f}s. Found {len(results)} items.")
        
        print("\nTesting Complex Query (Stats)...")
        # Simulate getting stats for a user (e.g., pending tasks)
        # Find a random user
        user = db.query(models.User).first()
        if user:
            start_time = time.time()
            pending_count = db.query(models.ItemUser).filter(
                models.ItemUser.user_id == user.id,
                models.ItemUser.feedback_status == "pending"
            ).count()
            end_time = time.time()
            print(f"User {user.username} pending tasks count: {pending_count}. Time: {end_time - start_time:.4f}s")

    finally:
        db.close()

if __name__ == "__main__":
    verify_performance()
