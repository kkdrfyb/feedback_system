import requests
import random
import time
from faker import Faker

fake = Faker('zh_CN')

BASE_URL = "http://localhost:8000/api"
ADMIN_USER = "admin"
ADMIN_PASS = "admin"

session = requests.Session()
token = None

def login(username, password):
    global token
    res = session.post(f"{BASE_URL}/login", json={"username": username, "password": password})
    if res.status_code == 200:
        data = res.json()
        token = data["access_token"]
        session.headers.update({"Authorization": f"Bearer {token}"})
        return data
    else:
        print(f"[ERROR] Login failed for {username}: {res.text}")
        return None

def create_users(count=50):
    print(f"\n--- Creating {count} Users ---")
    login(ADMIN_USER, ADMIN_PASS)
    
    # Simulate CSV Import Data
    # To do this cleanly via API, we might need a dedicated endpoint or just manipulate DB.
    # But since we have an import endpoint, let's try to mock uploading a CSV? 
    # Or just use the register endpoint if it exists? 
    # Wait, we only have login/groups import. Let's use the local 'models' import if possible, 
    # OR simpler: just hit the 'import_groups' endpoint with a crafted CSV string?
    # Actually, we don't have a direct 'register' API exposed in the router list I saw earlier (only import).
    # So I will generate a CSV file and upload it using the import endpoint! 
    
    csv_content = "name,username,password,role,group\n"
    groups = ["A组", "B组", "C组", "D组", "E组"]
    
    users_created = []
    
    for i in range(count):
        name = fake.name()
        username = f"user_{i}_{random.randint(1000,9999)}"
        password = "password"
        role = "feedbacker"
        group = random.choice(groups)
        csv_content += f"{name},{username},{password},{role},{group}\n"
        users_created.append({"username": username, "password": password, "name": name})

    # Save to file
    with open("stress_test_users.csv", "w", encoding="utf-8") as f:
        f.write(csv_content)
        
    # Upload
    with open("stress_test_users.csv", "rb") as f:
        files = {"file": ("users.csv", f, "text/csv")}
        res = session.post(f"{BASE_URL}/groups/import", params={"owner_id": 1}, files=files)
        
    if res.status_code == 200:
        print(">> Users imported successfully:", res.json())
    else:
        print(">> Import failed:", res.text)
        
    return users_created

def reset_items_data():
    print("\n--- Resetting Items and Feedback Data ---")
    login(ADMIN_USER, ADMIN_PASS)
    # We don't have a direct "delete all" API, so we might need to iterate or add one.
    # For speed in stress testing, let's just delete in a loop or use a dangerous DB hack if strict.
    # But adhering to API:
    items = session.get(f"{BASE_URL}/items").json()
    for item in items:
        session.delete(f"{BASE_URL}/items/{item['id']}")
    print(f">> Deleted {len(items)} items.")

