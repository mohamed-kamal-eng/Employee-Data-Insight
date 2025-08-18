import sqlite3
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import datetime
from typing import List, Tuple, Optional
import re

class EmployeeManagementSystem:
    def __init__(self):
        self.root = tk.Tk()
        self.db_file = self._find_database()
        self.current_user = None
        self.setup_styles()
        self.setup_main_window()
        
    def _find_database(self) -> str:
        """Find the database file in the current directory"""
        current_folder = os.path.dirname(os.path.abspath(__file__))
        
        for file in os.listdir(current_folder):
            if file.startswith("employees_db") and file.endswith(".db"):
                return os.path.join(current_folder, file)
        
        # If no database found, create a sample one or ask user to select
        messagebox.showwarning("Database Not Found", 
                             "No employee database found. Please select your database file.")
        db_path = filedialog.askopenfilename(
            title="Select Employee Database",
            filetypes=[("SQLite Database", "*.db"), ("All Files", "*.*")]
        )
        
        if not db_path:
            raise FileNotFoundError("No database file selected!")
        return db_path
    
    def setup_styles(self):
        """Configure modern styling"""
        style = ttk.Style()
        
        # Configure colors and fonts
        self.colors = {
            'primary': '#2E3440',
            'secondary': '#3B4252', 
            'accent': '#5E81AC',
            'success': '#A3BE8C',
            'warning': '#EBCB8B',
            'danger': '#BF616A',
            'light': '#ECEFF4',
            'dark': '#2E3440',
            'background': '#F8F9FA'
        }
        
        # Configure ttk styles
        style.theme_use('clam')
        style.configure('Title.TLabel', font=('Arial', 18, 'bold'), foreground=self.colors['primary'])
        style.configure('Heading.TLabel', font=('Arial', 14, 'bold'), foreground=self.colors['secondary'])
        style.configure('Custom.Treeview', font=('Arial', 10))
        style.configure('Custom.Treeview.Heading', font=('Arial', 11, 'bold'))
        
    def setup_main_window(self):
        """Setup main window properties"""
        self.root.title("🏢 Employee Management System v2.0")
        self.root.geometry("1200x800")
        self.root.configure(bg=self.colors['background'])
        self.root.minsize(900, 600)
        
        # Center the window
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (1200 // 2)
        y = (self.root.winfo_screenheight() // 2) - (800 // 2)
        self.root.geometry(f"1200x800+{x}+{y}")
        
    def run_query(self, query: str, params: tuple = ()) -> List[Tuple]:
        """Execute database query with error handling"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            return rows
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Error executing query: {str(e)}")
            return []
    
    def is_manager(self, emp_no: int) -> bool:
        """Check if employee is a manager"""
        query = "SELECT COUNT(*) FROM dept_manager WHERE emp_no = ?"
        result = self.run_query(query, (emp_no,))
        return result[0][0] > 0 if result else False
    
    def get_employee(self, emp_no: int) -> Optional[Tuple]:
        """Get employee information"""
        query = """
            SELECT emp_no, first_name, last_name, gender, birth_date, hire_date 
            FROM employees WHERE emp_no = ?
        """
        result = self.run_query(query, (emp_no,))
        return result[0] if result else None
    
    def get_employee_details(self, emp_no: int) -> dict:
        """Get comprehensive employee details"""
        query = """
            SELECT 
                e.emp_no, e.first_name, e.last_name, e.gender, 
                e.birth_date, e.hire_date,
                t.title,
                s.salary,
                d.dept_name,
                dm.from_date as manager_from
            FROM employees e
            LEFT JOIN titles t ON e.emp_no = t.emp_no AND t.to_date = '9999-01-01'
            LEFT JOIN salaries s ON e.emp_no = s.emp_no AND s.to_date = '9999-01-01'
            LEFT JOIN dept_emp de ON e.emp_no = de.emp_no AND de.to_date = '9999-01-01'
            LEFT JOIN departments d ON de.dept_no = d.dept_no
            LEFT JOIN dept_manager dm ON e.emp_no = dm.emp_no AND dm.to_date = '9999-01-01'
            WHERE e.emp_no = ?
        """
        result = self.run_query(query, (emp_no,))
        if result:
            row = result[0]
            return {
                'emp_no': row[0],
                'first_name': row[1],
                'last_name': row[2],
                'gender': row[3],
                'birth_date': row[4],
                'hire_date': row[5],
                'title': row[6] or 'N/A',
                'salary': f"${row[7]:,}" if row[7] else 'N/A',
                'department': row[8] or 'N/A',
                'is_manager': bool(row[9])
            }
        return None
    
    def get_all_departments(self) -> List[str]:
        """Get all department names"""
        result = self.run_query("SELECT dept_name FROM departments ORDER BY dept_name")
        return [dept[0] for dept in result]
    
    def get_employees_by_department(self, dept_name: str) -> List[Tuple]:
        """Get employees in a specific department"""
        query = """
            SELECT 
                e.emp_no, e.first_name, e.last_name, 
                t.title, s.salary, e.hire_date,
                CASE WHEN dm.emp_no IS NOT NULL THEN 'Yes' ELSE 'No' END as is_manager
            FROM employees e
            JOIN dept_emp de ON e.emp_no = de.emp_no AND de.to_date = '9999-01-01'
            JOIN departments d ON de.dept_no = d.dept_no
            LEFT JOIN titles t ON e.emp_no = t.emp_no AND t.to_date = '9999-01-01'
            LEFT JOIN salaries s ON e.emp_no = s.emp_no AND s.to_date = '9999-01-01'
            LEFT JOIN dept_manager dm ON e.emp_no = dm.emp_no AND dm.to_date = '9999-01-01'
            WHERE d.dept_name = ?
            ORDER BY s.salary DESC, e.hire_date
        """
        return self.run_query(query, (dept_name,))
    
    def search_employees(self, search_term: str) -> List[Tuple]:
        """Advanced employee search"""
        if not search_term.strip():
            return []
            
        # Check if search term is numeric (employee number)
        if search_term.isdigit():
            query = """
                SELECT e.emp_no, e.first_name, e.last_name, e.gender, 
                       e.birth_date, e.hire_date, t.title, s.salary, d.dept_name
                FROM employees e
                LEFT JOIN titles t ON e.emp_no = t.emp_no AND t.to_date = '9999-01-01'
                LEFT JOIN salaries s ON e.emp_no = s.emp_no AND s.to_date = '9999-01-01'
                LEFT JOIN dept_emp de ON e.emp_no = de.emp_no AND de.to_date = '9999-01-01'
                LEFT JOIN departments d ON de.dept_no = d.dept_no
                WHERE e.emp_no = ?
            """
            return self.run_query(query, (int(search_term),))
        
        # Name search
        terms = search_term.strip().lower().split()
        if len(terms) == 1:
            pattern = f"%{terms[0]}%"
            query = """
                SELECT e.emp_no, e.first_name, e.last_name, e.gender, 
                       e.birth_date, e.hire_date, t.title, s.salary, d.dept_name
                FROM employees e
                LEFT JOIN titles t ON e.emp_no = t.emp_no AND t.to_date = '9999-01-01'
                LEFT JOIN salaries s ON e.emp_no = s.emp_no AND s.to_date = '9999-01-01'
                LEFT JOIN dept_emp de ON e.emp_no = de.emp_no AND de.to_date = '9999-01-01'
                LEFT JOIN departments d ON de.dept_no = d.dept_no
                WHERE LOWER(e.first_name) LIKE ? OR LOWER(e.last_name) LIKE ?
                ORDER BY e.first_name, e.last_name
                LIMIT 100
            """
            return self.run_query(query, (pattern, pattern))
        else:
            first_pattern = f"%{terms[0]}%"
            last_pattern = f"%{terms[1]}%"
            query = """
                SELECT e.emp_no, e.first_name, e.last_name, e.gender, 
                       e.birth_date, e.hire_date, t.title, s.salary, d.dept_name
                FROM employees e
                LEFT JOIN titles t ON e.emp_no = t.emp_no AND t.to_date = '9999-01-01'
                LEFT JOIN salaries s ON e.emp_no = s.emp_no AND s.to_date = '9999-01-01'
                LEFT JOIN dept_emp de ON e.emp_no = de.emp_no AND de.to_date = '9999-01-01'
                LEFT JOIN departments d ON de.dept_no = d.dept_no
                WHERE LOWER(e.first_name) LIKE ? AND LOWER(e.last_name) LIKE ?
                ORDER BY e.first_name, e.last_name
                LIMIT 100
            """
            return self.run_query(query, (first_pattern, last_pattern))
    
    def get_department_stats(self, dept_name: str) -> dict:
        """Get department statistics"""
        query = """
            SELECT 
                COUNT(*) as total_employees,
                AVG(s.salary) as avg_salary,
                MAX(s.salary) as max_salary,
                MIN(s.salary) as min_salary,
                COUNT(DISTINCT dm.emp_no) as managers_count
            FROM employees e
            JOIN dept_emp de ON e.emp_no = de.emp_no AND de.to_date = '9999-01-01'
            JOIN departments d ON de.dept_no = d.dept_no
            LEFT JOIN salaries s ON e.emp_no = s.emp_no AND s.to_date = '9999-01-01'
            LEFT JOIN dept_manager dm ON e.emp_no = dm.emp_no AND dm.to_date = '9999-01-01'
            WHERE d.dept_name = ?
        """
        result = self.run_query(query, (dept_name,))
        if result:
            row = result[0]
            return {
                'total_employees': row[0],
                'avg_salary': f"${row[1]:,.0f}" if row[1] else 'N/A',
                'max_salary': f"${row[2]:,}" if row[2] else 'N/A',
                'min_salary': f"${row[3]:,}" if row[3] else 'N/A',
                'managers_count': row[4]
            }
        return {}
    
    def clear_window(self):
        """Clear all widgets from the window"""
        for widget in self.root.winfo_children():
            widget.destroy()
    
    def create_header(self, parent, title: str, subtitle: str = ""):
        """Create a styled header"""
        header_frame = tk.Frame(parent, bg=self.colors['primary'], height=80)
        header_frame.pack(fill='x', pady=(0, 20))
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(
            header_frame, text=title, 
            font=('Arial', 20, 'bold'), 
            fg='white', bg=self.colors['primary']
        )
        title_label.pack(pady=(15, 5))
        
        if subtitle:
            subtitle_label = tk.Label(
                header_frame, text=subtitle,
                font=('Arial', 12), 
                fg='#D8DEE9', bg=self.colors['primary']
            )
            subtitle_label.pack()
    
    def show_login(self):
        """Display login screen with modern styling"""
        self.clear_window()
        
        # Main container
        main_frame = tk.Frame(self.root, bg=self.colors['background'])
        main_frame.pack(expand=True, fill='both')
        
        # Login card
        login_frame = tk.Frame(
            main_frame, bg='white', 
            relief='raised', bd=0,
            padx=40, pady=40
        )
        login_frame.place(relx=0.5, rely=0.5, anchor='center')
        
        # Add shadow effect
        shadow_frame = tk.Frame(
            main_frame, bg='#E0E0E0',
            height=login_frame.winfo_reqheight() + 4,
            width=login_frame.winfo_reqwidth() + 4
        )
        
        # Title
        title_label = tk.Label(
            login_frame, text="🏢 Employee Portal",
            font=('Arial', 24, 'bold'),
            fg=self.colors['primary'], bg='white'
        )
        title_label.pack(pady=(0, 30))
        
        # Employee number input
        tk.Label(
            login_frame, text="Employee Number:",
            font=('Arial', 14), fg=self.colors['secondary'], bg='white'
        ).pack(pady=(0, 10))
        
        emp_entry = tk.Entry(
            login_frame, font=('Arial', 14), width=20,
            relief='solid', bd=1
        )
        emp_entry.pack(pady=(0, 20))
        emp_entry.focus()
        
        def attempt_login():
            emp_no_str = emp_entry.get().strip()
            
            if not emp_no_str:
                messagebox.showerror("Error", "Please enter your employee number!")
                return
                
            if not emp_no_str.isdigit():
                messagebox.showerror("Error", "Employee number must be numeric!")
                return
            
            emp_no = int(emp_no_str)
            employee = self.get_employee(emp_no)
            
            if not employee:
                messagebox.showerror("Error", "Employee not found! Please check your employee number.")
                return
            
            self.current_user = self.get_employee_details(emp_no)
            
            if self.is_manager(emp_no):
                self.show_manager_dashboard()
            else:
                self.show_employee_dashboard()
        
        # Login button
        login_btn = tk.Button(
            login_frame, text="🔑 Login",
            font=('Arial', 14, 'bold'),
            bg=self.colors['accent'], fg='white',
            relief='flat', padx=30, pady=10,
            cursor='hand2', command=attempt_login
        )
        login_btn.pack(pady=10)
        
        # Bind Enter key
        emp_entry.bind('<Return>', lambda e: attempt_login())
        
        # Info label
        tk.Label(
            login_frame, text="Enter your employee number to access the system",
            font=('Arial', 10), fg=self.colors['secondary'], bg='white'
        ).pack(pady=(20, 0))
    
    def show_employee_dashboard(self):
        """Display employee dashboard"""
        self.clear_window()
        
        user = self.current_user
        self.create_header(
            self.root, 
            f"Welcome, {user['first_name']} {user['last_name']}! 👋",
            f"Employee #{user['emp_no']} • {user['title']} • {user['department']}"
        )
        
        # Main content
        content_frame = tk.Frame(self.root, bg=self.colors['background'])
        content_frame.pack(expand=True, fill='both', padx=20, pady=10)
        
        # Employee info cards
        info_frame = tk.Frame(content_frame, bg=self.colors['background'])
        info_frame.pack(fill='x', pady=(0, 20))
        
        # Personal info card
        personal_card = tk.LabelFrame(
            info_frame, text="📋 Personal Information",
            font=('Arial', 12, 'bold'), bg='white', fg=self.colors['primary']
        )
        personal_card.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        personal_info = [
            ("Employee ID:", user['emp_no']),
            ("Gender:", user['gender']),
            ("Birth Date:", user['birth_date']),
            ("Hire Date:", user['hire_date'])
        ]
        
        for label, value in personal_info:
            row_frame = tk.Frame(personal_card, bg='white')
            row_frame.pack(fill='x', padx=15, pady=5)
            tk.Label(row_frame, text=label, font=('Arial', 10, 'bold'), bg='white', anchor='w').pack(side='left')
            tk.Label(row_frame, text=str(value), font=('Arial', 10), bg='white', anchor='e').pack(side='right')
        
        # Job info card
        job_card = tk.LabelFrame(
            info_frame, text="💼 Job Information",
            font=('Arial', 12, 'bold'), bg='white', fg=self.colors['primary']
        )
        job_card.pack(side='right', fill='both', expand=True, padx=(10, 0))
        
        job_info = [
            ("Title:", user['title']),
            ("Department:", user['department']),
            ("Salary:", user['salary']),
            ("Manager Status:", "Yes" if user['is_manager'] else "No")
        ]
        
        for label, value in job_info:
            row_frame = tk.Frame(job_card, bg='white')
            row_frame.pack(fill='x', padx=15, pady=5)
            tk.Label(row_frame, text=label, font=('Arial', 10, 'bold'), bg='white', anchor='w').pack(side='left')
            tk.Label(row_frame, text=str(value), font=('Arial', 10), bg='white', anchor='e').pack(side='right')
        
        # Action buttons
        button_frame = tk.Frame(content_frame, bg=self.colors['background'])
        button_frame.pack(pady=20)
        
        logout_btn = tk.Button(
            button_frame, text="🚪 Logout",
            font=('Arial', 12, 'bold'),
            bg=self.colors['danger'], fg='white',
            relief='flat', padx=30, pady=10,
            cursor='hand2', command=self.show_login
        )
        logout_btn.pack()
    
    def show_manager_dashboard(self):
        """Display manager dashboard with enhanced features"""
        self.clear_window()
        
        user = self.current_user
        self.create_header(
            self.root,
            f"Manager Dashboard - {user['first_name']} {user['last_name']} 👔",
            f"Employee #{user['emp_no']} • {user['title']} • {user['department']}"
        )
        
        # Main content with notebook
        content_frame = tk.Frame(self.root, bg=self.colors['background'])
        content_frame.pack(expand=True, fill='both', padx=20, pady=10)
        
        notebook = ttk.Notebook(content_frame)
        notebook.pack(expand=True, fill='both')
        
        # Departments Tab
        self.create_departments_tab(notebook)
        
        # Employee Search Tab
        self.create_search_tab(notebook)
        
        # Analytics Tab
        self.create_analytics_tab(notebook)
        
        # Logout button
        logout_frame = tk.Frame(self.root, bg=self.colors['background'])
        logout_frame.pack(pady=10)
        
        logout_btn = tk.Button(
            logout_frame, text="🚪 Logout",
            font=('Arial', 12, 'bold'),
            bg=self.colors['danger'], fg='white',
            relief='flat', padx=30, pady=10,
            cursor='hand2', command=self.show_login
        )
        logout_btn.pack()
    
    def create_departments_tab(self, notebook):
        """Create departments management tab"""
        dept_frame = tk.Frame(notebook, bg='white')
        notebook.add(dept_frame, text="🏢 Departments")
        
        # Controls frame
        controls_frame = tk.Frame(dept_frame, bg='white')
        controls_frame.pack(fill='x', padx=20, pady=10)
        
        tk.Label(
            controls_frame, text="Select Department:",
            font=('Arial', 12, 'bold'), bg='white'
        ).pack(side='left', padx=(0, 10))
        
        dept_var = tk.StringVar()
        dept_dropdown = ttk.Combobox(
            controls_frame, textvariable=dept_var,
            values=self.get_all_departments(),
            font=('Arial', 11), width=30, state='readonly'
        )
        dept_dropdown.pack(side='left', padx=(0, 20))
        
        # Stats frame
        stats_frame = tk.LabelFrame(
            controls_frame, text="📊 Department Statistics",
            font=('Arial', 10, 'bold'), bg='white'
        )
        stats_frame.pack(side='right', fill='both', expand=True)
        
        stats_text = tk.Text(
            stats_frame, height=3, width=50,
            font=('Arial', 9), bg='#F8F9FA',
            relief='flat', state='disabled'
        )
        stats_text.pack(padx=10, pady=5)
        
        # Employees table
        table_frame = tk.Frame(dept_frame, bg='white')
        table_frame.pack(expand=True, fill='both', padx=20, pady=10)
        
        columns = ("EmpNo", "First Name", "Last Name", "Title", "Salary", "Hire Date", "Manager")
        tree = ttk.Treeview(
            table_frame, columns=columns, show="headings",
            style='Custom.Treeview'
        )
        
        # Configure columns
        column_widths = {"EmpNo": 80, "First Name": 120, "Last Name": 120, 
                        "Title": 150, "Salary": 100, "Hire Date": 100, "Manager": 80}
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=column_widths.get(col, 100), minwidth=50)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=tree.yview)
        h_scrollbar = ttk.Scrollbar(table_frame, orient='horizontal', command=tree.xview)
        tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        tree.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        def load_department_data(event=None):
            # Clear existing data
            for item in tree.get_children():
                tree.delete(item)
            
            dept_name = dept_var.get()
            if not dept_name:
                return
            
            # Load employees
            employees = self.get_employees_by_department(dept_name)
            for emp in employees:
                # Format salary
                formatted_emp = list(emp)
                if formatted_emp[4]:  # salary
                    formatted_emp[4] = f"${formatted_emp[4]:,}"
                tree.insert("", "end", values=formatted_emp)
            
            # Update statistics
            stats = self.get_department_stats(dept_name)
            stats_text.config(state='normal')
            stats_text.delete('1.0', tk.END)
            stats_text.insert('1.0', 
                f"Total Employees: {stats.get('total_employees', 0)}\n"
                f"Average Salary: {stats.get('avg_salary', 'N/A')}\n"
                f"Salary Range: {stats.get('min_salary', 'N/A')} - {stats.get('max_salary', 'N/A')}"
            )
            stats_text.config(state='disabled')
        
        dept_dropdown.bind("<<ComboboxSelected>>", load_department_data)
    
    def create_search_tab(self, notebook):
        """Create employee search tab"""
        search_frame = tk.Frame(notebook, bg='white')
        notebook.add(search_frame, text="🔍 Employee Search")
        
        # Search controls
        search_controls = tk.Frame(search_frame, bg='white')
        search_controls.pack(fill='x', padx=20, pady=10)
        
        tk.Label(
            search_controls, text="Search Employee:",
            font=('Arial', 12, 'bold'), bg='white'
        ).pack(side='left', padx=(0, 10))
        
        search_var = tk.StringVar()
        search_entry = tk.Entry(
            search_controls, textvariable=search_var,
            font=('Arial', 11), width=30
        )
        search_entry.pack(side='left', padx=(0, 10))
        
        search_btn = tk.Button(
            search_controls, text="🔍 Search",
            font=('Arial', 10, 'bold'),
            bg=self.colors['accent'], fg='white',
            relief='flat', cursor='hand2'
        )
        search_btn.pack(side='left', padx=(0, 10))
        
        clear_btn = tk.Button(
            search_controls, text="🗑️ Clear",
            font=('Arial', 10, 'bold'),
            bg=self.colors['warning'], fg='white',
            relief='flat', cursor='hand2'
        )
        clear_btn.pack(side='left')
        
        # Results info
        results_label = tk.Label(
            search_controls, text="",
            font=('Arial', 10), bg='white', fg=self.colors['secondary']
        )
        results_label.pack(side='right')
        
        # Results table
        results_frame = tk.Frame(search_frame, bg='white')
        results_frame.pack(expand=True, fill='both', padx=20, pady=10)
        
        search_columns = ("EmpNo", "First Name", "Last Name", "Gender", 
                         "Birth Date", "Hire Date", "Title", "Salary", "Department")
        search_tree = ttk.Treeview(
            results_frame, columns=search_columns, show="headings",
            style='Custom.Treeview'
        )
        
        # Configure search columns
        search_widths = {"EmpNo": 70, "First Name": 100, "Last Name": 100, "Gender": 60,
                        "Birth Date": 90, "Hire Date": 90, "Title": 130, 
                        "Salary": 90, "Department": 120}
        
        for col in search_columns:
            search_tree.heading(col, text=col)
            search_tree.column(col, width=search_widths.get(col, 80), minwidth=50)
        
        # Scrollbars for search
        search_v_scroll = ttk.Scrollbar(results_frame, orient='vertical', command=search_tree.yview)
        search_h_scroll = ttk.Scrollbar(results_frame, orient='horizontal', command=search_tree.xview)
        search_tree.configure(yscrollcommand=search_v_scroll.set, xscrollcommand=search_h_scroll.set)
        
        search_tree.grid(row=0, column=0, sticky='nsew')
        search_v_scroll.grid(row=0, column=1, sticky='ns')
        search_h_scroll.grid(row=1, column=0, sticky='ew')
        
        results_frame.grid_rowconfigure(0, weight=1)
        results_frame.grid_columnconfigure(0, weight=1)
        
        def perform_search():
            # Clear existing results
            for item in search_tree.get_children():
                search_tree.delete(item)
            
            search_term = search_var.get().strip()
            if not search_term:
                results_label.config(text="Please enter a search term")
                return
            
            results = self.search_employees(search_term)
            
            if not results:
                results_label.config(text="No employees found")
                return
            
            # Display results
            for emp in results:
                formatted_emp = list(emp)
                # Format salary
                if formatted_emp[7]:  # salary column
                    formatted_emp[7] = f"${formatted_emp[7]:,}"
                search_tree.insert("", "end", values=formatted_emp)
            
            results_label.config(text=f"Found {len(results)} employee(s)")
        
        def clear_search():
            search_var.set("")
            for item in search_tree.get_children():
                search_tree.delete(item)
            results_label.config(text="")
        
        search_btn.config(command=perform_search)
        clear_btn.config(command=clear_search)
        search_entry.bind('<Return>', lambda e: perform_search())
    
    def create_analytics_tab(self, notebook):
        """Create analytics and reports tab"""
        analytics_frame = tk.Frame(notebook, bg='white')
        notebook.add(analytics_frame, text="📈 Analytics")
        
        # Analytics content
        analytics_content = tk.Frame(analytics_frame, bg='white')
        analytics_content.pack(expand=True, fill='both', padx=20, pady=20)
        
        # Overview cards
        overview_frame = tk.Frame(analytics_content, bg='white')
        overview_frame.pack(fill='x', pady=(0, 20))
        
        # Get overall statistics
        total_employees_query = "SELECT COUNT(*) FROM employees"
        total_employees = self.run_query(total_employees_query)[0][0]
        
        total_departments_query = "SELECT COUNT(*) FROM departments"
        total_departments = self.run_query(total_departments_query)[0][0]
        
        total_managers_query = "SELECT COUNT(DISTINCT emp_no) FROM dept_manager WHERE to_date = '9999-01-01'"
        total_managers = self.run_query(total_managers_query)[0][0]
        
        avg_salary_query = "SELECT AVG(salary) FROM salaries WHERE to_date = '9999-01-01'"
        avg_salary_result = self.run_query(avg_salary_query)
        avg_salary = f"${avg_salary_result[0][0]:,.0f}" if avg_salary_result[0][0] else "N/A"
        
        # Create stat cards
        stats = [
            ("👥 Total Employees", total_employees, self.colors['accent']),
            ("🏢 Departments", total_departments, self.colors['success']),
            ("👔 Managers", total_managers, self.colors['warning']),
            ("💰 Avg Salary", avg_salary, self.colors['primary'])
        ]
        
        for i, (title, value, color) in enumerate(stats):
            card = tk.Frame(overview_frame, bg=color, relief='raised', bd=2)
            card.pack(side='left', fill='both', expand=True, padx=5)
            
            tk.Label(
                card, text=title,
                font=('Arial', 12, 'bold'),
                fg='white', bg=color
            ).pack(pady=(10, 5))
            
            tk.Label(
                card, text=str(value),
                font=('Arial', 16, 'bold'),
                fg='white', bg=color
            ).pack(pady=(0, 10))
        
        # Department breakdown
        dept_frame = tk.LabelFrame(
            analytics_content, text="📊 Department Breakdown",
            font=('Arial', 12, 'bold'), bg='white'
        )
        dept_frame.pack(fill='both', expand=True, pady=10)
        
        # Department stats table
        dept_columns = ("Department", "Employees", "Managers", "Avg Salary", "Max Salary")
        dept_tree = ttk.Treeview(
            dept_frame, columns=dept_columns, show="headings",
            style='Custom.Treeview', height=10
        )
        
        for col in dept_columns:
            dept_tree.heading(col, text=col)
            dept_tree.column(col, width=150, minwidth=100)
        
        dept_tree.pack(expand=True, fill='both', padx=10, pady=10)
        
        # Load department analytics
        departments = self.get_all_departments()
        for dept in departments:
            stats = self.get_department_stats(dept)
            dept_tree.insert("", "end", values=(
                dept,
                stats.get('total_employees', 0),
                stats.get('managers_count', 0),
                stats.get('avg_salary', 'N/A'),
                stats.get('max_salary', 'N/A')
            ))
    
    def run(self):
        """Start the application"""
        self.show_login()
        self.root.mainloop()

# Create and run the application
if __name__ == "__main__":
    try:
        app = EmployeeManagementSystem()
        app.run()
    except Exception as e:
        messagebox.showerror("Application Error", f"Failed to start application: {str(e)}")
        print(f"Error: {str(e)}")








