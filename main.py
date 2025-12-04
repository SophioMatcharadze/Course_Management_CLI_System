import csv
import os
import re
from datetime import datetime
from collections import defaultdict
from courses_data import university_prep_data, discount_table

DB_FILE = "students_registry.csv"

# =========================================================
# 1. ვალიდაციის კლასი
# =========================================================
class Validator:
    @staticmethod
    def is_georgian_text(text):
        return all('\u10d0' <= char <= '\u10fa' for char in text)

    @staticmethod
    def validate_name_field(prompt):
        while True:
            value = input(prompt).strip()
            if len(value) < 2:
                print("❌ შეცდომა: შეიყვანეთ მინიმუმ 2 სიმბოლო.")
                continue
            if not Validator.is_georgian_text(value):
                print("❌ შეცდომა: გთხოვთ, გამოიყენოთ მხოლოდ ქართული ანბანი")
                continue
            return value

    @staticmethod
    def validate_phone():
        while True:
            phone = input("მობილურის ნომერი (9 ციფრი): ").strip()
            if phone.isdigit() and len(phone) == 9:
                return phone
            print("❌ შეცდომა: ნომერი უნდა შედგებოდეს 9 ციფრისგან.")

    @staticmethod
    def validate_email():
        regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        while True:
            email = input("ელ-ფოსტა: ").strip()
            if re.match(regex, email):
                return email
            print("❌ შეცდომა: არასწორი ფორმატი.")

