from backend.database import SessionLocal
from backend.models import Item, ItemUser, Feedback, User

db = SessionLocal()

print(f"Total Users: {db.query(User).count()}")
print(f"Total Items: {db.query(Item).count()}")
items = db.query(Item).all()
for item in items:
    assigned_count = db.query(ItemUser).filter(ItemUser.item_id == item.id).count()
    # Feedback is linked to ItemUser, not Item directly
    feedback_count = db.query(Feedback).join(ItemUser).filter(ItemUser.item_id == item.id).count()
    print(f"Item {item.id} ('{item.title}'): Assigned={assigned_count}, Feedbacks={feedback_count}")

db.close()
