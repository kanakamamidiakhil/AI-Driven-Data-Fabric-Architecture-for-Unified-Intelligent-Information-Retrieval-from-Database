from django.core.management.base import BaseCommand
from django.db import connection
import json

class Command(BaseCommand):
    help = 'Inspect existing employees table structure and data'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--table',
            type=str,
            default='employees',
            help='Table name to inspect (default: employees)'
        )
        parser.add_argument(
            '--sample-size',
            type=int,
            default=5,
            help='Number of sample records to show (default: 5)'
        )
    
    def handle(self, *args, **options):
        table_name = options['table']
        sample_size = options['sample_size']
        
        self.stdout.write(
            self.style.SUCCESS(f'🔍 Inspecting table: {table_name}')
        )
        
        with connection.cursor() as cursor:
            try:
                # Check if table exists
                if connection.vendor == 'postgresql':
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = %s
                        );
                    """, [table_name])
                    table_exists = cursor.fetchone()[0]
                elif connection.vendor == 'mysql':
                    cursor.execute("SHOW TABLES LIKE %s", [table_name])
                    table_exists = len(cursor.fetchall()) > 0
                else:  # SQLite
                    cursor.execute("""
                        SELECT name FROM sqlite_master 
                        WHERE type='table' AND name=?;
                    """, [table_name])
                    table_exists = len(cursor.fetchall()) > 0
                
                if not table_exists:
                    self.stdout.write(
                        self.style.ERROR(f'❌ Table "{table_name}" does not exist')
                    )
                    return
                
                # Get table structure
                self.stdout.write('\n📋 Table Structure:')
                if connection.vendor == 'postgresql':
                    cursor.execute("""
                        SELECT 
                            column_name, 
                            data_type, 
                            is_nullable, 
                            column_default,
                            character_maximum_length
                        FROM information_schema.columns 
                        WHERE table_name = %s
                        ORDER BY ordinal_position;
                    """, [table_name])
                    
                    columns_info = cursor.fetchall()
                    self.stdout.write('Column Name | Data Type | Nullable | Default | Max Length')
                    self.stdout.write('-' * 65)
                    
                    for col in columns_info:
                        col_name, data_type, is_nullable, default, max_length = col
                        max_len_str = str(max_length) if max_length else 'N/A'
                        default_str = str(default) if default else 'None'
                        self.stdout.write(
                            f'{col_name:<12} | {data_type:<10} | {is_nullable:<8} | {default_str:<8} | {max_len_str}'
                        )
                
                elif connection.vendor == 'mysql':
                    cursor.execute(f"DESCRIBE {table_name}")
                    columns_info = cursor.fetchall()
                    self.stdout.write('Field | Type | Null | Key | Default | Extra')
                    self.stdout.write('-' * 50)
                    for col in columns_info:
                        self.stdout.write(' | '.join(str(x) for x in col))
                
                else:  # SQLite
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns_info = cursor.fetchall()
                    self.stdout.write('ID | Name | Type | NotNull | Default | PK')
                    self.stdout.write('-' * 45)
                    for col in columns_info:
                        self.stdout.write(' | '.join(str(x) for x in col))
                
                # Get record count
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                record_count = cursor.fetchone()[0]
                
                self.stdout.write(f'\n📊 Total Records: {record_count}')
                
                if record_count == 0:
                    self.stdout.write(
                        self.style.WARNING('⚠️ Table is empty - no sample data to show')
                    )
                    return
                
                # Show sample data
                self.stdout.write(f'\n📄 Sample Data (first {sample_size} records):')
                cursor.execute(f"SELECT * FROM {table_name} LIMIT {sample_size}")
                sample_data = cursor.fetchall()
                
                # Get column names for headers
                column_names = [desc[0] for desc in cursor.description]
                
                # Print headers
                header = ' | '.join(f'{name:<15}' for name in column_names)
                self.stdout.write(header)
                self.stdout.write('-' * len(header))
                
                # Print sample data
                for row in sample_data:
                    formatted_row = ' | '.join(f'{str(val):<15}' for val in row)
                    self.stdout.write(formatted_row)
                
                # Show unique departments if department column exists
                try:
                    cursor.execute(f"SELECT DISTINCT department FROM {table_name} WHERE department IS NOT NULL")
                    departments = [row[0] for row in cursor.fetchall()]
                    if departments:
                        self.stdout.write(f'\n🏢 Departments found: {", ".join(departments)}')
                except:
                    self.stdout.write('\n🏢 No department column found or accessible')
                
                # Show salary range if salary column exists
                try:
                    cursor.execute(f"SELECT MIN(salary), MAX(salary), AVG(salary) FROM {table_name} WHERE salary IS NOT NULL")
                    salary_stats = cursor.fetchone()
                    if salary_stats and salary_stats[0] is not None:
                        min_sal, max_sal, avg_sal = salary_stats
                        self.stdout.write(f'\n💰 Salary Range: ${min_sal:,.2f} - ${max_sal:,.2f} (Avg: ${avg_sal:,.2f})')
                except:
                    self.stdout.write('\n💰 No salary column found or accessible')
                
                # Generate Django model code suggestion
                self.stdout.write('\n🔧 Suggested Django Model Fields:')
                self.stdout.write('# Add these fields to your Employee model in models.py:')
                
                for col in columns_info:
                    if connection.vendor == 'postgresql':
                        col_name, data_type, is_nullable, default, max_length = col
                        django_field = self._suggest_django_field(col_name, data_type, is_nullable, max_length)
                        self.stdout.write(f'    {django_field}')
                    else:
                        # For other databases, provide basic suggestions
                        col_name = col[1] if connection.vendor == 'mysql' else col[1]
                        self.stdout.write(f'    # {col_name} = models.CharField(max_length=255, null=True, blank=True)')
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Error inspecting table: {e}')
                )
    
    def _suggest_django_field(self, col_name, data_type, is_nullable, max_length):
        """Suggest appropriate Django field based on database column type"""
        null_blank = "null=True, blank=True" if is_nullable == 'YES' else ""
        
        if col_name.lower() == 'id':
            return f"{col_name} = models.AutoField(primary_key=True)"
        elif 'email' in col_name.lower():
            return f"{col_name} = models.EmailField({null_blank})"
        elif data_type == 'integer':
            return f"{col_name} = models.IntegerField({null_blank})"
        elif data_type == 'bigint':
            return f"{col_name} = models.BigIntegerField({null_blank})"
        elif data_type in ['numeric', 'decimal']:
            return f"{col_name} = models.DecimalField(max_digits=10, decimal_places=2, {null_blank})"
        elif data_type == 'date':
            return f"{col_name} = models.DateField({null_blank})"
        elif data_type in ['timestamp', 'datetime']:
            return f"{col_name} = models.DateTimeField({null_blank})"
        elif data_type == 'boolean':
            return f"{col_name} = models.BooleanField(default=True, {null_blank})"
        elif data_type == 'text':
            return f"{col_name} = models.TextField({null_blank})"
        elif 'character' in data_type or 'varchar' in data_type:
            max_len = f"max_length={max_length}" if max_length else "max_length=255"
            return f"{col_name} = models.CharField({max_len}, {null_blank})"
        else:
            return f"{col_name} = models.CharField(max_length=255, {null_blank})  # {data_type}"