# =========================================================
# 2. მონაცემთა ბაზის მენეჯერი
# =========================================================
class StudentDatabase:
    def __init__(self, filename):
        self.filename = filename
        self._init_db()

    def _init_db(self):
        if not os.path.exists(self.filename):
            with open(self.filename, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "name", "surname", "father_name", "phone", "email",
                    "course_id", "course_name", "time_keys", "status", "receipt_id", "timestamp"
                ])

    def add_record(self, student_info, course, receipt_id, status="Active"):
        with open(self.filename, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            time_keys_str = ";".join(course["time_keys"]) if isinstance(course["time_keys"], list) else course["time_keys"]
            
            writer.writerow([
                student_info["name"],
                student_info["surname"],
                student_info["father_name"],
                student_info["phone"],
                student_info["email"],
                course["id"],
                course["name"],
                time_keys_str,
                status,
                receipt_id,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ])

    def check_receipt_exists(self, receipt_id):
        """ამოწმებს, არის თუ არა ქვითარი უკვე გამოყენებული."""
        if not os.path.exists(self.filename): return False
        with open(self.filename, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # ამოწმებს მხოლოდ Active სტატუსის მქონე ჩანაწერებს
                if row["receipt_id"] == receipt_id and row["status"] == "Active":
                    return True
        return False

    def get_all_records(self):
        """აბრუნებს DB-ის ყველა ჩანაწერს."""
        if not os.path.exists(self.filename): return []
        with open(self.filename, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)

    def get_student_history(self, name, surname, father_name):
        active_courses = {}
        if not os.path.exists(self.filename): return []

        with open(self.filename, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if (row["name"] == name and row["surname"] == surname and row["father_name"] == father_name):
                    if row["status"] == "Active":
                        active_courses[row["course_id"]] = row
                    elif row["status"] == "Cancelled":
                        if row["course_id"] in active_courses:
                            del active_courses[row["course_id"]]
        return list(active_courses.values())

    def get_course_occupancy(self, course_id):
        student_status_map = defaultdict(lambda: "None")
        if not os.path.exists(self.filename): return 0
        
        with open(self.filename, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["course_id"] == course_id:
                    unique_key = (row["name"], row["surname"], row["father_name"])
                    student_status_map[unique_key] = row["status"]
                    
        return sum(1 for status in student_status_map.values() if status == "Active")


# =========================================================
# 3. სისტემის ლოგიკა
# =========================================================
class RegistrationSystem:
    def __init__(self):
        self.db = StudentDatabase(DB_FILE)
        self.courses = university_prep_data["subjects"]
        self.base_price = university_prep_data["price_per_subject"]

    def extract_subject_name(self, full_course_name):
        return full_course_name.split("(")[0].strip()

    def check_conflicts(self, student_history, new_course, cart_courses):
        new_time_keys = set(new_course["time_keys"] if isinstance(new_course["time_keys"], list) else new_course["time_keys"].split(";"))
        new_subject_name = self.extract_subject_name(new_course["name"])

        # 1. ისტორიასთან შემოწმება (history records)
        for record in student_history:
            existing_keys = set(record["time_keys"].split(";"))
            if not new_time_keys.isdisjoint(existing_keys):
                return f"დროის კონფლიქტი რეგისტრირებულ კურსთან: {record['course_name']}"
            if self.extract_subject_name(record["course_name"]) == new_subject_name:
                return f"უკვე რეგისტრირებული ხართ ამ საგანზე: {new_subject_name}"

        # 2. კალათასთან შემოწმება (course objects)
        for item in cart_courses:
            existing_keys = set(item["time_keys"])
            if not new_time_keys.isdisjoint(existing_keys):
                return f"დროის კონფლიქტი კალათაში არსებულთან: {item['name']}"
            if self.extract_subject_name(item["name"]) == new_subject_name:
                return f"კალათაში უკვე არის საგანი: {new_subject_name}"
        return None

    def calculate_prices(self, count):
        disc_percent = discount_table.get(count, 25 if count > 5 else 0)
        original = self.base_price
        discount_amt = original * (disc_percent / 100)
        final = original - discount_amt
        return original, disc_percent, final

    def print_cart(self, cart):
        if not cart:
            print("\n🛒 ამ ეტაპზე კურსი არ დამატებულა")
            return

        count = len(cart)
        orig, perc, fin = self.calculate_prices(count)
        
        print("\n🛒 თქვენი კალათა:")
        print(f"{'ID':<4} | {'დასახელება':<30} | {'საწყისი':<8} | {'ფასდ.%':<6} | {'ფასი':<8}")
        print("-" * 70)
        
        total_sum = 0
        for item in cart:
            print(f"{item['id']:<4} | {item['name']:<30} | {orig:<8} | {perc:<6}% | {fin:<8.2f}")
            total_sum += fin
            
        print("-" * 70)
        print(f"სულ გადასახდელი (კალათა): {total_sum:.2f} GEL")

    # ============================
    # მთავარი პროცესი (register_process)
    # ============================
    def register_process(self):
        cart = []
        last_message = ""
        
        while True:
            print("\n" * 2) 
            print("=== 1. კურსების არჩევა ===")
            
            print(f"{'ID':<4} | {'დასახელება':<30} | {'დრო':<25} | {'სტატუსი'}")
            print("-" * 85)
            for course in self.courses:
                occupied = self.db.get_course_occupancy(course["id"])
                available = course["capacity"] - occupied
                
                status_icon = "✅" if available > 0 else "⛔ ჯგუფი შევსებულია"
                in_cart_mark = " [კალათაშია]" if course in cart else ""
                
                print(f"{course['id']:<4} | {course['name']:<30} | {course['time_display']:<25} | {available}/{course['capacity']} {status_icon}{in_cart_mark}")
            
            self.print_cart(cart)

            if last_message:
                print(f"\n📢 {last_message}")
                last_message = ""

            print("\nინსტრუქცია:")
            print("• კურსის ასარჩევად აკრიფეთ კურსის ID (მაგ.: 1)")
            print("• არჩეული კურსის წასაშლელად აკრიფეთ 'del' და ID (მაგ.: del 1)")
            print("• არჩევის ეტაპის დასასრულებლად აკრიფეთ 'F'")
            print("• გასასვლელად აკრიფეთ 'X'")
            
            choice = input("\n>> თქვენი არჩევანი: ").strip().lower()

            if choice == 'x': return
            
            if choice == 'f':
                if not cart:
                    last_message = "❌ კალათა ცარიელია! აირჩიეთ მინიმუმ 1 საგანი."
                    continue
                break

            if choice.startswith("del "):
                del_id = choice.split(" ")[1]
                to_remove = next((c for c in cart if c["id"] == del_id), None)
                if to_remove:
                    cart.remove(to_remove)
                    last_message = f"🗑️ კურსი '{to_remove['name']}' წაიშალა კალათიდან."
                else:
                    last_message = "❌ ასეთი კურსი კალათაში არ არის."
                continue

            selected_course = next((c for c in self.courses if c["id"] == choice), None)
            
            if not selected_course:
                last_message = "❌ არასწორი ID."
                continue

            if self.db.get_course_occupancy(selected_course["id"]) >= selected_course["capacity"]:
                last_message = "❌ ჯგუფი შევსებულია!"
                continue

            if selected_course in cart:
                last_message = "⚠️ ეს კურსი უკვე კალათაშია."
                continue

            conflict_error = self.check_conflicts([], selected_course, cart)
            if conflict_error:
                last_message = f"❌ {conflict_error}"
                continue

            cart.append(selected_course)
            last_message = f"👍 '{selected_course['name']}' დაემატა კალათაში."


        # --- ეტაპი 2: პირადი მონაცემები ---
        print("\n\n=== 2. პირადი მონაცემები (იდენტიფიკაცია) ===")
        print("გთხოვთ შეიყვანოთ მონაცემები ქართული ანბანით")
        
        name = Validator.validate_name_field("სახელი: ")
        surname = Validator.validate_name_field("გვარი: ")
        father_name = Validator.validate_name_field("მამის სახელი: ")
        
        history = self.db.get_student_history(name, surname, father_name)
        
        final_conflicts = []
        for item in cart:
            err = self.check_conflicts(history, item, [])
            if err:
                final_conflicts.append(err)
        
        if final_conflicts:
            print("\n❌ დაფიქსირდა კონფლიქტი არჩეულ კურსებთან:")
            for err in final_conflicts:
                print(f"- {err}")
            print("რეგისტრაცია შეჩერებულია. გთხოვთ თავიდან აირჩიოთ კურსები.")
            return

        phone = Validator.validate_phone()
        email = Validator.validate_email()

        # --- ეტაპი 3: საბოლოო ანგარიში და გადახდა ---
        print("\n=== 3. საბოლოო ანგარიშსწორება ===")
        
        total_subjects = len(history) + len(cart)
        _, percent, final_item_price = self.calculate_prices(total_subjects)
        total_to_pay = final_item_price * len(cart)

        print(f"თქვენ უკვე სწავლობთ: {len(history)} საგანს.")
        print(f"ამატებთ: {len(cart)} საგანს.")
        print(f"საერთო რაოდენობა (ფასდაკლებისთვის): {total_subjects}")
        print(f"კუთვნილი ფასდაკლება: {percent}%")
        print("-" * 30)
        print(f"სულ გადასახდელი: {total_to_pay:.2f} GEL")

        while True:
            receipt = input("\nშეიყვანეთ გადახდის დამადასტურებელი დოკუმენტის ნომერი: ").strip()
            if not receipt:
                print("❌ გადახდის დამადასტურებელი დოკუმენტის ნომრის შეყვანა აუცილებელია.")
                continue
            
            if self.db.check_receipt_exists(receipt):
                print("❌ დოკუმენტის ეს ნომერი უკვე გამოყენებულია სისტემაში!")
                continue
            
            break

        # --- ეტაპი 4: შენახვა ---
        student_info = {
            "name": name, "surname": surname, "father_name": father_name,
            "phone": phone, "email": email
        }
        
        for item in cart:
            self.db.add_record(student_info, item, receipt, status="Active")
            
        print("\n🎉 რეგისტრაცია წარმატებით დასრულდა!")
        input("დააჭირეთ Enter-ს მენიუში დასაბრუნებლად...")

    # ============================
    # რედაქტირების პროცესი (edit_registration უცვლელია)
    # ============================
    def edit_registration(self):
        print("\n\n=== 2. პირადი მონაცემები (იდენტიფიკაცია) ===")
        print("გთხოვთ შეიყვანოთ მონაცემები ქართული ანბანით.")
        
        name = Validator.validate_name_field("სახელი: ")
        surname = Validator.validate_name_field("გვარი: ")
        father_name = Validator.validate_name_field("მამის სახელი: ")

        current_active_courses = self.db.get_student_history(name, surname, father_name)
        
        if not current_active_courses:
            print(f"\n❌ სტუდენტი {name} {surname} {father_name} არ არის რეგისტრირებული აქტიურ კურსებზე.")
            input("დააჭირეთ Enter-ს მენიუში დასაბრუნებლად...")
            return

        course_objects_map = {c["id"]: c for c in self.courses}
        
        active_cart = []
        for record in current_active_courses:
            course_obj = course_objects_map.get(record["course_id"])
            if course_obj:
                temp_course = course_obj.copy() 
                temp_course["_receipt_id"] = record["receipt_id"]
                active_cart.append(temp_course)

        newly_added = []
        removed_courses = []
        last_message = ""
        
        while True:
            # ეკრანის "გასუფთავება"
            print("\n" * 2) 
            print("=== 2. რეგისტრაციის რედაქტირება ===")
            
            # ------------------------------------------------------------------
            # <<< ახალი კოდი: კურსების ჩამონათვალის ბეჭდვა >>>
            # ------------------------------------------------------------------
            print("\n📚 არსებული კურსები:")
            print(f"{'ID':<4} | {'დასახელება':<30} | {'დრო':<25} | {'სტატუსი'}")
            print("-" * 85)
            for course in self.courses:
                occupied = self.db.get_course_occupancy(course["id"])
                available = course["capacity"] - occupied
                
                status_icon = "✅" if available > 0 else "⛔ ჯგუფი შევსებულია"
                
                # ვამოწმებთ არის თუ არა ეს კურსი უკვე აქტიური ან ახალდამატებული
                is_active = course["id"] in [c["id"] for c in active_cart if c not in removed_courses]
                is_newly_added = course in newly_added
                
                status_mark = ""
                if is_active:
                    status_mark = " [რეგისტრირებული]"
                elif is_newly_added:
                    status_mark = " [დასამატებელი]"
                    
                print(f"{course['id']:<4} | {course['name']:<30} | {course['time_display']:<25} | {available}/{course['capacity']} {status_icon}{status_mark}")
            # ------------------------------------------------------------------
            
            # 1. აქტიური/დასამატებელი კურსების შეჯამება (რომელიც ადრე იყო)
            print("\n✅ რეგისტრირებული და დასამატებელი კურსები (ID-ების მითითება არ არის საჭირო):")
            print(f"{'ID':<4} | {'დასახელება':<30} | {'დრო':<25} | {'სტატუსი'}")
            print("-" * 85)
            
            for c in active_cart:
                if c in removed_courses: continue
                
                occupied = self.db.get_course_occupancy(c["id"])
                available = c["capacity"] - occupied
                
                status_icon = "✅" if available > 0 else "⛔ ჯგუფი შევსებულია"
                print(f"{c['id']:<4} | {c['name']:<30} | {c['time_display']:<25} | {available}/{c['capacity']} {status_icon} [აქტიური]")

            for c in newly_added:
                occupied = self.db.get_course_occupancy(c["id"])
                available = c["capacity"] - occupied
                status_icon = "✅" if available > 0 else "⛔ ჯგუფი შევსებულია"
                print(f"{c['id']:<4} | {c['name']:<30} | {c['time_display']:<25} | {available}/{c['capacity']} {status_icon} [დასამატებელი]")
                
            self.print_cart(newly_added)

            if removed_courses:
                print(f"\n🗑️ მონიშნულია გასაუქმებლად: {', '.join(c['name'] for c in removed_courses)}")
            
            if last_message:
                print(f"\n📢 {last_message}")
            last_message = "" 

            print("\nინსტრუქცია:")
            print("• კურსის დასამატებლად აკრიფეთ კურსის ID (მაგ.: 1) ")
            print("• აქტიური/დასამატებელი კურსის გასაუქმებლად აკრიფეთ 'del' და ID (მაგ.: del 1)")
            print("• რედაქტირების ეტაპის დასასრულებლად აკრიფეთ 'F'")
            print("• გასასვლელად აკრიფეთ 'X'")
            
            choice = input("\n>> თქვენი არჩევანი: ").strip().lower()

            if choice == 'x': 
                return
            
            if choice == 'f':
                if not newly_added and not removed_courses:
                    print("\n✅ ცვლილებები არ განხორციელებულა. რედაქტირება დასრულდა.")
                    input("დააჭირეთ Enter-ს მენიუში დასაბრუნებლად...")
                    return

                break

            if choice.startswith("del "):
                del_id = choice.split(" ")[1]
                
                to_remove_from_new = next((c for c in newly_added if c["id"] == del_id), None)
                if to_remove_from_new:
                    newly_added.remove(to_remove_from_new)
                    last_message = f"🗑️ კურსი '{to_remove_from_new['name']}' წაიშალა დასამატებელთა სიიდან"
                    continue

                to_remove_from_active_list = [c for c in active_cart if c not in removed_courses]
                to_remove_from_active = next((c for c in to_remove_from_active_list if c["id"] == del_id), None)
                
                if to_remove_from_active:
                    removed_courses.append(to_remove_from_active)
                    last_message = f"❌ კურსი '{to_remove_from_active['name']}' მონიშნულია გასაუქმებლად"
                    continue
                
                to_reactivate = next((c for c in removed_courses if c["id"] == del_id), None)
                if to_reactivate:
                    removed_courses.remove(to_reactivate)
                    last_message = f"↩️ კურსი '{to_reactivate['name']}' აღარ არის მონიშნული გასაუქმებლად."
                    continue
                    
                last_message = "❌ ასეთი კურსი არ არის აქტიური ან დასამატებელთა სიაში."
                continue

            selected_course = course_objects_map.get(choice)
            
            if not selected_course:
                last_message = "❌ არასწორი ID."
                continue

            if self.db.get_course_occupancy(selected_course["id"]) >= selected_course["capacity"]:
                last_message = "❌ ჯგუფი შევსებულია!"
                continue

            if selected_course["id"] in [c["id"] for c in active_cart if c not in removed_courses]:
                last_message = "⚠️ ეს კურსი უკვე რეგისტრირებულია!"
                continue
                
            if selected_course in newly_added:
                last_message = "⚠️ ეს კურსი უკვე დასამატებელთა სიაშია."
                continue

            active_for_check = [c for c in active_cart if c not in removed_courses]
            history_for_check = [{
                "course_name": c["name"],
                "time_keys": ";".join(c["time_keys"]) 
            } for c in active_for_check]
            
            conflict_error = self.check_conflicts(history_for_check, selected_course, newly_added)
            
            if conflict_error:
                last_message = f"❌ {conflict_error}"
                continue

            newly_added.append(selected_course)
            last_message = f"👍 '{selected_course['name']}' დაემატა დასამატებელთა სიაში."

        # --- ეტაპი 3: საბოლოო ანგარიში და გადახდა (მხოლოდ ახალი კურსებისთვის) ---
        receipt = "N/A"
        if newly_added:
            print("\n=== 3. ახალი კურსების ანგარიშსწორება ===")
            
            total_active_after_edit = len(active_cart) - len(removed_courses) + len(newly_added)
            _, percent, final_item_price = self.calculate_prices(total_active_after_edit)
            total_to_pay = final_item_price * len(newly_added)

            print(f"აქტიური კურსები რედაქტირებამდე: {len(active_cart)}")
            print(f"გაუქმებული: {len(removed_courses)}, დამატებული: {len(newly_added)}")
            print(f"საერთო რაოდენობა (ფასდაკლებისთვის): {total_active_after_edit}")
            print(f"კუთვნილი ფასდაკლება: {percent}%")
            print("-" * 30)
            print(f"სულ გადასახდელი ახალი კურსებისთვის: {total_to_pay:.2f} GEL")

            while True:
                receipt = input("\nშეიყვანეთ გადახდის დამადასტურებელი დოკუმენტის ნომერი (სავალდებულოა): ").strip()
                if not receipt:
                    print("❌ გადახდის დამადასტურებელი დოკუმენტის ნომრის შეყვანა აუცილებელია.")
                    continue
                
                if self.db.check_receipt_exists(receipt):
                    print("❌ დოკუმენტის ეს ნომერი უკვე გამოყენებულია სისტემაში!")
                    continue
                
                break
        
        # --- ეტაპი 4: შენახვა (ცვლილებების ასახვა) ---
        print("\n=== საკონტაქტო მონაცემების განახლება ===")
        phone = Validator.validate_phone()
        email = Validator.validate_email()
        
        student_info = {
            "name": name, "surname": surname, "father_name": father_name,
            "phone": phone, "email": email
        }

        for item in removed_courses:
            original_receipt = item["_receipt_id"] 
            self.db.add_record(student_info, item, original_receipt, status="Cancelled")
            
        for item in newly_added:
            self.db.add_record(student_info, item, receipt, status="Active")
            
        print("\n🎉 რედაქტირება წარმატებით დასრულდა!")
        input("დააჭირეთ Enter-ს მენიუში დასაბრუნებლად...")

    # ============================
    # 4. რეპორტინგის ფუნქციები
    # ============================
    def generate_course_occupancy_report(self):
        print("\n\n=== 4.1. კურსის შევსების რეპორტი ===")
        all_records = self.db.get_all_records()
        
        # 1. ვაგროვებთ სტუდენტის ბოლო აქტიურ სტატუსს (უნიკალური სტუდენტის გასაღებით)
        # student_latest_status: { (name, surname, father_name, course_id): "Active" | "Cancelled" }
        student_latest_status = {}
        # student_info_by_key: { (name, surname, father_name): (phone, email) }
        student_info_by_key = {} 
        
        for row in all_records:
            student_key = (row["name"], row["surname"], row["father_name"])
            course_key = (row["course_id"], row["time_keys"]) # კურსის ID და დრო ერთად ქმნის "ჯგუფს"
            unique_entry_key = student_key + (row["course_id"],)

            # ვინახავთ ამ კონკრეტული სტუდენტის ბოლო სტატუსს ამ კონკრეტულ კურსზე
            student_latest_status[unique_entry_key] = row["status"]
            # ვინახავთ ბოლო საკონტაქტო მონაცემებს
            student_info_by_key[student_key] = (row["phone"], row["email"])

        # 2. ვაჯგუფებთ აქტიურ სტუდენტებს კურსებისა და ჯგუფების მიხედვით
        # course_group_occupancy: { (course_id, time_keys): [student_key1, student_key2, ...] }
        course_group_occupancy = defaultdict(list)
        
        # ვიყენებთ unique_entry_key-ს იმის შესამოწმებლად, რომ სტუდენტი აქტიურია ამ კურსზე
        for row in all_records:
            student_key = (row["name"], row["surname"], row["father_name"])
            group_key = (row["course_id"], row["time_keys"])
            unique_entry_key = student_key + (row["course_id"],)

            # ვამოწმებთ, რომ ეს არის სტუდენტის ბოლო აქტიური სტატუსი ამ კურსზე
            if student_latest_status.get(unique_entry_key) == "Active":
                # ვამოწმებთ, რომ ეს სტუდენტი ჯერ არ არის დამატებული ამ ჯგუფში (რადგან DB-ში დუბლიკატი ჩანაწერებია)
                if student_key not in course_group_occupancy[group_key]:
                    course_group_occupancy[group_key].append(student_key)


        # 3. ვაბეჭდინებთ რეპორტს
        
        for course in self.courses:
            course_id = course["id"]
            course_name = course["name"]
            
            print("\n" + "=" * 100)
            print(f"📚 კურსი: {course_name} (ID: {course_id}) | ტევადობა: {course['capacity']} სტუდენტი")
            print("=" * 100)
            
            # ვპოულობთ ყველა ჯგუფს, რომელიც ამ კურსს ეკუთვნის და ჰყავს რეგისტრირებული სტუდენტები
            course_groups = sorted([
                (c_id, time_keys) for c_id, time_keys in course_group_occupancy.keys() 
                if c_id == course_id
            ], key=lambda x: x[1])

            if not course_groups:
                # ვამოწმებთ, არის თუ არა ჯგუფი ყველა ადგილით ხელმისაწვდომი (რომელიც არავის აურჩევია)
                print("   ❌ ამ ჯგუფში ჯერ არავინაა რეგისტრირებული.")
                continue

            # ჯგუფების დეტალური ჩვენება
            for _, time_keys in course_groups:
                group_key = (course_id, time_keys)
                active_students = course_group_occupancy[group_key]
                occupied = len(active_students)
                available = course["capacity"] - occupied
                
                # ვიღებთ დროის გამოსახულებას courses_data-დან
                time_display = next((c["time_display"] for c in self.courses if c["id"] == course_id), time_keys)

                print("\n   " + "-" * 70)
                print(f"   📅 ჯგუფი: {time_display} (დროის კოდები: {time_keys.replace(';', ', ')})")
                print(f"   👤 შევსება: {occupied} / {course['capacity']} | თავისუფალი: {available} {'✅' if available > 0 else '⛔ ჯგუფი შევსებულია'}")
                print("   " + "-" * 70)
                
                # სტუდენტების სიის ბეჭდვა ამ ჯგუფისთვის
                print(f"   {'№':<4} | {'სახელი გვარი':<30} | {'მამის სახელი':<15} | {'მობილური':<10}")
                print("   " + "-" * 65)

                for i, student_key in enumerate(active_students, 1):
                    name, surname, father_name = student_key
                    phone, _ = student_info_by_key.get(student_key, ('N/A', 'N/A'))
                    
                    full_name = f"{name} {surname}"
                    
                    print(f"   {i:<4} | {full_name:<30} | {father_name:<15} | {phone:<10}")

        input("\nდააჭირეთ Enter-ს მენიუში დასაბრუნებლად...")

        
    def generate_active_students_report(self):
            print("\n\n=== 4.2. აქტიური რეგისტრირებული სტუდენტების სია ===")
            all_records = self.db.get_all_records()
            
            # 1. ვაგროვებთ სტუდენტის ბოლო საკონტაქტო მონაცემებს და აქტიურ კურსებს
            student_data = defaultdict(lambda: {
                "info": {"phone": "N/A", "email": "N/A"},
                "active_courses": []
            })
            
            # სტუდენტის უნიკალური გასაღები: (სახელი, გვარი, მამის სახელი)
            student_keys = set() 

            for row in all_records:
                key = (row["name"], row["surname"], row["father_name"])
                student_keys.add(key)
                
                # ვინახავთ ბოლო საკონტაქტო მონაცემებს
                student_data[key]["info"]["phone"] = row["phone"]
                student_data[key]["info"]["email"] = row["email"]

            # 2. ვაგროვებთ თითოეული სტუდენტის აქტიურ კურსებს
            for name, surname, father_name in student_keys:
                key = (name, surname, father_name)
                history = self.db.get_student_history(name, surname, father_name)
                
                if history:
                    # ვამატებთ აქტიური კურსების დეტალებს
                    student_data[key]["active_courses"].extend(history)
            
            # ვფილტრავთ მხოლოდ მათ, ვისაც აქვს აქტიური კურსები
            active_students_keys = sorted([
                key for key, data in student_data.items() 
                if data["active_courses"]
            ])
            
            if not active_students_keys:
                print("❌ ამჟამად არ არის აქტიური სტუდენტები.")
                input("\nდააჭირეთ Enter-ს მენიუში დასაბრუნებლად...")
                return

            # სათაურების ბეჭდვა
            HEADER_LINE = (
                f"{'სახელი გვარი':<25} | {'მამის სახ.':<10} | {'მობილური':<9} | {'ელ-ფოსტა':<30} | "
                f"{'კურსის დასახელება':<30} | {'დრო/ჯგუფი':<35} | {'გადახდ.N':<10}"
            )
            SEPARATOR_LENGTH = len(HEADER_LINE)
            
            print(HEADER_LINE)
            print("-" * SEPARATOR_LENGTH)
            
            for name, surname, father_name in active_students_keys:
                key = (name, surname, father_name)
                data = student_data[key]
                
                phone = data["info"]["phone"]
                email = data["info"]["email"] 

                first_course = data["active_courses"][0]
                
                full_name = f"{name} {surname}"
                
                # პირველი ხაზი სრული მონაცემებით
                print(
                    f"{full_name:<25} | {father_name:<10} | {phone:<9} | {email:<30} | " 
                    f"{first_course['course_name']:<30} | "                             
                    f"{first_course['time_keys'].replace(';', ', '):<35} | "
                    f"{first_course['receipt_id']:<10}"
                )
                
                # დანარჩენი კურსები
                for course in data["active_courses"][1:]:
                    print(
                        f"{'':<25} | {'':<10} | {'':<9} | {'':<30} | " 
                        f"{course['course_name']:<30} | "
                        f"{course['time_keys'].replace(';', ', '):<35} | "
                        f"{course['receipt_id']:<10}"
                    )
                print("-" * SEPARATOR_LENGTH) # გამყოფი ხაზი სტუდენტებს შორის

            input("\nდააჭირეთ Enter-ს მენიუში დასაბრუნებლად...")

        
    # ============================
    # ადმინისტრაციული მენიუ
    # ============================
    def admin_reports_menu(self):
        while True:
            print("\n" * 3)
            print("=== 4. ადმინისტრაციული რეპორტები ===")
            print("1. კურსის შევსების რეპორტი")
            print("2. აქტიური სტუდენტების სია")
            print("3. უკან (მთავარ მენიუში)")
            
            cmd = input(">> აირჩიეთ მოქმედება: ").strip()
            
            if cmd == "1":
                self.generate_course_occupancy_report()
            elif cmd == "2":
                self.generate_active_students_report()
            elif cmd == "3":
                break
            else:
                print("არასწორი ბრძანება.")
                input("დააჭირეთ Enter-ს გასაგრძელებლად...")


# =========================================================
# 5. მთავარი მენიუ 
# =========================================================
def main():
    system = RegistrationSystem()
    
    while True:
        print("\n" * 3)
        print("=== სასწავლო ცენტრის მართვის სისტემა ===")

        print("1. კურსზე რეგისტრაცია")
        print("2. რეგისტრაციის რედაქტირება")
        print("3. რეპორტი") 
        print("4. გასვლა")
        
        cmd = input(">> აირჩიეთ მოქმედება: ").strip()
        
        if cmd == "1":
            system.register_process()
        elif cmd == "2":
            system.edit_registration()
        elif cmd == "3":
            system.admin_reports_menu() # ახალი ფუნქციის გამოძახება
        elif cmd == "4":
            print("ნახვამდის!")
            break
        else:
            print("არასწორი ბრძანება.")

if __name__ == "__main__":
    main()