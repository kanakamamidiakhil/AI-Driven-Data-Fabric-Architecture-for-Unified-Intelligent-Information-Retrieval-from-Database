from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal

class Employee(models.Model):
    """
    Employee model that maps to your existing 'employees' table.
    This is unmanaged - Django won't create/modify the table structure.
    """
    
    # Basic fields that should exist in most employee tables
    # Adjust field names and types to match your existing table structure
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    department = models.CharField(max_length=100, null=True, blank=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    date_of_join = models.DateField(null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    position = models.CharField(max_length=200, null=True, blank=True)
    
    # Add any other fields that might exist in your table
    # Uncomment and modify as needed:
    # employee_id = models.CharField(max_length=50, null=True, blank=True)
    # first_name = models.CharField(max_length=100, null=True, blank=True)
    # last_name = models.CharField(max_length=100, null=True, blank=True)
    # phone = models.CharField(max_length=20, null=True, blank=True)
    # address = models.TextField(null=True, blank=True)
    # hire_date = models.DateField(null=True, blank=True)  # Alternative to date_of_join
    # status = models.CharField(max_length=20, null=True, blank=True)
    # manager_id = models.IntegerField(null=True, blank=True)
    # location = models.CharField(max_length=100, null=True, blank=True)
    # job_title = models.CharField(max_length=100, null=True, blank=True)  # Alternative to position
    
    class Meta:
        managed = False  # Django won't manage this table
        db_table = 'employees'  # Use your existing table name
        ordering = ['name'] if 'name' in locals() else ['id']
    
    def __str__(self):
        if hasattr(self, 'name') and self.name:
            dept = f" - {self.department}" if hasattr(self, 'department') and self.department else ""
            return f"{self.name}{dept}"
        return f"Employee {self.id}"
    
    @property
    def years_of_service(self):
        """Calculate years of service - adjust field name as needed"""
        if hasattr(self, 'date_of_join') and self.date_of_join:
            from datetime import date
            today = date.today()
            return today.year - self.date_of_join.year
        elif hasattr(self, 'hire_date') and self.hire_date:
            from datetime import date
            today = date.today()
            return today.year - self.hire_date.year
        return None

class QueryLog(models.Model):
    """Log of AI queries for analytics - this will be a new managed table"""
    
    original_query = models.TextField(help_text="Original natural language query")
    generated_sql = models.TextField(help_text="Generated SQL query")
    success = models.BooleanField(help_text="Whether query was successful")
    error_message = models.TextField(blank=True, null=True)
    execution_time = models.FloatField(help_text="Query execution time in seconds")
    result_count = models.IntegerField(default=0, help_text="Number of results returned")
    cached = models.BooleanField(default=False, help_text="Whether result was cached")
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        db_table = 'query_logs'  # This will be created by Django
    
    def __str__(self):
        status = "✅" if self.success else "❌"
        return f"{status} {self.original_query[:50]}... [{self.timestamp.strftime('%Y-%m-%d %H:%M')}]"