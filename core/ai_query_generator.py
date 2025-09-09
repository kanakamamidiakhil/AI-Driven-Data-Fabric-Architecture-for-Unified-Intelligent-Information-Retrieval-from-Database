import requests
import json
import time
import logging
import re
from django.conf import settings
from django.db import connection
from .models import QueryLog

logger = logging.getLogger('ai_query')

class AIQueryGenerator:
    """AI-powered SQL query generator that works with existing employee table"""
    
    def __init__(self):
        self.openrouter_api_key = settings.OPENROUTER_API_KEY
        self.openai_api_key = getattr(settings, 'OPENAI_API_KEY', '')
        self.anthropic_api_key = getattr(settings, 'ANTHROPIC_API_KEY', '')
        
        # Get actual database schema information
        self.schema_info = self._get_actual_schema_info()
    
    def _get_actual_schema_info(self):
        """Get actual database schema information from your existing table"""
        try:
            with connection.cursor() as cursor:
                # Get table structure - works for PostgreSQL, MySQL, SQLite
                if connection.vendor == 'postgresql':
                    cursor.execute("""
                        SELECT column_name, data_type, is_nullable, column_default
                        FROM information_schema.columns 
                        WHERE table_name = 'employees'
                        ORDER BY ordinal_position;
                    """)
                elif connection.vendor == 'mysql':
                    cursor.execute("DESCRIBE employees;")
                else:  # SQLite
                    cursor.execute("PRAGMA table_info(employees);")
                
                columns = cursor.fetchall()
                
                # Build schema description
                schema_description = "Database Schema for 'employees' table:\n"
                
                if connection.vendor == 'postgresql':
                    for col in columns:
                        col_name, data_type, is_nullable, default = col
                        nullable = "NULL" if is_nullable == 'YES' else "NOT NULL"
                        schema_description += f"- {col_name} ({data_type.upper()}): {nullable}\n"
                else:
                    # For other databases, format may vary
                    for col in columns:
                        if len(col) >= 2:
                            schema_description += f"- {col[1] if connection.vendor == 'mysql' else col[1]}\n"
                
                # Add sample data context
                cursor.execute("SELECT COUNT(*) FROM employees")
                count = cursor.fetchone()[0]
                schema_description += f"\nTable contains {count} employee records.\n"
                
                # Get sample departments if department column exists
                try:
                    cursor.execute("SELECT DISTINCT department FROM employees WHERE department IS NOT NULL LIMIT 10")
                    departments = [row[0] for row in cursor.fetchall()]
                    if departments:
                        schema_description += f"Sample departments: {', '.join(departments)}\n"
                except:
                    pass
                
                return schema_description
                
        except Exception as e:
            logger.error(f"Error getting schema info: {e}")
            return self._get_default_schema_info()
    
    def _get_default_schema_info(self):
        """Default schema info if we can't read the actual structure"""
        return """
        Database Schema for 'employees' table (common fields):
        - id: Primary key
        - name / first_name / last_name: Employee names
        - department: Department name
        - salary: Employee salary
        - date_of_join / hire_date: Date employee joined
        - email: Employee email
        - position / job_title: Job position
        - phone: Phone number
        - address: Address information
        - manager_id: Manager reference
        - status: Employment status
        
        Note: Field names may vary. Use appropriate field names based on the actual table structure.
        """
    
    def _create_system_prompt(self):
        """Create system prompt for AI models with actual schema"""
        return f"""You are a SQL query generator. Convert natural language questions into SQL SELECT queries for the existing 'employees' table.

{self.schema_info}

IMPORTANT RULES:
1. ONLY generate SELECT statements
2. Use ONLY the 'employees' table
3. Return valid SQL syntax for the database type in use
4. Use appropriate WHERE clauses for filtering
5. Handle case-insensitive searches with ILIKE (PostgreSQL) or LIKE with LOWER()
6. Use proper date functions for date comparisons
7. Always include appropriate column names in SELECT
8. Use ORDER BY for better results presentation
9. Limit results to reasonable numbers (LIMIT 100 or similar)
10. Handle NULL values appropriately with IS NULL / IS NOT NULL

FIELD NAME VARIATIONS TO CONSIDER:
- Name fields: name, first_name, last_name, full_name, employee_name
- Date fields: date_of_join, hire_date, start_date, employment_date
- Position fields: position, job_title, title, role
- ID fields: id, employee_id, emp_id
- Status fields: status, is_active, active, employment_status

EXAMPLE QUERY PATTERNS:
- "Show all employees" → SELECT * FROM employees LIMIT 100;
- "IT department employees" → SELECT * FROM employees WHERE department ILIKE '%IT%';
- "Employees earning over 50000" → SELECT * FROM employees WHERE salary > 50000 ORDER BY salary DESC;
- "Recent hires" → SELECT * FROM employees WHERE date_of_join > CURRENT_DATE - INTERVAL '1 year';

Respond with ONLY the SQL query, no explanations or formatting."""
    
    def _query_openrouter(self, user_query):
        """Query OpenRouter API with free models"""
        if not self.openrouter_api_key:
            return None
        
        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json"
        }
        
        models = [
            "meta-llama/llama-3.1-8b-instruct:free",
            "microsoft/phi-3-mini-128k-instruct:free",
            "google/gemma-7b-it:free"
        ]
        
        for model in models:
            try:
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": self._create_system_prompt()},
                        {"role": "user", "content": user_query}
                    ],
                    "max_tokens": 200,
                    "temperature": 0.1
                }
                
                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    sql_query = data['choices'][0]['message']['content'].strip()
                    logger.info(f"OpenRouter ({model}) generated SQL: {sql_query}")
                    return self._clean_sql_query(sql_query)
                else:
                    logger.warning(f"OpenRouter {model} failed: {response.status_code}")
                    continue
                    
            except Exception as e:
                logger.error(f"OpenRouter {model} error: {e}")
                continue
        
        return None
    
    def _query_fallback_local(self, user_query):
        """Enhanced fallback with smart column selection for existing table"""
        query_lower = user_query.lower()
        
        # Analyze what user is asking for to determine columns
        asking_for_salary = any(word in query_lower for word in ["salary", "pay", "wage", "earning", "income"])
        asking_for_department = any(word in query_lower for word in ["department", "dept"])
        asking_for_position = any(word in query_lower for word in ["position", "job", "title", "role"])
        asking_for_date = any(word in query_lower for word in ["joined", "hired", "date", "when"])
        asking_for_details = any(word in query_lower for word in ["details", "information", "everything", "all details"])
        asking_for_count = any(word in query_lower for word in ["count", "how many", "number of"])
        
        # Base columns - always include name
        base_columns = "name"
        
        # Add relevant columns based on query
        columns = [base_columns]
        if asking_for_department or "department" in query_lower:
            if "department" not in columns:
                columns.append("department")
        if asking_for_salary:
            if "salary" not in columns:
                columns.append("salary")
        if asking_for_position:
            if "position" not in columns:
                columns.append("position")  # or job_title based on your table
        if asking_for_date:
            if "date_of_join" not in columns:
                columns.append("date_of_join")  # or hire_date based on your table
        
        # Join columns
        if asking_for_details:
            select_clause = "*"
        elif asking_for_count:
            select_clause = "COUNT(*) as count"
        else:
            select_clause = ", ".join(columns)
        
        # Count queries
        if asking_for_count:
            if "department" in query_lower:
                departments = ["IT", "HR", "Sales", "Marketing", "Finance", "Engineering", "Operations"]
                for dept in departments:
                    if dept.lower() in query_lower:
                        return f"SELECT COUNT(*) as count FROM employees WHERE LOWER(department) LIKE '%{dept.lower()}%';"
                # General department count
                return "SELECT department, COUNT(*) as count FROM employees WHERE department IS NOT NULL GROUP BY department ORDER BY count DESC;"
            else:
                return "SELECT COUNT(*) as total_employees FROM employees;"
        
        # Get all employees (names only)
        if any(phrase in query_lower for phrase in ["all employees", "show employees", "list employees"]) and not asking_for_details:
            return f"SELECT {select_clause} FROM employees ORDER BY name LIMIT 100;"
        
        # Department queries
        if "department" in query_lower:
            departments = ["IT", "HR", "Sales", "Marketing", "Finance", "Engineering", "Operations"]
            for dept in departments:
                if dept.lower() in query_lower:
                    return f"SELECT {select_clause} FROM employees WHERE LOWER(department) LIKE '%{dept.lower()}%' ORDER BY name LIMIT 50;"
        
        # Salary queries
        if asking_for_salary and any(op in query_lower for op in ["greater", "more than", "above", "over"]):
            numbers = re.findall(r'\d+', query_lower)
            if numbers:
                amount = numbers[0]
                if not asking_for_salary:  # If not explicitly asking for salary info, add it
                    select_clause = "name, salary, department"
                return f"SELECT {select_clause} FROM employees WHERE salary > {amount} ORDER BY salary DESC LIMIT 50;"
        
        # Recent hires / date queries
        if any(phrase in query_lower for phrase in ["joined", "hired", "recent", "new"]):
            if not asking_for_date:  # Add date info if not explicitly requested
                select_clause = "name, department, date_of_join"  # or hire_date
            
            if "last year" in query_lower or "2023" in query_lower:
                return f"""
                SELECT {select_clause} FROM employees 
                WHERE (date_of_join >= CURRENT_DATE - INTERVAL '1 year' 
                   OR hire_date >= CURRENT_DATE - INTERVAL '1 year')
                ORDER BY COALESCE(date_of_join, hire_date) DESC LIMIT 50;
                """
            elif "this year" in query_lower or "2024" in query_lower:
                return f"""
                SELECT {select_clause} FROM employees 
                WHERE (EXTRACT(YEAR FROM date_of_join) = EXTRACT(YEAR FROM CURRENT_DATE)
                   OR EXTRACT(YEAR FROM hire_date) = EXTRACT(YEAR FROM CURRENT_DATE))
                ORDER BY COALESCE(date_of_join, hire_date) DESC LIMIT 50;
                """
        
        # Name searches
        if "name" in query_lower and any(word in query_lower for word in ["contains", "like", "starts", "ends"]):
            return f"SELECT name FROM employees WHERE name IS NOT NULL ORDER BY name LIMIT 100;"
        
        # Email searches  
        if "email" in query_lower:
            return "SELECT name, email, department FROM employees WHERE email IS NOT NULL ORDER BY name LIMIT 100;"
        
        # Position/title searches
        if asking_for_position:
            return f"SELECT name, position, department FROM employees WHERE position IS NOT NULL ORDER BY name LIMIT 100;"
        
        # Default: show names only
        return "SELECT name FROM employees ORDER BY name LIMIT 20;"
    
    def _clean_sql_query(self, sql_query):
        """Clean and validate SQL query for existing table"""
        if not sql_query:
            return None
        
        # Remove markdown formatting
        sql_query = re.sub(r'```sql\n?', '', sql_query)
        sql_query = re.sub(r'```\n?', '', sql_query)
        sql_query = sql_query.strip()
        
        # Basic security checks
        sql_lower = sql_query.lower()
        
        # Must be a SELECT query
        if not sql_lower.startswith('select'):
            return None
        
        # Prohibited operations
        prohibited = ['drop', 'delete', 'update', 'insert', 'alter', 'create', 'truncate', 'grant', 'revoke']
        if any(op in sql_lower for op in prohibited):
            return None
        
        # Must query employees table
        if 'employees' not in sql_lower:
            return None
        
        # Ensure query ends with semicolon
        if not sql_query.endswith(';'):
            sql_query += ';'
        
        return sql_query
    
    def _execute_sql_query(self, sql_query):
        """Execute SQL query safely against existing table"""
        try:
            start_time = time.time()
            
            with connection.cursor() as cursor:
                cursor.execute(sql_query)
                columns = [col[0] for col in cursor.description] if cursor.description else []
                results = cursor.fetchall()
                
                # Convert results to list of dictionaries
                data = []
                for row in results:
                    row_dict = {}
                    for i, value in enumerate(row):
                        column_name = columns[i] if i < len(columns) else f"column_{i}"
                        
                        # Handle different data types
                        if hasattr(value, 'isoformat'):  # Date/DateTime
                            row_dict[column_name] = value.isoformat()
                        elif isinstance(value, (float, int)) and 'salary' in column_name.lower():
                            row_dict[column_name] = round(float(value), 2) if value is not None else None
                        elif value is None:
                            row_dict[column_name] = None
                        else:
                            row_dict[column_name] = str(value)
                    data.append(row_dict)
            
            execution_time = time.time() - start_time
            
            return {
                'success': True,
                'data': data,
                'columns': columns,
                'row_count': len(data),
                'execution_time': execution_time
            }
            
        except Exception as e:
            logger.error(f"SQL execution error: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': [],
                'columns': [],
                'row_count': 0,
                'execution_time': 0
            }
    
    def _log_query(self, user_query, sql_query, success, error_message, execution_time, result_count, cached=False):
        """Log query to database"""
        try:
            QueryLog.objects.create(
                original_query=user_query,
                generated_sql=sql_query or '',
                success=success,
                error_message=error_message,
                execution_time=execution_time,
                result_count=result_count,
                cached=cached
            )
        except Exception as e:
            logger.error(f"Failed to log query: {e}")
    
    def process_natural_language_query(self, user_query):
        """Main method to process natural language query against existing table"""
        start_time = time.time()
        
        try:
            # Try AI services in order
            sql_query = None
            
            # 1. Try OpenRouter (free models)
            sql_query = self._query_openrouter(user_query)
            
            # 2. Fallback to enhanced pattern matching
            if not sql_query:
                logger.info("Using enhanced fallback pattern matching")
                sql_query = self._query_fallback_local(user_query)
            
            if not sql_query:
                return {
                    'success': False,
                    'error': 'Failed to generate SQL query from all available methods',
                    'original_query': user_query,
                    'sql_query': None,
                    'data': [],
                    'columns': [],
                    'row_count': 0
                }
            
            # Execute the generated query
            result = self._execute_sql_query(sql_query)
            
            # Prepare response
            response = {
                'success': result['success'],
                'original_query': user_query,
                'sql_query': sql_query,
                'data': result['data'],
                'columns': result.get('columns', []),
                'row_count': result.get('row_count', 0)
            }
            
            if not result['success']:
                response['error'] = result.get('error', 'Unknown error')
            
            # Log the query
            total_time = time.time() - start_time
            self._log_query(
                user_query, sql_query, result['success'],
                result.get('error', ''), total_time,
                result.get('row_count', 0)
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Query processing error: {e}")
            total_time = time.time() - start_time
            self._log_query(user_query, '', False, str(e), total_time, 0)
            
            return {
                'success': False,
                'error': f'Query processing failed: {str(e)}',
                'original_query': user_query,
                'sql_query': None,
                'data': [],
                'columns': [],
                'row_count': 0
            }