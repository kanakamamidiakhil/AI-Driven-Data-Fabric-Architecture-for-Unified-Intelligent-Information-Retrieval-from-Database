from django.contrib import admin
from django.utils.html import format_html
from .models import Employee, QueryLog

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    # Basic list display - only include fields that commonly exist
    list_display = [
        'id', 'name_display', 'department_display', 'salary_display', 'date_display'
    ]
    
    # Basic filtering - only on fields that commonly exist
    list_filter = ['department']
    
    # Search fields - only include common fields
    search_fields = ['name', 'department']
    
    # Ordering
    ordering = ['id']
    
    # No date hierarchy since field names vary
    # date_hierarchy = 'date_of_join'
    
    # Basic fieldsets - will be overridden by get_fieldsets()
    fieldsets = (
        ('Employee Information', {
            'fields': ('id', 'name', 'department', 'salary')
        }),
    )
    
    # No readonly fields by default - will be set dynamically
    readonly_fields = []
    
    def get_list_display(self, request):
        """Dynamically set list_display based on available fields"""
        available_fields = []
        
        # Always include ID if available
        if hasattr(self.model, 'id'):
            available_fields.append('id')
        
        # Add name field (various forms)
        if hasattr(self.model, 'name'):
            available_fields.append('name_display')
        elif hasattr(self.model, 'first_name') and hasattr(self.model, 'last_name'):
            available_fields.append('full_name_display')
        elif hasattr(self.model, 'full_name'):
            available_fields.append('full_name_display')
        
        # Add department
        if hasattr(self.model, 'department'):
            available_fields.append('department_display')
        elif hasattr(self.model, 'dept'):
            available_fields.append('department_display')
        
        # Add position/title
        if hasattr(self.model, 'position'):
            available_fields.append('position_display')
        elif hasattr(self.model, 'job_title'):
            available_fields.append('position_display')
        
        # Add salary
        if hasattr(self.model, 'salary'):
            available_fields.append('salary_display')
        
        # Add date fields
        if hasattr(self.model, 'date_of_join'):
            available_fields.append('date_display')
        elif hasattr(self.model, 'hire_date'):
            available_fields.append('date_display')
        
        # Add status if available
        if hasattr(self.model, 'is_active'):
            available_fields.append('status_display')
        elif hasattr(self.model, 'status'):
            available_fields.append('status_display')
        
        return available_fields
    
    def get_list_filter(self, request):
        """Dynamically set list_filter based on available fields"""
        available_filters = []
        
        if hasattr(self.model, 'department'):
            available_filters.append('department')
        elif hasattr(self.model, 'dept'):
            available_filters.append('dept')
        
        if hasattr(self.model, 'date_of_join'):
            available_filters.append('date_of_join')
        elif hasattr(self.model, 'hire_date'):
            available_filters.append('hire_date')
        
        if hasattr(self.model, 'is_active'):
            available_filters.append('is_active')
        elif hasattr(self.model, 'status'):
            available_filters.append('status')
        
        return available_filters
    
    def get_search_fields(self, request):
        """Dynamically set search_fields based on available fields"""
        available_search = []
        
        if hasattr(self.model, 'name'):
            available_search.append('name')
        if hasattr(self.model, 'first_name'):
            available_search.append('first_name')
        if hasattr(self.model, 'last_name'):
            available_search.append('last_name')
        if hasattr(self.model, 'email'):
            available_search.append('email')
        if hasattr(self.model, 'department'):
            available_search.append('department')
        if hasattr(self.model, 'position'):
            available_search.append('position')
        if hasattr(self.model, 'job_title'):
            available_search.append('job_title')
        
        return available_search
    
    def get_fieldsets(self, request, obj=None):
        """Dynamically create fieldsets based on available fields"""
        basic_fields = []
        employment_fields = []
        contact_fields = []
        
        # Basic information
        if hasattr(self.model, 'id'):
            basic_fields.append('id')
        if hasattr(self.model, 'name'):
            basic_fields.append('name')
        elif hasattr(self.model, 'first_name'):
            basic_fields.extend(['first_name', 'last_name'])
        if hasattr(self.model, 'employee_id'):
            basic_fields.append('employee_id')
        
        # Contact information
        if hasattr(self.model, 'email'):
            contact_fields.append('email')
        if hasattr(self.model, 'phone'):
            contact_fields.append('phone')
        if hasattr(self.model, 'address'):
            contact_fields.append('address')
        
        # Employment details
        if hasattr(self.model, 'department'):
            employment_fields.append('department')
        if hasattr(self.model, 'position'):
            employment_fields.append('position')
        elif hasattr(self.model, 'job_title'):
            employment_fields.append('job_title')
        if hasattr(self.model, 'salary'):
            employment_fields.append('salary')
        if hasattr(self.model, 'date_of_join'):
            employment_fields.append('date_of_join')
        elif hasattr(self.model, 'hire_date'):
            employment_fields.append('hire_date')
        if hasattr(self.model, 'manager_id'):
            employment_fields.append('manager_id')
        if hasattr(self.model, 'is_active'):
            employment_fields.append('is_active')
        elif hasattr(self.model, 'status'):
            employment_fields.append('status')
        
        # Build fieldsets
        fieldsets = []
        if basic_fields:
            fieldsets.append(('Basic Information', {'fields': basic_fields}))
        if contact_fields:
            fieldsets.append(('Contact Information', {'fields': contact_fields}))
        if employment_fields:
            fieldsets.append(('Employment Details', {'fields': employment_fields}))
        
        return fieldsets or (('Information', {'fields': ('id',)}),)
    
    def get_readonly_fields(self, request, obj=None):
        """Make ID field readonly, and any timestamp fields"""
        readonly = []
        if hasattr(self.model, 'id'):
            readonly.append('id')
        if hasattr(self.model, 'created_at'):
            readonly.append('created_at')
        if hasattr(self.model, 'updated_at'):
            readonly.append('updated_at')
        return readonly
    
    # Display methods that handle different field names
    def name_display(self, obj):
        """Display name - handles different name field variations"""
        if hasattr(obj, 'name') and obj.name:
            return obj.name
        elif hasattr(obj, 'first_name') and hasattr(obj, 'last_name'):
            first = getattr(obj, 'first_name', '') or ''
            last = getattr(obj, 'last_name', '') or ''
            return f"{first} {last}".strip()
        elif hasattr(obj, 'full_name') and obj.full_name:
            return obj.full_name
        return f"Employee {obj.id}"
    name_display.short_description = "Name"
    
    def full_name_display(self, obj):
        """Display full name for first_name/last_name fields"""
        return self.name_display(obj)
    full_name_display.short_description = "Full Name"
    
    def department_display(self, obj):
        """Display department - handles different field names"""
        if hasattr(obj, 'department') and obj.department:
            return obj.department
        elif hasattr(obj, 'dept') and obj.dept:
            return obj.dept
        return "-"
    department_display.short_description = "Department"
    
    def position_display(self, obj):
        """Display position - handles different field names"""
        if hasattr(obj, 'position') and obj.position:
            return obj.position
        elif hasattr(obj, 'job_title') and obj.job_title:
            return obj.job_title
        elif hasattr(obj, 'title') and obj.title:
            return obj.title
        return "-"
    position_display.short_description = "Position"
    
    def salary_display(self, obj):
        """Display salary with formatting"""
        if hasattr(obj, 'salary') and obj.salary:
            return f"${obj.salary:,.2f}"
        elif hasattr(obj, 'annual_salary') and obj.annual_salary:
            return f"${obj.annual_salary:,.2f}"
        return "-"
    salary_display.short_description = "Salary"
    
    def date_display(self, obj):
        """Display join date - handles different field names"""
        date_val = None
        if hasattr(obj, 'date_of_join') and obj.date_of_join:
            date_val = obj.date_of_join
        elif hasattr(obj, 'hire_date') and obj.hire_date:
            date_val = obj.hire_date
        elif hasattr(obj, 'start_date') and obj.start_date:
            date_val = obj.start_date
        
        if date_val:
            return date_val.strftime('%Y-%m-%d')
        return "-"
    date_display.short_description = "Join Date"
    
    def status_display(self, obj):
        """Display status with formatting"""
        if hasattr(obj, 'is_active'):
            if obj.is_active:
                return format_html('<span style="color: green;">✅ Active</span>')
            else:
                return format_html('<span style="color: red;">❌ Inactive</span>')
        elif hasattr(obj, 'status') and obj.status:
            status = str(obj.status).lower()
            if status in ['active', 'employed', '1', 'true']:
                return format_html('<span style="color: green;">✅ Active</span>')
            else:
                return format_html('<span style="color: gray;">⏸️ {}</span>', obj.status.title())
        return "-"
    status_display.short_description = "Status"
    
    def has_add_permission(self, request):
        """Prevent adding new employees through admin (read-only for existing table)"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deleting employees (read-only for existing table)"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Allow viewing but prevent changes to existing table"""
        return False  # Set to True if you want to allow viewing details

