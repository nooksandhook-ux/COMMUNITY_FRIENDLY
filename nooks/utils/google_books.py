import requests
import os

GOOGLE_BOOKS_API_KEY = os.environ.get('GOOGLE_BOOKS_API_KEY', '')
GOOGLE_BOOKS_BASE_URL = 'https://www.googleapis.com/books/v1/volumes'

def search_books(query, max_results=10):
    """Search for books using Google Books API"""
    try:
        params = {
            'q': query,
            'maxResults': max_results,
            'key': GOOGLE_BOOKS_API_KEY
        }
        
        response = requests.get(GOOGLE_BOOKS_BASE_URL, params=params)
        response.raise_for_status()
        
        data = response.json()
        books = []
        
        for item in data.get('items', []):
            volume_info = item.get('volumeInfo', {})
            
            book = {
                'google_books_id': item['id'],
                'title': volume_info.get('title', 'Unknown Title'),
                'authors': volume_info.get('authors', ['Unknown Author']),
                'description': volume_info.get('description', ''),
                'page_count': volume_info.get('pageCount', 0),
                'published_date': volume_info.get('publishedDate', ''),
                'categories': volume_info.get('categories', []),
                'cover_image': get_cover_image(volume_info),
                'preview_link': volume_info.get('previewLink', ''),
                'info_link': volume_info.get('infoLink', '')
            }
            books.append(book)
        
        return books
    
    except requests.RequestException as e:
        print(f"Error searching books: {e}")
        return []

def get_book_details(google_books_id):
    """Get detailed information about a specific book"""
    try:
        url = f"{GOOGLE_BOOKS_BASE_URL}/{google_books_id}"
        params = {'key': GOOGLE_BOOKS_API_KEY} if GOOGLE_BOOKS_API_KEY else {}
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        volume_info = data.get('volumeInfo', {})
        
        return {
            'google_books_id': data['id'],
            'title': volume_info.get('title', 'Unknown Title'),
            'authors': volume_info.get('authors', ['Unknown Author']),
            'description': volume_info.get('description', ''),
            'page_count': volume_info.get('pageCount', 0),
            'published_date': volume_info.get('publishedDate', ''),
            'categories': volume_info.get('categories', []),
            'cover_image': get_cover_image(volume_info),
            'preview_link': volume_info.get('previewLink', ''),
            'info_link': volume_info.get('infoLink', '')
        }
    
    except requests.RequestException as e:
        print(f"Error getting book details: {e}")
        return None

def get_cover_image(volume_info):
    """Extract the best available cover image"""
    image_links = volume_info.get('imageLinks', {})
    
    # Prefer larger images
    for size in ['extraLarge', 'large', 'medium', 'small', 'thumbnail', 'smallThumbnail']:
        if size in image_links:
            return image_links[size]
    
    return '/static/images/default-book-cover.png'