def create_specific_scenario(num_items=10):
    print(f"\n--- Creating Specific Scenario: {num_items} Items ---")
    login(ADMIN_USER, ADMIN_PASS)
    
    # Get all users
    all_users = session.get(f"{BASE_URL}/users").json()
    if len(all_users) < 15:
        print("!! Not enough users to run this test properly. Creating more...")
        create_users(20)
        all_users = session.get(f"{BASE_URL}/users").json()
        
    feedbacker_users = [u for u in all_users if u['role'] != 'admin']
    admin_users = [u for u in all_users if u['role'] == 'admin']
    
    if not feedbacker_users:
        print("!! No feedbacker users found.")
        return

    for i in range(num_items):
        # Determine creator: 70% chance to be non-admin (or exactly 7 items as requested)
        # Detailed request: "At least 7 items are created by ordinary users"
        if i < 7:
            creator = random.choice(feedbacker_users)
        else:
            creator = random.choice(admin_users) if admin_users else random.choice(feedbacker_users)
            
        # Log in as this creator to create item? 
        # API allows specifying creator_id, but usually backend enforces current user.
        # Check backend/routers/items.py: 
        # creator_id: int = Form(...)
        # It accepts form data for creator_id. It doesn't seem to enforce `current_user.id == creator_id` strictly 
        # or maybe we typically use admin to create for others.
        # Let's assume we can pass creator_id as Admin.
        
        # Select > 10 users (11 to 15)
        # User request: "Every item needs at least 10 users feedback" -> Assign >10 users
        candidates = [u['id'] for u in all_users]
        if len(candidates) < 11:
            candidates = candidates * 2 # Hack if few users
            
        selected_uids = random.sample(candidates, k=random.randint(11, min(15, len(candidates))))
        # Make unique just in case
        selected_uids = list(set(selected_uids))
        
        data = {
            "title": f"专项测试-{i+1}-{'普通' if i < 7 else '管'} ({len(selected_uids)}人)",
            "description": f"由 {creator['name']} 发起的测试事项",
            "deadline": "2026-12-31 23:59:59",
            "must_feedback": "true",
            "creator_id": creator['id'],
            "user_ids": str(selected_uids)
        }
        
        # We need to post as ADMIN to ensure we have rights to assign anyone, 
        # OR login as creator. Let's use Admin for simplicity if backend allows.
        # Trigger multipart/form-data by providing empty files dict
        res = session.post(f"{BASE_URL}/items", data=data, files={}) 
        
        if res.status_code == 200:
            try:
                item_id = res.json()['id']
                print(f">> Item {i+1} created (Creator: {creator['name']}, Assigned: {len(selected_uids)}).")
            except Exception as e:
                print(f">> Item {i+1} created but parsing failed: {res.text}")
                raise e
        else:
            print(f">> Item {i+1} failed: {res.text}")

def simulate_full_feedback():
    print("\n--- Simulating Feedback (Aiming for 100% on some) ---")
    # We want to verify 100% completion status.
    # Let's get all items
    login(ADMIN_USER, ADMIN_PASS)
    items = session.get(f"{BASE_URL}/items").json()
    
    all_users = session.get(f"{BASE_URL}/users").json()
    user_map = {u['id']: u for u in all_users}
    
    for idx, item in enumerate(items):
        # Get details to find who is assigned
        # But we don't have a clean "get item users" endpoint exposed easily in items list
        # We can use /items/{id}
        detail = session.get(f"{BASE_URL}/items/{item['id']}").json()
        # detail contains "item" and "feedbacks". 
        # It DOES NOT list pending users explicitly unless we infer from... wait.
        # We can assume we know the users if we just act as "users logging in and checking todos".
        pass

    # Better approach: Iterate all users, check their todos, and submit.
    # To satisfy "1/1 is completed" test, let's make the FIRST 3 items 100% complete.
    # The REST 50% complete.
    
    processed_count = 0
    
    for u in all_users:
        # Login as user
        # Note: password is 'password' from creation
        login_res = login(u['username'], "password")
        if not login_res: 
            # Try 'admin' if default
            login_res = login(u['username'], "admin")
            
        if not login_res: continue
        
        my_id = login_res['user_id']
        
        # Get Todos
        todos = session.get(f"{BASE_URL}/todos", params={"user_id": my_id}).json()
        
        for todo in todos:
            # Check item ID to decide strategy
            # Items are likely ID 1..10 (or higher if valid).
            # We want items 0, 1, 2 (as per loop index) to be fully done.
            # But we don't know the exact ID mapping to index easily.
            # Let's just say: 
            # If item title contains "专项测试-1-", "专项测试-2-", "专项测试-3-", ALWAYS feedback.
            # Others: 50% chance.
            
            should_feedback = False
            if any(x in todo['title'] for x in ["-1-", "-2-", "-3-"]):
                should_feedback = True
            elif random.random() > 0.5:
                should_feedback = True
                
            if should_feedback:
                session.post(f"{BASE_URL}/feedbacks", json={
                    "item_user_id": todo["item_user_id"],
                    "content": f"Full test feedback from {u['name']}"
                })
                processed_count += 1
                
    print(f">> Simulated {processed_count} feedback actions.")

if __name__ == "__main__":
    try:
        # new_users = create_users(50) # Optional: comment out if users exist
        # Or just ensure we have enough users
        create_users(10) # Ensure some users exist
        
        reset_items_data()
        create_specific_scenario(10)
        simulate_full_feedback()
        print("\n=== Stress Test Completed Successfully ===")
    except Exception as e:
        print("\n!!! Stress Test Failed !!!")
        print(e)