@admin.register(QueryLog)
class QueryLogAdmin(admin.ModelAdmin):
    list_display = [
        'truncated_query', 'success_icon', 'result_count', 
        'execution_time_display', 'cached_icon', 'timestamp'
    ]
    list_filter = ['success', 'cached', 'timestamp']
    search_fields = ['original_query', 'generated_sql']
    ordering = ['-timestamp']
    readonly_fields = [
        'original_query', 'generated_sql', 'success', 'error_message',
        'execution_time', 'result_count', 'cached', 'timestamp'
    ]
    
    fieldsets = (
        ('Query Information', {
            'fields': ('original_query', 'generated_sql')
        }),
        ('Execution Results', {
            'fields': ('success', 'error_message', 'result_count', 'execution_time')
        }),
        ('Meta Information', {
            'fields': ('cached', 'timestamp')
        })
    )
    
    def truncated_query(self, obj):
        """Display truncated query"""
        if len(obj.original_query) > 50:
            return obj.original_query[:50] + "..."
        return obj.original_query
    truncated_query.short_description = "Query"
    
    def success_icon(self, obj):
        """Display success status with icon"""
        if obj.success:
            return format_html('<span style="color: green;">✅ Success</span>')
        else:
            return format_html('<span style="color: red;">❌ Failed</span>')
    success_icon.short_description = "Status"
    
    def cached_icon(self, obj):
        """Display cached status with icon"""
        if obj.cached:
            return format_html('<span style="color: blue;">⚡ Cached</span>')
        else:
            return format_html('<span style="color: gray;">🔄 Fresh</span>')
    cached_icon.short_description = "Cache"
    
    def execution_time_display(self, obj):
        """Display execution time with formatting"""
        if obj.execution_time < 0.1:
            return f"{obj.execution_time*1000:.1f}ms"
        else:
            return f"{obj.execution_time:.2f}s"
    execution_time_display.short_description = "Exec Time"
    
    def has_add_permission(self, request):
        """Prevent manual addition of query logs"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent editing of query logs"""
        return False