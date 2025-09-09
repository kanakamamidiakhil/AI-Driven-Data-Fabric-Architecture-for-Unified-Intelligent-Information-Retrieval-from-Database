from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from django.views.decorators.http import require_http_methods
import json
import hashlib
import logging
from .ai_query_generator import AIQueryGenerator

logger = logging.getLogger('core')

@csrf_exempt
@require_http_methods(["POST"])
def process_ai_query(request):
    """Main API endpoint for processing natural language queries"""
    try:
        data = json.loads(request.body)
        query = data.get('query', '').strip()
        
        if not query:
            return JsonResponse({
                'success': False,
                'error': 'Query cannot be empty'
            }, status=400)
        
        # Create cache key based on query
        cache_key = f"ai_query_{hashlib.md5(query.encode()).hexdigest()}"
        
        # Check cache first (optional - for performance)
        cached_result = cache.get(cache_key)
        if cached_result:
            cached_result['cached'] = True
            logger.info(f"Serving cached result for query: {query[:50]}...")
            return JsonResponse(cached_result)
        
        # Process query using AI
        ai_generator = AIQueryGenerator()
        result = ai_generator.process_natural_language_query(query)
        
        # Cache successful results for 5 minutes
        if result['success']:
            cache.set(cache_key, result, 300)
            logger.info(f"Query processed successfully: {query[:50]}...")
        else:
            logger.warning(f"Query failed: {query[:50]}... - {result.get('error', 'Unknown error')}")
        
        # Add timing and debug info
        result['cached'] = False
        
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON in request body")
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error(f"Unexpected error in process_ai_query: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        }, status=500)

@require_http_methods(["GET"])
def get_query_examples(request):
    """API endpoint to get example queries"""
    examples = [
        "Show me all employees in the company",
        "Give me the list of all employees who joined last year",
        "How many employees work in the IT department?",
        "Show me employees with salary greater than 50000",
        "List all employees who joined this year",
        "Find employees in the Sales department",
        "Show me the highest paid employees",
        "Count of employees in each department",
        "Employees who joined in 2023",
        "Show me all employees with their salaries sorted by name",
        "Find all software engineers",
        "Show me employees earning between 40000 and 80000",
        "List employees who have been with company for more than 5 years",
        "Show me the average salary by department",
        "Find employees with Gmail addresses"
    ]
    
    return JsonResponse({
        'success': True,
        'examples': examples
    })

@require_http_methods(["GET"])
def health_check(request):
    """Simple health check endpoint"""
    return JsonResponse({
        'status': 'healthy',
        'service': 'DataFabric AI Employee Query Backend',
        'version': '1.0.0'
    })

@require_http_methods(["GET"])
def api_info(request):
    """API information endpoint"""
    return JsonResponse({
        'name': 'DataFabric Employee Query API',
        'version': '1.0.0',
        'description': 'Convert natural language queries to SQL and execute against employee database',
        'endpoints': {
            'POST /api/query/': 'Process natural language query',
            'GET /api/examples/': 'Get example queries',
            'GET /api/health/': 'Health check',
            'GET /api/info/': 'API information'
        },
        'supported_queries': [
            'Employee listings and filtering',
            'Department-based queries',
            'Salary-based filtering',
            'Date-based filtering (joining dates)',
            'Aggregation queries (count, average)',
            'Sorting and limiting results'
        ]
    })