import os
import csv
import bcrypt
import sqlite3

class DataConnection:
    def __init__(self, db_file='capstone.db'):
        self.connection = sqlite3.connect(db_file)
        self.cursor = self.connection.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        table_exists = self.cursor.fetchone()
        if not table_exists:
            # user table
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users(
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                password TEXT,
                first_name TEXT,
                last_name TEXT,
                is_active INTEGER,
                is_admin TEXT,
                date_created TEXT DEFAULT CURRENT_TIMESTAMP)''')
            self.connection.commit()

            # Create the Assessments table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS Assessments (
                    user_id INTEGER,
                    assessment_id INTEGER PRIMARY KEY,
                    assessment_score FLOAT,
                    assessment_weight INTEGER,
                    is_active INTEGER,
                    date_created TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES Users(user_id))''')
            self.connection.commit()

            # Create the Competency table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS Competency (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    competency_value FLOAT,
                    date_created TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)''')
            self.connection.commit()

    def execute_query(self, query, params=None):
        if params is None:
            params = ()
        normalized_query = query.strip().upper()
        is_select_query = normalized_query.startswith('SELECT')

        try:
            if is_select_query:
                self.cursor.execute(query, params)
                result = self.cursor.fetchall()
                columns = [col[0] for col in self.cursor.description]
                result_dicts = [dict(zip(columns, row)) for row in result]

                return result_dicts
            else:
                self.cursor.execute(query, params)
                self.connection.commit()
                return self.cursor.rowcount
        except Exception as e:
            print(f"Error executing query: {e}")
            self.connection.rollback()
            return None

class CsvManagement:
    @staticmethod
    def read_csv(file_path):
        with open(file_path, 'r') as file:
            return list(csv.DictReader(file))

    @staticmethod
    def get_csv_file_path(file_name):
        script_dir = os.path.dirname(__file__)
        csv_folder = os.path.join(script_dir, 'csv')
        os.makedirs(csv_folder, exist_ok=True)
        return os.path.join(csv_folder, file_name)

    @staticmethod 
    def get_csv_file_list():
        script_dir = os.path.dirname(__file__)
        csv_folder = os.path.join(script_dir, 'csv')
        csv_files = [f for f in os.listdir(csv_folder) if f.endswith('.csv')]
        return {i + 1: csv_file for i, csv_file in enumerate(csv_files)}

    @staticmethod
    def import_csv_data_into_database(db_connection, csv_file_path):
        csv_data = CsvManagement.read_csv(csv_file_path)
        if csv_data:
            CsvManagement.import_csv_data(db_connection, csv_data)
            print(f"CSV data from '{csv_file_path}' imported into the database.")
        else:
            print(f"No data found in the CSV file: '{csv_file_path}'.")

    @staticmethod
    def import_csv_data(db_connection, csv_data):
        for row in csv_data:
            username = row.get('username')
            first_name = row.get('first_name')
            last_name = row.get('last_name')
            is_active = row.get('is_active')
            is_admin = row.get('is_admin', 'n')
            password = bcrypt.hashpw(username.encode('utf-8'), bcrypt.gensalt())
            db_connection.cursor.execute('''
                INSERT INTO users (username, password, first_name, last_name, is_active, is_admin) 
                VALUES (?, ?, ?, ?, ?, ?)''',
                (username, password, first_name, last_name, is_active, is_admin))
        db_connection.connection.commit()

    @staticmethod
    def import_assignment_csv(db_connection, csv_file_path):
        if os.path.exists(csv_file_path):
            csv_data = CsvManagement.read_csv(csv_file_path)
            for row in csv_data:
                user_id = int(row.get('user_id'))
                assessment_id = int(row.get('assessment_id'))
                assessment_score_str = row.get('assessment_score')
                assessment_weight = int(row.get('assessment_weight'))
                is_active = int(row.get('is_active'))
                date_created = row.get('date_created')
                try:
                    assignment_score = float(assessment_score_str)
                    if 0 <= assignment_score <= 100:
                        user_info = db_connection.execute_query("SELECT * FROM users WHERE user_id = ?", (user_id,))
                        if user_info:
                            db_connection.cursor.execute('''
                                INSERT INTO Assessments (user_id, assessment_id, assessment_score, assessment_weight, is_active, date_created)
                                VALUES (?, ?, ?, ?, ?, ?)''', (user_id, assessment_id, assignment_score, assessment_weight, is_active, date_created))
                            db_connection.connection.commit()
                            print(f"Assignment added successfully for user with ID {user_id}.")
                        else:
                            print(f"User with ID {user_id} not found. Skipping assignment.")
                    else:
                        print("Invalid input. Please enter a number between 0 and 100.")
                except ValueError:
                    print("Invalid input. Please enter a valid number.")
        else:
            print(f"CSV file not found: {csv_file_path}")

    @staticmethod
    def export_users_to_csv(db_connection, file_name='users_export.csv'):
        users = db_connection.execute_query("SELECT * FROM users")
        if users:
            file_path = CsvManagement.get_csv_file_path(file_name)
            with open(file_path, 'w', newline='') as file:
                fieldnames = users[0].keys()
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(users)
            print(f"User data exported to '{file_path}' successfully.")
        else:
            print("No user data found for export.")

    @staticmethod
    def export_assessments_to_csv(db_connection, file_name='assessments_export.csv'):
        assessments = db_connection.execute_query("SELECT * FROM Assessments")
        if assessments:
            file_path = CsvManagement.get_csv_file_path(file_name)
            with open(file_path, 'w', newline='') as file:
                fieldnames = assessments[0].keys()
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(assessments)
            print(f"Assessment data exported to '{file_path}' successfully.")
        else:
            print("No assessment data found for export.")

    @staticmethod
    def export_competencies_to_csv(db_connection, file_name='competencies_export.csv'):
        competencies = db_connection.execute_query("SELECT * FROM Competencies")
        if competencies:
            file_path = CsvManagement.get_csv_file_path(file_name)
            with open(file_path, 'w', newline='') as file:
                fieldnames = competencies[0].keys()
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(competencies)
            print(f"Competency data exported to '{file_path}' successfully.")
        else:
            print("No competency data found for export.")  

class UserAuth:
    @staticmethod
    def register_user():
        db_connection = DataConnection()
        while True:
            username = input("Enter your username: ")
            if not username:
                print("Username cannot be empty. Please enter a valid username.")
            else:
                existing_user = db_connection.execute_query("SELECT * FROM users WHERE username = ?", (username,))
                if existing_user:
                    print("Username already exists. Please choose a different username.")
                else:
                    break
        while True:
            password = input("Enter your password: ")
            if not password:
                print("Password cannot be empty. Please enter a valid password.")
            else:
                break
        f_name_input = input("What is your first name? ")
        l_name_input = input("What is your last name? ")
        while True:
            is_usr_active = input("Is this user active? 1/0 ")
            if is_usr_active in ('1', '0'):
                break
            else:
                print("Invalid input. Please enter '1' for active or '0' for inactive.")
        while True:
            is_usr_admin = input('Is this user an Admin? (y/n): ').lower()
            if is_usr_admin in ('y', 'n'):
                break
            else:
                print("Invalid input. Please enter 'y' or 'n'.")

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        user_data = {'username': username, 'password': hashed_password}
        print(f"User '{username}' registered successfully!")

        db_connection.execute_query(
            '''INSERT INTO users (username, password, first_name, last_name, is_active, is_admin) 
               VALUES (?, ?, ?, ?, ?, ?)''',
            (username, hashed_password, f_name_input, l_name_input, is_usr_active, is_usr_admin)
        )

        return user_data

    @staticmethod
    def login_user():
        db_connection = DataConnection()
        username = input("Enter your username: ")
        password = input("Enter your password: ")
        # Retrieve user information from the database for the given username
        result = db_connection.execute_query("SELECT * FROM users WHERE username = ?", (username,))
        if result:
            stored_password = result[0]['password']
            # Check if the entered password matches the stored hashed password
            if bcrypt.checkpw(password.encode('utf-8'), stored_password):
                print(f"Welcome back, {username}!")
                return {'username': username, 'is_admin': result[0]['is_admin']}
            else:
                print("Invalid login credentials.")
        else:
            print("User not found.")

    @staticmethod
    def decrypt_password(hashed_password):
        return '*' * 8

class UserActions:
    @staticmethod
    def view_all_users():
        db_connection = DataConnection()
        result = db_connection.execute_query("SELECT * FROM users")
        return result

    @staticmethod
    def _search_users(data_connection, search_term=None):
        while True:
            if search_term is None:
                search_term = input("Enter the username, first name, or last name to search: ")

            query = """SELECT user_id, username, first_name, last_name FROM users WHERE first_name LIKE ? OR last_name LIKE ? """
            result = data_connection.execute_query(query, ('%' + search_term + '%', '%' + search_term + '%'))
            if not result:
                print("No users found.")
                return []
            else:
                print("Search results:")
                for i, user in enumerate(result, 1):
                    print(f"{i}. {user['username']} - {user['first_name']} {user['last_name']}")
                selected_index = int(input("Select a user to update (enter the UserId) or '0' to exit: ")) - 1
                if selected_index == -1:
                    print("Exiting user update menu.")
                    return [] 
                if 0 <= selected_index < len(result):
                    selected_user = result[selected_index]
                    print(f"Selected user: {selected_user['username']} - {selected_user['first_name']} {selected_user['last_name']}")
                    return [selected_user]
                else:
                    print("Invalid selection.")
                    return []

    @staticmethod
    def update_user(db_connection):
        while True:
            search_term = input("Enter the first name or last name to search (or '0' to exit): ")
            if search_term == '0':
                print("Exiting user update menu.")
                break
            selected_user = UserActions._search_users(db_connection, search_term)
            if not selected_user:
                print("No users found.")
                continue
            
            print("User Options:")
            print("[1.] Update username")
            print("[2.] Update password")
            print("[3.] Update first name")
            print("[4.] Update last name")
            print("[5.] Update active status")
            print("[6.] Update admin status")
            print("[0.] Exit and go back to user management menu")
            choice = input("Enter your choice (0-6): ")

            if choice == '0':
                print("Exiting user update menu.")
                break
            elif choice == '1':
                new_username = input("Enter the new username: ")
                db_connection.execute_query("UPDATE users SET username = ? WHERE user_id = ?", (new_username, selected_user['user_id']))
                print("Username updated successfully.")
            elif choice == '2':
                new_password = input("Enter the new password: ")
                hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
                db_connection.execute_query("UPDATE users SET password = ? WHERE user_id = ?", (hashed_password, selected_user['user_id']))
                print("Password updated successfully.")
            elif choice == '3':
                new_first_name = input("Enter the new first name: ")
                db_connection.execute_query("UPDATE users SET first_name = ? WHERE user_id = ?", (new_first_name, selected_user['user_id']))
                print("First name updated successfully.")
            elif choice == '4':
                new_last_name = input("Enter the new last name: ")
                db_connection.execute_query("UPDATE users SET last_name = ? WHERE user_id = ?", (new_last_name, selected_user['user_id']))
                print("Last name updated successfully.")
            elif choice == '5':
                new_active_status = input("Enter the new active status (1 or 0): ")
                db_connection.execute_query("UPDATE users SET is_active = ? WHERE user_id = ?", (new_active_status, selected_user['user_id']))
                print("Active status updated successfully.")
            elif choice == '6':
                new_admin_status = input("Enter the new admin status (y or n): ").lower()
                db_connection.execute_query("UPDATE users SET is_admin = ? WHERE user_id = ?", (new_admin_status, selected_user['user_id']))
                print("Admin status updated successfully.")
            else:
                print("Invalid choice.")

    @staticmethod
    def format_user_data(user):
        print(f"User ID: {user['user_id']}")
        print(f"Username: {user['username']}")
        print(f"First Name: {user['first_name']}")
        print(f"Last Name: {user['last_name']}")
        print(f"Password: {UserAuth.decrypt_password(user['password'])}")
        print(f"Active: {'Yes' if user['is_active'] == 1 else 'No'}")
        print(f"Admin: {'Yes' if user['is_admin'] == 'y' else 'No'}")

    @staticmethod
    def delete_user(data_connection, user_id_to_delete):
        try:
            delete_query = "DELETE FROM users WHERE user_id = ?"
            data_connection.execute_query(delete_query, (user_id_to_delete,))
            print(f"User with ID {user_id_to_delete} has been deleted successfully.")
        except Exception as e:
            print(f"Error deleting user: {e}")

class AssignmentManagement:
    @staticmethod
    def add_assignment(db_connection, user_id, assignment_score):
        db_connection.cursor.execute('''
            INSERT INTO Assessments (user_id, assessment_score, assessment_weight, is_active)
            VALUES (?, ?, 1, 1)''', (user_id, assignment_score))
        db_connection.connection.commit()
        print(f"Assignment added successfully for user with ID {user_id}.")

    @staticmethod
    def add_assignment_manually():
        db_connection = DataConnection()
        search_term = input("Enter the first name or last name to search: ")
        result = UserActions._search_users(db_connection, search_term)
        if result is not None and result:
            selected_user = result[0]
            print(f"Selected user: {selected_user['username']} - {selected_user['first_name']} {selected_user['last_name']}")
            assignment_score_str = input(f"How did the user score? (?/100): ")
            try:
                assignment_score = float(assignment_score_str)
                if 0 <= assignment_score <= 100:
                    AssignmentManagement.add_assignment(db_connection, selected_user['user_id'], assignment_score)
                else:
                    print("Invalid input. Please enter a number between 0 and 100.")
            except ValueError:
                print("Invalid input. Please enter a valid number.")
        else:
            print("No users found.")
            
class Reports:
    @staticmethod
    def calculate_competency(data_connection, search_term=None, selected_user_id=None):
        if search_term is not None:
            # Calculate competency for a specific user
            result = UserActions._search_users(data_connection, str(search_term))
            if result:
                selected_user = result[0]
            else:
                print(f"User '{search_term}' not found.")
                return
        elif selected_user_id:
            selected_user = UserActions.get_user_by_id(data_connection, selected_user_id)
            if not selected_user:
                print(f"User with ID {selected_user_id} not found.")
                return
        else:
            # Calculate competency for all users
            all_users = UserActions.view_all_users()
            if not all_users:
                print("No users found.")
                return
            selected_user = None  # No need to ask for user input

        if selected_user is not None:
            assessments = Reports._get_user_assessments(data_connection, selected_user['user_id'])
            Reports._print_competency_result(selected_user, assessments)

    @staticmethod
    def _get_user_assessments(data_connection, user_id):
        assessment_data_query = "SELECT assessment_score, assessment_weight FROM Assessments WHERE user_id = ? AND is_active = 1"
        return data_connection.execute_query(assessment_data_query, (user_id,))

    @staticmethod
    def calculate_competency_for_all_users(db_connection):
        all_users = UserActions.view_all_users()

        if not all_users:
            print("No users found.")
            return

        competency_reports = []

        for user in all_users:
            assessments = Reports._get_user_assessments(db_connection, user['user_id'])
            competency_value = Reports.calculate_competency(db_connection, selected_user_id=user['user_id'])
            assessment_ids = Reports.get_assessment_ids(db_connection, user['user_id'])
            competency_date_query = "SELECT date_created FROM Competency WHERE user_id = ?"
            competency_date = db_connection.execute_query(competency_date_query, (user['user_id'],))[0]['date_created']
            print(f"User: {user['first_name']} {user['last_name']}")
            print(f"Assessment IDs: {assessment_ids}")
            print(f"Competency Score: {competency_value}")
            print(f"Competency Date: {competency_date}")
            print("-" * 30)
            report_data = {
                'user': f"{user['first_name']} {user['last_name']}",
                'assessment_ids': assessment_ids,
                'competency_score': competency_value,
                'competency_date': competency_date
            }

            competency_reports.append(report_data)
        return competency_reports

    @staticmethod
    def _print_competency_result(user, assessments):
        if assessments:
            total_weighted_score = sum(assessment['assessment_score'] * assessment['assessment_weight'] for assessment in assessments)
            total_weight = sum(assessment['assessment_weight'] for assessment in assessments)
            if total_weight > 0:
                competency_score = total_weighted_score / total_weight
                print(f"Competency calculated successfully for user: {user['username']} - {user['first_name']} {user['last_name']}")
                print(f"Competency Score: {competency_score}")
            else:
                print(f"No active assessments found for the user: {user['username']} - {user['first_name']} {user['last_name']}")
        else:
            print(f"No assessments found for the user: {user['username']} - {user['first_name']} {user['last_name']}")

    @staticmethod
    def run_user_assignment_scores_report(db_connection):
        search_term = input("Enter the first name or last name to search: ")
        result = UserActions._search_users(db_connection, search_term)
        if not result:
            print("No users found.")
            return
        print("Search results:")
        for i, user in enumerate(result, 1):
            print(f"{i}. {user['username']} - {user['first_name']} {user['last_name']}")
        selected_index = int(input("Select a user to view assignment scores (enter the UserId): ")) - 1
        if 0 <= selected_index < len(result):
            selected_user = result[selected_index]
            print(f"Assignment scores for user: {selected_user['username']} - {selected_user['first_name']} {selected_user['last_name']}")
            # Pass the db_connection to the method
            assignment_scores = Reports.user_assignment_scores(selected_user['user_id'], db_connection)
            if assignment_scores:
                for assignment in assignment_scores:
                    print(f"Assignment ID: {assignment['assessment_id']}")
                    print(f"Score: {assignment['assessment_score']}")
                    print("-" * 30)
            else:
                print("No assignment scores found for the user.")
        else:
            print("Invalid selection.")
    
    @staticmethod
    def user_assignment_scores(user_id, db_connection):
        assignment_data_query = "SELECT assessment_id, assessment_score FROM Assessments WHERE user_id = ?"
        assignment_scores = db_connection.execute_query(assignment_data_query, (user_id,))
        return assignment_scores
    
    @staticmethod
    def generate_and_export_competency_report(db_connection, file_name='competency_report.csv'):
        competencies = db_connection.execute_query("SELECT * FROM Competency")
        if competencies:
            for user in competencies:
                competency_value = Reports.calculate_competency_for_all_users(db_connection, user['user_id'])
                db_connection.execute_query("""
                    INSERT INTO CompetencyReport (user_id, username, competency_value)
                    VALUES (?, ?, ?)
                """, (user['user_id'], user['username'], competency_value))

            print("Competency values stored in the CompetencyReport table.")
            file_path = CsvManagement.get_csv_file_path(file_name)
            Reports.export_competencies_to_csv_from_table(db_connection, 'CompetencyReport', file_path)
            print(f"Competency report exported to '{file_path}' successfully.")
        else:
            print("No users found for the report.")
    
class Menus:
    @staticmethod
    def login():
        db_connection = DataConnection()
        while True:
            print("Options:")
            print("[1.] Login")
            print("[2.] Create an account")
            print("[0.] Exit")
            choice = input("Enter your choice (1, 2, or 0.): ")

            if choice == '1':
                print('Please login')
                user_data = UserAuth.login_user()
                if user_data and user_data.get('is_admin') == 'y':
                    Menus.admin_menu(db_connection)
                elif user_data:
                    Menus.user_menu(db_connection, user_data)
            elif choice == '2':
                print('Create an account')
                registered_user = UserAuth.register_user()
            elif choice == '0':
                print('Exiting the program.')
                break
            else:
                print('Invalid choice. Please enter 1, 2, or 3.')

    @staticmethod
    def admin_menu(db_connection):
        while True:
            print("Admin Menu:")
            print("[1.] User Management")
            print("[2.] Assessment Management")
            print("[3.] Reports")
            print("[0.] Exit")

            admin_choice = input("Enter your choice (1, 2, 3, or 0): ")

            if admin_choice == '1':
                Menus.user_management_submenu(db_connection)
            elif admin_choice == '2':
                Menus.assessment_management_submenu(db_connection)
            elif admin_choice == '3':
                Menus.reports_submenu(db_connection)
            elif admin_choice == '0':
                print('Exiting admin menu.')
                break
            else:
                print('Invalid choice. Please enter 1, 2, 3, 4, or 0.')

    @staticmethod
    def export_csv_submenu(db_connection):
        while True:
            print("Export to CSV:")
            print("[1.] Export Users")
            print("[2.] Export Assessments")
            print("[3.] Export Competencies")
            print("[0.] Back to Admin Menu")

            export_choice = input("Enter your choice (1, 2, 3, or 0): ")
            if export_choice == '1':
                CsvManagement.export_users_to_csv(db_connection)
            elif export_choice == '2':
                CsvManagement.export_assessments_to_csv(db_connection)
            elif export_choice == '3':
                CsvManagement.export_competencies_to_csv(db_connection)
            elif export_choice == '0':
                print('Returning to Admin Menu.')
                break
            else:
                print('Invalid choice. Please enter 1, 2, 3, or 0.')

    @staticmethod
    def reports_submenu(db_connection):
        while True:
            print("Reports:")
            print("[1.] Calculate Competency")
            print("[2.] User Assignment Scores")
            print("[3.] Calculate Competency for All Users")
            print("[4.] Export to CSV")
            print("[0.] Back to Admin Menu")

            reports_choice = input("Enter your choice (1, 2, 3, 4, 5, or 0): ")
            if reports_choice == '1':
                Menus.calculate_competency_menu(db_connection)
            elif reports_choice == '2':
                Reports.run_user_assignment_scores_report(db_connection)
            elif reports_choice == '3':
                Reports.calculate_competency_for_all_users(db_connection)
            elif reports_choice == '4':
                Menus.export_csv_submenu(db_connection)
            elif reports_choice == '0':
                print('Returning to Admin Menu.')
                break
            else:
                print('Invalid choice. Please enter 1, 2, 3, 4, or 0.')

    @staticmethod
    def calculate_competency_menu(db_connection):
        user_choice = input("Do you want to calculate competency for a specific user? \n1. for yes \n2. for no: ")
        if user_choice == '1':
            search_term = input("Enter the username for which to calculate competency: ")
            Reports.calculate_competency(db_connection, search_term)
        else:
            Reports.calculate_competency(db_connection)

    @staticmethod
    def export_pdf_submenu(db_connection):
        while True:
            print("Export to PDF:")
            print("[1.] Export Competency Report")
            print("[0.] Back to Reports Menu")

            pdf_export_choice = input("Enter your choice (1 or 0): ")
            if pdf_export_choice == '1':
                Reports.export_competency_to_pdf(db_connection)
            elif pdf_export_choice == '0':
                print('Returning to Reports Menu.')
                break
            else:
                print('Invalid choice. Please enter 1, 0.')

    @staticmethod
    def user_management_submenu(db_connection):
        data_connection = DataConnection()
        while True:
            print("User Management:")
            print("[1.] Create a new user")
            print("[2.] Update user information")
            print("[3.] Delete a user")
            print("[4.] View all users")
            print("[0.] Back to Admin Menu")
            
            user_management_choice = input("Enter your choice (1, 2, 3, 4, or 0): ")
            if user_management_choice == '1':
                UserAuth.register_user()
            elif user_management_choice == '2':
                UserActions.update_user(db_connection)
            elif user_management_choice == '3':
                try:
                    search_term = input("Enter the username, first name, or last name to search for the user to delete: ")
                    selected_user = UserActions._search_users(data_connection, search_term)
                    if selected_user:
                        user_id_to_delete = selected_user['user_id']
                        UserActions.delete_user(data_connection, user_id_to_delete)
                        print(f"User with ID {user_id_to_delete} has been deleted successfully.")
                    else:
                        print("User not found.")
                except Exception as e:
                    print(f"Error deleting user: {e}")
            elif user_management_choice == '4':
                all_users = UserActions.view_all_users()
                if all_users:
                    print("All Users:")
                    for user in all_users:
                        UserActions.format_user_data(user)
                        print("-" * 30)
                else:
                    print("No users found.")
            elif user_management_choice == '0':
                print('Returning to Admin Menu.')
                break
            else:
                print('Invalid choice. Please enter 1, 2, 3, 4, or 5.')

    @staticmethod
    def assessment_management_submenu(db_connection):
        while True:
            print("Assessment Management:")
            print("[1.] Manually add assignment")
            print("[2.] CSV Management")
            print("[0.] Back to Admin Menu")
            
            assessment_management_choice = input("Enter your choice (1, 2, or 3): ")
            if assessment_management_choice == '1':
                AssignmentManagement.add_assignment_manually()
            elif assessment_management_choice == '2':
                Menus.csv_management_submenu(db_connection)
            elif assessment_management_choice == '0':
                print('Returning to Admin Menu.')
                break
            else:
                print('Invalid choice. Please enter 1, 2, or 0.')
            
    @staticmethod
    def csv_management_submenu(db_connection):
        while True:
            print("CSV Management:")
            print("[1.] Upload Users from a CSV")
            print("[2.] Upload assignments from a CSV")
            print("[0.] Back to Admin Menu")

            csv_choice = input("Enter your choice (1, 2, or 3): ")
            if csv_choice == '1':
                csv_file_name = input("Enter the CSV file name (e.g., data.csv): ")
                csv_file_path = CsvManagement.get_csv_file_path(csv_file_name)
                CsvManagement.import_csv_data_into_database(db_connection, csv_file_path)
            elif csv_choice == '2':
                csv_file_name = input("Enter the CSV file name with assignment data: ")
                csv_file_path = CsvManagement.get_csv_file_path(csv_file_name)
                CsvManagement.import_assignment_csv(db_connection, csv_file_path)
            elif csv_choice == '0':
                print('Returning to Admin Menu.')
                break
            else:
                print('Invalid choice. Please enter 1, 2, or 0.')

    @staticmethod
    def user_menu(db_connection, user_data):
        while True:
            print("User Menu:")
            print("[1.] View your data")
            print("[2.] Update your data")
            print("[0.] Exit")

            user_choice = input("Enter your choice (1, 2, or 0.): ")
            if user_choice == '1':
                UserActions.view_user_data()
            elif user_choice == '2':
                UserActions.update_user_data()
            elif user_choice == '0':
                print('Exiting user menu.')
                break
            else:
                print('Invalid choice. Please enter 1, 2, or 0.')
    
def main():
    Menus.login()

if __name__ == "__main__":
    main()
